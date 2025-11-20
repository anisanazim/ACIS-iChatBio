# parameter_resolver.py
import requests
from functools import cache
from typing import Optional, Dict
from parameter_extractor import ALASearchResponse


class ALAParameterResolver:
    def __init__(self, ala_api_base_url):
        self.ala_api_base_url = ala_api_base_url

    @cache
    def resolve_scientific_name(self, name: str) -> Optional[Dict]:
        """
        Resolve a common or scientific name to canonical scientific name and identifiers 
        using ALA's species/guid endpoint.
        """
        try:
            url = f"{self.ala_api_base_url}/species/guid/{name}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data:
                # Choose the first entry (primary match)
                primary = data[0] if isinstance(data, list) else data
                return {
                    "scientific_name": primary.get("acceptedName") or primary.get("scientificName"),
                    "lsid": primary.get("acceptedIdentifier") or primary.get("guid"),
                    "original_name": primary.get("name")
                }
        except Exception as e:
            print(f"Name resolution failed for {name}: {e}")
        return None

    async def resolve_unresolved_params(self, extracted_response: ALASearchResponse) -> ALASearchResponse:
        """
        Resolve unresolved parameters automatically using the authoritative GUID endpoint.
        
        This method:
        1. Resolves explicitly unresolved parameters (like scientific_name)
        2. ALWAYS attempts LSID resolution for species queries (for distribution/image tools)
        """
        
        # Step 1: Handle explicitly unresolved params first
        if extracted_response.unresolved_params:
            for param in extracted_response.unresolved_params.copy():
                if param == "scientific_name" and "q" in extracted_response.params:
                    query_name = extracted_response.params["q"]
                    resolution = self.resolve_scientific_name(query_name)
                    if resolution:
                        extracted_response.params["scientific_name"] = resolution["scientific_name"]
                        extracted_response.params["lsid"] = resolution.get("lsid")
                        extracted_response.unresolved_params.remove(param)

        # Step 2: ALWAYS try to resolve LSID if we have a species query and no LSID yet
        # This is critical for tools like get_species_distribution and get_species_images
        if "lsid" not in extracted_response.params or extracted_response.params["lsid"] is None:
            # Try to get species identifier from various fields
            species_identifier = None
            
            # Priority order for finding species name to resolve
            if "q" in extracted_response.params:
                species_identifier = extracted_response.params["q"]
            elif "scientific_name" in extracted_response.params:
                sci_name = extracted_response.params["scientific_name"]
                species_identifier = sci_name[0] if isinstance(sci_name, list) else sci_name
            elif "species_name" in extracted_response.params:
                sp_name = extracted_response.params["species_name"]
                species_identifier = sp_name[0] if isinstance(sp_name, list) else sp_name
            elif "common_name" in extracted_response.params:
                common = extracted_response.params["common_name"]
                species_identifier = common[0] if isinstance(common, list) else common
            
            # Attempt resolution if we found a species identifier
            if species_identifier:
                resolution = self.resolve_scientific_name(species_identifier)
                if resolution:
                    # Only update if not already present
                    if "scientific_name" not in extracted_response.params:
                        extracted_response.params["scientific_name"] = resolution["scientific_name"]
                    extracted_response.params["lsid"] = resolution.get("lsid")
                    extracted_response.params["id"] = resolution.get("lsid")  # Also set 'id' for image search

        # Step 3: Update clarification status
        extracted_response.clarification_needed = len(extracted_response.unresolved_params) > 0
        if not extracted_response.clarification_needed:
            extracted_response.clarification_reason = ""

        return extracted_response