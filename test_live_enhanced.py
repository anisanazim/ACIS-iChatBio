import pytest
import os
from ala_agent import ALA

# --- Markers for Pytest ---
# This marker skips tests that require the OpenAI API key if it's not found.
requires_openai_key = pytest.mark.skipif(
    not (os.getenv("OPENAI_API_KEY") or os.path.exists("env.yaml")),
    reason="This test requires a live OPENAI_API_KEY"
)

# This marker skips tests that require the authenticated ALA Species API key.
requires_ala_key = pytest.mark.skipif(
    not os.getenv("ALA_API_KEY"),
    reason="This test requires a live ALA_API_KEY for the species endpoint"
)


# --- Test Fixture ---
@pytest.fixture(scope="module")
def live_ala_instance():
    """Provides a single, live instance of the ALA class for all tests."""
    return ALA()

@requires_openai_key
class TestLiveWorkflow:
    """
    Tests the primary "happy path" workflows for occurrence searches,
    covering all major parameter types and combinations from your test plan.
    """

    @pytest.mark.parametrize(
        "query, expected_params, expected_url_parts, expected_output",
        [
            # Query 1: Boolean Flag (has_images)
            (
                "I need photos of the Laughing Kookaburra",
                {"has_images=True", "scientificname='Dacelo novaeguineae'"},
                ["q=Dacelo%20novaeguineae", "fq=multimedia%3AImage"],
                ["Dacelo novaeguineae", "total records"]
            ),
            # Query 2: Filter with Spaces
            (
                "show me koalas in New South Wales",
                {"state='New South Wales'", "scientificname='Phascolarctos cinereus'"},
                ["q=Phascolarctos%20cinereus", "state%3A%22New%20South%20Wales%22"],
                ["Phascolarctos cinereus", "New South Wales, Australia"]
            ),
            # Query 3: Taxonomic Rank Filter
            (
                "list all species from the family Macropodidae",
                {"family='Macropodidae'"},
                ["fq=family%3AMacropodidae"],
                ["total records", "Macropus"] # Check for a common genus in the family
            ),
            # Query 4: Location + Time Range
            (
                "platypus sightings in Tasmania between 2020-01-01 and 2022-12-31",
                {"state='Tasmania'", "startdate='2020-01-01'", "enddate='2022-12-31'"},
                ["state%3A%22Tasmania%22", "occurrence_date%3A%5B2020-01-01T00%3A00%3A00Z%20TO%202022-12-31T23%3A59%3A59Z%5D"],
                ["Ornithorhynchus anatinus", "Tasmania, Australia"]
            ),
            # Query 5: Location + Attribute
            (
                "find me wedge-tailed eagles in Western Australia that have GPS coordinates",
                {"state='Western Australia'", "has_coordinates=True"},
                ["state%3A%22Western%20Australia%22", "geospatial_kosher%3Atrue"],
                ["Aquila audax", "Western Australia"]
            ),
            # Query 6: Specific Record Type (basis_of_record)
            (
                "show me preserved specimens of the Tasmanian Devil",
                {"basis_of_record='PreservedSpecimen'", "state='Tasmania'"},
                ["basis_of_record%3A%22PreservedSpecimen%22", "state%3A%22Tasmania%22"],
                ["Sarcophilus harrisii", "PreservedSpecimen"]
            ),
        ]
    )
    def test_occurrence_workflow(self, live_ala_instance, capsys, query, expected_params, expected_url_parts, expected_output):
        """Validates the entire workflow: param extraction, URL building, and final summary."""
        result_summary = live_ala_instance.search_occurrences(query)
        captured = capsys.readouterr()
        console_output = captured.out

        for param_str in expected_params:
            assert param_str in console_output
        for url_part in expected_url_parts:
            assert url_part in console_output
        for output_str in expected_output:
            assert output_str in result_summary

@requires_openai_key

class TestLiveEdgeCases:
    """
    A test class dedicated to testing edge cases, ambiguous queries,
    and invalid user inputs.
    """

    def test_no_results_found(self, live_ala_instance):
        """Query 7: Tests a query guaranteed to return zero results."""
        query = "show me penguins in the year 1700"
        result_summary = live_ala_instance.search_occurrences(query)
        assert "No occurrences found" in result_summary

    def test_species_fallback_workflow(self, live_ala_instance, capsys):
        """Query 8: Verifies the species fallback mechanism when the API key is missing."""
        result_summary = live_ala_instance.search_species("get me info on the Barramundi")
        captured = capsys.readouterr()
        console_output = captured.out
        
        assert "Species API failed" in console_output
        assert "Falling back to occurrence search" in console_output
        assert "retrieved from occurrence records" in result_summary
        assert "Scientific Name:" in result_summary

    @pytest.mark.parametrize(
        "query, expected_strings",
        [
            # Query 9 & 10: Common and Scientific Name (via fallback)
            ("tell me about the koala", ["Phascolarctos cinereus"]),
            ("give me a profile for Phascolarctos cinereus", ["Phascolarctos cinereus"]),
            # Query 11: LSID Lookup (via fallback)
            ("lookup urn:lsid:biodiversity.org.au:afd.taxon:31a9b8b8-4e8f-4343-a15f-2ed24e0bf1ae", ["Solieriaceae"]),
        ]
    )
    def test_species_identifier_fallback(self, live_ala_instance, query, expected_strings):
        """Tests various species identifiers using the fallback mechanism."""
        result = live_ala_instance.search_species(query)
        for expected_string in expected_strings:
            assert expected_string in result

@requires_ala_key
@requires_openai_key
class TestLiveAuthenticated:
    """
    Tests functionality that requires a real ALA_API_KEY for the species endpoint.
    These tests will be SKIPPED if the key is not set as an environment variable.
    """
    
    def test_successful_species_api_call(self, live_ala_instance, capsys):
        """# Query 12: Tests a successful, authenticated call to the main species API."""
        query = "give me a profile for Phascolarctos cinereus"
        result_summary = live_ala_instance.search_species(query)
        captured = capsys.readouterr()
        console_output = captured.out

        # The most important assertion: the fallback was NOT used.
        assert "Species API call successful" in console_output
        assert "Falling back" not in console_output

        # Assert that the formatted output from the real species API is present.
        assert "## Taxonomic Classification" in result_summary
        assert "**LSID:**" in result_summary