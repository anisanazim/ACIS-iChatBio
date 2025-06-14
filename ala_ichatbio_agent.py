from ichatbio.types import AgentCard, AgentEntrypoint
from ichatbio.agent import IChatBioAgent
from ichatbio.types import TextMessage, ProcessMessage
from ichatbio.server import run_agent_server

# Importing existing models and logic from ala_agent.py
from ala_agent import OccurrenceSearchParams, ALA

# 1. Define the agent card (metadata and entrypoints)
card = AgentCard(
    name="ALA Search Agent",
    description="Searches the Atlas of Living Australia for biodiversity records.",
    icon="https://ala.org.au/icon.png",  # You can use your own icon URL
    entrypoints=[
        AgentEntrypoint(
            id="search",
            description="Search for occurrences in ALA.",
            parameters=OccurrenceSearchParams
        )
    ]
)

# 2. Implement the iChatBio agent class
class ALASearchAgent(IChatBioAgent):
    def get_agent_card(self):
        return card

    async def run(self, request: str, entrypoint: str, params: OccurrenceSearchParams):
        if entrypoint != "search":
            raise ValueError("Unsupported entrypoint")
        yield ProcessMessage(summary="Searching ALA", description="Running occurrence search")

        # Use your existing ALA logic
        ala = ALA()
        # params is already validated OccurrenceSearchParams
        api_url = ala.build_api_url(params)
        raw_response = ala.execute_search(api_url)
        formatted = ala.format_search_results(raw_response, params, api_url)
        summary = ala.create_display_summary(formatted)
        yield TextMessage(summary)

# 3. Run the agent server
if __name__ == "__main__":
    agent = ALASearchAgent()
    run_agent_server(agent, host="0.0.0.0", port=9999)