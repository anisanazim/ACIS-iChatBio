# agent_server.py
from pydantic import BaseModel
# --- FIX: Import only IChatBioAgent from ichatbio.agent ---
from ichatbio.agent import IChatBioAgent
from ichatbio.server import run_agent_server
from ichatbio.types import AgentCard, AgentEntrypoint

# Import your existing agent workflow and Pydantic models
from ala_ichatbio_agent import ALAiChatBioAgent
from ala_logic import OccurrenceSearchParams, SpeciesSearchParams, OccurrenceLookupParams, SpeciesLookupParams,NoParams,SpatialRegionListParams

# --- AgentCard definition remains the same, but ensure there are no syntax errors ---
card = AgentCard(
    name="Atlas of Living Australia Agent",
    description="Searches the Atlas of Living Australia for biodiversity records and species profiles.",
    icon="https://www.ala.org.au/wp-content/uploads/2018/06/logo-ALA-1-300x140.png",
    entrypoints=[
        AgentEntrypoint(
            id="search_occurrences",
            description="Search for species occurrence records in the ALA.",
            parameters=OccurrenceSearchParams
        ),
        AgentEntrypoint(
            id="search_species",
            description="Search for a list of species using faceted filters.",
            parameters=SpeciesSearchParams
        ),
        AgentEntrypoint(
            id="lookup_species",
            description="Get a profile for a single species from the ALA by name.",
            parameters=SpeciesLookupParams
        ),
        AgentEntrypoint(
            id="lookup_occurrence",
            description="Get a single occurrence record by its UUID.",
            parameters=OccurrenceLookupParams
        ),
        AgentEntrypoint(
            id="get_index_fields",
            description="Get a list of all searchable fields in the occurrence database.",
            parameters=NoParams
        ),

        AgentEntrypoint(
            id="list_regions",
            description="List all regions of a given type (e.g., STATE, IBRA, LGA).",
            parameters=SpatialRegionListParams
        ),
    ]
)

# --- Implement the iChatBio agent class with the new run signature ---
class ALAAgent(IChatBioAgent):
    def __init__(self):
        self.workflow_agent = ALAiChatBioAgent()

    def get_agent_card(self) -> AgentCard:
        """Returns the agent's metadata card."""
        return card

    async def run(self, context: "AgentContext", entrypoint_id: str, parameters: BaseModel):
        """Executes the requested agent entrypoint using the provided context."""
        
        if entrypoint_id == "search_occurrences":
            await self.workflow_agent.run_occurrence_search(context, parameters)
        elif entrypoint_id == "lookup_species":
            await self.workflow_agent.run_species_lookup(context, parameters)
        elif entrypoint_id == "search_species":
            await self.workflow_agent.run_species_search(context, parameters)
        elif entrypoint_id == "lookup_occurrence":
            await self.workflow_agent.run_occurrence_lookup(context, parameters)
        elif entrypoint_id == "get_index_fields":
            await self.workflow_agent.run_get_index_fields(context)
        elif entrypoint_id == "list_regions":
            await self.workflow_agent.run_list_regions(context, parameters)

        else:
            raise ValueError(f"Unsupported entrypoint ID: {entrypoint_id}")

if __name__ == "__main__":
    agent = ALAAgent()
    print(f"Starting iChatBio agent server for '{card.name}' at http://localhost:9999")
    run_agent_server(agent, host="0.0.0.0", port=9999)