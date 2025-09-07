#!/usr/bin/env python3
"""
Architecture Compliance Analyzer for DhafnckMCP Project

This script analyzes the codebase to ensure proper architectural flow:
Controller → Facade → Use Case → Repository Factory → Repository

Author: Architecture Compliance Team
Date: 2025-08-28
"""

import os
import re
import ast
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import defaultdict

class ArchitectureAnalyzer:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_root = project_root / "src/fastmcp/task_management"
        self.violations = []
        self.analysis_results = defaultdict(list)
        
    def analyze_controllers(self) -> List[Dict]:
        """Analyze all controllers for architectural compliance"""
        controllers_dir = self.src_root / "interface/controllers"
        violations = []
        
        if not controllers_dir.exists():
            return violations
            
        for file in controllers_dir.rglob("*.py"):
            if "test" in str(file) or "__pycache__" in str(file):
                continue
                
            with open(file, encoding='utf-8') as f:
                content = f.read()
                
            file_rel = file.relative_to(self.project_root)
            
            # Check for direct repository imports (violation)
            if re.search(r'from\s+.*infrastructure\.repositories\.(?!repository_factory)', content):
                violations.append({
                    "file": str(file_rel),
                    "type": "Direct Repository Import",
                    "severity": "HIGH",
                    "pattern": "Importing repository directly instead of using facade"
                })
            
            # Check for direct database imports (violation)
            if re.search(r'from\s+.*infrastructure\.database', content):
                violations.append({
                    "file": str(file_rel),
                    "type": "Direct Database Import",
                    "severity": "HIGH",
                    "pattern": "Controller accessing database directly"
                })
            
            # Check for proper facade usage
            if "Controller" in str(file.name) and "facade" not in content.lower() and "service" not in content.lower():
                violations.append({
                    "file": str(file_rel),
                    "type": "Missing Facade/Service",
                    "severity": "MEDIUM",
                    "pattern": "Controller not using facade or service layer"
                })
                
        return violations
    
    def analyze_facades(self) -> List[Dict]:
        """Check facade implementations for compliance"""
        facades_dir = self.src_root / "application/facades"
        violations = []
        
        if not facades_dir.exists():
            # Also check services directory
            facades_dir = self.src_root / "application/services"
            
        if not facades_dir.exists():
            return violations
            
        for file in facades_dir.rglob("*.py"):
            if "test" in str(file) or "__pycache__" in str(file):
                continue
                
            with open(file, encoding='utf-8') as f:
                content = f.read()
            
            file_rel = file.relative_to(self.project_root)
            
            # Check for hardcoded repository instantiation
            patterns = [
                r'SQLiteTaskRepository\s*\(',
                r'SupabaseTaskRepository\s*\(',
                r'ORMTaskRepository\s*\(',
                r'TaskRepository\s*\(',
                r'GlobalContextRepository\s*\(',
                r'ProjectContextRepository\s*\(',
                r'BranchContextRepository\s*\(',
                r'TaskContextRepository\s*\(',
            ]
            
            for pattern in patterns:
                if re.search(pattern, content) and "RepositoryFactory" not in content:
                    violations.append({
                        "file": str(file_rel),
                        "type": "Hardcoded Repository",
                        "severity": "HIGH",
                        "pattern": f"Hardcoded: {pattern}"
                    })
            
            # Check if using repository factory
            if "Repository" in content and "RepositoryFactory" not in content:
                violations.append({
                    "file": str(file_rel),
                    "type": "Missing Repository Factory",
                    "severity": "MEDIUM",
                    "pattern": "Using repositories without factory"
                })
                    
        return violations
    
    def analyze_cache_invalidation(self) -> List[Dict]:
        """Check if repositories properly invalidate cache"""
        repos_dir = self.src_root / "infrastructure/repositories"
        issues = []
        
        if not repos_dir.exists():
            return issues
            
        for file in repos_dir.rglob("*.py"):
            if "test" in str(file) or "__pycache__" in str(file) or "factory" in str(file):
                continue
                
            with open(file, encoding='utf-8') as f:
                content = f.read()
            
            file_rel = file.relative_to(self.project_root)
            
            # Check methods that should invalidate cache
            modify_methods = ["create", "update", "delete", "save", "remove"]
            
            for method in modify_methods:
                method_pattern = rf'def\s+{method}\s*\([^)]*\)'
                if re.search(method_pattern, content):
                    # Extract the method body
                    method_match = re.search(method_pattern, content)
                    if method_match:
                        method_start = method_match.end()
                        # Simple heuristic: check next 500 chars for invalidation
                        method_snippet = content[method_start:method_start+500]
                        
                        if "invalidate" not in method_snippet.lower() and \
                           "cache" not in method_snippet.lower():
                            issues.append({
                                "file": str(file_rel),
                                "method": method,
                                "type": "Missing Cache Invalidation",
                                "severity": "MEDIUM",
                                "pattern": f"Method '{method}' may not invalidate cache"
                            })
                        
        return issues
    
    def check_repository_factory(self) -> Dict[str, bool]:
        """Verify repository factory implementation"""
        factory_file = self.src_root / "infrastructure/repositories/repository_factory.py"
        checks = {
            "factory_exists": False,
            "checks_environment": False,
            "checks_database_type": False,
            "checks_redis_enabled": False,
            "no_hardcoded_repos": True,
            "has_fallback_logic": False
        }
        
        if not factory_file.exists():
            return checks
            
        checks["factory_exists"] = True
        
        with open(factory_file, encoding='utf-8') as f:
            content = f.read()
        
        # Check for environment variable usage
        if re.search(r"os\.getenv\(['\"]ENVIRONMENT", content):
            checks["checks_environment"] = True
        if re.search(r"os\.getenv\(['\"]DATABASE_TYPE", content):
            checks["checks_database_type"] = True
        if re.search(r"os\.getenv\(['\"]REDIS_ENABLED", content):
            checks["checks_redis_enabled"] = True
        
        # Check for hardcoded repository returns without conditions
        hardcoded_patterns = [
            r'return\s+SQLiteTaskRepository\s*\(\)',
            r'return\s+SupabaseTaskRepository\s*\(\)',
            r'return\s+ORMTaskRepository\s*\(\)'
        ]
        
        for pattern in hardcoded_patterns:
            if re.search(pattern, content):
                # Check if it's within a condition
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if re.search(pattern, line):
                        # Check previous lines for condition
                        context = '\n'.join(lines[max(0, i-2):i+1])
                        if not any(keyword in context for keyword in ['if ', 'elif ', 'else:']):
                            checks["no_hardcoded_repos"] = False
                            break
        
        # Check for fallback logic
        if 'else:' in content or 'except' in content:
            checks["has_fallback_logic"] = True
                
        return checks
    
    def analyze_layer_dependencies(self) -> List[Dict]:
        """Check for layer violation imports"""
        violations = []
        
        # Define allowed import patterns per layer
        layer_rules = {
            "interface": {
                "allowed": ["application", "domain"],
                "forbidden": ["infrastructure.repositories", "infrastructure.database"]
            },
            "application": {
                "allowed": ["domain", "infrastructure.repositories.repository_factory"],
                "forbidden": ["interface", "infrastructure.database"]
            },
            "domain": {
                "allowed": [],  # Domain should be independent
                "forbidden": ["application", "infrastructure", "interface"]
            },
            "infrastructure": {
                "allowed": ["domain"],
                "forbidden": ["interface", "application"]  # Except for specific patterns
            }
        }
        
        for layer, rules in layer_rules.items():
            layer_dir = self.src_root / layer
            if not layer_dir.exists():
                continue
                
            for file in layer_dir.rglob("*.py"):
                if "test" in str(file) or "__pycache__" in str(file):
                    continue
                    
                with open(file, encoding='utf-8') as f:
                    content = f.read()
                
                file_rel = file.relative_to(self.project_root)
                
                # Check forbidden imports
                for forbidden in rules["forbidden"]:
                    if f"from {forbidden}" in content or f"import {forbidden}" in content:
                        violations.append({
                            "file": str(file_rel),
                            "type": "Layer Violation",
                            "severity": "HIGH",
                            "pattern": f"{layer} layer importing from {forbidden}"
                        })
                        
        return violations
    
    def trace_request_flow(self, tool_name: str) -> Dict:
        """Trace the flow for a specific MCP tool"""
        flow = {
            "tool": tool_name,
            "controller": None,
            "facade": None,
            "use_case": None,
            "repository_factory": None,
            "repository": None,
            "cache": None,
            "flow_correct": False
        }
        
        # This would require more complex AST parsing
        # For now, return a template
        return flow
    
    def generate_report(self):
        """Generate comprehensive compliance report"""
        print("=" * 80)
        print(" " * 20 + "ARCHITECTURE COMPLIANCE ANALYSIS REPORT")
        print("=" * 80)
        print(f"\nProject Root: {self.project_root}")
        print(f"Analysis Date: 2025-08-28\n")
        
        # Analyze controllers
        print("\n" + "─" * 60)
        print("📋 CONTROLLER LAYER ANALYSIS")
        print("─" * 60)
        controller_violations = self.analyze_controllers()
        if controller_violations:
            for v in controller_violations:
                severity_color = "🔴" if v['severity'] == "HIGH" else "🟡"
                print(f"{severity_color} [{v['severity']}] {v['file']}")
                print(f"   Issue: {v['type']}")
                print(f"   Pattern: {v['pattern']}\n")
        else:
            print("✅ All controllers comply with architecture")
        
        # Analyze facades
        print("\n" + "─" * 60)
        print("📋 FACADE/SERVICE LAYER ANALYSIS")
        print("─" * 60)
        facade_violations = self.analyze_facades()
        if facade_violations:
            for v in facade_violations:
                severity_color = "🔴" if v['severity'] == "HIGH" else "🟡"
                print(f"{severity_color} [{v['severity']}] {v['file']}")
                print(f"   Issue: {v['type']}")
                print(f"   Pattern: {v['pattern']}\n")
        else:
            print("✅ All facades/services comply with architecture")
        
        # Check cache invalidation
        print("\n" + "─" * 60)
        print("📋 CACHE INVALIDATION ANALYSIS")
        print("─" * 60)
        cache_issues = self.analyze_cache_invalidation()
        if cache_issues:
            for issue in cache_issues:
                severity_color = "🔴" if issue['severity'] == "HIGH" else "🟡"
                print(f"{severity_color} [{issue['severity']}] {issue['file']}")
                print(f"   Method: {issue['method']}")
                print(f"   Issue: {issue['type']}\n")
        else:
            print("✅ All repositories properly handle cache invalidation")
        
        # Check repository factory
        print("\n" + "─" * 60)
        print("📋 REPOSITORY FACTORY ANALYSIS")
        print("─" * 60)
        factory_checks = self.check_repository_factory()
        for check, passed in factory_checks.items():
            status = "✅" if passed else "❌"
            check_display = check.replace("_", " ").title()
            print(f"{status} {check_display}")
        
        # Analyze layer dependencies
        print("\n" + "─" * 60)
        print("📋 LAYER DEPENDENCY ANALYSIS")
        print("─" * 60)
        layer_violations = self.analyze_layer_dependencies()
        if layer_violations:
            for v in layer_violations:
                severity_color = "🔴" if v['severity'] == "HIGH" else "🟡"
                print(f"{severity_color} [{v['severity']}] {v['file']}")
                print(f"   Issue: {v['pattern']}\n")
        else:
            print("✅ All layers respect dependency rules")
        
        # Summary
        print("\n" + "=" * 80)
        print(" " * 30 + "SUMMARY")
        print("=" * 80)
        
        total_issues = (
            len(controller_violations) + 
            len(facade_violations) + 
            len(cache_issues) + 
            len(layer_violations)
        )
        
        high_severity = sum(1 for v in controller_violations + facade_violations + cache_issues + layer_violations 
                           if v.get('severity') == 'HIGH')
        medium_severity = sum(1 for v in controller_violations + facade_violations + cache_issues + layer_violations 
                             if v.get('severity') == 'MEDIUM')
        
        if total_issues == 0:
            print("✅ ARCHITECTURE FULLY COMPLIANT - No violations detected!")
        else:
            print(f"⚠️  FOUND {total_issues} ARCHITECTURE VIOLATIONS")
            print(f"   🔴 High Severity: {high_severity}")
            print(f"   🟡 Medium Severity: {medium_severity}")
            
        print("\n" + "─" * 60)
        print("📊 Compliance Score:")
        if total_issues == 0:
            score = 100
        else:
            # Deduct points based on severity
            score = max(0, 100 - (high_severity * 10) - (medium_severity * 5))
        
        print(f"   Score: {score}/100")
        if score >= 90:
            print("   Grade: A - Excellent")
        elif score >= 80:
            print("   Grade: B - Good")
        elif score >= 70:
            print("   Grade: C - Fair")
        else:
            print("   Grade: D - Needs Improvement")
            
        print("=" * 80)
        
        # Recommendations
        if total_issues > 0:
            print("\n📝 RECOMMENDATIONS:")
            print("─" * 60)
            if any("Repository Factory" in str(v) for v in facade_violations):
                print("1. Replace all hardcoded repository instantiations with RepositoryFactory calls")
            if any("Direct Repository" in str(v) for v in controller_violations):
                print("2. Remove all direct repository imports from controllers - use facades instead")
            if cache_issues:
                print("3. Add cache invalidation to all data modification methods")
            if layer_violations:
                print("4. Refactor code to respect layer boundaries and dependency rules")
            print()

def main():
    """Main entry point for the architecture compliance analyzer"""
    # Get the project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent  # Assuming script is in dhafnck_mcp_main/scripts/
    
    print("\n🔍 Starting Architecture Compliance Analysis...\n")
    
    # Create analyzer and run analysis
    analyzer = ArchitectureAnalyzer(project_root)
    analyzer.generate_report()
    
    print("\n💡 For detailed architecture documentation, see:")
    print("   dhafnck_mcp_main/docs/architecture/")
    print("\n✨ Analysis complete!\n")

if __name__ == "__main__":
    main()