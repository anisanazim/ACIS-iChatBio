import asyncio
import json
from typing import Dict, Any
import requests
import os
import yaml
from datetime import datetime
from ala_logic import get_bie_fields

# Add new imports 
from typing_extensions import override
from pydantic import BaseModel, Field
from typing import Optional
import langchain.agents
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from ichatbio.agent import IChatBioAgent
from ichatbio.agent_response import ResponseContext
from ichatbio.types import AgentCard, AgentEntrypoint
from parameter_resolver import ALAParameterResolver
from ala_logic import ALASearchResponse

from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage


# Unified parameter model for ReAct agent
class UnifiedALAParams(BaseModel):
    query: str = Field(..., description="Natural language query about Australian biodiversity data")
    context: Optional[str] = Field(None, description="Additional context or specific requirements")


from ala_logic import (
    ALA, 
    OccurrenceSearchParams, OccurrenceLookupParams, OccurrenceFacetsParams, OccurrenceTaxaCountParams, TaxaCountHelper,
    SpeciesGuidLookupParams, SpeciesImageSearchParams, SpeciesBieSearchParams,
    NoParams, SpatialDistributionByLsidParams, SpatialDistributionMapParams,
    SpeciesListDetailsParams, 
    SpeciesListItemsParams, SpeciesListDistinctFieldParams
)
class ALAiChatBioAgent:
    """The iChatBio agent implementation for ALA"""

    def __init__(self):
        self.ala_logic = ALA()

    async def run_occurrence_search(self, context, params: OccurrenceSearchParams):
        """Workflow for searching occurrences using the context object."""
        async with context.begin_process("Searching for ALA occurrences") as process:
            await process.log("Extracted search parameters", data=params.model_dump(exclude_defaults=True))

            api_url = self.ala_logic.build_occurrence_url(params)
            await process.log(f"Constructed API URL: {api_url}")

            await process.log("Querying ALA for occurrence data...")
            try:
                loop = asyncio.get_event_loop()
                raw_response = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url)),
                    timeout=30.0
                )
                
                total = raw_response.get('totalRecords', 0)
                returned = len(raw_response.get('occurrences', []))

                await process.log(f"Query successful, found {total} records.")
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"ALA occurrence records - showing {returned} of {total:,} total records",
                    uris=[api_url],
                    content=json.dumps(raw_response).encode('utf-8'),
                    metadata={
                        "record_count": returned,
                        "total_matches": total,
                        "search_params": params.model_dump(exclude_defaults=True),
                        "data_source": "Atlas of Living Australia",
                        "retrieval_date": datetime.now().strftime("%Y-%m-%d")
                    }
                )
                
                # Reply to the assistant with a summary of the action taken.
                await context.reply(f"I have successfully searched for occurrences and found {total} matching records. I've created an artifact with the results.")

            except asyncio.TimeoutError:
                await process.log("API took too long to respond. Consider refining your request to reduce response time.")
                await context.reply("API took too long to respond. Consider refining your request to reduce response time.")
            except ConnectionError as e:
                await process.log(f"Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while trying to search for occurrences: {e}")

    async def run_occurrence_lookup(self, context, params: OccurrenceLookupParams):
        """Workflow for looking up a single occurrence record."""
        async with context.begin_process(f"Looking up occurrence record {params.recordUuid}") as process:
            api_url = self.ala_logic.build_occurrence_lookup_url(params)
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url)),
                    timeout=30.0
                )
                
                scientific_name = raw_response.get('processed', {}).get('scientificName', 'Unknown Species')
                await process.log(f"Successfully found record for '{scientific_name}'.")
                
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Raw JSON for occurrence record {params.recordUuid}",
                    uris=[api_url],
                    content=json.dumps(raw_response).encode('utf-8'),
                    metadata={"data_source": "ALA Occurrences", "uuid": params.recordUuid}
                    
                )
                await context.reply(f"I have retrieved the details for the occurrence record of '{scientific_name}'.")

            except asyncio.TimeoutError:
                await process.log("API took too long to respond. Consider refining your request to reduce response time.")
                await context.reply("API took too long to respond. Consider refining your request to reduce response time.")
            except ConnectionError as e:
                await process.log(f"Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while trying to search for occurrences: {e}")
    
    async def run_get_index_fields(self, context, params: NoParams):
        """Workflow for getting all available index fields."""
        async with context.begin_process("Fetching all available ALA index fields") as process:
            api_url = self.ala_logic.build_index_fields_url()
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url)),
                    timeout=30.0
                )
                field_count = len(raw_response)

                await process.log(f"Successfully found {field_count} indexed fields.")
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Raw JSON list of all {field_count} indexed fields.",
                    uris=[api_url],
                    content=json.dumps(raw_response).encode('utf-8'),
                    metadata={"data_source": "ALA Index Fields", "field_count": field_count}
                    
                )
                await context.reply(f"I have retrieved a list of all {field_count} searchable fields from the ALA.")     
            except asyncio.TimeoutError:
                await process.log("API took too long to respond. Consider refining your request to reduce response time.")
                await context.reply("API took too long to respond. Consider refining your request to reduce response time.")
            except ConnectionError as e:
                await process.log(f"Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while trying to search for occurrences: {e}")
    
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
                    content=json.dumps(raw_response).encode('utf-8'),
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
                    content=json.dumps(raw_response).encode('utf-8'),
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
                    metadata={"image_id": params.imageId, "size_bytes": len(image_data)},
                    content=image_data
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
                    content=json.dumps(raw_response).encode('utf-8'),
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

    async def run_user_friendly_taxa_count(self, context, params: TaxaCountHelper):
        """
        Workflow for the user-friendly taxa count helper.
        This method calls the high-level orchestrator in the logic layer.
        """
        name_list = (params.species_names or []) + (params.common_names or [])
        query_description = f"for '{', '.join(name_list)}'"
        filters = []
        if params.state:
            filters.append(f"state: {params.state}")
        if params.year:
            filters.append(f"year: {params.year}")
        if params.basis_of_record:
            filters.append(f"basis of record: {params.basis_of_record}")
        if filters:
            query_description += " with filters: " + ", ".join(filters)

        async with context.begin_process(f"Counting occurrences {query_description}") as process:
            await process.log("User-friendly taxa count parameters", data=params.model_dump(exclude_defaults=True))

            try:
                # Now get both the data and URL from the logic
                raw_response, api_url = await self.ala_logic.get_taxa_counts(params)
                await process.log("Successfully retrieved taxa count data.", data=raw_response)
                total_occurrences = sum(int(count) for count in raw_response.values() if isinstance(count, (int, float)))
                taxa_with_records = sum(1 for count in raw_response.values() if isinstance(count, (int, float)) and count > 0)
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Taxa occurrence counts - {total_occurrences:,} total occurrences.",
                    uris=[api_url],
                    content=json.dumps(raw_response).encode('utf-8'),
                    metadata={"total_occurrences": total_occurrences, "taxa_counted": taxa_with_records}
                )
                await context.reply(f"Found a total of {total_occurrences:,} occurrence records for the requested species with the specified filters.")

            except (ValueError, ConnectionError) as e:
                await process.log("Error during taxa count workflow", data={"error": str(e)})
                await context.reply(f"I encountered an error while trying to count the occurrences: {e}")

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
                    content=json.dumps(raw_response).encode('utf-8'),
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
        """
        Workflow for searching and fetching the first available image for a species.
        This function now includes the logic for Step 3 (parsing) and Step 4 (downloading).
        """
        async with context.begin_process(f"Fetching image for taxon ID '{params.id}'") as process:
            # --- STEP 2: Search for image metadata ---
            await process.log("Image search parameters", data=params.model_dump())
            
            # We only need one result to get an image URL
            metadata_url = self.ala_logic.build_species_image_search_url(params)
            await process.log(f"Constructed metadata URL: {metadata_url}")

            try:
                loop = asyncio.get_event_loop()
                image_metadata = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(metadata_url))
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
                    await context.reply(f"I found information about the species, but there are no images available for taxon ID '{params.id}'.")
                    return
            except (ValueError, KeyError, IndexError) as e:
                await process.log("Error parsing image metadata", data={"error": str(e)})
                await context.reply("I found image information but could not extract a valid download link.")
                return

    async def run_species_bie_search(self, context, params: SpeciesBieSearchParams):
        """Workflow for searching the Biodiversity Information Explorer (BIE) with field validation"""

        # --- Step 1: Fetch or cache valid BIE fields ---
        try:
            valid_bie_fields = get_bie_fields(self.ala_logic.ala_api_base_url)
        except Exception as e:
            await context.reply(f"Error fetching BIE index fields: {e}")
            valid_bie_fields = set()  # fallback: allow nothing

        # --- Step 2: Parse and filter params.fq ---
        dropped_filters = []
        filtered_fq = []
        if params.fq:
            # Support both string and list formats
            fq_items = params.fq if isinstance(params.fq, list) else [params.fq]
            for fq in fq_items:
                # Assume format: field:value or field:"value"
                field = fq.split(":", 1)[0].strip()
                if field in valid_bie_fields:
                    filtered_fq.append(fq)
                else:
                    dropped_filters.append(fq)
            params.fq = filtered_fq if len(filtered_fq) > 1 else (filtered_fq[0] if filtered_fq else None)

        filter_description = f" with filter '{params.fq}'" if params.fq else ""
        async with context.begin_process(f"Searching BIE for '{params.q}'{filter_description}") as process:
            await process.log("BIE search parameters", data=params.model_dump())
            if dropped_filters:
                await process.log("Dropped unsupported BIE filters", data={"dropped": dropped_filters})
                await context.reply(f"Note: The following filters are not supported by BIE and were ignored: {dropped_filters}")

            api_url = self.ala_logic.build_species_bie_search_url(params)
            await process.log(f"Constructed API URL: {api_url}")

            try:
                loop = asyncio.get_event_loop()
                raw_response = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url)),
                    timeout=30.0
                )
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
                    content=json.dumps(raw_response).encode('utf-8'),
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

            except asyncio.TimeoutError:
                await process.log("API took too long to respond. Consider refining your request to reduce response time.")
                await context.reply("API took too long to respond. Consider refining your request to reduce response time.")
            except ConnectionError as e:
                await process.log(f"Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while trying to search for occurrences: {e}")
    
    # async def run_filter_species_lists(self, context, params: SpeciesListFilterParams):
    #     """Workflow for filtering species lists by scientific names or data resource IDs"""
    #     filter_description = []
    #     if params.scientific_names:
    #         filter_description.append(f"scientific names: {', '.join(params.scientific_names)}")
    #     if params.dr_ids:
    #         filter_description.append(f"data resource IDs: {', '.join(params.dr_ids)}")
        
    #     filter_text = " and ".join(filter_description)
        
    #     async with context.begin_process(f"Filtering species lists by {filter_text}") as process:
    #         await process.log("Filter parameters", data=params.model_dump(exclude_defaults=True))

    #         try:
    #             url, request_body = self.ala_logic.build_species_list_filter_url(params)
    #             await process.log(f"Constructed API URL: {url}")
    #             await process.log("Request body", data=request_body)

    #             loop = asyncio.get_event_loop()
    #             raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_post_request(url, request_body))
                
    #             # Handle response structure
    #             if isinstance(raw_response, list):
    #                 lists = raw_response
    #                 total = len(lists)
    #             else:
    #                 lists = raw_response.get('lists', raw_response.get('results', []))
    #                 total = raw_response.get('totalRecords', len(lists))

    #             returned = len(lists)
    #             await process.log(f"Filter successful, found {total} matching species lists.")
                
    #             await process.create_artifact(
    #                 mimetype="application/json",
    #                 description=f"Filtered species lists - {returned} results",
    #                 uris=[url],
    #                 data=raw_response,
    #                 metadata={"list_count": returned, "total_matches": total, "filter_criteria": filter_text}
    #             )
                
    #             await context.reply(f"Found {total} species lists matching your filter criteria. I've created an artifact with the results.")

    #         except ValueError as ve:
    #             await context.reply(f"Filter error: {ve}")
    #         except ConnectionError as e:
    #             await process.log("Error during API request", data={"error": str(e)})
    #             await context.reply(f"I encountered an error while filtering species lists: {e}")

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
                    content=json.dumps(raw_response).encode('utf-8'),
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
                for item in items[:3]:  
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
                    content=json.dumps(raw_response).encode('utf-8'),
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
                    content=json.dumps(raw_response).encode('utf-8'),
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

    async def run_get_distribution_by_name(self, context, params: SpeciesGuidLookupParams):
        """
        Orchestrates the full workflow to get spatial distribution data for a species by its name.
        """
        species_name = params.name
        async with context.begin_process(f"Getting spatial distribution for '{species_name}'") as process:

            # --- STEP 1: Find the LSID for the species name ---
            try:
                await process.log(f"Looking up LSID for '{species_name}'...")
                loop = asyncio.get_event_loop()
                
                guid_url = self.ala_logic.build_species_guid_lookup_url(params)
                guid_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(guid_url))
                
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
                distribution_params = SpatialDistributionByLsidParams(lsid=lsid)
                # Re-use the existing agent method for this step
                await self.run_get_distribution_by_lsid(context, distribution_params)

            except Exception as e:
                # The run_get_distribution_by_lsid method already handles its own errors and replies.
                await process.log("Error during distribution data fetch", data={"error": str(e)})


