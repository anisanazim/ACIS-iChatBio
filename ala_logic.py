import os
import yaml
import requests
import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from urllib.parse import urlencode
import cloudscraper

from functools import cache
import requests

@cache
def get_bie_fields(base_url):
    url = f"{base_url}/species/ws/indexFields"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return set(field['name'] for field in response.json())

class OccurrenceSearchParams(BaseModel):
    """Pydantic model for ALA Occurrence Search API - matches real API structure while keeping user-friendly interface"""
    
    # Core search parameters
    q: Optional[str] = Field(None, 
        description="Main search query. Can be species name, vernacular name, or complex queries",
        examples=["Kangaroo", "Phascolarctos cinereus", "vernacularName:koala", "genus:Macropus","species:cinereus", "kingdom:Animalia"]
    )
    
    fq: Optional[List[str]] = Field(None,
        description="Filter queries array. Used for taxonomic, geographic, and temporal filters",
        examples=[["state:Queensland"], ["year:2020", "basis_of_record:HumanObservation"]]
    )
    
    fl: Optional[str] = Field(None,
        description="Fields to return in the search response",
        examples=["scientificName,commonName,decimalLatitude,decimalLongitude,eventDate"]
    )
    
    # Faceting parameters
    facets: Optional[List[str]] = Field(None,
        description="The facets to be included by the search",
        examples=[["basis_of_record", "state", "year"]]
    )
    
    flimit: Optional[int] = Field(None,
        description="The limit for the number of facet values to return",
        ge=1, examples=[10, 50]
    )
    
    fsort: Optional[str] = Field(None,
        description="The sort order for facets ('count' or 'index')",
        examples=["count", "index"]
    )
    
    foffset: Optional[int] = Field(None,
        description="The offset of facets to return",
        ge=0
    )
    
    fprefix: Optional[str] = Field(None,
        description="The prefix to limit facet values"
    )
    
    # Pagination parameters
    start: Optional[int] = Field(0,
        description="Paging start index",
        ge=0
    )
    
    pageSize: Optional[int] = Field(1000,
        description="Number of records to return per page",
        ge=1, le=1000
    )
    
    # Sorting parameters
    sort: Optional[str] = Field(None,
        description="The sort field to use",
        examples=["scientificName", "eventDate", "score"]
    )
    
    dir: Optional[str] = Field(None,
        description="Direction of sort ('asc' or 'desc')",
        examples=["asc", "desc"]
    )
    
    # Advanced parameters
    includeMultivalues: Optional[bool] = Field(None,
        description="Include multi values"
    )
    
    qc: Optional[str] = Field(None,
        description="The query context to be used for the search"
    )
    
    facet: Optional[bool] = Field(None,
        description="Enable/disable facets"
    )
    
    qualityProfile: Optional[str] = Field(None,
        description="The quality profile to use"
    )
    
    disableAllQualityFilters: Optional[bool] = Field(None,
        description="Disable all default filters"
    )
    
    disableQualityFilter: Optional[List[str]] = Field(None,
        description="Default filters to disable"
    )
    
    # Spatial search parameters
    radius: Optional[float] = Field(None,
        description="Radius for a spatial search in kilometers",
        gt=0, examples=[10.0, 50.0]
    )
    
    lat: Optional[float] = Field(None,
        description="Decimal latitude for the spatial search",
        ge=-90, le=90, examples=[-27.4698]
    )
    
    lon: Optional[float] = Field(None,
        description="Decimal longitude for the spatial search",
        ge=-180, le=180, examples=[153.0251]
    )
    
    wkt: Optional[str] = Field(None,
        description="Well Known Text for the spatial search",
        examples=["POLYGON((140 -40, 150 -40, 150 -30, 140 -30, 140 -40))"]
    )
    
    # Image metadata
    im: Optional[bool] = Field(None,
        description="Include image metadata"
    )
    
    # USER-FRIENDLY PARAMETERS (for backward compatibility)
    # These will be converted to q/fq parameters in build_occurrence_url
    
    scientificname: Optional[str] = Field(None, 
        description="Full scientific name (converted to q parameter)", 
        examples=["Phascolarctos cinereus", "Macropus rufus"]
    )
    
    kingdom: Optional[str] = Field(None, 
        description="Taxonomic kingdom (converted to fq filter)", 
        examples=["Animalia", "Plantae"]
    )
    
    phylum: Optional[str] = Field(None, 
        description="Taxonomic phylum (converted to fq filter)", 
        examples=["Chordata", "Arthropoda"]
    )
    
    class_name: Optional[str] = Field(None, alias="class",
        description="Taxonomic class (converted to fq filter)", 
        examples=["Mammalia", "Aves"]
    )
    
    order: Optional[str] = Field(None, 
        description="Taxonomic order (converted to fq filter)", 
        examples=["Diprotodontia", "Carnivora"]
    )
    
    family: Optional[str] = Field(None, 
        description="Taxonomic family (converted to fq filter)", 
        examples=["Phascolarctidae", "Macropodidae"]
    )
    
    genus: Optional[str] = Field(None, 
        description="Taxonomic genus (converted to fq filter)", 
        examples=["Phascolarctos", "Macropus"]
    )
    
    species: Optional[str] = Field(None, 
        description="Species epithet (converted to fq filter)", 
        examples=["cinereus", "rufus"]
    )
    
    state: Optional[str] = Field(None, 
        description="Australian state (converted to fq filter)", 
        examples=["Queensland", "New South Wales"]
    )
    
    year: Optional[str] = Field(None, 
        description="Year (converted to fq filter)", 
        examples=["2020", "2023"]
    )
    
    has_images: Optional[bool] = Field(None, 
        description="Filter to records with images (converted to fq filter)"
    )
    
    has_coordinates: Optional[bool] = Field(None, 
        description="Filter to records with coordinates (converted to fq filter)"
    )
    
    basis_of_record: Optional[str] = Field(None, 
        description="Type of record (converted to fq filter)", 
        examples=["PreservedSpecimen", "HumanObservation"]
    )
    
    # Fields for date range filtering
    startdate: Optional[str] = Field(None, 
        description="Start date for a date range filter (YYYY-MM-DD)",
        examples=["2020-01-01"]
    )
    enddate: Optional[str] = Field(None, 
        description="End date for a date range filter (YYYY-MM-DD)",
        examples=["2020-12-31"]
    )

    # Legacy pagination 
    limit: Optional[int] = Field(None, 
        description="Maximum results (converted to pageSize)", 
        ge=1, le=1000
    )
    
    offset: Optional[int] = Field(None, 
        description="Results to skip (converted to start)", 
        ge=0
    )

