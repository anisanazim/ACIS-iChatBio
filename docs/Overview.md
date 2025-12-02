# Overview

## What is the ALA iChatBio Agent?

The **ALA (Atlas of Living Australia) iChatBio Agent** is a conversational AI system that enables natural-language querying of Australian biodiversity data.  
Built on the **iChatBio framework** (Google A2A protocol), the agent interprets user questions, extracts parameters, resolves species names, and executes ALA API calls to produce accurate, human-friendly biodiversity insights.

## Key Features
- 🔍 **Natural language query processing**
- 🐾 **Species name resolution**  
  Converts common names → scientific names → LSIDs using ALA Name Matching API
- 🛠️ **7 specialized biodiversity tools**
- 🧠 **LLM-based research planning**  
  Priority system for must-call and optional tools
- ⚡ **Smart caching** for fast repeated queries
- 🧩 **Pydantic models** for all parameter validation
- 🗺️ **Artifact generation** (JSON, metadata, maps, images)

## Technology Stack
- **Framework:** iChatBio (Google A2A protocol)
- **LLM:** OpenAI GPT-4o-mini
- **Language:** Python 3.11+
- **APIs:** ALA REST APIs (occurrences, species, name matching)
- **Libraries:**  
  - openai  
  - instructor  
  - aiohttp  
  - pydantic v2  

## Purpose
The agent allows researchers, students, and biodiversity analysts to retrieve:
- species distribution maps  
- observation counts  
- occurrence breakdowns  
- occurrence records  
- taxonomy and species info  
- species images  

…all through natural language.