"""Test Suite for Compliance Orchestrator

Comprehensive tests for compliance checking operations, rule evaluation, 
validation logic, and error scenarios.
"""

import pytest
import uuid
import time
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, call, ANY

from fastmcp.task_management.application.orchestrators.compliance_orchestrator import ComplianceOrchestrator
from fastmcp.task_management.domain.enums.compliance_enums import ComplianceLevel, ValidationResult, ProcessStatus
from fastmcp.task_management.domain.value_objects.compliance_objects import ComplianceRule, ValidationReport, ProcessInfo


class TestComplianceOrchestrator:
    """Test suite for ComplianceOrchestrator"""
    
    @pytest.fixture
    def mock_compliance_service(self):
        """Create mock compliance service"""
        mock = Mock()
        mock.validate_operation.return_value = {
            "success": True,
            "compliance_score": 95.0,
            "validation_results": []
        }
        mock.get_compliance_rules.return_value = [
            ComplianceRule(
                rule_id="TEST_RULE",
                name="Test Rule",
                description="Test compliance rule",
                level=ComplianceLevel.HIGH,
                category="test_compliance"
            )
        ]
        return mock
    
    @pytest.fixture
    def mock_audit_service(self):
        """Create mock audit service"""
        mock = Mock()
        mock.log_operation.return_value = None
        mock.generate_compliance_report.return_value = {
            "report_id": "test-report-123",
            "overall_compliance_rate": 92.5,
            "total_operations": 100,
            "compliant_operations": 92,
            "violations": 8
        }
        mock.get_audit_log.return_value = [
            {
                "timestamp": datetime.now().isoformat(),
                "operation": "test_operation",
                "compliance_level": "high",
                "success": True,
                "compliance_score": 95.0
            }
        ]
        mock.get_compliance_metrics.return_value = {
            "total_operations": 100,
            "compliant_operations": 92,
            "violations": 8,
            "last_audit": datetime.now().isoformat()
        }
        return mock
    
    @pytest.fixture
    def mock_process_monitor(self):
        """Create mock process monitor"""
        mock = Mock()
        mock.start_monitoring.return_value = None
        mock.stop_monitoring.return_value = None
        mock.get_active_processes.return_value = {}
        mock.execute_with_timeout.return_value = {
            "success": True,
            "process_id": "process-123",
            "stdout": "Test output",
            "stderr": "",
            "return_code": 0,
            "execution_time": 1.5,
            "timeout_enforced": False
        }
        return mock
    
    @pytest.fixture
    def orchestrator(self, mock_compliance_service, mock_audit_service, mock_process_monitor):
        """Create orchestrator with mocked dependencies"""
        with patch('fastmcp.task_management.application.orchestrators.compliance_orchestrator.ComplianceService', 
                   return_value=mock_compliance_service):
            with patch('fastmcp.task_management.application.orchestrators.compliance_orchestrator.AuditService',
                       return_value=mock_audit_service):
                with patch('fastmcp.task_management.application.orchestrators.compliance_orchestrator.ProcessMonitor',
                           return_value=mock_process_monitor):
                    orchestrator = ComplianceOrchestrator(Path("/test/project"))
                    # Replace with our mocked services
                    orchestrator._compliance_service = mock_compliance_service
                    orchestrator._audit_service = mock_audit_service
                    orchestrator._process_monitor = mock_process_monitor
                    return orchestrator


