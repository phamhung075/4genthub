#!/usr/bin/env python3
"""
WebSocket Security Test Runner

Comprehensive test execution script for WebSocket security validation.
Runs all security tests and generates detailed security report.

Usage:
    python run_security_tests.py [--category CATEGORY] [--report] [--verbose]

Categories:
    - all: Run all security tests (default)
    - auth: Authentication tests only
    - authz: Authorization tests only
    - token: Token validation tests only
    - integration: Integration tests only
    - penetration: Penetration tests only
    - performance: Performance security tests only
"""

import sys
import subprocess
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WebSocketSecurityTestRunner:
    """Test runner for WebSocket security validation"""

    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.results = {
            "execution_time": None,
            "summary": {},
            "test_results": {},
            "security_report": {},
            "recommendations": []
        }

    def run_test_category(self, category: str, verbose: bool = False) -> dict:
        """Run specific category of tests"""

        test_files = {
            "all": [
                "test_websocket_security.py",
                "test_token_validation.py",
                "test_websocket_integration.py",
                "test_penetration_scenarios.py"
            ],
            "auth": ["test_websocket_security.py::TestWebSocketAuthentication"],
            "authz": ["test_websocket_integration.py::TestWebSocketAuthorization"],
            "token": ["test_token_validation.py"],
            "integration": ["test_websocket_integration.py"],
            "penetration": ["test_penetration_scenarios.py"],
            "performance": ["test_penetration_scenarios.py::TestPerformanceAttacks"]
        }

        if category not in test_files:
            raise ValueError(f"Unknown test category: {category}")

        # Build pytest command
        cmd = ["python", "-m", "pytest"]

        if verbose:
            cmd.extend(["-v", "-s"])
        else:
            cmd.append("-v")

        # Add test files/patterns
        cmd.extend(test_files[category])

        # Add additional flags
        cmd.extend([
            "--tb=short",
            "--json-report",
            "--json-report-file=security_test_results.json"
        ])

        logger.info(f"Running {category} security tests...")
        logger.info(f"Command: {' '.join(cmd)}")

        # Execute tests
        start_time = datetime.now(timezone.utc)
        result = subprocess.run(
            cmd,
            cwd=self.test_dir,
            capture_output=True,
            text=True
        )
        end_time = datetime.now(timezone.utc)

        execution_time = (end_time - start_time).total_seconds()

        # Parse results
        test_results = {
            "category": category,
            "execution_time": execution_time,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat()
        }

        # Load JSON report if available
        json_report_file = self.test_dir / "security_test_results.json"
        if json_report_file.exists():
            try:
                with open(json_report_file, 'r') as f:
                    json_report = json.load(f)
                test_results["detailed_results"] = json_report
            except Exception as e:
                logger.warning(f"Could not load JSON report: {e}")

        return test_results

    def analyze_security_results(self, test_results: dict) -> dict:
        """Analyze test results for security implications"""

        security_analysis = {
            "overall_status": "UNKNOWN",
            "critical_issues": [],
            "vulnerabilities_found": [],
            "tests_passed": 0,
            "tests_failed": 0,
            "security_score": 0
        }

        # Parse detailed results if available
        if "detailed_results" in test_results:
            detailed = test_results["detailed_results"]

            if "summary" in detailed:
                summary = detailed["summary"]
                security_analysis["tests_passed"] = summary.get("passed", 0)
                security_analysis["tests_failed"] = summary.get("failed", 0)

                total_tests = security_analysis["tests_passed"] + security_analysis["tests_failed"]
                if total_tests > 0:
                    security_analysis["security_score"] = (security_analysis["tests_passed"] / total_tests) * 100

            # Analyze individual test results
            if "tests" in detailed:
                for test in detailed["tests"]:
                    if test.get("outcome") == "failed":
                        test_name = test.get("nodeid", "unknown")

                        # Identify critical security failures
                        if any(keyword in test_name.lower() for keyword in [
                            "attack", "bypass", "escalation", "hijacking", "injection"
                        ]):
                            security_analysis["critical_issues"].append({
                                "test": test_name,
                                "category": "Security Bypass",
                                "description": "Critical security test failed - vulnerability may exist"
                            })

                        # Identify specific vulnerabilities
                        if "expired_token" in test_name.lower():
                            security_analysis["vulnerabilities_found"].append({
                                "type": "Token Expiry Vulnerability",
                                "test": test_name,
                                "severity": "HIGH"
                            })
                        elif "unauthorized" in test_name.lower():
                            security_analysis["vulnerabilities_found"].append({
                                "type": "Authorization Bypass",
                                "test": test_name,
                                "severity": "CRITICAL"
                            })

        # Determine overall security status
        if security_analysis["security_score"] >= 95:
            security_analysis["overall_status"] = "SECURE"
        elif security_analysis["security_score"] >= 80:
            security_analysis["overall_status"] = "MOSTLY_SECURE"
        elif security_analysis["security_score"] >= 60:
            security_analysis["overall_status"] = "INSECURE"
        else:
            security_analysis["overall_status"] = "CRITICAL_VULNERABILITIES"

        return security_analysis

    def generate_security_recommendations(self, security_analysis: dict) -> list:
        """Generate security recommendations based on test results"""

        recommendations = []

        # Critical issues recommendations
        if security_analysis["critical_issues"]:
            recommendations.append({
                "priority": "IMMEDIATE",
                "category": "Critical Security",
                "title": "Address Critical Security Test Failures",
                "description": f"Found {len(security_analysis['critical_issues'])} critical security test failures",
                "actions": [
                    "Review failed penetration tests immediately",
                    "Implement missing security controls",
                    "Re-run tests to verify fixes"
                ]
            })

        # Vulnerability-specific recommendations
        for vuln in security_analysis["vulnerabilities_found"]:
            if vuln["type"] == "Token Expiry Vulnerability":
                recommendations.append({
                    "priority": "HIGH",
                    "category": "Authentication",
                    "title": "Implement Token Expiry Handling",
                    "description": "WebSocket connections not properly handling token expiry",
                    "actions": [
                        "Add periodic token validation to WebSocket connections",
                        "Implement automatic disconnection on token expiry",
                        "Add token refresh mechanism for long-lived connections"
                    ]
                })
            elif vuln["type"] == "Authorization Bypass":
                recommendations.append({
                    "priority": "CRITICAL",
                    "category": "Authorization",
                    "title": "Fix Authorization Controls",
                    "description": "Users receiving unauthorized data through WebSocket",
                    "actions": [
                        "Implement user-scoped message filtering",
                        "Add entity-level permission checks",
                        "Verify tenant isolation in multi-tenant environments"
                    ]
                })

        # General security recommendations
        if security_analysis["security_score"] < 100:
            recommendations.append({
                "priority": "MEDIUM",
                "category": "General Security",
                "title": "Improve Overall Security Posture",
                "description": f"Security score: {security_analysis['security_score']:.1f}%",
                "actions": [
                    "Review and fix all failed security tests",
                    "Implement comprehensive logging for security events",
                    "Add monitoring for suspicious WebSocket activity",
                    "Conduct regular security testing"
                ]
            })

        # Performance security recommendations
        recommendations.append({
            "priority": "MEDIUM",
            "category": "Performance Security",
            "title": "Implement Rate Limiting and DoS Protection",
            "description": "Protect against connection flooding and message spam",
            "actions": [
                "Implement connection rate limiting per IP/user",
                "Add message rate limiting for WebSocket connections",
                "Set maximum concurrent connections per user",
                "Monitor and alert on unusual connection patterns"
            ]
        })

        return recommendations

    def generate_html_report(self, results: dict) -> str:
        """Generate HTML security test report"""

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>WebSocket Security Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .status-secure {{ color: green; font-weight: bold; }}
        .status-insecure {{ color: red; font-weight: bold; }}
        .status-warning {{ color: orange; font-weight: bold; }}
        .section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #ccc; }}
        .critical {{ border-left-color: red; background-color: #ffe6e6; }}
        .high {{ border-left-color: orange; background-color: #fff4e6; }}
        .medium {{ border-left-color: blue; background-color: #e6f3ff; }}
        .recommendation {{ margin: 10px 0; padding: 10px; background-color: #f9f9f9; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .pass {{ color: green; }}
        .fail {{ color: red; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>WebSocket Security Test Report</h1>
        <p><strong>Generated:</strong> {results['execution_time']}</p>
        <p><strong>Overall Status:</strong>
            <span class="status-{results['security_report']['overall_status'].lower()}">
                {results['security_report']['overall_status']}
            </span>
        </p>
        <p><strong>Security Score:</strong> {results['security_report']['security_score']:.1f}%</p>
    </div>

    <div class="section">
        <h2>Executive Summary</h2>
        <ul>
            <li><strong>Tests Passed:</strong> {results['security_report']['tests_passed']}</li>
            <li><strong>Tests Failed:</strong> {results['security_report']['tests_failed']}</li>
            <li><strong>Critical Issues:</strong> {len(results['security_report']['critical_issues'])}</li>
            <li><strong>Vulnerabilities Found:</strong> {len(results['security_report']['vulnerabilities_found'])}</li>
        </ul>
    </div>
        """

        # Add critical issues if any
        if results['security_report']['critical_issues']:
            html += '<div class="section critical"><h2>🚨 Critical Security Issues</h2><ul>'
            for issue in results['security_report']['critical_issues']:
                html += f'<li><strong>{issue["category"]}:</strong> {issue["description"]}</li>'
            html += '</ul></div>'

        # Add vulnerabilities if any
        if results['security_report']['vulnerabilities_found']:
            html += '<div class="section high"><h2>🛡️ Vulnerabilities Found</h2><ul>'
            for vuln in results['security_report']['vulnerabilities_found']:
                html += f'<li><strong>{vuln["type"]}</strong> (Severity: {vuln["severity"]})</li>'
            html += '</ul></div>'

        # Add recommendations
        html += '<div class="section"><h2>📋 Security Recommendations</h2>'
        for rec in results['recommendations']:
            priority_class = rec['priority'].lower()
            html += f'''
            <div class="recommendation {priority_class}">
                <h3>{rec['title']} ({rec['priority']} Priority)</h3>
                <p>{rec['description']}</p>
                <ul>
            '''
            for action in rec['actions']:
                html += f'<li>{action}</li>'
            html += '</ul></div>'

        html += '</div></body></html>'
        return html

    def run_security_tests(self, category: str = "all", verbose: bool = False, generate_report: bool = False):
        """Run complete security test suite"""

        logger.info("🔒 Starting WebSocket Security Test Suite")
        logger.info(f"Category: {category}")

        start_time = datetime.now(timezone.utc)

        try:
            # Run tests
            test_results = self.run_test_category(category, verbose)

            # Analyze security implications
            security_analysis = self.analyze_security_results(test_results)

            # Generate recommendations
            recommendations = self.generate_security_recommendations(security_analysis)

            # Compile final results
            self.results = {
                "execution_time": datetime.now(timezone.utc).isoformat(),
                "summary": {
                    "category": category,
                    "total_execution_time": test_results["execution_time"],
                    "return_code": test_results["return_code"]
                },
                "test_results": test_results,
                "security_report": security_analysis,
                "recommendations": recommendations
            }

            # Print summary
            self.print_security_summary()

            # Generate detailed report if requested
            if generate_report:
                self.generate_reports()

        except Exception as e:
            logger.error(f"Security test execution failed: {e}")
            raise

    def print_security_summary(self):
        """Print security test summary to console"""

        print("\n" + "="*60)
        print("🔒 WEBSOCKET SECURITY TEST SUMMARY")
        print("="*60)

        status = self.results['security_report']['overall_status']
        score = self.results['security_report']['security_score']

        print(f"Overall Status: {status}")
        print(f"Security Score: {score:.1f}%")
        print(f"Tests Passed: {self.results['security_report']['tests_passed']}")
        print(f"Tests Failed: {self.results['security_report']['tests_failed']}")

        if self.results['security_report']['critical_issues']:
            print(f"\n🚨 CRITICAL ISSUES: {len(self.results['security_report']['critical_issues'])}")
            for issue in self.results['security_report']['critical_issues']:
                print(f"  - {issue['category']}: {issue['description']}")

        if self.results['security_report']['vulnerabilities_found']:
            print(f"\n🛡️ VULNERABILITIES: {len(self.results['security_report']['vulnerabilities_found'])}")
            for vuln in self.results['security_report']['vulnerabilities_found']:
                print(f"  - {vuln['type']} (Severity: {vuln['severity']})")

        print(f"\n📋 RECOMMENDATIONS: {len(self.results['recommendations'])}")
        for rec in self.results['recommendations'][:3]:  # Show top 3
            print(f"  - {rec['priority']}: {rec['title']}")

        print("\n" + "="*60)

    def generate_reports(self):
        """Generate detailed security reports"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON report
        json_file = self.test_dir / f"security_report_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"JSON report saved: {json_file}")

        # HTML report
        html_content = self.generate_html_report(self.results)
        html_file = self.test_dir / f"security_report_{timestamp}.html"
        with open(html_file, 'w') as f:
            f.write(html_content)
        logger.info(f"HTML report saved: {html_file}")


def main():
    """Main entry point"""

    parser = argparse.ArgumentParser(
        description="WebSocket Security Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Categories:
  all         Run all security tests (default)
  auth        Authentication tests only
  authz       Authorization tests only
  token       Token validation tests only
  integration Integration tests only
  penetration Penetration tests only
  performance Performance security tests only

Examples:
  python run_security_tests.py
  python run_security_tests.py --category penetration --verbose
  python run_security_tests.py --category all --report
        """
    )

    parser.add_argument(
        "--category",
        choices=["all", "auth", "authz", "token", "integration", "penetration", "performance"],
        default="all",
        help="Test category to run (default: all)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    parser.add_argument(
        "--report", "-r",
        action="store_true",
        help="Generate detailed HTML and JSON reports"
    )

    args = parser.parse_args()

    try:
        runner = WebSocketSecurityTestRunner()
        runner.run_security_tests(
            category=args.category,
            verbose=args.verbose,
            generate_report=args.report
        )

        # Exit with appropriate code
        return_code = runner.results['summary']['return_code']
        if return_code == 0:
            logger.info("✅ All security tests passed!")
        else:
            logger.warning("⚠️ Some security tests failed - review results")

        sys.exit(return_code)

    except Exception as e:
        logger.error(f"Security test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()