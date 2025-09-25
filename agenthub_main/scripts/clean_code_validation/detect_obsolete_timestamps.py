#!/usr/bin/env python3
"""Obsolete Timestamp Detection Script

This script automatically detects manual timestamp handling patterns that violate
the clean BaseTimestampEntity architecture. It helps enforce the single source
of truth principle for timestamp management.

Key Features:
- Detects manual updated_at assignments
- Finds direct datetime.now() calls in entities
- Identifies timezone-related manual handling
- Reports violations with file locations
- Suggests clean alternatives

Usage:
    python detect_obsolete_timestamps.py
    python detect_obsolete_timestamps.py --fix-suggestions
    python detect_obsolete_timestamps.py --strict
"""

import os
import re
import ast
import sys
from typing import List, Dict, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class ViolationReport:
    """Represents a timestamp handling violation."""
    file_path: str
    line_number: int
    line_content: str
    violation_type: str
    severity: str  # 'error', 'warning', 'info'
    suggestion: str
    context: str = ""


class ObsoleteTimestampDetector:
    """Detects obsolete timestamp handling patterns in the codebase."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.violations: List[ViolationReport] = []

        # Patterns that indicate manual timestamp handling (VIOLATIONS)
        self.violation_patterns = [
            # Direct updated_at assignments
            (r'self\.updated_at\s*=\s*datetime\.now', 'manual_updated_at_assignment', 'error',
             'Use entity.touch() instead of manual updated_at assignment'),

            # Direct created_at assignments (except in __init__)
            (r'self\.created_at\s*=\s*datetime\.now', 'manual_created_at_assignment', 'error',
             'Remove manual created_at assignment - BaseTimestampEntity handles this'),

            # Manual timezone handling
            (r'\.replace\(tzinfo=timezone\.utc\)', 'manual_timezone_handling', 'warning',
             'BaseTimestampEntity handles UTC timezone automatically'),

            # Direct datetime.now() in entity methods
            (r'datetime\.now\(timezone\.utc\)', 'manual_datetime_now', 'warning',
             'Use entity.touch() or repository methods instead'),

            # Context timestamp validation (should be in service layer)
            (r'context_updated_at.*<=.*updated_at', 'context_timestamp_validation', 'error',
             'Move timestamp validation to application service layer'),

            # Manual timestamp comparisons in entities
            (r'self\.updated_at\s*[<>=].*datetime', 'manual_timestamp_comparison', 'warning',
             'Use BaseTimestampEntity comparison methods'),

            # Hardcoded timestamp strings
            (r'"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"', 'hardcoded_timestamp', 'info',
             'Use proper datetime objects instead of hardcoded strings'),

            # Database trigger usage
            (r'ON\s+UPDATE\s+CURRENT_TIMESTAMP', 'database_trigger_usage', 'error',
             'Remove database triggers; manage timestamps in the application layer'),
            (r'DEFAULT\s+CURRENT_TIMESTAMP', 'database_default_timestamp', 'warning',
             'Use BaseTimestampEntity for default timestamps instead of database defaults'),

            # Legacy/compatibility flags
            (r'legacy.*timestamp', 'legacy_timestamp_code', 'warning',
             'Remove legacy timestamp compatibility code'),
            (r'backward.*compat', 'legacy_timestamp_code', 'warning',
             'Remove backward compatibility timestamp code'),

            # Attribute manipulation fallbacks
            (r'setattr\(.*updated_at', 'manual_updated_at_assignment', 'error',
             'Use entity.touch() instead of setattr for timestamps'),
        ]

        # File patterns to scan
        self.scan_patterns = [
            "**/*.py",  # All Python files
        ]

        # Files to exclude from scanning
        self.exclude_patterns = [
            "**/test_*.py",
            "**/tests/**",
            "**/migrations/**",
            "**/venv/**",
            "**/__pycache__/**",
            "**/build/**",
            "**/dist/**",
        ]

    def scan_codebase(self) -> List[ViolationReport]:
        """Scan the entire codebase for timestamp violations.

        Returns:
            List[ViolationReport]: All detected violations
        """
        print(f"🔍 Scanning codebase for obsolete timestamp patterns...")
        print(f"📁 Project root: {self.project_root}")

        files_scanned = 0

        for pattern in self.scan_patterns:
            for file_path in self.project_root.rglob(pattern):
                if self._should_exclude_file(file_path):
                    continue

                try:
                    self._scan_file(file_path)
                    files_scanned += 1
                except Exception as e:
                    print(f"⚠️ Error scanning {file_path}: {e}")

        print(f"📊 Scanned {files_scanned} files")
        print(f"🚨 Found {len(self.violations)} violations")

        return self.violations

    def _should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from scanning."""
        file_str = str(file_path)

        for exclude_pattern in self.exclude_patterns:
            if file_path.match(exclude_pattern) or exclude_pattern in file_str:
                return True

        return False

    def _scan_file(self, file_path: Path) -> None:
        """Scan a single file for timestamp violations."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                self._check_line_for_violations(file_path, line_num, line.strip())

        except UnicodeDecodeError:
            # Skip binary files
            pass
        except Exception as e:
            print(f"⚠️ Error reading {file_path}: {e}")

    def _check_line_for_violations(self, file_path: Path, line_num: int, line: str) -> None:
        """Check a single line for timestamp violations."""
        for pattern, violation_type, severity, suggestion in self.violation_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                # Get some context around the violation
                context = self._get_line_context(file_path, line_num)

                violation = ViolationReport(
                    file_path=str(file_path.relative_to(self.project_root)),
                    line_number=line_num,
                    line_content=line,
                    violation_type=violation_type,
                    severity=severity,
                    suggestion=suggestion,
                    context=context
                )

                self.violations.append(violation)

    def _get_line_context(self, file_path: Path, line_num: int, context_lines: int = 2) -> str:
        """Get context lines around a violation."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()

            start = max(0, line_num - context_lines - 1)
            end = min(len(all_lines), line_num + context_lines)

            context_lines_list = all_lines[start:end]
            context = "".join(context_lines_list).strip()

            return context
        except Exception:
            return ""

    def generate_report(self, output_file: str = None) -> str:
        """Generate a detailed violation report.

        Args:
            output_file: Optional file to write report to

        Returns:
            str: Report content
        """
        # Group violations by type and severity
        violations_by_type = defaultdict(list)
        violations_by_severity = defaultdict(list)

        for violation in self.violations:
            violations_by_type[violation.violation_type].append(violation)
            violations_by_severity[violation.severity].append(violation)

        # Build report
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("🚨 OBSOLETE TIMESTAMP HANDLING DETECTION REPORT")
        report_lines.append("=" * 80)
        report_lines.append("")

        # Summary
        report_lines.append("📊 SUMMARY")
        report_lines.append("-" * 40)
        report_lines.append(f"Total Violations: {len(self.violations)}")
        report_lines.append(f"  • Errors:   {len(violations_by_severity['error'])}")
        report_lines.append(f"  • Warnings: {len(violations_by_severity['warning'])}")
        report_lines.append(f"  • Info:     {len(violations_by_severity['info'])}")
        report_lines.append("")

        # Violations by type
        report_lines.append("🔍 VIOLATIONS BY TYPE")
        report_lines.append("-" * 40)
        for violation_type, violations in sorted(violations_by_type.items()):
            report_lines.append(f"{violation_type}: {len(violations)} instances")
        report_lines.append("")

        # Detailed violations
        report_lines.append("📋 DETAILED VIOLATIONS")
        report_lines.append("-" * 40)

        # Sort by severity: error -> warning -> info
        severity_order = ['error', 'warning', 'info']
        sorted_violations = sorted(
            self.violations,
            key=lambda v: (severity_order.index(v.severity), v.file_path, v.line_number)
        )

        for violation in sorted_violations:
            severity_icon = {'error': '❌', 'warning': '⚠️', 'info': 'ℹ️'}[violation.severity]

            report_lines.append(f"{severity_icon} {violation.severity.upper()}: {violation.violation_type}")
            report_lines.append(f"   📁 File: {violation.file_path}:{violation.line_number}")
            report_lines.append(f"   📝 Line: {violation.line_content}")
            report_lines.append(f"   💡 Fix: {violation.suggestion}")

            if violation.context and len(violation.context) < 200:
                report_lines.append(f"   🔍 Context:")
                for ctx_line in violation.context.split('\n')[:3]:
                    if ctx_line.strip():
                        report_lines.append(f"      {ctx_line.strip()}")

            report_lines.append("")

        # Recommendations
        report_lines.append("🎯 CLEAN CODE RECOMMENDATIONS")
        report_lines.append("-" * 40)
        report_lines.append("1. Replace manual timestamp assignments with entity.touch()")
        report_lines.append("2. Use BaseTimestampRepository for database operations")
        report_lines.append("3. Move timestamp validation to application service layer")
        report_lines.append("4. Inherit all entities from BaseTimestampEntity")
        report_lines.append("5. Remove all manual datetime.now() calls in entities")
        report_lines.append("")

        # Migration guide
        report_lines.append("🔧 MIGRATION PATTERNS")
        report_lines.append("-" * 40)
        report_lines.append("OLD (Manual):           NEW (Clean Architecture):")
        report_lines.append("self.updated_at = now   entity.touch('reason')")
        report_lines.append("datetime.now()          Use repository methods")
        report_lines.append("Manual timezone         BaseTimestampEntity handles it")
        report_lines.append("Direct comparisons      entity.is_newer_than(other)")
        report_lines.append("")

        report_content = "\n".join(report_lines)

        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                print(f"📄 Report written to: {output_file}")
            except Exception as e:
                print(f"⚠️ Failed to write report to {output_file}: {e}")

        return report_content

    def get_violation_summary(self) -> Dict[str, Any]:
        """Get a summary of violations for programmatic use.

        Returns:
            Dict[str, Any]: Summary data
        """
        violations_by_severity = defaultdict(int)
        violations_by_type = defaultdict(int)
        files_with_violations = set()

        for violation in self.violations:
            violations_by_severity[violation.severity] += 1
            violations_by_type[violation.violation_type] += 1
            files_with_violations.add(violation.file_path)

        return {
            "total_violations": len(self.violations),
            "violations_by_severity": dict(violations_by_severity),
            "violations_by_type": dict(violations_by_type),
            "files_with_violations": len(files_with_violations),
            "affected_files": sorted(files_with_violations)
        }


