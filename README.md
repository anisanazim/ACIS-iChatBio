# Atlas of Living Australia (ALA) iChatBio Agent

This project is an AI agent designed to interact with the [Atlas of Living Australia (ALA)](https://ala.org.au/) API. It is built using the `ichatbio-sdk` and provides a conversational interface to search for biodiversity data, including species occurrences, taxonomic profiles, and spatial distribution maps.

## Table of Contents
- [Key Features](#key-features)
- [Project Structure](#project-structure)
- [Setup and Installation](#setup-and-installation)
- [Usage](#usage)
    - [Running the iChatBio Server](#running-the-ichatbio-server)
- [API Entrypoints](#api-entrypoints)
- [Testing](#testing)

## Key Features

This agent exposes several capabilities across three main ALA APIs:

### Occurrence API
- **Occurrence Search**: Search for species occurrence records with natural language queries.
- **Single Occurrence Lookup**: Retrieve a specific occurrence record by its UUID.
- **Field Discovery**: Programmatically fetch a list of all searchable fields in the occurrence database.

### Species API
- **Faceted Species Search**: Find lists of species using powerful, direct queries.
- **Single Species Lookup**: Get a detailed profile and the full taxonomic classification for a species by its name.

### Spatial API
- **Expert Distribution Discovery**: List all available expert distribution maps for species.
- **Distribution Map Visualization**: Retrieve PNG map images showing species distribution ranges across Australia.

## Project Structure

The agent is organized into four distinct files, each with a clear responsibility:

- **`ala_logic.py`**: The core logic layer. This file handles all direct communication with the ALA API across three services (Occurrences, Species, and Spatial). It contains the Pydantic models for structuring API parameters, builds the API request URLs, and uses `cloudscraper` to execute HTTP requests for both JSON data and binary image content.

- **`ala_ichatbio_agent.py`**: The workflow orchestrator. This file defines the step-by-step processes for each of the agent's capabilities across all three API categories. It uses the functions from `ala_logic.py` and translates the outcomes into standardized `iChatBio` messages and artifacts.

- **`agent_server.py`**: The production-ready web server. This file uses the `ichatbio-sdk` to wrap the agent in a web server, defines the formal `AgentCard` to advertise its capabilities across occurrence, species, and spatial services, and routes incoming requests to the appropriate workflow in `ala_ichatbio_agent.py`.

- **`test_agent.py`**: Comprehensive test suite covering all implemented endpoints with real-world test data and scenarios.

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

The agent exposes the following entrypoints across three ALA API categories:

### Occurrence API Entrypoints

| Entrypoint ID | Description | Parameters Model |
| :-- | :-- | :-- |
| `search_occurrences` | Search for species occurrence records in the ALA. | `OccurrenceSearchParams` |
| `lookup_occurrence` | Get a single occurrence record by its UUID. | `OccurrenceLookupParams` |
| `get_index_fields` | Get a list of all searchable fields in the occurrence database. | `NoParams` |

### Species API Entrypoints

| Entrypoint ID | Description | Parameters Model |
| :-- | :-- | :-- |
| `search_species` | Search for a list of species using faceted filters. | `SpeciesSearchParams` |
| `lookup_species` | Get a profile for a single species from the ALA by name. | `SpeciesLookupParams` |

### Spatial API Entrypoints

| Entrypoint ID | Description | Parameters Model |
| :-- | :-- | :-- |
| `list_distributions` | List all expert distributions available in the ALA spatial service. | `NoParams` |
| `get_distribution_map` | Get PNG image for a distribution map by image ID. | `SpatialDistributionMapParams` |

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
```

### Test Coverage

The test suite covers:
- **Occurrence Search**: Using real species and location data
- **Species Lookup**: With valid scientific names  
- **Spatial Distributions**: Using real imageIds from ALA's distribution database
- **Error Handling**: Network failures and invalid parameters

### Example User Interactions

Once deployed, users can interact with the agent using natural language:

- *"Find koala sightings in Queensland"* → `search_occurrences`
- *"Show me information about Malurus cyaneus"* → `lookup_species`  
- *"What species have distribution maps available?"* → `list_distributions`
- *"Can I see a map of where brush-tailed rabbit-rats live?"* → `get_distribution_map`

## Architecture Notes

### API Integration Strategy
- **Occurrences & Species**: Use `api.ala.org.au` endpoints for JSON data
- **Spatial Maps**: Use `api.ala.org.au/spatial-service` endpoints for binary PNG images
- **Error Handling**: Graceful fallbacks for network issues and missing data
- **Authentication**: Currently uses public endpoints; easily extensible for API keys

### Performance Considerations
- Uses `cloudscraper` to handle potential bot detection
- Implements proper async/await patterns for non-blocking API calls
- Creates artifacts for large datasets to avoid message size limits

The implementation handles these scenarios gracefully and provides meaningful feedback to users.