class TestOrchestratorInitialization:
    """Test orchestrator initialization"""
    
    def test_initialization_success(self):
        """Test successful orchestrator initialization"""
        with patch('fastmcp.task_management.application.orchestrators.compliance_orchestrator.ComplianceService'):
            with patch('fastmcp.task_management.application.orchestrators.compliance_orchestrator.AuditService'):
                with patch('fastmcp.task_management.application.orchestrators.compliance_orchestrator.ProcessMonitor') as mock_monitor:
                    mock_monitor_instance = Mock()
                    mock_monitor.return_value = mock_monitor_instance
                    
                    orchestrator = ComplianceOrchestrator(Path("/test/project"))
                    
                    assert orchestrator.project_root == Path("/test/project")
                    mock_monitor_instance.start_monitoring.assert_called_once()
    
    def test_initialization_with_custom_services(self):
        """Test initialization with custom service instances"""
        mock_compliance = Mock()
        mock_audit = Mock()
        mock_monitor = Mock()
        
        with patch('fastmcp.task_management.application.orchestrators.compliance_orchestrator.ComplianceService', 
                   return_value=mock_compliance):
            with patch('fastmcp.task_management.application.orchestrators.compliance_orchestrator.AuditService',
                       return_value=mock_audit):
                with patch('fastmcp.task_management.application.orchestrators.compliance_orchestrator.ProcessMonitor',
                           return_value=mock_monitor):
                    orchestrator = ComplianceOrchestrator(Path("/test/project"))
                    
                    assert orchestrator._compliance_service == mock_compliance
                    assert orchestrator._audit_service == mock_audit
                    assert orchestrator._process_monitor == mock_monitor


class TestValidateOperation:
    """Test operation validation"""
    
    def test_validate_operation_success(self, orchestrator, mock_compliance_service, mock_audit_service):
        """Test successful operation validation"""
        result = orchestrator.validate_operation("create_file", file_path="/test/file.py")
        
        assert result["success"] is True
        assert result["compliance_score"] == 95.0
        assert "error" not in result
        
        # Verify service calls
        mock_compliance_service.validate_operation.assert_called_once_with(
            "create_file", file_path="/test/file.py"
        )
        mock_audit_service.log_operation.assert_called_once()
    
    def test_validate_operation_failure(self, orchestrator, mock_compliance_service, mock_audit_service):
        """Test operation validation failure"""
        mock_compliance_service.validate_operation.return_value = {
            "success": False,
            "compliance_score": 45.0,
            "error": "Compliance check failed"
        }
        
        result = orchestrator.validate_operation("delete_file", file_path="/critical/system.conf")
        
        assert result["success"] is False
        assert result["compliance_score"] == 45.0
        
        # Verify audit logging happened even on failure
        mock_audit_service.log_operation.assert_called_once()
    
    def test_validate_operation_exception(self, orchestrator, mock_compliance_service, mock_audit_service):
        """Test operation validation with exception"""
        mock_compliance_service.validate_operation.side_effect = Exception("Service error")
        
        result = orchestrator.validate_operation("execute_command", command="dangerous_command")
        
        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "Service error"
        assert result["compliance_score"] == 0.0
        
        # Verify audit logging of error
        mock_audit_service.log_operation.assert_called_once()
        call_args = mock_audit_service.log_operation.call_args[0]
        assert call_args[0] == "execute_command"
        assert call_args[1]["success"] is False
        assert call_args[2] == ComplianceLevel.HIGH
    
    def test_compliance_level_determination(self, orchestrator, mock_compliance_service, mock_audit_service):
        """Test compliance level determination for different operations"""
        test_cases = [
            ("delete_file", ComplianceLevel.CRITICAL),
            ("execute_command", ComplianceLevel.CRITICAL),
            ("modify_system", ComplianceLevel.CRITICAL),
            ("create_file", ComplianceLevel.HIGH),
            ("edit_file", ComplianceLevel.HIGH),
            ("update_config", ComplianceLevel.HIGH),
            ("read_file", ComplianceLevel.MEDIUM),
            ("list_files", ComplianceLevel.MEDIUM),
            ("get_status", ComplianceLevel.MEDIUM),
            ("unknown_operation", ComplianceLevel.LOW)
        ]
        
        for operation, expected_level in test_cases:
            orchestrator.validate_operation(operation)
            
            # Get the last call to log_operation
            call_args = mock_audit_service.log_operation.call_args[0]
            assert call_args[0] == operation
            assert call_args[2] == expected_level


