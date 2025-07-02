import asyncio
import json
from typing import Dict, Any

from ala_logic import ALA, OccurrenceSearchParams, SpeciesSearchParams, OccurrenceLookupParams, SpeciesLookupParams, NoParams, SpatialRegionListParams

class ALAiChatBioAgent:
    """The iChatBio agent implementation for ALA"""

    def __init__(self):
        self.ala_logic = ALA()

    async def run_occurrence_search(self, context, params: OccurrenceSearchParams):
        """Workflow for searching occurrences using the new context object."""
        with context.begin_process("Searching for ALA occurrences") as process:
            process.log("Extracted search parameters", data=params.model_dump(exclude_defaults=True))

            api_url = self.ala_logic.build_occurrence_url(params)
            process.log(f"Constructed API URL: {api_url}")

            process.log("Querying ALA for occurrence data...")
            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                
                total = raw_response.get('totalRecords', 0)
                returned = len(raw_response.get('occurrences', []))

                process.log(f"Query successful, found {total} records.")
                process.create_artifact(
                    mimetype="application/json",
                    description=f"Raw JSON for {returned} ALA records.",
                    uris=[api_url],
                    metadata={"record_count": returned, "total_matches": total}
                )
                
                # Reply to the assistant with a summary of the action taken.
                context.reply(f"I have successfully searched for occurrences and found {total} matching records. I've created an artifact with the results.")

            except ConnectionError as e:
                process.log("Error during API request", data={"error": str(e)})
                context.reply(f"I encountered an error while trying to search for occurrences: {e}")

    async def run_occurrence_lookup(self, context, params: OccurrenceLookupParams):
        """Workflow for looking up a single occurrence record."""
        with context.begin_process(f"Looking up occurrence record {params.uuid}") as process:
            api_url = self.ala_logic.build_occurrence_lookup_url(params)
            process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                
                scientific_name = raw_response.get('processed', {}).get('scientificName', 'Unknown Species')
                process.log(f"Successfully found record for '{scientific_name}'.")
                
                process.create_artifact(
                    mimetype="application/json",
                    description=f"Raw JSON for occurrence record {params.uuid}",
                    uris=[api_url],
                    metadata={"data_source": "ALA Occurrences", "uuid": params.uuid}
                )
                context.reply(f"I have retrieved the details for the occurrence record of '{scientific_name}'.")

            except ConnectionError as e:
                process.log("Error during API request", data={"error": str(e)})
                context.reply(f"I encountered an error while looking up the occurrence record: {e}")

    async def run_get_index_fields(self, context, params: NoParams):
        """Workflow for getting all available index fields."""
        with context.begin_process("Fetching all available ALA index fields") as process:
            api_url = self.ala_logic.build_index_fields_url()
            process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                field_count = len(raw_response)

                process.log(f"Successfully found {field_count} indexed fields.")
                process.create_artifact(
                    mimetype="application/json",
                    description=f"Raw JSON list of all {field_count} indexed fields.",
                    uris=[api_url],
                    metadata={"data_source": "ALA Index Fields", "field_count": field_count}
                )
                context.reply(f"I have retrieved a list of all {field_count} searchable fields from the ALA.")
            
            except ConnectionError as e:
                process.log("Error during API request", data={"error": str(e)})
                context.reply(f"I encountered an error while fetching the index fields: {e}")

    async def run_species_lookup(self, context, params: SpeciesLookupParams):
        with context.begin_process(f"Looking up species profile for '{params.name}'") as process:
            search_params = SpeciesSearchParams(q=f"taxon_name:\"{params.name}\"")
            api_url = self.ala_logic.build_species_search_url(search_params)
            process.log("Requesting species profile via search...", data={"url": api_url})

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                results = raw_response.get('searchResults', {}).get('results', [])

                if not results:
                    context.reply(f"I could not find a species profile for '{params.name}'.")
                    return

                species_data = results[0]
                scientific_name = species_data.get('name', 'Unknown Species')

                # --- Extract and format the classification ---
                classification_list = species_data.get('classification', [])
                if classification_list and isinstance(classification_list, list):
                    classification_path = " -> ".join(
                        rank.get('name', '') for rank in classification_list if isinstance(rank, dict)
                    )
                    classification_text = f"\nFull Classification: {classification_path}"
                else:
                    classification_text = "\nFull Classification: [Not available in ALA for this species. This may occur for some common names or recently updated taxa.]"

                process.log(f"Found matching profile for {scientific_name}.")
                process.create_artifact(
                    mimetype="application/json",
                    description=f"Raw JSON from ALA Species Search for '{scientific_name}'.",
                    uris=[api_url],
                    metadata={"data_source": "ALA Species Search", "lsid": species_data.get('guid')}
                )
                context.reply(f"I have successfully found a matching profile for {scientific_name}.{classification_text}")

            except ConnectionError as e:
                process.log("Error during API request", data={"error": str(e)})
                context.reply(f"I encountered an error while looking up the species profile: {e}")

    async def run_species_search(self, context, params: SpeciesSearchParams):
        """Workflow for faceted searching of species."""
        with context.begin_process(f"Searching for species with query: '{params.q}'") as process:
            api_url = self.ala_logic.build_species_search_url(params)
            process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                
                results = raw_response.get('searchResults', {}).get('results', [])
                count = len(results)
                total_records = raw_response.get('searchResults', {}).get('totalRecords', 0)

                process.log(f"Found {total_records} total matching species.")
                process.create_artifact(
                    mimetype="application/json",
                    description=f"Raw JSON for {count} species matching query '{params.q}'.",
                    uris=[api_url],
                    metadata={"data_source": "ALA Species Search", "returned_records": count, "total_matches": total_records}
                )
                context.reply(f"My search for species found {total_records} total matches. I've created an artifact with the first {count} results.")
            
            except ConnectionError as e:
                process.log("Error during API request", data={"error": str(e)})
                context.reply(f"I encountered an error while searching for species: {e}")
    
    
    async def run_list_regions(self, context, params: SpatialRegionListParams):
        with context.begin_process(f"Listing regions of type '{params.type}'") as process:
            api_url = self.ala_logic.build_spatial_regions_url(params)
            process.log(f"Constructed API URL: {api_url}")
            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                region_count = len(raw_response)
                process.log(f"Found {region_count} regions.")
                process.create_artifact(
                    mimetype="application/json",
                    description=f"Raw JSON for {region_count} regions of type {params.type}.",
                    uris=[api_url],
                    metadata={"region_type": params.type, "region_count": region_count}
                )
                context.reply(f"I found {region_count} regions of type '{params.type}'. See the artifact for details.")
            except ConnectionError as e:
                process.log("Error during API request", data={"error": str(e)})
                context.reply(f"Error listing regions: {e}")
