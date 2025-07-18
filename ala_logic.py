import os
import yaml
import requests
import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from urllib.parse import urlencode
import cloudscraper

class OccurrenceSearchParams(BaseModel):
    """Pydantic model for ALA Occurrence Search API - matches real API structure while keeping user-friendly interface"""
    
    # Core search parameters
    q: Optional[str] = Field(None, 
        description="Main search query. Can be species name, vernacular name, or complex queries",
        examples=["Kangaroo", "Phascolarctos cinereus", "vernacularName:koala"]
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
    
    pageSize: Optional[int] = Field(20,
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
    
    pageSize: Optional[int] = Field(20,
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
    
    start: Optional[int] = Field(1,
        description="The records offset, to enable paging",
        ge=1, examples=[1, 10, 20]
    )
    
    rows: Optional[int] = Field(5,
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
    
    pageSize: Optional[int] = Field(5,
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
    """Pydantic model for distribution information for a specific LSID"""
    lsid: str = Field(..., 
        description="Life Science Identifier for the taxon in https:// format", 
        examples=[
            "https://biodiversity.org.au/afd/taxa/6a01d711-2ac6-4928-bab4-a1de1a58e995",
            "https://biodiversity.org.au/afd/taxa/ae56080e-4e73-457d-93a1-0be6a1d50f34"
        ]
    )    

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

# 1. POST /ws/specieslist/filter - Filter lists by scientific names or drIds
class SpeciesListFilterParams(BaseModel):
    """Filter species lists by scientific names or data resource IDs"""
    scientific_names: Optional[List[str]] = Field(None,
        description="List of scientific names to filter by",
        examples=[["Phascolarctos cinereus"], ["Macropus rufus", "Osphranter robustus"]]
    )
    dr_ids: Optional[List[str]] = Field(None,
        description="List of data resource IDs to filter by", 
        examples=[["dr123", "dr456"]]
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

# 5. GET /ws/listCommonKeys - Get common keys across species lists
class SpeciesListCommonKeysParams(BaseModel):
    """Get a list of common keys (KVP) across multiple species lists"""
    druid: str = Field(...,
        description="Comma separated data resource IDs to identify lists",
        examples=["dr781", "dr123","dr781","dr332"]
    )

class ALA:
    def __init__(self): # Corrected to double underscores
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

    async def _extract_params(self, user_query: str, response_model):
        system_prompt = "You are an assistant that extracts search parameters for the Atlas of Living Australia (ALA) API..."
        try:
            return await self.openai_client.chat.completions.create(
                model="gpt-4o-mini", response_model=response_model,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": f"Extract parameters from: {user_query}"}],
                temperature=0,
            ) 
        except Exception as e:
            raise ValueError(f"Failed to extract parameters: {e}")
    
    def build_occurrence_url(self, params: OccurrenceSearchParams) -> str:
        """Build occurrence search URL"""
        param_dict = params.model_dump(exclude_none=True, by_alias=True)
        api_params = {}
        fq_filters = []
        
        # Handle real API parameters directly
        direct_api_params = [
            'q', 'fl', 'facets', 'flimit', 'fsort', 'foffset', 'fprefix',
            'sort', 'dir', 'includeMultivalues', 'qc', 'facet', 'qualityProfile',
            'disableAllQualityFilters', 'disableQualityFilter', 'radius', 'lat', 'lon', 'wkt', 'im'
        ]
        
        for param in direct_api_params:
            if param in param_dict:
                api_params[param] = param_dict.pop(param)
        
        # Handle pagination - prefer real API params, fall back to legacy
        if 'pageSize' in param_dict:
            api_params['pageSize'] = param_dict.pop('pageSize')
        elif 'limit' in param_dict:
            api_params['pageSize'] = param_dict.pop('limit')
        else:
            api_params['pageSize'] = 20  # default
        
        if 'start' in param_dict:
            api_params['start'] = param_dict.pop('start')
        elif 'offset' in param_dict:
            api_params['start'] = param_dict.pop('offset')
        else:
            api_params['start'] = 0  # default
        
        # Handle existing fq parameter
        if 'fq' in param_dict:
            existing_fq = param_dict.pop('fq')
            if isinstance(existing_fq, list):
                fq_filters.extend(existing_fq)
            else:
                fq_filters.append(existing_fq)
        
        # Handle main query - prefer explicit q, fall back to scientificname
        if 'q' in param_dict:
            api_params['q'] = param_dict.pop('q')
        elif 'scientificname' in param_dict:
            api_params['q'] = f'scientificName:"{param_dict.pop("scientificname")}"'
        
        # Convert user-friendly parameters to fq filters
        taxonomic_fields = ['kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species']
        for field in taxonomic_fields:
            if field in param_dict:
                value = param_dict.pop(field)
                if isinstance(value, str) and " " in value:
                    fq_filters.append(f'{field}:"{value}"')
                else:
                    fq_filters.append(f'{field}:{value}')
        
        # Handle geographic filters
        if 'state' in param_dict:
            state = param_dict.pop('state')
            if " " in state:
                fq_filters.append(f'state:"{state}"')
            else:
                fq_filters.append(f'state:{state}')
        
        # Handle temporal filters
        if 'year' in param_dict:
            fq_filters.append(f'year:{param_dict.pop("year")}')
        
        # Handle date ranges (your existing logic)
        if 'startdate' in param_dict or 'enddate' in param_dict:
            start = param_dict.pop('startdate', None)
            end = param_dict.pop('enddate', None)
            start_str = start + "T00:00:00Z" if start else "*"
            end_str = end + "T23:59:59Z" if end else "NOW"
            fq_filters.append(f"occurrence_date:[{start_str} TO {end_str}]")
        
        # Handle boolean filters
        if param_dict.get('has_images'):
            fq_filters.append("multimedia:Image")
            param_dict.pop('has_images')
        
        if param_dict.get('has_coordinates'):
            fq_filters.append("geospatial_kosher:true")
            param_dict.pop('has_coordinates')
        
        # Handle basis of record
        if 'basis_of_record' in param_dict:
            fq_filters.append(f'basis_of_record:{param_dict.pop("basis_of_record")}')
        
        for key, value in param_dict.items():
            if value is not None:
                if isinstance(value, str) and " " in value:
                    fq_filters.append(f'{key}:"{value}"')
                else:
                    fq_filters.append(f'{key}:{value}')
        
        if fq_filters:
            api_params['fq'] = fq_filters if len(fq_filters) > 1 else fq_filters[0]
        
        return f"{self.ala_api_base_url}/occurrences/occurrences/search?{urlencode(api_params, doseq=True, quote_via=requests.utils.quote)}"

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
        # Handle direct API parameters
        direct_params = [
            'q', 'fq', 'fl', 'facets', 'flimit', 'fsort', 'foffset', 'fprefix',
            'start', 'pageSize', 'sort', 'dir', 'includeMultivalues', 'qc', 'facet',
            'qualityProfile', 'disableAllQualityFilters', 'disableQualityFilter',
            'radius', 'lat', 'lon', 'wkt'
        ]
        
        for param in direct_params:
            if param in param_dict:
                api_params[param] = param_dict[param]
        
        # Build the URL with query string
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
        query_params = {
            "start": params.start,
            "rows": params.rows
        }
        
        if params.qc:
            query_params["qc"] = params.qc
        
        query_string = urlencode(query_params)
        return f"{self.ala_api_base_url}/species/imageSearch/{encoded_id}?{query_string}"

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
   
    def build_spatial_distributions_url(self):
        return f"{self.ala_api_base_url}/spatial-service/distributions"

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
    
    async def convert_species_to_guids(self, species_names: List[str]) -> Dict[str, str]:
        """
        Helper method to convert species names to GUIDs using species search.
        This would use your existing species search functionality.
        """
        # TODO: Implement this to automatically convert species names to GUIDs
        # For now, users need to provide GUIDs directly
        guid_map = {}
        for name in species_names:
            # This would do a species search to find the GUID for each name
            # guid_map[name] = found_guid
            pass
        return guid_map

    def build_species_list_filter_url(self, params: SpeciesListFilterParams) -> tuple:
        """Build URL and request body for POST /ws/specieslist/filter"""
        request_body = {}
        
        if params.scientific_names:
            request_body["scientificNames"] = params.scientific_names
        
        if params.dr_ids:
            request_body["drIds"] = params.dr_ids
        
        if not request_body:
            raise ValueError("At least one filter (scientific_names or dr_ids) must be provided")
        
        url = f"{self.ala_api_base_url}/specieslist/ws/specieslist/filter"
        return url, request_body

    def build_species_list_details_url(self, params: SpeciesListDetailsParams) -> str:
        """Build URL for GET /ws/specieslist/{druid}"""
        query_params = {
            "sort": params.sort,
            "max": params.max,
            "offset": params.offset
        }
        query_string = urlencode(query_params)
        return f"{self.ala_api_base_url}/specieslist/ws/specieslist/{params.druid}?{query_string}"

    def build_species_list_items_url(self, params: SpeciesListItemsParams) -> str:
        """Build URL for GET /ws/specieslistItems/{druid}"""
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
        return f"{self.ala_api_base_url}/specieslist/ws/specieslistItems/{params.druid}?{query_string}"

    def build_species_list_distinct_field_url(self, params: SpeciesListDistinctFieldParams) -> str:
        """Build URL for GET /ws/specieslistItems/distinct/{field}"""
        return f"{self.ala_api_base_url}/specieslist/ws/specieslistItems/distinct/{params.field}"

    def build_species_list_common_keys_url(self, params: SpeciesListCommonKeysParams) -> str:
        """Build URL for GET /ws/listCommonKeys"""
        query_params = {"druid": params.druid}
        query_string = urlencode(query_params)
        return f"{self.ala_api_base_url}/specieslist/ws/listCommonKeys?{query_string}"

    def execute_image_request(self, url: str) -> bytes:
        """Execute request for image data (PNG)."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Image request failed: {e}")    
        
    def execute_request(self, url: str) -> dict:
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            try:
                return response.json()
            except ValueError:
                raise ConnectionError(f"API response was not JSON. Response: {response.text[:200]}")
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