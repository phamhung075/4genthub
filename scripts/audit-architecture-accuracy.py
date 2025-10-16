#!/usr/bin/env python3
"""
Architecture Accuracy Audit Script

Scans all documentation in ai_docs/ for:
1. Outdated architecture patterns (legacy pre-DDD, old Python versions, static tool configs)
2. Missing coverage for recent changes (Phase 8 DDD, Dynamic Tool Enforcement v2.0)
3. Obsolete feature references
4. Architecture gaps

Generates comprehensive architecture gap report.

Output: ai_docs/reports-status/architecture-accuracy-audit-YYYYMMDD.md
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import hashlib


class ArchitectureAudit:
    """Audit documentation for architecture accuracy."""

    def __init__(self, docs_root: Path):
        self.docs_root = docs_root
        self.files_scanned = 0
        self.results = {
            'outdated_patterns': defaultdict(list),
            'missing_coverage': defaultdict(list),
            'version_issues': defaultdict(list),
            'architecture_gaps': defaultdict(list),
            'files_scanned': 0,
            'total_issues': 0
        }

        # Define outdated patterns to detect
        self.outdated_patterns = {
            'legacy_repository': [
                r'legacy.*repository',
                r'old.*repository.*pattern',
                r'pre-ddd.*repository',
                r'repository.*before.*phase\s*8'
            ],
            'old_python': [
                r'python\s+3\.1[0-3]',
                r'python\s+3\.[0-9](?!\d)',
                r'py3\.1[0-2]',
                r'requires.*python.*3\.1[0-2]'
            ],
            'yaml_tool_config': [
                r'yaml.*tool.*config',
                r'static.*tool.*permission',
                r'\.yml.*agent.*tools',
                r'hardcoded.*tool.*list',
                r'tools\.yaml'
            ],
            'old_context': [
                r'3-tier.*context',
                r'global.*project.*task(?!.*branch)',
                r'non.*user.*scoped.*global',
                r'shared.*global.*context'
            ],
            'removed_feature_flags': [
                r'feature.*flag.*enable',
                r'USE_OLD.*FLAG',
                r'ENABLE_LEGACY',
                r'deprecated.*flag'
            ]
        }

        # Define required modern architecture coverage
        self.required_coverage = {
            'python_314': ['python 3.14', 'python3.14', 'py3.14'],
            'ddd_phase8': ['phase 8', 'ddd complete', '100% ddd', 'ddd compliance'],
            'dynamic_tools': ['dynamic tool enforcement', 'v2.0', 'call_agent', 'tools array'],
            '4tier_context': ['4-tier', 'global → project → branch → task', 'user-scoped global'],
            'event_system': ['eventqueue', 'eventbus', 'eventworker', 'event system'],
            'keycloak_auth': ['keycloak', 'source of truth', 'jwt tokens'],
            'react19_vite7': ['react 19', 'vite 7', 'react 19.x'],
            '32_agents': ['32 agents', '32+ agents', 'specialized agents']
        }

        # Architecture topics that should have coverage
        self.architecture_topics = {
            'ddd_layers': ['domain layer', 'application layer', 'infrastructure layer', 'interface layer'],
            'context_hierarchy': ['global', 'project', 'branch', 'task'],
            'agent_categories': ['development', 'testing', 'design', 'planning', 'security', 'operations'],
            'mcp_tools': ['manage_task', 'manage_subtask', 'manage_context', 'manage_project']
        }

    def scan_all_docs(self) -> None:
        """Scan all markdown files in ai_docs."""
        print("Scanning documentation files...")

        for md_file in self.docs_root.rglob('*.md'):
            # Skip obsolete docs
            if '_obsolete_docs' in str(md_file):
                continue

            self.files_scanned += 1
            self.analyze_file(md_file)

        self.results['files_scanned'] = self.files_scanned

    def analyze_file(self, file_path: Path) -> None:
        """Analyze a single file for architecture issues."""
        try:
            content = file_path.read_text(encoding='utf-8')
            relative_path = file_path.relative_to(self.docs_root)

            # Check for outdated patterns
            self.check_outdated_patterns(content, relative_path)

            # Check for missing required coverage
            self.check_missing_coverage(content, relative_path)

            # Check architecture topics
            self.check_architecture_topics(content, relative_path)

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")

    def check_outdated_patterns(self, content: str, file_path: Path) -> None:
        """Check for outdated architecture patterns."""
        content_lower = content.lower()

        for pattern_type, patterns in self.outdated_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, content_lower, re.IGNORECASE)
                for match in matches:
                    # Get context (50 chars before and after)
                    start = max(0, match.start() - 50)
                    end = min(len(content), match.end() + 50)
                    context = content[start:end].replace('\n', ' ')

                    self.results['outdated_patterns'][pattern_type].append({
                        'file': str(file_path),
                        'pattern': match.group(),
                        'context': context.strip()
                    })
                    self.results['total_issues'] += 1

    def check_missing_coverage(self, content: str, file_path: Path) -> None:
        """Check if file mentions architecture but lacks modern coverage."""
        content_lower = content.lower()

        # Check if file discusses architecture topics
        architecture_indicators = [
            'architecture', 'system design', 'technology stack',
            'backend', 'frontend', 'database', 'infrastructure'
        ]

        has_architecture_content = any(
            indicator in content_lower for indicator in architecture_indicators
        )

        if has_architecture_content:
            # Check for missing modern architecture coverage
            for topic, keywords in self.required_coverage.items():
                has_coverage = any(
                    keyword.lower() in content_lower for keyword in keywords
                )

                if not has_coverage:
                    self.results['missing_coverage'][topic].append({
                        'file': str(file_path),
                        'missing_topic': topic,
                        'should_include': keywords
                    })
                    self.results['total_issues'] += 1

    def check_architecture_topics(self, content: str, file_path: Path) -> None:
        """Check for complete coverage of architecture topics."""
        content_lower = content.lower()

        for topic, required_terms in self.architecture_topics.items():
            # If file mentions the topic, check if it has all required terms
            topic_name = topic.replace('_', ' ')
            if topic_name in content_lower:
                missing_terms = [
                    term for term in required_terms
                    if term not in content_lower
                ]

                if missing_terms:
                    self.results['architecture_gaps'][topic].append({
                        'file': str(file_path),
                        'topic': topic,
                        'missing_terms': missing_terms,
                        'complete_coverage': required_terms
                    })

    def generate_report(self, output_path: Path) -> None:
        """Generate comprehensive architecture accuracy report."""
        report = self.build_report_content()
        output_path.write_text(report, encoding='utf-8')
        print(f"\nReport generated: {output_path}")

    def build_report_content(self) -> str:
        """Build the markdown report content."""
        date_str = datetime.now().strftime('%Y-%m-%d')

        report = f"""# Architecture Accuracy Audit Report

