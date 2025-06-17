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
from datetime import datetime, timezone, timedelta
import argparse

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

class SpeciesSearchParams(BaseModel):
    """Pydantic model for Species API parameters"""
    name: str = Field(
        ...,
        description="Scientific name, common name, or LSID for species lookup",
        examples=["Phascolarctos cinereus", "koala", "urn:lsid:biodiversity.org.au:afd.taxon:31a9b8b8-4e8f-4343-a15f-2ed24e0bf1ae"]
    )
    include_children: Optional[bool] = Field(
        False,
        description="Include child taxa in response",
        examples=[True, False]
    )
    include_synonyms: Optional[bool] = Field(
        False,
        description="Include taxonomic synonyms in response",
        examples=[True, False]
    )

class OccurrenceResponse(BaseModel):
    """Response model for occurrence search results"""
    
    total_records: int = Field(..., description="Total number of matching records")
    returned_records: int = Field(..., description="Number of records in this response")
    occurrences: List[Dict[str, Any]] = Field(..., description="List of occurrence records")
    query_url: str = Field(..., description="URL used for the API query")
    search_params: Dict[str, Any] = Field(..., description="Parameters used in the search")

class SpeciesResponse(BaseModel):
    """Response model for species information"""
    lsid: Optional[str] = Field(..., description="Life Science Identifier")
    scientific_name: Optional[str] = Field(..., description="Accepted scientific name")
    common_names: Optional[List[str]] = Field(..., description="List of common names")
    taxonomy: Optional[Dict[str, str]] = Field(..., description="Full taxonomic classification")
    conservation_status: Optional[str] = Field(..., description="Conservation status in Australia")
    images: Optional[List[str]] = Field(..., description="List of image URLs")
    data_resources: Optional[List[str]] = Field(..., description="Data sources contributing information")
    query_url: str = Field(..., description="URL used for the API query")

