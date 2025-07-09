# agent_server.py
from typing_extensions  import override
from pydantic import BaseModel
from ichatbio.agent import IChatBioAgent
from ichatbio.server import run_agent_server
from ichatbio.types import AgentCard, AgentEntrypoint

# Importing the existing agent workflow and Pydantic models
from ala_ichatbio_agent import ALAiChatBioAgent
from ala_logic import (
    OccurrenceSearchParams, OccurrenceLookupParams, OccurrenceFacetsParams, OccurrenceTaxaCountParams,
    SpeciesGuidLookupParams, SpeciesImageSearchParams, SpeciesBieSearchParams,
    NoParams, SpatialDistributionByLsidParams, SpatialDistributionMapParams,
    SpeciesListFilterParams, SpeciesListDetailsParams, 
    SpeciesListItemsParams, SpeciesListDistinctFieldParams, SpeciesListCommonKeysParams
)

# --- AgentCard definitions ---
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
            id="list_distributions",
            description="List all expert distributions available in the ALA spatial service.",
            parameters=NoParams
        ),
        AgentEntrypoint(
            id="get_distribution_by_lsid",
            description="Get expert distribution for a taxon by LSID.",
            parameters=SpatialDistributionByLsidParams
        ),
        AgentEntrypoint(
            id="get_distribution_map",
            description="Get PNG image for a distribution map by image ID.",
            parameters=SpatialDistributionMapParams
        ),
        AgentEntrypoint(
            id="get_occurrence_facets",
            description="Get data breakdowns and insights from occurrence records using facets.",
            parameters=OccurrenceFacetsParams
        ),
        AgentEntrypoint(
            id="get_occurrence_taxa_count",
            description="Get occurrence counts for specific taxa by their GUIDs/LSIDs.",
            parameters=OccurrenceTaxaCountParams
        ),
        AgentEntrypoint(
            id="species_guid_lookup",
            description="Look up a taxon GUID by name - essential for linking species to occurrence data.",
            parameters=SpeciesGuidLookupParams
        ),
        AgentEntrypoint(
            id="species_image_search", 
            description="Search for taxa with images available - visual species information.",
            parameters=SpeciesImageSearchParams
        ),
        AgentEntrypoint(
            id="species_bie_search",
            description="Search the Biodiversity Information Explorer (BIE) for species and taxa.",
            parameters=SpeciesBieSearchParams
        ),
        AgentEntrypoint(
            id="filter_species_lists",
            description="Filter species lists by scientific names or data resource IDs.",
            parameters=SpeciesListFilterParams
        ),
        AgentEntrypoint(
            id="get_species_list_details",
            description="Get detailed information about specific species lists.",
            parameters=SpeciesListDetailsParams
        ),
        AgentEntrypoint(
            id="get_species_list_items",
            description="Get species from specific lists with optional name filtering.",
            parameters=SpeciesListItemsParams
        ),
        AgentEntrypoint(
            id="get_species_list_distinct_fields",
            description="Get distinct values for a field across all species list items.",
            parameters=SpeciesListDistinctFieldParams
        ),
        AgentEntrypoint(
            id="get_species_list_common_keys",
            description="Get common keys (metadata) across multiple species lists.",
            parameters=SpeciesListCommonKeysParams
        ),
    ]
)

# --- Implement the iChatBio agent ---
class ALAAgent(IChatBioAgent):
    def __init__(self):
        self.workflow_agent = ALAiChatBioAgent()

    @override
    def get_agent_card(self) -> AgentCard:
        """Returns the agent's metadata card."""
        return card

    @override
    async def run(self, context: "AgentContext", entrypoint_id: str, parameters: BaseModel, request_text: str):
        """Executes the requested agent entrypoint using the provided context."""
        
        if entrypoint_id == "search_occurrences":
            await self.workflow_agent.run_occurrence_search(context, parameters)
        elif entrypoint_id == "lookup_species":
            await self.workflow_agent.run_species_lookup(context, parameters)
        elif entrypoint_id == "lookup_occurrence":
            await self.workflow_agent.run_occurrence_lookup(context, parameters)
        elif entrypoint_id == "get_index_fields":
            await self.workflow_agent.run_get_index_fields(context, parameters)
        elif entrypoint_id == "list_distributions":
            await self.workflow_agent.run_list_distributions(context, parameters)
        elif entrypoint_id == "get_distribution_by_lsid":
            await self.workflow_agent.run_get_distribution_by_lsid(context, parameters)
        elif entrypoint_id == "get_distribution_map":
            await self.workflow_agent.run_get_distribution_map(context, parameters)
        elif entrypoint_id == "get_occurrence_facets":
            await self.workflow_agent.run_get_occurrence_facets(context, parameters)
        elif entrypoint_id == "get_occurrence_taxa_count":
            await self.workflow_agent.run_get_occurrence_taxa_count(context, parameters)
        elif entrypoint_id == "species_guid_lookup":
            await self.workflow_agent.run_species_guid_lookup(context, parameters)
        elif entrypoint_id == "species_image_search":
            await self.workflow_agent.run_species_image_search(context, parameters)
        elif entrypoint_id == "species_bie_search":
            await self.workflow_agent.run_species_bie_search(context, parameters)
        elif entrypoint_id == "filter_species_lists":
            await self.workflow_agent.run_filter_species_lists(context, parameters)
        elif entrypoint_id == "get_species_list_details":
            await self.workflow_agent.run_get_species_list_details(context, parameters)
        elif entrypoint_id == "get_species_list_items":
            await self.workflow_agent.run_get_species_list_items(context, parameters)
        elif entrypoint_id == "get_species_list_distinct_fields":
            await self.workflow_agent.run_get_species_list_distinct_fields(context, parameters)
        elif entrypoint_id == "get_species_list_common_keys":
            await self.workflow_agent.run_get_species_list_common_keys(context, parameters)
        else:
            raise ValueError(f"Unsupported entrypoint ID: {entrypoint_id}")

if __name__ == "__main__":
    agent = ALAAgent()
    print(f"Starting iChatBio agent server for '{card.name}' at http://localhost:9999")
    run_agent_server(agent, host="0.0.0.0", port=9999)