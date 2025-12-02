# Architecture

The ALA iChatBio Agent uses a modular, multi-layer architecture that separates language understanding, planning, and ALA API integration into distinct components. This design makes the system easier to extend, debug, and test as new tools or APIs are added.

## High-Level Flow

1. The user sends a natural-language query (for example, "Count koala sightings in Queensland").
2. The Parameter Extractor converts the query into structured ALA search parameters.
3. The Parameter Resolver resolves species names to scientific names and LSIDs.
4. The Research Planner decides which tools to run and in what order.
5. The Tool Executor runs the selected tools and calls ALA API endpoints through the ALA Logic Layer.
6. The agent formats results into user-friendly responses and artifacts such as JSON, maps, and images.

## System Components

### iChatBio Agent Server (`agent_server.py`)
Handles incoming requests, manages sessions, and connects to the iChatBio framework.

### ALA iChatBio Agent (`ala_ichatbio_agent.py`)
Orchestrates the workflow, manages tool closures, and coordinates parameter extraction, resolution, planning, and execution.

### Parameter Extractor (`parameter_extractor.py`)
Uses an LLM with structured output (Pydantic models) to extract query parameters such as species, spatial filters, temporal filters, and facets.

### Parameter Resolver (`parameter_resolver.py`)
Resolves species names to LSIDs via the ALA Name Matching APIs and caches results to reduce repeated lookups.

### Research Planner (`create_research_plan`)
Chooses which tools to call and in what sequence, using a priority-based plan (must-call vs optional tools).

### Tool Executor
Executes planned tools in two phases (must-call then optional), handles errors, and ensures essential tools complete before running enhancements.

### ALA Logic Layer (`ala_logic.py` and `main_ala_logic.py`)
Builds ALA API URLs, validates parameters with Pydantic models, executes HTTP requests (via aiohttp), handles errors, and parses responses.

## Data Flow

### 1. Input
A user sends a natural-language query via the iChatBio interface.

### 2. Parameter Extraction
The Parameter Extractor produces a structured search object (for example, with fields like `q`, `fq`, spatial constraints, temporal filters, and flags such as `clarification_needed`).

### 3. Parameter Resolution
If a species name is present, the resolver calls ALA name services and enriches the parameters with `scientific_name`, `lsid`, and other identifiers, caching these mappings for the current session.

### 4. Research Plan Creation
The Research Planner inspects the resolved parameters and query type (single species, distribution, images, counts, breakdowns, and so on) and outputs a plan containing ordered tool calls and priorities.

### 5. Tool Execution
Tool closures receive the context and resolved parameters, use the ALA Logic Layer to construct URLs, make async HTTP calls to ALA endpoints, create artifacts (JSON payloads, image links, distribution data), and log the process.

### 6. Response Generation
The agent aggregates tool outputs, converts them into a natural-language answer, attaches any artifacts (JSON, maps, images), and returns the final response to the user.

## Architectural Principles

### Modularity
Each responsibility (extraction, resolution, planning, execution, ALA integration) resides in a focused module.

### Strong typing and validation
Pydantic models enforce correct parameter shapes and catch errors early.

### Async I/O
aiohttp enables concurrent, non-blocking calls to ALA APIs, improving performance.

### Caching
Species name resolutions are cached to avoid redundant calls to the ALA name services within a session.

### Plan-based execution
A research plan with must-call and optional tools ensures essential information is retrieved first, with additional tools running only after the core steps succeed.