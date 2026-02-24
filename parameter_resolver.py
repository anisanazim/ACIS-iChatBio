# ala_parameter_resolver.py

from typing import Optional, Dict, Any
from parameter_extractor import ALASearchResponse
from ala_logic import NameMatchingSearchParams
import json
import logging

logger = logging.getLogger(__name__)


class ALAParameterResolver:
    """
    Redis-backed species resolver for ALA.

    Responsibilities:
    - Given an ALASearchResponse that needs LSID, resolve species name → LSID + metadata.
    - Use Redis as a species knowledge base (full ALA responses cached).
    - Avoid unnecessary ALA API calls by checking Redis first.
    """

    def __init__(self, ala_logic, redis_client):
        """
        ala_logic: object exposing:
            - async search_scientific_name(name: str) -> dict
            - async search_vernacular_name(name: str) -> dict

        redis_client: aioredis-like client with get/set and (optionally) FT.SEARCH support.
        """
        self.ala_logic = ala_logic
        self.redis = redis_client

    # -------------------------------------------------------------------------
    # Basic Redis helpers
    # -------------------------------------------------------------------------

    async def _redis_get(self, key: str) -> Optional[Dict[str, Any]]:
        raw = await self.redis.get(key)
        if not raw:
            logger.warning(f"Cache MISS: {key}")
            return None
        logger.warning(f"Cache HIT: {key}")
        return json.loads(raw)

    async def _redis_set(self, key: str, value: Dict[str, Any]):
        logger.warning(f"💾 Storing in cache: {key}")
        await self.redis.set(key, json.dumps(value))

    # -------------------------------------------------------------------------
    # Key helpers
    # -------------------------------------------------------------------------

    def _key_scientific(self, name: str) -> str:
        return f"scientific:{name.lower()}"

    def _key_vernacular(self, name: str) -> str:
        return f"vernacular:{name.lower()}"

    def _key_synonym(self, name: str) -> str:
        return f"synonym:{name.lower()}"

    def _key_lsid(self, lsid: str) -> str:
        return f"lsid:{lsid}"

    def _key_no_match(self, name: str) -> str:
        return f"noMatch:{name.lower()}"

    # -------------------------------------------------------------------------
    # LSID detection
    # -------------------------------------------------------------------------

    def _is_lsid(self, value: str) -> bool:
        if not isinstance(value, str):
            return False
        return (
            value.startswith("https://biodiversity.org.au/afd/taxa/")
            or value.startswith("https://id.biodiversity.org.au/taxon/")
            or value.startswith("https://biodiversity.org.au/apni/")
        )

    # -------------------------------------------------------------------------
    # Store full ALA response in Redis under multiple keys
    # -------------------------------------------------------------------------

    async def _store_full_response(self, original_name: str, data: Dict[str, Any]):
        """
        Store the full ALA name-matching response under multiple lookup keys.
        """
        logger.warning(f"📦 Storing full ALA response for: {original_name}")
        # Always store under the original query name (scientific bucket)
        await self._redis_set(self._key_scientific(original_name), data)

        sci_name = data.get("scientificName")
        vernacular = data.get("vernacularName")
        lsid = data.get("taxonConceptID")

        # Canonical scientific name
        if sci_name:
            await self._redis_set(self._key_scientific(sci_name), data)

        # Vernacular name
        if vernacular:
            await self._redis_set(self._key_vernacular(vernacular), data)

        # Synonym mapping (if synonymType present)
        synonym_type = data.get("synonymType")
        if synonym_type and original_name.lower() != (sci_name or "").lower():
            # original_name is a synonym of sci_name
            await self._redis_set(self._key_synonym(original_name), data)

        # LSID mapping
        if lsid:
            await self._redis_set(self._key_lsid(lsid), data)

    # -------------------------------------------------------------------------
    # Optional: fuzzy / prefix lookup hooks (you can implement with RedisSearch)
    # -------------------------------------------------------------------------

    async def _redis_fuzzy_lookup(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Placeholder for fuzzy lookup using RedisSearch (FT.SEARCH).
        For now, return None; you can implement later if needed.
        """
        return None

    async def _redis_prefix_lookup(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Placeholder for prefix lookup using RedisSearch.
        For now, return None; you can implement later if needed.
        """
        return None

    # -------------------------------------------------------------------------
    # Main species resolution entrypoint (name → full ALA record)
    # -------------------------------------------------------------------------

    async def _resolve_via_redis_only(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Try to resolve using Redis only (no external API calls).
        Order:
        - LSID
        - exact scientific
        - exact vernacular
        - synonym
        - fuzzy
        - prefix
        - negative cache
        """
        logger.warning(f"🔍 c: {name}")
        # Direct LSID
        if self._is_lsid(name):
            cached = await self._redis_get(self._key_lsid(name))
            if cached:
                return cached

        # Exact scientific
        cached = await self._redis_get(self._key_scientific(name))
        if cached:
            return cached

        # Exact vernacular
        cached = await self._redis_get(self._key_vernacular(name))
        if cached:
            return cached

        # Synonym
        cached = await self._redis_get(self._key_synonym(name))
        if cached:
            return cached

        # Fuzzy
        fuzzy = await self._redis_fuzzy_lookup(name)
        if fuzzy:
            return fuzzy

        # Prefix
        prefix = await self._redis_prefix_lookup(name)
        if prefix:
            return prefix

        # Negative cache
        no_match = await self._redis_get(self._key_no_match(name))
        if no_match:
            return None

        return None

    async def resolve_species_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Resolve a species name (or LSID, or common name) to a full ALA record.
        Uses Redis first, then falls back to ALA APIs (scientific + vernacular).
        Deterministic, metadata-driven.
        """

        # 1. Try Redis-only resolution
        cached = await self._resolve_via_redis_only(name)
        if cached:
            logger.warning(f"CACHE HIT: Resolved '{name}' from Redis")
            return cached

        # 2. LSID passthrough
        if self._is_lsid(name):
            logger.warning(f"LSID not cached, returning minimal record: {name}")
            return {
                "scientificName": None,
                "taxonConceptID": name,
                "rank": None,
                "vernacularName": None,
                "issues": ["noIssue"],
            }

        # -------------------------------
        # 3. Call BOTH ALA endpoints
        # -------------------------------

        logger.warning(f"⚠️ CACHE MISS: Calling ALA scientific name API for '{name}'")
        sci_params = NameMatchingSearchParams(q=name)
        sci_data = await self.ala_logic.search_scientific_name(sci_params)

        logger.warning(f"Trying ALA vernacular name API for '{name}'")
        vern_params = NameMatchingSearchParams(q=name)
        vern_data = await self.ala_logic.search_vernacular_name(vern_params)

        # -------------------------------
        # 4. Validate responses
        # -------------------------------

        def is_valid_vernacular(d):
            if not d or not d.get("success"):
                return False
            return (
                d.get("matchType") == "vernacularMatch"
                and d.get("nameType") in ["INFORMAL", "COMMON"]
            )

        def is_valid_scientific(d):
            if not d or not d.get("success"):
                return False
            if d.get("nameType") != "SCIENTIFIC":
                return False
            # Accept only SAFE match types
            return d.get("matchType") in [
                "exactMatch",
                "phraseMatch",
                "taxonIdMatch",
            ]

        vern_ok = is_valid_vernacular(vern_data)
        sci_ok = is_valid_scientific(sci_data)

        # -------------------------------
        # 5. Deterministic priority rule
        # -------------------------------

        # 1️⃣ Prefer vernacular (strict, safe)
        if vern_ok:
            logger.warning(f"ALA API SUCCESS: Vernacular match for '{name}'")
            await self._store_full_response(name, vern_data)
            return vern_data

        # 2️⃣ Fall back to scientific (only exact/phrase/taxonId)
        if sci_ok:
            logger.warning(f"ALA API SUCCESS: Scientific match for '{name}'")
            await self._store_full_response(name, sci_data)
            return sci_data

        # -------------------------------
        # 6. No valid match → negative cache
        # -------------------------------

        logger.warning(f"NO MATCH: Species '{name}' not found in ALA - caching negative result")
        await self._redis_set(self._key_no_match(name), {"noMatch": True})
        return None

    # -------------------------------------------------------------------------
    # Pick best species identifier from params
    # -------------------------------------------------------------------------

    def _pick_species_identifier(self, params: Dict[str, Any]) -> Optional[str]:
        keys = ["scientific_name", "species_name", "common_name", "q", "id"]
        for key in keys:
            if key in params:
                value = params[key]
                return value[0] if isinstance(value, list) else value
        return None

    # -------------------------------------------------------------------------
    # Attach extra metadata to params
    # -------------------------------------------------------------------------

    def _add_extra_metadata(self, params: Dict[str, Any], data: Dict[str, Any]):
        """
        Attach useful metadata from the full ALA record into params.
        """
        mapping = {
            "vernacularName": "common_name",
            "rank": "rank",
            "family": "family",
            "genus": "genus",
            "species": "species",
            "kingdom": "kingdom",
        }
        for src, dst in mapping.items():
            if data.get(src) and dst not in params:
                params[dst] = data[src]

    # -------------------------------------------------------------------------
    # MAIN PUBLIC METHOD — called only when LSID is required
    # -------------------------------------------------------------------------

    async def resolve_unresolved_params(self, extracted: ALASearchResponse) -> ALASearchResponse:
        """
        Given an ALASearchResponse whose selected tool requires LSID,
        resolve species → LSID + scientific_name + metadata using Redis + ALA.
        """
        params = extracted.params

        # Already has LSID → nothing to do
        if params.get("lsid"):
            return extracted

        # Pick identifier
        species_identifier = self._pick_species_identifier(params)
        if not species_identifier:
            extracted.clarification_needed = True
            extracted.clarification_reason = (
                "I need a species name or LSID to proceed with this operation."
            )
            return extracted

        # Resolve via Redis + ALA
        record = await self.resolve_species_name(species_identifier)
        if not record:
            extracted.clarification_needed = True
            extracted.clarification_reason = (
                f"I couldn't identify the species '{species_identifier}'. "
                "Please provide a more complete scientific name, a clearer common name, "
                "or the exact LSID if available."
            )
            return extracted

        # Extract core fields
        lsid = record.get("taxonConceptID")
        sci_name = record.get("scientificName")

        if sci_name and "scientific_name" not in params:
            params["scientific_name"] = sci_name

        if lsid:
            params["lsid"] = lsid
            params["id"] = lsid

        # Attach metadata (family, genus, vernacular, etc.)
        self._add_extra_metadata(params, record)

        extracted.clarification_needed = False
        extracted.clarification_reason = ""
        return extracted