class OccurrenceLookupParams(BaseModel):
    """Parameters for looking up a single occurrence record by its UUID."""
    
    # Path parameter (required)
    recordUuid: str = Field(..., 
        description="The unique identifier (UUID) of the occurrence record.",
        examples=["ed26f40e-1dc1-499b-bf64-5d22cbeed5e6", "c4262666-3d23-4f69-8492-968d92823b65"]
    )
    
    # Query parameter (optional)
    im: Optional[bool] = Field(False,
        description="Include image metadata in the response",
        examples=[True, False]
    )

class OccurrenceFacetsParams(BaseModel):
    """Pydantic model for GET /occurrences/facets - Get distinct facet counts"""
    
    # Core search parameters (same as search endpoint)
    q: Optional[str] = Field(None, 
        description="Main search query. Examples 'q=Kangaroo' or 'q=vernacularName:red'",
        examples=["Kangaroo", "vernacularName:koala", "scientificName:Phascolarctos"]
    )
    
    fq: Optional[List[str]] = Field(None,
        description="Filter queries. Examples 'fq=state:Victoria&fq=state:Queensland'",
        examples=[["state:Victoria"], ["state:Queensland", "year:2020"]]
    )
    
    fl: Optional[str] = Field(None,
        description="Fields to return in the search response. Optional",
        examples=["scientificName,commonName,decimalLatitude,decimalLongitude"]
    )
    
    # Facet-specific parameters
    facets: Optional[List[str]] = Field(None,
        description="The facets to be included by the search",
        examples=[["basis_of_record", "state", "year"], ["institution_code", "collection_code"]]
    )
    
    flimit: Optional[int] = Field(None,
        description="The limit for the number of facet values to return",
        ge=1, examples=[10, 50, 100]
    )
    
    fsort: Optional[str] = Field(None,
        description="The sort order in which to return the facets. Either 'count' or 'index'",
        examples=["count", "index"]
    )
    
    foffset: Optional[int] = Field(None,
        description="The offset of facets to return. Used in conjunction to flimit",
        ge=0, examples=[0, 10, 20]
    )
    
    fprefix: Optional[str] = Field(None,
        description="The prefix to limit facet values",
        examples=["Aus", "New", "Qld"]
    )
    
    # Pagination parameters  
    start: Optional[int] = Field(0,
        description="Paging start index",
        ge=0
    )
    
    pageSize: Optional[int] = Field(1000,
        description="The number of records per page",
        ge=1, le=1000
    )
    
    # Sorting parameters
    sort: Optional[str] = Field(None,
        description="The sort field to use",
        examples=["scientificName", "eventDate"]
    )
    
    dir: Optional[str] = Field(None,
        description="Direction of sort",
        examples=["asc", "desc"]
    )
    
    # Advanced parameters
    includeMultivalues: Optional[bool] = Field(None,
        description="Include multi values"
    )
    
    qc: Optional[str] = Field(None,
        description="The query context to be used for the search. This will be used to generate extra query filters."
    )
    
    facet: Optional[bool] = Field(None,
        description="Enable/disable facets"
    )
    
    qualityProfile: Optional[str] = Field(None,
        description="The quality profile to use, null for default"
    )
    
    disableAllQualityFilters: Optional[bool] = Field(None,
        description="Disable all default filters"
    )
    
    disableQualityFilter: Optional[List[str]] = Field(None,
        description="Default filters to disable (currently can only disable on category, so it's a list of disabled category name)"
    )
    
    # Spatial search parameters
    radius: Optional[float] = Field(None,
        description="Radius for a spatial search",
        gt=0, examples=[10.0, 50.0]
    )
    
    lat: Optional[float] = Field(None,
        description="Decimal latitude for the spatial search",
        ge=-90, le=90, examples=[-27.4698]
    )
    
    lon: Optional[float] = Field(None,
        description="Decimal longitude for the spatial search",
        ge=-180, le=180, examples=[153.0251]
    )
    
    wkt: Optional[str] = Field(None,
        description="Well Known Text for the spatial search",
        examples=["POLYGON((140 -40, 150 -40, 150 -30, 140 -30, 140 -40))"]
    )
    # User-friendly filter parameters
    state: Optional[str] = Field(None, description="Filter by Australian state")
    year: Optional[str] = Field(None, description="Filter by year")
    has_images: Optional[bool] = Field(None, description="Filter for records with images")
    basis_of_record: Optional[str] = Field(None, description="Filter by the basis of record")

