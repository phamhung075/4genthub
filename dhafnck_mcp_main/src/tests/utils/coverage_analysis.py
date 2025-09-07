"""
Test Coverage Analysis Utilities

Provides tools for analyzing test coverage patterns, identifying gaps,
and generating coverage reports specific to the DhafnckMCP architecture.
"""

import os
import ast
import importlib.util
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class CoverageGap:
    """Represents a gap in test coverage"""
    file_path: str
    function_name: str
    line_number: int
    gap_type: str  # 'untested_function', 'missing_test_file', 'untested_class', etc.
    description: str
    severity: str = 'medium'  # 'low', 'medium', 'high', 'critical'


@dataclass
class CoverageReport:
    """Comprehensive coverage analysis report"""
    project_root: Path
    total_source_files: int = 0
    total_test_files: int = 0
    coverage_percentage: float = 0.0
    gaps: List[CoverageGap] = field(default_factory=list)
    tested_modules: Set[str] = field(default_factory=set)
    untested_modules: Set[str] = field(default_factory=set)
    test_patterns: Dict[str, int] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class FunctionExtractor(ast.NodeVisitor):
    """AST visitor to extract function and class definitions"""
    
    def __init__(self):
        self.functions = []
        self.classes = []
        self.imports = []
    
    def visit_FunctionDef(self, node):
        """Visit function definitions"""
        if not node.name.startswith('_'):  # Ignore private functions
            self.functions.append({
                'name': node.name,
                'line': node.lineno,
                'is_async': isinstance(node, ast.AsyncFunctionDef),
                'args': [arg.arg for arg in node.args.args],
                'decorators': [self._get_decorator_name(d) for d in node.decorator_list]
            })
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node):
        """Visit async function definitions"""
        self.visit_FunctionDef(node)
    
    def visit_ClassDef(self, node):
        """Visit class definitions"""
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not item.name.startswith('_'):  # Ignore private methods
                    methods.append({
                        'name': item.name,
                        'line': item.lineno,
                        'is_async': isinstance(item, ast.AsyncFunctionDef)
                    })
        
        self.classes.append({
            'name': node.name,
            'line': node.lineno,
            'methods': methods,
            'bases': [self._get_base_name(base) for base in node.bases]
        })
        self.generic_visit(node)
    
    def visit_Import(self, node):
        """Visit import statements"""
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Visit from-import statements"""
        if node.module:
            for alias in node.names:
                self.imports.append(f"{node.module}.{alias.name}")
        self.generic_visit(node)
    
    def _get_decorator_name(self, decorator):
        """Extract decorator name from AST node"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return f"{decorator.value.id}.{decorator.attr}"
        return str(decorator)
    
    def _get_base_name(self, base):
        """Extract base class name from AST node"""
        if isinstance(base, ast.Name):
            return base.id
        elif isinstance(base, ast.Attribute):
            return f"{base.value.id}.{base.attr}"
        return str(base)


