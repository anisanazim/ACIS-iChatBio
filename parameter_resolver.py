# parameter_resolver.py
import requests
from functools import cache
from typing import Optional, Dict
from ala_logic import ALASearchResponse

class ALAParameterResolver:
    def __init__(self, ala_api_base_url):
        self.ala_api_base_url = ala_api_base_url
    
    @cache
    def resolve_scientific_name(self, common_name: str) -> Optional[Dict]:
        """Resolve common name to scientific name using ALA name matching"""
        try:
            url = f"{self.ala_api_base_url}/species/search"
            params = {"q": common_name, "pageSize": 5}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = data.get('searchResults', {}).get('results', [])
            if results:
                best_match = results[0]
                return {
                    "scientific_name": best_match.get('name'),
                    "common_name": best_match.get('commonNameSingle'),
                    "lsid": best_match.get('guid'),
                    "rank": best_match.get('rank')
                }
        except Exception as e:
            print(f"Name resolution failed for {common_name}: {e}")
        return None
    
    async def resolve_unresolved_params(self, extracted_response: ALASearchResponse) -> ALASearchResponse:
        """Resolve any unresolved parameters automatically"""
        if not extracted_response.unresolved_params:
            return extracted_response
        
        for param in extracted_response.unresolved_params.copy():
            if param == "scientific_name" and "q" in extracted_response.params:
                common_name = extracted_response.params["q"]
                resolution = self.resolve_scientific_name(common_name)
                if resolution:
                    extracted_response.params["scientific_name"] = resolution["scientific_name"]
                    extracted_response.params["lsid"] = resolution.get("lsid")
                    extracted_response.unresolved_params.remove(param)
        
        # Update clarification status
        extracted_response.clarification_needed = len(extracted_response.unresolved_params) > 0
        if not extracted_response.clarification_needed:
            extracted_response.clarification_reason = ""
        
        return extracted_response