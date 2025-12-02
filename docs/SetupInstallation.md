# Setup & Installation

This section describes how to set up and run the ALA iChatBio Agent in a local development environment. It assumes basic familiarity with Python virtual environments and environment configuration.

## Prerequisites

Before installing, ensure the following are available:

- Python 3.11
- `pip` (Python package manager)
- A virtual environment tool (`venv` or conda)
- An OpenAI API key for LLM-based components

## 1. Clone the Repository

Clone the project and switch into its directory:

git clone <repository-url>
cd ALA-iChatBio-Agent


Replace `<repository-url>` with the actual Git repository URL for your project.

## 2. Create and Activate a Virtual Environment

Create a fresh virtual environment to isolate dependencies:

python -m venv venv


Activate the environment:

- On macOS/Linux:

source venv/bin/activate

- On Windows:

venv\Scripts\activate


## 3. Install Dependencies

Install all required Python packages using the provided requirements file:

pip install -r requirements.txt


This will pull in the core libraries such as Pydantic, OpenAI client, aiohttp, the iChatBio framework, and related dependencies.

## 4. Configure Environment

Create an `env.yaml` file in the project root to configure API keys and base URLs. A typical configuration looks like:

OPENAI_API_KEY: "your-api-key"
OPENAI_BASE_URL: "https://api.openai.com" # or your proxy/base URL
ALA_API_BASE_URL: "https://api.ala.org.au"


- `OPENAI_API_KEY` is required for LLM-based parameter extraction and planning.
- `OPENAI_BASE_URL` can point to the standard OpenAI endpoint or a proxy.
- `ALA_API_BASE_URL` should normally point to the public ALA API host, but can be overridden for testing or proxying.

Ensure this file is not committed to version control if it contains secrets.

## 5. Run the Agent Server

Once dependencies and environment configuration are in place, start the agent server:

python agent_server.py


This command launches the iChatBio-based server that hosts the ALA iChatBio Agent, making it available to accept natural-language biodiversity queries and route them through the configured tools and ALA APIs.