def main():
    """Main script execution."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Detect obsolete timestamp handling patterns"
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root directory to scan"
    )
    parser.add_argument(
        "--output",
        help="Output file for report"
    )
    parser.add_argument(
        "--fix-suggestions",
        action="store_true",
        help="Show detailed fix suggestions"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors"
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Show only summary, not detailed violations"
    )

    args = parser.parse_args()

    # Initialize detector
    detector = ObsoleteTimestampDetector(args.project_root)

    # Scan codebase
    violations = detector.scan_codebase()

    if not violations:
        print("✅ No obsolete timestamp patterns found! Clean codebase.")
        return 0

    # Generate and display report
    if args.summary_only:
        summary = detector.get_violation_summary()
        print(f"📊 Summary: {summary['total_violations']} violations in {summary['files_with_violations']} files")
        for severity, count in summary['violations_by_severity'].items():
            severity_icon = {'error': '❌', 'warning': '⚠️', 'info': 'ℹ️'}[severity]
            print(f"  {severity_icon} {severity}: {count}")
    else:
        report = detector.generate_report(args.output)
        if not args.output:
            print(report)

    # Return appropriate exit code
    summary = detector.get_violation_summary()
    error_count = summary['violations_by_severity'].get('error', 0)
    warning_count = summary['violations_by_severity'].get('warning', 0)

    if error_count > 0:
        print(f"❌ Found {error_count} error-level violations")
        return 1
    elif args.strict and warning_count > 0:
        print(f"⚠️ Found {warning_count} warning-level violations (strict mode)")
        return 1
    else:
        print(f"✅ Scan complete. Found {len(violations)} violations.")
        return 0


if __name__ == "__main__":
    exit(main())