class SpeciesGuidLookupParams(BaseModel):
    """Pydantic model for GET /guid/{name} - Look up a taxon guid by name"""
    name: str = Field(..., 
        description="The name to search the taxon guid",
        examples=["kangaroo", "Macropus rufus", "koala", "Phascolarctos cinereus"]
    )

class SpeciesImageSearchParams(BaseModel):
    """Pydantic model for GET /imageSearch/{id} - Search for a taxon with images"""
    id: str = Field(...,
        description="The guid of a specific taxon, data resource, layer etc. GUIDs can be URLs but can also be interpolated into paths",
        examples=[
            "https://id.biodiversity.org.au/node/apni/29057",
            "https://biodiversity.org.au/afd/taxa/7e6e134b-2bc7-43c4-b23a-6e3f420f57ad"
        ]
    )
    
    start: Optional[int] = Field(
    None,
    description="The records offset, to enable paging",
    ge=1, examples=[1, 10, 20]
    )

    rows: Optional[int] = Field(
        None,
        description="The number of records to return, to enable paging",
        ge=1, le=100, examples=[5, 10, 20]
    )
    
    qc: Optional[str] = Field(None,
        description="Solr query context, passed on to the search engine"
    )

class SpeciesBieSearchParams(BaseModel):
    """Pydantic model for GET /search - Search the BIE"""
    q: str = Field(...,
        description="Primary search query for the form field value e.g. q=rk_genus:Macropus or free text e.g q=gum",
        examples=["gum", "rk_genus:Macropus", "Eucalyptus", "kangaroo"]
    )
    
    fq: Optional[str] = Field(None,
        description="Filters to be applied to the original query. These are additional params of the form fq=INDEXEDFIELD:VALUE",
        examples=["imageAvailable:\"true\"", "rank:species"]
    )
    
    start: Optional[int] = Field(0,
        description="The records offset, to enable paging",
        ge=0, examples=[0, 10, 20]
    )
    
    pageSize: Optional[int] = Field(100,
        description="The number of records to return",
        ge=1, le=100, examples=[5, 10, 20]
    )
    
    sort: Optional[str] = Field("commonNameSingle",
        description="The field to sort the records by",
        examples=["commonNameSingle", "score", "scientificName", "rank"]
    )
    
    dir: Optional[str] = Field("desc",
        description="Sort direction 'asc' or 'desc'",
        examples=["asc", "desc"]
    )
    
    facets: Optional[str] = Field(None,
        description="Comma separated list of fields to display facets for",
        examples=["datasetName,commonNameExact", "rank,genus"]
    )

class NoParams(BaseModel):
    """An empty model for entrypoints that require no parameters."""
    pass

class SpatialDistributionByLsidParams(BaseModel):
    lsid: str = Field(
        ...,
        description="Life Science Identifier for the taxon in https:// format",
        examples=[
            "https://biodiversity.org.au/afd/taxa/6a01d711-2ac6-4928-bab4-a1de1a58e995",
            "https://biodiversity.org.au/afd/taxa/ae56080e-4e73-457d-93a1-0be6a1d50f34"
        ]
    )
    @field_validator('lsid')
    def validate_lsid(cls, v):
        if not v.startswith("https://biodiversity.org.au/afd/taxa/"):
            raise ValueError("Invalid LSID format")
        return v

   

class SpatialDistributionMapParams(BaseModel):
    """Pydantic model for distribution map image for a species (after fetching the imageId) """
    imageId: str = Field(..., 
        description="The image ID for the distribution map", 
        examples=[
            "30444","31539","30561"
        ]
    )