class UnifiedALAReActAgent(IChatBioAgent):
    """Unified ALA agent using LangChain ReAct pattern"""
    
    def __init__(self):
        self.workflow_agent = ALAiChatBioAgent()
    
    def _get_config_value(self, key: str, default: str = None) -> str:
        """Get configuration value from environment or env.yaml file"""
        # First try environment variable
        value = os.getenv(key)
        if value:
            return value
            
        # Then try env.yaml file
        try:
            with open("env.yaml", "r") as f:
                config = yaml.safe_load(f) or {}
                return config.get(key, default)
        except FileNotFoundError:
            return default
        
    @override
    async def run(self, context: ResponseContext, request: str, entrypoint: str, params: UnifiedALAParams):
        """Execute the unified biodiversity search using ReAct agent"""
        
        # Get API configuration directly
        api_key = self._get_config_value("OPENAI_API_KEY")
        base_url = self._get_config_value("OPENAI_BASE_URL", "https://api.ai.it.ufl.edu")

        if not api_key:
            await context.reply("Error: OpenAI API key not found in environment or env.yaml file")
            return

        # Define tools as closures inside run() method
        @tool(return_direct=True)
        async def abort(reason: str):
            """Call if you cannot fulfill the request."""
            await context.reply(f"Unable to complete request: {reason}")

        @tool(return_direct=True)
        async def finish(summary: str):
            """Call when request is successfully completed."""
            await context.reply(summary)

        @tool
        async def search_species_occurrences(user_query: str) -> str:
            """Search for species occurrence records in Australia with enhanced parameter extraction."""
            
            async with context.begin_process(f"Searching ALA for: '{user_query}'") as process:
                
                # Step 1: Enhanced parameter extraction with validation
                try:
                    extracted = await self.workflow_agent.ala_logic._extract_params_enhanced(user_query, ALASearchResponse)
                    await process.log("Enhanced extraction successful", data=extracted.model_dump())
                except ValueError as e:
                    await process.log(f"Parameter extraction failed: {e}")
                    return f"I had trouble understanding your query: {e}"
                
                # Step 2: Automatic parameter resolution
                resolver = ALAParameterResolver(self.workflow_agent.ala_logic.ala_api_base_url)
                resolved = await resolver.resolve_unresolved_params(extracted)
                
                if resolved.clarification_needed:
                    return f"I need clarification: {resolved.clarification_reason}"
                
                # Step 3: Convert enhanced parameters to fq filters - ADD THIS SECTION HERE
                fq_filters = resolved.params.get('fq', []).copy()
                
                # Convert taxonomic parameters to fq filters
                if 'family' in resolved.params:
                    fq_filters.append(f"family:{resolved.params['family']}")
                if 'genus' in resolved.params:
                    fq_filters.append(f"genus:{resolved.params['genus']}")
                if 'species' in resolved.params:
                    fq_filters.append(f"species:{resolved.params['species']}")
                if 'class' in resolved.params:
                    fq_filters.append(f"class:{resolved.params['class']}")
                if 'order' in resolved.params:
                    fq_filters.append(f"order:{resolved.params['order']}")
                if 'kingdom' in resolved.params:
                    fq_filters.append(f"kingdom:{resolved.params['kingdom']}")

                # Step 4: Create OccurrenceSearchParams
                occurrence_params = OccurrenceSearchParams(
                    q=resolved.params.get('q', '*'),
                    fq=fq_filters, 
                    # q=resolved.params.get('fq', []), 
                    # family=resolved.params.get('family'),        
                    # genus=resolved.params.get('genus'),          
                    # species=resolved.params.get('species'), 
                    year=resolved.params.get('year'),
                    startdate=resolved.params.get('startdate'),
                    enddate=resolved.params.get('enddate'),
                    pageSize=resolved.params.get('pageSize', 1000),
                    start=resolved.params.get('start', 0)
                )
                
                # Step 5: Execute search using existing workflow
                try:
                    await self.workflow_agent.run_occurrence_search(context, occurrence_params)
                    return f"Successfully found occurrence records for: {resolved.artifact_description}"
                except Exception as e:
                    return f"Error executing search: {str(e)}"


        @tool
        async def get_species_images(species_name: str) -> str:
            """Get images of Australian species."""
            async with context.begin_process(f"Fetching images for {species_name}") as process:
                try:
                    params = SpeciesImageSearchParams(q=species_name)
                    await process.log(f"Searching ALA for {species_name} images")
                    await self.workflow_agent.run_species_image_search(context, params)
                    
                    return f"Found images for {species_name}"
                except Exception as e:
                    await process.log(f"Error fetching images: {str(e)}")
                    return f"Error fetching images: {str(e)}"

        @tool
        async def lookup_species_info(species_name: str) -> str:
            """Look up comprehensive species information."""
            async with context.begin_process(f"Looking up species info for {species_name}") as process:
                try:
                    params = SpeciesBieSearchParams(q=species_name)
                    await process.log(f"Searching BIE for {species_name} information")
                    await self.workflow_agent.run_species_bie_search(context, params)
                    
                    return f"Found species information for {species_name}"
                except Exception as e:
                    await process.log(f"Error looking up species info: {str(e)}")
                    return f"Error looking up species info: {str(e)}"

        @tool
        async def get_species_distribution(species_name: str) -> str:
            """Get species distribution maps and data."""
            async with context.begin_process(f"Fetching distribution for {species_name}") as process:
                try:
                    await process.log(f"Searching for distribution data for {species_name}")
                    await self.workflow_agent.run_get_distribution_by_name(
                        context, 
                        SpeciesGuidLookupParams(name=species_name)
                    )
                    await process.log(f"Successfully retrieved distribution data for {species_name}")
                    return f"Found spatial distribution and geographic range data for {species_name}"
                    
                except Exception as e:
                    await process.log(f"Error fetching distribution: {str(e)}")
                    return f"Error fetching distribution: {str(e)}"

        tools = [
            search_species_occurrences,
            get_species_images, 
            lookup_species_info,
            get_species_distribution,
            abort,
            finish
        ]

        # Execute agent
        async with context.begin_process("Searching ALA API") as process:
            await process.log(f"Initializing ALA agent for query: '{request}' with {len(tools)} available tools")
            
            llm = ChatOpenAI(
                model="gpt-4o-mini",
                api_key=api_key,
                base_url=base_url
            )
            
            system_prompt = self._make_system_prompt(params.query, request)
            agent = create_react_agent(llm, tools)
            
            try:
                await agent.ainvoke({
                    "messages": [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=request)
                    ]
                })
                
            except Exception as e:
                await process.log(f"Agent execution failed: {type(e).__name__} - {str(e)}")
                await context.reply(f"An error occurred: {str(e)}")

    def _make_system_prompt(self, user_query: str, user_request: str) -> str:
        """Generate system prompt for ALA agent"""
        return f"""\
    You are an Australian biodiversity assistant with access to the Atlas of Living Australia (ALA) database.

    User Query: "{user_query}"
    Request: "{user_request}"

    Available Tools:
    - search_species_occurrences: Find where species have been observed in Australia, filter by year, location, or other occurrence-level attributes
    - get_species_images: Retrieve photos and images of species
    - lookup_species_info: Get comprehensive species profiles, taxonomy, and metadata (BIE search)
    - get_species_distribution: Get distribution maps and geographic data

    CRITICAL STOPPING RULES - FOLLOW THESE EXACTLY:
    1. Use each tool ONLY ONCE per query
    2. After ANY successful tool result, immediately call finish() with the results
    3. Do NOT call the same tool multiple times
    4. Do NOT call additional tools unless the user explicitly asks for multiple types of information

    TOOL SELECTION RULES - CHOOSE THE RIGHT TOOL:
    - For occurrence queries (records, sightings, observations, "where", "when", "how many"):
    → Use search_species_occurrences
    → Examples: "Show koala occurrences", "Find records in Queensland", "Sightings after 2020"

    - For taxonomy queries (classification, "what family", "scientific name", species information):
    → Use lookup_species_info  
    → Examples: "What family does bilby belong to?", "Tell me about Macropus rufus", "Classification of koala"

    - For image requests (photos, pictures, "what does it look like"):
    → Use get_species_images
    → Examples: "Show me photos of wombat", "What does echidna look like?"

    - For distribution queries (range, habitat, geographic data):
    → Use get_species_distribution
    → Examples: "Where do platypus live?", "Distribution of quoll"

    QUERY INTERPRETATION:
    - "Show me [species] occurrences" = occurrence search (NOT taxonomy)
    - "Find [species] records" = occurrence search (NOT taxonomy)  
    - "[Species] sightings" = occurrence search (NOT taxonomy)
    - "What is [species]?" = taxonomy search (NOT occurrence)
    - "Tell me about [species]" = taxonomy search (NOT occurrence)

    For taxonomy queries specifically:
    - Call lookup_species_info ONCE
    - Present the results you receive (species list, classification, etc.)
    - Call finish() immediately - DO NOT retry the search

    REMEMBER: ONE tool call + finish() = Complete response

    Always create artifacts when retrieving data.
    """



