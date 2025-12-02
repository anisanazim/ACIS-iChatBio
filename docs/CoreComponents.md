# Core Components

The ALA iChatBio Agent is built from several core components that work together to turn natural-language biodiversity queries into ALA API calls and structured outputs. Each component focuses on a specific part of the workflow, from parameter extraction to API integration. 

## 1. Parameter Extractor (parameter_extractor.py)

The Parameter Extractor converts natural-language queries into structured API parameters suitable for ALA endpoints. It uses an LLM with structured output (Pydantic models) to produce an `ALASearchResponse` object that includes fields such as `q`, `fq`, temporal filters (e.g., year), unresolved parameters, and a `clarification_needed` flag. It extracts taxonomic, spatial, temporal, and facet parameters, validates temporal queries, and supports filter queries like coordinates, states, and years. The extractor is configured with a deterministic model setup (for example, GPT-4o-mini), low temperature, and a limited number of retries. 

## 2. Parameter Resolver (parameter_resolver.py)

The Parameter Resolver resolves species names into scientific names and LSIDs using the ALA Name Matching APIs. It supports two main name-matching endpoints: one for scientific names and one for vernacular (common) names, and applies heuristics such as trying the common-name endpoint first for multi-word capitalized inputs. The resolver automatically skips the lookup step when the input already looks like an LSID, and caches all successful resolutions to minimize repeated ALA calls within a session. For example, a query like “Red Kangaroo” is resolved to the corresponding scientific name, LSID, rank, and vernacular name, with subsequent lookups served from the cache. 

## 3. Research Planner (create_research_plan)

The Research Planner determines which tools to use and in what order for a given query. It takes as input the user query plus resolved species information and outputs a `ResearchPlan` that includes the query type, species mentioned, and a list of `ToolPlan` items with tool names and priorities. The planner uses a priority system where must-call tools are essential and always executed, while optional tools are enhancement steps that run only after must-call tools succeed. It encodes decision rules such as: “count in location” → `get_occurrence_taxa_count`, “count in each category” → `get_occurrence_breakdown`, “show occurrences” → `search_species_occurrences`, “tell me about” → `lookup_species_info`, “where does it live” → `get_species_distribution`, and “show me a photo” → `get_species_images`. 

## 4. Tool Executor

The Tool Executor is responsible for running the tools specified in the research plan in priority order. Execution happens in two phases: first, it runs all must-call tools; if any must-call tool fails, it stops and reports an error back to the user. In the second phase, it runs all optional tools and logs any failures without interrupting the workflow. Each tool is implemented as a closure with access to shared context (such as the iChatBio response context, resolved parameters with LSIDs, the workflow agent, and the ALA logic layer), allowing tools to create artifacts, call APIs, and reply to the user in a consistent way. 

## 5. ALA Logic Layer (ala_logic.py)

The ALA Logic Layer encapsulates all ALA API interactions and parameter validation. It builds API URLs with correct encoding for endpoints such as name matching, occurrence search, facets, taxa count, species distribution, and species images. It executes HTTP requests, handles errors and retries, and returns parsed responses for downstream use by tools and the agent workflow. All API parameters are validated using Pydantic v2 models, ensuring correct types and required fields before a request is sent, which helps catch malformed queries early. 

## 6. ALA Agent and Tool Set (ala_ichatbio_agent.py)

The ALA iChatBio Agent module orchestrates the workflow and exposes the main biodiversity tools used in the research plans. The core tools include:

- `search_species_occurrences`: Retrieves individual occurrence records (up to a configurable maximum) with coordinates, dates, collectors, and related metadata, using the `occurrences/search` endpoint.  
- `get_occurrence_breakdown`: Returns analytical counts grouped by facets such as state, year, species, kingdom, family, basis of record, or institution code, backed by the `occurrences/facets` endpoint.  
- `get_occurrence_taxa_count`: Returns total counts of records for one or more LSIDs (with optional filters) using the `occurrences/taxaCount` endpoint.  
- `lookup_species_info`: Retrieves comprehensive species information including names, taxonomy, and classification via the species search endpoint.  
- `get_species_distribution`: Fetches expert distribution data and spatial ranges for species given an LSID via the distribution endpoint.  
- `get_species_images`: Retrieves primary species images and associated metadata via the image search endpoint.  

Each tool is integrated with the Parameter Extractor, Parameter Resolver, Research Planner, and ALA Logic Layer so that natural-language queries can be translated into precise ALA API calls and user-friendly artifacts. 