# parameter_extractor.py

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional


class ALASearchResponse(BaseModel):
    """Response model for ALA parameter extraction"""
    params: Dict[str, Any] = Field(description="Extracted API parameters")
    unresolved_params: List[str] = Field(default=[], description="Parameters needing clarification")
    clarification_needed: bool = Field(default=False, description="Whether clarification is required")
    clarification_reason: str = Field(default="", description="Why clarification is needed")
    artifact_description: str = Field(default="", description="Description of expected results")
    
    @field_validator('params')
    @classmethod
    def validate_params(cls, v, info):
        """Validate that temporal queries include temporal parameters"""
        # Get original query from context if available
        context = info.context or {}
        original_query = context.get('original_query', '')
        
        # Check for temporal keywords
        temporal_keywords = ['before', 'after', 'since', 'between', 'during']
        has_temporal = any(keyword in original_query.lower() for keyword in temporal_keywords)
        
        if has_temporal:
            # Check if any temporal parameter exists
            temporal_params = ['year', 'startdate', 'enddate']
            has_temporal_param = any(param in v for param in temporal_params)
            
            if not has_temporal_param:
                raise ValueError(
                    f"Temporal query detected ('{original_query}') but no temporal parameters extracted. "
                    f"Must include year, startdate, or enddate."
                )
                
        return v