**Generated**: {date_str}
**Files Scanned**: {self.results['files_scanned']}
**Total Issues Found**: {self.results['total_issues']}

---

## Executive Summary

This report identifies documentation that contains outdated architecture references or lacks coverage of recent architectural changes.

### Issue Categories
- **Outdated Patterns**: {sum(len(v) for v in self.results['outdated_patterns'].values())} instances
- **Missing Coverage**: {sum(len(v) for v in self.results['missing_coverage'].values())} files
- **Architecture Gaps**: {sum(len(v) for v in self.results['architecture_gaps'].values())} incomplete topics

---

## 1. Outdated Architecture Patterns

Files containing references to legacy or deprecated patterns that should be updated.

"""

        # Outdated patterns section
        if self.results['outdated_patterns']:
            for pattern_type, issues in self.results['outdated_patterns'].items():
                if issues:
                    report += f"\n### {pattern_type.replace('_', ' ').title()} ({len(issues)} instances)\n\n"

                    # Group by file
                    by_file = defaultdict(list)
                    for issue in issues:
                        by_file[issue['file']].append(issue)

                    for file_path, file_issues in sorted(by_file.items()):
                        report += f"#### `{file_path}`\n\n"
                        for issue in file_issues:
                            report += f"- **Pattern**: `{issue['pattern']}`\n"
                            report += f"  - Context: `{issue['context'][:100]}...`\n\n"
        else:
            report += "No outdated patterns found.\n\n"

        report += "\n---\n\n## 2. Missing Modern Architecture Coverage\n\n"
        report += "Files discussing architecture topics but lacking coverage of recent changes.\n\n"

        if self.results['missing_coverage']:
            for topic, files in self.results['missing_coverage'].items():
                if files:
                    report += f"\n### {topic.replace('_', ' ').title()} ({len(files)} files)\n\n"
                    report += f"**Should include keywords**: {', '.join(files[0]['should_include'])}\n\n"

                    for item in files:
                        report += f"- `{item['file']}`\n"

                    report += "\n"
        else:
            report += "All files have appropriate modern architecture coverage.\n\n"

        report += "\n---\n\n## 3. Architecture Topic Gaps\n\n"
        report += "Files discussing specific topics but missing complete coverage.\n\n"

        if self.results['architecture_gaps']:
            for topic, gaps in self.results['architecture_gaps'].items():
                if gaps:
                    report += f"\n### {topic.replace('_', ' ').title()} ({len(gaps)} files)\n\n"

                    for gap in gaps:
                        report += f"#### `{gap['file']}`\n\n"
                        report += f"- **Missing terms**: {', '.join(gap['missing_terms'])}\n"
                        report += f"- **Complete coverage should include**: {', '.join(gap['complete_coverage'])}\n\n"
        else:
            report += "All architecture topics have complete coverage.\n\n"

        report += self.build_recommendations_section()

        return report

    def build_recommendations_section(self) -> str:
        """Build recommendations section."""
        return """
