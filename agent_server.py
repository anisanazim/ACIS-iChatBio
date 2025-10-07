# agent_server.py

from typing_extensions import override
from pydantic import BaseModel
from ichatbio.agent import IChatBioAgent
from ichatbio.agent_response import ResponseContext
from ichatbio.server import run_agent_server
from ichatbio.types import AgentCard, AgentEntrypoint

# Import the new unified agent and parameter model
from ala_ichatbio_agent import UnifiedALAReActAgent, UnifiedALAParams

# --- AgentCard definition with unified entrypoint ---
card = AgentCard(
    name="Unified Atlas of Living Australia Agent",
    description="Search Australian biodiversity data using natural language queries. Ask about species occurrences, distributions, images, and more.",
    icon="https://www.ala.org.au/wp-content/uploads/2018/06/logo-ALA-1-300x140.png",
    url="http://localhost:9999",
    entrypoints=[
        AgentEntrypoint(
            id="search_biodiversity_data",
            description="Search Australian biodiversity data using natural language. Ask about species occurrences, distributions, images, statistics, and more.",
            parameters=UnifiedALAParams
        )
    ]
)

# --- Implement the unified iChatBio agent class ---
class ALAAgent(UnifiedALAReActAgent):
    """Unified ALA Agent using LangChain ReAct pattern"""
    
    @override
    def get_agent_card(self) -> AgentCard:
        """Returns the agent's metadata card."""
        return card

if __name__ == "__main__":
    agent = ALAAgent()
    print(f"Starting unified iChatBio agent server for '{card.name}' at http://localhost:9999")
    run_agent_server(agent, host="0.0.0.0", port=9999)