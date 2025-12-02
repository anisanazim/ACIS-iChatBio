# Troubleshooting

This section lists common issues you may encounter when using or extending the ALA iChatBio Agent, along with likely causes and recommended solutions.

## 1. Species Name Resolution Issues

### Symptom
- Resolver logs messages like: “Failed to resolve LSID for `<name>`”.
- Queries with generic names (e.g., “kangaroo”) do not return expected results.

### Likely Causes
- Generic common name not present or not specific enough in ALA.
- Typo or misspelling in the species name.
- ALA name-matching API timeout or connectivity issue.

### Solutions
- Use more specific common names (e.g., `Red Kangaroo` instead of `kangaroo`).
- Prefer scientific names (e.g., `Osphranter rufus`).
- Check network connectivity and ALA API status.
- Inspect resolver logs to see the exact name-matching requests and responses.

---

## 2. Wrong Tool Selected by Planner

### Symptom
- Query: “Count koala sightings in Queensland”  
  Tool chosen: `get_occurrence_breakdown` instead of `get_occurrence_taxa_count`.
- Planner appears to interpret “how many” as a breakdown instead of a simple total.

### Likely Causes
- Planning prompt not explicit enough about which tool to use for “total count” vs “breakdown”.
- Ambiguous example queries or missing negative examples in the planner prompt.
- Model limitations in interpreting nuanced wording.

### Solutions
- Refine the planning prompt:
  - Add explicit examples for:
    - “Count X in location” → `get_occurrence_taxa_count`.
    - “How many X in EACH state/year” → `get_occurrence_breakdown`.
- Add more planner examples that mirror real user queries.
- If needed, upgrade the planner model (e.g., from a lightweight to a stronger LLM).

---

## 3. Cache Not Working (Repeated Name Lookups)

### Symptom
- Same species name triggers name-matching API calls every query.
- Repeated queries feel slower than expected.

### Likely Causes
- Resolver instance recreated per request instead of being shared.
- Cache is not stored on a persistent object used across the workflow.
- Cache keys too specific (e.g., including noise or whitespace differences).

### Solutions
- Ensure the resolver is instantiated once in the agent initialization and reused:
  - For example, keep `ALAParameterResolver` as a member of the agent.
- Confirm that the cache is a long-lived structure (e.g., dict on the resolver instance).
- Normalize name keys (e.g., lowercase and trim) before caching and lookup.

---

## 4. HTTP 400 Bad Request Errors

### Symptom
- Logs show: “API request failed: 400 Client Error”.
- ALA endpoint returns a client error for what seems like a valid query.

### Likely Causes
- Malformed query parameters (missing required fields).
- Invalid LSID format or incorrect `guids` encoding.
- Special characters not properly URL-encoded.

### Solutions
- Inspect the exact URL in the logs and compare with ALA’s documented examples.
- Verify Pydantic models and ensure required fields are set before URL building.
- Check URL-encoding logic (`urlencode`) and confirm special characters are handled correctly.
- Test the constructed URL directly in a browser or with `curl` to isolate the issue.

---

## 5. Pydantic Validation Errors

### Symptom
- Exceptions like `ValidationError: field required` or type mismatch traces.
- Tool closures fail before calling ALA APIs.

### Likely Causes
- Missing required fields in the parameters passed to the Pydantic model.
- Mismatched types (e.g., passing a string where an int is expected).
- Model definitions not updated after adding new parameters.

### Solutions
- Inspect the Pydantic model definition in the logic layer and confirm:
  - Required fields use `...`.
  - Optional fields use `Optional[...]` with sensible defaults.
- Log the raw params passed into the model when debugging.
- Adjust parameter extraction and tool closures to provide correct names and types.

---

## 6. Tool Fails Silently or Appears to Do Nothing

### Symptom
- No user-facing message or artifact is created.
- Process log shows a tool started but not completed.

### Likely Causes
- Exceptions caught and swallowed in the tool closure without proper logging.
- Early return paths that skip artifact creation.
- Context or workflow methods not awaited correctly.

### Solutions
- Ensure tool closures:
  - Catch and log exceptions with enough detail.
  - Always return a structured status (`success`, `message`).
- Check that `await` is used for async calls (e.g., `await context.reply(...)`).
- Use process logs to confirm each step (URL build, request, artifact creation) is reached.

---

## 7. Performance and Latency Issues

### Symptom
- Queries feel slow, especially repeated queries on the same species.
- Multiple tools in a plan compound delays.

### Likely Causes
- Name resolution cache not reused (see Section 3).
- Overly large `pageSize` or heavy facet queries.
- Network latency or ALA API rate limiting.

### Solutions
- Verify caching is enabled and working for name resolution.
- Tune tool defaults:
  - Use smaller `pageSize` for occurrence search unless large batches are essential.
  - Limit the number of facets per request when possible.
- Consider adding simple timeouts or backoff strategies in the HTTP layer.
- Where acceptable, prefetch or reuse previous tool outputs for similar queries.

---

## 8. General Debugging Tips

- Use debug logging generously in:
  - Parameter Extractor (incoming query and extracted params).
  - Parameter Resolver (name-matching inputs and outputs).
  - ALA Logic Layer (constructed URLs and responses).
- Check iChatBio process logs to see:
  - Which tools were selected by the planner.
  - The order of execution and any failure messages.
- When in doubt:
  - Start with a minimal query (“Count koala sightings in Queensland”) and verify each step.
  - Mock ALA responses in unit tests to confirm tool and logic behavior without external variability.