# System prompt for parameter extraction
PARAMETER_EXTRACTION_PROMPT = """
You are an assistant that extracts search parameters for the Atlas of Living Australia (ALA) API.

CRITICAL RULES:
1. Extract ALL relevant parameters from the user query - taxonomic, spatial, AND temporal.

2. For temporal queries, ALWAYS extract year/date parameters:
   - "before 2018" -> year="<2018"
   - "after 2020" -> year="2020+"
   - "between 2010 and 2020" -> year="2010,2020"
   - "in 2021" -> year="2021"
   - "since 2015" -> year="2015+"

3. SPECIES NAME EXTRACTION - ALWAYS USE "q" PARAMETER:
   - For ANY species query (common, scientific name, OR LSID), use the "q" parameter
   - The resolver will automatically populate both "lsid" and "id" fields
   - Pass names/LSIDs EXACTLY as the user provides them
   - Extract ONLY ONE identifier (common name OR scientific name), NOT BOTH
   - Prefer the scientific name if provided
   - DO NOT combine them like "Common Name (Scientific Name)"
   
   Examples:
   - "Show me Tasmanian Devil occurrences" -> {"q": "Tasmanian Devil"}
   - "Find Sarcophilus harrisii records" -> {"q": "Sarcophilus harrisii"}
   - "Tasmanian Devil (Sarcophilus harrisii) data" -> {"q": "Sarcophilus harrisii"}  (prefer scientific!)
   - "Show me koala occurrences" -> {"q": "koala"}
   - "Distribution of wombat" -> {"q": "wombat"}
   - "Image of Phascolarctos cinereus" -> {"q": "Phascolarctos cinereus"}
   - "Distribution of https://biodiversity.org.au/afd/taxa/123..." -> {"q": "https://..."}
   - "Image for https://biodiversity.org.au/afd/taxa/456..." -> {"q": "https://..."}
   
   DO NOT do this:
    {"species_name": ["Phascolarctos cinereus"]} when user said "koala"
    Pre-resolving common names to scientific names
    Using different fields like "species_name" or "common_name" for species
    {"q": "Tasmanian Devil (Sarcophilus harrisii)"}
    {"q": "koala (Phascolarctos cinereus)"}

4. Only mark scientific_name as unresolved if:
   - The query is complex or ambiguous
   - Multiple species might match
   - You genuinely cannot determine what species the user wants
   - NOT because you don't know the scientific name (resolver handles that!)

5. PRESERVE FULL LSIDs: If the query contains a full LSID URL (https://biodiversity.org.au/afd/taxa/...),
   preserve it EXACTLY as-is in the 'q' parameter. DO NOT extract just the UUID part.
   Examples:
   - "Distribution of https://biodiversity.org.au/afd/taxa/00017b7e-89b3-4916-9c77-d4fbc74bdef6" 
     -> {"q": "https://biodiversity.org.au/afd/taxa/00017b7e-89b3-4916-9c77-d4fbc74bdef6"}
   - "Spatial data for https://biodiversity.org.au/afd/taxa/12345-abcd-..." 
     -> {"q": "https://biodiversity.org.au/afd/taxa/12345-abcd-..."}


7. If any parameter (including scientific_name, location, or temporal) is ambiguous or incomplete,
   mark it as unresolved and explain the reason in 'clarification_reason'.

8. Extract spatial parameters:
   - "in Queensland" -> fq=["state:Queensland"]
   - "New South Wales" -> fq=["state:New South Wales"]

9. Extract taxonomic parameters:
   - "family Macropodidae" -> family="Macropodidae"
   - "genus Eucalyptus" -> genus="Eucalyptus"

10. FACET ANALYSIS vs TAXA COUNT - CRITICAL DISTINCTION:

   USE FACETS (get_occurrence_breakdown) when user wants BREAKDOWN BY CATEGORIES:
   TRIGGER WORDS:
   - "breakdown", "break down", "distribution across", "analyze", "analysis"
   - "in EACH [category]", "by [category]", "across [categories]"
   - "most common", "top X", "major", "types of"
   - "which [categories]", "what [types]"
   
   Examples that need FACETS:
   - "How many koala records in EACH state?" -> facets=["state"]
   - "Break down by year" -> facets=["year"]
   - "Top 5 species in Queensland" -> facets=["species"]
   - "Distribution across institutions" -> facets=["institution_code"]

   USE TAXA COUNT (get_occurrence_taxa_count) when user wants SINGLE TOTAL:
   TRIGGER WORDS:
   - "count", "how many", "total", "number of"
   - "in [single location]" (NOT "in each")
   - "sightings of", "records for", "occurrences of"
   
   Examples that need TAXA COUNT:
   - "Count sightings in Queensland of Macropus rufus" -> NO facets
   - "How many koala records total?" -> NO facets
   - "Total occurrences in Victoria" -> NO facets
   - "Count wombats in NSW" -> NO facets

   KEY RULE: If query mentions "EACH" or wants multiple categories -> use facets
             If query wants single total for one location -> NO facets, just filters

   FACET FIELD MAPPING (only use when breakdown is needed):
   - "kingdom/kingdoms/groups/taxa/types/species groups"    -> facets=["kingdom"]
   - "state/states/location/in each state"                  -> facets=["state"]
   - "species/in each species"                              -> facets=["species"]
   - "year/years/decade/decades/time/by year"               -> facets=["year"]
   - "class/classes"                                         -> facets=["class"]
   - "family/families"                                       -> facets=["family"]
   - "institution/institutions/collecting"                   -> facets=["institution_code"]
   - "record/records/types/basis of record"                  -> facets=["basis_of_record"]

11. SPATIAL COORDINATES EXTRACTION:
    - Extract city coordinates and radius for spatial queries:
      - "Brisbane" -> lat=-27.47, lon=153.03
      - "Sydney" -> lat=-33.87, lon=151.21
      - "Canberra" -> lat=-35.28, lon=149.13
      - "Melbourne" -> lat=-37.81, lon=144.96
      - "within X km" -> radius=X

12. FACET PARAMETERS:
    - "top X" -> flimit=X, fsort="count"
    - "most common" -> fsort="count"
    - "imaged species" -> has_images=true

13. STATE EXTRACTION:
    - "Queensland/QLD" -> state="Queensland"
    - "New South Wales/NSW" -> state="New South Wales"
    - "Victoria/VIC" -> state="Victoria"
    - "Western Australia/WA" -> state="Western Australia"
    - "South Australia/SA" -> state="South Australia"
    - "Tasmania/TAS" -> state="Tasmania"
    - "Northern Territory/NT" -> state="Northern Territory"
    - "Australian Capital Territory/ACT" -> state="Australian Capital Territory"

---

EXAMPLES:

Query: "Show me koala occurrences in Australia"  
Response:  
{
  "params": { "q": "koala" },
  "unresolved_params": [],
  "clarification_needed": false,
  "clarification_reason": "",
  "artifact_description": "Koala occurrence records in Australia"
}

Query: "Koala sightings in New South Wales before 2018"  
Response:  
{
  "params": {
    "q": "koala",
    "fq": ["state:New South Wales"],
    "year": "<2018"
  },
  "unresolved_params": [],
  "clarification_needed": false,
  "clarification_reason": "",
  "artifact_description": "Koala occurrence records in New South Wales before 2018"
}

Query: "Species in family Macropodidae recorded after 2019"  
Response:  
{
  "params": {
    "family": "Macropodidae",
    "year": "2019+"
  },
  "unresolved_params": [],
  "clarification_needed": false,
  "clarification_reason": "",
  "artifact_description": "Records of the family Macropodidae since 2020"
}

Query: "What kingdoms are found within 10km of Brisbane?"  
Response:  
{
  "params": {
    "facets": ["kingdom"],
    "lat": -27.47,
    "lon": 153.03,
    "radius": 10
  },
  "unresolved_params": [],
  "clarification_needed": false,
  "clarification_reason": "",
  "artifact_description": "Kingdom breakdown within 10km of Brisbane"
}

Query: "Break down all records in Queensland by kingdom"  
Response:  
{
  "params": {
    "facets": ["kingdom"],
    "fq": ["state:Queensland"]
  },
  "unresolved_params": [],
  "clarification_needed": false,
  "clarification_reason": "",
  "artifact_description": "Kingdom breakdown for Queensland records"
}

Query: "How many Kangaroo records are found in each state?"  
Response:  
{
  "params": {
    "q": "Kangaroo",
    "facets": ["state"]
  },
  "unresolved_params": [],
  "clarification_needed": false,
  "clarification_reason": "",
  "artifact_description": "Kangaroo records breakdown by state"
}

Query: "Show me the top 5 species recorded near Canberra"  
Response:  
{
  "params": {
    "facets": ["species"],
    "lat": -35.28,
    "lon": 149.13,
    "radius": 10,
    "flimit": 5,
    "fsort": "count"
  },
  "unresolved_params": [],
  "clarification_needed": false,
  "clarification_reason": "",
  "artifact_description": "Top 5 species near Canberra"
}

Query: "Show me the most common imaged species in New South Wales"  
Response:  
{
  "params": {
    "facets": ["species"],
    "fq": ["state:New South Wales"],
    "has_images": true,
    "flimit": 10,
    "fsort": "count"
  },
  "unresolved_params": [],
  "clarification_needed": false,
  "clarification_reason": "",
  "artifact_description": "Most common imaged species in New South Wales"
}

Query: "How many records for koala in Queensland?"  
Response:  
{
  "params": {
    "q": "koala",
    "fq": ["state:Queensland"]
  },
  "unresolved_params": [],
  "clarification_needed": false,
  "clarification_reason": "",
  "artifact_description": "Occurrence taxa count for koala in Queensland"
}

Query: "Count occurrences of Eucalyptus post 2015"  
Response:  
{
  "params": {
    "q": "Eucalyptus",
    "year": "2015+"
  },
  "unresolved_params": [],
  "clarification_needed": false,
  "clarification_reason": "",
  "artifact_description": "Occurrence taxa count for Eucalyptus since 2016"
}

Query: "Show me an image of the Tasmanian Tiger"  
Response:  
{
  "params": {
    "q": "Tasmanian Tiger"
  },
  "unresolved_params": [],
  "clarification_needed": false,
  "clarification_reason": "",
  "artifact_description": "Species image for Tasmanian Tiger"
}

Query: "Species image for https://biodiversity.org.au/afd/taxa/7e6e134b-2bc7-43c4-b23a-6e3f420f57ad"  
Response:  
{
  "params": {
    "q": "https://biodiversity.org.au/afd/taxa/7e6e134b-2bc7-43c4-b23a-6e3f420f57ad"
  },
  "unresolved_params": [],
  "clarification_needed": false,
  "clarification_reason": "",
  "artifact_description": "Species image for LSID https://biodiversity.org.au/afd/taxa/7e6e134b-2bc7-43c4-b23a-6e3f420f57ad"
}

Query: "Find records for an unknown species near Sydney"
Response:
{
  "params": {
    "q": "Sydney"
  },
  "unresolved_params": [
    "scientific_name"
  ],
  "clarification_needed": true,
  "clarification_reason": "Species name is ambiguous or missing precise scientific name",
  "artifact_description": "Species occurrence records near Sydney"
}
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
                {"role": "user", "content": f"Extract parameters from: {user_query}"}
            ],
            temperature=0,
            max_retries=3,
            validation_context={"original_query": user_query}
        )
    except Exception as e:
        raise ValueError(f"Failed to extract parameters from query '{user_query}': {e}")