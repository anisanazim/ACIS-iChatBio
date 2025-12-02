# How It Works

This section walks through the end-to-end flow of a user query inside the ALA iChatBio Agent, from natural language input to ALA API calls and final response.

## 1. User Query

A user starts by asking a natural-language question, such as:

> "Count koala sightings in Queensland"  
> "Where do koalas live?"  
> "Show me a photo of a platypus"

This free-text input is sent to the agent server, which hands it to the ALA iChatBio Agent workflow.

## 2. Parameter Extraction

The Parameter Extractor converts the raw query into a structured search request.

- It uses an LLM with a Pydantic schema (e.g., `ALASearchResponse`) to extract:
  - `q`: main taxon or search term (e.g., `koala`)
  - `fq`: filter queries (e.g., `state:Queensland`, year filters)
  - Spatial parameters (coordinates, bounding boxes, states)
  - Temporal parameters (years, date ranges)
  - Facet-related hints and unresolved parameters
  - A `clarification_needed` flag if the query is ambiguous
- The result is a validated object that can be passed safely into the rest of the pipeline.

If extraction fails or is incomplete, the agent can ask the user for clarification instead of calling downstream tools blindly.

## 3. Parameter Resolution (Name → LSID)

If the query mentions a species, the Parameter Resolver enriches the extracted parameters with canonical taxonomic identifiers.

- It calls ALA name-matching services to resolve:
  - Common names (e.g., `koala`, `Red Kangaroo`)
  - Scientific names (e.g., `Phascolarctos cinereus`)
- The resolver:
  - Chooses between scientific-name and vernacular-name endpoints
  - Detects when input is already an LSID and skips lookups
  - Caches all resolutions for the current session (first call hits the API, subsequent calls are served from cache)
- The output parameters now include fields such as:
  - `scientific_name`
  - `lsid` / `taxonConceptID`
  - Rank and other taxonomic metadata

These enriched parameters are passed to the planner.

## 4. Research Planning

The Research Planner decides which tools to use and in what order.

**Input:**
- User query text
- Resolved species information (names, LSIDs)
- Extracted filters and context

**Output:**
- A `ResearchPlan` containing:
  - `query_type` (e.g., single species, multi-species, distribution, images)
  - `species_mentioned`
  - A list of `ToolPlan` entries with:
    - `tool_name`
    - `priority` (`must_call` or `optional`)
    - A brief reasoning string

The planner applies simple decision rules, for example:

- "Count X in location" → `get_occurrence_taxa_count`
- "How many X in each state/year?" → `get_occurrence_breakdown`
- "Show X occurrences" → `search_species_occurrences`
- "Tell me about X" → `lookup_species_info`
- "Where does X live?" → `get_species_distribution`
- "Show me a photo of X" → `get_species_images`

This plan governs the next phase.

## 5. Tool Execution

The Tool Executor runs the tools defined in the research plan in a two-phase process.

**Phase 1:** Execute all `must_call` tools
- If any `must_call` tool fails, stop execution and report an error or fallback message to the user.

**Phase 2:** Execute all `optional` tools
- Failures in optional tools are logged but do not abort the workflow.

Each tool is implemented as a closure that has access to:

- The current response context (for creating artifacts and replies)
- Resolved parameters (including LSIDs and filters)
- The workflow helper for running steps
- The ALA logic layer for building URLs and executing HTTP calls

**Examples:**

- `get_occurrence_taxa_count` builds an `occurrences/taxaCount` URL with LSIDs and filters, executes it, and returns a total count.
- `get_occurrence_breakdown` calls `occurrences/facets` with selected facets (e.g., state, year).
- `search_species_occurrences` calls `occurrences/search` and returns individual records.
- `lookup_species_info` queries species search endpoints for profiles.
- `get_species_distribution` and `get_species_images` call distribution and image endpoints using LSIDs or derived IDs.

Each tool typically creates JSON artifacts with raw results and attaches human-readable descriptions.

## 6. ALA Logic and HTTP Layer

Under the hood, all tools rely on a shared ALA logic layer.

**Responsibilities:**
- Validate parameters with Pydantic models
- Build endpoint URLs for name matching, occurrences, species, distribution, and images
- Encode query parameters correctly
- Execute async HTTP requests (e.g., using `aiohttp`)
- Handle errors and retries
- Return parsed JSON data to tools

By centralizing this logic, tools can focus on "what" they need (counts, facets, records, distributions, images) instead of "how" to talk to the ALA APIs.

## 7. Response Formatting

After tools complete, the agent assembles a final answer.

- Combines outputs from must-call and optional tools
- Generates:
  - Natural-language summaries (e.g., "Found 15,234 occurrence records for koala in Queensland.")
  - Structured artifacts (JSON with counts, facet breakdowns, occurrence records)
  - Links or references to maps and images where appropriate
- Returns this combined result back to the user through the iChatBio interface.

The result is a multi-step, plan-driven workflow that starts from plain English and ends with precise ALA-backed biodiversity insights.