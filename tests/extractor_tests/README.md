# ALA Parameter Extractor - Evaluation Suite

## Overview

The **Extractor Evaluation Suite** is a comprehensive automated regression testing framework for the ALA Parameter Extractor. It contains 30 carefully designed test cases covering all aspects of parameter extraction from natural language queries.

## 📁 Files

```
tests/extractor_tests/
├── test_parameter_extraction.json  # 30 test cases with validation rules
├── run_extractor_tests.py         # Automated test runner
└── README.md                       # This file
```

## 🎯 Test Coverage

The test suite covers **8 major categories** of parameter extraction:

### 1. Species Extraction (4 tests)
- Common names (e.g., "koalas")
- Scientific names (e.g., "Eucalyptus regnans")
- AFD URLs (full URL preservation)
- No species mentioned (proper absence handling)

### 2. Temporal Extraction (6 tests)
- "after" / "post" / "since" → `year="2020+"`
- "before" → `year="<2010"`
- "between X and Y" → `year="2015,2020"`
- Exact year → `year="2021"`
- Taxa count temporal (converts to `fq`)
- Relative expressions → `relative_years=5`

### 3. Spatial Extraction (3 tests)
- State filters → `fq=["state:Queensland"]`
- State abbreviations → QLD → Queensland
- City to lat/lon with radius

### 4. Taxonomic Filters (2 tests)
- Family-level filtering
- Genus-level filtering

### 5. Basis of Record (2 tests)
- Preserved specimens
- Human observations

### 6. Seasonal Filters (3 tests)
- Summer → `month:(12 OR 1 OR 2)`
- Winter → `month:(6 OR 7 OR 8)`
- Specific months → `month:1`

### 7. Facets and Breakdowns (4 tests)
- State faceting
- Month faceting
- Taxonomic rank faceting (families → family)
- Multi-state comparison (facets instead of filters)

### 8. Edge Cases (6 tests)
- Complex multi-parameter queries
- Historical queries with multiple filters
- Seasonal comparisons
- Taxonomic rank plurals
- Complex spatial + seasonal + basis queries

## 🚀 Quick Start

### Prerequisites

**Option A: Use existing env.yaml (Recommended)**
```bash
# If you have env.yaml in the project root with OPENAI_API_KEY,
# the test runner will automatically load it.
```

**Option B: Set environment variable**
```bash
# Linux/Mac
export OPENAI_API_KEY="your-api-key-here"

# Windows PowerShell
$env:OPENAI_API_KEY="your-api-key-here"
```

### Running Tests

```bash
# Navigate to the test directory
cd tests/extractor_tests

# Run with default settings
python run_extractor_tests.py

# Run with verbose output (shows each test)
python run_extractor_tests.py --verbose

# Specify custom output file
python run_extractor_tests.py --output my_report.json

# Run specific test file
python run_extractor_tests.py --test-file test_parameter_extraction.json
```

### Command Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--verbose` | `-v` | Show detailed output for each test | False |
| `--output` | `-o` | Output file for JSON report | `extractor_test_report.json` |
| `--test-file` | `-t` | Test suite JSON file to run | `test_parameter_extraction.json` |

## 📊 Output

### Console Output

The runner provides:
1. **Real-time progress** (in verbose mode)
2. **Summary statistics** (total, passed, failed, pass rate)
3. **Results by category** (breakdown by test category)
4. **Failed test details** (with expected vs actual comparison)

Example:
```
============================================================
TEST SUMMARY
============================================================
Total Tests:     30
Passed:          28 (93.3%)
Failed:          2 (6.7%)
Execution Time:  15.42s

============================================================
RESULTS BY CATEGORY
============================================================
✅ species_extraction              4/ 4 (100.0%)
✅ temporal_extraction             6/ 6 (100.0%)
✅ spatial_extraction              3/ 3 (100.0%)
❌ taxonomic_filters               1/ 2 ( 50.0%)
✅ basis_of_record                 2/ 2 (100.0%)
✅ seasonal_filters                3/ 3 (100.0%)
✅ facets_and_breakdowns           4/ 4 (100.0%)
❌ edge_cases                      5/ 6 ( 83.3%)
```

### JSON Report

Detailed JSON report includes:
- Summary statistics
- Pass/fail by category
- Complete results for each test
- Expected vs actual parameters
- Validation errors
- Execution times

Structure:
```json
{
  "summary": {
    "total_tests": 30,
    "passed": 28,
    "failed": 2,
    "pass_rate": 93.3,
    "execution_time": 15.42,
    "timestamp": "2026-03-03T10:30:00",
    "by_category": { ... }
  },
  "results": [
    {
      "test_id": "extract_001",
      "category": "species_extraction",
      "query": "Tell me about koalas",
      "description": "Basic common name extraction",
      "passed": true,
      "execution_time": 0.52,
      "expected_params": {"q": "koalas"},
      "actual_params": {"q": "koalas"},
      "validation_errors": [],
      "extraction_error": null
    },
    ...
  ]
}
```

