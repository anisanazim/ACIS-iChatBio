from ichatbio.types import AgentCard, AgentEntrypoint, Message, TextMessage, ProcessMessage, ArtifactMessage
from ichatbio.agent import IChatBioAgent
from ichatbio.server import run_agent_server
from pydantic import BaseModel 
from typing import AsyncIterator 
from ala_ichatbio_agent import ALAiChatBioAgent
from ala_logic import OccurrenceSearchParams, SpeciesSearchParams, OccurrenceLookupParams, SpeciesLookupParams

# Define the AgentCard (metadata and entrypoints)
# This tells the iChatBio platform what ALA agent is, and what it can do.
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
            description="Get a list of all searchable fields in the occurrence database."
        )
    ] 
)

# Implement  iChatBio agent class
# This class acts as the bridge between the iChatBio SDK and your custom agent logic.
class ALAAgent(IChatBioAgent):
    def __init__(self):
        # Instantiating custom agent logic
        self.workflow_agent = ALAiChatBioAgent()

    def get_agent_card(self) -> AgentCard:
        """Returns the agent's metadata card."""
        return card

    # run() receives the `entrypoint_id` and the already-parsed `parameters`.
    async def run(self, entrypoint_id: str, parameters: BaseModel) -> AsyncIterator[Message]:
        """
        Executes the requested agent entrypoint.
        Yields messages back to the iChatBio platform.
        """
        user_query_str = f"User asked for {entrypoint_id} with parameters: {parameters.model_dump_json()}"

        if entrypoint_id == "search_occurrences":
            async for message in self.workflow_agent.run_occurrence_search(user_query_str):
                yield message
        elif entrypoint_id == "lookup_species":
            async for message in self.workflow_agent.run_species_lookup(parameters.name):
                 yield message
        elif entrypoint_id == "search_species":
            async for message in self.workflow_agent.run_species_search(parameters):
                 yield message
        elif entrypoint_id == "lookup_occurrence":
            async for message in self.workflow_agent.run_occurrence_lookup(parameters):
                yield message
        elif entrypoint_id == "get_index_fields":
            async for message in self.workflow_agent.run_get_index_fields():
                yield message
        else:
            raise ValueError(f"Unsupported entrypoint ID: {entrypoint_id}")

if __name__ == "__main__":
    agent = ALAAgent()
    print(f"Starting iChatBio agent server for '{card.name}' at http://localhost:9999")
    # This function from the SDK starts the actual web server
    run_agent_server(agent, host="0.0.0.0", port=9999)