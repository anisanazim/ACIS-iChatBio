import asyncio
import json
from typing import Dict, Any, List
import requests
import os
import yaml
from datetime import datetime
from ala_logic import get_bie_fields, map_params_to_model
from typing_extensions import override
from pydantic import BaseModel, Field
from typing import Optional
from langchain_openai import ChatOpenAI
from ichatbio.agent import IChatBioAgent
from ichatbio.agent_response import ResponseContext
from ichatbio.types import AgentCard, AgentEntrypoint
from parameter_resolver import ALAParameterResolver
from parameter_extractor import extract_params_from_query, ALASearchResponse
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

def get_config_value(key: str, default: str = None) -> str:
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
    
# Unified parameter model for the agent
class UnifiedALAParams(BaseModel):
    query: str = Field(..., description="Natural language query about Australian biodiversity data")
    context: Optional[str] = Field(None, description="Additional context or specific requirements")


from main_ala_logic import (
    ALA, 
    OccurrenceSearchParams, OccurrenceLookupParams, OccurrenceFacetsParams, OccurrenceTaxaCountParams, TaxaCountHelper,
    SpeciesGuidLookupParams, SpeciesImageSearchParams, SpeciesBieSearchParams,
    NoParams, SpatialDistributionByLsidParams, SpatialDistributionMapParams,
    SpeciesListDetailsParams, 
    SpeciesListItemsParams, SpeciesListDistinctFieldParams
)

from pydantic import BaseModel, Field
from typing import List, Literal

class ToolPlan(BaseModel):
    tool_name: str
    priority: Literal["must_call", "optional"]
    reason: str

class ResearchPlan(BaseModel):
    query_type: Literal["singlespecies", "comparison", "conservation", "distribution", "taxonomy"]
    species_mentioned: List[str]
    tools_planned: List[ToolPlan]


