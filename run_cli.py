# run_cli.py
import argparse
import asyncio

from ala_ichatbio_agent import ALAiChatBioAgent
from ala_logic import OccurrenceLookupParams, OccurrenceSearchParams, SpeciesSearchParams,SpeciesLookupParams 

async def main():
    """Parses command-line arguments and runs the agent."""
    parser = argparse.ArgumentParser(description="ALA Agent CLI Test Harness")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Parser for the 'occurrences' command
    p_occ = subparsers.add_parser("occurrences", help="Search for occurrence records")
    p_occ.add_argument("query", type=str, help="Natural language query")

    # Parser for the 'lookup_occurrence' command
    p_lookup = subparsers.add_parser("lookup_occurrence", help="Look up a single occurrence by UUID")
    p_lookup.add_argument("uuid", type=str, help="The UUID of the record")
    
    # Parser for the 'index_fields' command
    p_fields = subparsers.add_parser("index_fields", help="Get a list of all searchable fields")

    # Parser for the 'species' command
    p_lookup_spec = subparsers.add_parser("lookup_species", help="Look up a single species profile by name")
    p_lookup_spec.add_argument("query", type=str, help="Natural language query for a species name")

    p_search_spec = subparsers.add_parser("search_species", help="Faceted search for species")
    p_search_spec.add_argument("query", type=str, help="Search query (e.g., 'rk_genus:Macropus')")

    args = parser.parse_args()
    agent = ALAiChatBioAgent()

    if hasattr(args, 'query'):
        print(f"\n--- Running '{args.command}' for: '{args.query}' ---\n")
    elif hasattr(args, 'uuid'):
        print(f"\n--- Running '{args.command}' for UUID: '{args.uuid}' ---\n")
    else: 
        print(f"\n--- Running '{args.command}' command ---\n")


    if args.command == "occurrences":
        params = OccurrenceSearchParams(scientificname=args.query)
        async for message in agent.run_occurrence_search(args.query): 
            print(f"[{message.__class__.__name__}] {message.model_dump_json(indent=2)}\n")
    elif args.command == "lookup_species":
        async for message in agent.run_species_lookup(args.query):
            print(f"[{message.__class__.__name__}] {message.model_dump_json(indent=2)}\n")
    elif args.command == "lookup_occurrence":
        params = OccurrenceLookupParams(uuid=args.uuid)
        async for message in agent.run_occurrence_lookup(params):
            print(f"[{message.__class__.__name__}] {message.model_dump_json(indent=2)}\n")
    elif args.command == "index_fields":
        async for message in agent.run_get_index_fields():
            print(f"[{message.__class__.__name__}] {message.model_dump_json(indent=2)}\n")
    elif args.command == "search_species":
        params = SpeciesSearchParams(q=args.query)
        async for message in agent.run_species_search(params):
            print(f"[{message.__class__.__name__}] {message.model_dump_json(indent=2)}\n")

if __name__ == "__main__":
    asyncio.run(main())