class TestComplianceDashboard:
    """Test compliance dashboard generation"""
    
    def test_get_compliance_dashboard_success(self, orchestrator, mock_audit_service, 
                                             mock_compliance_service, mock_process_monitor):
        """Test successful dashboard generation"""
        result = orchestrator.get_compliance_dashboard()
        
        assert result["success"] is True
        assert "dashboard_id" in result
        assert "generated_at" in result
        assert result["compliance_report"]["overall_compliance_rate"] == 92.5
        assert result["active_processes"] == 0
        assert result["compliance_rules_count"] == 1
        assert result["system_health"]["compliance_service"] == "active"
        assert result["system_health"]["audit_service"] == "active"
        assert result["system_health"]["process_monitor"] == "active"
        assert str(result["project_root"]) == "/test/project"
    
    def test_get_compliance_dashboard_with_active_processes(self, orchestrator, mock_process_monitor):
        """Test dashboard with active processes"""
        mock_process_monitor.get_active_processes.return_value = {
            "proc1": ProcessInfo("proc1", "test command", time.time(), 10, ProcessStatus.RUNNING),
            "proc2": ProcessInfo("proc2", "another command", time.time(), 20, ProcessStatus.RUNNING)
        }
        
        result = orchestrator.get_compliance_dashboard()
        
        assert result["success"] is True
        assert result["active_processes"] == 2
    
    def test_get_compliance_dashboard_failure(self, orchestrator, mock_audit_service):
        """Test dashboard generation failure"""
        mock_audit_service.generate_compliance_report.side_effect = Exception("Report generation failed")
        
        result = orchestrator.get_compliance_dashboard()
        
        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "Report generation failed"
        assert "dashboard_id" in result
        assert "generated_at" in result


class TestExecuteWithCompliance:
    """Test compliant command execution"""
    
    def test_execute_with_compliance_success(self, orchestrator, mock_compliance_service, 
                                            mock_process_monitor):
        """Test successful compliant execution"""
        result = orchestrator.execute_with_compliance("echo 'test'", timeout=5)
        
        assert result["success"] is True
        assert result["compliance_enforced"] is True
        assert result["validation_result"]["success"] is True
        assert result["execution_result"]["success"] is True
        assert result["execution_result"]["stdout"] == "Test output"
        
        # Verify validation happened first
        mock_compliance_service.validate_operation.assert_called_once_with(
            "execute_command", command="echo 'test'"
        )
        mock_process_monitor.execute_with_timeout.assert_called_once_with("echo 'test'", 5)
    
    def test_execute_with_compliance_validation_failure(self, orchestrator, mock_compliance_service,
                                                       mock_process_monitor):
        """Test execution blocked by compliance validation"""
        mock_compliance_service.validate_operation.return_value = {
            "success": False,
            "compliance_score": 30.0,
            "error": "Command not allowed"
        }
        
        result = orchestrator.execute_with_compliance("rm -rf /", timeout=5)
        
        assert result["success"] is False
        assert result["error"] == "Compliance validation failed"
        assert result["validation_result"]["success"] is False
        assert "execution_result" not in result
        
        # Verify execution was not attempted
        mock_process_monitor.execute_with_timeout.assert_not_called()
    
    def test_execute_with_compliance_execution_failure(self, orchestrator, mock_compliance_service,
                                                       mock_process_monitor):
        """Test execution failure after successful validation"""
        mock_process_monitor.execute_with_timeout.return_value = {
            "success": False,
            "process_id": "failed-123",
            "error": "Command not found",
            "timeout_enforced": False
        }
        
        result = orchestrator.execute_with_compliance("nonexistent_command", timeout=10)
        
        assert result["success"] is False
        assert result["compliance_enforced"] is True
        assert result["validation_result"]["success"] is True
        assert result["execution_result"]["success"] is False
    
    def test_execute_with_compliance_timeout(self, orchestrator, mock_compliance_service,
                                            mock_process_monitor):
        """Test execution with timeout"""
        mock_process_monitor.execute_with_timeout.return_value = {
            "success": False,
            "process_id": "timeout-123",
            "error": "Command timed out",
            "timeout_enforced": True,
            "execution_time": 10
        }
        
        result = orchestrator.execute_with_compliance("sleep 100", timeout=10)
        
        assert result["success"] is False
        assert result["compliance_enforced"] is True
        assert result["execution_result"]["timeout_enforced"] is True
    
    def test_execute_with_compliance_exception(self, orchestrator, mock_compliance_service):
        """Test execution with exception"""
        mock_compliance_service.validate_operation.side_effect = Exception("Validation error")
        
        result = orchestrator.execute_with_compliance("test command")
        
        assert result["success"] is False
        assert result["compliance_enforced"] is False
        assert "error" in result


