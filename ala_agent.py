import os
import yaml
from pydantic import BaseModel, Field, field_validator, ValidationError
from datetime import datetime
import requests
from openai import OpenAI
import json
from typing import Optional, List, Dict, Any
from urllib.parse import urlencode
import instructor


class OccurrenceSearchParams(BaseModel):
    """Pydantic model for ALA API parameters with Field metadata"""
    
    scientificname: Optional[str] = Field(
        None,
        description="Full scientific name (e.g., 'Phascolarctos cinereus' for koala)",
        examples=["Phascolarctos cinereus", "Macropus rufus", "Eucalyptus globulus"]
    )
    
    taxonid: Optional[str] = Field(
        None,
        description="Taxon concept ID from ALA taxonomy",
        examples=["urn:lsid:biodiversity.org.au:afd.taxon:31a9b8b8-4e8f-4343-a15f-2ed24e0bf1ae"]
    )
    
    kingdom: Optional[str] = Field(
        None,
        description="Taxonomic kingdom",
        examples=["Animalia", "Plantae", "Fungi"]
    )
    
    phylum: Optional[str] = Field(
        None,
        description="Taxonomic phylum",
        examples=["Chordata", "Arthropoda", "Magnoliophyta"]
    )
    
    class_name: Optional[str] = Field(
        None,
        alias="class",
        description="Taxonomic class (use 'class_name' in code, mapped to 'class' in API)",
        examples=["Mammalia", "Aves", "Insecta"]
    )
    
    order: Optional[str] = Field(
        None,
        description="Taxonomic order",
        examples=["Primates", "Carnivora", "Lepidoptera"]
    )
    
    family: Optional[str] = Field(
        None,
        description="Taxonomic family",
        examples=["Phascolarctidae", "Macropodidae", "Myrtaceae"]
    )
    
    genus: Optional[str] = Field(
        None,
        description="Taxonomic genus",
        examples=["Phascolarctos", "Macropus", "Eucalyptus"]
    )
    
    species: Optional[str] = Field(
        None,
        description="Species epithet only",
        examples=["cinereus", "rufus", "globulus"]
    )
    
    country: Optional[str] = Field(
        None,
        description="Country name (primarily Australia for ALA)",
        examples=["Australia"]
    )
    
    state: Optional[str] = Field(
        None,
        description="Australian state or territory",
        examples=["Queensland", "New South Wales", "Victoria", "Tasmania", 
                 "Western Australia", "South Australia", "Northern Territory", 
                 "Australian Capital Territory"]
    )
    
    locality: Optional[str] = Field(
        None,
        description="Specific locality or place name",
        examples=["Sydney", "Great Barrier Reef", "Kakadu National Park"]
    )
    
    year: Optional[str] = Field(
        None,
        description="Specific year or year range (YYYY or YYYY-YYYY)",
        examples=["2020", "2018-2022", "2000-2010"]
    )
    
    month: Optional[str] = Field(
        None,
        description="Month number (1-12) or range",
        examples=["6", "1-3", "12"]
    )
    
    startdate: Optional[str] = Field(
        None,
        description="Start date in YYYY-MM-DD format",
        examples=["2020-01-01", "2022-06-15"]
    )
    
    enddate: Optional[str] = Field(
        None,
        description="End date in YYYY-MM-DD format",
        examples=["2023-12-31", "2022-12-31"]
    )
    
    lat: Optional[float] = Field(
        None,
        description="Latitude for geographic search (decimal degrees)",
        examples=[-27.4698, -33.8688, -37.8136],
        ge=-90,
        le=90
    )
    
    lon: Optional[float] = Field(
        None,
        description="Longitude for geographic search (decimal degrees)",
        examples=[153.0251, 151.2093, 144.9631],
        ge=-180,
        le=180
    )
    
    radius: Optional[float] = Field(
        None,
        description="Search radius in kilometers (when using lat/lon)",
        examples=[10, 50, 100],
        gt=0
    )
    
    has_images: Optional[bool] = Field(
        None,
        description="Filter to records with images"
    )
    
    has_coordinates: Optional[bool] = Field(
        None,
        description="Filter to records with GPS coordinates"
    )
    
    institution_code: Optional[str] = Field(
        None,
        description="Institution that holds the specimen",
        examples=["ANIC", "MEL", "QM"]
    )
    
    collection_code: Optional[str] = Field(
        None,
        description="Collection within the institution",
        examples=["Mammals", "Insects", "Herbarium"]
    )
    
    basis_of_record: Optional[str] = Field(
        None,
        description="Type of record",
        examples=["PreservedSpecimen", "HumanObservation", "MachineObservation"]
    )
    
    limit: int = Field(
        20,
        description="Maximum number of results to return",
        ge=1,
        le=1000
    )
    
    offset: int = Field(
        0,
        description="Number of results to skip (for pagination)",
        ge=0
    )

    @field_validator('startdate', 'enddate')
    @classmethod
    def validate_date_format(cls, value):
        if value is None:
            return value
        
        if len(value) == 4 and value.isdigit():
            return f"{value}-01-01"
        
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return value
        except ValueError:
            raise ValueError("Incorrect date format, should be YYYY-MM-DD or YYYY")

    @field_validator('year')
    @classmethod
    def validate_year_format(cls, value):
        if value is None:
            return value
        # Allow single year or year range
        if '-' in value:
            start_year, end_year = value.split('-')
            try:
                int(start_year)
                int(end_year)
                return value
            except ValueError:
                raise ValueError("Year range should be in format YYYY-YYYY")
        else:
            try:
                int(value)
                return value
            except ValueError:
                raise ValueError("Year should be a 4-digit number")


