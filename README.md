# Atlas of Living Australia (ALA) iChatBio Agent

This project is an AI agent designed to interact with the [Atlas of Living Australia (ALA)](https://ala.org.au/) API. It is built using the `ichatbio-sdk` and provides a conversational interface to search for biodiversity data, including species occurrences, taxonomic profiles, spatial distribution maps, and species lists.

## Table of Contents
- [Key Features](#key-features)
- [Project Structure](#project-structure)
- [Setup and Installation](#setup-and-installation)
- [Usage](#usage)
    - [Running the iChatBio Server](#running-the-ichatbio-server)
- [API Entrypoints](#api-entrypoints)
- [Testing](#testing)
- [Example User Interactions](#example-user-interactions)

## Key Features

This agent exposes comprehensive capabilities across four main ALA APIs:

### Occurrence API
- **Occurrence Search**: Search for species occurrence records with natural language queries and advanced filtering
- **Single Occurrence Lookup**: Retrieve a specific occurrence record by its UUID
- **Occurrence Facets**: Get data breakdowns and insights from occurrence records using faceted analysis
- **Taxa Count**: Get occurrence counts for specific taxa by their GUIDs/LSIDs
- **Field Discovery**: Programmatically fetch a list of all searchable fields in the occurrence database

### Species API
- **Species GUID Lookup**: Look up taxon GUIDs by name - essential for linking species to occurrence data
- **Species Image Search**: Search for taxa with images available - visual species information
- **BIE Search**: Search the Biodiversity Information Explorer (BIE) for species and taxa

### Spatial API
- **Expert Distribution Discovery**: List all available expert distribution maps for species
- **Distribution by LSID**: Get expert distribution data for a taxon by its LSID
- **Distribution Map Visualization**: Retrieve PNG map images showing species distribution ranges across Australia

### Species List API
- **Filter Species Lists**: Filter species lists by scientific names or data resource IDs
- **Species List Details**: Get detailed information about specific species lists
- **Species List Items**: Get species from specific lists with optional name filtering
- **Distinct Field Values**: Get distinct values for fields across all species list items
- **Common Keys**: Get common metadata keys across multiple species lists

## Project Structure

The agent is organized into four distinct files, each with a clear responsibility:

- **`ala_logic.py`**: The core logic layer. This file handles all direct communication with the ALA API across four services (Occurrences, Species, Spatial, and Species Lists). It contains the Pydantic models for structuring API parameters, builds the API request URLs, and uses `cloudscraper` to execute HTTP requests for both JSON data and binary image content.

- **`ala_ichatbio_agent.py`**: The workflow orchestrator. This file defines the step-by-step processes for each of the agent's capabilities across all four API categories. It uses the functions from `ala_logic.py` and translates the outcomes into standardized `iChatBio` messages and artifacts.

- **`agent_server.py`**: The production-ready web server. This file uses the `ichatbio-sdk` to wrap the agent in a web server, defines the formal `AgentCard` to advertise its capabilities across occurrence, species, spatial, and species list services, and routes incoming requests to the appropriate workflow in `ala_ichatbio_agent.py`.

- **`test_agent.py`**: Comprehensive test suite covering all implemented endpoints with real-world test data and scenarios across all API categories.

## Setup and Installation

Follow these steps to set up and run the agent locally.

**1. Clone the Repository**

```bash
git clone <your-repository-url>
cd <your-repository-name>
```

**2. Create and Activate a Virtual Environment**
It's highly recommended to use a virtual environment to manage dependencies.

- On Windows:

```bash
python -m venv venv
.\venv\Scripts\activate
```

- On macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

**3. Install Dependencies**
Create a file named `requirements.txt` with the following content:

```
ichatbio-sdk
openai
instructor
requests
pyyaml
cloudscraper
pytest
pytest-asyncio
```

Then, install the dependencies using pip:

```bash
pip install -r requirements.txt
```

**4. Configure Environment Variables**
The agent requires an OpenAI API key to understand natural language queries. Create a file named `env.yaml` in the root of the project and add your key:

```yaml
# env.yaml
OPENAI_API_KEY: "sk-..."
ALA_API_URL: "https://api.ala.org.au"  # Optional, defaults to this value
```

## Usage

You can run the agent in two ways: as a full `iChatBio` server or using the test suite for validation.

### Running the iChatBio Server

To run the agent as a network service that the `iChatBio` platform can communicate with, use the `agent_server.py` script.

```bash
python agent_server.py
```

You should see output from `Uvicorn` indicating the server is running on `http://0.0.0.0:9999`.

To verify that the agent is running and discoverable, navigate to the following URL in your web browser:
`http://localhost:9999/.well-known/agent.json`

This will display the agent's `AgentCard` in JSON format.

## API Entrypoints

The agent exposes the following entrypoints across four ALA API categories:

### Occurrence API Entrypoints

| Entrypoint ID | Description | Parameters Model |
| :-- | :-- | :-- |
| `search_occurrences` | Search for species occurrence records in the ALA. | `OccurrenceSearchParams` |
| `lookup_occurrence` | Get a single occurrence record by its UUID. | `OccurrenceLookupParams` |
| `get_occurrence_facets` | Get data breakdowns and insights from occurrence records using facets. | `OccurrenceFacetsParams` |
| `get_occurrence_taxa_count` | Get occurrence counts for specific taxa by their GUIDs/LSIDs. | `OccurrenceTaxaCountParams` |
| `get_index_fields` | Get a list of all searchable fields in the occurrence database. | `NoParams` |

### Species API Entrypoints

| Entrypoint ID | Description | Parameters Model |
| :-- | :-- | :-- |
| `species_guid_lookup` | Look up a taxon GUID by name - essential for linking species to occurrence data. | `SpeciesGuidLookupParams` |
| `species_image_search` | Search for taxa with images available - visual species information. | `SpeciesImageSearchParams` |
| `species_bie_search` | Search the Biodiversity Information Explorer (BIE) for species and taxa. | `SpeciesBieSearchParams` |

### Spatial API Entrypoints

| Entrypoint ID | Description | Parameters Model |
| :-- | :-- | :-- |
| `list_distributions` | List all expert distributions available in the ALA spatial service. | `NoParams` |
| `get_distribution_by_lsid` | Get expert distribution for a taxon by LSID. | `SpatialDistributionByLsidParams` |
| `get_distribution_map` | Get PNG image for a distribution map by image ID. | `SpatialDistributionMapParams` |

### Species List API Entrypoints

| Entrypoint ID | Description | Parameters Model |
| :-- | :-- | :-- |
| `filter_species_lists` | Filter species lists by scientific names or data resource IDs. | `SpeciesListFilterParams` |
| `get_species_list_details` | Get detailed information about specific species lists. | `SpeciesListDetailsParams` |
| `get_species_list_items` | Get species from specific lists with optional name filtering. | `SpeciesListItemsParams` |
| `get_species_list_distinct_fields` | Get distinct values for a field across all species list items. | `SpeciesListDistinctFieldParams` |
| `get_species_list_common_keys` | Get common keys (metadata) across multiple species lists. | `SpeciesListCommonKeysParams` |

## Testing

The project includes a comprehensive test suite that validates all API endpoints with real-world data.

### Running Tests

```bash
# Run all tests
pytest test_agent.py -v

# Run specific test categories
pytest test_agent.py -v -k "occurrence"
pytest test_agent.py -v -k "species"
pytest test_agent.py -v -k "spatial"
pytest test_agent.py -v -k "species_list"
```

### Test Coverage

The test suite covers:
- **Occurrence Search**: Using real species and location data
- **Occurrence Facets**: Data breakdown and analysis capabilities
- **Taxa Count**: Counting occurrences for specific GUIDs
- **Species GUID Lookup**: Converting names to GUIDs
- **Species Image Search**: Finding taxa with visual content
- **BIE Search**: Comprehensive species database search
- **Spatial Distributions**: Using real LSIDs and imageIds from ALA's distribution database
- **Species Lists**: Filtering, details, items, and metadata operations
- **Error Handling**: Network failures and invalid parameters

## Example User Interactions

Once deployed, users can interact with the agent using natural language:

### Occurrence Queries
- *"Find koala sightings in Queensland"* → `search_occurrences`
- *"Show me the details for occurrence record abc123"* → `lookup_occurrence`
- *"What are the data sources for bird observations in 2023?"* → `get_occurrence_facets`
- *"How many records exist for Macropus rufus?"* → `get_occurrence_taxa_count`

### Species Information
- *"What's the GUID for the Red Kangaroo?"* → `species_guid_lookup`
- *"Find species with photos available"* → `species_image_search`
- *"Search for eucalyptus species in the BIE"* → `species_bie_search`

### Spatial Distribution
- *"What species have distribution maps available?"* → `list_distributions`
- *"Show me the distribution data for this species LSID"* → `get_distribution_by_lsid`
- *"Can I see a map of where brush-tailed rabbit-rats live?"* → `get_distribution_map`

### Species Lists
- *"Find species lists that contain koalas"* → `filter_species_lists`
- *"Show me details about the threatened species list dr781"* → `get_species_list_details`
- *"What Acacia species are in the flora list?"* → `get_species_list_items`
- *"What kingdoms are represented in the species lists?"* → `get_species_list_distinct_fields`

## Architecture Notes

### API Integration Strategy
- **Occurrences API**: Use `api.ala.org.au/occurrences` endpoints for occurrence data and faceted analysis
- **Species API**: Use `api.ala.org.au/species` endpoints for taxonomic information and images
- **Spatial API**: Use `api.ala.org.au/spatial-service` endpoints for distribution data and PNG maps
- **Species Lists API**: Use `api.ala.org.au/specieslist` endpoints for curated species collections
- **Error Handling**: Graceful fallbacks for network issues and missing data
- **Authentication**: Currently uses public endpoints; easily extensible for API keys

### Performance Considerations
- Uses `cloudscraper` to handle potential bot detection
- Implements proper async/await patterns for non-blocking API calls
- Creates artifacts for large datasets to avoid message size limits
- Supports both GET and POST requests for different API endpoints
- Handles various response formats (JSON objects, arrays, binary images)

### Data Flow
1. **User Query** → Natural language input processed by OpenAI
2. **Parameter Extraction** → Structured parameters using Pydantic models
3. **API Request** → HTTP requests to appropriate ALA endpoints
4. **Response Processing** → JSON/binary data parsed and analyzed
5. **Artifact Creation** → Large datasets stored as downloadable artifacts
6. **User Response** → Human-friendly summary with actionable insights
