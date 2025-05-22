from ala_agent import ALA
import os

def test_environment_setup():
    """Test if the environment is properly configured"""
    print("Testing Environment Setup")
    print("-" * 40)
  
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        try:
            import yaml
            with open('env.yaml', 'r') as file:
                data = yaml.safe_load(file)
            api_key = data.get('OPENAI_API_KEY')
        except:
            pass
    
    if api_key:
        print(f"OpenAI API Key found (ending in: ...{api_key[-4:]})")
    else:
        print("OpenAI API Key not found")
        print("Please set OPENAI_API_KEY environment variable or create env.yaml file")
        return False
    
    try:
        ala = ALA()
        print("ALA instance created successfully")
        return True
    except Exception as e:
        print(f"Error creating ALA instance: {e}")
        return False

def test_individual_steps():
    """Test each step of the pipeline individually"""
    print("\nTesting Individual Pipeline Steps")
    print("-" * 40)
    
    ala = ALA()
    test_query = "Find koala occurrences in Queensland"
 
    print("Step 1: Building prompt...")
    ala.build_prompt(test_query)
    if ala.prompt:
        print("Prompt built successfully")
        print(f"   Length: {len(ala.prompt)} characters")
    else:
        print("Failed to build prompt")
        return False
   
    print("\nStep 2: Getting API payload...")
    ala.getApiPayload()
    if ala.payload and not ala.error:
        print("API payload extracted successfully")
        print(f"   Payload: {ala.payload}")
    else:
        print(f"Failed to get API payload: {ala.error}")
        return False
    
    print("\nStep 3: Verifying payload...")
    if ala.verify_payload():
        print("Payload validation successful")
    else:
        print(f"Payload validation failed: {ala.error}")
        return False

    print("\nStep 4: Extracting parameters...")
    ala.extract_params_dict()
    if ala.payload:
        print("Parameters extracted successfully")
        print(f"   URL params: {ala.payload}")
    else:
        print("Failed to extract parameters")
        return False
    
    print("\nStep 5: Querying ALA API...")
    result = ala.query_ala_api()
    if result:
        print("ALA API query successful")
        total = result.get('totalRecords', 0)
        print(f"   Found {total} records")
    else:
        print(f"ALA API query failed: {ala.error}")
        return False
   
    print("\nStep 6: Formatting results...")
    formatted = ala.format_results()
    if formatted:
        print("Results formatted successfully")
        print(f"   Preview: {formatted[:100]}...")
    else:
        print("Failed to format results")
        return False
    
    return True

def run_test_queries():
    """Run a series of test queries"""
    print("\nRunning Test Queries")
    print("-" * 40)
    
    test_queries = [
        "Find koala occurrences in Queensland",
        "Show me kangaroo records with images",
        "Eucalyptus trees in Tasmania",
        "Birds recorded in Sydney in 2023"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\nTest Query {i}: {query}")
        print("-" * 30)
        
        ala = ALA()
        try:
            ala.build_prompt(user_input=query)
            ala.getApiPayload()
            ala.verify_payload()
            print(f"Payload: {ala.getPayload()}")
            ala.extract_params_dict()
            result = ala.query_ala_api()
            if result:
                formatted = ala.format_results()
                print("Query completed successfully")
                print(f"Result preview: {formatted[:150]}...")
            
        except Exception as e:
            print(f"Query failed: {str(e)}")
            if ala.getError():
                print(f"   Error details: {ala.getError()}")

def main():
    print("ALA Agent Implementation Test")
    print("=" * 60)
    
    if not test_environment_setup():
        print("\nEnvironment setup failed. Please fix configuration issues.")
        return
    
    if not test_individual_steps():
        print("\nPipeline steps test failed.")
        return
    
    run_test_queries()
    
    print("\n" + "=" * 60)
    print("All tests completed!")

if __name__ == "__main__":
    main()