## 🧪 Test Case Structure

Each test case in `test_parameter_extraction.json` follows this schema:

```json
{
  "id": "extract_001",
  "category": "species_extraction",
  "query": "Tell me about koalas",
  "description": "Basic common name extraction",
  "expected_params": {
    "q": "koalas"
  },
  "should_succeed": true,
  "validation_rules": {
    "must_have": ["q"],
    "must_not_have": ["year", "fq"],
    "q_matches_exactly": "koalas"
  }
}
```

### Validation Rules

| Rule | Description | Example |
|------|-------------|---------|
| `must_have` | Fields that must be present | `["q", "year"]` |
| `must_not_have` | Fields that must be absent | `["fq"]` |
| `q_matches_exactly` | Exact match for q parameter | `"koalas"` |
| `year_matches` | Exact match for year parameter | `"2020+"` |
| `q_contains` | Substring check for q | `"biodiversity.org.au"` |
| `fq_contains` | Check if fq contains substring | `"state:Queensland"` |
| `must_not_have_in_fq` | fq must not contain substring | `"state:"` |
| `facets_contains` | Check if facets contains value | `"state"` |
| `radius_equals` | Exact numeric match for radius | `50` |
| `relative_years_equals` | Exact match for relative_years | `5` |

## 📈 Regression Testing

### Recommended Workflow

1. **Baseline Run**: Establish baseline with current extractor
   ```bash
   python run_extractor_tests.py -o baseline_report.json
   ```

2. **Make Changes**: Modify parameter_extractor.py or prompt

3. **Regression Run**: Test changes against baseline
   ```bash
   python run_extractor_tests.py -o regression_report.json
   ```

4. **Compare Reports**: Check for new failures
   ```bash
   # Compare pass rates by category
   diff baseline_report.json regression_report.json
   ```

5. **Fix or Update**: Either fix regressions or update test expectations

### CI/CD Integration

Add to your CI pipeline:

```yaml
# Example GitHub Actions
- name: Run Extractor Tests
  run: |
    cd tests/extractor_tests
    python run_extractor_tests.py
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

The test runner exits with code 1 on failure, making it suitable for CI/CD.

## 🔧 Adding New Tests

### Step 1: Add Test Case to JSON

Edit `test_parameter_extraction.json`:

```json
{
  "id": "extract_031",
  "category": "your_category",
  "query": "Your natural language query",
  "description": "What this tests",
  "expected_params": {
    "q": "expected value"
  },
  "should_succeed": true,
  "validation_rules": {
    "must_have": ["q"],
    "q_matches_exactly": "expected value"
  }
}
```

### Step 2: Run Tests

```bash
python run_extractor_tests.py --verbose
```

### Step 3: Verify Results

Check that your new test behaves as expected.

## 🐛 Debugging Failed Tests

When a test fails:

1. **Run in verbose mode**:
   ```bash
   python run_extractor_tests.py --verbose
   ```

2. **Check the error message**:
   - Missing fields?
   - Value mismatches?
   - Extraction errors?

3. **Inspect expected vs actual**:
   - Console shows both side-by-side
   - JSON report has complete details

4. **Test manually**:
   ```python
   from parameter_extractor import extract_parameters
   result = extract_parameters("your query")
   print(result)
   ```

## 📝 Best Practices

1. **Test One Thing**: Each test should focus on one extraction feature
2. **Use Descriptive IDs**: `extract_XXX` with sequential numbering
3. **Clear Descriptions**: Explain what the test validates
4. **Specific Rules**: Use precise validation rules
5. **Document Edge Cases**: Add notes for unusual scenarios
6. **Keep Updated**: Update tests when extractor behavior changes intentionally

## 🎓 Example Workflow

```bash
# 1. Make changes to parameter_extractor.py
vim ../../parameter_extractor.py

# 2. Run tests with verbose output
python run_extractor_tests.py --verbose

# 3. Check results
# ✅ All tests pass → Good to commit
# ❌ Some fail → Fix or update tests

# 4. Save report for documentation
python run_extractor_tests.py -o reports/$(date +%Y%m%d)_report.json

# 5. Commit changes
git add test_parameter_extraction.json run_extractor_tests.py
git commit -m "Add/update extractor tests"
```

## 📚 Related Documentation

- [PARAMETER_EXTRACTION_PROMPT](../../parameter_extractor.py) - The extraction prompt
- [AGENT_TEST_QUERIES.md](../../AGENT_TEST_QUERIES.md) - End-to-end agent tests
- [test_runner.py](../test_runner.py) - Full agent test runner

## 🤝 Contributing

To contribute new tests:

1. Identify extraction scenarios not covered
2. Add test cases to JSON following the schema
3. Run tests to verify they work
4. Update this README if adding new categories
5. Submit PR with clear description

## ⚖️ License

Same as parent project.

---

**Last Updated**: 2026-03-03  
**Test Suite Version**: 1.0  
**Total Test Cases**: 30
