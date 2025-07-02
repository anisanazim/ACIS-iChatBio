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
    """Pydantic model for ALA API parameters with detailed Field metadata for the LLM."""
    scientificname: Optional[str] = Field(None, description="Full scientific name (e.g., 'Phascolarctos cinereus' for koala)", examples=["Phascolarctos cinereus", "Macropus rufus"])
    taxonid: Optional[str] = Field(None, description="Taxon concept ID from ALA taxonomy", examples=["urn:lsid:biodiversity.org.au:afd.taxon:31a9b8b8-4e8f-4343-a15f-2ed24e0bf1ae"])
    kingdom: Optional[str] = Field(None, description="Taxonomic kingdom", examples=["Animalia", "Plantae", "Fungi"])
    phylum: Optional[str] = Field(None, description="Taxonomic phylum", examples=["Chordata", "Arthropoda"])
    class_name: Optional[str] = Field(None, alias="class", description="Taxonomic class", examples=["Mammalia", "Aves"])
    order: Optional[str] = Field(None, description="Taxonomic order", examples=["Diprotodontia", "Carnivora"])
    family: Optional[str] = Field(None, description="Taxonomic family", examples=["Phascolarctidae", "Macropodidae"])
    genus: Optional[str] = Field(None, description="Taxonomic genus", examples=["Phascolarctos", "Macropus"])
    species: Optional[str] = Field(None, description="Species epithet only", examples=["cinereus", "rufus"])
    country: Optional[str] = Field(None, description="Country name", examples=["Australia"])
    state: Optional[str] = Field(None, description="Australian state or territory", examples=["Queensland", "New South Wales"])
    locality: Optional[str] = Field(None, description="Specific locality or place name", examples=["Sydney", "Kakadu National Park"])
    year: Optional[str] = Field(None, description="A single, specific year (e.g., 1995). For date ranges, use startdate and enddate.", examples=["2020", "1995"])
    month: Optional[str] = Field(None, description="Month number (1-12). For ranges, use startdate and enddate.", examples=["6", "9"])
    startdate: Optional[str] = Field(None, description="The start date for a search range in YYYY-MM-DD format. Use this for queries like 'since 2020' or 'after 2022'.", examples=["2020-01-01", "2023-01-01"])
    enddate: Optional[str] = Field(None, description="The end date for a search range in YYYY-MM-DD format. Use this for queries like 'before 1990'. If a start date is given but no end date, the range will go to the present day.", examples=["1989-12-31"])
    lat: Optional[float] = Field(None, description="Latitude for geographic search", ge=-90, le=90, examples=[-27.4698])
    lon: Optional[float] = Field(None, description="Longitude for geographic search", ge=-180, le=180, examples=[153.0251])
    radius: Optional[float] = Field(None, description="Search radius in kilometers", gt=0, examples=[10, 50])
    has_images: Optional[bool] = Field(None, description="Filter to records with images")
    has_coordinates: Optional[bool] = Field(None, description="Filter to records with GPS coordinates")
    institution_code: Optional[str] = Field(None, description="Institution that holds the specimen", examples=["ANIC", "MEL"])
    collection_code: Optional[str] = Field(None, description="Collection within the institution", examples=["Mammals"])
    basis_of_record: Optional[str] = Field(None, description="Type of record", examples=["PreservedSpecimen", "HumanObservation"])
    limit: int = Field(20, description="Maximum number of results to return", ge=1, le=1000)
    offset: int = Field(0, description="Number of results to skip for pagination", ge=0)

class OccurrenceLookupParams(BaseModel):
    """Parameters for looking up a single occurrence record by its UUID."""
    uuid: str = Field(..., description="The unique identifier (UUID) of the occurrence record.", examples=["c4262666-3d23-4f69-8492-968d92823b65"])

