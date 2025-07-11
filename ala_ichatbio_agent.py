import asyncio
import json
from typing import Dict, Any
import requests

from ala_logic import (
    ALA, 
    OccurrenceSearchParams, OccurrenceLookupParams, OccurrenceFacetsParams, OccurrenceTaxaCountParams,
    SpeciesGuidLookupParams, SpeciesImageSearchParams, SpeciesBieSearchParams,
    NoParams, SpatialDistributionByLsidParams, SpatialDistributionMapParams,
    SpeciesListFilterParams, SpeciesListDetailsParams, 
    SpeciesListItemsParams, SpeciesListDistinctFieldParams, SpeciesListCommonKeysParams
)
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
        async with context.begin_process(f"Looking up occurrence record {params.recordUuid}") as process:
            api_url = self.ala_logic.build_occurrence_lookup_url(params)
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                
                scientific_name = raw_response.get('processed', {}).get('scientificName', 'Unknown Species')
                await process.log(f"Successfully found record for '{scientific_name}'.")
                
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Raw JSON for occurrence record {params.recordUuid}",
                    uris=[api_url],
                    metadata={"data_source": "ALA Occurrences", "uuid": params.recordUuid}
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

    async def run_get_distribution_map(self, context, params: SpatialDistributionMapParams):
        async with context.begin_process(f"Getting distribution map image for imageId '{params.imageId}'") as process:
            api_url = self.ala_logic.build_spatial_distribution_map_url(params.imageId)
            await process.log(f"Constructed API URL: {api_url}")
            try:
                loop = asyncio.get_event_loop()
                image_data = await loop.run_in_executor(None, lambda: self.ala_logic.execute_image_request(api_url))
                
                await process.create_artifact(
                    mimetype="image/png",
                    description=f"PNG map image for imageId {params.imageId}.",
                    uris=[api_url],
                    metadata={"image_id": params.imageId, "size_bytes": len(image_data)}
                )
                await context.reply(f"Fetched PNG map image for imageId '{params.imageId}'.")
            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"Error fetching PNG map image for imageId '{params.imageId}': {e}")

    async def run_get_occurrence_facets(self, context, params: OccurrenceFacetsParams):
        
        """Workflow for getting occurrence facet information - data breakdowns and insights"""
        query_description = []
        if params.q:
            query_description.append(f"query: '{params.q}'")
        if params.fq:
            query_description.append(f"filters: {', '.join(params.fq)}")
        if params.facets:
            query_description.append(f"facets: {', '.join(params.facets)}")
        
        search_context = " with " + ", ".join(query_description) if query_description else " for all occurrence data"
        
        async with context.begin_process(f"Getting occurrence data breakdowns{search_context}") as process:
            await process.log("Facet search parameters", data=params.model_dump(exclude_defaults=True))

            api_url = self.ala_logic.build_occurrence_facets_url(params)
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                
                await process.log("Successfully retrieved facet data.")
                
                # Extract key insights from facet response
                facet_fields = []
                total_facets = 0
                
                if isinstance(raw_response, dict):
                    facet_results = raw_response.get('facetResults', [])
                    for facet in facet_results:
                        field_name = facet.get('fieldName', 'Unknown')
                        field_result = facet.get('fieldResult', [])
                        facet_count = len(field_result)
                        facet_fields.append(f"{field_name} ({facet_count} values)")
                        total_facets += facet_count
                
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Occurrence facet data breakdown - {total_facets} total facet values across {len(facet_fields)} fields",
                    uris=[api_url],
                    metadata={
                        "data_source": "ALA Occurrence Facets", 
                        "facet_fields": len(facet_fields),
                        "total_facet_values": total_facets,
                        "search_context": search_context.strip()
                    }
                )
                
                if facet_fields:
                    summary = f"Retrieved data breakdown with {total_facets} facet values across {len(facet_fields)} categories: {', '.join(facet_fields[:3])}"
                    if len(facet_fields) > 3:
                        summary += f" and {len(facet_fields) - 3} more"
                    summary += "."
                else:
                    summary = "Retrieved facet data breakdown from the occurrence database."
                
                await context.reply(summary)

            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while retrieving occurrence facet data: {e}")

    async def run_get_occurrence_taxa_count(self, context, params: OccurrenceTaxaCountParams):
        """Workflow for getting occurrence counts for specific taxa"""
        
        # Parse the GUIDs to understand what we're counting
        guid_list = params.guids.replace('\n', params.separator).split(params.separator)
        guid_count = len([g for g in guid_list if g.strip()])
        
        # Build description
        filter_description = ""
        if params.fq:
            filter_description = f" with filters: {', '.join(params.fq)}"
        
        async with context.begin_process(f"Counting occurrences for {guid_count} taxa{filter_description}") as process:
            await process.log("Taxa count parameters", data=params.model_dump(exclude_defaults=True))
            await process.log(f"Analyzing {guid_count} taxa GUIDs")

            api_url = self.ala_logic.build_occurrence_taxa_count_url(params)
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                
                await process.log("Successfully retrieved taxa count data.")
                
                # Parse the response to extract meaningful information
                total_occurrences = 0
                taxa_with_records = 0
                sample_results = []
                
                if isinstance(raw_response, dict):
                    for guid, count in raw_response.items():
                        if isinstance(count, (int, float)) and count > 0:
                            taxa_with_records += 1
                            total_occurrences += int(count)
                            sample_results.append(f"{guid}: {count:,} records")
                
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Taxa occurrence counts for {guid_count} taxa - {total_occurrences:,} total occurrences",
                    uris=[api_url],
                    metadata={
                        "data_source": "ALA Occurrence Taxa Count",
                        "taxa_requested": guid_count,
                        "taxa_with_records": taxa_with_records,
                        "total_occurrences": total_occurrences,
                        "filter_applied": filter_description.strip()
                    }
                )
                
                # Create user-friendly summary
                if taxa_with_records > 0:
                    summary = f"Found occurrence counts for {taxa_with_records} out of {guid_count} taxa, totaling {total_occurrences:,} occurrence records"
                    if filter_description:
                        summary += filter_description
                    summary += "."
                    
                    # Add sample of results if we have them
                    if sample_results and len(sample_results) <= 3:
                        summary += f" Results: {', '.join(sample_results)}."
                    elif sample_results:
                        summary += f" Sample results: {', '.join(sample_results[:2])} and {len(sample_results)-2} more."
                else:
                    summary = f"No occurrence records found for the {guid_count} taxa provided"
                    if filter_description:
                        summary += filter_description
                    summary += "."
                
                await context.reply(summary)

            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while retrieving taxa occurrence counts: {e}")

    async def run_species_guid_lookup(self, context, params: SpeciesGuidLookupParams):
        """Workflow for looking up a taxon GUID by name - critical for linking to occurrence data"""
        async with context.begin_process(f"Looking up GUID for '{params.name}'") as process:
            await process.log("GUID lookup parameters", data=params.model_dump())

            api_url = self.ala_logic.build_species_guid_lookup_url(params)
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                
                await process.log("Successfully retrieved GUID data.")
                
                # Extract meaningful information from the response
                matches_found = 0
                sample_matches = []
                guids = []
                
                if isinstance(raw_response, list):
                    matches_found = len(raw_response)
                    for item in raw_response[:3]:  # First 3 matches
                        if isinstance(item, dict):
                            name = item.get('name', item.get('acceptedName', 'Unknown'))
                            identifier = item.get('identifier', item.get('guid', ''))
                            sample_matches.append(f"{name}")
                            if identifier:
                                guids.append(identifier)
                
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"GUID lookup results for '{params.name}' - {matches_found} matches found",
                    uris=[api_url],
                    metadata={
                        "data_source": "ALA Species GUID Lookup",
                        "search_term": params.name,
                        "matches_found": matches_found,
                        "guids": guids[:3]  # Store first few GUIDs for reference
                    }
                )
                
                # Create user-friendly response
                if matches_found > 0:
                    if matches_found == 1:
                        summary = f"Found GUID for '{params.name}': {sample_matches[0] if sample_matches else 'match found'}"
                    else:
                        summary = f"Found {matches_found} GUID matches for '{params.name}'"
                        if sample_matches:
                            summary += f": {', '.join(sample_matches)}"
                            if matches_found > 3:
                                summary += f" and {matches_found - 3} more"
                    summary += "."
                else:
                    summary = f"No GUID matches found for '{params.name}'. Try checking the spelling or using a different name format."
                
                await context.reply(summary)

            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while looking up the GUID for '{params.name}': {e}")
               
    async def run_species_image_search(self, context, params: SpeciesImageSearchParams):
            """Workflow for searching taxa with images - visual species information"""
            async with context.begin_process(f"Searching for images of taxon ID '{params.id}'") as process:
                await process.log("Image search parameters", data=params.model_dump())

                api_url = self.ala_logic.build_species_image_search_url(params)
                await process.log(f"Constructed API URL: {api_url}")

                try:
                    loop = asyncio.get_event_loop()
                    raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                    
                    await process.log("Successfully retrieved image search data.")
                    
                    # Extract information from the response - handle different structures
                    total_records = 0
                    results_count = 0
                    facet_results = []
                    
                    if isinstance(raw_response, dict):
                        # Check if it has searchResults structure
                        if 'searchResults' in raw_response:
                            search_results = raw_response.get('searchResults', {})
                            if isinstance(search_results, dict):
                                total_records = search_results.get('totalRecords', 0)
                                results = search_results.get('results', [])
                                results_count = len(results)
                            else:
                                # searchResults is a list
                                results_count = len(search_results)
                                total_records = results_count
                        else:
                            # Direct structure
                            total_records = raw_response.get('totalRecords', 0)
                            results = raw_response.get('results', [])
                            results_count = len(results)
                        
                        # Extract facet information if available
                        facet_results = raw_response.get('facetResults', [])
                    elif isinstance(raw_response, list):
                        # Response is directly a list
                        results_count = len(raw_response)
                        total_records = results_count
                    
                    await process.create_artifact(
                        mimetype="application/json",
                        description=f"Image search results for taxon '{params.id}' - {results_count} results from {total_records} total",
                        uris=[api_url],
                        metadata={
                            "data_source": "ALA Species Image Search",
                            "taxon_id": params.id,
                            "results_returned": results_count,
                            "total_records": total_records,
                            "has_facets": len(facet_results) > 0
                        }
                    )
                    
                    # Create user-friendly response
                    if total_records > 0:
                        summary = f"Found {total_records} taxa with images"
                        if results_count != total_records:
                            summary += f" (showing first {results_count})"
                        summary += f" for the specified taxon."
                    else:
                        summary = f"No taxa with images found for the specified taxon ID."
                    
                    await context.reply(summary)

                except ConnectionError as e:
                    await process.log("Error during API request", data={"error": str(e)})
                    await context.reply(f"I encountered an error while searching for images: {e}")

    async def run_species_bie_search(self, context, params: SpeciesBieSearchParams):
        """Workflow for searching the Biodiversity Information Explorer (BIE)"""
        filter_description = f" with filter '{params.fq}'" if params.fq else ""
        
        async with context.begin_process(f"Searching BIE for '{params.q}'{filter_description}") as process:
            await process.log("BIE search parameters", data=params.model_dump())

            api_url = self.ala_logic.build_species_bie_search_url(params)
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                
                await process.log("Successfully retrieved BIE search data.")
                
                # Extract information from the response
                total_records = 0
                results_count = 0
                sample_results = []
                
                if isinstance(raw_response, dict):
                    search_results = raw_response.get('searchResults', {})
                    total_records = search_results.get('totalRecords', 0)
                    results = search_results.get('results', [])
                    results_count = len(results)
                    
                    # Extract sample results
                    for result in results[:3]:
                        if isinstance(result, dict):
                            name = result.get('name', result.get('scientificName', 'Unknown'))
                            common_name = result.get('commonNameSingle', '')
                            if common_name:
                                sample_results.append(f"{name} ({common_name})")
                            else:
                                sample_results.append(name)
                
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"BIE search results for '{params.q}' - {results_count} results from {total_records} total",
                    uris=[api_url],
                    metadata={
                        "data_source": "ALA BIE Search",
                        "search_query": params.q,
                        "filter_applied": params.fq,
                        "results_returned": results_count,
                        "total_records": total_records
                    }
                )
                
                # Create user-friendly response
                if total_records > 0:
                    summary = f"Found {total_records} results in the BIE"
                    if results_count != total_records:
                        summary += f" (showing first {results_count})"
                    if sample_results:
                        summary += f". Sample results: {', '.join(sample_results)}"
                        if results_count > 3:
                            summary += f" and {results_count - 3} more"
                    summary += "."
                else:
                    summary = f"No results found in the BIE for '{params.q}'{filter_description}."
                
                await context.reply(summary)

            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while searching the BIE: {e}")

    async def run_filter_species_lists(self, context, params: SpeciesListFilterParams):
        """Workflow for filtering species lists by scientific names or data resource IDs"""
        filter_description = []
        if params.scientific_names:
            filter_description.append(f"scientific names: {', '.join(params.scientific_names)}")
        if params.dr_ids:
            filter_description.append(f"data resource IDs: {', '.join(params.dr_ids)}")
        
        filter_text = " and ".join(filter_description)
        
        async with context.begin_process(f"Filtering species lists by {filter_text}") as process:
            await process.log("Filter parameters", data=params.model_dump(exclude_defaults=True))

            try:
                url, request_body = self.ala_logic.build_species_list_filter_url(params)
                await process.log(f"Constructed API URL: {url}")
                await process.log("Request body", data=request_body)

                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_post_request(url, request_body))
                
                # Handle response structure
                if isinstance(raw_response, list):
                    lists = raw_response
                    total = len(lists)
                else:
                    lists = raw_response.get('lists', raw_response.get('results', []))
                    total = raw_response.get('totalRecords', len(lists))

                returned = len(lists)
                await process.log(f"Filter successful, found {total} matching species lists.")
                
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Filtered species lists - {returned} results",
                    uris=[url],
                    metadata={"list_count": returned, "total_matches": total, "filter_criteria": filter_text}
                )
                
                await context.reply(f"Found {total} species lists matching your filter criteria. I've created an artifact with the results.")

            except ValueError as ve:
                await context.reply(f"Filter error: {ve}")
            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while filtering species lists: {e}")

    async def run_get_species_list_details(self, context, params: SpeciesListDetailsParams):
        """Workflow for getting detailed information about a specific species list"""
        async with context.begin_process(f"Getting details for species list {params.druid}") as process:
            api_url = self.ala_logic.build_species_list_details_url(params)
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                
                # Handle both single list and multiple lists responses
                if isinstance(raw_response, list):
                    lists = raw_response
                    list_count = len(lists)
                    if lists:
                        list_name = lists[0].get('listName', lists[0].get('title', 'Unknown List'))
                        total_items = sum(lst.get('itemCount', 0) for lst in lists)
                    else:
                        list_name = "No Lists Found"
                        total_items = 0
                else:
                    lists = [raw_response]
                    list_count = 1
                    list_name = raw_response.get('listName', raw_response.get('title', 'Unknown List'))
                    total_items = raw_response.get('itemCount', 0)
                
                await process.log(f"Successfully retrieved details for {list_count} list(s).")
                
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Species list details: {list_name}" + (f" ({list_count} lists)" if list_count > 1 else ""),
                    uris=[api_url],
                    metadata={"data_source": "ALA Species List", "druid": params.druid, "list_count": list_count, "total_items": total_items}
                )
                
                if list_count == 1:
                    await context.reply(f"Retrieved details for '{list_name}' containing {total_items} species.")
                else:
                    await context.reply(f"Retrieved details for {list_count} species lists containing a total of {total_items} species.")

            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while retrieving the species list details: {e}")

    async def run_get_species_list_items(self, context, params: SpeciesListItemsParams):
        """Workflow for getting species within specific lists with optional filtering"""
        query_description = f"list(s) {params.druid}"
        if params.q:
            query_description += f" searching for '{params.q}'"
        
        async with context.begin_process(f"Getting species from {query_description}") as process:
            api_url = self.ala_logic.build_species_list_items_url(params)
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                
                # Handle different response structures
                if isinstance(raw_response, list):
                    items = raw_response
                    total = len(items)
                else:
                    items = raw_response.get('items', raw_response.get('results', []))
                    total = raw_response.get('totalRecords', len(items))
                
                returned = len(items)
                await process.log(f"Successfully retrieved {returned} species from the list(s).")
                
                # Extract sample species names for the reply
                sample_species = []
                for item in items[:3]:  # First 3 species
                    if isinstance(item, dict):
                        name = item.get('name', item.get('scientificName', item.get('rawScientificName', 'Unknown')))
                        common_name = item.get('commonName', '')
                        if common_name:
                            sample_species.append(f"{name} ({common_name})")
                        else:
                            sample_species.append(name)
                
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Species from list(s) {params.druid}" + (f" matching '{params.q}'" if params.q else "") + f" - {returned} items",
                    uris=[api_url],
                    metadata={"data_source": "ALA Species List Items", "druid": params.druid, "returned_count": returned, "total_count": total, "search_query": params.q}
                )
                
                reply = f"Retrieved {returned} species from the list(s)"
                if total > returned:
                    reply += f" (showing first {returned} of {total} total)"
                if params.q:
                    reply += f" matching '{params.q}'"
                if sample_species:
                    reply += f". Sample species: {', '.join(sample_species)}"
                reply += "."
                
                await context.reply(reply)

            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while retrieving species from the list: {e}")

    async def run_get_species_list_distinct_fields(self, context, params: SpeciesListDistinctFieldParams):
        """Workflow for getting distinct values for a field across species list items"""
        async with context.begin_process(f"Getting distinct values for field '{params.field}' across all species lists") as process:
            api_url = self.ala_logic.build_species_list_distinct_field_url(params)
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                
                # Handle response structure
                if isinstance(raw_response, list):
                    distinct_values = raw_response
                else:
                    distinct_values = raw_response.get('values', raw_response.get('results', []))
                
                value_count = len(distinct_values)
                await process.log(f"Found {value_count} distinct values for field '{params.field}'.")
                
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Distinct values for field '{params.field}' - {value_count} unique values",
                    uris=[api_url],
                    metadata={"data_source": "ALA Species List Distinct Fields", "field": params.field, "value_count": value_count}
                )
                
                sample_values = distinct_values[:5] if distinct_values else []
                reply = f"Found {value_count} distinct values for field '{params.field}'"
                if sample_values:
                    reply += f". Sample values: {', '.join(str(v) for v in sample_values)}"
                reply += "."
                
                await context.reply(reply)

            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while retrieving distinct field values: {e}")

    async def run_get_species_list_common_keys(self, context, params: SpeciesListCommonKeysParams):
        """Workflow for getting common keys (KVP) across multiple species lists"""
        async with context.begin_process(f"Getting common keys across species lists: {params.druid}") as process:
            api_url = self.ala_logic.build_species_list_common_keys_url(params)
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
                
                # Handle response structure
                if isinstance(raw_response, list):
                    common_keys = raw_response
                else:
                    common_keys = raw_response.get('keys', raw_response.get('results', []))
                
                key_count = len(common_keys)
                await process.log(f"Found {key_count} common keys across the specified lists.")
                
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Common keys across species lists {params.druid} - {key_count} keys",
                    uris=[api_url],
                    metadata={"data_source": "ALA Species List Common Keys", "druid": params.druid, "key_count": key_count}
                )
                
                await context.reply(f"Found {key_count} common keys across the specified species lists. These keys can be used for additional data analysis.")

            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while retrieving common keys: {e}")