class OccurrenceResponse(BaseModel):
    """Response model for occurrence search results"""
    
    total_records: int = Field(..., description="Total number of matching records")
    returned_records: int = Field(..., description="Number of records in this response")
    occurrences: List[Dict[str, Any]] = Field(..., description="List of occurrence records")
    query_url: str = Field(..., description="URL used for the API query")
    search_params: Dict[str, Any] = Field(..., description="Parameters used in the search")


class ALA:
    """Improved Atlas of Living Australia API client - stateless design"""
    
    def __init__(self):
        self.openai_client = instructor.patch(OpenAI(api_key=self._get_config_value("OPENAI_API_KEY")))
        self.ala_base_url = self._get_config_value("ALA_URL", "https://biocache.ala.org.au/ws/occurrences")

    def _get_config_value(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get configuration value from environment or YAML file"""
        value = os.getenv(key)
        if value is None:
            try:
                with open('env.yaml', 'r') as file:
                    data = yaml.safe_load(file)
                value = data.get(key, default)
            except FileNotFoundError:
                value = default
        return value

    def extract_search_parameters(self, user_query: str) -> OccurrenceSearchParams:
        """
        Extract search parameters from natural language using LLM with proper message roles
        
        Args:
            user_query: Natural language query from user
            
        Returns:
            Validated OccurrenceSearchParams object
        """
        
        system_message = """You are an assistant that extracts search parameters for the Atlas of Living Australia (ALA) API.
        
        Your task is to analyze natural language queries about Australian biodiversity and extract relevant search parameters.
        
        Guidelines:
        - Focus on Australian context - if location not specified, assume Australia
        - Convert common names to scientific names when possible (e.g., "koala" → "Phascolarctos cinereus")
        - Use appropriate taxonomic hierarchy
        - Set reasonable limits for searches (20-100 for general queries)
        - For location queries, use Australian states/territories
        - When users mention "images" or "photos", set has_images=true
        - When users mention coordinates/GPS/mapping, set has_coordinates=true
        
        Return only the extracted parameters as a valid JSON object matching the OccurrenceSearchParams schema."""
        
        user_message = f"Extract search parameters from this query: {user_query}"
        
        try:
            params = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                response_model=OccurrenceSearchParams,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0
            )
            return params
            
        except Exception as e:
            raise ValueError(f"Failed to extract parameters from query: {str(e)}")

    def build_api_url(self, params: OccurrenceSearchParams) -> str:
        """
        Build the ALA API URL from search parameters
        
        Args:
            params: Validated search parameters
            
        Returns:
            Complete API URL string
        """
        
        # Convert Pydantic model to dict, excluding None values
        param_dict = params.model_dump(exclude_none=True, by_alias=True)
        
        # Build query parameters for ALA biocache API
        api_params = {}
        filter_queries = []
        
        for key, value in param_dict.items():
            if key == "scientificname":
                # Use simple scientific name search in q parameter
                api_params["q"] = value
            elif key == "state":
                filter_queries.append(f"state:{value}")
            elif key == "country":
                filter_queries.append(f"country:{value}")
            elif key == "has_images" and value:
                filter_queries.append("multimedia:Image")
            elif key == "has_coordinates" and value:
                filter_queries.append("geospatial_kosher:true")
            elif key == "year":
                filter_queries.append(f"year:{value}")
            elif key == "startdate":
                filter_queries.append(f"occurrence_date:[{value}T00:00:00Z TO *]")
            elif key == "enddate":
                filter_queries.append(f"occurrence_date:[* TO {value}T23:59:59Z]")
            elif key in ["kingdom", "phylum", "class", "order", "family", "genus"]:
                filter_queries.append(f"{key}:{value}")
            elif key in ["locality", "institution_code", "collection_code", "basis_of_record"]:
                filter_queries.append(f"{key}:{value}")
            else:
                api_params[key] = value
        
        # Combine all filter queries
        if filter_queries:
            api_params["fq"] = " AND ".join(filter_queries)
        
        # Build final URL
        query_string = urlencode(api_params)
        return f"{self.ala_base_url}/search?{query_string}"

    def execute_search(self, url: str) -> Dict[str, Any]:
        """
        Execute the API search request
        
        Args:
            url: Complete API URL to query
            
        Returns:
            Raw API response as dictionary
        """
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise requests.HTTPError(
                    f"ALA API error {response.status_code}: {response.text}"
                )
                
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to connect to ALA API: {str(e)}")

    def format_search_results(self, raw_response: Dict[str, Any], 
                            search_params: OccurrenceSearchParams, 
                            query_url: str) -> OccurrenceResponse:
        """
        Format raw API response into structured result
        
        Args:
            raw_response: Raw response from ALA API
            search_params: Original search parameters
            query_url: URL used for the query
            
        Returns:
            Formatted OccurrenceResponse object
        """
        
        total_records = raw_response.get('totalRecords', 0)
        occurrences = raw_response.get('occurrences', [])
        
        return OccurrenceResponse(
            total_records=total_records,
            returned_records=len(occurrences),
            occurrences=occurrences,
            query_url=query_url,
            search_params=search_params.model_dump(exclude_none=True)
        )

    def create_display_summary(self, response: OccurrenceResponse) -> str:
        """
        Create user-friendly summary of search results
        
        Args:
            response: Formatted search response
            
        Returns:
            Human-readable summary string
        """
        
        if response.total_records == 0:
            return "No occurrences found in Atlas of Living Australia for your query."
        
        summary_lines = [
            f"Found {response.total_records} total records in Atlas of Living Australia.",
            f"Showing {response.returned_records} results:\n"
        ]
        
        for i, occ in enumerate(response.occurrences[:5], 1):
            name = occ.get('scientificName', 'Unknown species')
            lat = occ.get('decimalLatitude')
            lon = occ.get('decimalLongitude')
            locality = occ.get('locality', '')
            state = occ.get('stateProvince', '')
            country = occ.get('country', '')
            date = occ.get('eventDate', '')
            
            location_parts = [part for part in [locality, state, country] if part]
            location_str = ', '.join(location_parts) if location_parts else 'Location not specified'
            
            coord_str = f" ({lat}, {lon})" if lat and lon else ""
            date_str = f" on {date}" if date else ""
            
            summary_lines.append(f"{i}. {name} - {location_str}{coord_str}{date_str}")
        
        if response.returned_records < response.total_records:
            summary_lines.append(f"\n... and {response.total_records - response.returned_records} more records available.")
        
        # Add query information
        summary_lines.extend([
            f"\nQuery URL: {response.query_url}",
            f"Search parameters: {json.dumps(response.search_params, indent=2)}"
        ])
        
        return "\n".join(summary_lines)

    def search_occurrences(self, user_query: str) -> str:
        """
        Complete workflow: from user query to formatted results
        
        Args:
            user_query: Natural language query from user
            
        Returns:
            Human-readable summary of results
        """
        
        try:
            # Step 1: Extract parameters using LLM
            search_params = self.extract_search_parameters(user_query)
            print(f"✓ Extracted parameters: {search_params}")
            
            # Step 2: Build API URL
            api_url = self.build_api_url(search_params)
            print(f"✓ API URL: {api_url}")
            
            # Step 3: Execute search
            raw_response = self.execute_search(api_url)
            print(f"✓ API call successful")
            
            # Step 4: Format response
            formatted_response = self.format_search_results(raw_response, search_params, api_url)
            print(f"✓ Found {formatted_response.total_records} records")
            
            # Step 5: Create display summary
            display_summary = self.create_display_summary(formatted_response)
            
            return display_summary
            
        except Exception as e:
            return f"Error processing query: {str(e)}"


# Maintain backward compatibility with original interface
def main():
    """Main function for command-line usage"""
    ala = ALA()
    user_input = input("Enter Search Query: \n")
    
    if not user_input.strip():
        print("Please enter a valid search query")
        return
    
    result = ala.search_occurrences(user_input)
    print("\n" + "="*60)
    print("RESULTS:")
    print("="*60)
    print(result)


if __name__ == "__main__":
    main()