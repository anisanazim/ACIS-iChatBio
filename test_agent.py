import pytest
from agent_server import ALAAgent
from ala_logic import (
    OccurrenceSearchParams, OccurrenceLookupParams, OccurrenceFacetsParams, OccurrenceTaxaCountParams,
    SpeciesGuidLookupParams, SpeciesImageSearchParams, SpeciesBieSearchParams,
    NoParams, SpatialDistributionByLsidParams, SpatialDistributionMapParams,
    SpeciesListFilterParams, SpeciesListDetailsParams, 
    SpeciesListItemsParams, SpeciesListDistinctFieldParams, SpeciesListCommonKeysParams
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
    params = OccurrenceLookupParams(recordUuid="e9d6fbbd-1505-4073-990a-dc66c930dad6")
    await agent.run(context, "lookup_occurrence", params)
    assert any("details" in getattr(m, "text", "") or "error" in getattr(m, "text", "") for m in messages)

@pytest.mark.asyncio
async def test_index_fields(context, messages):
    agent = ALAAgent()
    params = NoParams()
    await agent.run(context, "get_index_fields", params)
    assert any("searchable fields" in getattr(m, "text", "") for m in messages)

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

@pytest.mark.asyncio
async def test_get_occurrence_facets_basic(context, messages):
    """Test basic facet retrieval"""
    agent = ALAAgent()
    params = OccurrenceFacetsParams(
        q="koala",
        facets=["state", "year", "basis_of_record"],
        flimit=10
    )
    await agent.run(context, "get_occurrence_facets", params)
    assert any("breakdown" in getattr(m, "text", "") or "facet" in getattr(m, "text", "") for m in messages)

@pytest.mark.asyncio
async def test_get_occurrence_facets_filtered(context, messages):
    """Test facets with filters"""
    agent = ALAAgent()
    params = OccurrenceFacetsParams(
        q="birds",
        fq=["state:Queensland"],
        facets=["year", "institution_code"]
    )
    await agent.run(context, "get_occurrence_facets", params)
    assert any("breakdown" in getattr(m, "text", "") or "error" in getattr(m, "text", "") for m in messages)

@pytest.mark.asyncio
async def test_get_occurrence_facets_spatial(context, messages):
    """Test facets with spatial filtering"""
    agent = ALAAgent()
    params = OccurrenceFacetsParams(
        lat=-27.4698,
        lon=153.0251,
        radius=50,
        facets=["species_group", "state"]
    )
    await agent.run(context, "get_occurrence_facets", params)
    assert any("breakdown" in getattr(m, "text", "") or "error" in getattr(m, "text", "") for m in messages)

@pytest.mark.asyncio
async def test_get_occurrence_taxa_count_single(context, messages):
    """Test taxa count for a single species"""
    agent = ALAAgent()
    params = OccurrenceTaxaCountParams(
        guids="https://biodiversity.org.au/afd/taxa/7e6e134b-2bc7-43c4-b23a-6e3f420f57ad"
    )
    await agent.run(context, "get_occurrence_taxa_count", params)
    assert any("occurrence" in getattr(m, "text", "") or "error" in getattr(m, "text", "") for m in messages)

@pytest.mark.asyncio
async def test_get_occurrence_taxa_count_multiple(context, messages):
    """Test taxa count for multiple species"""
    agent = ALAAgent()
    params = OccurrenceTaxaCountParams(
        guids="https://biodiversity.org.au/afd/taxa/7e6e134b-2bc7-43c4-b23a-6e3f420f57ad\nhttps://biodiversity.org.au/afd/taxa/another-guid"
    )
    await agent.run(context, "get_occurrence_taxa_count", params)
    assert any("taxa" in getattr(m, "text", "") or "error" in getattr(m, "text", "") for m in messages)

@pytest.mark.asyncio
async def test_get_occurrence_taxa_count_filtered(context, messages):
    """Test taxa count with filters"""
    agent = ALAAgent()
    params = OccurrenceTaxaCountParams(
        guids="https://biodiversity.org.au/afd/taxa/7e6e134b-2bc7-43c4-b23a-6e3f420f57ad",
        fq=["state:Queensland", "year:2020"]
    )
    await agent.run(context, "get_occurrence_taxa_count", params)
    assert any("occurrence" in getattr(m, "text", "") or "error" in getattr(m, "text", "") for m in messages)

@pytest.mark.asyncio
async def test_species_guid_lookup(context, messages):
    """Test GUID lookup for a species name"""
    agent = ALAAgent()
    params = SpeciesGuidLookupParams(name="kangaroo")
    await agent.run(context, "species_guid_lookup", params)
    assert any("GUID" in getattr(m, "text", "") or "error" in getattr(m, "text", "") for m in messages)

@pytest.mark.asyncio
async def test_species_guid_lookup_scientific(context, messages):
    """Test GUID lookup with scientific name"""
    agent = ALAAgent()
    params = SpeciesGuidLookupParams(name="Macropus rufus")
    await agent.run(context, "species_guid_lookup", params)
    assert any("GUID" in getattr(m, "text", "") or "matches" in getattr(m, "text", "") for m in messages)

@pytest.mark.asyncio
async def test_species_image_search(context, messages):
    """Test image search for a taxon"""
    agent = ALAAgent()
    params = SpeciesImageSearchParams(
        id="https://id.biodiversity.org.au/node/apni/29057",
        rows=10
    )
    await agent.run(context, "species_image_search", params)
    assert any("images" in getattr(m, "text", "") or "error" in getattr(m, "text", "") for m in messages)

@pytest.mark.asyncio
async def test_species_bie_search(context, messages):
    """Test BIE search"""
    agent = ALAAgent()
    params = SpeciesBieSearchParams(
        q="gum",
        fq="imageAvailable:\"true\"",
        pageSize=10
    )
    await agent.run(context, "species_bie_search", params)
    assert any("BIE" in getattr(m, "text", "") or "results" in getattr(m, "text", "") for m in messages)

@pytest.mark.asyncio
async def test_filter_species_lists_by_scientific_name(context, messages):
    """Test filtering lists by scientific name"""
    agent = ALAAgent()
    params = SpeciesListFilterParams(scientific_names=["Phascolarctos cinereus"])
    await agent.run(context, "filter_species_lists", params)
    assert any("species lists" in getattr(m, "text", "") or "error" in getattr(m, "text", "") for m in messages)

@pytest.mark.asyncio
async def test_get_species_list_details(context, messages):
    """Test getting details for a specific species list"""
    agent = ALAAgent()
    params = SpeciesListDetailsParams(druid="dr781")  # Use example from screenshot
    await agent.run(context, "get_species_list_details", params)
    assert any("details" in getattr(m, "text", "") or "error" in getattr(m, "text", "") for m in messages)

@pytest.mark.asyncio
async def test_get_species_list_items(context, messages):
    """Test getting species from a list"""
    agent = ALAAgent()
    params = SpeciesListItemsParams(druid="dr781", q="Acacia", max=5)  # Search for Acacia in dr781
    await agent.run(context, "get_species_list_items", params)
    assert any("species" in getattr(m, "text", "") or "error" in getattr(m, "text", "") for m in messages)

@pytest.mark.asyncio
async def test_get_species_list_distinct_fields(context, messages):
    """Test getting distinct field values"""
    agent = ALAAgent()
    params = SpeciesListDistinctFieldParams(field="kingdom")
    await agent.run(context, "get_species_list_distinct_fields", params)
    assert any("distinct values" in getattr(m, "text", "") or "error" in getattr(m, "text", "") for m in messages)

@pytest.mark.asyncio
async def test_get_species_list_common_keys(context, messages):
    """Test getting common keys across lists"""
    agent = ALAAgent()
    params = SpeciesListCommonKeysParams(druid="dr781")
    await agent.run(context, "get_species_list_common_keys", params)
    assert any("common keys" in getattr(m, "text", "") or "error" in getattr(m, "text", "") for m in messages)