# Quick Start Guide - Extractor Evaluation Suite

## Setup (One-Time)

### 1. Environment Setup
```powershell
# Ensure you're in the ALA project directory
cd "c:\Users\shaik\OneDrive\Desktop\ALA"

# Activate your virtual environment (if using one)
.\venv\Scripts\Activate.ps1

# Verify Python and dependencies
python --version  # Should be Python 3.8+
```

### 2. Set API Key

**Option A: Use existing env.yaml (Recommended)**
```powershell
# If you already have env.yaml in the project root with OPENAI_API_KEY,
# the test runner will automatically load it. No action needed!
```

**Option B: Set environment variable manually**
```powershell
# Set OpenAI API key temporarily (for current session)
$env:OPENAI_API_KEY = "your-openai-api-key-here"

# Verify it's set
$env:OPENAI_API_KEY
```

**Option C: Add to env.yaml**
```yaml
# Edit env.yaml in project root
OPENAI_API_KEY: "your-api-key-here"
```

### 3. Install Dependencies (if needed)
```powershell
# The test runner requires:
# - openai
# - pydantic
# These should already be in requirements.txt

pip install openai pydantic
```

## Running Tests

### Option 1: Quick Start Script (Recommended)
```powershell
# Navigate to test directory
cd tests\extractor_tests

# Run the quick test script
.\quick_test.ps1

# Follow the prompts
```

### Option 2: Direct Python Execution
```powershell
# Navigate to test directory
cd tests\extractor_tests

# Basic run
python run_extractor_tests.py

# Verbose mode (see each test)
python run_extractor_tests.py --verbose

# Custom output file
python run_extractor_tests.py --output my_report.json

# Combine options
python run_extractor_tests.py -v -o custom_report.json
```

## Understanding Results

### Console Output

#### Success (All Tests Pass)
```
============================================================
TEST SUMMARY
============================================================
Total Tests:     30
Passed:          30 (100.0%)
Failed:          0 (0.0%)
Execution Time:  15.42s

============================================================
RESULTS BY CATEGORY
============================================================
✅ species_extraction              4/ 4 (100.0%)
✅ temporal_extraction             6/ 6 (100.0%)
✅ spatial_extraction              3/ 3 (100.0%)
✅ taxonomic_filters               2/ 2 (100.0%)
✅ basis_of_record                 2/ 2 (100.0%)
✅ seasonal_filters                3/ 3 (100.0%)
✅ facets_and_breakdowns           4/ 4 (100.0%)
✅ edge_cases                      6/ 6 (100.0%)
```

#### Failure (Some Tests Fail)
```
============================================================
FAILED TESTS
============================================================

❌ extract_005: Temporal 'after' extraction for occurrence search
   Query: Show me koala sightings after 2020
   - year mismatch: expected '2020+', got '2021+'
   Expected: {'q': 'koala', 'year': '2020+'}
   Actual:   {'q': 'koala', 'year': '2021+'}
```

### JSON Report

Located at: `extractor_test_report.json` (or your custom filename)

Structure:
```json
{
  "summary": {
    "total_tests": 30,
    "passed": 28,
    "failed": 2,
    "pass_rate": 93.3,
    "execution_time": 15.42,
    "by_category": { ... }
  },
  "results": [
    {
      "test_id": "extract_001",
      "passed": true,
      "expected_params": {...},
      "actual_params": {...},
      "validation_errors": []
    }
  ]
}
```

## Common Issues

### Issue 1: API Key Not Set
```
Error: OPENAI_API_KEY environment variable not set
       and env.yaml not found
```

**Solution**:
```powershell
# Option 1: Add to env.yaml in project root
# OPENAI_API_KEY: "your-api-key"

# Option 2: Set environment variable
$env:OPENAI_API_KEY = "your-api-key"
```

### Issue 2: Module Not Found
```
ModuleNotFoundError: No module named 'openai'
```

**Solution**:
```powershell
pip install openai pydantic
```

### Issue 3: Cannot Find Test File
```
Error: Test file not found
```

**Solution**:
```powershell
# Make sure you're in the correct directory
cd tests\extractor_tests

# Verify file exists
ls test_parameter_extraction.json
```

### Issue 4: Tests Failing Unexpectedly
```
❌ Multiple tests failing
```

**Solution**:
1. Run in verbose mode: `python run_extractor_tests.py -v`
2. Check if parameter_extractor.py was modified
3. Review the actual vs expected parameters
4. Determine if tests need updating or if there's a bug

## Interpreting Test Failures

### Expected Failures (Intentional Changes)
If you modified the extractor prompt or logic:
1. Review failed tests
2. If new behavior is correct, update test expectations
3. Rerun to confirm

### Unexpected Failures (Regressions)
If tests were passing before:
1. Review recent changes to `parameter_extractor.py`
2. Check the `PARAMETER_EXTRACTION_PROMPT`
3. Fix the extraction logic
4. Rerun tests

### Validation Error Types

| Error | Meaning | Action |
|-------|---------|--------|
| "Missing required field" | Expected parameter not extracted | Check extraction logic |
| "Should not have field" | Unexpected parameter extracted | Review extraction rules |
| "mismatch" | Wrong value extracted | Verify prompt instructions |
| "should contain" | Value doesn't include expected substring | Check string handling |

## Test Development Workflow

### Adding a New Test

1. **Identify scenario**:
   - What extraction behavior needs testing?
   - What category does it fall under?

2. **Add test case** to `test_parameter_extraction.json`:
   ```json
   {
     "id": "extract_031",
     "category": "temporal_extraction",
     "query": "Show me sightings during 2023",
     "description": "Temporal 'during' extraction",
     "expected_params": {
       "q": "sightings",
       "year": "2023"
     },
     "should_succeed": true,
     "validation_rules": {
       "must_have": ["year"],
       "year_matches": "2023"
     }
   }
   ```

3. **Run test**:
   ```powershell
   python run_extractor_tests.py -v
   ```

4. **Verify behavior**:
   - Does it pass/fail as expected?
   - Are validation rules correct?

5. **Commit**:
   ```powershell
   git add test_parameter_extraction.json
   git commit -m "Add test for 'during' temporal extraction"
   ```

## Maintenance

### Regular Testing
Run tests:
- Before committing changes
- After modifying extractor prompt
- Before deploying to production
- Weekly for regression checking

### Updating Tests
When extraction behavior changes intentionally:
1. Update test expectations in JSON
2. Update description if needed
3. Document the change
4. Rerun to verify

### Reviewing Reports
Keep historical reports:
```powershell
# Create reports directory
mkdir reports

# Save timestamped reports
python run_extractor_tests.py -o "reports/$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
```

## Performance

- **Average execution time**: ~15 seconds for 30 tests
- **Per test**: ~0.5 seconds
- **API calls**: 30 total (one per test)

## Tips

1. **Use verbose mode** during development: `-v`
2. **Save reports** for comparison: `-o timestamped_report.json`
3. **Test incrementally** when adding new extraction rules
4. **Review failures carefully** - they indicate either bugs or needed updates
5. **Keep tests updated** as extraction requirements evolve

## Next Steps

After running tests:
1. ✅ All pass → Safe to commit/deploy
2. ❌ Some fail → Review and fix
3. 📊 Check report for detailed analysis
4. 📝 Update documentation if behavior changed

## Additional Resources

- **Full Documentation**: [README.md](README.md)
- **Test Cases**: [test_parameter_extraction.json](test_parameter_extraction.json)
- **Overview**: [../../EXTRACTOR_EVALUATION_SUITE.md](../../EXTRACTOR_EVALUATION_SUITE.md)

---

**Last Updated**: 2026-03-03
