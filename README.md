# ALA Search Agent: Natural Language Interface for the Atlas of Living Australia

This repository contains a powerful Python agent that allows users to query the [Atlas of Living Australia (ALA)](https://ala.org.au/) using natural language. The agent can be run as a command-line tool or as an iChatBio-compatible server. It leverages a Large Language Model (LLM) to understand user queries and translate them into valid API requests for species occurrences and profiles.

## Features

* **Natural Language Queries**: Ask for biodiversity data in plain English (e.g., `"show me koalas in New South Wales"`).
* **Occurrence Search**: Retrieve species occurrence records with support for a wide range of filters, including:
    * **Taxonomic**: family, genus, scientific name, etc.
    * **Geographic**: country, state, locality.
    * **Temporal**: year, date ranges.
    * **Attribute**: records with images or coordinates.
* **Species Profile Search**: Get detailed information about specific species.
* **Robust Fallback**: If the authenticated species API is unavailable, the agent gracefully falls back to the public occurrences API to provide a basic species profile.
* **Dual Interface**: Can be used directly from the command line (`ala_agent.py`) or run as a persistent agent server (`ala_ichatbio_agent.py`).
* **Comprehensive Test Suite**: Includes both unit tests (using mocks) and "glass-box" integration tests to verify live end-to-end functionality.


## Prerequisites

* Python 3.9+
* An [OpenAI API Key](https://platform.openai.com/api-keys)
* (Optional) An [ALA API Key](https://api.ala.org.au/) for full access to the authenticated species endpoint.


## Installation

1. **Clone the repository:**

```bash
git clone <your-repository-url>
cd <your-repository-name>
```

2. **Create and activate a virtual environment:**

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

3. **Install the required dependencies:**

```bash
pip install -r requirements.txt
```

*(Note: If a `requirements.txt` file is not present, you can create one from the imports in `ala_agent.py`, including `pydantic`, `requests`, `openai`, `pyyaml`, `instructor`, and `ichatbio`.)*
4. **Configure your API keys:**
Create a file named `env.yaml` in the root of the project directory and add your API keys. This file is included in `.gitignore` and should not be committed to version control.

**`env.yaml` template:**

```yaml
OPENAI_API_KEY: "your-openai-api-key-here"
# ALA_API_KEY: "your-ala-jwt-token-here"  # Optional, for authenticated species search
```


## Usage

The agent can be run directly from the command line for immediate queries.

### Occurrence Search

Use the `occurrences` command to search for species occurrence records.

**Examples:**

* **Filter by common name and location:**

```bash
python ala_agent.py occurrences "show me koalas in New South Wales"
```

* **Filter by year and scientific name:**

```bash
python ala_agent.py occurrences "any platypus sightings in 2023"
```

* **Filter by attribute (records with images):**

```bash
python ala_agent.py occurrences "I need photos of the Laughing Kookaburra"
```

* **Filter by a combination of parameters:**

```bash
python ala_agent.py occurrences "show me preserved specimens of the Tasmanian Devil"
```


### Species Profile Search

Use the `species` command to get a profile for a specific species. This command will automatically use the fallback mechanism if an ALA API key is not provided.

**Examples:**

* **Lookup by common name:**

```bash
python ala_agent.py species "tell me about the koala"
```

* **Lookup by Life Science Identifier (LSID):**

```bash
python ala_agent.py species "lookup urn:lsid:biodiversity.org.au:afd.taxon:31a9b8b8-4e8f-4343-a15f-2ed24e0bf1ae"
```


### Running as an iChatBio Agent Server

To run the agent as a persistent server compatible with the iChatBio framework, use the `ala_ichatbio_agent.py` script[^1]:

```bash
python ala_ichatbio_agent.py
```

The server will start on `http://0.0.0.0:9999` by default.

## Testing

This project includes a robust test suite to ensure reliability.

### Unit Tests

The unit tests use mocking to test the agent's logic in isolation, without making any real API calls. They are fast and can be run without an API key.

```bash
pytest test.py
```


### Integration Tests

The integration tests make **real calls** to the OpenAI and ALA APIs to verify the end-to-end functionality. These tests require a valid `OPENAI_API_KEY` to be set in your `env.yaml` file. Tests that require an authenticated `ALA_API_KEY` will be automatically skipped if the key is not present[^2].

To see the detailed `print` statements during the test run (recommended for debugging), use the `-s` flag:

```bash
pytest -s test_live_enhanced.py
```


## Project Structure

```
.
├── ala_agent.py              # Core logic and command-line interface
├── ala_ichatbio_agent.py     # iChatBio server implementation
├── test.py                   # Unit tests (mocked)
└── test_live_enhanced.py     # Integration tests (live APIs)
├── env.yaml                  # Local configuration for API keys (not in git)
└── README.md                 # This file
```