"""
ALA Parameter Extractor - Evaluation Suite Runner
Automated regression testing for parameter extraction

Usage:
    python run_extractor_tests.py [--verbose] [--output report.json]
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict
import sys
import os

# Add parent directory to path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, ROOT)

from openai import OpenAI
from parameter_extractor import ALASearchResponse, PARAMETER_EXTRACTION_PROMPT


@dataclass
class ValidationResult:
    """Result of validating extracted parameters"""
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ExtractorTestResult:
    """Result of a single extractor test case"""
    test_id: str
    category: str
    query: str
    description: str
    passed: bool
    execution_time: float
    expected_params: Dict[str, Any]
    actual_params: Dict[str, Any]
    validation_errors: List[str] = field(default_factory=list)
    extraction_error: Optional[str] = None
    notes: str = ""


@dataclass
class ExtractorTestSummary:
    """Summary of extractor test run"""
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    by_category: Dict[str, Dict[str, int]] = field(default_factory=dict)
    execution_time: float = 0.0
    timestamp: str = ""
    results: List[ExtractorTestResult] = field(default_factory=list)


class ExtractorTester:
    """Automated tester for parameter extraction"""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None, verbose: bool = False):
        """Initialize tester with OpenAI client"""
        if base_url:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = OpenAI(api_key=api_key)
        self.verbose = verbose
        
    def extract_parameters(self, query: str) -> tuple[Dict[str, Any], Optional[str]]:
        """
        Extract parameters from a query using the parameter extractor
        
        Returns:
            (extracted_params, error_message)
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": PARAMETER_EXTRACTION_PROMPT},
                    {"role": "user", "content": query}
                ],
                temperature=0.0
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            extracted_data = json.loads(response_text)
            
            # Validate with Pydantic model
            ala_response = ALASearchResponse.model_validate(
                extracted_data,
                context={'original_query': query}
            )
            
            return ala_response.params, None
            
        except json.JSONDecodeError as e:
            return {}, f"JSON parsing error: {str(e)}"
        except Exception as e:
            return {}, f"Extraction error: {str(e)}"
    
    def validate_extraction(
        self, 
        actual: Dict[str, Any], 
        expected: Dict[str, Any],
        rules: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate extracted parameters against expected values and rules
        
        Args:
            actual: Actually extracted parameters
            expected: Expected parameters
            rules: Validation rules from test case
        
        Returns:
            ValidationResult with pass/fail and error messages
        """
        errors = []
        warnings = []
        
        # Check must_have fields
        if must_have := rules.get('must_have', []):
            for field in must_have:
                if field not in actual:
                    errors.append(f"Missing required field: {field}")
                    
        # Check must_not_have fields
        if must_not_have := rules.get('must_not_have', []):
            for field in must_not_have:
                if field in actual:
                    errors.append(f"Should not have field: {field}")
        
        # Check exact matches
        if 'q_matches_exactly' in rules:
            expected_q = rules['q_matches_exactly']
            actual_q = actual.get('q', '')
            if actual_q != expected_q:
                errors.append(f"q mismatch: expected '{expected_q}', got '{actual_q}'")
        
        # Check year matches
        if 'year_matches' in rules:
            expected_year = rules['year_matches']
            actual_year = str(actual.get('year', ''))
            if actual_year != expected_year:
                errors.append(f"year mismatch: expected '{expected_year}', got '{actual_year}'")
        
        # Check if value contains substring
        if 'q_contains' in rules:
            substring = rules['q_contains']
            actual_q = actual.get('q', '')
            if substring not in actual_q:
                errors.append(f"q should contain '{substring}', got '{actual_q}'")
        
        # Check fq contains
        if 'fq_contains' in rules:
            expected_fq = rules['fq_contains']
            actual_fq = actual.get('fq', [])
            if isinstance(actual_fq, str):
                actual_fq = [actual_fq]
            if not any(expected_fq in fq for fq in actual_fq):
                errors.append(f"fq should contain '{expected_fq}', got {actual_fq}")
        
        # Check must not have in fq
        if 'must_not_have_in_fq' in rules:
            forbidden = rules['must_not_have_in_fq']
            actual_fq = actual.get('fq', [])
            if isinstance(actual_fq, str):
                actual_fq = [actual_fq]
            if any(forbidden in fq for fq in actual_fq):
                errors.append(f"fq should not contain '{forbidden}', got {actual_fq}")
        
        # Check facets contains
        if 'facets_contains' in rules:
            expected_facet = rules['facets_contains']
            actual_facets = actual.get('facets', [])
            if isinstance(actual_facets, str):
                actual_facets = [actual_facets]
            if expected_facet not in actual_facets:
                errors.append(f"facets should contain '{expected_facet}', got {actual_facets}")
        
        # Check numeric equality
        if 'radius_equals' in rules:
            expected_radius = rules['radius_equals']
            actual_radius = actual.get('radius')
            if actual_radius != expected_radius:
                errors.append(f"radius should be {expected_radius}, got {actual_radius}")
        
        if 'relative_years_equals' in rules:
            expected_rel = rules['relative_years_equals']
            actual_rel = actual.get('relative_years')
            if actual_rel != expected_rel:
                errors.append(f"relative_years should be {expected_rel}, got {actual_rel}")
        
        # Compare with expected params (if provided)
        if expected:
            for key, expected_value in expected.items():
                if key not in actual:
                    warnings.append(f"Expected key '{key}' not found in extracted params")
                elif actual[key] != expected_value:
                    # Only warning if not already caught by specific rules
                    if not any(key in str(e) for e in errors):
                        warnings.append(
                            f"Value mismatch for '{key}': expected {expected_value}, got {actual[key]}"
                        )
        
        passed = len(errors) == 0
        return ValidationResult(passed=passed, errors=errors, warnings=warnings)
    
    def run_test_case(self, test_case: Dict[str, Any]) -> ExtractorTestResult:
        """Run a single test case"""
        test_id = test_case['id']
        category = test_case['category']
        query = test_case['query']
        description = test_case['description']
        expected_params = test_case['expected_params']
        should_succeed = test_case.get('should_succeed', True)
        validation_rules = test_case.get('validation_rules', {})
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Test {test_id}: {description}")
            print(f"Query: {query}")
        
        # Extract parameters
        import time
        start_time = time.time()
        actual_params, error = self.extract_parameters(query)
        execution_time = time.time() - start_time
        
        # Validate extraction
        if error:
            if self.verbose:
                print(f" EXTRACTION ERROR: {error}")
            return ExtractorTestResult(
                test_id=test_id,
                category=category,
                query=query,
                description=description,
                passed=not should_succeed,  # If we expected failure, this is ok
                execution_time=execution_time,
                expected_params=expected_params,
                actual_params=actual_params,
                extraction_error=error
            )
        
        # Validate against rules
        validation = self.validate_extraction(actual_params, expected_params, validation_rules)
        
        if self.verbose:
            if validation.passed:
                print(f" PASSED")
            else:
                print(f" FAILED")
                for error in validation.errors:
                    print(f"   - {error}")
            
            if validation.warnings:
                print(f" WARNINGS:")
                for warning in validation.warnings:
                    print(f"   - {warning}")
            
            print(f"Expected: {expected_params}")
            print(f"Actual:   {actual_params}")
        
        return ExtractorTestResult(
            test_id=test_id,
            category=category,
            query=query,
            description=description,
            passed=validation.passed,
            execution_time=execution_time,
            expected_params=expected_params,
            actual_params=actual_params,
            validation_errors=validation.errors,
            notes=test_case.get('notes', '')
        )
    
    def run_test_suite(self, test_file: Path) -> ExtractorTestSummary:
        """Run all tests in a test suite file"""
        print(f"\n{'='*60}")
        print(f"Loading test suite: {test_file.name}")
        print(f"{'='*60}")
        
        with open(test_file, 'r', encoding='utf-8') as f:
            test_suite = json.load(f)
        
        test_cases = test_suite['test_cases']
        print(f"Total test cases: {len(test_cases)}")
        
        summary = ExtractorTestSummary(
            total_tests=len(test_cases),
            timestamp=datetime.now().isoformat()
        )
        
        import time
        start_time = time.time()
        
        for test_case in test_cases:
            result = self.run_test_case(test_case)
            summary.results.append(result)
            
            if result.passed:
                summary.passed += 1
            else:
                summary.failed += 1
            
            # Track by category
            category = result.category
            if category not in summary.by_category:
                summary.by_category[category] = {'passed': 0, 'failed': 0}
            
            if result.passed:
                summary.by_category[category]['passed'] += 1
            else:
                summary.by_category[category]['failed'] += 1
        
        summary.execution_time = time.time() - start_time
        
        return summary
    
    def print_summary(self, summary: ExtractorTestSummary):
        """Print test summary to console"""
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total Tests:     {summary.total_tests}")
        print(f"Passed:          {summary.passed} ({summary.passed/summary.total_tests*100:.1f}%)")
        print(f"Failed:          {summary.failed} ({summary.failed/summary.total_tests*100:.1f}%)")
        print(f"Execution Time:  {summary.execution_time:.2f}s")
        
        print(f"\n{'='*60}")
        print(f"RESULTS BY CATEGORY")
        print(f"{'='*60}")
        
        for category, stats in sorted(summary.by_category.items()):
            total = stats['passed'] + stats['failed']
            pass_rate = stats['passed'] / total * 100 if total > 0 else 0
            status = "✅" if stats['failed'] == 0 else "❌"
            print(f"{status} {category:30s} {stats['passed']:2d}/{total:2d} ({pass_rate:5.1f}%)")
        
        if summary.failed > 0:
            print(f"\n{'='*60}")
            print(f"FAILED TESTS")
            print(f"{'='*60}")
            
            for result in summary.results:
                if not result.passed:
                    print(f"\n❌ {result.test_id}: {result.description}")
                    print(f"   Query: {result.query}")
                    if result.extraction_error:
                        print(f"   Error: {result.extraction_error}")
                    else:
                        for error in result.validation_errors:
                            print(f"   - {error}")
                        print(f"   Expected: {result.expected_params}")
                        print(f"   Actual:   {result.actual_params}")
    
    def save_report(self, summary: ExtractorTestSummary, output_file: Path):
        """Save detailed report to JSON file"""
        report = {
            'summary': {
                'total_tests': summary.total_tests,
                'passed': summary.passed,
                'failed': summary.failed,
                'pass_rate': summary.passed / summary.total_tests * 100,
                'execution_time': summary.execution_time,
                'timestamp': summary.timestamp,
                'by_category': summary.by_category
            },
            'results': [
                {
                    'test_id': r.test_id,
                    'category': r.category,
                    'query': r.query,
                    'description': r.description,
                    'passed': r.passed,
                    'execution_time': r.execution_time,
                    'expected_params': r.expected_params,
                    'actual_params': r.actual_params,
                    'validation_errors': r.validation_errors,
                    'extraction_error': r.extraction_error
                }
                for r in summary.results
            ]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n Detailed report saved to: {output_file}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Run ALA Parameter Extractor Evaluation Suite'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output (show each test)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='extractor_test_report.json',
        help='Output file for detailed report (default: extractor_test_report.json)'
    )
    parser.add_argument(
        '--test-file', '-t',
        type=str,
        default='test_parameter_extraction.json',
        help='Test suite file to run (default: test_parameter_extraction.json)'
    )
    
    args = parser.parse_args()
    
    # Get API key from environment or env.yaml
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        # Try to load from env.yaml in project root
        env_yaml_path = Path(__file__).parent.parent.parent / 'env.yaml'
        if env_yaml_path.exists():
            try:
                import yaml
                with open(env_yaml_path, 'r') as f:
                    env_config = yaml.safe_load(f)
                    api_key = env_config.get('OPENAI_API_KEY')
                    if api_key:
                        print("[OK] Loaded OPENAI_API_KEY from env.yaml")
                    else:
                        print("Error: OPENAI_API_KEY not found in env.yaml")
                        sys.exit(1)
            except ImportError:
                print("Error: PyYAML not installed. Install with: pip install pyyaml")
                print("Or set OPENAI_API_KEY environment variable")
                sys.exit(1)
            except Exception as e:
                print(f"Error loading env.yaml: {e}")
                sys.exit(1)
        else:
            print("Error: OPENAI_API_KEY environment variable not set")
            print(f"       and env.yaml not found at {env_yaml_path}")
            sys.exit(1)
    
    # Get base URL from environment or env.yaml (optional)
    base_url = os.getenv('OPENAI_BASE_URL')
    if not base_url:
        # Try to load from env.yaml
        env_yaml_path = Path(__file__).parent.parent.parent / 'env.yaml'
        if env_yaml_path.exists():
            try:
                import yaml
                with open(env_yaml_path, 'r') as f:
                    env_config = yaml.safe_load(f)
                    base_url = env_config.get('OPENAI_BASE_URL')
                    if base_url:
                        print(f"[OK] Loaded OPENAI_BASE_URL from env.yaml: {base_url}")
                    else:
                        # Use default
                        base_url = "https://api.ai.it.ufl.edu"
                        print(f"[OK] Using default OpenAI base URL: {base_url}")
            except:
                # Use default if any error
                base_url = "https://api.ai.it.ufl.edu"
                print(f"[OK] Using default OpenAI base URL: {base_url}")
        else:
            # Use default if no env.yaml
            base_url = "https://api.ai.it.ufl.edu"
            print(f"[OK] Using default OpenAI base URL: {base_url}")
    else:
        print(f"[OK] Using OpenAI base URL from environment: {base_url}")
    
    # Locate test file
    test_dir = Path(__file__).parent
    test_file = test_dir / args.test_file
    
    if not test_file.exists():
        print(f"Error: Test file not found: {test_file}")
        sys.exit(1)
    
    # Run tests
    tester = ExtractorTester(api_key=api_key, base_url=base_url, verbose=args.verbose)
    summary = tester.run_test_suite(test_file)
    
    # Print summary
    tester.print_summary(summary)
    
    # Save detailed report
    output_file = test_dir / args.output
    tester.save_report(summary, output_file)
    
    # Exit with appropriate code
    sys.exit(0 if summary.failed == 0 else 1)


if __name__ == '__main__':
    main()
