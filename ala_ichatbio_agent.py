import asyncio
from typing import AsyncIterator, Optional, Dict, Any, List
from pydantic import BaseModel
import json
from ala_logic import ALA, OccurrenceSearchParams, SpeciesSearchParams, OccurrenceLookupParams, SpeciesLookupParams 

# Define the iChatBio message types
class Message(BaseModel): pass
class ProcessMessage(Message):
    summary: Optional[str] = None; description: Optional[str] = None; data: Optional[Dict[str, Any]] = None
class TextMessage(Message):
    text: str
class ArtifactMessage(Message):
    mimetype: str; description: str; uris: List[str]; metadata: Dict[str, Any]

class ALAiChatBioAgent:
    """The iChatBio agent implementation for ALA."""
    def __init__(self):
        self.ala_logic = ALA()

    async def run_occurrence_search(self, user_query: str) -> AsyncIterator[Message]:
        yield ProcessMessage(summary="Extracting Parameters", description=f"Processing query: '{user_query}'")
        try:
            params = await self.ala_logic._extract_params(user_query, OccurrenceSearchParams)
            yield ProcessMessage(description="Extracted search parameters", data=params.model_dump(exclude_defaults=True))
        except ValueError as e:
            yield ProcessMessage(summary="Error", description=str(e)); return

        api_url = self.ala_logic.build_occurrence_url(params)
        yield ProcessMessage(description=f"Constructed API URL: {api_url}")

        yield ProcessMessage(summary="Querying ALA", description="Requesting occurrence data...")
        try:
            loop = asyncio.get_event_loop()
            raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
            total = raw_response.get('totalRecords', 0)
            returned = len(raw_response.get('occurrences', []))
            yield TextMessage(text=f"Query returned {returned} of {total} matching records.")
            yield ArtifactMessage(mimetype="application/json", description=f"Raw JSON for {returned} ALA records.", uris=[api_url], metadata={"record_count": returned, "total_matches": total})
        except ConnectionError as e:
            yield ProcessMessage(summary="Error", description=str(e)); return

    async def run_occurrence_lookup(self, params: OccurrenceLookupParams) -> AsyncIterator[Message]:
        """Workflow for looking up a single occurrence record."""
        yield ProcessMessage(summary="Looking up record", description=f"Fetching occurrence record with UUID: {params.uuid}")

        api_url = self.ala_logic.build_occurrence_lookup_url(params)
        yield ProcessMessage(description=f"Constructed API URL: {api_url}")

        try:
            loop = asyncio.get_event_loop()
            raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
            
            # Extract a summary for the TextMessage
            processed_occurrence = raw_response.get('processed', {})
            scientific_name = processed_occurrence.get('scientificName', 'Unknown Species')
            event_date = processed_occurrence.get('eventDate', 'No Date')

            yield TextMessage(text=f"Successfully found record for '{scientific_name}' observed on {event_date}.")
            
            yield ArtifactMessage(
                mimetype="application/json",
                description=f"Raw JSON for occurrence record {params.uuid}",
                uris=[api_url],
                metadata={"data_source": "ALA Occurrences", "uuid": params.uuid}
            )

        except ConnectionError as e:
            yield ProcessMessage(summary="Error", description=str(e))
            return
        
    async def run_get_index_fields(self) -> AsyncIterator[Message]:
        """Workflow for getting all available index fields."""
        yield ProcessMessage(summary="Fetching fields", description="Requesting all available index fields from ALA...")

        api_url = self.ala_logic.build_index_fields_url()
        yield ProcessMessage(description=f"Constructed API URL: {api_url}")

        try:
            loop = asyncio.get_event_loop()
            raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
            
            field_count = len(raw_response)
            yield TextMessage(text=f"Successfully found {field_count} indexed fields available for searching.")
            
            yield ArtifactMessage(
                mimetype="application/json",
                description=f"Raw JSON list of all {field_count} indexed fields.",
                uris=[api_url],
                metadata={"data_source": "ALA Index Fields", "field_count": field_count}
            )

        except ConnectionError as e:
            yield ProcessMessage(summary="Error", description=str(e))
            return
            
    async def run_species_lookup(self, user_query: str) -> AsyncIterator[Message]:
        """Workflow for looking up a single species profile using the reliable search endpoint."""
        yield ProcessMessage(summary="Extracting Species Parameters", description=f"Processing query: '{user_query}'")
        try:
            params = await self.ala_logic._extract_params(user_query, SpeciesLookupParams)
            yield ProcessMessage(description="Extracted species parameters", data=params.model_dump())
        except ValueError as e:
            yield ProcessMessage(summary="Error", description=str(e)); return

        search_params = SpeciesSearchParams(q=f"taxon_name:\"{params.name}\"")
        api_url = self.ala_logic.build_species_search_url(search_params)
        
        yield ProcessMessage(summary="Querying ALA Species", description="Requesting species profile via search...")

        try:
            loop = asyncio.get_event_loop()
            raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
            
            results = raw_response.get('searchResults', {}).get('results', [])
            if not results:
                yield TextMessage(text=f"Could not find a species profile for '{params.name}'.")
                return

            # Take the first result as the best match
            species_data = results[0]
            scientific_name = species_data.get('name', 'Unknown Species')
            
            response_text = f"Successfully found a matching profile for {scientific_name}."
            yield TextMessage(text=response_text)

            yield ArtifactMessage(
                mimetype="application/json", description=f"Raw JSON from ALA Species Search for '{scientific_name}'.",
                uris=[api_url], metadata={"data_source": "ALA Species Search", "lsid": species_data.get('guid')}
            )
        except ConnectionError as e:
            yield ProcessMessage(summary="API Error", description=str(e))

    async def run_species_search(self, params: SpeciesSearchParams) -> AsyncIterator[Message]:
        """Workflow for faceted searching of species."""
        yield ProcessMessage(summary="Searching Species", description=f"Searching for species with query: '{params.q}'")

        api_url = self.ala_logic.build_species_search_url(params)
        yield ProcessMessage(description=f"Constructed API URL: {api_url}")

        try:
            loop = asyncio.get_event_loop()
            raw_response = await loop.run_in_executor(None, lambda: self.ala_logic.execute_request(api_url))
            
            results = raw_response.get('searchResults', {}).get('results', [])
            count = len(results)
            total_records = raw_response.get('searchResults', {}).get('totalRecords', 0)

            yield TextMessage(text=f"Found {total_records} total matching species. Returning first {count}.")
            
            yield ArtifactMessage(
                mimetype="application/json",
                description=f"Raw JSON for {count} species matching query '{params.q}'.",
                uris=[api_url],
                metadata={"data_source": "ALA Species Search", "returned_records": count, "total_matches": total_records}
            )
        except ConnectionError as e:
            yield ProcessMessage(summary="Error", description=str(e))