class OccurrenceTaxaCountParams(BaseModel):
    """Pydantic model for GET /occurrences/taxaCount - Report occurrence counts for supplied list of taxa"""
    
    # Required parameter
    guids: str = Field(...,
        description="taxonConceptIDs, newline separated (by default). Provide the GUIDs/LSIDs for the taxa you want counts for.",
        examples=[
            "https://biodiversity.org.au/afd/taxa/7e6e134b-2bc7-43c4-b23a-6e3f420f57ad",
            "https://biodiversity.org.au/afd/taxa/7e6e134b-2bc7-43c4-b23a-6e3f420f57ad\nhttps://biodiversity.org.au/afd/taxa/another-guid",
            "urn:lsid:biodiversity.org.au:afd.taxon:31a9b8b8-4e8f-4343-a15f-2ed24e0bf1ae"
        ]
    )
    
    # Optional parameters
    fq: Optional[List[str]] = Field(None,
        description="Filter queries to apply when counting occurrences",
        examples=[["state:Queensland"], ["year:2020", "basis_of_record:HumanObservation"]]
    )
    
    separator: Optional[str] = Field("\n",
        description="Separator character for the guids parameter",
        examples=["\n", ",", "|"]
    )

class TaxaCountHelper(BaseModel):
    """User-friendly helper for counting taxa - converts common queries to GUIDs"""
    
    # User-friendly parameters
    species_names: Optional[List[str]] = Field(None,
        description="List of scientific names to count",
        examples=[["Phascolarctos cinereus", "Macropus rufus"], ["Eucalyptus globulus"]]
    )
    
    common_names: Optional[List[str]] = Field(None,
        description="List of common names to count", 
        examples=[["koala", "kangaroo"], ["blue gum"]]
    )
    
    # Filter parameters
    state: Optional[str] = Field(None,
        description="Australian state to filter by",
        examples=["Queensland", "New South Wales"]
    )
    
    year: Optional[int] = Field(None,
        description="Year to filter by",
        examples=[2020, 2023]
    )
    
    basis_of_record: Optional[str] = Field(None,
        description="Type of record to filter by",
        examples=["HumanObservation", "PreservedSpecimen"]
    )

# 2. GET /ws/specieslist/{druid} - Get species list details
class SpeciesListDetailsParams(BaseModel):
    """Get details of a specific species list"""
    druid: str = Field(..., 
        description="The data resource ID to identify a list (required for specific list, optional for multiple lists)",
        examples=["dr781", "dr123", "dr456"]
    )
    sort: Optional[str] = Field("dataResourceUid",
        description="The field on which to sort the returned results",
        examples=["dataResourceUid", "listName", "dateCreated"]
    )
    max: int = Field(10, description="The number of records to return", ge=1, le=1000)
    offset: int = Field(0, description="The records offset, to enable paging", ge=0)

# 3. GET /ws/specieslistItems/{druid} - Get species list items
class SpeciesListItemsParams(BaseModel):
    """Get species within a specific list with advanced filtering"""
    druid: str = Field(...,
        description="The data resource ID or comma separated data resource IDs to identify lists",
        examples=["dr781", "dr123","dr781","dr332"]
    )
    q: Optional[str] = Field(None,
        description="Optional query string to search common name, supplied name and scientific name",
        examples=["Acacia pycnantha", "Eurystomus orientalis", "golden wattle"]
    )
    nonulls: bool = Field(True,
        description="Whether to include or exclude species list items with null value for species guid"
    )
    sort: str = Field("itemOrder",
        description="The field on which to sort the returned results",
        examples=["itemOrder", "scientificName", "commonName"]
    )
    max: int = Field(10, description="The number of records to return", ge=1, le=1000)
    offset: int = Field(0, description="The records offset, to enable paging", ge=0)
    include_kvp: bool = Field(True,
        description="Whether to include KVP (key value pairs) values in the returned list item"
    )

# 4. GET /ws/specieslistItems/distinct/{field} - Get distinct field values
class SpeciesListDistinctFieldParams(BaseModel):
    """Get distinct values for a field across all species list items"""
    field: str = Field(...,
        description="The field (e.g. kingdom, matchedName, rawScientificName etc.) to get distinct values for",
        examples=["kingdom", "matchedName", "rawScientificName", "family", "genus"]
    )

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any

class ALASearchResponse(BaseModel):
    params: Dict[str, Any] = Field(description="Extracted API parameters")
    unresolved_params: List[str] = Field(default=[], description="Parameters needing clarification")
    clarification_needed: bool = Field(default=False, description="Whether clarification is required")
    clarification_reason: str = Field(default="", description="Why clarification is needed")
    artifact_description: str = Field(default="", description="Description of expected results")
    
    @field_validator('params')
    @classmethod
    def validate_params(cls, v, info):
        # Get original query from context if available
        context = info.context or {}
        original_query = context.get('original_query', '')
        
        # Check for temporal keywords
        temporal_keywords = ['before', 'after', 'since', 'between', 'in', 'during']
        has_temporal = any(keyword in original_query.lower() for keyword in temporal_keywords)
        
        if has_temporal:
            # Check if any temporal parameter exists
            temporal_params = ['year', 'startdate', 'enddate']
            has_temporal_param = any(param in v for param in temporal_params)
            
            if not has_temporal_param:
                raise ValueError(f"Temporal query detected ('{original_query}') but no temporal parameters extracted. Must include year, startdate, or enddate.")
                
        return v

