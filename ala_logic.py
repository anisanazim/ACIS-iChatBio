import os
import yaml
import requests
import instructor
from openai import AsyncOpenAI
from pydantic_core import PydanticUndefined
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Type, Tuple
from urllib.parse import urlencode
import cloudscraper
from parameter_extractor import extract_params_from_query, ALASearchResponse

from functools import cache
import requests

@cache
def get_bie_fields(base_url):
    url = f"{base_url}/species/ws/indexFields"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return set(field['name'] for field in response.json())

class NameMatchingSearchParams(BaseModel):
    """Parameters for scientific name search"""
    q: str = Field(..., description="Scientific name to search")

class VernacularNameSearchParams(BaseModel):
    """Parameters for vernacular/common name search"""
    vernacularName: str = Field(..., description="Common/vernacular name to search")

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

def map_params_to_model(resolved_params: dict, model_class: Type[BaseModel]) -> Tuple[BaseModel, List[str]]:
    model_fields = model_class.model_fields
    missing_required = []
    mapped = {}
    
    for name, field in model_fields.items():
        if name in resolved_params:
            mapped[name] = resolved_params[name]
        elif field.is_required():
            # Field is required and not provided
            missing_required.append(name)
        # Optional fields with defaults will be handled by Pydantic automatically
    
    return model_class(**mapped), missing_required

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

    async def extract_params(self, user_query: str, response_model=ALASearchResponse):
        """Wrapper for parameter extraction"""
        return await extract_params_from_query(
            openai_client=self.openai_client,
            user_query=user_query,
            response_model=response_model
        )
    
    def _get_config_value(self, key: str, default: Optional[str] = None) -> Optional[str]:
        value = os.getenv(key)
        if value is None and os.path.exists('env.yaml'):
            with open('env.yaml', 'r') as f:
                value = (yaml.safe_load(f) or {}).get(key, default)
        return value if value is not None else default
 
    def search_scientific_name(self, params: NameMatchingSearchParams) -> dict:
        """Search for a scientific name using name matching API."""
        query_params = {"q": params.q}
        query_string = urlencode(query_params)
        url = f"{self.ala_api_base_url}/namematching/api/search?{query_string}"
        return self.execute_request(url)

    def search_vernacular_name(self, params: VernacularNameSearchParams) -> dict:
        """Search for a vernacular/common name using name matching API."""
        query_params = {"vernacularName": params.vernacularName}
        query_string = urlencode(query_params)
        url = f"{self.ala_api_base_url}/namematching/api/searchByVernacularName?{query_string}"
        return self.execute_request(url)

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