# Atlas of Living Australia (ALA) iChatBio Agent

This project is an AI agent designed to interact with the [Atlas of Living Australia (ALA)](https://ala.org.au/) API. It is built using the `ichatbio-sdk` and provides a conversational interface to search for biodiversity data, including species occurrences and taxonomic profiles.

## Table of Contents
- [Key Features](#key-features)
- [Project Structure](#project-structure)
- [Setup and Installation](#setup-and-installation)
- [Usage](#usage)
    - [Running the iChatBio Server](#running-the-ichatbio-server)
    - [Using the CLI for Testing](#using-the-cli-for-testing)
- [API Entrypoints](#api-entrypoints)


## Key Features

This agent exposes several capabilities of the ALA API:

- **Occurrence Search**: Search for species occurrence records with natural language queries.
- **Single Occurrence Lookup**: Retrieve a specific occurrence record by its UUID.
- **Faceted Species Search**: Find lists of species using powerful, direct queries.
- **Single Species Lookup**: Get a detailed profile and the full taxonomic classification for a species by its name.
- **Field Discovery**: Programmatically fetch a list of all searchable fields in the occurrence database.


## Project Structure

The agent is organized into four distinct files, each with a clear responsibility:

- **`ala_logic.py`**: The core logic layer. This file handles all direct communication with the ALA API. It contains the Pydantic models for structuring API parameters, builds the API request URLs, and uses `cloudscraper` to execute the HTTP requests.
- **`ala_ichatbio_agent.py`**: The workflow orchestrator. This file defines the step-by-step processes for each of the agent's capabilities (e.g., how to perform a species search). It uses the functions from `ala_logic.py` and translates the outcomes into standardized `iChatBio` messages.
- **`agent_server.py`**: The production-ready web server. This file uses the `ichatbio-sdk` to wrap the agent in a web server, defines the formal `AgentCard` to advertise its capabilities, and routes incoming requests to the appropriate workflow in `ala_ichatbio_agent.py`.
- **`run_cli.py`**: A command-line interface for development and testing. This script allows you to run each of the agent's workflows directly from your terminal to verify their functionality in isolation.


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
```

## Usage

You can run the agent in two ways: as a full `iChatBio` server or using the command-line tool for testing.

### Running the iChatBio Server

To run the agent as a network service that the `iChatBio` platform can communicate with, use the `agent_server.py` script.

```bash
python agent_server.py
```

You should see output from `Uvicorn` indicating the server is running on `http://0.0.0.0:9999`.

To verify that the agent is running and discoverable, navigate to the following URL in your web browser:
`http://localhost:9999/.well-known/agent.json`

This will display the agent's `AgentCard` in JSON format.

### Using the CLI for Testing

The `run_cli.py` script allows you to test each agent function directly.

- **Search for occurrences:**

```bash
python run_cli.py occurrences "find records of Macropus rufus"
```

- **Look up a single occurrence by UUID:**

```bash
python run_cli.py lookup_occurrence <uuid>
```

- **Search for a list of species:**

```bash
python run_cli.py search_species "rk_genus:Macropus"
```

- **Look up a single species and its classification:**

```bash
python run_cli.py lookup_species "koala"
```

- **Get all searchable fields:**

```bash
python run_cli.py index_fields
```


## API Entrypoints

The agent exposes the following entrypoints, as defined in its `AgentCard`:


| Entrypoint ID | Description | Parameters Model |
| :-- | :-- | :-- |
| `search_occurrences` | Search for species occurrence records in the ALA. | `OccurrenceSearchParams` |
| `search_species` | Search for a list of species using faceted filters. | `SpeciesSearchParams` |
| `lookup_species` | Get a profile for a single species from the ALA by name. | `SpeciesLookupParams` |
| `lookup_occurrence` | Get a single occurrence record by its UUID. | `OccurrenceLookupParams` |
| `get_index_fields` | Get a list of all searchable fields. | (None) |
