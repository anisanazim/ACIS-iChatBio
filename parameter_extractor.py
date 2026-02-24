# parameter_extractor.py
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional

class ALASearchResponse(BaseModel):
    """Response model for ALA parameter extraction"""
    params: Dict[str, Any] = Field(default_factory=dict, description="Extracted API parameters - REQUIRED, use {} if truly no parameters needed")    
    unresolved_params: List[str] = Field(default_factory=list, description="Parameters needing clarification")
    clarification_needed: bool = Field(default=False, description="Whether clarification is required")
    clarification_reason: str = Field(default="", description="Why clarification is needed")
    artifact_description: str = Field(default="", description="Description of expected results")
    
    @field_validator('params')
    @classmethod
    def validate_params(cls, v, info):
        """Validate that temporal queries include temporal parameters"""
        # temporal‑consistency checker
        
        # shows exactly what the extractor produced
        print("DEBUG: Raw extracted params BEFORE validation:", v)

        # Get original query from context if available
        context = info.context or {}
        original_query = context.get('original_query', '')
        
        # Check for temporal keywords
        temporal_keywords = ['before', 'after', 'since', 'between', 'during', 'post']
        has_temporal = any(keyword in original_query.lower() for keyword in temporal_keywords)
        
        if has_temporal:
            # Check if any temporal parameter exists
            temporal_params = ['year', 'startdate', 'enddate']
            has_temporal_param = any(param in v for param in temporal_params)
            
            # Also check for month filters in fq parameter
            if not has_temporal_param and 'fq' in v:
                fq_filters = v['fq'] if isinstance(v['fq'], list) else [v['fq']]
                has_temporal_param = any('month:' in str(fq) for fq in fq_filters)
            
            # Also check for month faceting (seasonal breakdowns)
            if not has_temporal_param and 'facets' in v:
                facets = v['facets'] if isinstance(v['facets'], list) else [v['facets']]
                has_temporal_param = 'month' in facets
            
            if not has_temporal_param:
                raise ValueError(
                    f"Temporal query detected ('{original_query}') but no temporal parameters extracted. "
                    f"Must include year, startdate, enddate, month filter, or month faceting."
                )
                
        return v