class SpeciesSearchParams(BaseModel):
    """Pydantic model for faceted species search."""
    q: str = Field(..., description="The search query string (e.g., 'rk_genus:Macropus').")
    fq: Optional[List[str]] = Field(None, description="A list of filter queries to apply (e.g., ['rank:species']).")
    limit: int = Field(20, description="Maximum number of results to return.", ge=1)
    offset: int = Field(0, description="Number of results to skip for pagination.", ge=0)

class SpeciesLookupParams(BaseModel):
    """Pydantic model for Species API parameters."""
    name: str = Field(..., description="Scientific name, common name, or LSID for species lookup", examples=["Phascolarctos cinereus", "koala"])
    include_children: Optional[bool] = Field(False, description="Include child taxa in response", examples=[True, False])
    include_synonyms: Optional[bool] = Field(False, description="Include taxonomic synonyms", examples=[True, False])

class NoParams(BaseModel):
    """An empty model for entrypoints that require no parameters."""
    pass

class SpatialRegionListParams(BaseModel):
    type: str = Field(..., description="Region type (e.g., STATE, IBRA, LGA, etc.)")


class ALA:
    def __init__(self):
        self.openai_client = instructor.patch(AsyncOpenAI(api_key=self._get_config_value("OPENAI_API_KEY")))
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
        param_dict = params.model_dump(exclude_none=True, by_alias=True)
        api_params, fq = {}, []
        if 'startdate' in param_dict or 'enddate' in param_dict:
            start = param_dict.pop('startdate') + "T00:00:00Z" if 'startdate' in param_dict else "*"
            end = param_dict.pop('enddate') + "T23:59:59Z" if 'enddate' in param_dict else "NOW"
            fq.append(f"occurrence_date:[{start} TO {end}]")
        for key, value in param_dict.items():
            if key == "scientificname": api_params["q"] = value
            elif key in ["limit", "offset"]: api_params[key] = value
            elif isinstance(value, str) and " " in value: fq.append(f'{key}:"{value}"')
            elif key == "has_images" and value: fq.append("multimedia:Image")
            elif key == "has_coordinates" and value: fq.append("geospatial_kosher:true")
            else: fq.append(f"{key}:{value}")
        if fq: api_params["fq"] = " AND ".join(fq)
        return f"{self.ala_api_base_url}/occurrences/occurrences/search?{urlencode(api_params, quote_via=requests.utils.quote)}"
    

    def build_occurrence_lookup_url(self, params: OccurrenceLookupParams) -> str:
        """Builds the API URL for looking up a single occurrence."""
        return f"{self.ala_api_base_url}/occurrences/{params.uuid}"

    def build_index_fields_url(self) -> str:
        """Builds the API URL for getting all indexed fields."""
        return f"{self.ala_api_base_url}/occurrences/index/fields"
    
    def build_species_lookup_url(self, params: SpeciesLookupParams) -> str:
        """Builds the API URL for looking up a single species."""
        base_params = {"includeChildren": params.include_children, "includeSynonyms": params.include_synonyms}
        query = urlencode({k: str(v).lower() for k, v in base_params.items() if v is not None})
        return f"{self.ala_api_base_url}/species/{requests.utils.quote(params.name)}?{query}"
    
    def build_species_search_url(self, params: SpeciesSearchParams) -> str:
        """Builds the API URL for a faceted species search."""
        param_dict = params.model_dump(exclude_none=True)
        if 'limit' in param_dict:
            param_dict['pageSize'] = param_dict.pop('limit')
        if 'offset' in param_dict:
            param_dict['startIndex'] = param_dict.pop('offset')
            
        query = urlencode(param_dict, doseq=True) # doseq=True handles list parameters like fq
        return f"{self.ala_api_base_url}/species/search?{query}"
    
    def build_spatial_distributions_url(self):
        return f"{self.ala_api_base_url}/spatial-service/distributions"

    def execute_request(self, url: str) -> Dict[str, Any]:
        """Executes a synchronous web request using the session object."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"API request failed: {e}")