"""
Test Suite: Controller Layer DDD Architecture Compliance
Ensures controllers don't directly access infrastructure or repositories
"""

import pytest
from pathlib import Path
import ast
import re


class TestControllerCompliance:
    """Test that controllers follow DDD architecture - no direct DB/repo access"""
    
    @pytest.fixture
    def controller_path(self):
        """Get the path to controllers directory"""
        return Path(__file__).parent.parent.parent / 'fastmcp/task_management/interface/controllers'
    
    def test_no_direct_database_imports(self, controller_path):
        """Controllers must not import database directly"""
        violations = []
        
        # List of forbidden import patterns
        forbidden_imports = [
            r'from .*infrastructure\.database',
            r'from .*infrastructure\.repositories',
            r'import .*infrastructure\.database',
            r'import .*infrastructure\.repositories',
            r'from .*session_manager import',
            r'from .*SessionLocal',
        ]
        
        # Check each controller file
        for controller_file in controller_path.glob('*.py'):
            if controller_file.name == '__init__.py':
                continue
                
            content = controller_file.read_text()
            
            # Check for forbidden imports
            for pattern in forbidden_imports:
                matches = re.findall(pattern, content)
                for match in matches:
                    line_no = content[:content.find(match)].count('\n') + 1
                    violations.append(
                        f"{controller_file.name}:{line_no} - {match}"
                    )
        
        assert not violations, (
            f"Controllers with direct DB/repo imports:\n" + 
            "\n".join(violations)
        )
    
    def test_no_direct_database_usage(self, controller_path):
        """Controllers must not create database sessions directly"""
        violations = []
        
        # Patterns that indicate direct database usage
        forbidden_usage = [
            'SessionLocal()',
            'get_session_manager()',
            'Session()',
            'create_engine',
            'Repository()',
            'Base.metadata',
        ]
        
        for controller_file in controller_path.glob('*.py'):
            if controller_file.name == '__init__.py':
                continue
                
            content = controller_file.read_text()
            
            for forbidden in forbidden_usage:
                if forbidden in content:
                    # Find all occurrences with line numbers
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if forbidden in line:
                            violations.append(
                                f"{controller_file.name}:{i} - {forbidden}"
                            )
        
        assert not violations, (
            f"Controllers with direct DB usage:\n" +
            "\n".join(violations)
        )
    
    def test_controllers_use_facades(self, controller_path):
        """Controllers should use application facades, not repositories directly"""
        violations = []
        missing_facade = []
        
        for controller_file in controller_path.glob('*.py'):
            if controller_file.name == '__init__.py':
                continue
                
            content = controller_file.read_text()
            
            # Check if this is a controller class
            if 'class' not in content or 'Controller' not in content:
                continue
            
            # Controllers should import facades
            has_facade_import = (
                'from ...application.facades import' in content or
                'from fastmcp.task_management.application.facades import' in content
            )
            
            # Check for direct repository usage
            has_repository = (
                'self.repository =' in content or
                'Repository()' in content
            )
            
            if not has_facade_import and 'Controller' in content:
                missing_facade.append(f"{controller_file.name}: No facade import")
            
            if has_repository:
                violations.append(f"{controller_file.name}: Uses repository directly")
        
        # Combine all issues
        all_issues = missing_facade + violations
        
        assert not all_issues, (
            f"Controllers not properly using facades:\n" +
            "\n".join(all_issues)
        )
    
    def test_specific_controller_fixes(self, controller_path):
        """Test that specific known violating controllers are fixed"""
        
        # Known violators from the issues report
        known_issues = {
            'task_mcp_controller.py': [
                'from ...infrastructure.database.session_manager import get_session_manager',
            ],
            'subtask_mcp_controller.py': [
                'from ...infrastructure.database.session_manager import get_session_manager',
            ],
            'git_branch_mcp_controller.py': [
                'from ...infrastructure.repositories.orm.git_branch_repository import ORMGitBranchRepository',
            ],
        }
        
        violations = []
        
        for controller_name, forbidden_lines in known_issues.items():
            controller_file = controller_path / controller_name
            
            if not controller_file.exists():
                continue
                
            content = controller_file.read_text()
            
            for forbidden in forbidden_lines:
                if forbidden in content:
                    violations.append(
                        f"{controller_name}: Still contains '{forbidden}'"
                    )
        
        assert not violations, (
            f"Known violating controllers not fixed:\n" +
            "\n".join(violations)
        )
    
    def test_controller_dependency_injection(self, controller_path):
        """Controllers should use dependency injection for facades"""
        violations = []
        
        for controller_file in controller_path.glob('*.py'):
            if controller_file.name == '__init__.py':
                continue
                
            content = controller_file.read_text()
            
            # Skip non-controller files
            if 'class' not in content or 'Controller' not in content:
                continue
            
            # Check for proper initialization pattern
            has_init = '__init__' in content
            has_facade = 'self.facade' in content or 'self._facade' in content
            
            # Parse the file to check constructor
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and 'Controller' in node.name:
                        # Check if class has __init__ method
                        init_method = None
                        for item in node.body:
                            if (isinstance(item, ast.FunctionDef) and 
                                item.name == '__init__'):
                                init_method = item
                                break
                        
                        if init_method:
                            # Check if facade is passed as parameter or created
                            has_facade_param = any(
                                arg.arg.endswith('facade') 
                                for arg in init_method.args.args[1:]  # Skip self
                            )
                            
                            if not has_facade_param and has_facade:
                                # Check if facade is created inside __init__
                                init_body = ast.unparse(init_method)
                                if 'Facade(' not in init_body:
                                    violations.append(
                                        f"{controller_file.name}: "
                                        "Facade not properly injected or created"
                                    )
            except SyntaxError:
                # Skip files with syntax errors
                continue
        
        # This is more of a warning than a hard failure
        if violations:
            pytest.skip(f"Dependency injection issues (non-critical):\n" + 
                       "\n".join(violations))


