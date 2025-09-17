from typing import List
#!/usr/bin/env python3
"""
Test Coverage Analyzer - Identifies Python source files without corresponding unit tests.
Follows DDD (Domain-Driven Design) 4-layer architecture patterns.
"""
import os
import sys
from pathlib import Path
from typing import List, Dict, Set


class CoverageAnalyzer:
    """Analyzes test coverage for DDD-structured Python codebase."""
    
    def __init__(self, src_root: str, tests_root: str):
        self.src_root = Path(src_root)
        self.tests_root = Path(tests_root)
        
    def get_source_files(self, domain: str = None) -> List[Path]:
        """Get all Python source files, optionally filtered by domain."""
        pattern = "**/*.py" if not domain else f"{domain}/**/*.py"
        source_files = []
        
        for file_path in self.src_root.glob(pattern):
            # Skip test files, __init__.py, and __pycache__
            if (not any(part.startswith('test') for part in file_path.parts) and 
                file_path.name != "__init__.py" and
                "__pycache__" not in str(file_path)):
                source_files.append(file_path)
        
        return sorted(source_files)
    
    def get_test_files(self, domain: str = None) -> List[Path]:
        """Get all test files, optionally filtered by domain."""
        pattern = "**/*_test.py" if not domain else f"{domain}/**/*_test.py"
        test_files = []
        
        for file_path in self.tests_root.glob(pattern):
            test_files.append(file_path)
        
        return sorted(test_files)
    
    def source_to_test_path(self, source_path: Path) -> Path:
        """Convert source file path to expected test file path."""
        # Convert source path relative to src_root to test path
        rel_path = source_path.relative_to(self.src_root)
        
        # Remove 'fastmcp/' prefix if present
        if rel_path.parts[0] == 'fastmcp':
            rel_path = Path(*rel_path.parts[1:])
        
        # Create test path
        test_name = f"{rel_path.stem}_test.py"
        test_path = self.tests_root / "unit" / rel_path.parent / test_name
        
        return test_path
    
    def find_untested_files(self, domain: str = None) -> Dict[str, List[Path]]:
        """Find source files without corresponding test files."""
        source_files = self.get_source_files(domain)
        untested = {
            'critical': [],  # Domain entities, services, value objects
            'important': [], # Application services, use cases, facades
            'standard': [],  # Infrastructure, interface, utilities
        }
        
        for source_file in source_files:
            expected_test = self.source_to_test_path(source_file)
            
            if not expected_test.exists():
                # Categorize by importance based on DDD layer
                category = self.categorize_file_importance(source_file)
                untested[category].append(source_file)
        
        return untested
    
    def categorize_file_importance(self, file_path: Path) -> str:
        """Categorize file importance based on DDD patterns."""
        path_str = str(file_path).lower()
        
        # Critical: Domain layer components
        if any(pattern in path_str for pattern in [
            '/domain/entities/', '/domain/services/', '/domain/value_objects/',
            '/domain/repositories/', '/domain/events/', '/domain/exceptions/'
        ]):
            return 'critical'
        
        # Important: Application layer components  
        if any(pattern in path_str for pattern in [
            '/application/services/', '/application/use_cases/', 
            '/application/facades/', '/application/dtos/'
        ]):
            return 'important'
        
        # Standard: Infrastructure and Interface layers
        return 'standard'
    
    def generate_report(self, domain: str = None) -> str:
        """Generate a comprehensive test coverage report."""
        untested = self.find_untested_files(domain)
        
        report = []
        report.append("=" * 80)
        report.append("TEST COVERAGE ANALYSIS REPORT")
        report.append("=" * 80)
        
        if domain:
            report.append(f"Domain: {domain}")
        else:
            report.append("Scope: All domains")
        
        report.append("")
        
        for category, files in untested.items():
            if files:
                report.append(f"\n{category.upper()} FILES WITHOUT TESTS ({len(files)} files):")
                report.append("-" * 60)
                
                for file_path in files:
                    rel_path = file_path.relative_to(self.src_root)
                    expected_test = self.source_to_test_path(file_path)
                    report.append(f"  Source: {rel_path}")
                    report.append(f"  Test:   {expected_test.relative_to(self.tests_root)}")
                    report.append("")
        
        # Summary
        total_untested = sum(len(files) for files in untested.values())
        report.append(f"\nSUMMARY:")
        report.append(f"Critical files without tests: {len(untested['critical'])}")
        report.append(f"Important files without tests: {len(untested['important'])}")
        report.append(f"Standard files without tests: {len(untested['standard'])}")
        report.append(f"Total untested files: {total_untested}")
        
        return "\n".join(report)


def main():
    """Main function to run the test coverage analyzer."""
    if len(sys.argv) > 1:
        domain = sys.argv[1]
    else:
        domain = None
    
    # Set up paths relative to this script
    script_dir = Path(__file__).parent
    src_root = script_dir.parent.parent  # 4genthub_main/src
    tests_root = script_dir.parent       # 4genthub_main/src/tests
    
    analyzer = CoverageAnalyzer(str(src_root), str(tests_root))
    report = analyzer.generate_report(domain)
    
    print(report)
    
    # Also save to file
    output_file = tests_root / "utilities" / "coverage_report.txt"
    with open(output_file, 'w') as f:
        f.write(report)
    
    print(f"\nReport saved to: {output_file}")


if __name__ == "__main__":
    main()