import asyncio
import json
from typing import Dict, Any
import requests

from ala_logic import ALA, OccurrenceSearchParams, SpeciesSearchParams, OccurrenceLookupParams, SpeciesLookupParams, NoParams, SpatialDistributionByLsidParams, SpatialDistributionByIdParams, SpatialDistributionMapParams, SpatialFieldByIdParams

class ALAiChatBioAgent:
    """The iChatBio agent implementation for ALA"""

    def __init__(self):
        self.ala_logic = ALA()

    async def run_occurrence_search(self, context, params: OccurrenceSearchParams):
        """Workflow for searching occurrences using the new context object."""
        async with context.begin_process("Searching for ALA occurrences") as process:
            await process.log("Extracted search parameters", data=params.model_dump(exclude_defaults=True))

            api_url = self.ala_logic.build_occurrence_url(params)
            await process.log(f"Constructed API URL: {api_url}")

            await process.log("Querying ALA for occurrence data...")
            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                
                total = raw_response.get('totalRecords', 0)
                returned = len(raw_response.get('occurrences', []))

                await process.log(f"Query successful, found {total} records.")
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Raw JSON for {returned} ALA records.",
                    uris=[api_url],
                    metadata={"record_count": returned, "total_matches": total}
                )
                
                # Reply to the assistant with a summary of the action taken.
                await context.reply(f"I have successfully searched for occurrences and found {total} matching records. I've created an artifact with the results.")

            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while trying to search for occurrences: {e}")

    async def run_occurrence_lookup(self, context, params: OccurrenceLookupParams):
        """Workflow for looking up a single occurrence record."""
        async with context.begin_process(f"Looking up occurrence record {params.uuid}") as process:
            api_url = self.ala_logic.build_occurrence_lookup_url(params)
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                
                scientific_name = raw_response.get('processed', {}).get('scientificName', 'Unknown Species')
                await process.log(f"Successfully found record for '{scientific_name}'.")
                
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Raw JSON for occurrence record {params.uuid}",
                    uris=[api_url],
                    metadata={"data_source": "ALA Occurrences", "uuid": params.uuid}
                )
                await context.reply(f"I have retrieved the details for the occurrence record of '{scientific_name}'.")

            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while looking up the occurrence record: {e}")

    async def run_get_index_fields(self, context, params: NoParams):
        """Workflow for getting all available index fields."""
        async with context.begin_process("Fetching all available ALA index fields") as process:
            api_url = self.ala_logic.build_index_fields_url()
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                field_count = len(raw_response)

                await process.log(f"Successfully found {field_count} indexed fields.")
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Raw JSON list of all {field_count} indexed fields.",
                    uris=[api_url],
                    metadata={"data_source": "ALA Index Fields", "field_count": field_count}
                )
                await context.reply(f"I have retrieved a list of all {field_count} searchable fields from the ALA.")
            
            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while fetching the index fields: {e}")

    async def run_species_lookup(self, context, params: SpeciesLookupParams):
        async with context.begin_process(f"Looking up species profile for '{params.name}'") as process:
            search_params = SpeciesSearchParams(q=f"taxon_name:\"{params.name}\"")
            api_url = self.ala_logic.build_species_search_url(search_params)
            await process.log("Requesting species profile via search...", data={"url": api_url})

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

                await process.log(f"Found matching profile for {scientific_name}.")
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Raw JSON from ALA Species Search for '{scientific_name}'.",
                    uris=[api_url],
                    metadata={"data_source": "ALA Species Search", "lsid": species_data.get('guid')}
                )
                await context.reply(f"I have successfully found a matching profile for {scientific_name}.{classification_text}")

            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while looking up the species profile: {e}")

    async def run_species_search(self, context, params: SpeciesSearchParams):
        """Workflow for faceted searching of species."""
        async with context.begin_process(f"Searching for species with query: '{params.q}'") as process:
            api_url = self.ala_logic.build_species_search_url(params)
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                
                results = raw_response.get('searchResults', {}).get('results', [])
                count = len(results)
                total_records = raw_response.get('searchResults', {}).get('totalRecords', 0)

                await process.log(f"Found {total_records} total matching species.")
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Raw JSON for {count} species matching query '{params.q}'.",
                    uris=[api_url],
                    metadata={"data_source": "ALA Species Search", "returned_records": count, "total_matches": total_records}
                )
                await context.reply(f"My search for species found {total_records} total matches. I've created an artifact with the first {count} results.")
            
            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while searching for species: {e}")
    
    
    async def run_list_distributions(self, context, params: NoParams):
        """Workflow to list available spatial layers/distributions to users"""
        async with context.begin_process("Listing expert distributions") as process:
            api_url = self.ala_logic.build_spatial_distributions_url()
            await process.log(f"Constructed API URL: {api_url}")
            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                count = len(raw_response)
                await process.log(f"Found {count} expert distributions.")
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Raw JSON for {count} expert distributions.",
                    uris=[api_url],
                    metadata={"distribution_count": count}
                )
                await context.reply(f"I found {count} expert distributions. See the artifact for details.")
            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"Error listing expert distributions: {e}")

    async def run_get_distribution_by_lsid(self, context, params: SpatialDistributionByLsidParams):
        async with context.begin_process(f"Getting distribution for LSID '{params.lsid}'") as process:
            api_url = self.ala_logic.build_spatial_distribution_by_lsid_url(params.lsid)
            await process.log(f"Constructed API URL: {api_url}")
            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                await process.log("Fetched distribution data.")
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Raw JSON for distribution of LSID {params.lsid}.",
                    uris=[api_url],
                    metadata={"lsid": params.lsid}
                )
                await context.reply(f"Fetched distribution data for LSID '{params.lsid}'.")
            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"Error fetching distribution for LSID '{params.lsid}': {e}")
 
    async def run_get_distribution_by_id(self, context, params: SpatialDistributionByIdParams):
        async with context.begin_process(f"Getting distribution for ID '{params.id}'") as process:
            api_url = self.ala_logic.build_spatial_distribution_by_id_url(params.id)
            await process.log(f"Constructed API URL: {api_url}")
            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                await process.log("Fetched distribution data.")
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Raw JSON for distribution with ID {params.id}.",
                    uris=[api_url],
                    metadata={"distribution_id": params.id}
                )
                await context.reply(f"Fetched distribution data for ID '{params.id}'.")
            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"Error fetching distribution for ID '{params.id}': {e}")
   
    async def run_get_distribution_map(self, context, params: SpatialDistributionMapParams):
        async with context.begin_process(f"Getting distribution map image for imageId '{params.imageId}'") as process:
            api_url = self.ala_logic.build_spatial_distribution_map_url(params.imageId)
            await process.log(f"Constructed API URL: {api_url}")
            try:
                # Note: This endpoint returns a PNG image, not JSON!
                response = self.ala_logic.session.get(api_url, timeout=30)
                response.raise_for_status()
                # Save or handle image bytes as needed, or just return the URL as an artifact
                await process.create_artifact(
                    mimetype="image/png",
                    description=f"PNG map image for imageId {params.imageId}.",
                    uris=[api_url],
                    metadata={"image_id": params.imageId}
                )
                await context.reply(f"Fetched PNG map image for imageId '{params.imageId}'.")
            except requests.exceptions.RequestException as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"Error fetching PNG map image for imageId '{params.imageId}': {e}")

    async def run_list_fieldsdb(self, context, params: NoParams):
        async with context.begin_process("Listing spatial fieldsdb") as process:
            api_url = self.ala_logic.build_spatial_fieldsdb_url()
            await process.log(f"Constructed API URL: {api_url}")
            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                count = len(raw_response)
                await process.log(f"Found {count} fields in fieldsdb.")
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Raw JSON for {count} fields in fieldsdb.",
                    uris=[api_url],
                    metadata={"fieldsdb_count": count}
                )
                await context.reply(f"I found {count} fields in the spatial fieldsdb. See the artifact for details.")
            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"Error listing fieldsdb: {e}")

    async def run_get_field_by_id(self, context, params: SpatialFieldByIdParams):
        async with context.begin_process(f"Getting spatial field for ID '{params.id}'") as process:
            api_url = self.ala_logic.build_spatial_field_by_id_url(params.id)
            await process.log(f"Constructed API URL: {api_url}")
            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                await process.log("Fetched field data.")
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Raw JSON for field with ID {params.id}.",
                    uris=[api_url],
                    metadata={"field_id": params.id}
                )
                await context.reply(f"Fetched field data for ID '{params.id}'.")
            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"Error fetching field for ID '{params.id}': {e}")