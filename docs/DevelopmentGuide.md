# Development Guide

This guide describes how to extend, debug, and maintain the ALA iChatBio Agent, with a focus on adding new tools and evolving parameter extraction and planning.

## 1. Adding a New Tool

Adding a new tool involves four main steps:

1. Define a Pydantic parameter model.
2. Add a URL builder in the ALA logic layer.
3. Implement a workflow method in the agent.
4. Register a tool closure and update the planning prompt.

### 1.1 Define a Pydantic Model

In `ala_logic.py` (or the relevant models module), define a parameter model for your new tool:

class NewToolParams(BaseModel):
param1: str = Field(..., description="Description of param1")
param2: Optional[int] = Field(None, description="Description of param2")


Use required fields for mandatory parameters and `Optional[...]` for non-required ones.

### 1.2 Add a URL Builder

In `ala_logic.py`, add a URL builder that turns your params into a fully encoded URL:

def build_newtool_url(self, params: NewToolParams) -> str:
query_params = {
"param1": params.param1,
}
if params.param2 is not None:
query_params["param2"] = params.param2

query_string = urlencode(query_params)
return f"{self.ala_api_base_url}/newEndpoint?{query_string}"


All encoding and query construction should live here, not in the tool closure.

### 1.3 Add a Workflow Method

In `ala_ichatbio_agent.py`, create an async method that runs the new tool:

async def run_newtool(self, context, params: NewToolParams):
async with context.begin_process("Processing new tool") as process:
url = self.alalogic.build_newtool_url(params)
result = self.alalogic.execute_request(url)

    await process.create_artifact(
        mimetype="application/json",
        description="New tool results",
        uris=[url],
        content=json.dumps(result).encode("utf-8"),
    )

    await context.reply("New tool completed successfully.")


This method should:

- Build the URL via the logic layer.
- Execute the request.
- Create an artifact with the raw JSON.
- Optionally send a short user-facing message.

### 1.4 Add a Tool Closure and Register It

In the agent’s tool map, add a closure that validates input, instantiates the params model, and calls the workflow method:

async def newtool(resolved_obj):
# Description: What this tool does and when it should be used.
param1 = resolved_obj.params.get("param1")
if not param1:
return {"success": False, "message": "Missing param1"}

try:
    params = NewToolParams(param1=param1)
    await self.workflow_agent.run_newtool(context, params)
    return {"success": True}
except Exception as e:
    return {"success": False, "message": str(e)}


Register it in the tool map:

tool_map["newtool"] = newtool


## 2. Update the Planning Prompt

To make the planner aware of the new tool:

- Add `newtool` to the “Available Tools” section of the planning prompt, describing:
  - When it should be used.
  - What kind of query patterns map to it.
- Add 1–2 concrete example queries that should trigger `newtool` in the planner’s examples section.

This helps the LLM choose the new tool reliably and avoid conflicts with existing tools.

## 3. Updating Parameter Extraction

If your new tool requires additional parameters that are not currently extracted:

- Edit the parameter extraction prompt in `parameter_extractor.py`.
- Add a new rule describing:
  - The query pattern.
  - The name of the new parameter.
  - Example values and how they should appear in the structured response.

For example, add a new bullet:

- “NEW PARAMETER TYPE – when the query mentions X pattern, extract `new_param` with value Y.”

Then adjust the Pydantic response model if needed to include the new field.

## 4. Debugging and Logging

Key debugging practices:

- Enable debug logging in resolver and logic layers (e.g., log URL construction and responses).
- Use process logs in the iChatBio UI to inspect:
  - Which tools were selected.
  - The URLs that were called.
  - Raw API responses and validation errors.
- For failing tools:
  - Check that parameters satisfy the Pydantic model.
  - Verify URL encoding and query parameters.
  - Confirm the ALA endpoint accepts the given combination of params.

Common issues and checks:

- Wrong tool selected:
  - Refine the planning prompt with more explicit examples.
  - Add negative examples if necessary.
- LSID not resolved:
  - Inspect resolver logs and ALA name-matching responses.
  - Try more specific common names or direct scientific names.
- 400 Bad Request:
  - Check for malformed query parameters, invalid LSID formats, or unencoded special characters.
- Pydantic validation errors:
  - Ensure required fields are provided and types match the model.
  - Mark non-required fields as optional.

## 5. Testing

### 5.1 Manual Testing

Use representative queries to manually test:

- Simple count queries.
- Faceted breakdowns.
- Distribution and image lookups.
- Edge cases (generic common names, typos, incomplete filters).

Monitor logs and artifacts in the UI to confirm tools, URLs, and outputs.

### 5.2 Automated Testing

Set up automated tests (e.g., with `pytest`) to validate core components:

- Parameter extractor: given a query, returns expected structured parameters.
- Parameter resolver: resolves common/scientific names to correct LSIDs.
- Logic layer: builds valid URLs and handles typical responses.
- Tools: mock ALA responses and assert correct artifacts and messages.

Example invocation:

pytest tests/


Consider adding unit tests for each new tool and integration tests for full query flows.

## 6. Known Limitations (for Developers)

When modifying or extending the system, keep in mind:

- Generic common names may not resolve (e.g., “kangaroo” vs “Red Kangaroo”).
- The planner may occasionally pick a facet-based tool instead of a count-based tool for ambiguous “how many” queries.
- Temporal extraction can miss nuanced phrases (e.g., “from 2020 onward”).
- Comparison queries (e.g., “compare koalas and wombats”) are not yet fully supported.
- Cache is in-memory per agent instance and does not persist across restarts.

Design new features and prompts with these constraints in mind, or plan incremental improvements to address them.