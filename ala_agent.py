import os
import yaml
from pydantic import BaseModel, field_validator, ValidationError
from datetime import datetime
import requests
from openai import OpenAI
import json
from typing import Optional
from urllib.parse import urlencode

class OccurrenceApi(BaseModel):
    """Pydantic model for ALA API parameters validation"""
    scientificname: Optional[str] = None
    taxonid: Optional[str] = None
    kingdom: Optional[str] = None
    phylum: Optional[str] = None
    class_name: Optional[str] = None
    order: Optional[str] = None
    family: Optional[str] = None
    genus: Optional[str] = None
    species: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    locality: Optional[str] = None
    year: Optional[str] = None
    month: Optional[str] = None
    startdate: Optional[str] = None
    enddate: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    radius: Optional[float] = None
    has_images: Optional[bool] = None
    has_coordinates: Optional[bool] = None
    institution_code: Optional[str] = None
    collection_code: Optional[str] = None
    basis_of_record: Optional[str] = None
    limit: Optional[int] = 20
    offset: Optional[int] = 0

    @field_validator('startdate', 'enddate')
    @classmethod
    def validate_date_format(cls, value):
        if value is None:
            return value
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return value
        except ValueError:
            raise ValueError("Incorrect date format, should be YYYY-MM-DD")

    @field_validator('limit')
    @classmethod
    def validate_limit(cls, value):
        if value is not None and (value < 1 or value > 1000):
            raise ValueError("Limit must be between 1 and 1000")
        return value

