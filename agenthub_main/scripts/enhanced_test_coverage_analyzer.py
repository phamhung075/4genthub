#!/usr/bin/env python3
"""
Enhanced Test Coverage Analysis for agenthub - DDD Architecture Focus
Creates comprehensive test coverage report with specific recommendations for DDD layers
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter

@dataclass
class FileAnalysis:
    """Detailed analysis of a source file"""
    path: str
    module: str
    layer: str
    domain: str
    component: str
    complexity_score: int
    priority: int
    has_test: bool = False
    test_path: str = ""
    lines_of_code: int = 0
    class_count: int = 0
    method_count: int = 0

class EnhancedTestCoverageAnalyzer:
    """Enhanced test coverage analyzer with DDD focus"""
    
    # DDD Layer priorities (higher = more important)
    LAYER_PRIORITIES = {
        'domain': 10,      # Core business logic - highest priority
        'application': 8,  # Use cases and orchestration
        'infrastructure': 5, # Data access and external services
        'interface': 3     # Controllers and endpoints - lowest priority for unit tests
    }
    
    # Component priorities within layers
    COMPONENT_PRIORITIES = {
        # Domain layer components (business logic core)
        'entities': 10,
        'value_objects': 10,
        'services': 9,
        'repositories': 9,
        'events': 8,
        'exceptions': 7,
        
        # Application layer components
        'use_cases': 9,
        'facades': 8,
        'orchestrators': 8,
        'event_handlers': 7,
        'dtos': 5,
        
        # Infrastructure layer components
        'orm': 7,
        'database': 6,
        'migrations': 4,
        'factories': 6,
        
        # Interface layer components
        'controllers': 6,
        'mcp_controllers': 6,
        'endpoints': 5,
        'middleware': 4,
        
        # Cross-cutting
        'interfaces': 8,  # Domain interfaces
        'constants': 3,
        'enums': 6,
    }
    
    def __init__(self, src_path: str = "agenthub_main/src", test_path: str = "agenthub_main/src/tests"):
        self.src_path = Path(src_path)
        self.test_path = Path(test_path)
        self.files: List[FileAnalysis] = []
        self.existing_tests: Set[str] = set()
        
    def analyze(self) -> Dict:
        """Run comprehensive analysis"""
        print("🔍 Enhanced DDD Test Coverage Analysis")
        print("=" * 60)
        
        self._collect_existing_tests()
        self._analyze_source_files()
        self._calculate_priorities()
        
        return self._generate_comprehensive_report()
    
    def _collect_existing_tests(self):
        """Collect all existing test files"""
        print("📋 Collecting existing test files...")
        
        for test_file in self.test_path.rglob("*test*.py"):
            if "__pycache__" not in str(test_file):
                # Convert test path to potential source module paths
                rel_path = test_file.relative_to(self.test_path)
                
                # Handle various test naming conventions
                possible_modules = self._generate_possible_source_modules(str(rel_path))
                self.existing_tests.update(possible_modules)
        
        print(f"   Found {len(self.existing_tests)} existing test modules")
    
    def _generate_possible_source_modules(self, test_path: str) -> List[str]:
        """Generate possible source module names from test file"""
        modules = []
        
        # Remove unit/ prefix
        if test_path.startswith("unit/"):
            test_path = test_path[5:]
        
        # Convert to module path
        base_module = test_path.replace("/", ".").replace(".py", "")
        
        # Handle different test naming patterns
        patterns = [
            lambda x: x.replace("_test", ""),
            lambda x: x.replace("test_", ""),
            lambda x: x.replace("_tests", ""),
            lambda x: x if not x.endswith("_test") else x[:-5],
        ]
        
        for pattern in patterns:
            module = pattern(base_module)
            if module and module != base_module:
                modules.append(module)
        
        return modules
    
    def _analyze_source_files(self):
        """Analyze all source files"""
        print("🔍 Analyzing source files...")
        
        for py_file in self.src_path.rglob("*.py"):
            # Skip system files and cache
            if (py_file.name in ["__init__.py", "__main__.py"] or 
                "__pycache__" in str(py_file) or
                "migrations" in str(py_file).lower()):
                continue
            
            analysis = self._analyze_single_file(py_file)
            if analysis:
                self.files.append(analysis)
        
        print(f"   Analyzed {len(self.files)} source files")
    
    def _analyze_single_file(self, file_path: Path) -> FileAnalysis:
        """Analyze a single source file"""
        try:
            rel_path = file_path.relative_to(self.src_path)
            module_path = str(rel_path).replace("/", ".").replace(".py", "")
            
            # Skip files not in fastmcp
            if not str(rel_path).startswith("fastmcp"):
                return None
            
            # Classify file
            layer, domain, component = self._classify_file(rel_path)
            if not layer:
                return None
            
            # Analyze file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            complexity_score = self._calculate_complexity(content, component)
            loc, classes, methods = self._count_code_elements(content)
            
            # Check if test exists
            has_test = any(module_path.endswith(existing) for existing in self.existing_tests)
            
            return FileAnalysis(
                path=str(rel_path),
                module=module_path,
                layer=layer,
                domain=domain,
                component=component,
                complexity_score=complexity_score,
                priority=0,  # Will be calculated later
                has_test=has_test,
                lines_of_code=loc,
                class_count=classes,
                method_count=methods
            )
            
        except Exception as e:
            print(f"   Warning: Could not analyze {file_path}: {e}")
            return None
    
    def _classify_file(self, file_path: Path) -> Tuple[str, str, str]:
        """Classify file into layer, domain, and component"""
        parts = file_path.parts
        
        # Extract domain
        domains = ['task_management', 'connection_management', 'auth', 'client', 'server']
        domain = 'core'
        for part in parts:
            if part in domains:
                domain = part
                break
        
        # Extract layer
        layers = ['domain', 'application', 'infrastructure', 'interface']
        layer = 'other'
        for part in parts:
            if part in layers:
                layer = part
                break
        
        # Extract component
        component = self._determine_component(file_path, parts)
        
        return layer, domain, component
    
    def _determine_component(self, file_path: Path, parts: Tuple[str]) -> str:
        """Determine component type from file path and name"""
        filename = file_path.stem.lower()
        
        # Check path components first
        for part in reversed(parts[:-1]):
            if part in self.COMPONENT_PRIORITIES:
                return part
        
        # Check filename patterns
        component_patterns = {
            'entities': ['entity', 'entities'],
            'value_objects': ['value_object', 'value_objects'],
            'services': ['service', 'services'],
            'repositories': ['repository', 'repositories'],
            'use_cases': ['use_case', 'use_cases'],
            'facades': ['facade', 'facades'],
            'controllers': ['controller', 'controllers'],
            'exceptions': ['exception', 'exceptions', 'error'],
            'events': ['event', 'events'],
            'dtos': ['dto', 'dtos', 'request', 'response'],
            'factories': ['factory', 'factories'],
            'middleware': ['middleware'],
            'orchestrators': ['orchestrator', 'orchestrators'],
        }
        
        for component, patterns in component_patterns.items():
            if any(pattern in filename for pattern in patterns):
                return component
        
        return 'misc'
    
    def _calculate_complexity(self, content: str, component: str) -> int:
        """Calculate complexity score for prioritization"""
        complexity = 0
        
        # Count structural elements
        classes = len(re.findall(r'^class\s+\w+', content, re.MULTILINE))
        methods = len(re.findall(r'def\s+\w+', content))
        async_methods = len(re.findall(r'async\s+def\s+\w+', content))
        decorators = len(re.findall(r'@\w+', content))
        
        # Basic complexity from structure
        complexity += classes * 5
        complexity += methods * 2
        complexity += async_methods * 3
        complexity += decorators
        
        # Business logic indicators
        if_statements = len(re.findall(r'\bif\s+', content))
        loops = len(re.findall(r'\b(for|while)\s+', content))
        exceptions = len(re.findall(r'\b(raise|except)\s+', content))
        
        complexity += if_statements + loops * 2 + exceptions
        
        # Component-specific bonuses
        component_bonuses = {
            'entities': 10,     # Core business objects
            'services': 8,      # Business logic
            'use_cases': 8,     # Application workflows
            'repositories': 6,  # Data access
            'facades': 6,       # Application boundaries
        }
        
        complexity += component_bonuses.get(component, 0)
        
        return min(complexity, 100)  # Cap at 100
    
    def _count_code_elements(self, content: str) -> Tuple[int, int, int]:
        """Count lines of code, classes, and methods"""
        lines = [line.strip() for line in content.split('\n') if line.strip() and not line.strip().startswith('#')]
        loc = len(lines)
        
        classes = len(re.findall(r'^class\s+\w+', content, re.MULTILINE))
        methods = len(re.findall(r'def\s+\w+', content))
        
        return loc, classes, methods
    
    def _calculate_priorities(self):
        """Calculate final priority scores"""
        print("📊 Calculating priority scores...")
        
        for file_analysis in self.files:
            layer_priority = self.LAYER_PRIORITIES.get(file_analysis.layer, 1)
            component_priority = self.COMPONENT_PRIORITIES.get(file_analysis.component, 1)
            
            # Base priority from layer and component
            base_priority = layer_priority * component_priority
            
            # Complexity bonus (up to 20 points)
            complexity_bonus = min(file_analysis.complexity_score // 5, 20)
            
            # Domain importance (task_management is core business domain)
            domain_bonus = 10 if file_analysis.domain == 'task_management' else 5 if file_analysis.domain in ['auth', 'connection_management'] else 0
            
            file_analysis.priority = base_priority + complexity_bonus + domain_bonus
    
    def _generate_comprehensive_report(self) -> Dict:
        """Generate detailed analysis report"""
        print("📋 Generating comprehensive report...")
        
        # Separate tested and untested files
        untested_files = [f for f in self.files if not f.has_test]
        tested_files = [f for f in self.files if f.has_test]
        
        # Sort by priority
        untested_files.sort(key=lambda x: x.priority, reverse=True)
        
        # Statistics by layer and domain
        layer_stats = self._calculate_layer_stats()
        domain_stats = self._calculate_domain_stats()
        
        report = {
            'summary': {
                'total_files': len(self.files),
                'tested_files': len(tested_files),
                'untested_files': len(untested_files),
                'coverage_percentage': len(tested_files) / len(self.files) * 100 if self.files else 0
            },
            'untested_files': untested_files,
            'layer_stats': layer_stats,
            'domain_stats': domain_stats,
            'top_priority_files': untested_files[:30]
        }
        
        self._print_detailed_report(report)
        return report
    
    def _calculate_layer_stats(self) -> Dict:
        """Calculate statistics by DDD layer"""
        layer_stats = defaultdict(lambda: {'total': 0, 'tested': 0, 'untested': 0, 'components': Counter()})
        
        for file_analysis in self.files:
            layer = file_analysis.layer
            layer_stats[layer]['total'] += 1
            layer_stats[layer]['components'][file_analysis.component] += 1
            
            if file_analysis.has_test:
                layer_stats[layer]['tested'] += 1
            else:
                layer_stats[layer]['untested'] += 1
        
        return dict(layer_stats)
    
    def _calculate_domain_stats(self) -> Dict:
        """Calculate statistics by domain"""
        domain_stats = defaultdict(lambda: {'total': 0, 'tested': 0, 'untested': 0, 'layers': Counter()})
        
        for file_analysis in self.files:
            domain = file_analysis.domain
            domain_stats[domain]['total'] += 1
            domain_stats[domain]['layers'][file_analysis.layer] += 1
            
            if file_analysis.has_test:
                domain_stats[domain]['tested'] += 1
            else:
                domain_stats[domain]['untested'] += 1
        
        return dict(domain_stats)
    
    def _print_detailed_report(self, report: Dict):
        """Print comprehensive coverage report"""
        print("\n" + "="*80)
        print("🎯 ENHANCED TEST COVERAGE ANALYSIS REPORT - DDD FOCUSED")
        print("="*80)
        
        # Executive Summary
        summary = report['summary']
        print(f"\n📈 EXECUTIVE SUMMARY")
        print(f"   Total source files: {summary['total_files']:>6}")
        print(f"   Files with tests:   {summary['tested_files']:>6} ({summary['tested_files']/summary['total_files']*100:5.1f}%)")
        print(f"   Files without tests: {summary['untested_files']:>5} ({summary['untested_files']/summary['total_files']*100:5.1f}%)")
        print(f"   Overall coverage:   {summary['coverage_percentage']:>6.1f}%")
        
        # Layer Analysis
        print(f"\n🏗️  DDD LAYER ANALYSIS")
        print("   " + "-" * 60)
        layer_stats = report['layer_stats']
        
        for layer in ['domain', 'application', 'infrastructure', 'interface']:
            if layer in layer_stats:
                stats = layer_stats[layer]
                coverage = stats['tested'] / stats['total'] * 100 if stats['total'] > 0 else 0
                priority_indicator = "🔴" if coverage < 30 else "🟡" if coverage < 60 else "🟢"
                
                print(f"   {priority_indicator} {layer.upper():<15}: {stats['tested']:3d}/{stats['total']:3d} ({coverage:5.1f}%)")
                
                # Top missing components in this layer
                missing_components = Counter()
                for file_analysis in self.files:
                    if file_analysis.layer == layer and not file_analysis.has_test:
                        missing_components[file_analysis.component] += 1
                
                if missing_components:
                    top_missing = missing_components.most_common(3)
                    components_str = ", ".join([f"{comp}({count})" for comp, count in top_missing])
                    print(f"     Missing tests in: {components_str}")
        
        # Domain Analysis
        print(f"\n🎯 DOMAIN ANALYSIS")
        print("   " + "-" * 60)
        domain_stats = report['domain_stats']
        
        for domain, stats in sorted(domain_stats.items(), key=lambda x: -x[1]['untested']):
            coverage = stats['tested'] / stats['total'] * 100 if stats['total'] > 0 else 0
            priority_indicator = "🔴" if stats['untested'] > 50 else "🟡" if stats['untested'] > 20 else "🟢"
            
            print(f"   {priority_indicator} {domain.upper():<20}: {stats['tested']:3d}/{stats['total']:3d} ({coverage:5.1f}%) - {stats['untested']} missing")
        
        # Top Priority Files
        print(f"\n🎖️  TOP PRIORITY FILES NEEDING TESTS")
        print("   (Ranked by business importance, complexity, and DDD layer priority)")
        print("   " + "-" * 70)
        
        top_files = report['top_priority_files'][:20]
        for i, file_analysis in enumerate(top_files, 1):
            priority_icon = "🔴" if file_analysis.priority > 150 else "🟡" if file_analysis.priority > 100 else "🟠"
            
            print(f"   {i:2d}. {priority_icon} {file_analysis.path}")
            print(f"       Domain: {file_analysis.domain} | Layer: {file_analysis.layer} | Component: {file_analysis.component}")
            print(f"       Priority: {file_analysis.priority} | LOC: {file_analysis.lines_of_code} | Classes: {file_analysis.class_count} | Methods: {file_analysis.method_count}")
        
        # Strategic Recommendations
        print(f"\n💡 STRATEGIC TESTING RECOMMENDATIONS")
        print("   " + "-" * 50)
        print("   1. 🎯 IMMEDIATE FOCUS: Domain entities and services (business logic core)")
        print("   2. 🔄 NEXT PHASE: Application use cases and facades (workflow orchestration)")
        print("   3. 🔌 INFRASTRUCTURE: Repositories and data access patterns")
        print("   4. 🌐 INTERFACE: Controllers (focus on integration tests)")
        print("   5. 📊 METRICS: Aim for 80%+ coverage in Domain, 70%+ in Application layers")
        
        # Quick Wins
        print(f"\n⚡ QUICK WINS - Start with these files:")
        quick_wins = [f for f in top_files if f.component in ['entities', 'value_objects', 'exceptions'] and f.lines_of_code < 200][:10]
        
        for i, file_analysis in enumerate(quick_wins, 1):
            test_path = f"agenthub_main/src/tests/unit/{file_analysis.path.replace('.py', '_test.py')}"
            print(f"   {i}. {file_analysis.path}")
            print(f"      Test: {test_path}")
        
        # Test Creation Commands
        print(f"\n🛠️  TEST CREATION COMMANDS")
        print("   Copy and run these commands to create high-priority tests:")
        print("   " + "-" * 55)
        
        for i, file_analysis in enumerate(top_files[:10], 1):
            test_path = f"agenthub_main/src/tests/unit/{file_analysis.path.replace('.py', '_test.py')}"
            test_dir = Path(test_path).parent
            
            print(f"   # {i}. {file_analysis.component.upper()} - {file_analysis.domain}")
            print(f"   mkdir -p {test_dir}")
            print(f"   touch {test_path}")
            print()

def main():
    """Run enhanced test coverage analysis"""
    analyzer = EnhancedTestCoverageAnalyzer()
    report = analyzer.analyze()
    
    print(f"\n📁 TEST CREATION TEMPLATE")
    print("="*50)
    print("Use this template to create tests for the priority files above:")
    print("""
# Test Template Example for Domain Entity
import pytest
from your.module import YourClass

class TestYourClass:
    def test_creation_with_valid_data(self):
        # Test entity creation with valid data
        pass
    
    def test_validation_with_invalid_data(self):
        # Test validation rules
        pass
    
    def test_business_logic_methods(self):
        # Test core business logic
        pass
""")

if __name__ == "__main__":
    main()