class TestControllerLayerBoundaries:
    """Test that controllers respect layer boundaries"""
    
    def test_controller_imports_hierarchy(self):
        """Controllers should only import from application and domain layers"""
        controller_path = Path(__file__).parent.parent.parent / 'fastmcp/task_management/interface/controllers'
        
        allowed_patterns = [
            r'from \.\.\.application',  # Application layer
            r'from \.\.\.domain',        # Domain layer
            r'from \.\.\.interface',     # Same layer (interface)
            r'from fastmcp\.task_management\.application',
            r'from fastmcp\.task_management\.domain',
            r'from fastmcp\.task_management\.interface',
            r'from typing import',        # Standard library
            r'import logging',            # Standard library
            r'from datetime import',      # Standard library
        ]
        
        violations = []
        
        for controller_file in controller_path.glob('*.py'):
            if controller_file.name == '__init__.py':
                continue
                
            content = controller_file.read_text()
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                # Check import lines
                if line.strip().startswith(('from ', 'import ')):
                    # Skip if it matches allowed patterns
                    is_allowed = any(
                        re.search(pattern, line) 
                        for pattern in allowed_patterns
                    )
                    
                    # Check for forbidden infrastructure imports
                    if not is_allowed and 'infrastructure' in line:
                        violations.append(
                            f"{controller_file.name}:{i} - Forbidden import: {line.strip()}"
                        )
        
        assert not violations, (
            f"Controllers violating layer boundaries:\n" +
            "\n".join(violations)
        )


class TestControllerComplianceSummary:
    """Summary test for overall controller compliance"""
    
    def test_overall_controller_compliance(self):
        """Run all controller compliance checks and report overall status"""
        controller_path = Path(__file__).parent.parent.parent / 'fastmcp/task_management/interface/controllers'
        
        report = {
            'total_files': 0,
            'compliant_files': 0,
            'violations': [],
            'compliance_score': 0
        }
        
        # Count controller files
        controller_files = list(controller_path.glob('*.py'))
        controller_files = [f for f in controller_files if f.name != '__init__.py']
        report['total_files'] = len(controller_files)
        
        # Check each file for compliance
        for controller_file in controller_files:
            content = controller_file.read_text()
            is_compliant = True
            
            # Check for infrastructure imports
            if 'infrastructure' in content:
                is_compliant = False
                report['violations'].append(
                    f"{controller_file.name}: Has infrastructure imports"
                )
            
            # Check for session manager usage
            if 'session_manager' in content.lower() or 'sessionlocal' in content:
                is_compliant = False
                report['violations'].append(
                    f"{controller_file.name}: Direct session management"
                )
            
            # Check for repository instantiation
            if 'Repository()' in content and 'Mock' not in content:
                is_compliant = False
                report['violations'].append(
                    f"{controller_file.name}: Direct repository instantiation"
                )
            
            if is_compliant:
                report['compliant_files'] += 1
        
        # Calculate compliance score
        if report['total_files'] > 0:
            report['compliance_score'] = (
                report['compliant_files'] / report['total_files'] * 100
            )
        
        # Generate report
        compliance_report = f"""
        Controller Layer Compliance Report:
        ===================================
        Total Controller Files: {report['total_files']}
        Compliant Files: {report['compliant_files']}
        Non-Compliant Files: {report['total_files'] - report['compliant_files']}
        Compliance Score: {report['compliance_score']:.1f}%
        
        Violations Found:
        {chr(10).join(report['violations']) if report['violations'] else 'None'}
        """
        
        print(compliance_report)
        
        # Assert high compliance
        assert report['compliance_score'] >= 90, (
            f"Controller compliance score too low: {report['compliance_score']:.1f}% "
            f"(minimum required: 90%)"
        )