class ALA:
    """Atlas of Living Australia API client"""
    
    def __init__(self):
        self.api_key = self.getValue("OPENAI_API_KEY")
        self.ala_url = self.getValue("ALA_URL", "https://biocache.ala.org.au/ws/occurrences")
        self.prompt = ""
        self.payload = ""
        self.error = ""
        self.response_data = None

    def build_prompt(self, user_input):
        """Build the prompt for OpenAI to extract ALA API parameters"""
        if user_input is None or len(user_input) == 0:
            return
        
        self.prompt = f"""
            You are an assistant that generates query parameters for the Atlas of Living Australia (ALA) API's `/occurrence/search` endpoint.
            Given a natural language request, extract the relevant parameters and return a valid Python dictionary.
            
            The natural language input is: {user_input}
            
            Supported parameters:
            - `scientificname`: full scientific name (e.g., "Phascolarctos cinereus" for koala)
            - `taxonid`: Taxon concept ID from ALA
            - `kingdom`: taxonomic kingdom (e.g., "Animalia", "Plantae")
            - `phylum`: taxonomic phylum (e.g., "Chordata", "Arthropoda")
            - `class_name`: taxonomic class (e.g., "Mammalia", "Aves") - use 'class_name' not 'class'
            - `order`: taxonomic order (e.g., "Primates", "Carnivora")
            - `family`: taxonomic family (e.g., "Phascolarctidae", "Macropodidae")
            - `genus`: taxonomic genus (e.g., "Phascolarctos", "Macropus")
            - `species`: species name only (e.g., "cinereus", "rufus")
            - `country`: country name (e.g., "Australia")
            - `state`: Australian state/territory (e.g., "Queensland", "New South Wales", "Victoria", "Tasmania", "Western Australia", "South Australia", "Northern Territory", "Australian Capital Territory")
            - `locality`: specific locality or place name
            - `year`: specific year or year range (e.g., "2020" or "2018-2022")
            - `month`: month number (1-12) or range
            - `startdate`: start date in YYYY-MM-DD format
            - `enddate`: end date in YYYY-MM-DD format
            - `lat`: latitude for geographic search (decimal degrees)
            - `lon`: longitude for geographic search (decimal degrees)
            - `radius`: search radius in kilometers (when using lat/lon)
            - `has_images`: true if user wants records with images
            - `has_coordinates`: true if user wants records with GPS coordinates
            - `institution_code`: institution that holds the specimen
            - `collection_code`: collection within the institution
            - `basis_of_record`: type of record (e.g., "PreservedSpecimen", "HumanObservation", "MachineObservation")
            - `limit`: maximum number of results to return (default 20, max 1000)
            - `offset`: number of results to skip (for pagination)
            
            Important notes:
            - Australia-focused: Prefer Australian locations and native species
            - For common names, convert to scientific names when possible
            - If location is mentioned without specifying Australia, assume Australian context
            - Use appropriate taxonomic hierarchy
            - Set reasonable limits (20-100 for general searches)
            
            Return only the Python dictionary, no explanations or additional text.
        """

    def getApiPayload(self):
        """Get API payload using OpenAI to parse the user prompt"""
        if len(self.prompt) == 0:
            return
        
        try:
            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": self.prompt}],
                temperature=0
            )
            
            self.payload = response.choices[0].message.content.strip()
            
            # Clean up the response to ensure it's valid JSON
            if self.payload.startswith("```python"):
                self.payload = self.payload[9:]
            if self.payload.startswith("```"):
                self.payload = self.payload[3:]
            if self.payload.endswith("```"):
                self.payload = self.payload[:-3]
            
            self.payload = self.payload.strip()
            
        except Exception as e:
            self.error = f"Error getting API payload: {str(e)}"
            print(self.error)

    def verify_payload(self):
        """Verify the payload using Pydantic validation"""
        try:
            # Parse the JSON string first
            params_dict = json.loads(self.payload)
            
            # Validate using Pydantic model
            validated_params = OccurrenceApi.model_validate(params_dict)
            print(validated_params)
            return True
            
        except json.JSONDecodeError as e:
            self.error = f"JSON decode error: {str(e)}"
            print(f"Error: {self.error}")
            print(f"Payload: {self.payload}")
            return False
            
        except ValidationError as e:
            self.error = f"Validation error: {str(e)}"
            print(f"Error: {self.error}")
            return False

    def extract_params_dict(self):
        """Extract parameters and convert to URL encoding"""
        if len(self.payload) == 0:
            return
        
        try:
            data = json.loads(self.payload)
            
            # Remove None values and convert special fields for biocache API
            clean_data = {}
            for key, value in data.items():
                if value is not None:
                    # Handle special field mappings for ALA biocache API
                    if key == "class_name":
                        clean_data["class"] = value
                    elif key == "scientificname":
                        # Use 'taxa' parameter for scientific name search (based on ALA examples)
                        clean_data["taxa"] = value
                    elif key == "has_images":
                        # Add filter for multimedia records
                        if value:
                            clean_data["fq"] = "multimedia:Image"
                    elif key == "has_coordinates":
                        # Add filter for georeferenced records
                        if value:
                            if "fq" in clean_data:
                                clean_data["fq"] += " AND geospatial_kosher:true"
                            else:
                                clean_data["fq"] = "geospatial_kosher:true"
                    elif key == "state":
                        # Add as filter query - try common field names
                        state_filter = f"state:{value}"
                        if "fq" in clean_data:
                            clean_data["fq"] += f" AND {state_filter}"
                        else:
                            clean_data["fq"] = state_filter
                    elif key == "country":
                        # Add as filter query
                        country_filter = f"country:{value}"
                        if "fq" in clean_data:
                            clean_data["fq"] += f" AND {country_filter}"
                        else:
                            clean_data["fq"] = country_filter
                    else:
                        clean_data[key] = value
            
            # Remove None values after processing
            clean_data = {k: v for k, v in clean_data.items() if v is not None}
            
            self.payload = urlencode(clean_data)
            
        except json.JSONDecodeError as e:
            self.error = f"Error parsing JSON: {str(e)}"
            print(self.error)

    def query_ala_api(self):
        """Query the ALA API and return results"""
        if not self.payload:
            print("No payload to query with")
            return None
            
        url = f"{self.ala_url}/search?{self.payload}"
        print(f"Querying ALA API: {url}")
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                self.response_data = response.json()
                return self.response_data
            else:
                error_msg = f"ALA API error {response.status_code}: {response.text}"
                print(error_msg)
                self.error = error_msg
                return None
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error: {str(e)}"
            print(error_msg)
            self.error = error_msg
            return None

    def format_results(self):
        """Format the API results for display"""
        if not self.response_data:
            return "No data to format"
        
        try:
            total_records = self.response_data.get('totalRecords', 0)
            occurrences = self.response_data.get('occurrences', [])
            
            if total_records == 0:
                return "No occurrences found in Atlas of Living Australia for your query."
            
            result = f"Found {total_records} total records in Atlas of Living Australia.\n"
            result += f"Showing {len(occurrences)} results:\n\n"
            
            for i, occ in enumerate(occurrences[:5], 1):  # Show first 5
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
                
                result += f"{i}. {name} - {location_str}{coord_str}{date_str}\n"
            
            if len(occurrences) < total_records:
                result += f"\n... and {total_records - len(occurrences)} more records available.\n"
            
            return result
            
        except Exception as e:
            return f"Error formatting results: {str(e)}"

    def getValue(self, key, default=None):
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

    def getPayload(self):
        """Get the current payload"""
        return self.payload

    def getApiKey(self):
        """Get the API key"""
        return self.api_key

    def getError(self):
        """Get any error messages"""
        return self.error

if __name__ == "__main__":
    ala = ALA()
    userInput = input("Enter Search Query: \n")
    ala.build_prompt(user_input=userInput)
    ala.getApiPayload()
    ala.verify_payload()
    print(ala.getPayload())
    ala.extract_params_dict()
    result = ala.query_ala_api()
    if result:
        print(ala.format_results())