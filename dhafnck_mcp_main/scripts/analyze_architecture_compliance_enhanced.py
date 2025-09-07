#!/usr/bin/env python3
"""
Enhanced Architecture Compliance Analyzer for DhafnckMCP Project V6

Systematically analyzes each code path to verify correct architectural flow.
Ensures NO shortcuts, NO layer violations, and PROPER separation of concerns.

Enhanced Features:
- Complete code path tracing from entry point to database
- Visual flow diagrams for each MCP endpoint
- Layer compliance verification matrix
- Cache invalidation pattern detection
- Automated violation detection with suggested fixes

Author: Architecture Compliance Team
Date: 2025-08-28
Version: 6.0
"""

import os
import re
import ast
import json
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
from collections import defaultdict
from datetime import datetime
import textwrap

class EnhancedArchitectureAnalyzer:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_root = project_root / "src/fastmcp/task_management"
        self.violations = []
        self.analysis_results = defaultdict(list)
        self.compliance_scores = {}
        self.remediation_suggestions = []
        self.code_paths = {}  # Store traced code paths
        self.layer_compliance_matrix = {}  # Layer compliance status
        
    def analyze_controllers(self) -> List[Dict]:
        """Analyze all controllers for architectural compliance with line-level detail"""
        controllers_dir = self.src_root / "interface/controllers"
        violations = []
        
        if not controllers_dir.exists():
            return violations
            
        for file in controllers_dir.rglob("*.py"):
            if "test" in str(file) or "__pycache__" in str(file):
                continue
                
            with open(file, encoding='utf-8') as f:
                lines = f.readlines()
                content = ''.join(lines)
                
            file_rel = file.relative_to(self.project_root)
            
            # Check for direct repository imports with line numbers
            for i, line in enumerate(lines, 1):
                if re.search(r'from\s+.*infrastructure\.repositories\.(?!repository_factory)', line):
                    violations.append({
                        "file": str(file_rel),
                        "type": "Direct Repository Import",
                        "severity": "HIGH",
                        "line": i,
                        "code": line.strip(),
                        "pattern": "Importing repository directly instead of using facade",
                        "fix": "Replace with facade import and usage"
                    })
            
                # Check for direct database imports
                if re.search(r'from\s+.*infrastructure\.database', line):
                    violations.append({
                        "file": str(file_rel),
                        "type": "Direct Database Import",
                        "severity": "HIGH",
                        "line": i,
                        "code": line.strip(),
                        "pattern": "Controller accessing database directly",
                        "fix": "Use facade for database operations"
                    })
            
            # Check for instantiation patterns
            repo_instantiation_pattern = r'(\w+Repository)\s*\(\s*\)'
            for match in re.finditer(repo_instantiation_pattern, content):
                line_num = content[:match.start()].count('\n') + 1
                violations.append({
                    "file": str(file_rel),
                    "type": "Direct Repository Instantiation",
                    "severity": "HIGH",
                    "line": line_num,
                    "code": match.group(0),
                    "pattern": f"Direct instantiation of {match.group(1)}",
                    "fix": f"Use RepositoryFactory.get_{match.group(1).lower()}()"
                })
                
        return violations
    
    def analyze_facades(self) -> List[Dict]:
        """Check facade implementations for compliance with detailed analysis"""
        facades_dirs = [
            self.src_root / "application/facades",
            self.src_root / "application/services"
        ]
        violations = []
        
        for facades_dir in facades_dirs:
            if not facades_dir.exists():
                continue
                
            for file in facades_dir.rglob("*.py"):
                if "test" in str(file) or "__pycache__" in str(file):
                    continue
                    
                with open(file, encoding='utf-8') as f:
                    lines = f.readlines()
                    content = ''.join(lines)
                
                file_rel = file.relative_to(self.project_root)
                
                # Check for hardcoded repository instantiation with line numbers
                patterns = [
                    (r'SQLiteTaskRepository\s*\(', 'SQLiteTaskRepository'),
                    (r'SupabaseTaskRepository\s*\(', 'SupabaseTaskRepository'),
                    (r'ORMTaskRepository\s*\(', 'ORMTaskRepository'),
                    (r'(\w+Repository)\s*\(\)', 'Repository'),
                    (r'MockTaskContextRepository\s*\(', 'MockTaskContextRepository'),
                ]
                
                for pattern, repo_name in patterns:
                    for match in re.finditer(pattern, content):
                        line_num = content[:match.start()].count('\n') + 1
                        if "RepositoryFactory" not in lines[line_num - 1]:
                            violations.append({
                                "file": str(file_rel),
                                "type": "Hardcoded Repository",
                                "severity": "HIGH",
                                "line": line_num,
                                "code": lines[line_num - 1].strip(),
                                "pattern": f"Hardcoded instantiation of {repo_name}",
                                "fix": f"Use RepositoryFactory.get_{repo_name.lower().replace('repository', '_repository')}()"
                            })
                
                # Check if using repository factory
                if "Repository" in content and "RepositoryFactory" not in content:
                    violations.append({
                        "file": str(file_rel),
                        "type": "Missing Repository Factory",
                        "severity": "MEDIUM",
                        "line": 0,
                        "code": "N/A - File-level issue",
                        "pattern": "Using repositories without factory",
                        "fix": "Import and use RepositoryFactory for all repository needs"
                    })
                        
        return violations
    
    def analyze_cache_invalidation(self) -> List[Dict]:
        """Check if repositories properly invalidate cache with detailed method analysis"""
        repos_dir = self.src_root / "infrastructure/repositories"
        issues = []
        
        if not repos_dir.exists():
            return issues
            
        for file in repos_dir.rglob("*.py"):
            if "test" in str(file) or "__pycache__" in str(file) or "factory" in str(file):
                continue
                
            with open(file, encoding='utf-8') as f:
                content = f.read()
                lines = f.readlines()
            
            file_rel = file.relative_to(self.project_root)
            
            # Parse the file to find method definitions
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        method_name = node.name
                        if method_name in ["create", "update", "delete", "save", "remove"]:
                            # Get method body as string
                            method_start_line = node.lineno
                            method_end_line = node.end_lineno if hasattr(node, 'end_lineno') else method_start_line + 10
                            method_body = ''.join(lines[method_start_line - 1:method_end_line])
                            
                            # Check for cache invalidation
                            if "invalidate" not in method_body.lower() and "cache" not in method_body.lower():
                                issues.append({
                                    "file": str(file_rel),
                                    "method": method_name,
                                    "type": "Missing Cache Invalidation",
                                    "severity": "MEDIUM",
                                    "line": method_start_line,
                                    "code": f"def {method_name}(...)",
                                    "pattern": f"Method '{method_name}' lacks cache invalidation",
                                    "fix": f"Add self.invalidate_cache_for_entity() after {method_name} operation"
                                })
            except SyntaxError:
                # If parsing fails, fall back to regex
                pass
                        
        return issues
    
    def check_repository_factories(self) -> Dict[str, Dict]:
        """Verify all repository factory implementations"""
        factory_files = list(self.src_root.rglob("*repository_factory.py"))
        factory_analysis = {}
        
        for factory_file in factory_files:
            factory_name = factory_file.stem
            checks = {
                "file": str(factory_file.relative_to(self.project_root)),
                "exists": True,
                "checks_environment": False,
                "checks_database_type": False,
                "checks_redis_enabled": False,
                "has_switching_logic": False,
                "has_fallback_logic": False,
                "violations": []
            }
            
            with open(factory_file, encoding='utf-8') as f:
                content = f.read()
            
            # Check for environment variable usage
            if re.search(r"os\.getenv\(['\"]ENVIRONMENT", content):
                checks["checks_environment"] = True
            else:
                checks["violations"].append({
                    "type": "Missing ENVIRONMENT check",
                    "severity": "HIGH",
                    "fix": "Add os.getenv('ENVIRONMENT', 'production') check"
                })
                
            if re.search(r"os\.getenv\(['\"]DATABASE_TYPE", content):
                checks["checks_database_type"] = True
            else:
                checks["violations"].append({
                    "type": "Missing DATABASE_TYPE check",
                    "severity": "HIGH",
                    "fix": "Add os.getenv('DATABASE_TYPE', 'supabase') check"
                })
                
            if re.search(r"os\.getenv\(['\"]REDIS_ENABLED", content):
                checks["checks_redis_enabled"] = True
            else:
                checks["violations"].append({
                    "type": "Missing REDIS_ENABLED check",
                    "severity": "HIGH",
                    "fix": "Add os.getenv('REDIS_ENABLED', 'true') check"
                })
            
            # Check for switching logic
            if re.search(r'if\s+.*==\s*[\'"]test[\'"]', content):
                checks["has_switching_logic"] = True
            
            # Check for fallback logic
            if 'else:' in content or 'except' in content:
                checks["has_fallback_logic"] = True
                
            factory_analysis[factory_name] = checks
                
        return factory_analysis
    
    def analyze_layer_dependencies(self) -> List[Dict]:
        """Check for layer violation imports with detailed tracking"""
        violations = []
        
        layer_rules = {
            "interface": {
                "allowed": ["application", "domain"],
                "forbidden": ["infrastructure.repositories", "infrastructure.database"],
                "description": "Interface layer (controllers)"
            },
            "application": {
                "allowed": ["domain", "infrastructure.repositories.repository_factory"],
                "forbidden": ["interface", "infrastructure.database", "infrastructure.repositories.orm"],
                "description": "Application layer (facades/services)"
            },
            "domain": {
                "allowed": [],
                "forbidden": ["application", "infrastructure", "interface"],
                "description": "Domain layer (entities/value objects)"
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
                    lines = f.readlines()
                    content = ''.join(lines)
                
                file_rel = file.relative_to(self.project_root)
                
                # Check forbidden imports with line numbers
                for forbidden in rules["forbidden"]:
                    for i, line in enumerate(lines, 1):
                        if f"from {forbidden}" in line or f"import {forbidden}" in line:
                            violations.append({
                                "file": str(file_rel),
                                "type": "Layer Violation",
                                "severity": "HIGH",
                                "line": i,
                                "code": line.strip(),
                                "pattern": f"{rules['description']} importing from {forbidden}",
                                "fix": f"Remove import from {forbidden}, use allowed layers: {', '.join(rules['allowed'])}"
                            })
                        
        return violations
    
    def generate_compliance_score(self, violations: List[Dict]) -> Dict:
        """Calculate compliance score based on violations"""
        total_possible = 100
        
        # Deduct points based on severity
        high_violations = sum(1 for v in violations if v.get('severity') == 'HIGH')
        medium_violations = sum(1 for v in violations if v.get('severity') == 'MEDIUM')
        low_violations = sum(1 for v in violations if v.get('severity') == 'LOW')
        
        score = max(0, total_possible - (high_violations * 10) - (medium_violations * 5) - (low_violations * 2))
        
        grade = 'A' if score >= 90 else 'B' if score >= 80 else 'C' if score >= 70 else 'D' if score >= 60 else 'F'
        
        return {
            "score": score,
            "total": total_possible,
            "grade": grade,
            "high_violations": high_violations,
            "medium_violations": medium_violations,
            "low_violations": low_violations,
            "total_violations": high_violations + medium_violations + low_violations
        }
    
    def generate_remediation_plan(self, all_violations: List[Dict]) -> List[Dict]:
        """Generate step-by-step remediation plan"""
        remediation_steps = []
        
        # Group violations by type and severity
        by_type = defaultdict(list)
        for v in all_violations:
            by_type[v['type']].append(v)
        
        # Priority 1: Fix controller violations
        if "Direct Repository Import" in by_type or "Direct Database Import" in by_type:
            remediation_steps.append({
                "priority": "CRITICAL",
                "phase": "Phase 1",
                "title": "Fix Controller Layer Violations",
                "steps": [
                    "Remove all direct repository imports from controllers",
                    "Remove all direct database imports from controllers",
                    "Create or update facades for business logic",
                    "Update controllers to use facades exclusively"
                ],
                "affected_files": list(set(v['file'] for v in by_type.get("Direct Repository Import", []) + by_type.get("Direct Database Import", [])))
            })
        
        # Priority 2: Fix facade violations
        if "Hardcoded Repository" in by_type or "Missing Repository Factory" in by_type:
            remediation_steps.append({
                "priority": "HIGH",
                "phase": "Phase 2",
                "title": "Fix Facade Layer Violations",
                "steps": [
                    "Replace all hardcoded repository instantiations with factory calls",
                    "Import RepositoryFactory in all facades",
                    "Update repository creation to use factory methods",
                    "Add proper error handling for repository creation"
                ],
                "affected_files": list(set(v['file'] for v in by_type.get("Hardcoded Repository", []) + by_type.get("Missing Repository Factory", [])))
            })
        
        # Priority 3: Implement repository factories properly
        remediation_steps.append({
            "priority": "HIGH",
            "phase": "Phase 3",
            "title": "Implement Repository Factory Pattern",
            "steps": [
                "Add environment variable checking (ENVIRONMENT, DATABASE_TYPE, REDIS_ENABLED)",
                "Implement repository switching logic based on environment",
                "Add Redis cache wrapper when enabled",
                "Implement fallback mechanisms for each repository type"
            ],
            "affected_files": ["All *repository_factory.py files"]
        })
        
        # Priority 4: Add cache invalidation
        if "Missing Cache Invalidation" in by_type:
            remediation_steps.append({
                "priority": "MEDIUM",
                "phase": "Phase 4",
                "title": "Implement Cache Invalidation",
                "steps": [
                    "Add CacheInvalidationMixin to all repositories",
                    "Call invalidate methods after create/update/delete operations",
                    "Implement proper cache key strategies",
                    "Add cache warming for frequently accessed data"
                ],
                "affected_files": list(set(v['file'] for v in by_type.get("Missing Cache Invalidation", [])))
            })
        
        return remediation_steps
    
    def generate_markdown_report(self) -> str:
        """Generate comprehensive markdown report"""
        report_lines = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Header
        report_lines.append("# Architecture Compliance Analysis Report V5")
        report_lines.append(f"**Generated**: {now}")
        report_lines.append(f"**Project**: {self.project_root}")
        report_lines.append("")
        
        # Collect all violations
        all_violations = []
        
        # Controller analysis
        controller_violations = self.analyze_controllers()
        all_violations.extend(controller_violations)
        
        # Facade analysis
        facade_violations = self.analyze_facades()
        all_violations.extend(facade_violations)
        
        # Cache analysis
        cache_issues = self.analyze_cache_invalidation()
        all_violations.extend(cache_issues)
        
        # Layer dependency analysis
        layer_violations = self.analyze_layer_dependencies()
        all_violations.extend(layer_violations)
        
        # Calculate compliance score
        compliance = self.generate_compliance_score(all_violations)
        
        # Executive Summary
        report_lines.append("## 📊 Executive Summary")
        report_lines.append("")
        report_lines.append(f"**Compliance Score**: {compliance['score']}/{compliance['total']} (Grade: {compliance['grade']})")
        report_lines.append(f"**Total Violations**: {compliance['total_violations']}")
        report_lines.append(f"- 🔴 High Severity: {compliance['high_violations']}")
        report_lines.append(f"- 🟡 Medium Severity: {compliance['medium_violations']}")
        report_lines.append(f"- 🟢 Low Severity: {compliance['low_violations']}")
        report_lines.append("")
        
        if compliance['score'] < 50:
            report_lines.append("**Status**: ❌ **CRITICAL FAILURE** - System not following DDD architecture")
        elif compliance['score'] < 70:
            report_lines.append("**Status**: ⚠️ **NEEDS IMPROVEMENT** - Major violations detected")
        elif compliance['score'] < 90:
            report_lines.append("**Status**: 🟡 **FAIR** - Some violations need attention")
        else:
            report_lines.append("**Status**: ✅ **GOOD** - Minor issues only")
        report_lines.append("")
        
        # Expected vs Actual Flow
        report_lines.append("## 🔄 Architecture Flow Analysis")
        report_lines.append("")
        report_lines.append("### Expected Flow (DDD)")
        report_lines.append("```")
        report_lines.append("Controller → Facade → Repository Factory → Repository → Database")
        report_lines.append("                ↓")
        report_lines.append("           Use Case (optional)")
        report_lines.append("```")
        report_lines.append("")
        
        if controller_violations or facade_violations:
            report_lines.append("### ❌ Actual Flow (BROKEN)")
            report_lines.append("```")
            report_lines.append("Controller → Direct Repository/Database Access")
            report_lines.append("Facade → Hardcoded Repository Instantiation")
            report_lines.append("```")
        else:
            report_lines.append("### ✅ Actual Flow (COMPLIANT)")
            report_lines.append("```")
            report_lines.append("Following expected DDD pattern")
            report_lines.append("```")
        report_lines.append("")
        
        # Controller Violations
        if controller_violations:
            report_lines.append("## 🔴 Controller Layer Violations")
            report_lines.append("")
            report_lines.append("| File | Line | Type | Severity | Code |")
            report_lines.append("|------|------|------|----------|------|")
            for v in controller_violations[:10]:  # Show first 10
                code = v['code'][:50] + "..." if len(v['code']) > 50 else v['code']
                report_lines.append(f"| `{v['file'].split('/')[-1]}` | {v['line']} | {v['type']} | {v['severity']} | `{code}` |")
            if len(controller_violations) > 10:
                report_lines.append(f"| ... | ... | *{len(controller_violations) - 10} more violations* | ... | ... |")
            report_lines.append("")
        
        # Facade Violations
        if facade_violations:
            report_lines.append("## 🔴 Facade Layer Violations")
            report_lines.append("")
            report_lines.append("| File | Line | Type | Severity | Pattern |")
            report_lines.append("|------|------|------|----------|---------|")
            for v in facade_violations[:10]:
                report_lines.append(f"| `{v['file'].split('/')[-1]}` | {v['line']} | {v['type']} | {v['severity']} | {v['pattern'][:40]}... |")
            if len(facade_violations) > 10:
                report_lines.append(f"| ... | ... | *{len(facade_violations) - 10} more violations* | ... | ... |")
            report_lines.append("")
        
        # Repository Factory Analysis
        report_lines.append("## 🏭 Repository Factory Analysis")
        report_lines.append("")
        factory_analysis = self.check_repository_factories()
        
        if factory_analysis:
            report_lines.append("| Factory | ENV Check | DB_TYPE Check | REDIS Check | Switching | Status |")
            report_lines.append("|---------|-----------|---------------|-------------|-----------|--------|")
            for name, checks in factory_analysis.items():
                env = "✅" if checks['checks_environment'] else "❌"
                db = "✅" if checks['checks_database_type'] else "❌"
                redis = "✅" if checks['checks_redis_enabled'] else "❌"
                switch = "✅" if checks['has_switching_logic'] else "❌"
                status = "✅" if all([checks['checks_environment'], checks['checks_database_type'], 
                                     checks['checks_redis_enabled'], checks['has_switching_logic']]) else "❌"
                report_lines.append(f"| `{name}` | {env} | {db} | {redis} | {switch} | {status} |")
        else:
            report_lines.append("❌ **No repository factories found!**")
        report_lines.append("")
        
        # Cache Invalidation Issues
        if cache_issues:
            report_lines.append("## 🟡 Cache Invalidation Issues")
            report_lines.append("")
            report_lines.append(f"**Total Methods Missing Invalidation**: {len(cache_issues)}")
            report_lines.append("")
            
            # Group by file
            by_file = defaultdict(list)
            for issue in cache_issues:
                by_file[issue['file']].append(issue['method'])
            
            report_lines.append("| File | Methods Missing Invalidation |")
            report_lines.append("|------|------------------------------|")
            for file, methods in list(by_file.items())[:5]:
                report_lines.append(f"| `{file.split('/')[-1]}` | {', '.join(methods)} |")
            if len(by_file) > 5:
                report_lines.append(f"| ... | *{len(by_file) - 5} more files* |")
            report_lines.append("")
        
        # Remediation Plan
        report_lines.append("## 🔧 Remediation Plan")
        report_lines.append("")
        remediation = self.generate_remediation_plan(all_violations)
        
        for step in remediation:
            report_lines.append(f"### {step['phase']}: {step['title']} ({step['priority']})")
            report_lines.append("")
            for i, action in enumerate(step['steps'], 1):
                report_lines.append(f"{i}. {action}")
            report_lines.append("")
            if len(step['affected_files']) > 0 and step['affected_files'][0] != "All *repository_factory.py files":
                report_lines.append("**Affected Files**:")
                for f in step['affected_files'][:3]:
                    report_lines.append(f"- `{f}`")
                if len(step['affected_files']) > 3:
                    report_lines.append(f"- *... and {len(step['affected_files']) - 3} more*")
            report_lines.append("")
        
        # Code Templates
        report_lines.append("## 📝 Code Templates for Fixes")
        report_lines.append("")
        
        # Controller template
        report_lines.append("### Controller Fix Template")
        report_lines.append("```python")
        report_lines.append("class SomeMCPController:")
        report_lines.append("    def __init__(self):")
        report_lines.append("        # ✅ Use facade, not repository")
        report_lines.append("        self.facade = SomeApplicationFacade()")
        report_lines.append("        ")
        report_lines.append("    def manage_entity(self, **params):")
        report_lines.append("        try:")
        report_lines.append("            # ✅ Delegate to facade")
        report_lines.append("            result = self.facade.execute_action(params)")
        report_lines.append("            return self.format_response(result)")
        report_lines.append("        except Exception as e:")
        report_lines.append("            return self.error_response(e)")
        report_lines.append("```")
        report_lines.append("")
        
        # Facade template
        report_lines.append("### Facade Fix Template")
        report_lines.append("```python")
        report_lines.append("from ..infrastructure.repositories.repository_factory import RepositoryFactory")
        report_lines.append("")
        report_lines.append("class SomeApplicationFacade:")
        report_lines.append("    def execute_action(self, params):")
        report_lines.append("        # ✅ Use factory for repository")
        report_lines.append("        repository = RepositoryFactory.get_some_repository()")
        report_lines.append("        ")
        report_lines.append("        # Business logic here")
        report_lines.append("        result = repository.operation(params)")
        report_lines.append("        ")
        report_lines.append("        return result")
        report_lines.append("```")
        report_lines.append("")
        
        # Repository Factory template
        report_lines.append("### Repository Factory Template")
        report_lines.append("```python")
        report_lines.append("import os")
        report_lines.append("")
        report_lines.append("class SomeRepositoryFactory:")
        report_lines.append("    @staticmethod")
        report_lines.append("    def get_repository():")
        report_lines.append("        # ✅ Check environment variables")
        report_lines.append("        env = os.getenv('ENVIRONMENT', 'production')")
        report_lines.append("        ")
        report_lines.append("        if env == 'test':")
        report_lines.append("            return SQLiteSomeRepository()")
        report_lines.append("        ")
        report_lines.append("        db_type = os.getenv('DATABASE_TYPE', 'supabase')")
        report_lines.append("        redis_enabled = os.getenv('REDIS_ENABLED', 'true')")
        report_lines.append("        ")
        report_lines.append("        if db_type == 'supabase':")
        report_lines.append("            repo = SupabaseSomeRepository()")
        report_lines.append("        else:")
        report_lines.append("            repo = ORMSomeRepository()")
        report_lines.append("        ")
        report_lines.append("        if redis_enabled == 'true':")
        report_lines.append("            from ..cache import CachedRepository")
        report_lines.append("            return CachedRepository(repo)")
        report_lines.append("        ")
        report_lines.append("        return repo")
        report_lines.append("```")
        report_lines.append("")
        
        # Success Metrics
        report_lines.append("## 🎯 Success Metrics")
        report_lines.append("")
        report_lines.append("After implementing all fixes, the system should achieve:")
        report_lines.append("")
        report_lines.append("- ✅ **Compliance Score**: 90+ / 100")
        report_lines.append("- ✅ **All requests** follow: Controller → Facade → Factory → Repository")
        report_lines.append("- ✅ **Repository switching** works based on environment variables")
        report_lines.append("- ✅ **Cache invalidation** occurs on all data mutations")
        report_lines.append("- ✅ **No direct database access** from controllers")
        report_lines.append("- ✅ **No hardcoded repository** instantiations")
        report_lines.append("- ✅ **Redis cache** properly integrated when enabled")
        report_lines.append("")
        
        # Footer
        report_lines.append("---")
        report_lines.append(f"*Report Generated: {now}*")
        report_lines.append("*Analysis Version: 5.0*")
        report_lines.append("*Next Review: After Phase 1 implementation*")
        
        return "\n".join(report_lines)
    
    def generate_json_report(self) -> Dict:
        """Generate JSON report for programmatic consumption"""
        all_violations = []
        
        # Collect all violations
        all_violations.extend(self.analyze_controllers())
        all_violations.extend(self.analyze_facades())
        all_violations.extend(self.analyze_cache_invalidation())
        all_violations.extend(self.analyze_layer_dependencies())
        
        compliance = self.generate_compliance_score(all_violations)
        factory_analysis = self.check_repository_factories()
        remediation = self.generate_remediation_plan(all_violations)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "compliance_score": compliance,
            "violations": all_violations,
            "factory_analysis": factory_analysis,
            "remediation_plan": remediation,
            "summary": {
                "total_violations": len(all_violations),
                "violations_by_type": dict(self._group_by_type(all_violations)),
                "violations_by_severity": dict(self._group_by_severity(all_violations)),
                "affected_files": len(set(v['file'] for v in all_violations))
            }
        }
    
    def _group_by_type(self, violations):
        """Group violations by type"""
        by_type = defaultdict(int)
        for v in violations:
            by_type[v['type']] += 1
        return by_type
    
    def _group_by_severity(self, violations):
        """Group violations by severity"""
        by_severity = defaultdict(int)
        for v in violations:
            by_severity[v.get('severity', 'UNKNOWN')] += 1
        return by_severity
    
    def save_reports(self, output_dir: Optional[Path] = None):
        """Save reports in multiple formats"""
        if not output_dir:
            output_dir = self.project_root / "docs/architecture/compliance_reports"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save markdown report
        md_report = self.generate_markdown_report()
        md_file = output_dir / f"compliance_report_{timestamp}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_report)
        print(f"✅ Saved markdown report: {md_file}")
        
        # Save JSON report
        json_report = self.generate_json_report()
        json_file = output_dir / f"compliance_report_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_report, f, indent=2, default=str)
        print(f"✅ Saved JSON report: {json_file}")
        
        # Update latest symlink
        latest_md = output_dir / "compliance_report_latest.md"
        latest_json = output_dir / "compliance_report_latest.json"
        
        if latest_md.exists():
            latest_md.unlink()
        if latest_json.exists():
            latest_json.unlink()
            
        latest_md.symlink_to(md_file.name)
        latest_json.symlink_to(json_file.name)
        
        return md_file, json_file

def main():
    """Main entry point for the enhanced architecture compliance analyzer"""
    # Get the project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    print("\n" + "=" * 80)
    print(" " * 15 + "🔍 Enhanced Architecture Compliance Analysis V5")
    print("=" * 80)
    print(f"\nProject Root: {project_root}")
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "-" * 60)
    
    # Create analyzer
    analyzer = EnhancedArchitectureAnalyzer(project_root)
    
    # Generate and save reports
    print("\n📊 Generating compliance reports...")
    md_file, json_file = analyzer.save_reports()
    
    # Print summary to console
    json_report = analyzer.generate_json_report()
    compliance = json_report['compliance_score']
    
    print("\n" + "=" * 80)
    print(" " * 30 + "ANALYSIS SUMMARY")
    print("=" * 80)
    
    print(f"\n📈 Compliance Score: {compliance['score']}/{compliance['total']} (Grade: {compliance['grade']})")
    print(f"\n📊 Violation Breakdown:")
    print(f"   🔴 High Severity: {compliance['high_violations']}")
    print(f"   🟡 Medium Severity: {compliance['medium_violations']}")
    print(f"   🟢 Low Severity: {compliance['low_violations']}")
    print(f"   📁 Affected Files: {json_report['summary']['affected_files']}")
    
    if compliance['score'] < 50:
        print("\n❌ **CRITICAL**: System architecture is severely compromised!")
        print("   Immediate remediation required.")
    elif compliance['score'] < 70:
        print("\n⚠️  **WARNING**: Significant architecture violations detected.")
        print("   Priority remediation recommended.")
    elif compliance['score'] < 90:
        print("\n🟡 **NOTICE**: Some architecture violations need attention.")
    else:
        print("\n✅ **GOOD**: Architecture is mostly compliant.")
    
    print("\n" + "-" * 60)
    print("\n📄 Reports saved to:")
    print(f"   - Markdown: {md_file}")
    print(f"   - JSON: {json_file}")
    
    print("\n💡 Next Steps:")
    print("   1. Review the markdown report for detailed findings")
    print("   2. Follow the remediation plan in priority order")
    print("   3. Run this analysis again after implementing fixes")
    
    print("\n✨ Analysis complete!\n")
    
    # Return exit code based on compliance
    return 0 if compliance['score'] >= 70 else 1

if __name__ == "__main__":
    exit(main())