class CoverageAnalyzer:
    """Analyzes test coverage patterns in the DhafnckMCP project"""
    
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.src_root = self.project_root / "src"
        self.test_root = self.project_root / "src" / "tests"
    
    def analyze_coverage(self) -> CoverageReport:
        """
        Perform comprehensive coverage analysis.
        
        Returns:
            CoverageReport with detailed analysis
        """
        report = CoverageReport(project_root=self.project_root)
        
        # Find all source and test files
        source_files = self._find_source_files()
        test_files = self._find_test_files()
        
        report.total_source_files = len(source_files)
        report.total_test_files = len(test_files)
        
        # Analyze which modules have tests
        tested_modules, untested_modules = self._analyze_module_coverage(source_files, test_files)
        report.tested_modules = tested_modules
        report.untested_modules = untested_modules
        
        # Calculate basic coverage percentage
        total_modules = len(tested_modules) + len(untested_modules)
        if total_modules > 0:
            report.coverage_percentage = (len(tested_modules) / total_modules) * 100
        
        # Identify coverage gaps
        report.gaps = self._identify_coverage_gaps(source_files, test_files)
        
        # Analyze test patterns
        report.test_patterns = self._analyze_test_patterns(test_files)
        
        # Generate recommendations
        report.recommendations = self._generate_recommendations(report)
        
        return report
    
    def _find_source_files(self) -> List[Path]:
        """Find all Python source files (excluding tests)"""
        source_files = []
        
        if not self.src_root.exists():
            return source_files
        
        for py_file in self.src_root.rglob("*.py"):
            # Skip test files, __pycache__, and __init__.py files
            if (not str(py_file).startswith(str(self.test_root)) and
                "__pycache__" not in str(py_file) and
                py_file.name != "__init__.py"):
                source_files.append(py_file)
        
        return source_files
    
    def _find_test_files(self) -> List[Path]:
        """Find all test files"""
        test_files = []
        
        if not self.test_root.exists():
            return test_files
        
        for py_file in self.test_root.rglob("*.py"):
            # Include files that start with 'test_' or end with '_test.py'
            if (py_file.name.startswith("test_") or 
                py_file.name.endswith("_test.py") or
                "test" in py_file.name):
                test_files.append(py_file)
        
        return test_files
    
    def _analyze_module_coverage(self, source_files: List[Path], test_files: List[Path]) -> Tuple[Set[str], Set[str]]:
        """Analyze which modules have corresponding tests"""
        # Extract module paths from source files
        source_modules = set()
        for source_file in source_files:
            rel_path = source_file.relative_to(self.src_root)
            module_path = str(rel_path.with_suffix(''))
            module_path = module_path.replace(os.sep, '.')
            source_modules.add(module_path)
        
        # Extract tested modules from test files
        tested_modules = set()
        for test_file in test_files:
            # Try to infer what module this test is for
            test_name = test_file.name
            
            # Remove test_ prefix and .py suffix
            if test_name.startswith("test_"):
                module_name = test_name[5:-3]  # Remove 'test_' and '.py'
            else:
                module_name = test_name.replace("_test.py", "").replace(".py", "")
            
            # Try to find corresponding source module
            for source_module in source_modules:
                if module_name in source_module or source_module.endswith(module_name):
                    tested_modules.add(source_module)
                    break
        
        untested_modules = source_modules - tested_modules
        return tested_modules, untested_modules
    
    def _identify_coverage_gaps(self, source_files: List[Path], test_files: List[Path]) -> List[CoverageGap]:
        """Identify specific coverage gaps in the codebase"""
        gaps = []
        
        # Analyze each source file for untested functions
        for source_file in source_files:
            try:
                gaps.extend(self._analyze_source_file_coverage(source_file, test_files))
            except Exception as e:
                # Skip files that can't be parsed
                print(f"Warning: Could not analyze {source_file}: {e}")
        
        return gaps
    
    def _analyze_source_file_coverage(self, source_file: Path, test_files: List[Path]) -> List[CoverageGap]:
        """Analyze coverage gaps in a specific source file"""
        gaps = []
        
        try:
            # Parse the source file
            with open(source_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            extractor = FunctionExtractor()
            extractor.visit(tree)
            
            # Check if there's a corresponding test file
            rel_path = source_file.relative_to(self.src_root)
            has_test_file = self._find_corresponding_test_file(rel_path, test_files)
            
            if not has_test_file:
                gaps.append(CoverageGap(
                    file_path=str(rel_path),
                    function_name="",
                    line_number=1,
                    gap_type="missing_test_file",
                    description=f"No test file found for {rel_path}",
                    severity="medium"
                ))
            
            # Check for untested functions
            for func in extractor.functions:
                # Skip certain types of functions
                if (func['name'].startswith('_') or  # Private functions
                    'property' in func['decorators'] or  # Properties
                    'staticmethod' in func['decorators']):  # Static methods might be tested implicitly
                    continue
                
                gaps.append(CoverageGap(
                    file_path=str(rel_path),
                    function_name=func['name'],
                    line_number=func['line'],
                    gap_type="potentially_untested_function",
                    description=f"Function '{func['name']}' may not have direct tests",
                    severity="low"
                ))
            
            # Check for untested classes
            for cls in extractor.classes:
                if cls['name'].startswith('_'):  # Skip private classes
                    continue
                
                gaps.append(CoverageGap(
                    file_path=str(rel_path),
                    function_name=cls['name'],
                    line_number=cls['line'],
                    gap_type="potentially_untested_class",
                    description=f"Class '{cls['name']}' may not have comprehensive tests",
                    severity="medium"
                ))
        
        except Exception as e:
            # Add a gap for unparseable files
            gaps.append(CoverageGap(
                file_path=str(source_file.relative_to(self.src_root)),
                function_name="",
                line_number=1,
                gap_type="parse_error",
                description=f"Could not parse file: {e}",
                severity="low"
            ))
        
        return gaps
    
    def _find_corresponding_test_file(self, source_rel_path: Path, test_files: List[Path]) -> bool:
        """Check if there's a corresponding test file for a source file"""
        source_name = source_rel_path.stem
        
        for test_file in test_files:
            test_name = test_file.name
            
            # Check various naming patterns
            if (f"test_{source_name}" in test_name or
                f"{source_name}_test" in test_name or
                source_name in test_name):
                return True
        
        return False
    
    def _analyze_test_patterns(self, test_files: List[Path]) -> Dict[str, int]:
        """Analyze patterns in test files"""
        patterns = defaultdict(int)
        
        for test_file in test_files:
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Count different test patterns
                if 'pytest.fixture' in content:
                    patterns['uses_fixtures'] += 1
                
                if '@pytest.mark.' in content:
                    patterns['uses_marks'] += 1
                
                if 'mock' in content.lower() or 'Mock' in content:
                    patterns['uses_mocking'] += 1
                
                if 'async def test_' in content:
                    patterns['async_tests'] += 1
                
                if 'def test_' in content:
                    patterns['sync_tests'] += 1
                
                if 'class Test' in content:
                    patterns['test_classes'] += 1
                
                if 'parametrize' in content:
                    patterns['parametrized_tests'] += 1
                
                # Count integration vs unit test patterns
                if 'integration' in str(test_file).lower():
                    patterns['integration_tests'] += 1
                elif 'unit' in str(test_file).lower():
                    patterns['unit_tests'] += 1
                elif 'e2e' in str(test_file).lower():
                    patterns['e2e_tests'] += 1
            
            except Exception:
                patterns['parse_errors'] += 1
        
        return dict(patterns)
    
    def _generate_recommendations(self, report: CoverageReport) -> List[str]:
        """Generate recommendations based on coverage analysis"""
        recommendations = []
        
        # Coverage percentage recommendations
        if report.coverage_percentage < 70:
            recommendations.append(
                f"Coverage is low ({report.coverage_percentage:.1f}%). "
                "Consider adding tests for untested modules."
            )
        
        # Missing test files
        missing_test_files = [gap for gap in report.gaps if gap.gap_type == "missing_test_file"]
        if missing_test_files:
            recommendations.append(
                f"Found {len(missing_test_files)} modules without test files. "
                "Create corresponding test files for comprehensive coverage."
            )
        
        # Test pattern recommendations
        if report.test_patterns.get('uses_fixtures', 0) < report.total_test_files * 0.3:
            recommendations.append(
                "Consider using more pytest fixtures to reduce test setup duplication."
            )
        
        if report.test_patterns.get('uses_marks', 0) < report.total_test_files * 0.2:
            recommendations.append(
                "Consider using pytest marks to categorize tests (unit, integration, etc.)."
            )
        
        # Architecture-specific recommendations
        if report.test_patterns.get('integration_tests', 0) < 5:
            recommendations.append(
                "Consider adding more integration tests to verify component interactions."
            )
        
        if report.test_patterns.get('async_tests', 0) == 0:
            recommendations.append(
                "Consider adding async tests if your codebase uses async operations."
            )
        
        return recommendations
    
    def generate_coverage_report(self, output_file: Optional[Path] = None) -> str:
        """
        Generate a comprehensive coverage report.
        
        Args:
            output_file: Optional file to write the report to
            
        Returns:
            String containing the formatted report
        """
        report = self.analyze_coverage()
        
        lines = [
            "# DhafnckMCP Test Coverage Analysis Report",
            f"Generated for: {self.project_root}",
            "",
            "## Overview",
            f"- Total source files: {report.total_source_files}",
            f"- Total test files: {report.total_test_files}",
            f"- Module coverage: {report.coverage_percentage:.1f}%",
            f"- Tested modules: {len(report.tested_modules)}",
            f"- Untested modules: {len(report.untested_modules)}",
            "",
            "## Coverage Gaps",
            f"Found {len(report.gaps)} potential coverage gaps:",
            ""
        ]
        
        # Group gaps by type
        gaps_by_type = defaultdict(list)
        for gap in report.gaps:
            gaps_by_type[gap.gap_type].append(gap)
        
        for gap_type, gaps in gaps_by_type.items():
            lines.append(f"### {gap_type.replace('_', ' ').title()} ({len(gaps)} items)")
            for gap in gaps[:10]:  # Limit to first 10 per type
                lines.append(f"- {gap.file_path}:{gap.line_number} - {gap.description}")
            if len(gaps) > 10:
                lines.append(f"- ... and {len(gaps) - 10} more")
            lines.append("")
        
        # Test patterns
        lines.extend([
            "## Test Patterns",
            ""
        ])
        
        for pattern, count in report.test_patterns.items():
            lines.append(f"- {pattern.replace('_', ' ').title()}: {count}")
        
        lines.extend([
            "",
            "## Recommendations",
            ""
        ])
        
        for i, rec in enumerate(report.recommendations, 1):
            lines.append(f"{i}. {rec}")
        
        # Untested modules
        if report.untested_modules:
            lines.extend([
                "",
                "## Untested Modules",
                ""
            ])
            for module in sorted(report.untested_modules):
                lines.append(f"- {module}")
        
        report_text = "\n".join(lines)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
        
        return report_text


# =============================================
# CLI INTERFACE FOR COVERAGE ANALYSIS
# =============================================

def main():
    """CLI interface for running coverage analysis"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze test coverage for DhafnckMCP")
    parser.add_argument("project_root", help="Path to project root directory")
    parser.add_argument("-o", "--output", help="Output file for the report")
    
    args = parser.parse_args()
    
    analyzer = CoverageAnalyzer(Path(args.project_root))
    report_text = analyzer.generate_coverage_report(
        output_file=Path(args.output) if args.output else None
    )
    
    print(report_text)


if __name__ == "__main__":
    main()