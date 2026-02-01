# parameter_resolver.py
from functools import lru_cache
from typing import Optional, Dict
from parameter_extractor import ALASearchResponse


# Manual cache dictionaries for explicit cache tracking
_scientific_name_cache = {}
_vernacular_name_cache = {}


# Module-level cache for name resolution (keyed by name only, ala_logic assumed singleton)
def _cached_scientific_search_global(name: str):
    """Global cached wrapper for scientific name searches with explicit cache tracking"""
    # Check if in manual cache first
    if name in _scientific_name_cache:
        print(f"[Resolver CACHE] HIT for scientific name: '{name}' (returning cached result)")
        return _scientific_name_cache[name]
    
    # Cache miss - call API
    try:
        print(f"[Resolver CACHE] MISS for scientific name: '{name}' (calling API)")
        from ala_logic import NameMatchingSearchParams
        params = NameMatchingSearchParams(q=name)
        result = _ala_logic_ref.search_scientific_name(params)
        # Store in cache
        _scientific_name_cache[name] = result
        print(f"[Resolver CACHE] API response cached for: '{name}'")
        return result
    except Exception as e:
        print(f"[Resolver DEBUG] Exception in scientific search: {e}")
        raise


def _cached_vernacular_search_global(name: str):
    """Global cached wrapper for vernacular name searches with explicit cache tracking"""
    # Check if in manual cache first
    if name in _vernacular_name_cache:
        print(f"[Resolver CACHE] HIT for vernacular name: '{name}' (returning cached result)")
        return _vernacular_name_cache[name]
    
    # Cache miss - call API
    try:
        print(f"[Resolver CACHE] MISS for vernacular name: '{name}' (calling API)")
        from ala_logic import VernacularNameSearchParams
        params = VernacularNameSearchParams(vernacularName=name)
        result = _ala_logic_ref.search_vernacular_name(params)
        # Store in cache
        _vernacular_name_cache[name] = result
        print(f"[Resolver CACHE] API response cached for: '{name}'")
        return result
    except Exception as e:
        print(f"[Resolver DEBUG] Exception in vernacular search: {e}")
        raise


# Global reference to ala_logic (set once during resolver init)
_ala_logic_ref = None


class ALAParameterResolver:
    """
    Resolves scientific/common names & LSIDs using ALA's Name Matching API.
    Also fills unresolved parameters in ALASearchResponse.
    """

    def __init__(self, ala_logic):
        self.ala_logic = ala_logic
        # Set the global reference for the cached functions (only once)
        global _ala_logic_ref
        if _ala_logic_ref is None:
            _ala_logic_ref = ala_logic

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
    # These use the global cached functions above
    # Cache key is just the species name (ala_logic is global singleton)
    # -----------------------------
    def resolve_scientific_name(self, name: str) -> Optional[Dict]:
        """Resolve scientific names using /search (cached globally)."""
        try:
            data = _cached_scientific_search_global(name)

            if not (data and data.get("success")):
                return None

            result = self._extract_resolution_fields(data, name)
            return result

        except Exception as e:
            print(f"[Resolver] Scientific name resolution failed for '{name}': {e}")
            return None

    def resolve_common_name(self, name: str) -> Optional[Dict]:
        """Resolve common names using /searchByVernacularName (cached globally)."""
        try:
            data = _cached_vernacular_search_global(name)

            if not (data and data.get("success")):
                return None

            result = self._extract_resolution_fields(data, name)
            return result

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
        
        # Try scientific name endpoint 
        sci = self.resolve_scientific_name(name)
        if sci:  # ← Remove the complex filter, just check if we got a result
            # The actual API call (if it happened) is logged in the cached function
            # If no [Resolver CACHE] message appeared, it was a cache hit
            return sci

        # Try common name endpoint 
        common = self.resolve_common_name(name)
        if common:
            # The actual API call (if it happened) is logged in the cached function
            # If no [Resolver CACHE] message appeared, it was a cache hit
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
                    print(f"[Resolver] Failed to resolve LSID for: {species_identifier}")
                    # Resolution failed - set clarification_needed so user can provide correct species name
                    extracted_response.clarification_needed = True
                    extracted_response.clarification_reason = (
                        f"Could not identify the species '{species_identifier}'. "
                        f"Please provide either:\n"
                        f"• A more complete species name (e.g., 'scientific name species', not just '{species_identifier}')\n"
                        f"• A different common name\n"
                        f"• The exact LSID if you have it"
                    )
                    extracted_response.unresolved_params.append(f"species_name ('{species_identifier}')")

        # -----------------------------
        # Final: update flags
        # -----------------------------
        extracted_response.clarification_needed = extracted_response.clarification_needed or len(extracted_response.unresolved_params) > 0
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