class ALA:
    
    def __init__(self):
        self.openai_client = instructor.patch(OpenAI(api_key=self._get_config_value("OPENAI_API_KEY")))
        self.ala_base_url = self._get_config_value("ALA_URL", "https://biocache.ala.org.au/ws/occurrences")

    @property
    def species_base_url(self) -> str:
        return self._get_config_value("ALA_SPECIES_URL", "https://api.ala.org.au/species")
    
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

  
    def _format_event_date(self, date_value):
        """
        Convert eventDate to a readable string.
        Handles ISO dates, UNIX timestamps (seconds or ms), and returns as YYYY-MM-DD.
        """
        if not date_value:
            return ""
        # If already in ISO format (YYYY-MM-DD), just return
        if isinstance(date_value, str) and len(date_value) >= 10 and date_value[:4].isdigit() and date_value[4] == '-':
            return date_value[:10]
        try:
            ts = int(float(date_value))
            # Handle both ms and s timestamps (positive or negative)
            if abs(ts) > 1e12:
                ts_secs = ts / 1000.0
            else:
                ts_secs = ts
            try:
                dt = datetime.fromtimestamp(ts_secs, tz=timezone.utc)
            except (OSError, OverflowError, ValueError):
                # Fallback for platforms that can't handle large negative timestamps
                dt = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=ts_secs)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return str(date_value)
    
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

    def extract_species_parameters(self, user_query: str) -> SpeciesSearchParams:
        """
        Extract species search parameters from natural language using LLM.
        """
        system_message = """You are an assistant that extracts parameters for the ALA Species API.
        Extract the species name (scientific, common, or LSID) and flags for including children or synonyms.
        Return only the extracted parameters as a valid JSON object matching the SpeciesSearchParams schema."""
        user_message = f"Extract species search parameters from this query: {user_query}"
        try:
            params = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                response_model=SpeciesSearchParams,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0
            )
            return params
        except Exception as e:
            raise ValueError(f"Failed to extract species parameters from query: {str(e)}")

    def build_api_url(self, params: OccurrenceSearchParams) -> str:
        """
        Build the ALA API URL from search parameters.
        """
        param_dict = params.model_dump(exclude_none=True, by_alias=True)
        api_params = {}
        filter_queries = []

        # Handle date range as a single filter
        start_date = param_dict.pop('startdate', None)
        end_date = param_dict.pop('enddate', None)

        if start_date or end_date:
            start_str = f"{start_date}T00:00:00Z" if start_date else "*"
            end_str = f"{end_date}T23:59:59Z" if end_date else "*"
            filter_queries.append(f"occurrence_date:[{start_str} TO {end_str}]")

        # Define fields that need quoting for exact phrase matching
        text_fields_to_quote = [
            "state", "country", "locality", "institution_code", 
            "collection_code", "basis_of_record"
        ]

        for key, value in param_dict.items():
            if key == "scientificname":
                api_params["q"] = value
            elif key in ["limit", "offset"]:
                api_params[key] = value
            elif key in text_fields_to_quote:
                # This logic correctly quotes values with spaces
                filter_queries.append(f'{key}:"{value}"')
            elif key == "has_images" and value:
                filter_queries.append("multimedia:Image")
            elif key == "has_coordinates" and value:
                filter_queries.append("geospatial_kosher:true")
            elif key == "year":
                filter_queries.append(f"year:{value}")
            # Note: startdate and enddate are now handled above
            elif key in ["kingdom", "phylum", "class", "order", "family", "genus"]:
                filter_queries.append(f"{key}:{value}")
        
        # Combine all filter queries with "AND"
        if filter_queries:
            api_params["fq"] = " AND ".join(filter_queries)
        
        # Use quote_plus for robust URL encoding
        query_string = urlencode(api_params, quote_via=requests.utils.quote)
        return f"{self.ala_base_url}/search?{query_string}"


    def build_species_url(self, params: SpeciesSearchParams) -> str:
        """Build URL for species lookup API"""
        base_params = {
            "includeChildren": params.include_children,
            "includeSynonyms": params.include_synonyms
        }
        query_string = urlencode({k: str(v).lower() for k, v in base_params.items() if v is not None})
        
        encoded_name = requests.utils.quote(params.name)
        return f"{self.species_base_url}/{encoded_name}?{query_string}"
    
    def execute_species_search(self, url: str) -> Dict[str, Any]:
        """Execute species API request"""
        try:
            # Get API key for authentication
            api_key = self._get_config_value("ALA_API_KEY")
            
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                return response.json()
            raise requests.HTTPError(
                f"ALA Species API error {response.status_code}: {response.text}"
            )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to connect to ALA Species API: {str(e)}")
        
    def format_species_results(self, raw_response: Dict[str, Any], query_url: str) -> SpeciesResponse:
        """Format raw species API response"""
        return SpeciesResponse(
            lsid=raw_response.get('guid'),
            scientific_name=raw_response.get('scientificName'),
            common_names=raw_response.get('commonNames', []),
            taxonomy=raw_response.get('classification'),
            conservation_status=raw_response.get('conservationStatus'),
            images=[img.get('identifier') for img in raw_response.get('images', []) if img.get('identifier')],
            data_resources=raw_response.get('dataResources', []),
            query_url=query_url
        )
    
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
            formatted_date = self._format_event_date(date)
            
            location_parts = [part for part in [locality, state, country] if part]
            location_str = ', '.join(location_parts) if location_parts else 'Location not specified'
            
            coord_str = f" ({lat}, {lon})" if lat and lon else ""
            date_str = f" on {formatted_date}" if formatted_date else ""
            
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
        
        try:
            # Step 1: Extract parameters using LLM
            search_params = self.extract_search_parameters(user_query)
            print(f" Extracted parameters: {search_params}")
            
            # Step 2: Build API URL
            api_url = self.build_api_url(search_params)
            print(f" API URL: {api_url}")
            
            # Step 3: Execute search
            raw_response = self.execute_search(api_url)
            print(f" API call successful")
            
            # Step 4: Format response
            formatted_response = self.format_search_results(raw_response, search_params, api_url)
            print(f" Found {formatted_response.total_records} records")
            
            # Step 5: Create display summary
            display_summary = self.create_display_summary(formatted_response)
            
            return display_summary
            
        except Exception as e:
            return f"Error processing query: {str(e)}"

    def search_species(self, user_query: str) -> str:
        """
        Full workflow for species search from natural language query.
        """
        try:
            # Step 1: Extract parameters
            species_params = self.extract_species_parameters(user_query)
            print(f" Extracted species parameters: {species_params}")

            # Step 2: Build Species API URL
            species_url = self.build_species_url(species_params)
            print(f" Species API URL: {species_url}")

            # Step 3: Execute API call
            try:
                raw_response = self.execute_species_search(species_url)
                print(" Species API call successful")
                
                # Step 4: Format response
                formatted = self.format_species_results(raw_response, species_url)
                print(" Species results formatted")
                
                # Step 5: Create summary
                summary = self.create_species_summary(formatted)
                return summary
                
            except Exception as api_error:
                print(f" Species API failed: {api_error}")
                print(" Falling back to occurrence search for species info...")
                
                # Fallback: Use occurrence search to get basic species info
                return self._fallback_species_search(species_params.name)

        except Exception as e:
            return f"Error processing species query: {str(e)}"
    
    def _fallback_species_search(self, species_name: str) -> str:
        """
        Fallback method to get species info using occurrence search
        """
        try:
            # Search for occurrences of this species
            search_params = OccurrenceSearchParams(scientificname=species_name, limit=10)
            api_url = self.build_api_url(search_params)
            
            raw_response = self.execute_search(api_url)
            
            if raw_response.get('totalRecords', 0) == 0:
                return f"No information found for '{species_name}' in the Atlas of Living Australia."
            
            # Extract basic species info from occurrence records
            occurrences = raw_response.get('occurrences', [])
            if occurrences:
                first_occ = occurrences[0]
                
                summary_lines = [
                    f"Species Information: {species_name}",
                    f"Scientific Name: {first_occ.get('scientificName', 'Not available')}",
                    f"Common Name: {first_occ.get('vernacularName', 'Not available')}",
                    f"Kingdom: {first_occ.get('kingdom', 'Not available')}",
                    f"Phylum: {first_occ.get('phylum', 'Not available')}",
                    f"Class: {first_occ.get('class', 'Not available')}",
                    f"Order:{first_occ.get('order', 'Not available')}",
                    f"Family: {first_occ.get('family', 'Not available')}",
                    f"Genus:{first_occ.get('genus', 'Not available')}",
                    f"",
                    f"Total Records Found:{raw_response.get('totalRecords', 0)}",
                    f"",
                    f"Note: This information was retrieved from occurrence records as the species API requires authentication.",
                    f"Query URL: {api_url}"
                ]
                
                return "\n".join(summary_lines)
            
            return f"Found {raw_response.get('totalRecords', 0)} records but couldn't extract species details."
            
        except Exception as e:
            return f"Error in fallback species search: {str(e)}"

    def create_species_summary(self, response: SpeciesResponse) -> str:
        """
        Create a user-friendly summary of species results.
        """
        lines = [
            f"# Species Profile: {response.scientific_name or 'Unknown'}",
            f"**LSID:** {response.lsid or 'Not available'}",
            f"**Common Names:** {', '.join(response.common_names) if response.common_names else 'None recorded'}"
        ]
        
        if response.conservation_status:
            lines.append(f"**Conservation Status:** {response.conservation_status}")
        
        if response.taxonomy:
            lines.append("\n## Taxonomic Classification:")
            for rank, name in response.taxonomy.items():
                lines.append(f"- **{rank.capitalize()}:** {name}")
        
        if response.images:
            lines.append("\n## Images:")
            for img in response.images[:3]:
                lines.append(f"![Species Image]({img})")
        
        if response.data_resources:
            lines.append("\n## Data Sources:")
            lines.extend([f"- {src}" for src in response.data_resources[:5]])
        
        lines.append(f"\n*Query URL:* {response.query_url}")
        return "\n".join(lines)


# Maintain backward compatibility with original interface
def main():
    """Multi-command CLI for ALA agent"""
    parser = argparse.ArgumentParser(
        description="Atlas of Living Australia CLI: occurrence and species search"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Occurrence search subcommand
    parser_occ = subparsers.add_parser(
        "occurrences", help="Search for occurrence records"
    )
    parser_occ.add_argument(
        "query", type=str, help="Natural language query for occurrence search"
    )

    # Species search subcommand
    parser_species = subparsers.add_parser(
        "species", help="Search for species profile"
    )
    parser_species.add_argument(
        "query", type=str, help="Natural language query for species search"
    )

    args = parser.parse_args()

    ala = ALA()

    if args.command == "occurrences":
        result = ala.search_occurrences(args.query)
        print("\n" + "=" * 30)
        print("OCCURRENCE RESULTS:")
        print("=" * 30)
        print(result)
    elif args.command == "species":
        result = ala.search_species(args.query)
        print("\n" + "=" * 30)
        print("SPECIES PROFILE:")
        print("=" * 30)
        print(result)

if __name__ == "__main__":
    main()