class TestAuditTrail:
    """Test audit trail operations"""
    
    def test_get_audit_trail_success(self, orchestrator, mock_audit_service):
        """Test successful audit trail retrieval"""
        result = orchestrator.get_audit_trail(limit=50)
        
        assert result["success"] is True
        assert len(result["audit_entries"]) == 1
        assert result["total_entries"] == 1
        assert result["metrics"]["total_operations"] == 100
        assert result["metrics"]["compliant_operations"] == 92
        
        mock_audit_service.get_audit_log.assert_called_once_with(50)
        mock_audit_service.get_compliance_metrics.assert_called_once()
    
    def test_get_audit_trail_with_default_limit(self, orchestrator, mock_audit_service):
        """Test audit trail with default limit"""
        result = orchestrator.get_audit_trail()
        
        assert result["success"] is True
        mock_audit_service.get_audit_log.assert_called_once_with(100)
    
    def test_get_audit_trail_failure(self, orchestrator, mock_audit_service):
        """Test audit trail retrieval failure"""
        mock_audit_service.get_audit_log.side_effect = Exception("Database error")
        
        result = orchestrator.get_audit_trail()
        
        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "Database error"


class TestShutdown:
    """Test orchestrator shutdown"""
    
    def test_shutdown_success(self, orchestrator, mock_process_monitor):
        """Test successful shutdown"""
        orchestrator.shutdown()
        
        mock_process_monitor.stop_monitoring.assert_called_once()
    
    def test_shutdown_with_error(self, orchestrator, mock_process_monitor):
        """Test shutdown with error handling"""
        mock_process_monitor.stop_monitoring.side_effect = Exception("Shutdown error")
        
        # Should not raise exception
        orchestrator.shutdown()
        
        mock_process_monitor.stop_monitoring.assert_called_once()