class ALA:
    def __init__(self): 
        self.openai_client = instructor.patch(AsyncOpenAI(api_key=self._get_config_value("OPENAI_API_KEY"), base_url="https://api.ai.it.ufl.edu"))
        self.ala_api_base_url = self._get_config_value("ALA_API_URL", "https://api.ala.org.au")
        
        self.session = cloudscraper.create_scraper()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        })

    def _get_config_value(self, key: str, default: Optional[str] = None) -> Optional[str]:
        value = os.getenv(key)
        if value is None and os.path.exists('env.yaml'):
            with open('env.yaml', 'r') as f:
                value = (yaml.safe_load(f) or {}).get(key, default)
        return value if value is not None else default

    async def _extract_params_enhanced(self, user_query: str, response_model=ALASearchResponse):
        system_prompt = """
        You are an assistant that extracts search parameters for the Atlas of Living Australia (ALA) API.
        
        CRITICAL RULES:
        1. Extract ALL relevant parameters from the user query - taxonomic, spatial, AND temporal
        2. For temporal queries, ALWAYS extract year/date parameters:
        - "before 2018" → year="<2018"
        - "after 2020" → year="2020+"  
        - "between 2010 and 2020" → year="2010,2020"
        - "in 2021" → year="2021"
        - "since 2015" → year="2015+"
        
        3. For simple occurrence queries with common names, you can proceed WITHOUT scientific name resolution:
        - "Show me koala occurrences" → {"q": "koala"} (no resolution needed)
        - "Find wombat records" → {"q": "wombat"} (no resolution needed)
        - "Kangaroo sightings" → {"q": "kangaroo"} (no resolution needed)
        
        4. PRESERVE FULL LSIDs: If the query contains a full LSID URL (https://biodiversity.org.au/afd/taxa/...), 
        preserve it EXACTLY as-is in the 'q' parameter. DO NOT extract just the UUID part.
        Examples:
        - "Distribution of https://biodiversity.org.au/afd/taxa/00017b7e-89b3-4916-9c77-d4fbc74bdef6" 
            → {"q": "https://biodiversity.org.au/afd/taxa/00017b7e-89b3-4916-9c77-d4fbc74bdef6"}
        - "Spatial data for https://biodiversity.org.au/afd/taxa/12345-abcd-..." 
            → {"q": "https://biodiversity.org.au/afd/taxa/12345-abcd-..."}
        
        5. Only mark scientific_name as unresolved if:
        - The query is complex/ambiguous
        - Multiple species might match
        - User specifically asks for scientific details
        - You genuinely cannot determine the species
        
        6. Extract spatial parameters:
        - "in Queensland" → fq=["state:Queensland"]
        - "New South Wales" → fq=["state:New South Wales"]
        
        7. Extract taxonomic parameters:
        - "family Macropodidae" → family="Macropodidae"
        - "genus Eucalyptus" → genus="Eucalyptus"
        
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
        
        try:
            return await self.openai_client.chat.completions.create(
                model="gpt-4o-mini", 
                response_model=response_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract parameters from: {user_query}"}
                ],
                temperature=0,
                max_retries=3,
                validation_context={"original_query": user_query}  # Pass query for validation
            )
        except Exception as e:
            raise ValueError(f"Failed to extract parameters: {e}")
    
    async def convert_species_to_guids(self, names: List[str]) -> Dict[str, str]:
        guid_map = {}
        for name in names:
            try:
                params = SpeciesGuidLookupParams(name=name)
                url = self.build_species_guid_lookup_url(params)
                result = self.execute_request(url)
                guid = None
                if isinstance(result, list):
                    for entry in result:
                        if isinstance(entry, dict):
                            guid = (
                                entry.get('taxonConceptID') or
                                entry.get('guid') or
                                entry.get('acceptedIdentifier') or
                                entry.get('identifier')
                            )
                            if guid:
                                break
                elif isinstance(result, dict):
                    guid = (
                        result.get('taxonConceptID') or
                        result.get('guid') or
                        result.get('acceptedIdentifier') or
                        result.get('identifier')
                    )
                
                if guid and guid.startswith("https://biodiversity.org.au/afd/taxa/"):
                    lsid = "urn:lsid:biodiversity.org.au:afd.taxon:" + guid.rsplit("/", 1)[-1]
                    guid_map[name] = lsid
                elif guid:
                    guid_map[name] = guid
                else:
                    print(f"Warning: No GUID found for '{name}' in API response: {result}")
            except Exception as e:
                print(f"Warning: Could not find GUID for '{name}'. Skipping. Error: {e}")
        return guid_map

    async def get_taxa_counts(self, params: TaxaCountHelper) -> dict:
        """
        Orchestrates getting taxa counts from user-friendly names.
        """
        names_to_lookup = (params.species_names or []) + (params.common_names or [])
        if not names_to_lookup:
            raise ValueError("You must provide at least one species or common name.")

        # Step 1: Call the worker function to convert names to GUIDs
        guid_map = await self.convert_species_to_guids(names_to_lookup)
        
        all_guids = list(guid_map.values())
        if not all_guids:
            raise ValueError("Could not resolve any of the provided names to a valid GUID.")

        # Step 2: Construct filter queries (fq)
        fq_filters = []
        if params.state:
            fq_filters.append(f"state:{params.state}")
        if params.year:
            fq_filters.append(f"year:{params.year}")
        if params.basis_of_record:
            fq_filters.append(f"basis_of_record:{params.basis_of_record}")

        # Step 3: Build the final parameters for the API call
        taxa_count_params = OccurrenceTaxaCountParams(
            guids="\n".join(all_guids),
            fq=fq_filters if fq_filters else None
        )
        print("DEBUG fq param:", fq_filters, type(fq_filters))
        # Step 4: Build the URL and execute the request
        url = self.build_occurrence_taxa_count_url(taxa_count_params)
        return self.execute_request(url), url
 
    def build_occurrence_url(self, params: OccurrenceSearchParams) -> str:
        """Build occurrence search URL"""
        param_dict = params.model_dump(exclude_none=True, by_alias=True)
        api_params = {}
        fq_filters = [] 

        #  Remove q if spatial search params are present
        if (
            param_dict.get("lat") is not None
            and param_dict.get("lon") is not None
            and param_dict.get("radius") is not None
            and param_dict.get("q") is not None
        ):
            param_dict.pop("q")

        # Handle  API parameters directly
        direct_api_params = [
            'q', 'fl', 'facets', 'flimit', 'fsort', 'foffset', 'fprefix',
            'sort', 'dir', 'includeMultivalues', 'qc', 'facet', 'qualityProfile',
            'disableAllQualityFilters', 'disableQualityFilter', 'radius', 'lat', 'lon', 'wkt', 'im'
        ]
        
        for param in direct_api_params:
            if param in param_dict:
                api_params[param] = param_dict.pop(param)
                
        # Handle pagination - prefer API params, fall back to legacy
        api_params['pageSize'] = param_dict.pop('pageSize', param_dict.pop('limit', 20))
        api_params['start'] = param_dict.pop('start', param_dict.pop('offset', 0))

        # Handle existing fq parameter
        if 'fq' in param_dict:
            fq_filters.extend(param_dict.pop('fq'))
        
        # Handle main query - prefer explicit q, fall back to scientificname
        if 'q' not in api_params and 'scientificname' in param_dict:
            api_params['q'] = f'scientificName:"{param_dict.pop("scientificname")}"'
        elif 'scientificname' in param_dict:
            # If both q and scientificname are present, pop scientificname to avoid it being processed later
            param_dict.pop("scientificname")

        # Convert user-friendly parameters to fq filters
        fq_mapping = {
            'kingdom': 'kingdom', 'phylum': 'phylum', 'class': 'class', 
            'order': 'order', 'family': 'family', 'genus': 'genus', 
            'species': 'species', 'state': 'state', 'year': 'year', 
            'basis_of_record': 'basis_of_record'
        }
        
        for user_param, api_field in fq_mapping.items():
            if user_param in param_dict:
                value = param_dict.pop(user_param)
                if user_param == "year":
                    # Handle ranges in value
                    if isinstance(value, str) and "," in value:
                        # Example: year='2001,2025' -> year:[2001 TO 2025]
                        years = [v.strip() for v in value.split(",")]
                        if len(years) == 2:
                            fq_filters.append(f'{api_field}:[{years[0]} TO {years[1]}]')
                        else:
                            fq_filters.extend([f'{api_field}:{y}' for y in years if y])
                    elif isinstance(value, str) and value.endswith("+"):
                        # Example: year='2001+' -> year:[2002 TO *] (after 2001)
                        year_start = value[:-1]
                        fq_filters.append(f'{api_field}:[{int(year_start)+1} TO *]')
                    elif isinstance(value, str) and value.startswith("<"):
                        # Example: year='<2018' -> year:[* TO 2017] (before 2018)
                        year_end = value[1:]  # Remove '<'
                        fq_filters.append(f'{api_field}:[* TO {int(year_end)-1}]')
                    elif isinstance(value, str) and value.startswith(">"):
                        # Example: year='>2020' -> year:[2021 TO *] (after 2020)
                        year_start = value[1:]  # Remove '>'
                        fq_filters.append(f'{api_field}:[{int(year_start)+1} TO *]')
                    elif isinstance(value, str) and value.isdigit():
                        # Example: year='2021' -> year:2021
                        fq_filters.append(f'{api_field}:{value}')
                    elif isinstance(value, (list, tuple)) and len(value) == 2:
                        # Example: year=[2010, 2020] -> year:[2010 TO 2020]
                        fq_filters.append(f'{api_field}:[{value[0]} TO {value[1]}]')
                    else:
                        # Fallback for other formats
                        fq_filters.append(f'{api_field}:{value}')
         
        # Handle date ranges
        start_date = param_dict.pop('startdate', None)
        end_date = param_dict.pop('enddate', None)
        if start_date or end_date:
            start_str = f"{start_date}T00:00:00Z" if start_date else "*"
            end_str = f"{end_date}T23:59:59Z" if end_date else "NOW"
            fq_filters.append(f"occurrence_date:[{start_str} TO {end_str}]")
            
        # Handle boolean filters
        if param_dict.pop('has_images', None):
            fq_filters.append("multimedia:Image")
        
        if param_dict.pop('has_coordinates', None):
            fq_filters.append("geospatial_kosher:true")
        
        # Add combined filters to the final parameter dictionary
        if fq_filters:
            api_params['fq'] = fq_filters
            
        base_url = self.ala_api_base_url
        endpoint_path = "/occurrences/occurrences/search"
        query_string = urlencode(api_params, doseq=True, quote_via=requests.utils.quote)

        return f"{base_url}{endpoint_path}?{query_string}"

    def build_occurrence_lookup_url(self, params: OccurrenceLookupParams) -> str:
        """Builds the API URL for looking up a single occurrence."""
        base_url = f"{self.ala_api_base_url}/occurrences/occurrences/{params.recordUuid}"
        
        # Add query parameters if needed
        query_params = {}
        if params.im is not None:
            query_params['im'] = str(params.im).lower()
        
        if query_params:
            query_string = urlencode(query_params)
            return f"{base_url}?{query_string}"
        else:
            return base_url
        
    def build_occurrence_facets_url(self, params: OccurrenceFacetsParams) -> str:
        """Build URL for GET /occurrences/facets"""
        param_dict = params.model_dump(exclude_none=True, by_alias=True)
        api_params = {}
        fq_filters = []

        # Remove q if spatial search params are present ---
        if (
            param_dict.get("lat") is not None
            and param_dict.get("lon") is not None
            and param_dict.get("radius") is not None
            and param_dict.get("q") is not None
        ):
            param_dict.pop("q")

        # Handle direct API parameters first
        direct_params = [
            'q', 'fl', 'facets', 'flimit', 'fsort', 'foffset', 'fprefix',
            'start', 'pageSize', 'sort', 'dir', 'includeMultivalues', 'qc', 'facet',
            'qualityProfile', 'disableAllQualityFilters', 'disableQualityFilter',
            'radius', 'lat', 'lon', 'wkt'
        ]
        
        for param in direct_params:
            if param in param_dict:
                api_params[param] = param_dict.pop(param)
        
        # Handle any pre-formatted fq filters
        if 'fq' in param_dict:
            fq_filters.extend(param_dict.pop('fq'))

        # Convert user-friendly parameters to fq filters
        if param_dict.pop('has_images', None):
            fq_filters.append("multimedia:Image")
        
        if 'state' in param_dict:
            fq_filters.append(f"state:{param_dict.pop('state')}")

        if 'year' in param_dict:
            value = param_dict.pop('year')
            if isinstance(value, str) and ',' in value:
                years = [v.strip() for v in value.split(",")]
                if len(years) == 2:
                    fq_filters.append(f'year:[{years[0]} TO {years[1]}]')
                else:
                    fq_filters.extend([f'year:{y}' for y in years if y])
            elif isinstance(value, str) and value.endswith("+"):
                year_start = value[:-1]
                fq_filters.append(f'year:[{year_start} TO *]')
            elif isinstance(value, str):
                fq_filters.append(f'year:{value}')
            elif isinstance(value, (list, tuple)) and len(value) == 2:
                fq_filters.append(f'year:[{value[0]} TO {value[1]}]')
            else:
                fq_filters.append(f'year:{value}')

        if 'basis_of_record' in param_dict:
            fq_filters.append(f"basis_of_record:{param_dict.pop('basis_of_record')}")

        # Add the final list of filters to the API parameters
        if fq_filters:
            api_params['fq'] = fq_filters
        
        # Build the final URL
        query_string = urlencode(api_params, doseq=True, quote_via=requests.utils.quote)
        return f"{self.ala_api_base_url}/occurrences/occurrences/facets?{query_string}"

    def build_index_fields_url(self) -> str:
        """Builds the API URL for getting all indexed fields."""
        return f"{self.ala_api_base_url}/occurrences/index/fields"
    
    def build_species_guid_lookup_url(self, params: SpeciesGuidLookupParams) -> str:
        """Build URL for GET /guid/{name}"""
        encoded_name = requests.utils.quote(params.name, safe='')
        return f"{self.ala_api_base_url}/species/guid/{encoded_name}"

    def build_species_image_search_url(self, params: SpeciesImageSearchParams) -> str:
        """Build URL for GET /imageSearch/{id}"""
        # Handle URL encoding for the ID parameter
        encoded_id = requests.utils.quote(params.id, safe='')
        
        # Build query parameters
        query_params = {}

        if params.start is not None:
            query_params["start"] = params.start
        if params.rows is not None:
            query_params["rows"] = params.rows
        if params.qc:
            query_params["qc"] = params.qc

        if query_params:
            query_string = urlencode(query_params)
            return f"{self.ala_api_base_url}/species/imageSearch/{encoded_id}?{query_string}"
        else:
            return f"{self.ala_api_base_url}/species/imageSearch/{encoded_id}"


    def build_species_bie_search_url(self, params: SpeciesBieSearchParams) -> str:
        """Build URL for GET /search"""
        query_params = {
            "q": params.q,
            "start": params.start,
            "pageSize": params.pageSize,
            "sort": params.sort,
            "dir": params.dir
        }
        
        if params.fq:
            query_params["fq"] = params.fq
        
        if params.facets:
            query_params["facets"] = params.facets
        
        query_string = urlencode(query_params, quote_via=requests.utils.quote)
        return f"{self.ala_api_base_url}/species/search?{query_string}" 
   

    def build_spatial_distribution_by_lsid_url(self, lsid: str):
        # The API expects the LSID to be URL-encoded
        encoded_lsid = requests.utils.quote(lsid, safe='')
        return f"{self.ala_api_base_url}/spatial-service/distribution/lsids/{encoded_lsid}"
    
    def build_spatial_distribution_map_url(self, imageId: str) -> str:
        return f"{self.ala_api_base_url}/spatial-service/distribution/map/png/{imageId}"
    
    def build_occurrence_taxa_count_url(self, params: OccurrenceTaxaCountParams) -> str:
        """Build URL for GET /occurrences/taxaCount"""
        
        # Build query parameters
        api_params = {
            "guids": params.guids
        }
        
        if params.fq:
            api_params["fq"] = params.fq
        
        if params.separator != "\n":  # Only add if different from default
            api_params["separator"] = params.separator
        
        # Build the URL with query string
        query_string = urlencode(api_params, doseq=True, quote_via=requests.utils.quote)
        return f"{self.ala_api_base_url}/occurrences/occurrences/taxaCount?{query_string}"
    
    def build_species_list_details_url(self, params: SpeciesListDetailsParams) -> str:
        """Build URL for GET /ws/specieslist/{druid}"""
        query_params = {
            "sort": params.sort,
            "max": params.max,
            "offset": params.offset
        }
        query_string = urlencode(query_params)
        return f"{self.ala_api_base_url}/specieslist/ws/speciesList/{params.druid}?{query_string}"

    def build_species_list_items_url(self, params: SpeciesListItemsParams) -> str:
        """Build URL for GET /ws/speciesListItems/{druid}"""
        query_params = {
            "nonulls": str(params.nonulls).lower(),
            "sort": params.sort,
            "max": params.max,
            "offset": params.offset,
            "includeKVP": str(params.include_kvp).lower()
        }
        
        if params.q:
            query_params["q"] = params.q
        
        query_string = urlencode(query_params)
        return f"{self.ala_api_base_url}/specieslist/ws/speciesListItems/{params.druid}?{query_string}"

    def build_species_list_distinct_field_url(self, params: SpeciesListDistinctFieldParams) -> str:
        """Build URL for GET /ws/speciesListItems/distinct/{field}"""
        return f"{self.ala_api_base_url}/specieslist/ws/speciesListItems/distinct/{params.field}"


    def execute_image_request(self, url: str) -> bytes:
        """Execute request for image data (PNG)."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Image request failed: {e}")    
        
    def execute_request(self, url: str) -> dict:
        """Execute GET request and return JSON response."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            try:
                return response.json()
            except ValueError:
                raise ConnectionError(f"API response was not JSON. Response: {response.text[:200]}")
        except requests.exceptions.Timeout:
            raise ConnectionError("API took too long to respond. Consider refining your request to reduce response time.")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"API request failed: {e}")


    def execute_post_request(self, url: str, data: dict) -> dict:
        """Execute POST request with JSON data."""
        try:
            response = self.session.post(url, json=data, timeout=30)
            response.raise_for_status()
            try:
                return response.json()
            except ValueError:
                raise ConnectionError(f"API response was not JSON. Response: {response.text[:200]}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"POST request failed: {e}")