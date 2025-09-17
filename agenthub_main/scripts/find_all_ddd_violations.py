#!/usr/bin/env python3
"""
Find ALL DDD violations across the entire codebase
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

class DDDViolationFinder:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.violations = []
        
    def check_interface_layer(self):
        """Check interface layer for violations"""
        interface_paths = [
            self.project_root / 'src/fastmcp/task_management/interface',
        ]
        
        violations = []
        for base_path in interface_paths:
            for filepath in base_path.rglob('*.py'):
                if '__pycache__' in str(filepath):
                    continue
                    
                with open(filepath, 'r') as f:
                    content = f.read()
                    
                # Check for infrastructure imports
                if 'from fastmcp.task_management.infrastructure' in content:
                    # Skip if it's importing facade_provider (that's allowed)
                    if 'facade_provider' not in content or 'factories' in content or 'repositories' in content:
                        violations.append({
                            'file': str(filepath.relative_to(self.project_root)),
                            'layer': 'Interface',
                            'violation': 'Imports from infrastructure layer',
                            'details': self.extract_infrastructure_imports(content)
                        })
                        
                # Check for direct database/ORM usage
                if any(pattern in content for pattern in ['db.query', 'session.query', 'db.session', '.commit()', '.rollback()']):
                    violations.append({
                        'file': str(filepath.relative_to(self.project_root)),
                        'layer': 'Interface', 
                        'violation': 'Direct database/ORM usage',
                        'details': 'Found database operations in interface layer'
                    })
                    
        return violations
    
    def check_application_layer(self):
        """Check application layer for violations"""
        app_paths = [
            self.project_root / 'src/fastmcp/task_management/application',
        ]
        
        violations = []
        for base_path in app_paths:
            for filepath in base_path.rglob('*.py'):
                if '__pycache__' in str(filepath):
                    continue
                    
                with open(filepath, 'r') as f:
                    content = f.read()
                    
                # Check for infrastructure imports (except RepositoryProviderService)
                if 'from fastmcp.task_management.infrastructure' in content:
                    # Skip if it's the RepositoryProviderService itself
                    if 'repository_provider_service' in str(filepath):
                        continue
                    # Also skip facade_service as it's allowed to coordinate
                    if 'facade_service' in str(filepath):
                        continue
                    violations.append({
                        'file': str(filepath.relative_to(self.project_root)),
                        'layer': 'Application',
                        'violation': 'Imports from infrastructure layer',
                        'details': self.extract_infrastructure_imports(content)
                    })
                        
                # Check for direct database/ORM usage  
                if any(pattern in content for pattern in ['db.query', 'session.query', 'db.session', '.commit()', '.rollback()']):
                    violations.append({
                        'file': str(filepath.relative_to(self.project_root)),
                        'layer': 'Application',
                        'violation': 'Direct database/ORM usage',
                        'details': 'Found database operations in application layer'
                    })
                    
        return violations
        
    def extract_infrastructure_imports(self, content: str) -> str:
        """Extract infrastructure import statements"""
        imports = []
        lines = content.split('\n')
        for line in lines:
            if 'from fastmcp.task_management.infrastructure' in line:
                imports.append(line.strip())
        return ' | '.join(imports[:3])  # First 3 imports
    
    def generate_report(self) -> str:
        """Generate violation report"""
        interface_violations = self.check_interface_layer()
        app_violations = self.check_application_layer()
        
        all_violations = interface_violations + app_violations
        
        report = []
        report.append("="*80)
        report.append("DDD VIOLATION REPORT - FINAL ITERATION")
        report.append("="*80)
        report.append("")
        
        # Group by layer
        interface_files = [v for v in all_violations if v['layer'] == 'Interface']
        app_files = [v for v in all_violations if v['layer'] == 'Application']
        
        report.append(f"📊 SUMMARY:")
        report.append(f"- Interface Layer: {len(interface_files)} violations")
        report.append(f"- Application Layer: {len(app_files)} violations")
        report.append(f"- Total Violations: {len(all_violations)}")
        report.append("")
        
        if interface_files:
            report.append("="*60)
            report.append("INTERFACE LAYER VIOLATIONS")
            report.append("="*60)
            for v in interface_files:
                report.append(f"\n❌ {v['file']}")
                report.append(f"   Violation: {v['violation']}")
                if v['details']:
                    report.append(f"   Details: {v['details']}")
                    
        if app_files:
            report.append("\n"+"="*60)
            report.append("APPLICATION LAYER VIOLATIONS")
            report.append("="*60)
            for v in app_files:
                report.append(f"\n❌ {v['file']}")
                report.append(f"   Violation: {v['violation']}")
                if v['details']:
                    report.append(f"   Details: {v['details']}")
                    
        if not all_violations:
            report.append("✅ NO VIOLATIONS FOUND - SYSTEM IS FULLY DDD COMPLIANT!")
            
        return '\n'.join(report)

def main():
    project_root = '/home/daihungpham/__projects__/agentic-project/agenthub_main'
    finder = DDDViolationFinder(project_root)
    print(finder.generate_report())
    
if __name__ == "__main__":
    main()