class TestIntegrationScenarios:
    """Test complex integration scenarios"""
    
    def test_full_compliance_workflow(self, orchestrator, mock_compliance_service, 
                                     mock_audit_service, mock_process_monitor):
        """Test complete compliance workflow"""
        # 1. Validate a high-risk operation
        validation_result = orchestrator.validate_operation("delete_file", 
                                                          file_path="/important/data.db")
        assert validation_result["success"] is True
        
        # 2. Execute a command with compliance
        execution_result = orchestrator.execute_with_compliance(
            "backup_database.sh", 
            timeout=30,
            user_id="test-user"
        )
        assert execution_result["success"] is True
        
        # 3. Generate compliance dashboard
        dashboard = orchestrator.get_compliance_dashboard()
        assert dashboard["success"] is True
        assert dashboard["compliance_rules_count"] > 0
        
        # 4. Get audit trail
        audit_trail = orchestrator.get_audit_trail(limit=10)
        assert audit_trail["success"] is True
        
        # Verify all services were used
        assert mock_compliance_service.validate_operation.call_count >= 2
        assert mock_audit_service.log_operation.call_count >= 1
        assert mock_process_monitor.execute_with_timeout.call_count == 1
    
    def test_compliance_enforcement_workflow(self, orchestrator, mock_compliance_service):
        """Test compliance enforcement prevents dangerous operations"""
        # Configure compliance service to reject dangerous operations
        def validate_side_effect(operation, **kwargs):
            if operation == "execute_command" and "rm -rf" in kwargs.get("command", ""):
                return {
                    "success": False,
                    "compliance_score": 0.0,
                    "error": "Dangerous operation blocked"
                }
            return {
                "success": True,
                "compliance_score": 95.0,
                "validation_results": []
            }
        
        mock_compliance_service.validate_operation.side_effect = validate_side_effect
        
        # Safe operation should succeed
        safe_result = orchestrator.execute_with_compliance("ls -la")
        assert safe_result["success"] is True
        assert safe_result["compliance_enforced"] is True
        
        # Dangerous operation should be blocked
        dangerous_result = orchestrator.execute_with_compliance("rm -rf /")
        assert dangerous_result["success"] is False
        assert dangerous_result["error"] == "Compliance validation failed"
        assert dangerous_result["validation_result"]["error"] == "Dangerous operation blocked"
    
    def test_process_monitoring_lifecycle(self, orchestrator, mock_process_monitor):
        """Test process monitoring through execution lifecycle"""
        # Configure process monitor to simulate timeout
        def execute_side_effect(command, timeout):
            if "sleep" in command:
                return {
                    "success": False,
                    "process_id": "sleep-proc",
                    "error": "Command timed out",
                    "timeout_enforced": True,
                    "execution_time": timeout
                }
            return {
                "success": True,
                "process_id": str(uuid.uuid4()),
                "stdout": "Command output",
                "stderr": "",
                "return_code": 0,
                "execution_time": 0.5,
                "timeout_enforced": False
            }
        
        mock_process_monitor.execute_with_timeout.side_effect = execute_side_effect
        
        # Normal execution
        normal_result = orchestrator.execute_with_compliance("echo 'test'", timeout=5)
        assert normal_result["success"] is True
        assert normal_result["execution_result"]["timeout_enforced"] is False
        
        # Timeout execution
        timeout_result = orchestrator.execute_with_compliance("sleep 100", timeout=2)
        assert timeout_result["success"] is False
        assert timeout_result["execution_result"]["timeout_enforced"] is True
        assert timeout_result["execution_result"]["execution_time"] == 2


class TestErrorHandling:
    """Test error handling scenarios"""
    
    def test_cascading_service_failures(self, orchestrator):
        """Test handling of cascading service failures"""
        with patch.object(orchestrator._compliance_service, 'validate_operation',
                         side_effect=Exception("Compliance service down")):
            result = orchestrator.validate_operation("test_operation")
            
            assert result["success"] is False
            assert result["compliance_score"] == 0.0
            assert "Compliance service down" in result["error"]
    
    def test_partial_service_availability(self, orchestrator, mock_compliance_service, 
                                         mock_audit_service):
        """Test operation with partial service availability"""
        # Audit service fails but compliance should still work
        mock_audit_service.log_operation.side_effect = Exception("Audit service unavailable")
        
        result = orchestrator.validate_operation("create_file", file_path="/test/file.py")
        
        # Operation should still succeed despite audit failure
        assert result["success"] is True
        assert result["compliance_score"] == 95.0
    
    def test_invalid_operation_parameters(self, orchestrator):
        """Test handling of invalid operation parameters"""
        # Empty operation
        result = orchestrator.validate_operation("")
        assert "success" in result
        
        # None operation
        result = orchestrator.validate_operation(None)
        assert result["success"] is False
        
        # Operation with invalid kwargs
        result = orchestrator.validate_operation("test_op", **{"invalid\nkey": "value"})
        assert "success" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])