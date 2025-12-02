# API Integration

The ALA iChatBio Agent integrates with the Atlas of Living Australia (ALA) through a set of REST APIs that provide name matching, occurrence data, species information, distributions, and images. The agent’s logic layer is responsible for constructing URLs, validating parameters, executing HTTP requests, and parsing the responses.

## Base URL

All ALA endpoints are accessed via a configurable base URL:

- Base URL: `https://api.ala.org.au`

This value is typically set in configuration (for example, `ALA_API_BASE_URL` in `env.yaml`) so it can be changed or proxied without modifying code.

## Name Matching APIs

The agent uses ALA name-matching services to resolve common and scientific names into canonical scientific names and LSIDs:

- `namematching/api/search`  
  - Purpose: Resolve scientific names.  
  - Typical usage: When the user provides a scientific name or when heuristics indicate a scientific-name lookup is appropriate.

- `namematching/api/searchByVernacularName`  
  - Purpose: Resolve common (vernacular) names.  
  - Typical usage: When the user provides a common name such as “koala” or “Red Kangaroo”.

The Parameter Resolver encapsulates the logic for choosing which endpoint to call, handling retries, and caching results.

## Occurrence APIs

The occurrence endpoints provide raw records and aggregated statistics for biodiversity data:

- `occurrences/occurrences/search`  
  - Purpose: Retrieve individual occurrence records.  
  - Used by: `search_species_occurrences`.  
  - Common parameters:  
    - `q`: Species name or LSID.  
    - `fq`: Filter queries (e.g., `state:Queensland`, year filters).  
    - `pageSize`: Number of records to return (subject to a maximum cap).

- `occurrences/occurrences/facets`  
  - Purpose: Get counts grouped by facets (e.g., state, year, species).  
  - Used by: `get_occurrence_breakdown`.  
  - Common facets: `state`, `year`, `species`, `kingdom`, `family`, `basisOfRecord`, `institutionCode`.

- `occurrences/occurrences/taxaCount`  
  - Purpose: Get total counts for taxa identified by LSIDs.  
  - Used by: `get_occurrence_taxa_count`.  
  - Key parameters:  
    - `guids`: One or more LSIDs (often newline-separated or encoded as a parameter).  
    - `fq`: Optional filters (e.g., state or year constraints).

## Species and Distribution APIs

The species and distribution endpoints support profiles, taxonomy, and spatial range information:

- `species/search`  
  - Purpose: Search species information and profiles.  
  - Used by: `lookup_species_info`.  
  - Returns: Scientific names, common names, taxonomic hierarchy, and related metadata.

- `species/lsid/{lsid}`  
  - Purpose: Retrieve expert distribution and range information for a species given its LSID.  
  - Used by: `get_species_distribution`.  
  - Returns: Spatial polygons, distribution metadata, and related range data.

These endpoints rely on the Parameter Resolver to supply valid LSIDs.

## Image APIs

The image endpoint provides access to species images:

- `species/imageSearch/{id}`  
  - Purpose: Retrieve primary images and associated metadata for a species.  
  - Used by: `get_species_images`.  
  - Input: Typically an identifier derived from LSID resolution or species search results.

The agent extracts image URLs and metadata to present user-friendly image artifacts.

## Authentication and Configuration

The current integration uses public ALA endpoints and does not require an ALA-specific API key. Environment configuration typically includes:

- `ALA_API_BASE_URL`: Base URL for ALA APIs (default `https://api.ala.org.au`).  
- `OPENAI_API_KEY` and `OPENAI_BASE_URL`: For the LLM components, configured separately from ALA.

These values are stored in configuration files (such as `env.yaml`) and loaded by the application at startup.

## ALA Logic Layer Responsibilities

The ALA Logic Layer (for example, in `ala_logic.py` and `main_ala_logic.py`) centralizes API integration concerns:

- Builds endpoint-specific URLs (search, facets, taxaCount, species, distribution, images) with correct query parameter encoding.
- Validates parameters with Pydantic models before sending requests, ensuring required fields and correct types.
- Executes HTTP requests using an async client (such as `aiohttp`), with error handling and retries.
- Returns parsed JSON responses for use by tools and higher-level workflows.

This separation allows the rest of the agent (parameter extraction, planning, and tools) to work with high-level functions instead of constructing raw HTTP requests directly.