---

## 4. Recommendations

### High Priority Updates

1. **Remove Legacy Patterns**
   - Update all references to pre-DDD repository patterns
   - Replace mentions of old Python versions with Python 3.14.0
   - Remove references to static YAML tool configurations

2. **Add Modern Architecture Coverage**
   - Document Dynamic Tool Enforcement v2.0 in relevant files
   - Include Phase 8 DDD completion status
   - Add 4-tier context hierarchy details where missing
   - Document Event System architecture (EventQueue, EventBus, EventWorker)

3. **Complete Architecture Topics**
   - Ensure DDD layer documentation includes all four layers
   - Verify context hierarchy docs cover all four tiers
   - Check agent documentation includes all categories
   - Validate MCP tool documentation is comprehensive

### Implementation Strategy

1. **Immediate Actions** (Files with outdated patterns)
   - Review and update files flagged with legacy patterns
   - Replace outdated version references
   - Update architecture diagrams and examples

2. **Content Enhancement** (Files with missing coverage)
   - Add sections for modern architecture features
   - Include current system specifications
   - Update examples to reflect current architecture

3. **Completeness Check** (Files with topic gaps)
   - Review architecture topic coverage
   - Add missing terms and concepts
   - Ensure consistency across related documents

### Validation Checklist

After updates, verify:
- [ ] No references to Python versions < 3.14
- [ ] All DDD documentation reflects Phase 8 completion
- [ ] Tool enforcement documented as dynamic (v2.0), not static
- [ ] Context hierarchy consistently shows 4 tiers
- [ ] Event system properly documented
- [ ] All 32+ specialized agents documented
- [ ] Keycloak referenced as authentication source of truth
- [ ] React 19.x and Vite 7.x mentioned for frontend

---

## Next Steps

1. Review this report with the development team
2. Prioritize files with multiple issues
3. Create update tasks for high-impact documentation
4. Coordinate with deep-research-agent on duplicate content analysis
5. Plan merge and update strategy based on both reports

---

*Report generated by audit-architecture-accuracy.py*
*Part of Documentation Audit: Phase 2 - Architecture Accuracy*
"""

    def print_summary(self) -> None:
        """Print summary to console."""
        print("\n" + "="*70)
        print("ARCHITECTURE ACCURACY AUDIT SUMMARY")
        print("="*70)
        print(f"Files scanned: {self.results['files_scanned']}")
        print(f"Total issues found: {self.results['total_issues']}")
        print("\nIssue breakdown:")
        print(f"  - Outdated patterns: {sum(len(v) for v in self.results['outdated_patterns'].values())}")
        print(f"  - Missing coverage: {sum(len(v) for v in self.results['missing_coverage'].values())}")
        print(f"  - Architecture gaps: {sum(len(v) for v in self.results['architecture_gaps'].values())}")
        print("\nMost common issues:")

        # Show top 3 issue types
        all_issues = []
        for pattern_type, issues in self.results['outdated_patterns'].items():
            all_issues.append((pattern_type, len(issues)))
        for topic, files in self.results['missing_coverage'].items():
            all_issues.append((f"missing_{topic}", len(files)))

        all_issues.sort(key=lambda x: x[1], reverse=True)

        for issue_type, count in all_issues[:3]:
            print(f"  {issue_type.replace('_', ' ').title()}: {count}")

        print("="*70)


def main():
    """Main execution."""
    # Setup paths
    project_root = Path(__file__).parent.parent
    docs_root = project_root / 'ai_docs'
    reports_dir = docs_root / 'reports-status'
    reports_dir.mkdir(exist_ok=True)

    date_str = datetime.now().strftime('%Y%m%d')
    output_file = reports_dir / f'architecture-accuracy-audit-{date_str}.md'

    print("="*70)
    print("ARCHITECTURE ACCURACY AUDIT")
    print("="*70)
    print(f"Documentation root: {docs_root}")
    print(f"Output file: {output_file}")
    print()

    # Run audit
    auditor = ArchitectureAudit(docs_root)
    auditor.scan_all_docs()

    # Generate report
    auditor.generate_report(output_file)

    # Print summary
    auditor.print_summary()

    print(f"\n✅ Audit complete! Report saved to:\n   {output_file}")
    print("\n📋 Next steps:")
    print("   1. Review the generated report")
    print("   2. Coordinate with deep-research-agent on duplicate analysis")
    print("   3. Plan documentation merge and update strategy")


if __name__ == '__main__':
    main()