class ALAiChatBioAgent:
    """The iChatBio agent implementation for ALA"""

    def __init__(self):
        self.ala_logic = ALA()
       
            
    async def create_research_plan(self, request: str, species_names: list[str]) -> ResearchPlan:
        parser = JsonOutputParser(pydantic_object=ResearchPlan)

        planning_prompt = ChatPromptTemplate.from_messages([
            ("system", """
You are an expert biodiversity research planner.

Analyze each query and create a JSON execution plan describing:
- query_type: one of singlespecies, comparison, conservation, distribution, taxonomy
- species_mentioned: list of scientific/common names if known, else "unknown"
- tools_planned: list of dicts with properties {{"tool_name", "priority", "reason"}} using EXACT tool names below.

Available Tools:
- search_species_occurrences: Returns ACTUAL occurrence records (individual sightings with dates, coordinates, collectors). Use for: "show me occurrences", "find sightings", "list observations"
- get_occurrence_breakdown: Returns ANALYTICAL COUNTS and breakdowns by categories (facets). Use for: "how many in each state", "breakdown by year", "count by category", "distribution across", "top X species"
- get_occurrence_taxa_count: Get TOTAL record counts for specific species (just numbers). Use for: "how many records for koala", "count of species X", "total occurrences"
- lookup_species_info: Get comprehensive species profiles, taxonomy, and metadata (BIE search). Use for: "tell me about species", "what is", "taxonomy of"
- get_species_distribution: Get expert distribution maps and geographic range data. Use for: "where does it live", "distribution map", "geographic range"
- get_species_images: Retrieve primary images for Australian species. Use for: "show me a photo", "image of species", "what does it look like"
- finish: Call when the request is successfully completed

Query types:
- singlespecies: Single species info
- comparison: Compare species
- conservation: Conservation status queries
- distribution: Geographic distribution/habitat
- taxonomy: Classification info

Tool priorities (USE ONLY THESE TWO):
- must_call: Essential tools to answer the user's explicit request. ALL must_call tools will execute in sequence. If ANY must_call tool fails, the entire request fails.
- optional: Enhancement tools that add extra value but aren't required. These run ONLY AFTER all must_call tools succeed. If an optional tool fails, it's silently skipped.

**When to use each priority:**
- Use must_call for ANYTHING the user explicitly requested
- Use optional for helpful additions the user didn't ask for (like bonus images or extra context)
- If user asks for multiple things, mark them ALL as must_call

**Critical Query Pattern Rules:**
1. "How many X in EACH Y" → must_call get_occurrence_breakdown (returns counts per category)
2. "Show me X occurrences" → must_call search_species_occurrences (returns actual records)
3. "How many X records" (no "each") → must_call get_occurrence_taxa_count (returns single total)
4. "Break down by X" or "distribution across X" → must_call get_occurrence_breakdown
5. "Tell me about X and show Y" → BOTH are must_call (user wants both)

**Examples:**
- "How many kangaroo records in each state?" → get_occurrence_breakdown (must_call only)
- "Show me koala occurrences" → search_species_occurrences (must_call only)
- "Tell me about koalas" → lookup_species_info (must_call), get_species_images (optional bonus)
- "Show koala occurrences AND their distribution" → search_species_occurrences (must_call), get_species_distribution (must_call)
- "How many koala records?" → get_occurrence_taxa_count (must_call), get_species_images (optional)

Respond ONLY with valid JSON matching the ResearchPlan Pydantic model.
"""),
            ("human", """
Query: "{request}"
Species mentioned: {species}
Create the execution plan.
""")
        ])

        api_key = get_config_value("OPENAI_API_KEY")
        base_url = get_config_value("OPENAI_BASE_URL", "https://api.ai.it.ufl.edu")
        
        llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    api_key=api_key,
                    base_url=base_url
                )

        chain = planning_prompt | llm | parser

        try:
            plan_dict = await chain.ainvoke({
                "request": request,
                "species": species_names if species_names else ["unknown"]
            })
            return ResearchPlan.parse_obj(plan_dict)
        except Exception as e:
            # Fallback if planning fails
            print(f"Warning: Plan creation failed ({e}), using fallback plan")

            tools_planned = [
                ToolPlan(
                    tool_name="lookup_species_info",
                    priority="must_call",
                    reason="Get species taxonomy and metadata"
                ),
                ToolPlan(
                    tool_name="search_species_occurrences",
                    priority="must_call",
                    reason="Occurrence data search for species"
                ),
            ]
            query_type = "singlespecies" if len(species_names) <= 1 else "comparison"
            species_mentioned = species_names if species_names else ["unknown"]
            return ResearchPlan(
                query_type=query_type,
                species_mentioned=species_mentioned,
                tools_planned=tools_planned,
            )
        
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

    async def convert_species_to_guids(self, names: List[str]) -> Dict[str, str]:
        guid_map = {}
        for name in names:
            try:
                params = SpeciesGuidLookupParams(name=name)
                url = self.ala_logic.build_species_guid_lookup_url(params)
                result = self.ala_logic.execute_request(url)
                guid = None
                if isinstance(result, list):
                    for entry in result:
                        if isinstance(entry, dict):
                            guid = (
                                entry.get('taxonConceptID') or
                                entry.get('guid') or
                                entry.get('acceptedIdentifier') or
                                entry.get('identifier')
                            )
                            if guid:
                                break
                elif isinstance(result, dict):
                    guid = (
                        result.get('taxonConceptID') or
                        result.get('guid') or
                        result.get('acceptedIdentifier') or
                        result.get('identifier')
                    )
                
                if guid and guid.startswith("https://biodiversity.org.au/afd/taxa/"):
                    lsid = "urn:lsid:biodiversity.org.au:afd.taxon:" + guid.rsplit("/", 1)[-1]
                    guid_map[name] = lsid
                elif guid:
                    guid_map[name] = guid
                else:
                    print(f"Warning: No GUID found for '{name}' in API response: {result}")
            except Exception as e:
                print(f"Warning: Could not find GUID for '{name}'. Skipping. Error: {e}")
        return guid_map

    async def get_taxa_counts(self, params: TaxaCountHelper) -> dict:
        """
        Orchestrates getting taxa counts from user-friendly names.
        """
        names_to_lookup = (params.species_names or []) + (params.common_names or [])
        if not names_to_lookup:
            raise ValueError("You must provide at least one species or common name.")

        # Step 1: Call the worker function to convert names to GUIDs
        guid_map = await self.convert_species_to_guids(names_to_lookup)
        
        all_guids = list(guid_map.values())
        if not all_guids:
            raise ValueError("Could not resolve any of the provided names to a valid GUID.")

        # Step 2: Construct filter queries (fq)
        fq_filters = []
        if params.state:
            fq_filters.append(f"state:{params.state}")
        if params.year:
            fq_filters.append(f"year:{params.year}")
        if params.basis_of_record:
            fq_filters.append(f"basis_of_record:{params.basis_of_record}")

        # Step 3: Build the final parameters for the API call
        taxa_count_params = OccurrenceTaxaCountParams(
            guids="\n".join(all_guids),
            fq=fq_filters if fq_filters else None
        )
        
        # Step 4: Build the URL and execute the request
        url = self.ala_logic.build_occurrence_taxa_count_url(taxa_count_params)
        return self.ala_logic.execute_request(url), url
    
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
        
    async def run_species_image_search(self, context, params: SpeciesImageSearchParams):
        """
        Workflow for searching and fetching the first available image for a species.
        """
        async with context.begin_process(f"Fetching image for taxon ID '{params.id}'") as process:
            await process.log("Image search parameters", data=params.model_dump())
            
            metadata_url = self.ala_logic.build_species_image_search_url(params)
            await process.log(f"Constructed metadata URL: {metadata_url}")

            try:
                loop = asyncio.get_event_loop()
                image_metadata = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(metadata_url))
                await process.log("Successfully retrieved image metadata.", data=image_metadata)
                
            except ConnectionError as e:
                await process.log("Error during metadata request", data={"error": str(e)})
                await context.reply(f"I encountered an error while searching for image information: {e}")
                return

            except asyncio.TimeoutError:
                await process.log("Image metadata request timed out")
                await context.reply("The image search took too long to respond. Please try again later.")
                return

            image_url = None
            try:
                results = image_metadata.get('searchResults', {}).get('results', [])
                if results and 'imageUrl' in results[0]:
                    image_url = results[0]['imageUrl']
                    await process.log(f"Extracted direct image URL: {image_url}")
                else:
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
                    
    async def _fetch_distribution_data(self, context, lsid: str, species_name: str) -> Dict:
        """
        Fetch spatial distribution data for a given LSID.
        
        Args:
            lsid: Life Science Identifier URL
            species_name: Species name for display
        
        Returns:
            Dict with success, species_name, lsid, record_count, image_ids, data
        """
        async with context.begin_process("Fetching distribution data") as process:
            await process.log(f"Fetching spatial distribution for {species_name}")
            await process.log(f"Using LSID: {lsid}")
            
            try:
                api_url = self.ala_logic.build_spatial_distribution_by_lsid_url(lsid)
                await process.log(f"Distribution API URL: {api_url}")
                
                loop = asyncio.get_event_loop()
                raw_response = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url)),
                    timeout=30.0
                )
                
                await process.log("Successfully retrieved distribution data")
                
                # Extract imageIds from response
                image_ids = []
                if isinstance(raw_response, list):
                    for distribution in raw_response:
                        if isinstance(distribution, dict):
                            geom_idx = distribution.get('geom_idx')
                            if geom_idx:
                                image_ids.append(str(geom_idx))

                # Calculate statistics
                distribution_count = len(raw_response) if isinstance(raw_response, list) else 1
                
                # Create artifact
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Expert spatial distribution data for {species_name} - {distribution_count} areas",
                    uris=[api_url],
                    content=json.dumps(raw_response).encode('utf-8'),
                    metadata={
                        "species_name": species_name,
                        "lsid": lsid,
                        "data_type": "expert_spatial_distribution",
                        "data_source": "ALA Spatial Service",
                        "record_count": distribution_count,
                        "image_ids": image_ids,
                        "image_urls": [dist.get('imageUrl') for dist in raw_response if isinstance(dist, dict) and dist.get('imageUrl')],
                        "retrieval_date": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                )

                # Enhanced: Display distribution images and provide URLs
                image_info = []  
                displayed_images = 0
                
                if image_ids:
                    await process.log(f"Processing {len(image_ids)} distribution map(s)")
                    
                    for i, distribution in enumerate(raw_response):
                        if isinstance(distribution, dict):
                            geom_idx = distribution.get('geom_idx')
                            image_url = distribution.get('imageUrl')
                            area_name = distribution.get('area_name', f'Distribution Area {i+1}')
                            
                            if geom_idx and image_url:
                                image_info.append({
                                    'id': str(geom_idx),
                                    'url': image_url,
                                    'name': area_name
                                })
                                
                                # Display images directly in chat (limit to 3 for performance)
                                if displayed_images < 3:
                                    try:
                                        image_params = SpatialDistributionMapParams(imageId=str(geom_idx))
                                        await self.run_get_distribution_map(context, image_params)
                                        displayed_images += 1
                                        await process.log(f"Displayed distribution map: {area_name}")
                                    except Exception as e:
                                        await process.log(f"Failed to display image {geom_idx}: {e}")
                
                summary = f"Successfully retrieved {distribution_count} expert spatial distribution area(s) for {species_name}. "
                summary += "This data shows geographic areas where experts believe the species should occur based on ecological knowledge.\n\n"

                if image_info:
                    summary += f"**Distribution Maps Available ({len(image_info)} total):**\n"
                    
                    # Show displayed images
                    if displayed_images > 0:
                        summary += f"{displayed_images} map(s) displayed above\n"
                    
                    # Provide URLs for all images
                    summary += "\n**Direct Image URLs:**\n"
                    for img in image_info:
                        summary += f"• **{img['name']}**: {img['url']}\n"
                    
                    # Show remaining if more than 3
                    if len(image_info) > 3:
                        summary += f"\nShowing first 3 images. {len(image_info) - 3} additional map(s) available via URLs above."
                else:
                    summary += "\nNo distribution map images are available for this species."

                await context.reply(summary)
                
                # Return success case INSIDE try block
                return {
                    "success": True,
                    "species_name": species_name,
                    "lsid": lsid,
                    "record_count": distribution_count,
                    "image_ids": image_ids,
                    "data": raw_response
                }

            except asyncio.TimeoutError:
                await process.log("Distribution API timed out")
                await context.reply("API timeout - try again later or refine your request")
                return {"success": False, "error": "timeout"}
                    
            except Exception as e:
                await process.log(f"Error fetching distribution: {e}")
                await context.reply(f"Error fetching distribution data: {e}")
                return {"success": False, "error": str(e)}

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
                raw_response = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url)),
                    timeout=30.0
                )
                
                await process.log("Successfully retrieved facet data")
                
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
                    if isinstance(facet, dict):
                        field_name = facet.get('fieldName', 'Unknown')
                        field_result = facet.get('fieldResult', [])
                        facet_count = len(field_result)
                        facet_fields.append(f"{field_name} ({facet_count} values)")
                        total_facets += facet_count
                
                await process.log(f"Total facet values: {total_facets}")
                
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Occurrence facet data breakdown - {total_facets} total facet values across {len(facet_fields)} fields",
                    uris=[api_url],
                    content=json.dumps(raw_response).encode('utf-8'),  
                    metadata={
                        "data_source": "ALA Occurrence Facets", 
                        "facet_fields": len(facet_fields),
                        "total_facet_values": total_facets,
                        "search_context": search_context.strip(),
                        "retrieval_date": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                )
                
                if facet_fields:
                    summary = f"Found {total_facets} facet values across {len(facet_fields)} categories: {', '.join(facet_fields[:3])}"
                    if len(facet_fields) > 3:
                        summary += f" and {len(facet_fields) - 3} more"
                    summary += "."
                else:
                    summary = "No facet data found - this may indicate no matching records or an API issue."
                
                await context.reply(summary)

            except asyncio.TimeoutError:
                await process.log("Facet API timeout (30s)")
                await context.reply("Facet analysis timed out. Try a more specific query or try again later.")
            except ConnectionError as e:
                await process.log("Error during API request", data={"error": str(e)})
                await context.reply(f"I encountered an error while retrieving occurrence facet data: {e}")
            except Exception as e:
                await process.log(f"Unexpected error: {e}")
                await context.reply(f"An unexpected error occurred during facet analysis: {e}")

    async def process_user_query(self, raw_query: str) -> ALASearchResponse:
        # Step 1: Extract parameters
        extracted = await self.ala_logic.extract_params(
            user_query=raw_query, 
            response_model=ALASearchResponse
        )
        
        # Step 2: Resolve unresolved parameters (including scientific_name, lsid)
        resolver = ALAParameterResolver(self.ala_logic.ala_api_base_url)
        resolved = await resolver.resolve_unresolved_params(extracted)
        
        # Return resolved structured parameters ready for API consumption
        return resolved


