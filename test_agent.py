import pytest
from agent_server import ALAAgent
from ala_logic import (
    OccurrenceSearchParams, SpeciesSearchParams, OccurrenceLookupParams, 
    SpeciesLookupParams, NoParams, SpatialDistributionByLsidParams,SpatialDistributionMapParams
)

@pytest.mark.asyncio
async def test_search_occurrences(context, messages):
    agent = ALAAgent()
    params = OccurrenceSearchParams(scientificname="Macropus rufus", state="Queensland")
    await agent.run(context, "search_occurrences", params)
    assert any("matching records" in getattr(m, "text", "") for m in messages)

@pytest.mark.asyncio
async def test_lookup_occurrence(context, messages):
    agent = ALAAgent()
    params = OccurrenceLookupParams(uuid="e9d6fbbd-1505-4073-990a-dc66c930dad6")  # Replace with a valid UUID
    await agent.run(context, "lookup_occurrence", params)
    assert any("details" in getattr(m, "text", "") or "error" in getattr(m, "text", "") for m in messages)

@pytest.mark.asyncio
async def test_index_fields(context, messages):
    agent = ALAAgent()
    params = NoParams()
    await agent.run(context, "get_index_fields", params)
    assert any("searchable fields" in getattr(m, "text", "") for m in messages)

@pytest.mark.asyncio
async def test_search_species(context, messages):
    agent = ALAAgent()
    params = SpeciesSearchParams(q="rk_genus:Macropus")
    await agent.run(context, "search_species", params)
    assert any("total matches" in getattr(m, "text", "") for m in messages)

@pytest.mark.asyncio
async def test_lookup_species(context, messages):
    agent = ALAAgent()
    params = SpeciesLookupParams(name="Malurus cyaneus")
    await agent.run(context, "lookup_species", params)
    assert any("matching profile" in getattr(m, "text", "") for m in messages)

@pytest.mark.asyncio
async def test_spatial_list_distributions(context, messages):
    agent = ALAAgent()
    params = NoParams()
    await agent.run(context, "list_distributions", params)
    assert any("expert distributions" in getattr(m, "text", "") for m in messages)

@pytest.mark.asyncio
async def test_spatial_get_distribution_by_lsid(context, messages):
    agent = ALAAgent()
    params = SpatialDistributionByLsidParams(lsid="https://biodiversity.org.au/afd/taxa/6a01d711-2ac6-4928-bab4-a1de1a58e995") 
    await agent.run(context, "get_distribution_by_lsid", params)
    assert any("distribution data" in getattr(m, "text", "") for m in messages)

@pytest.mark.asyncio
async def test_spatial_get_distribution_map(context, messages):
    agent = ALAAgent()
    params = SpatialDistributionMapParams(imageId="30444")  
    await agent.run(context, "get_distribution_map", params)
    assert any("PNG map image" in getattr(m, "text", "") for m in messages)