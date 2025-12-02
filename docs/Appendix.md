# Appendix

This appendix summarizes key configuration, dependencies, and terminology used in the ALA iChatBio Agent.

## Environment Variables

The agent relies on a small set of environment variables, typically configured in an `env.yaml` file:

- `OPENAI_API_KEY`  
  - Required.  
  - OpenAI API key used for LLM-based parameter extraction, resolution, and planning.

- `OPENAI_BASE_URL`  
  - Optional.  
  - Base URL for the OpenAI API or compatible proxy.  
  - Default: `https://api.openai.com`

- `ALA_API_BASE_URL`  
  - Optional.  
  - Base URL for the Atlas of Living Australia APIs.  
  - Default: `https://api.ala.org.au`

These variables are read at startup and should be kept out of version control when they contain secrets.

## Key Dependencies

Core dependencies (exact versions may be pinned in `requirements.txt`):

- `python` 3.11  
- `pydantic` 2.x  
- `openai` 1.x  
- `instructor` (for structured LLM outputs)  
- `aiohttp` 3.x (async HTTP client)  
- `ichatbio` (iChatBio framework library)

Additional tooling and testing libraries can be added as needed (for example, `pytest` for automated tests).

## Glossary

- **LSID (Life Science Identifier)**  
  A globally unique identifier for taxonomic concepts (e.g., species) used to unambiguously refer to taxa across systems.

- **AFD (Australian Faunal Directory)**  
  A national database of Australian fauna; many LSIDs and taxonomic concepts referenced by ALA come from AFD.

- **APNI (Australian Plant Name Index)**  
  A comprehensive index of Australian plant names; plant-related taxon records in ALA often link back to APNI.

- **BIE (Biodiversity Information Explorer)**  
  ALA’s biodiversity information portal that aggregates species-level information such as profiles, images, and distributions.

- **Facet**  
  A categorical field used for grouping and counting records (for example, `state`, `year`, `species`, `family`, `basisOfRecord`, `institutionCode`).

- **`fq` (Filter Query)**  
  ALA’s filter syntax used to restrict occurrence and taxa queries by fields such as state, year, basis of record, and more (e.g., `state:Queensland`, `year:2020`).

## Versioning and Metadata

- **Last Updated:** 01-12-2025  
- **Documentation Version:** 1.0  
- **Author:** Anisa Shaik

Update this appendix when adding new environment variables, dependencies, or domain-specific terminology to keep the documentation aligned with the codebase.