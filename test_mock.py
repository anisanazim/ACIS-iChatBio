import pytest
import requests
from unittest.mock import MagicMock, patch

# Import the classes and models from your agent script
from ala_agent import ALA, OccurrenceSearchParams, SpeciesSearchParams

@pytest.fixture
def ala_instance(mocker):
    """
    Provides a mocked instance of the ALA class for testing.
    - Mocks the OpenAI class to prevent its actual instantiation.
    - Mocks requests.get to prevent actual API calls.
    """
    # Patch the OpenAI class within the ala_agent module before ALA is instantiated.
    mocker.patch('ala_agent.OpenAI', return_value=MagicMock())
    
    # Patch the requests.get method to control API responses for all tests.
    mocker.patch('requests.get')
    
    # Now, it is safe to instantiate the ALA class.
    ala = ALA()
    
    # Mock the parameter extraction methods directly on the instance.
    ala.extract_search_parameters = MagicMock()
    ala.extract_species_parameters = MagicMock()

    return ala

# --- A. Occurrences API Testing ---

class TestOccurrenceSearches:
    """
    Tests for the `search_occurrences` workflow, covering single filters,
    combinations, and edge cases.
    """

    # 1. Core Functionality & Single Filters (Refactored with parametrize)
    @pytest.mark.parametrize(
        "query, mock_params, expected_url_part",
        [
            # Query 1: Basic Scientific Name
            ("find records of Macropus rufus", 
             OccurrenceSearchParams(scientificname="Macropus rufus"), 
             "q=Macropus%20rufus"),
            # Query 2: Common Name Translation
            ("koala sightings", 
             OccurrenceSearchParams(scientificname="Phascolarctos cinereus"), 
             "q=Phascolarctos%20cinereus"),
            # Query 3: Filter with Spaces
            ("show me koalas in New South Wales", 
             OccurrenceSearchParams(scientificname="Phascolarctos cinereus", state="New South Wales"), 
             'fq=state%3A%22New%20South%20Wales%22'),
            # Query 4: Boolean Flag (has_images)
            ("I need photos of the Laughing Kookaburra", 
             OccurrenceSearchParams(scientificname="Dacelo novaeguineae", has_images=True), 
             "fq=multimedia%3AImage"),
            # Query 5: Numeric Filter (year)
            ("any platypus sightings in 2023", 
             OccurrenceSearchParams(scientificname="Ornithorhynchus anatinus", year="2023"), 
             "fq=year%3A2023"),
            # Query 6: Taxonomic Rank Filter (family)
            ("list all species from the family Macropodidae", 
             OccurrenceSearchParams(family="Macropodidae"), 
             "fq=family%3AMacropodidae"),
            # Query 11: Specific Record Type (basis_of_record)
            ("show me preserved specimens of the Tasmanian Devil",
             OccurrenceSearchParams(scientificname="Sarcophilus harrisii", basis_of_record="PreservedSpecimen"),
             'fq=basis_of_record%3A%22PreservedSpecimen%22')
        ]
    )
    def test_single_filter_queries(self, ala_instance, query, mock_params, expected_url_part):
        """ Tests various single-parameter queries. """
        ala_instance.extract_search_parameters.return_value = mock_params
        requests.get.return_value.status_code = 200
        requests.get.return_value.json.return_value = {"totalRecords": 1, "occurrences": [{}]}

        ala_instance.search_occurrences(query)

        ala_instance.extract_search_parameters.assert_called_with(query)
        call_args, _ = requests.get.call_args
        assert expected_url_part in call_args[0]

    # 2. Combining Multiple Filters
    def test_complex_combination_query(self, ala_instance):
        """
        Query 9: Tests a complex query combining genus, state, and has_images.
        """
        query = "I want pictures of any animal from the genus Eucalyptus in Victoria"
        mock_params = OccurrenceSearchParams(genus="Eucalyptus", state="Victoria", has_images=True)
        ala_instance.extract_search_parameters.return_value = mock_params
        requests.get.return_value.status_code = 200
        requests.get.return_value.json.return_value = {"totalRecords": 123, "occurrences": [{}]}
        
        ala_instance.search_occurrences(query)

        ala_instance.extract_search_parameters.assert_called_with(query)
        call_args, _ = requests.get.call_args
        url = call_args[0]
        assert "fq=genus%3AEucalyptus" in url
        assert "state%3A%22Victoria%22" in url
        assert "multimedia%3AImage" in url
    
    def test_no_results_found_query(self, ala_instance):
        """
        Query 12: Tests graceful handling of a query that returns zero results.
        """
        query = "show me penguins in Kakadu National Park"
        mock_params = OccurrenceSearchParams(family="Spheniscidae", locality="Kakadu National Park")
        ala_instance.extract_search_parameters.return_value = mock_params
        
        requests.get.return_value.status_code = 200
        requests.get.return_value.json.return_value = {"totalRecords": 0, "occurrences": []}

        result = ala_instance.search_occurrences(query)

        assert "No occurrences found" in result

# --- B. Species API Testing ---

class TestSpeciesSearches:
    """
    Tests for the `search_species` workflow, including the fallback mechanism.
    """

    def test_species_api_fallback_mechanism(self, mocker, ala_instance):
        """
        Query 16: Explicitly tests the species search fallback mechanism.
        """
        query = "get me info on the Barramundi"
        mock_params = SpeciesSearchParams(name="Barramundi")
        ala_instance.extract_species_parameters.return_value = mock_params

        # Mock the primary API call to fail
        mocker.patch.object(ala_instance, 'execute_species_search', side_effect=requests.HTTPError("401 Unauthorized"))
        
        # Mock the fallback API call to succeed
        fallback_data = {
            "totalRecords": 1,
            "occurrences": [{"scientificName": "Lates calcarifer", "family": "Latidae"}]
        }
        mocker.patch.object(ala_instance, 'execute_search', return_value=fallback_data)
        
        result = ala_instance.search_species(query)

        ala_instance.execute_species_search.assert_called_once()
        ala_instance.execute_search.assert_called_once()
        assert "Note: This information was retrieved from occurrence records" in result
        assert "Scientific Name: Lates calcarifer" in result