class UnifiedALAReActAgent(IChatBioAgent):
    """Unified ALA agent using Pure Plan-Based execution"""
    
    def __init__(self):
        self.workflow_agent = ALAiChatBioAgent()
        
    @override
    async def run(self, context: ResponseContext, request: str, entrypoint: str, params: UnifiedALAParams):
        """Execute the unified biodiversity search using plan-based coordinator"""
        
        # Get API configuration
        api_key = get_config_value("OPENAI_API_KEY")
        base_url = get_config_value("OPENAI_BASE_URL", "https://api.ai.it.ufl.edu")

        if not api_key:
            await context.reply("Error: OpenAI API key not found in environment or env.yaml file")
            return

        # Step 1: Extract and resolve parameters once at the start
        resolved_params = await self.workflow_agent.process_user_query(request)
        
        # Extract species names from params dict (they can be in different fields)
        species_names = []
        if 'scientific_name' in resolved_params.params:
            sci_name = resolved_params.params['scientific_name']
            species_names = [sci_name] if isinstance(sci_name, str) else sci_name
        elif 'species_name' in resolved_params.params:
            sp_name = resolved_params.params['species_name']
            species_names = [sp_name] if isinstance(sp_name, str) else sp_name
        elif 'q' in resolved_params.params:
            # Use the query parameter as fallback
            species_names = [resolved_params.params['q']]

        # Step 2: Create the execution plan from user query and resolved species
        plan = await self.workflow_agent.create_research_plan(request, species_names)

        # Step 3: Begin execution process
        async with context.begin_process("Executing ALA biodiversity search") as process:
            await process.log(f"Created execution plan with {len(plan.tools_planned)} tools")
            await process.log(f"Query type: {plan.query_type}")
            await process.log(f"Species mentioned: {', '.join(plan.species_mentioned)}")

        # Step 4: Define tool closures that execute workflows
        async def _search_species_occurrences(resolved_obj):
            """Search for species occurrence records"""
            try:
                occurrence_params, missing = map_params_to_model(resolved_obj.params, OccurrenceSearchParams)
                if missing:
                    return {"success": False, "message": f"Please provide missing information: {', '.join(missing)}"}
                
                await self.workflow_agent.run_occurrence_search(context, occurrence_params)
                return {"success": True, "message": f"Successfully found occurrence records"}
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                print(f"ERROR in _search_species_occurrences: {error_detail}")
                return {"success": False, "message": f"Error executing search: {str(e)}"}

        async def _get_species_images(resolved_obj):
            """Retrieve species images"""
            species_id = None
            
            # Try to get ID from params or as direct attribute
            if hasattr(resolved_obj, 'params'):
                species_id = resolved_obj.params.get('id') or resolved_obj.params.get('lsid')
            elif hasattr(resolved_obj, 'id'):
                species_id = resolved_obj.id
            
            if not species_id:
                return {"success": False, "message": "No valid species identifier provided to fetch images."}
            try:
                # Create SpeciesImageSearchParams with the id
                image_params = SpeciesImageSearchParams(id=species_id)
                await self.workflow_agent.run_species_image_search(context, image_params)
                return {"success": True, "message": f"Species image search completed for identifier '{species_id}'."}
            except Exception as e:
                return {"success": False, "message": f"Error fetching images: {str(e)}"}

        async def _lookup_species_info(resolved_obj):
            """Look up comprehensive species information"""
            # Try to get species name from params dict
            species_names = None
            if hasattr(resolved_obj, 'params'):
                species_names = (resolved_obj.params.get('scientific_name') or 
                               resolved_obj.params.get('species_name') or 
                               resolved_obj.params.get('common_name') or
                               resolved_obj.params.get('q'))
            
            if not species_names:
                return {"success": False, "message": "No species name provided for lookup."}
            
            species_name = species_names[0] if isinstance(species_names, list) else species_names
            try:
                params = SpeciesBieSearchParams(q=species_name)
                await self.workflow_agent.run_species_bie_search(context, params)
                return {"success": True, "message": f"Found species information for {species_name}"}
            except Exception as e:
                return {"success": False, "message": f"Error looking up species info: {str(e)}"}

        async def _get_species_distribution(resolved_obj):
            """Get expert spatial distribution data"""
            lsid = None
            species_name = None
            
            # Access from params dict
            if hasattr(resolved_obj, 'params'):
                lsid = resolved_obj.params.get('lsid')
                
                # Try different possible name fields
                sci_name = resolved_obj.params.get('scientific_name')
                if sci_name:
                    species_name = sci_name[0] if isinstance(sci_name, list) else sci_name
                else:
                    common = resolved_obj.params.get('common_name') or resolved_obj.params.get('q')
                    if common:
                        species_name = common[0] if isinstance(common, list) else common

            if not lsid and not species_name:
                return {"success": False, "message": "No valid species identifier (LSID or scientific/common name) provided for distribution lookup."}

            try:
                if lsid:
                    result = await self.workflow_agent._fetch_distribution_data(context, lsid, species_name or "Unknown species")
                else:
                    return {"success": False, "message": "LSID missing; cannot fetch distribution data without resolved LSID."}
                if result and result.get("success"):
                    return {"success": True, "message": f"Retrieved distribution for {result['species_name']}: {result['record_count']} area(s)", "data": result}
                else:
                    error = result.get("error", "unknown") if result else "species not found"
                    return {"success": False, "message": f"Could not retrieve distribution: {error}"}
            except Exception as e:
                return {"success": False, "message": f"Error processing distribution request: {str(e)}"}

        async def _get_occurrence_breakdown(resolved_obj):
            """Get analytical breakdowns from occurrence data"""
            try:
                params = OccurrenceFacetsParams(**resolved_obj.params)
                await self.workflow_agent.run_get_occurrence_facets(context, params)
                return {"success": True, "message": "Successfully processed occurrence breakdown request"}
            except Exception as e:
                return {"success": False, "message": f"Error processing breakdown: {str(e)}"}

        async def _get_occurrence_taxa_count(resolved_obj):
            """Get occurrence counts for species"""
            try:
                await self.workflow_agent.run_user_friendly_taxa_count(context, resolved_obj)
                return {"success": True, "message": "Successfully processed taxa count request."}
            except Exception as e:
                return {"success": False, "message": f"Error processing taxa count: {e}"}

        async def _finish(summary: str):
            """Mark completion"""
            await context.reply(summary)
            return {"success": True, "message": summary}

        # Step 5: Map tool names to their implementations
        tool_map = {
            "search_species_occurrences": _search_species_occurrences,
            "get_species_images": _get_species_images,
            "lookup_species_info": _lookup_species_info,
            "get_species_distribution": _get_species_distribution,
            "get_occurrence_breakdown": _get_occurrence_breakdown,
            "get_occurrence_taxa_count": _get_occurrence_taxa_count,
            "finish": _finish
        }

        # Step 6: Execute planned tools in two phases
        executed_tools = []  # Track which tools have been executed
        
        async with context.begin_process("Executing planned tools") as process:
            await process.log(f"Total tools planned: {len(plan.tools_planned)}")
            await process.log(f"Tool execution order: {[(t.tool_name, t.priority) for t in plan.tools_planned]}")
            
            # PHASE 1: Execute ALL must_call tools
            must_call_tools = [t for t in plan.tools_planned if t.priority == "must_call"]
            await process.log(f"Phase 1: Executing {len(must_call_tools)} must_call tool(s)")
            
            for tool_plan in must_call_tools:
                tool_name = tool_plan.tool_name
                
                # Skip if already executed
                if tool_name in executed_tools:
                    await process.log(f"Skipping '{tool_name}' - already executed")
                    continue
                    
                tool_fn = tool_map.get(tool_name)
                if tool_fn is None:
                    await context.reply(f"Error: Planned tool '{tool_name}' is not implemented.")
                    return

                await process.log(f"Executing must_call tool: {tool_name} - {tool_plan.reason}")
                
                # Execute the tool
                try:
                    if tool_name == "finish":
                        result = await tool_fn("All required operations completed")
                    else:
                        result = await tool_fn(resolved_params)
                    
                    executed_tools.append(tool_name)
                    
                except Exception as e:
                    result = {"success": False, "message": f"Tool {tool_name} raised exception: {e}"}

                # Check result
                if result.get("success"):
                    await process.log(f"Must-call tool '{tool_name}' succeeded")
                else:
                    # Must-call failed - stop everything
                    error_msg = result.get('message', 'Unknown error')
                    await process.log(f"Must-call tool '{tool_name}' FAILED: {error_msg}")
                    await context.reply(f"Required operation failed: {error_msg}")
                    return  # Exit - don't run any more tools
            
            # PHASE 2: All must_calls succeeded, now execute optional tools
            optional_tools = [t for t in plan.tools_planned if t.priority == "optional"]
            
            if optional_tools:
                await process.log(f"Phase 2: Executing {len(optional_tools)} optional tool(s)")
                
                for tool_plan in optional_tools:
                    tool_name = tool_plan.tool_name
                    
                    # Skip if already executed
                    if tool_name in executed_tools:
                        await process.log(f"Skipping '{tool_name}' - already executed")
                        continue
                        
                    tool_fn = tool_map.get(tool_name)
                    if tool_fn is None:
                        await process.log(f"Skipping '{tool_name}' - not implemented")
                        continue

                    await process.log(f"Executing optional tool: {tool_name} - {tool_plan.reason}")
                    
                    # Execute the tool
                    try:
                        if tool_name == "finish":
                            result = await tool_fn("Optional enhancements completed")
                        else:
                            result = await tool_fn(resolved_params)
                        
                        executed_tools.append(tool_name)
                        
                    except Exception as e:
                        result = {"success": False, "message": f"Tool {tool_name} raised exception: {e}"}

                    # Check result
                    if result.get("success"):
                        await process.log(f"Optional tool '{tool_name}' succeeded")
                    else:
                        # Optional failed - log but continue
                        error_msg = result.get('message', 'Unknown error')
                        await process.log(f"Optional tool '{tool_name}' failed (continuing): {error_msg}")
                        # Don't return - keep going to next optional tool
            else:
                await process.log("No optional tools to execute")
            
            # PHASE 3: All tools completed
            await process.log(f"Completed execution: {len(executed_tools)} tool(s) executed successfully")