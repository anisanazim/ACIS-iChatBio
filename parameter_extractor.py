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
1. Extract ALL relevant parameters from the user query - taxonomic, spatial, AND temporal

2. For temporal queries, ALWAYS extract year/date parameters:
   - "before 2018" -> year="<2018"
   - "after 2020" -> year="2020+"  
   - "between 2010 and 2020" -> year="2010,2020"
   - "in 2021" -> year="2021"
   - "since 2015" -> year="2015+"

3. For simple occurrence queries with common names, you can proceed WITHOUT scientific name resolution:
   - "Show me koala occurrences" -> {"q": "koala"} (no resolution needed)
   - "Find wombat records" -> {"q": "wombat"} (no resolution needed)
   - "Kangaroo sightings" -> {"q": "kangaroo"} (no resolution needed)

4. PRESERVE FULL LSIDs: If the query contains a full LSID URL (https://biodiversity.org.au/afd/taxa/...), 
   preserve it EXACTLY as-is in the 'q' parameter. DO NOT extract just the UUID part.
   Examples:
   - "Distribution of https://biodiversity.org.au/afd/taxa/00017b7e-89b3-4916-9c77-d4fbc74bdef6" 
     -> {"q": "https://biodiversity.org.au/afd/taxa/00017b7e-89b3-4916-9c77-d4fbc74bdef6"}
   - "Spatial data for https://biodiversity.org.au/afd/taxa/12345-abcd-..." 
     -> {"q": "https://biodiversity.org.au/afd/taxa/12345-abcd-..."}

5. Only mark scientific_name as unresolved if:
   - The query is complex/ambiguous
   - Multiple species might match
   - User specifically asks for scientific details
   - You genuinely cannot determine the species

6. Extract spatial parameters:
   - "in Queensland" -> fq=["state:Queensland"]
   - "New South Wales" -> fq=["state:New South Wales"]

7. Extract taxonomic parameters:
   - "family Macropodidae" -> family="Macropodidae"
   - "genus Eucalyptus" -> genus="Eucalyptus"

EXAMPLES:

Query: "Show me koala occurrences in Australia"
Response: {
    "params": {
        "q": "koala"
    },
    "unresolved_params": [],
    "clarification_needed": false,
    "clarification_reason": "",
    "artifact_description": "Koala occurrence records in Australia"
}

Query: "Koala sightings in New South Wales before 2018"
Response: {
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
Response: {
    "params": {
        "family": "Macropodidae",
        "year": "2019+"
    },
    "unresolved_params": [],
    "clarification_needed": false,
    "clarification_reason": "",
    "artifact_description": "Records of the family Macropodidae since 2020"
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