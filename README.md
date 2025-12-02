# 🌿 ALA iChatBio Agent

Natural-language biodiversity querying powered by the Atlas of Living Australia (ALA)

The ALA iChatBio Agent is an intelligent conversational agent built on the iChatBio framework. It allows users to query Australian biodiversity data using plain English, automatically resolving species names, constructing ALA API calls, and producing structured artifacts such as occurrence records, species profiles, and distribution data.

This project integrates advanced LLM reasoning, ALA's public APIs, and a multi-step research workflow to deliver accurate, human-friendly biodiversity insights.

## ✨ Key Features

* 🔍 Natural language to ALA API translation
* 🐾 Automatic species name resolution Common → Scientific → LSID, using Name Matching API
* 🧠 Research planning using an LLM with priority-based tool sequencing
* 🛠️ 7 specialized biodiversity tools (occurrences, facets, taxa count, species info, distribution, images)
* ⚡ Smart caching for faster repeated queries
* 🧩 Pydantic-validated parameter models
* 📄 Rich artifact generation (JSON, metadata, process logs)
* 🌐 Async HTTP execution via aiohttp

## 📁 Project Structure

```
ALA-iChatBio-Agent/
├── agent_server.py              # iChatBio server entry point
├── ala_ichatbio_agent.py        # Main agent implementation + tool execution
├── parameter_extractor.py       # LLM-based parameter extraction
├── parameter_resolver.py        # Name → LSID resolution (with caching)
├── ala_logic.py                 # ALA API logic + URL builders
├── main_ala_logic.py            # Pydantic models for validation
├── env.yaml                     # Environment variables
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## ⚙️ Installation

### Prerequisites

* Python 3.11+
* `pip`
* Virtual environment tool (`venv` or conda)
* OpenAI API key

### 1. Clone the repository

```bash
git clone <repository-url>
cd ALA-iChatBio-Agent
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

Create an `env.yaml` file:

```yaml
OPENAI_API_KEY: "your-api-key"
OPENAI_BASE_URL: "https://api.openai.com"
ALA_API_BASE_URL: "https://api.ala.org.au"
```

### 5. Run the agent server

```bash
python agent_server.py
```

## ▶️ Quick Example

**User:**
```
Count koala sightings in Queensland
```

**Agent internal steps:**
1. Extract parameters → `{ q: "koala", fq: ["state:Queensland"] }`
2. Resolve species → Phascolarctos cinereus (LSID)
3. Research planner selects → `get_occurrence_taxa_count`
4. ALA API called → `/occurrences/taxaCount?...`
5. Returns → 15,234 records

**Agent Response:**
```
Found 15,234 occurrence records for koalas in Queensland.
```

## 📚 Full Documentation

Detailed technical documentation is available in the `/docs` folder:

* Overview
* Architecture
* Core Components
* API Integration
* Setup & Installation
* How It Works
* Development Guide
* Troubleshooting
* Appendix

## 🧪 Testing

Manual queries and automated tests can be added. Run tests (if implemented):

```bash
pytest tests/
```

## 🤝 Contributing

Pull requests and issue submissions are welcome. Please ensure changes are documented and tested where appropriate.

## 📬 Contact

**Developer:** Anisa Shaik  
**Email:** anisa.shaik@ufl.edu  
**Issues:** GitHub repository issue tracker