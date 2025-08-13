import asyncio
import json
from typing import Dict, Any
import requests

from ala_logic import (
    ALA, 
    OccurrenceSearchParams, OccurrenceLookupParams, OccurrenceFacetsParams, OccurrenceTaxaCountParams, TaxaCountHelper,
    SpeciesGuidLookupParams, SpeciesImageSearchParams, SpeciesBieSearchParams,
    NoParams, SpatialDistributionByLsidParams, SpatialDistributionMapParams,
    SpeciesListFilterParams, SpeciesListDetailsParams, 
    SpeciesListItemsParams, SpeciesListDistinctFieldParams, SpeciesListCommonKeysParams
)
class ALAiChatBioAgent:
    """The iChatBio agent implementation for ALA"""

    def __init__(self):
        self.ala_logic = ALA()
    
    async def extract_occurrence_search_params(self, user_request: str) -> OccurrenceSearchParams:
        """Extract occurrence search parameters from natural language."""
        return await self.ala_logic._extract_params(user_request, OccurrenceSearchParams)

    async def extract_species_image_search_params(self, user_request: str) -> SpeciesImageSearchParams:
        """Extract image search parameters from natural language."""
        return await self.ala_logic._extract_params(user_request, SpeciesImageSearchParams)

    async def extract_species_bie_search_params(self, user_request: str) -> SpeciesBieSearchParams:
        """Extract BIE search parameters from natural language."""
        return await self.ala_logic._extract_params(user_request, SpeciesBieSearchParams)

    async def extract_occurrence_lookup_params(self, user_request: str) -> OccurrenceLookupParams:
        """Extract occurrence lookup parameters from natural language."""
        return await self.ala_logic._extract_params(user_request, OccurrenceLookupParams)

    async def extract_species_guid_lookup_params(self, user_request: str) -> SpeciesGuidLookupParams:
        """Extract GUID lookup parameters from natural language."""
        return await self.ala_logic._extract_params(user_request, SpeciesGuidLookupParams)
    
    # Facets and analysis
    async def extract_occurrence_facets_params(self, user_request: str) -> OccurrenceFacetsParams:
        """Extract occurrence facets parameters from natural language."""
        return await self.ala_logic._extract_params(user_request, OccurrenceFacetsParams)

    async def extract_occurrence_taxa_count_params(self, user_request: str) -> OccurrenceTaxaCountParams:
        """Extract taxa count parameters from natural language."""
        return await self.ala_logic._extract_params(user_request, OccurrenceTaxaCountParams)

    async def extract_taxa_count_helper_params(self, user_request: str) -> TaxaCountHelper:
        """Extract user-friendly taxa count parameters from natural language."""
        return await self.ala_logic._extract_params(user_request, TaxaCountHelper)

    # Spatial distribution
    async def extract_spatial_distribution_by_lsid_params(self, user_request: str) -> SpatialDistributionByLsidParams:
        """Extract spatial distribution LSID parameters from natural language."""
        return await self.ala_logic._extract_params(user_request, SpatialDistributionByLsidParams)

    async def extract_spatial_distribution_map_params(self, user_request: str) -> SpatialDistributionMapParams:
        """Extract distribution map parameters from natural language."""
        return await self.ala_logic._extract_params(user_request, SpatialDistributionMapParams)

    # Species lists
    async def extract_species_list_filter_params(self, user_request: str) -> SpeciesListFilterParams:
        """Extract species list filter parameters from natural language."""
        return await self.ala_logic._extract_params(user_request, SpeciesListFilterParams)

    async def extract_species_list_details_params(self, user_request: str) -> SpeciesListDetailsParams:
        """Extract species list details parameters from natural language."""
        return await self.ala_logic._extract_params(user_request, SpeciesListDetailsParams)

    async def extract_species_list_items_params(self, user_request: str) -> SpeciesListItemsParams:
        """Extract species list items parameters from natural language."""
        return await self.ala_logic._extract_params(user_request, SpeciesListItemsParams)

    async def extract_species_list_distinct_field_params(self, user_request: str) -> SpeciesListDistinctFieldParams:
        """Extract distinct field parameters from natural language."""
        return await self.ala_logic._extract_params(user_request, SpeciesListDistinctFieldParams)

    async def extract_species_list_common_keys_params(self, user_request: str) -> SpeciesListCommonKeysParams:
        """Extract common keys parameters from natural language."""
        return await self.ala_logic._extract_params(user_request, SpeciesListCommonKeysParams)

    # No parameters (for endpoints that don't need extraction)
    async def extract_no_params(self, user_request: str) -> NoParams:
        """Handle endpoints with no parameters."""
        return NoParams()

    async def run_occurrence_search(self, context, request: str): 
        """Workflow for searching occurrences using dynamic parameter extraction."""
        try:
            extracted_params = await self.extract_occurrence_search_params(request)
        except ValueError as e:
            await context.reply(f"I couldn't understand your search request: {e}")
            return
        
        async with context.begin_process("Searching for ALA occurrences") as process:
            await process.log("Extracted search parameters", data=extracted_params.model_dump(exclude_defaults=True))
            api_url = self.ala_logic.build_occurrence_url(extracted_params)
            await process.log(f"Constructed API URL: {api_url}")

            await process.log("Querying ALA for occurrence data...")
            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_get_request(api_url))
                
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


    async def run_occurrence_lookup(self, context, request: str):
        """Workflow for looking up a single occurrence record."""
        try:
            extracted_params = await self.extract_occurrence_lookup_params(request)
        except ValueError as e:
            await context.reply(f"I couldn't understand your search request: {e}")
            return
            
        async with context.begin_process("Looking up occurrence record") as process:
            await process.log("Extracted Lookup parameters", data=extracted_params.model_dump(exclude_defaults=True))
            api_url = self.ala_logic.build_occurrence_lookup_url(extracted_params)  
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_get_request(api_url))  
                
                scientific_name = raw_response.get('processed', {}).get('scientificName', 'Unknown Species')
                await process.log(f"Successfully found record for '{scientific_name}'.")
                
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Raw JSON for occurrence record {extracted_params.recordUuid}",  
                    uris=[api_url],
                    metadata={"data_source": "ALA Occurrences", "uuid": extracted_params.recordUuid} 
                )
                await context.reply(f"I have retrieved the details for the occurrence record of '{scientific_name}'.")

            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while looking up the occurrence record: {e}")


    async def run_get_index_fields(self, context, request: str):  
        """Workflow for getting all available index fields."""
        async with context.begin_process("Fetching all available ALA index fields") as process:
            api_url = self.ala_logic.build_index_fields_url()
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_get_request(api_url))  
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


    async def run_list_distributions(self, context, request: str):  
        """Workflow to list available spatial layers/distributions to users"""
        async with context.begin_process("Listing expert distributions") as process:
            api_url = self.ala_logic.build_spatial_distributions_url()
            await process.log(f"Constructed API URL: {api_url}")
            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_get_request(api_url))  
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


    async def run_get_distribution_by_lsid(self, context, request: str): 
        """Workflow for getting distribution by LSID."""
        try:
            extracted_params = await self.extract_spatial_distribution_by_lsid_params(request) 
        except ValueError as e:
            await context.reply(f"I couldn't understand your distribution request: {e}")
            return
            
        async with context.begin_process(f"Getting distribution for LSID '{extracted_params.lsid}'") as process:
            await process.log("Extracted distribution parameters", data=extracted_params.model_dump(exclude_defaults=True)) 
            api_url = self.ala_logic.build_spatial_distribution_by_lsid_url(extracted_params.lsid) 
            await process.log(f"Constructed API URL: {api_url}")
            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_get_request(api_url))  
                await process.log("Fetched distribution data.")
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Raw JSON for distribution of LSID {extracted_params.lsid}.", 
                    uris=[api_url],
                    metadata={"lsid": extracted_params.lsid}  
                )
                await context.reply(f"Fetched distribution data for LSID '{extracted_params.lsid}'.")  
            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"Error fetching distribution for LSID '{extracted_params.lsid}': {e}")  


    async def run_get_distribution_map(self, context, request: str): 
        """Workflow for getting distribution map image."""
        try:
            extracted_params = await self.extract_spatial_distribution_map_params(request)  
        except ValueError as e:
            await context.reply(f"I couldn't understand your map request: {e}")
            return
            
        async with context.begin_process(f"Getting distribution map image for imageId '{extracted_params.imageId}'") as process:
            await process.log("Extracted map parameters", data=extracted_params.model_dump(exclude_defaults=True)) 
            api_url = self.ala_logic.build_spatial_distribution_map_url(extracted_params.imageId)  
            await process.log(f"Constructed API URL: {api_url}")
            try:
                loop = asyncio.get_event_loop()
                image_data = await loop.run_in_executor(None, lambda: self.ala_logic.execute_image_request(api_url))
                
                await process.create_artifact(
                    mimetype="image/png",
                    description=f"PNG map image for imageId {extracted_params.imageId}.",  
                    uris=[api_url],
                    metadata={"image_id": extracted_params.imageId, "size_bytes": len(image_data)}  
                )
                await context.reply(f"Fetched PNG map image for imageId '{extracted_params.imageId}'.") 
            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"Error fetching PNG map image for imageId '{extracted_params.imageId}': {e}")  


    async def run_get_occurrence_facets(self, context, request: str):  
        """Workflow for getting occurrence facet information - data breakdowns and insights"""
        try:
            extracted_params = await self.extract_occurrence_facets_params(request) 
        except ValueError as e:
            await context.reply(f"I couldn't understand your facets request: {e}")
            return
        
        # Build description from extracted parameters
        query_description = []
        if extracted_params.q:
            query_description.append(f"query: '{extracted_params.q}'")
        if extracted_params.fq:
            query_description.append(f"filters: {', '.join(extracted_params.fq)}")
        if extracted_params.facets:
            query_description.append(f"facets: {', '.join(extracted_params.facets)}")
        
        search_context = " with " + ", ".join(query_description) if query_description else " for all occurrence data"
        
        async with context.begin_process(f"Getting occurrence data breakdowns{search_context}") as process:
            await process.log("Extracted facet search parameters", data=extracted_params.model_dump(exclude_defaults=True)) 

            api_url = self.ala_logic.build_occurrence_facets_url(extracted_params)  
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_get_request(api_url)) 
                
                await process.log("Successfully retrieved facet data.")
                
                # Extract key insights from facet response
                facet_fields = []
                total_facets = 0
                
                if isinstance(raw_response, dict):
                    facet_results = raw_response.get('facetResults', [])
                elif isinstance(raw_response, list):
                    facet_results = raw_response
                else:
                    facet_results = []

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


    async def run_get_occurrence_taxa_count(self, context, request: str): 
        """Workflow for getting occurrence counts for specific taxa"""
        try:
            extracted_params = await self.extract_occurrence_taxa_count_params(request)  
        except ValueError as e:
            await context.reply(f"I couldn't understand your taxa count request: {e}")
            return
        
        # Parse the GUIDs to understand what we're counting
        guid_list = extracted_params.guids.replace('\n', extracted_params.separator).split(extracted_params.separator)  
        guid_count = len([g for g in guid_list if g.strip()])
        
        # Build description
        filter_description = ""
        if extracted_params.fq:  
            filter_description = f" with filters: {', '.join(extracted_params.fq)}"
        
        async with context.begin_process(f"Counting occurrences for {guid_count} taxa{filter_description}") as process:
            await process.log("Extracted taxa count parameters", data=extracted_params.model_dump(exclude_defaults=True)) 
            await process.log(f"Analyzing {guid_count} taxa GUIDs")

            api_url = self.ala_logic.build_occurrence_taxa_count_url(extracted_params)
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_get_request(api_url))  
                
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


    async def run_user_friendly_taxa_count(self, context, request: str):  
        """
        Workflow for the user-friendly taxa count helper.
        This method calls the high-level orchestrator in the logic layer.
        """
        try:
            extracted_params = await self.extract_taxa_count_helper_params(request) 
        except ValueError as e:
            await context.reply(f"I couldn't understand your taxa count request: {e}")
            return
        
        name_list = (extracted_params.species_names or []) + (extracted_params.common_names or [])  
        query_description = f"for '{', '.join(name_list)}'"
        filters = []
        if extracted_params.state:  
            filters.append(f"state: {extracted_params.state}")
        if extracted_params.year:  
            filters.append(f"year: {extracted_params.year}")
        if extracted_params.basis_of_record: 
            filters.append(f"basis of record: {extracted_params.basis_of_record}")
        if filters:
            query_description += " with filters: " + ", ".join(filters)

        async with context.begin_process(f"Counting occurrences {query_description}") as process:
            await process.log("Extracted user-friendly taxa count parameters", data=extracted_params.model_dump(exclude_defaults=True))  

            try:
                # Now get both the data and URL from the logic
                raw_response, api_url = await self.ala_logic.get_taxa_counts(extracted_params) 
                await process.log("Successfully retrieved taxa count data.", data=raw_response)
                total_occurrences = sum(int(count) for count in raw_response.values() if isinstance(count, (int, float)))
                taxa_with_records = sum(1 for count in raw_response.values() if isinstance(count, (int, float)) and count > 0)
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Taxa occurrence counts - {total_occurrences:,} total occurrences.",
                    uris=[api_url],
                    metadata={"total_occurrences": total_occurrences, "taxa_counted": taxa_with_records}
                )
                await context.reply(f"Found a total of {total_occurrences:,} occurrence records for the requested species with the specified filters.")

            except (ValueError, ConnectionError) as e:
                await process.log("Error during taxa count workflow", data={"error": str(e)})
                await context.reply(f"I encountered an error while trying to count the occurrences: {e}")


    async def run_species_guid_lookup(self, context, request: str): 
        """Workflow for looking up a taxon GUID by name - critical for linking to occurrence data"""
        try:
            extracted_params = await self.extract_species_guid_lookup_params(request)  
        except ValueError as e:
            await context.reply(f"I couldn't understand your GUID lookup request: {e}")
            return
            
        async with context.begin_process(f"Looking up GUID for '{extracted_params.name}'") as process:  
            await process.log("Extracted GUID lookup parameters", data=extracted_params.model_dump())  

            api_url = self.ala_logic.build_species_guid_lookup_url(extracted_params)  
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_get_request(api_url)) 
                
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
                    description=f"GUID lookup results for '{extracted_params.name}' - {matches_found} matches found",  
                    uris=[api_url],
                    metadata={
                        "data_source": "ALA Species GUID Lookup",
                        "search_term": extracted_params.name,  
                        "matches_found": matches_found,
                        "guids": guids[:3]  # Store first few GUIDs for reference
                    }
                )
                
                # Create user-friendly response
                if matches_found > 0:
                    if matches_found == 1:
                        summary = f"Found GUID for '{extracted_params.name}': {sample_matches[0] if sample_matches else 'match found'}"  
                    else:
                        summary = f"Found {matches_found} GUID matches for '{extracted_params.name}'"  
                        if sample_matches:
                            summary += f": {', '.join(sample_matches)}"
                            if matches_found > 3:
                                summary += f" and {matches_found - 3} more"
                    summary += "."
                else:
                    summary = f"No GUID matches found for '{extracted_params.name}'. Try checking the spelling or using a different name format."  
                
                await context.reply(summary)

            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while looking up the GUID for '{extracted_params.name}': {e}")  


    async def run_species_image_search(self, context, request: str):  
        """
        Workflow for searching and fetching the first available image for a species.
        This function now includes the logic for Step 3 (parsing) and Step 4 (downloading).
        """
        try:
            extracted_params = await self.extract_species_image_search_params(request)  
        except ValueError as e:
            await context.reply(f"I couldn't understand your image search request: {e}")
            return
            
        async with context.begin_process(f"Fetching image for taxon ID '{extracted_params.id}'") as process:  
            # --- STEP 2: Search for image metadata ---
            await process.log("Extracted image search parameters", data=extracted_params.model_dump())  
            
            # We only need one result to get an image URL
            metadata_url = self.ala_logic.build_species_image_search_url(extracted_params)  
            await process.log(f"Constructed metadata URL: {metadata_url}")

            try:
                loop = asyncio.get_event_loop()
                image_metadata = await loop.run_in_executor(None, lambda: self.ala_logic.execute_get_request(metadata_url))  
                await process.log("Successfully retrieved image metadata.", data=image_metadata)
                
            except ConnectionError as e:
                await process.log("Error during metadata request", data={"error": str(e)})
                await context.reply(f"I encountered an error while searching for image information: {e}")
                return # Stop execution if metadata search fails

            # --- STEP 3: Parse JSON and extract the direct image URL ---
            image_url = None
            try:
                results = image_metadata.get('searchResults', {}).get('results', [])
                if results and 'imageUrl' in results[0]:
                    image_url = results[0]['imageUrl']
                    await process.log(f"Extracted direct image URL: {image_url}")
                else:
                    # This handles cases where the search is successful but returns no images
                    await context.reply(f"I found information about the species, but there are no images available for taxon ID '{extracted_params.id}'.")  
                    return
            except (ValueError, KeyError, IndexError) as e:
                await process.log("Error parsing image metadata", data={"error": str(e)})
                await context.reply("I found image information but could not extract a valid download link.")
                return
            
            # --- STEP 4: Download the image and create artifact ---
            try:
                loop = asyncio.get_event_loop()
                image_data = await loop.run_in_executor(None, lambda: self.ala_logic.execute_image_request(image_url))
                
                await process.create_artifact(
                    mimetype="image/jpeg",
                    description=f"Species image for taxon ID {extracted_params.id}",
                    uris=[image_url],
                    metadata={"taxon_id": extracted_params.id, "image_url": image_url, "size_bytes": len(image_data)}
                )
                await context.reply(f"Successfully retrieved and downloaded an image for taxon ID '{extracted_params.id}'.")
                
            except ConnectionError as e:
                await process.log("Error downloading image", data={"error": str(e)})
                await context.reply(f"I found an image URL but couldn't download the image: {e}")


    async def run_species_bie_search(self, context, request: str):  
        """Workflow for searching the Biodiversity Information Explorer (BIE)"""
        try:
            extracted_params = await self.extract_species_bie_search_params(request) 
        except ValueError as e:
            await context.reply(f"I couldn't understand your BIE search request: {e}")
            return
            
        filter_description = f" with filter '{extracted_params.fq}'" if extracted_params.fq else ""  
        
        async with context.begin_process(f"Searching BIE for '{extracted_params.q}'{filter_description}") as process:  
            await process.log("Extracted BIE search parameters", data=extracted_params.model_dump())

            api_url = self.ala_logic.build_species_bie_search_url(extracted_params)   
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_get_request(api_url)) 
                
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
                    description=f"BIE search results for '{extracted_params.q}' - {results_count} results from {total_records} total", 
                    uris=[api_url],
                    metadata={
                        "data_source": "ALA BIE Search",
                        "search_query": extracted_params.q,  
                        "filter_applied": extracted_params.fq,  
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
                    summary = f"No results found in the BIE for '{extracted_params.q}'{filter_description}."  
                
                await context.reply(summary)

            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while searching the BIE: {e}")


    async def run_filter_species_lists(self, context, request: str):  
        """Workflow for filtering species lists by scientific names or data resource IDs"""
        try:
            extracted_params = await self.extract_species_list_filter_params(request) 
        except ValueError as e:
            await context.reply(f"I couldn't understand your species list filter request: {e}")
            return
            
        filter_description = []
        if extracted_params.scientific_names:  
            filter_description.append(f"scientific names: {', '.join(extracted_params.scientific_names)}")
        if extracted_params.dr_ids:  
            filter_description.append(f"data resource IDs: {', '.join(extracted_params.dr_ids)}")
        
        filter_text = " and ".join(filter_description)
        
        async with context.begin_process(f"Filtering species lists by {filter_text}") as process:
            await process.log("Extracted filter parameters", data=extracted_params.model_dump(exclude_defaults=True))  

            try:
                url, request_body = self.ala_logic.build_species_list_filter_url(extracted_params)   
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


    async def run_get_species_list_details(self, context, request: str):   
        """Workflow for getting detailed information about a specific species list"""
        try:
            extracted_params = await self.extract_species_list_details_params(request)  
        except ValueError as e:
            await context.reply(f"I couldn't understand your species list details request: {e}")
            return
            
        async with context.begin_process(f"Getting details for species list {extracted_params.druid}") as process:   
            await process.log("Extracted species list details parameters", data=extracted_params.model_dump(exclude_defaults=True))  
            api_url = self.ala_logic.build_species_list_details_url(extracted_params)   
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_get_request(api_url))   
                
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
                    metadata={"data_source": "ALA Species List", "druid": extracted_params.druid, "list_count": list_count, "total_items": total_items}   
                )
                
                if list_count == 1:
                    await context.reply(f"Retrieved details for '{list_name}' containing {total_items} species.")
                else:
                    await context.reply(f"Retrieved details for {list_count} species lists containing a total of {total_items} species.")

            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while retrieving the species list details: {e}")


    async def run_get_species_list_items(self, context, request: str):   
        """Workflow for getting species within specific lists with optional filtering"""
        try:
            extracted_params = await self.extract_species_list_items_params(request)  
        except ValueError as e:
            await context.reply(f"I couldn't understand your species list items request: {e}")
            return
            
        query_description = f"list(s) {extracted_params.druid}"   
        if extracted_params.q:   
            query_description += f" searching for '{extracted_params.q}'"
        
        async with context.begin_process(f"Getting species from {query_description}") as process:
            await process.log("Extracted species list items parameters", data=extracted_params.model_dump(exclude_defaults=True))  
            api_url = self.ala_logic.build_species_list_items_url(extracted_params)   
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_get_request(api_url))   
                
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
                    description=f"Species from list(s) {extracted_params.druid}" + (f" matching '{extracted_params.q}'" if extracted_params.q else "") + f" - {returned} items",   
                    uris=[api_url],
                    metadata={"data_source": "ALA Species List Items", "druid": extracted_params.druid, "returned_count": returned, "total_count": total, "search_query": extracted_params.q}   
                )
                
                reply = f"Retrieved {returned} species from the list(s)"
                if total > returned:
                    reply += f" (showing first {returned} of {total} total)"
                if extracted_params.q:   
                    reply += f" matching '{extracted_params.q}'"
                if sample_species:
                    reply += f". Sample species: {', '.join(sample_species)}"
                reply += "."
                
                await context.reply(reply)

            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while retrieving species from the list: {e}")


    async def run_get_species_list_distinct_fields(self, context, request: str):   
        """Workflow for getting distinct values for a field across species list items"""
        try:
            extracted_params = await self.extract_species_list_distinct_field_params(request)  
        except ValueError as e:
            await context.reply(f"I couldn't understand your distinct fields request: {e}")
            return
            
        async with context.begin_process(f"Getting distinct values for field '{extracted_params.field}' across all species lists") as process:   
            await process.log("Extracted distinct field parameters", data=extracted_params.model_dump(exclude_defaults=True))  
            api_url = self.ala_logic.build_species_list_distinct_field_url(extracted_params)   
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_get_request(api_url))   
                
                # Handle response structure
                if isinstance(raw_response, list):
                    distinct_values = raw_response
                else:
                    distinct_values = raw_response.get('values', raw_response.get('results', []))
                
                value_count = len(distinct_values)
                await process.log(f"Found {value_count} distinct values for field '{extracted_params.field}'.")   
                
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Distinct values for field '{extracted_params.field}' - {value_count} unique values",   
                    uris=[api_url],
                    metadata={"data_source": "ALA Species List Distinct Fields", "field": extracted_params.field, "value_count": value_count}   
                )
                
                sample_values = distinct_values[:5] if distinct_values else []
                reply = f"Found {value_count} distinct values for field '{extracted_params.field}'"   
                if sample_values:
                    reply += f". Sample values: {', '.join(str(v) for v in sample_values)}"
                reply += "."
                
                await context.reply(reply)

            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while retrieving distinct field values: {e}")


    async def run_get_species_list_common_keys(self, context, request: str):   
        """Workflow for getting common keys (KVP) across multiple species lists"""
        try:
            extracted_params = await self.extract_species_list_common_keys_params(request)  
        except ValueError as e:
            await context.reply(f"I couldn't understand your common keys request: {e}")
            return
            
        async with context.begin_process(f"Getting common keys across species lists: {extracted_params.druid}") as process:   
            await process.log("Extracted common keys parameters", data=extracted_params.model_dump(exclude_defaults=True))  
            api_url = self.ala_logic.build_species_list_common_keys_url(extracted_params)   
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_get_request(api_url))   
                
                # Handle response structure
                if isinstance(raw_response, list):
                    common_keys = raw_response
                else:
                    common_keys = raw_response.get('keys', raw_response.get('results', []))
                
                key_count = len(common_keys)
                await process.log(f"Found {key_count} common keys across the specified lists.")
                
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Common keys across species lists {extracted_params.druid} - {key_count} keys",   
                    uris=[api_url],
                    metadata={"data_source": "ALA Species List Common Keys", "druid": extracted_params.druid, "key_count": key_count}   
                )
                
                await context.reply(f"Found {key_count} common keys across the specified species lists. These keys can be used for additional data analysis.")

            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while retrieving common keys: {e}")


    async def run_get_distribution_by_name(self, context, request: str):   
        """
        Orchestrates the full workflow to get spatial distribution data for a species by its name.
        """
        try:
            extracted_params = await self.extract_species_guid_lookup_params(request)  
        except ValueError as e:
            await context.reply(f"I couldn't understand your species distribution request: {e}")
            return
            
        species_name = extracted_params.name   
        async with context.begin_process(f"Getting spatial distribution for '{species_name}'") as process:
            await process.log("Extracted distribution by name parameters", data=extracted_params.model_dump(exclude_defaults=True))  

            # --- STEP 1: Find the LSID for the species name ---
            try:
                await process.log(f"Looking up LSID for '{species_name}'...")
                loop = asyncio.get_event_loop()
                
                guid_url = self.ala_logic.build_species_guid_lookup_url(extracted_params)   
                guid_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_get_request(guid_url))   
                
                # Extract the first LSID (guid) from the response
                if guid_response and isinstance(guid_response, list) and guid_response[0].get('guid'):
                    lsid = guid_response[0]['guid']
                    await process.log(f"Found LSID: {lsid}")
                else:
                    await context.reply(f"Sorry, I could not find a unique identifier (LSID) for '{species_name}'. Please try a different name.")
                    return
            except (ConnectionError, IndexError, KeyError) as e:
                await process.log("Error during LSID lookup", data={"error": str(e)})
                await context.reply(f"I encountered an error while trying to find an identifier for '{species_name}': {e}")
                return

            # --- STEP 2: Get the distribution data using the found LSID ---
            try:
                await process.log(f"Fetching distribution data for LSID: {lsid}")
                # Create a request string for the distribution lookup and call the updated method
                distribution_request = f"Get distribution for LSID {lsid}"  
                await self.run_get_distribution_by_lsid(context, distribution_request)  

            except Exception as e:
                # The run_get_distribution_by_lsid method already handles its own errors and replies.
                await process.log("Error during distribution data fetch", data={"error": str(e)})