PARAMETER_EXTRACTION_PROMPT = """
You extract structured ALA API parameters from natural language queries.

OUTPUT FORMAT:
- Respond with ONLY valid JSON matching ALASearchResponse.
- "params" must always exist (use {} if empty).
- No explanations, no markdown, no extra text.

---------------------------------------
CORE EXTRACTION RULES
---------------------------------------

1. SPECIES / IDENTIFIER EXTRACTION
- Put the species/common name/LSID EXACTLY as written into "q".
- Do NOT modify, resolve, or normalize names.
- Do NOT combine common + scientific names.
- Resolver will handle scientific/common/LSID resolution.
If the user does NOT mention a species, genus, or taxon name:
- Do NOT include "q" in the params.
- Do NOT set q="".
If the query contains an AFD/ALA taxon URL (e.g., https://biodiversity.org.au/afd/taxa/...),
- extract the FULL URL into the field "q".
- Do NOT shorten it, do NOT extract only the UUID, do NOT modify it.

2. TEMPORAL EXTRACTION

Convert natural language to:
- “before X” → year="<X"        (occurrence searches only)
- “after X”, “post X”, “since X” → year="X+"   (occurrence searches only)
- “in X” → year="X"
- “between A and B”, “from A to B” → year="A,B"

Relative temporal expressions:
- “last N years”, “past N years”, “last decade”, “past decade”
    → extract: relative_years = N
    → Do NOT compute actual years (backend will convert)

PLACEMENT RULES:

A. For occurrence searches (search_species_occurrences, get_occurrence_breakdown):
    → Use the field: year="…" exactly as extracted above.
    → Occurrence search supports ranges (e.g., "2021+", "<2000", "2010,2020").

B. For taxaCount queries (get_occurrence_taxa_count):
    IMPORTANT: taxaCount DOES NOT support ranges or operators.
    It only accepts exact years.

    Therefore:
    - “after X”, “post X”, “since X” → convert to the NEXT YEAR:
          post 2020 → year="2021"
          after 1999 → year="2000"
    - “before X” → NOT SUPPORTED for taxaCount → ignore the filter
    - “between A and B” → NOT SUPPORTED → ignore the filter unless A == B
    - “in X” → year="X"

    Then convert the year into fq entries:
        year="2021" → fq=["year:2021"]
        year="2000" → fq=["year:2000"]

    NEVER output:
        year="2021+"
        year="<2000"
        year="2010,2020"
        fq=["year:2021+"]
        fq=["year:<2000"]
        fq=["year:2010,2020"]

C. If no temporal intent is present:
    → Do NOT include “year” or “fq:year:…”

3. SPATIAL EXTRACTION
States:
- Normalize abbreviations (QLD → Queensland, NSW → New South Wales, etc.)

Cities → lat/lon:
- Brisbane (-27.47,153.03)
- Sydney (-33.87,151.21)
- Canberra (-35.28,149.13)
- Melbourne (-37.81,144.96)

Radius:
- “within X km” → radius=X

4. TAXONOMIC FILTERS
Extract when explicitly mentioned:
- kingdom=...
- phylum=...
- class=...
- order=...
- family=...
- genus=...

5. BASIS OF RECORD
Extract only when explicitly stated:
- specimens → PreservedSpecimen
- human observations → HumanObservation
- machine observations → MachineObservation
- living specimens → LivingSpecimen
- fossils → FossilSpecimen
- material samples → MaterialSample

6. MONTH / SEASON FILTERS
Use month numbers (1-12).

Seasons (Southern Hemisphere):
- summer → month:(12 OR 1 OR 2)
- autumn/fall → month:(3 OR 4 OR 5)
- winter → month:(6 OR 7 OR 8)
- spring → month:(9 OR 10 OR 11)

Specific months:
January=1, February=2, ..., December=12

Month ranges:
- Dec-Feb → (12 OR 1 OR 2)
- Jun-Aug → (6 OR 7 OR 8)
- Mar-May → (3 OR 4 OR 5)

7. FACETS vs TAXA COUNT

Use FACETS when the user wants breakdowns:
- “in each…”, “by…”, “distribution across…”, “top…”, “most…”, “common…”, “major…”, “types of…”

Explicit month-faceting triggers (because users phrase these differently):
- “break down by month”
- “monthly distribution”
- “month-wise”
- “which months”
- “by month”

Season comparison triggers:
- “summer or winter”
- “winter or summer”
- “compare seasons”
- “seasonal comparison”
- “seasonal difference”
→ facets=["month"]

Taxonomic rank plural handling:
If the user mentions a taxonomic rank in plural form 
(families, genera, orders, classes, phyla, kingdoms),
map it to the corresponding singular facet field.

State comparison triggers:
If the user lists multiple states in a comparison context,
use facets=["state"] and do NOT apply state filters

Use TAXA COUNT when the user wants totals:
- “how many”, “count”, “total occurrences”, “number of”

Facet field mapping:
- state → ["state"]
- species → ["species"]
- year → ["year"]
- month → ["month"]
- family → ["family"]
- class → ["class"]
- phylum → ["phylum"]
- order → ["order"]
- genus → ["genus"]
- kingdom → ["kingdom"]
- basis of record → ["basis_of_record"]
- institution → ["institution_code"]

8. FACET LIMIT & SORT RULES

- “top X …” →
    flimit = X
    fsort = "count"
    If the phrase is “top X species”, “top species”, or “top 5 species”:
        facets = ["species"]

- “most …”, “highest …”, “most common …” →
    fsort = "count"
    If the phrase is “most common species”, “species with the most records”:
        facets = ["species"]

- If the user explicitly names a facet 
  (“by kingdom”, “kingdom distribution”, “breakdown by family”, “top 10 families”):
    facets = [that facet]

- Seasonal comparisons (“summer vs winter”, etc.) →
    facets = ["month"]
    fsort = "count"

- If the query requests a ranking or top-N list but does not specify the facet:
    Default to facets=["species"] unless another facet is clearly implied.

9. AMBIGUITY
If species, temporal, or spatial intent is unclear:
- add to unresolved_params
- set clarification_needed=true
- explain briefly in clarification_reason

10. ARTIFACT DESCRIPTION
Provide a short natural-language summary of what the user wants.

---------------------------------------
EXAMPLES (pattern only)
---------------------------------------

Example 1 — Species + State:
Query: "Koala sightings in Queensland"
→ {"params": {"q": "koala", "state": "Queensland"}}

Example 2 — Date Range:
Query: "Koala sightings from 2020 to 2024"
→ {"params": {"q": "koala", "year": "2020,2024"}}

Example 3 — Has Images:
Query: "Koala records that have images"
→ {"params": {"q": "koala", "has_images": true}}

Example 4 — Facets:
Query: "Where are Eucalyptus trees most commonly found?"
→ {"params": {"q": "Eucalyptus", "facets": ["state"], "fsort": "count"}}

Example 5 — Basis of Record:
Query: "Preserved specimens of Tasmanian Devils"
→ {"params": {"q": "Tasmanian Devil", "basis_of_record": "PreservedSpecimen"}}

Example 6 — Season:
Query: "Rainbow Bee-eater sightings in summer"
→ {"params": {"q": "Rainbow Bee-eater", "fq": ["month:(12 OR 1 OR 2)"]}}

Example 7 — Total Count:
Query: "How many koala occurrences in Queensland?"
→ {"params": {"q": "koala", "state": "Queensland"}}

Example 8 — Top X:
Query: "Top 5 species near Canberra"
→ {"params": {"facets": ["species"], "lat": -35.28, "lon": 149.13, "radius": 10, "flimit": 5, "fsort": "count"}}

Example 9 — Relative Years:
Query: "Find Common Myna observations in the last 5 years"
→ {"params": {"q": "Common Myna", "relative_years": 5}}

Example 10 — LSID / AFD Taxon URL:
Query: "Can you give me the distribution of https://biodiversity.org.au/afd/taxa/56d25dd8-4282-4cd6-9bc7-baaa0b8adfc4?"
→ {"params": {"q": "https://biodiversity.org.au/afd/taxa/56d25dd8-4282-4cd6-9bc7-baaa0b8adfc4"}}

---------------------------------------
END OF RULES
---------------------------------------
"""

async def extract_params_from_query(
    openai_client,
    user_query: str,
    response_model=ALASearchResponse
) -> ALASearchResponse:
    """
    Extract API parameters from natural language query using LLM.
    
    Args:
        openai_client: OpenAI client instance (configured with instructor)
        user_query: Natural language query from user
        response_model: Pydantic model for structured output (default: ALASearchResponse)
    
    Returns:
        ALASearchResponse with extracted parameters
    
    Raises:
        ValueError: If parameter extraction fails
    
    Example:
        >>> client = instructor.from_openai(OpenAI())
        >>> result = await extract_params_from_query(
        ...     client,
        ...     "koala sightings in NSW after 2020"
        ... )
        >>> print(result.params)
        {'q': 'koala', 'fq': ['state:New South Wales'], 'year': '2020+'}
    """
    try:
        return await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            response_model=response_model,
            messages=[
                {"role": "system", "content": PARAMETER_EXTRACTION_PROMPT},
                {"role": "user", "content": f" {user_query}"}
            ],
            temperature=0,
            max_retries=3,
            validation_context={"original_query": user_query}
        )
    except Exception as e:
        raise ValueError(f"Failed to extract parameters from query '{user_query}': {e}")