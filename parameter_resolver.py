# parameter_resolver.py
from functools import cache
from typing import Optional, Dict
from parameter_extractor import ALASearchResponse


class ALAParameterResolver:
    """
    Resolves scientific/common names & LSIDs using ALA's Name Matching API.
    Also fills unresolved parameters in ALASearchResponse.
    """

    def __init__(self, ala_logic):
        self.ala_logic = ala_logic
        # Create cached versions of the logic methods
        self._cached_scientific_search = cache(self._search_scientific_wrapper)
        self._cached_vernacular_search = cache(self._search_vernacular_wrapper)

    # -----------------------------
    # Cached API Wrappers
    # -----------------------------
    def _search_scientific_wrapper(self, name: str):
        """Wrapper for caching scientific name searches"""
        try:
            from ala_logic import NameMatchingSearchParams
            print(f"[Resolver DEBUG] Creating NameMatchingSearchParams for: {name}")
            params = NameMatchingSearchParams(q=name)
            print(f"[Resolver DEBUG] Calling ala_logic.search_scientific_name")
            result = self.ala_logic.search_scientific_name(params)
            # print(f"[Resolver DEBUG] Result: {result}")
            return result
        except Exception as e:
            print(f"[Resolver DEBUG] Exception in _search_scientific_wrapper: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _search_vernacular_wrapper(self, name: str):
        """Wrapper for caching vernacular name searches"""
        try:
            from ala_logic import VernacularNameSearchParams
            print(f"[Resolver DEBUG] Creating VernacularNameSearchParams for: {name}")
            params = VernacularNameSearchParams(vernacularName=name)
            print(f"[Resolver DEBUG] Calling ala_logic.search_vernacular_name")
            result = self.ala_logic.search_vernacular_name(params)
            # print(f"[Resolver DEBUG] Result: {result}")
            return result
        except Exception as e:
            print(f"[Resolver DEBUG] Exception in _search_vernacular_wrapper: {e}")
            import traceback
            traceback.print_exc()
            raise

    # -----------------------------
    # LSID Detection
    # -----------------------------
    def _is_lsid(self, value: str) -> bool:
        """Check if a string is already an LSID URL."""
        if not isinstance(value, str):
            return False
        return (
            value.startswith("https://biodiversity.org.au/afd/taxa/") or
            value.startswith("https://id.biodiversity.org.au/taxon/") or
            value.startswith("https://biodiversity.org.au/apni/")
        )

    # -----------------------------
    # Name Resolution Helpers
    # -----------------------------
    def resolve_scientific_name(self, name: str) -> Optional[Dict]:
        """Resolve scientific names using /search (cached)."""
        try:
            data = self._cached_scientific_search(name)

            if not (data and data.get("success")):
                return None

            return self._extract_resolution_fields(data, name)

        except Exception as e:
            print(f"[Resolver] Scientific name resolution failed for '{name}': {e}")
            return None

    def resolve_common_name(self, name: str) -> Optional[Dict]:
        """Resolve common names using /searchByVernacularName (cached)."""
        try:
            data = self._cached_vernacular_search(name)

            if not (data and data.get("success")):
                return None

            return self._extract_resolution_fields(data, name)

        except Exception as e:
            print(f"[Resolver] Common name resolution failed for '{name}': {e}")
            return None

    def _extract_resolution_fields(self, data, original_name):
        """Extract fields from name matching API response."""
        return {
            "scientific_name": data.get("scientificName"),
            "lsid": data.get("taxonConceptID"),
            "original_name": original_name,
            "rank": data.get("rank"),
            "match_type": data.get("matchType"),
            "name_type": data.get("nameType"),
            "vernacular_name": data.get("vernacularName"),
            "kingdom": data.get("kingdom"),
            "family": data.get("family"),
            "genus": data.get("genus"),
            "species": data.get("species"),
        }

    # -----------------------------
    # Smart Name Resolution
    # -----------------------------
    def resolve_species_name(self, name: str) -> Optional[Dict]:
        # SPECIAL CASE: If it's already an LSID, return it directly
        if self._is_lsid(name):
            print(f"[Resolver] Input is already an LSID: {name}")
            return {
                "scientific_name": None,
                "lsid": name,
                "original_name": name,
                "rank": None,
                "match_type": "directLSID",
                "name_type": "LSID",
                "vernacular_name": None,
                "kingdom": None,
                "family": None,
                "genus": None,
                "species": None,
            }
        
        # Try scientific name endpoint (cached)
        sci = self.resolve_scientific_name(name)
        if sci:  # ← Remove the complex filter, just check if we got a result
            print(f"[Resolver] Resolved '{name}' via scientific search")
            return sci

        # Try common name endpoint (cached)
        common = self.resolve_common_name(name)
        if common:
            print(f"[Resolver] Resolved '{name}' via common name search")
            return common

        print(f"[Resolver] Could not resolve '{name}'")
        return None
  
    # -----------------------------
    # Resolve extracted response
    # -----------------------------
    async def resolve_unresolved_params(self, extracted_response: ALASearchResponse) -> ALASearchResponse:
        """
        Auto resolves:
        - unresolved scientific_name
        - LSID for species queries
        - enrichment metadata
        """

        params = extracted_response.params

        # -----------------------------
        # STEP 1: Resolve explicit unresolved params
        # -----------------------------
        if extracted_response.unresolved_params:
            for param in list(extracted_response.unresolved_params):
                if param == "scientific_name" and "q" in params:
                    resolved = self.resolve_species_name(params["q"])
                    if resolved:
                        # Update scientific_name only if not present AND it was resolved
                        if "scientific_name" not in params and resolved.get("scientific_name"):
                            params["scientific_name"] = resolved.get("scientific_name")
                        
                        # Always update LSID and ID
                        params["lsid"] = resolved.get("lsid")
                        params["id"] = resolved.get("lsid")
                        
                        # Remove from unresolved
                        extracted_response.unresolved_params.remove(param)

        # -----------------------------
        # STEP 2: Always try LSID resolution if missing
        # -----------------------------
        if not params.get("lsid"):
            species_identifier = self._pick_species_identifier(params)

            if species_identifier:
                print(f"[Resolver] Attempting LSID resolution for: {species_identifier}")
                resolved = self.resolve_species_name(species_identifier)

                if resolved:
                    lsid = resolved.get('lsid')
                    sci_name = resolved.get('scientific_name')
                    
                    # Log what we got
                    if sci_name:
                        print(f"[Resolver] Resolved: {sci_name} LSID={lsid}")
                    else:
                        print(f"[Resolver] Using direct LSID: {lsid}")

                    # Update scientific_name only if not present AND it was resolved
                    if "scientific_name" not in params and sci_name:
                        params["scientific_name"] = sci_name
                    
                    # Always update LSID and ID (critical for tools)
                    params["lsid"] = lsid
                    params["id"] = lsid

                    # Optional metadata (only if available)
                    self._add_extra_metadata(params, resolved)

                else:
                    print(f"[Resolver] ✗ Failed to resolve LSID for: {species_identifier}")

        # -----------------------------
        # Final: update flags
        # -----------------------------
        extracted_response.clarification_needed = len(extracted_response.unresolved_params) > 0
        if not extracted_response.clarification_needed:
            extracted_response.clarification_reason = ""

        return extracted_response

    # -----------------------------
    # Helper utilities
    # -----------------------------
    def _pick_species_identifier(self, params):
        """Pick best identifier to resolve LSID."""
        keys = ["q", "id", "scientific_name", "species_name", "common_name"]
        for key in keys:
            if key in params:
                value = params[key]
                return value[0] if isinstance(value, list) else value
        return None

    def _add_extra_metadata(self, params, resolved):
        """Attach extra info (vernacular, rank, family, etc.) only if not already present."""
        if resolved.get("vernacular_name") and "common_name" not in params:
            params["common_name"] = resolved["vernacular_name"]
        if resolved.get("rank") and "rank" not in params:
            params["rank"] = resolved["rank"]
        if resolved.get("family") and "family" not in params:
            params["family"] = resolved["family"]