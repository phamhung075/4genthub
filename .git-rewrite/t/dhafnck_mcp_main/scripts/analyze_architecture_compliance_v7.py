#!/usr/bin/env python3
"""
Architecture Compliance Analyzer V7 - Complete Code Path (Chemin) Analysis
Analyzes each code path from MCP entry to database to verify DDD compliance
"""

import os
import re
import ast
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum

class Severity(Enum):
    """Violation severity levels"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class ViolationType(Enum):
    """Types of architecture violations"""
    LAYER_VIOLATION = "LAYER_VIOLATION"
    DIRECT_DB_ACCESS = "DIRECT_DB_ACCESS"
    DIRECT_REPOSITORY = "DIRECT_REPOSITORY"
    MISSING_FACTORY = "MISSING_FACTORY"
    HARDCODED_REPO = "HARDCODED_REPO"
    NO_CACHE_INVALIDATION = "NO_CACHE_INVALIDATION"
    NO_ENV_CHECK = "NO_ENV_CHECK"
    BROKEN_FACTORY = "BROKEN_FACTORY"

@dataclass
class CodePath:
    """Represents a complete code flow path from entry to database"""
    name: str
    entry_point: str
    controller: Optional[str] = None
    facade: Optional[str] = None
    use_case: Optional[str] = None
    repository_factory: Optional[str] = None
    repository: Optional[str] = None
    violations: List['Violation'] = field(default_factory=list)
    cache_invalidation: bool = False
    follows_ddd: bool = True

@dataclass
class Violation:
    """Represents an architecture violation"""
    type: ViolationType
    severity: Severity
    file: str
    line: int
    description: str
    code_snippet: str = ""
    fix_suggestion: str = ""

class CodePathAnalyzer:
    """Analyzes complete code paths for architecture compliance"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_root = project_root / "src"
        self.test_root = project_root / "tests"
        self.code_paths: List[CodePath] = []
        self.all_violations: List[Violation] = []
        
    def analyze_all_paths(self) -> Dict[str, Any]:
        """Analyze all code paths in the system"""
        print("=" * 80)
        print("ARCHITECTURE COMPLIANCE ANALYZER V7 - SYSTEMATIC CODE PATH ANALYSIS")
        print("=" * 80)
        
        # Find all MCP entry points
        entry_points = self._find_mcp_entry_points()
        print(f"\n📍 Found {len(entry_points)} MCP entry points")
        
        # Analyze each code path
        for entry in entry_points:
            path = self._trace_code_path(entry)
            self.code_paths.append(path)
            self.all_violations.extend(path.violations)
        
        # Analyze repository factories
        factory_analysis = self._analyze_all_repository_factories()
        
        # Generate comprehensive report
        return self._generate_comprehensive_report(factory_analysis)
    
    def _find_mcp_entry_points(self) -> List[Tuple[str, str]]:
        """Find all MCP tool entry points"""
        entry_points = []
        controllers_dir = self.src_root / "fastmcp/task_management/interface/controllers"
        
        if not controllers_dir.exists():
            print(f"⚠️ Controllers directory not found: {controllers_dir}")
            return []
        
        # Find all controller files
        for file in controllers_dir.glob("*_controller.py"):
            if file.name == "__init__.py":
                continue
                
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Find all methods that look like MCP handlers
            pattern = r'def (manage_\w+|execute_\w+|handle_\w+)\s*\('
            matches = re.finditer(pattern, content)
            
            for match in matches:
                method_name = match.group(1)
                entry_points.append((str(file), method_name))
                
        return entry_points
    
    def _trace_code_path(self, entry: Tuple[str, str]) -> CodePath:
        """Trace complete code path from entry point to database"""
        file_path, method_name = entry
        path_name = f"{Path(file_path).stem}.{method_name}"
        
        path = CodePath(
            name=path_name,
            entry_point=f"{file_path}:{method_name}",
            controller=file_path
        )
        
        # Analyze controller
        controller_violations = self._analyze_controller(file_path)
        path.violations.extend(controller_violations)
        
        # Trace to facade/service
        facade_info = self._find_facade_usage(file_path)
        if facade_info:
            path.facade = facade_info['file']
            facade_violations = self._analyze_facade(facade_info['file'])
            path.violations.extend(facade_violations)
            
            # Check for repository factory usage
            factory_usage = self._check_factory_usage(facade_info['file'])
            if factory_usage:
                path.repository_factory = factory_usage['factory']
                factory_violations = self._analyze_factory(factory_usage['factory'])
                path.violations.extend(factory_violations)
            else:
                path.violations.append(Violation(
                    type=ViolationType.MISSING_FACTORY,
                    severity=Severity.HIGH,
                    file=facade_info['file'],
                    line=0,
                    description=f"Facade does not use RepositoryFactory pattern",
                    fix_suggestion="Import and use RepositoryFactory to get repository instances"
                ))
        
        # Check cache invalidation
        path.cache_invalidation = self._check_cache_invalidation(path)
        
        # Determine if path follows DDD
        path.follows_ddd = len([v for v in path.violations if v.severity == Severity.HIGH]) == 0
        
        return path
    
    def _analyze_controller(self, file_path: str) -> List[Violation]:
        """Analyze controller for DDD violations"""
        violations = []
        
        if not os.path.exists(file_path):
            return violations
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            content = ''.join(lines)
        
        # Check for direct database imports
        db_import_pattern = r'from\s+[\w.]*(?:database|db|orm|sqlalchemy)[\w.]*\s+import'
        for i, line in enumerate(lines, 1):
            if re.search(db_import_pattern, line):
                violations.append(Violation(
                    type=ViolationType.DIRECT_DB_ACCESS,
                    severity=Severity.HIGH,
                    file=file_path,
                    line=i,
                    description="Controller directly imports database modules",
                    code_snippet=line.strip(),
                    fix_suggestion="Remove database imports and use facades/services instead"
                ))
        
        # Check for direct repository imports
        repo_import_pattern = r'from\s+[\w.]*repositories[\w.]*\s+import\s+(?!.*Interface|.*Abstract|.*repository_factory)'
        for i, line in enumerate(lines, 1):
            if re.search(repo_import_pattern, line):
                violations.append(Violation(
                    type=ViolationType.DIRECT_REPOSITORY,
                    severity=Severity.HIGH,
                    file=file_path,
                    line=i,
                    description="Controller directly imports concrete repository implementations",
                    code_snippet=line.strip(),
                    fix_suggestion="Use facades/services instead of direct repository access"
                ))
        
        # Check for direct repository instantiation
        repo_instantiation = r'(\w+Repository)\s*\(\s*\)'
        matches = re.finditer(repo_instantiation, content)
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1
            violations.append(Violation(
                type=ViolationType.HARDCODED_REPO,
                severity=Severity.HIGH,
                file=file_path,
                line=line_num,
                description=f"Controller directly instantiates repository: {match.group(1)}",
                code_snippet=match.group(0),
                fix_suggestion="Use facade/service methods instead"
            ))
        
        return violations
    
    def _analyze_facade(self, file_path: str) -> List[Violation]:
        """Analyze facade for factory pattern usage"""
        violations = []
        
        if not os.path.exists(file_path):
            return violations
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            content = ''.join(lines)
        
        # Check for repository factory import
        has_factory_import = bool(re.search(r'from.*repository_factory.*import', content))
        
        # Check for hardcoded repository instantiation
        hardcoded_patterns = [
            r'SQLiteTaskRepository\s*\(\s*\)',
            r'SupabaseTaskRepository\s*\(\s*\)',
            r'ORMTaskRepository\s*\(\s*\)',
            r'MockTaskContextRepository\s*\(\s*\)',
            r'(\w+Repository)\s*\(\s*\)(?!.*Factory)',
        ]
        
        for pattern in hardcoded_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                violations.append(Violation(
                    type=ViolationType.HARDCODED_REPO,
                    severity=Severity.MEDIUM,
                    file=file_path,
                    line=line_num,
                    description=f"Hardcoded repository instantiation: {match.group(0)}",
                    code_snippet=lines[line_num-1].strip() if line_num <= len(lines) else "",
                    fix_suggestion="Use RepositoryFactory.get_*_repository() instead"
                ))
        
        # If no factory import but has repository usage
        if not has_factory_import and re.search(r'repository', content, re.IGNORECASE):
            violations.append(Violation(
                type=ViolationType.MISSING_FACTORY,
                severity=Severity.MEDIUM,
                file=file_path,
                line=0,
                description="Facade doesn't import RepositoryFactory",
                fix_suggestion="Import RepositoryFactory and use it to get repository instances"
            ))
        
        return violations
    
    def _analyze_factory(self, factory_path: str) -> List[Violation]:
        """Analyze repository factory for environment checking"""
        violations = []
        
        if not os.path.exists(factory_path):
            return violations
        
        with open(factory_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for environment variable checking
        required_checks = {
            'ENVIRONMENT': r"os\.(?:getenv|environ\.get)\s*\(\s*['\"]ENVIRONMENT",
            'DATABASE_TYPE': r"os\.(?:getenv|environ\.get)\s*\(\s*['\"]DATABASE_TYPE",
            'REDIS_ENABLED': r"os\.(?:getenv|environ\.get)\s*\(\s*['\"]REDIS_ENABLED",
        }
        
        missing_checks = []
        for var, pattern in required_checks.items():
            if not re.search(pattern, content):
                missing_checks.append(var)
        
        if missing_checks:
            violations.append(Violation(
                type=ViolationType.NO_ENV_CHECK,
                severity=Severity.HIGH,
                file=factory_path,
                line=0,
                description=f"Factory doesn't check environment variables: {', '.join(missing_checks)}",
                fix_suggestion=f"Add environment checks for: {', '.join(missing_checks)}"
            ))
        
        # Check for conditional repository selection
        if 'if' not in content and 'return' in content:
            violations.append(Violation(
                type=ViolationType.BROKEN_FACTORY,
                severity=Severity.HIGH,
                file=factory_path,
                line=0,
                description="Factory returns hardcoded repository without conditional logic",
                fix_suggestion="Implement conditional logic based on environment variables"
            ))
        
        return violations
    
    def _find_facade_usage(self, controller_path: str) -> Optional[Dict[str, str]]:
        """Find which facade/service a controller uses"""
        if not os.path.exists(controller_path):
            return None
        
        with open(controller_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for facade/service imports
        facade_pattern = r'from\s+([\w.]*(?:facades?|services?)[\w.]*)\s+import\s+(\w+)'
        matches = re.findall(facade_pattern, content)
        
        if matches:
            # Try to find the actual facade file
            for module, class_name in matches:
                # Convert module path to file path
                module_path = module.replace('.', '/')
                possible_paths = [
                    self.src_root / f"{module_path}.py",
                    self.src_root / f"{module_path}/{class_name.lower()}.py",
                    self.src_root / f"{module_path}/_{class_name.lower()}.py",
                ]
                
                for path in possible_paths:
                    if path.exists():
                        return {'file': str(path), 'class': class_name}
        
        return None
    
    def _check_factory_usage(self, facade_path: str) -> Optional[Dict[str, str]]:
        """Check if facade uses repository factory"""
        if not os.path.exists(facade_path):
            return None
        
        with open(facade_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for repository factory usage
        factory_pattern = r'(?:RepositoryFactory|TaskRepositoryFactory|ProjectRepositoryFactory)\.(\w+)'
        match = re.search(factory_pattern, content)
        
        if match:
            # Find the factory file
            factory_paths = list(self.src_root.glob("**/repository_factory*.py"))
            if factory_paths:
                return {'factory': str(factory_paths[0]), 'method': match.group(1)}
        
        return None
    
    def _check_cache_invalidation(self, path: CodePath) -> bool:
        """Check if the code path properly invalidates cache"""
        # This would need more sophisticated analysis
        # For now, we'll check if there's any cache invalidation mentioned
        for component in [path.controller, path.facade, path.repository]:
            if component and os.path.exists(component):
                with open(component, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'invalidate' in content.lower():
                        return True
        return False
    
    def _analyze_all_repository_factories(self) -> Dict[str, Any]:
        """Analyze all repository factories in the system"""
        factory_analysis = {
            'total_factories': 0,
            'working_factories': 0,
            'broken_factories': [],
            'factories': []
        }
        
        # Find all repository factory files
        factory_files = list(self.src_root.glob("**/repository_factory*.py"))
        factory_files.extend(list(self.src_root.glob("**/*_factory.py")))
        
        factory_analysis['total_factories'] = len(factory_files)
        
        for factory_file in factory_files:
            with open(factory_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            factory_info = {
                'file': str(factory_file),
                'name': factory_file.stem,
                'checks_environment': bool(re.search(r"os\.(?:getenv|environ\.get)\s*\(\s*['\"]ENVIRONMENT", content)),
                'checks_database_type': bool(re.search(r"os\.(?:getenv|environ\.get)\s*\(\s*['\"]DATABASE_TYPE", content)),
                'checks_redis': bool(re.search(r"os\.(?:getenv|environ\.get)\s*\(\s*['\"]REDIS_ENABLED", content)),
                'has_conditional_logic': 'if' in content,
                'working': False
            }
            
            # Determine if factory is working
            if (factory_info['checks_environment'] or factory_info['checks_database_type']) and factory_info['has_conditional_logic']:
                factory_info['working'] = True
                factory_analysis['working_factories'] += 1
            else:
                factory_analysis['broken_factories'].append(factory_info['name'])
            
            factory_analysis['factories'].append(factory_info)
        
        return factory_analysis
    
    def _generate_comprehensive_report(self, factory_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""
        # Calculate statistics
        total_paths = len(self.code_paths)
        compliant_paths = len([p for p in self.code_paths if p.follows_ddd])
        paths_with_violations = len([p for p in self.code_paths if p.violations])
        
        high_violations = [v for v in self.all_violations if v.severity == Severity.HIGH]
        medium_violations = [v for v in self.all_violations if v.severity == Severity.MEDIUM]
        low_violations = [v for v in self.all_violations if v.severity == Severity.LOW]
        
        # Group violations by type
        violations_by_type = {}
        for v in self.all_violations:
            if v.type not in violations_by_type:
                violations_by_type[v.type] = []
            violations_by_type[v.type].append(v)
        
        # Calculate compliance score
        compliance_score = self._calculate_compliance_score(
            total_paths, compliant_paths, 
            len(high_violations), len(medium_violations), len(low_violations),
            factory_analysis
        )
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'version': 'V7',
            'summary': {
                'total_code_paths': total_paths,
                'compliant_paths': compliant_paths,
                'paths_with_violations': paths_with_violations,
                'total_violations': len(self.all_violations),
                'high_violations': len(high_violations),
                'medium_violations': len(medium_violations),
                'low_violations': len(low_violations),
                'compliance_score': compliance_score,
                'grade': self._get_grade(compliance_score)
            },
            'factory_analysis': factory_analysis,
            'violations_by_type': {
                str(vtype): len(violations) 
                for vtype, violations in violations_by_type.items()
            },
            'code_paths': [
                {
                    'name': path.name,
                    'entry_point': path.entry_point,
                    'follows_ddd': path.follows_ddd,
                    'violations_count': len(path.violations),
                    'has_cache_invalidation': path.cache_invalidation,
                    'flow': self._get_path_flow(path)
                }
                for path in self.code_paths
            ],
            'detailed_violations': [
                {
                    'type': str(v.type),
                    'severity': str(v.severity),
                    'file': v.file,
                    'line': v.line,
                    'description': v.description,
                    'fix': v.fix_suggestion
                }
                for v in self.all_violations
            ]
        }
        
        return report
    
    def _get_path_flow(self, path: CodePath) -> str:
        """Get visual flow representation of code path"""
        components = []
        if path.controller:
            components.append(f"Controller({Path(path.controller).stem})")
        if path.facade:
            components.append(f"Facade({Path(path.facade).stem})")
        if path.repository_factory:
            components.append(f"Factory({Path(path.repository_factory).stem})")
        if path.repository:
            components.append(f"Repository({Path(path.repository).stem})")
        else:
            components.append("Repository(?)")
        
        return " → ".join(components)
    
    def _calculate_compliance_score(self, total_paths: int, compliant_paths: int,
                                   high_violations: int, medium_violations: int, 
                                   low_violations: int, factory_analysis: Dict) -> int:
        """Calculate overall compliance score (0-100)"""
        if total_paths == 0:
            return 0
        
        # Base score from compliant paths
        path_score = (compliant_paths / total_paths) * 40
        
        # Deduct for violations
        violation_penalty = (high_violations * 5) + (medium_violations * 2) + (low_violations * 1)
        violation_score = max(0, 30 - violation_penalty)
        
        # Factory score
        if factory_analysis['total_factories'] > 0:
            factory_score = (factory_analysis['working_factories'] / factory_analysis['total_factories']) * 30
        else:
            factory_score = 0
        
        total_score = path_score + violation_score + factory_score
        return max(0, min(100, int(total_score)))
    
    def _get_grade(self, score: int) -> str:
        """Get letter grade from score"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def print_report(self, report: Dict[str, Any]):
        """Print formatted compliance report"""
        print("\n" + "=" * 80)
        print("ARCHITECTURE COMPLIANCE REPORT V7 - SYSTEMATIC CODE PATH ANALYSIS")
        print("=" * 80)
        
        # Summary
        summary = report['summary']
        print(f"\n📊 COMPLIANCE SUMMARY")
        print(f"   Score: {summary['compliance_score']}/100 (Grade: {summary['grade']})")
        print(f"   Code Paths Analyzed: {summary['total_code_paths']}")
        print(f"   Compliant Paths: {summary['compliant_paths']}")
        print(f"   Paths with Violations: {summary['paths_with_violations']}")
        
        print(f"\n📈 VIOLATION STATISTICS")
        print(f"   Total Violations: {summary['total_violations']}")
        print(f"   🔴 High Severity: {summary['high_violations']}")
        print(f"   🟡 Medium Severity: {summary['medium_violations']}")
        print(f"   🟢 Low Severity: {summary['low_violations']}")
        
        # Factory Analysis
        factory = report['factory_analysis']
        print(f"\n🏭 REPOSITORY FACTORY ANALYSIS")
        print(f"   Total Factories: {factory['total_factories']}")
        print(f"   Working Factories: {factory['working_factories']}")
        print(f"   Broken Factories: {len(factory['broken_factories'])}")
        if factory['broken_factories']:
            print(f"   Broken: {', '.join(factory['broken_factories'][:5])}")
        
        # Violations by Type
        print(f"\n🔍 VIOLATIONS BY TYPE")
        for vtype, count in report['violations_by_type'].items():
            print(f"   {vtype}: {count}")
        
        # Code Path Details
        print(f"\n🛤️ CODE PATH ANALYSIS (Top 10)")
        for i, path in enumerate(report['code_paths'][:10], 1):
            status = "✅" if path['follows_ddd'] else "❌"
            print(f"   {i}. {status} {path['name']}")
            print(f"      Flow: {path['flow']}")
            if path['violations_count'] > 0:
                print(f"      Violations: {path['violations_count']}")
        
        # Critical Violations
        print(f"\n⚠️ CRITICAL VIOLATIONS (First 10)")
        critical_violations = [v for v in report['detailed_violations'] if v['severity'] == 'HIGH']
        for i, v in enumerate(critical_violations[:10], 1):
            print(f"   {i}. {v['type']} in {Path(v['file']).name}:{v['line']}")
            print(f"      {v['description']}")
            print(f"      Fix: {v['fix']}")
        
        print("\n" + "=" * 80)
        print("END OF COMPLIANCE REPORT")
        print("=" * 80)
    
    def save_report(self, report: Dict[str, Any], output_dir: Path):
        """Save report to file"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save JSON report
        json_file = output_dir / f"compliance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Save Markdown report
        md_file = output_dir / f"compliance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        self._save_markdown_report(report, md_file)
        
        print(f"\n📁 Reports saved to:")
        print(f"   JSON: {json_file}")
        print(f"   Markdown: {md_file}")
        
        return json_file, md_file
    
    def _save_markdown_report(self, report: Dict[str, Any], file_path: Path):
        """Save report as markdown"""
        with open(file_path, 'w') as f:
            f.write("# Architecture Compliance Report V7\n")
            f.write(f"Generated: {report['timestamp']}\n\n")
            
            # Summary
            s = report['summary']
            f.write("## Executive Summary\n")
            f.write(f"- **Compliance Score**: {s['compliance_score']}/100 (Grade: {s['grade']})\n")
            f.write(f"- **Total Code Paths**: {s['total_code_paths']}\n")
            f.write(f"- **Compliant Paths**: {s['compliant_paths']}\n")
            f.write(f"- **Total Violations**: {s['total_violations']}\n\n")
            
            # Violation breakdown
            f.write("## Violation Breakdown\n")
            f.write(f"- 🔴 **High Severity**: {s['high_violations']}\n")
            f.write(f"- 🟡 **Medium Severity**: {s['medium_violations']}\n")
            f.write(f"- 🟢 **Low Severity**: {s['low_violations']}\n\n")
            
            # Factory analysis
            fa = report['factory_analysis']
            f.write("## Repository Factory Analysis\n")
            f.write(f"- **Total Factories**: {fa['total_factories']}\n")
            f.write(f"- **Working Factories**: {fa['working_factories']}\n")
            f.write(f"- **Broken Factories**: {len(fa['broken_factories'])}\n\n")
            
            if fa['factories']:
                f.write("### Factory Details\n")
                f.write("| Factory | Env Check | DB Check | Redis Check | Status |\n")
                f.write("|---------|-----------|----------|-------------|--------|\n")
                for factory in fa['factories']:
                    status = "✅ Working" if factory['working'] else "❌ Broken"
                    f.write(f"| {factory['name']} | ")
                    f.write(f"{'✅' if factory['checks_environment'] else '❌'} | ")
                    f.write(f"{'✅' if factory['checks_database_type'] else '❌'} | ")
                    f.write(f"{'✅' if factory['checks_redis'] else '❌'} | ")
                    f.write(f"{status} |\n")
                f.write("\n")
            
            # Code paths
            f.write("## Code Path Analysis\n")
            for path in report['code_paths'][:20]:
                status = "✅" if path['follows_ddd'] else "❌"
                f.write(f"\n### {status} {path['name']}\n")
                f.write(f"- **Entry Point**: {path['entry_point']}\n")
                f.write(f"- **Flow**: {path['flow']}\n")
                f.write(f"- **Violations**: {path['violations_count']}\n")
                f.write(f"- **Cache Invalidation**: {'✅' if path['has_cache_invalidation'] else '❌'}\n")
            
            # Detailed violations
            f.write("\n## Detailed Violations\n")
            
            # Group by severity
            for severity in ['HIGH', 'MEDIUM', 'LOW']:
                violations = [v for v in report['detailed_violations'] if v['severity'] == severity]
                if violations:
                    f.write(f"\n### {severity} Severity Violations ({len(violations)})\n")
                    for v in violations[:10]:  # First 10 of each type
                        f.write(f"\n#### {v['type']}\n")
                        f.write(f"- **File**: `{v['file']}`\n")
                        f.write(f"- **Line**: {v['line']}\n")
                        f.write(f"- **Description**: {v['description']}\n")
                        f.write(f"- **Fix**: {v['fix']}\n")


def main():
    """Main execution function"""
    # Get project root
    project_root = Path(__file__).parent.parent
    
    print(f"🔍 Analyzing project: {project_root}")
    
    # Create analyzer
    analyzer = CodePathAnalyzer(project_root)
    
    # Run analysis
    report = analyzer.analyze_all_paths()
    
    # Print report
    analyzer.print_report(report)
    
    # Save report
    output_dir = project_root / "docs" / "architecture" / "compliance_reports"
    analyzer.save_report(report, output_dir)
    
    # Return compliance score for CI/CD integration
    return report['summary']['compliance_score']


if __name__ == "__main__":
    score = main()
    # Exit with non-zero if compliance is below threshold
    exit(0 if score >= 70 else 1)