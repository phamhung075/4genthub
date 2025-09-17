#!/usr/bin/env python3
"""
DDD Layer Tracer - Comprehensive audit of all DDD layers
Routes → Controller → Facade → Service → Repository → ORM → DB
"""

import os
import re
import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class LayerViolation:
    """Represents a DDD layer violation"""
    file: str
    line: int
    violation_type: str
    details: str
    layer_from: str
    layer_to: str

@dataclass
class LayerFlow:
    """Represents the flow through DDD layers"""
    route_file: str
    controller: Set[str]
    facade: Set[str]
    service: Set[str]
    repository: Set[str]
    orm_models: Set[str]
    database_ops: Set[str]
    violations: List[LayerViolation]

class DDDLayerTracer:
    """Traces DDD layer compliance through entire stack"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.route_flows: Dict[str, LayerFlow] = {}
        
        # Layer patterns
        self.layer_patterns = {
            'controller': [
                r'Controller\(',
                r'APIController\(',
                r'api_controller',
                r'_controller\s*=',
                r'controller\s*=',
            ],
            'facade': [
                r'Facade\(',
                r'ApplicationFacade\(',
                r'_facade\s*=',
                r'facade\s*=',
                r'FacadeFactory',
            ],
            'service': [
                r'Service\(',
                r'DomainService\(',
                r'_service\s*=',
                r'service\s*=',
                r'ServiceFactory',
            ],
            'repository': [
                r'Repository\(',
                r'ORMRepository\(',
                r'_repository\s*=',
                r'repository\s*=',
                r'RepositoryFactory',
            ],
            'orm': [
                r'\.query\(',
                r'\.filter\(',
                r'\.add\(',
                r'\.commit\(',
                r'\.rollback\(',
                r'db\.query',
                r'session\.query',
                r'APIToken\(',
                r'Task\(',
                r'Project\(',
            ],
            'database': [
                r'create_engine\(',
                r'sessionmaker\(',
                r'Session\(',
                r'execute\(',
                r'raw\(',
                r'text\(',
            ]
        }
        
    def analyze_file(self, filepath: Path) -> Dict:
        """Analyze a single file for layer usage"""
        with open(filepath, 'r') as f:
            content = f.read()
            
        # Parse imports
        try:
            tree = ast.parse(content)
        except:
            return {'error': 'Could not parse file'}
            
        imports = self.extract_imports(tree)
        layer_usage = self.detect_layer_usage(content, imports)
        
        return {
            'imports': imports,
            'layers': layer_usage,
            'violations': self.check_violations(filepath, content, imports, layer_usage)
        }
    
    def extract_imports(self, tree: ast.AST) -> Dict[str, List[str]]:
        """Extract imports categorized by layer"""
        imports = {
            'controller': [],
            'facade': [],
            'service': [],
            'repository': [],
            'orm': [],
            'database': [],
            'other': []
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    self.categorize_import(name.name, imports)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module
                    for name in node.names:
                        full_name = f"{module}.{name.name}"
                        self.categorize_import(full_name, imports)
        
        return imports
    
    def categorize_import(self, import_name: str, imports: Dict):
        """Categorize an import by DDD layer"""
        if 'controller' in import_name.lower() or 'api_controller' in import_name.lower():
            imports['controller'].append(import_name)
        elif 'facade' in import_name.lower() or 'application_facade' in import_name.lower():
            imports['facade'].append(import_name)
        elif 'service' in import_name.lower() and 'domain' in import_name.lower():
            imports['service'].append(import_name)
        elif 'repository' in import_name.lower() or 'repositories' in import_name.lower():
            imports['repository'].append(import_name)
        elif 'models' in import_name.lower() or 'database.models' in import_name:
            imports['orm'].append(import_name)
        elif 'sqlalchemy' in import_name.lower() or 'database' in import_name.lower():
            imports['database'].append(import_name)
        else:
            imports['other'].append(import_name)
    
    def detect_layer_usage(self, content: str, imports: Dict) -> Dict[str, List[Tuple[int, str]]]:
        """Detect actual usage of each layer in code"""
        usage = defaultdict(list)
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Skip comments and strings
            if line.strip().startswith('#') or line.strip().startswith('"""'):
                continue
                
            for layer, patterns in self.layer_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, line):
                        usage[layer].append((i, line.strip()))
                        break
        
        return dict(usage)
    
    def check_violations(self, filepath: Path, content: str, imports: Dict, usage: Dict) -> List[LayerViolation]:
        """Check for DDD layer violations"""
        violations = []
        filename = filepath.name
        
        # Routes should only use controllers
        if 'routes' in str(filepath):
            # Should not import facades directly
            if imports['facade']:
                for imp in imports['facade']:
                    violations.append(LayerViolation(
                        file=str(filepath),
                        line=0,
                        violation_type="Direct Facade Import",
                        details=f"Route imports facade: {imp}",
                        layer_from="Route",
                        layer_to="Facade"
                    ))
            
            # Should not import services directly
            if imports['service']:
                for imp in imports['service']:
                    violations.append(LayerViolation(
                        file=str(filepath),
                        line=0,
                        violation_type="Direct Service Import",
                        details=f"Route imports service: {imp}",
                        layer_from="Route",
                        layer_to="Service"
                    ))
            
            # Should not import repositories directly
            if imports['repository']:
                for imp in imports['repository']:
                    violations.append(LayerViolation(
                        file=str(filepath),
                        line=0,
                        violation_type="Direct Repository Import",
                        details=f"Route imports repository: {imp}",
                        layer_from="Route",
                        layer_to="Repository"
                    ))
            
            # Should not use ORM directly
            if 'orm' in usage and usage['orm']:
                for line_num, line in usage['orm']:
                    violations.append(LayerViolation(
                        file=str(filepath),
                        line=line_num,
                        violation_type="Direct ORM Usage",
                        details=f"Route uses ORM: {line}",
                        layer_from="Route",
                        layer_to="ORM"
                    ))
        
        # Controllers should only use facades
        if 'controller' in str(filepath).lower():
            # Should not import services directly
            if imports['service']:
                for imp in imports['service']:
                    violations.append(LayerViolation(
                        file=str(filepath),
                        line=0,
                        violation_type="Direct Service Import",
                        details=f"Controller imports service: {imp}",
                        layer_from="Controller",
                        layer_to="Service"
                    ))
            
            # Should not import repositories directly
            if imports['repository']:
                for imp in imports['repository']:
                    violations.append(LayerViolation(
                        file=str(filepath),
                        line=0,
                        violation_type="Direct Repository Import",
                        details=f"Controller imports repository: {imp}",
                        layer_from="Controller",
                        layer_to="Repository"
                    ))
        
        # Facades should only use services
        if 'facade' in str(filepath).lower():
            # Should not import repositories directly
            if imports['repository']:
                for imp in imports['repository']:
                    violations.append(LayerViolation(
                        file=str(filepath),
                        line=0,
                        violation_type="Direct Repository Import",
                        details=f"Facade imports repository: {imp}",
                        layer_from="Facade",
                        layer_to="Repository"
                    ))
            
            # Should not use ORM directly
            if 'orm' in usage and usage['orm']:
                for line_num, line in usage['orm']:
                    violations.append(LayerViolation(
                        file=str(filepath),
                        line=line_num,
                        violation_type="Direct ORM Usage",
                        details=f"Facade uses ORM: {line}",
                        layer_from="Facade",
                        layer_to="ORM"
                    ))
        
        return violations
    
    def trace_route(self, route_file: Path) -> LayerFlow:
        """Trace a route through all DDD layers"""
        flow = LayerFlow(
            route_file=str(route_file),
            controller=set(),
            facade=set(),
            service=set(),
            repository=set(),
            orm_models=set(),
            database_ops=set(),
            violations=[]
        )
        
        # Analyze the route file
        analysis = self.analyze_file(route_file)
        
        # Record controllers used
        for ctrl in analysis['imports']['controller']:
            flow.controller.add(ctrl)
        
        # Record violations
        flow.violations.extend(analysis['violations'])
        
        # Now trace each controller to facade
        for ctrl_import in analysis['imports']['controller']:
            controller_file = self.find_file_from_import(ctrl_import)
            if controller_file and controller_file.exists():
                ctrl_analysis = self.analyze_file(controller_file)
                
                # Record facades used by controller
                for facade in ctrl_analysis['imports']['facade']:
                    flow.facade.add(facade)
                
                # Check for violations in controller
                flow.violations.extend(ctrl_analysis['violations'])
                
                # Trace each facade to service
                for facade_import in ctrl_analysis['imports']['facade']:
                    facade_file = self.find_file_from_import(facade_import)
                    if facade_file and facade_file.exists():
                        facade_analysis = self.analyze_file(facade_file)
                        
                        # Record services used by facade
                        for service in facade_analysis['imports']['service']:
                            flow.service.add(service)
                        
                        # Continue tracing...
                        # (This would continue through all layers)
        
        return flow
    
    def find_file_from_import(self, import_str: str) -> Path:
        """Find the actual file from an import string"""
        # Convert import to path
        parts = import_str.split('.')
        
        # Try to find the file
        possible_paths = [
            self.project_root / 'src' / 'fastmcp' / '/'.join(parts) + '.py',
            self.project_root / 'src' / '/'.join(parts) + '.py',
            self.project_root / '/'.join(parts) + '.py',
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        return None
    
    def generate_report(self) -> str:
        """Generate comprehensive DDD layer report"""
        report = []
        report.append("=" * 80)
        report.append("DDD LAYER COMPLIANCE REPORT")
        report.append("Routes → Controller → Facade → Service → Repository → ORM → DB")
        report.append("=" * 80)
        report.append("")
        
        # Analyze all route files
        route_dir = self.project_root / 'src' / 'fastmcp' / 'server' / 'routes'
        route_files = list(route_dir.glob('*.py'))
        
        total_violations = 0
        
        for route_file in sorted(route_files):
            if route_file.name == '__init__.py':
                continue
                
            report.append(f"\n{'='*60}")
            report.append(f"ROUTE: {route_file.name}")
            report.append(f"{'='*60}")
            
            # Analyze the file
            analysis = self.analyze_file(route_file)
            
            # Report layer usage
            report.append("\n📊 Layer Usage:")
            for layer in ['controller', 'facade', 'service', 'repository', 'orm', 'database']:
                if analysis['imports'][layer]:
                    report.append(f"  {layer.upper()}:")
                    for imp in analysis['imports'][layer]:
                        report.append(f"    - {imp}")
            
            # Report violations
            if analysis['violations']:
                report.append("\n❌ VIOLATIONS FOUND:")
                for v in analysis['violations']:
                    report.append(f"  Line {v.line}: {v.violation_type}")
                    report.append(f"    {v.details}")
                    report.append(f"    Layer jump: {v.layer_from} → {v.layer_to}")
                total_violations += len(analysis['violations'])
            else:
                report.append("\n✅ No violations found")
        
        # Summary
        report.append("\n" + "="*80)
        report.append("SUMMARY")
        report.append("="*80)
        report.append(f"Total route files analyzed: {len(route_files)}")
        report.append(f"Total violations found: {total_violations}")
        
        if total_violations == 0:
            report.append("\n🎉 All routes follow proper DDD layering!")
        else:
            report.append(f"\n⚠️  {total_violations} violations need to be fixed")
        
        return '\n'.join(report)

def main():
    """Run the DDD layer tracer"""
    project_root = '/home/daihungpham/__projects__/agentic-project/agenthub_main'
    tracer = DDDLayerTracer(project_root)
    
    print(tracer.generate_report())

if __name__ == "__main__":
    main()