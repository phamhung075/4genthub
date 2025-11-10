#!/usr/bin/env python3
"""Analyze coverage HTML reports to extract uncovered lines for easy-win files."""

import json
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Tuple


class CoverageHTMLParser(HTMLParser):
    """Parse coverage HTML to extract uncovered line numbers."""

    def __init__(self):
        super().__init__()
        self.uncovered_lines = []
        self.partial_lines = []
        self.current_line = None
        self.in_paragraph = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        # Check for paragraph with line number
        if tag == 'p':
            class_attr = attrs_dict.get('class', '')
            if 'mis' in class_attr:
                self.in_paragraph = True
                self.is_missing = True
            elif 'par' in class_attr:
                self.in_paragraph = True
                self.is_partial = True
            else:
                self.in_paragraph = False
                self.is_missing = False
                self.is_partial = False

        # Get line number from anchor
        if tag == 'a' and self.in_paragraph:
            line_id = attrs_dict.get('id', '')
            if line_id.startswith('t'):
                try:
                    line_num = int(line_id[1:])
                    if self.is_missing:
                        self.uncovered_lines.append(line_num)
                    elif self.is_partial:
                        self.partial_lines.append(line_num)
                except ValueError:
                    pass

def find_html_file(source_file: str, htmlcov_dir: Path) -> Path:
    """Find the HTML coverage file for a source file."""
    # Try different patterns
    file_basename = Path(source_file).stem

    # Search for HTML files containing the basename
    for html_file in htmlcov_dir.glob(f'*_{file_basename}_py.html'):
        return html_file

    return None

def analyze_file_coverage(html_file: Path) -> tuple[list[int], list[int]]:
    """Extract uncovered and partial lines from HTML coverage file."""
    parser = CoverageHTMLParser()

    with open(html_file, encoding='utf-8') as f:
        content = f.read()

    parser.feed(content)

    return sorted(set(parser.uncovered_lines)), sorted(set(parser.partial_lines))

def categorize_file(filepath: str) -> tuple[str, str]:
    """Categorize file by type and importance."""
    if '/domain/services/' in filepath:
        return ('Domain Service', 'HIGH')
    elif '/domain/entities/' in filepath:
        return ('Domain Entity', 'HIGH')
    elif '/application/use_cases/' in filepath:
        return ('Use Case', 'HIGH')
    elif '/application/services/' in filepath:
        return ('Application Service', 'MEDIUM')
    elif '/application/facades/' in filepath:
        return ('Application Facade', 'MEDIUM')
    elif '/infrastructure/' in filepath:
        return ('Infrastructure', 'LOW')
    elif '/interface/' in filepath:
        return ('Interface/Controller', 'MEDIUM')
    else:
        return ('Other', 'LOW')

def estimate_effort(uncovered_count: int, partial_count: int, file_category: str) -> int:
    """Estimate effort in minutes to cover uncovered lines."""
    base_effort = uncovered_count * 3 + partial_count * 2  # 3 min per missing, 2 min per partial

    # Adjust by file category complexity
    if file_category == 'Domain Service':
        multiplier = 1.5
    elif file_category == 'Infrastructure':
        multiplier = 2.0
    else:
        multiplier = 1.0

    return int(base_effort * multiplier)

def main():
    htmlcov_dir = Path('/home/daihungpham/__projects__/4genthub/agenthub_main/htmlcov')

    # Top priority files (91-93% coverage)
    tier1_files = [
        "src/fastmcp/task_management/domain/services/intelligence/progressive_expander.py",
        "src/fastmcp/task_management/application/services/ai_integration_service.py",
        "src/fastmcp/task_management/application/services/progressive_enforcement_service.py",
        "src/fastmcp/task_management/application/facades/project_application_facade.py",
        "src/fastmcp/task_management/domain/services/task_state_transition_service.py",
        "src/fastmcp/task_management/application/use_cases/create_task.py",
        "src/fastmcp/task_management/domain/services/dependency_validation_service.py",
        "src/fastmcp/task_management/infrastructure/services/template_engine_service.py",
        "src/fastmcp/task_management/domain/services/task_completion_service.py",
        "src/fastmcp/auth/middleware/jwt_auth_middleware.py",
        "src/fastmcp/task_management/application/use_cases/batch_context_operations.py",
        "src/fastmcp/task_management/application/services/project_application_service.py",
        "src/fastmcp/task_management/domain/entities/agent.py",
        "src/fastmcp/auth/keycloak_integration.py",
        "src/fastmcp/task_management/application/services/context_template_manager.py",
    ]

    results = []

    for source_file in tier1_files:
        html_file = find_html_file(source_file, htmlcov_dir)

        if not html_file:
            print(f"⚠️  HTML not found: {source_file}")
            continue

        uncovered, partial = analyze_file_coverage(html_file)
        category, importance = categorize_file(source_file)
        effort_min = estimate_effort(len(uncovered), len(partial), category)

        result = {
            'file': source_file,
            'html_file': html_file.name,
            'category': category,
            'importance': importance,
            'uncovered_lines': uncovered,
            'partial_lines': partial,
            'uncovered_count': len(uncovered),
            'partial_count': len(partial),
            'total_gaps': len(uncovered) + len(partial),
            'estimated_effort_minutes': effort_min
        }

        results.append(result)

    # Sort by easiest wins (fewest gaps, highest importance)
    results.sort(key=lambda x: (x['total_gaps'], -ord(x['importance'][0])))

    # Print summary
    print("=" * 100)
    print("TIER 1 COVERAGE ANALYSIS - Easy Wins (91-93% Coverage)")
    print("=" * 100)
    print()

    for i, result in enumerate(results, 1):
        print(f"{i}. {Path(result['file']).name}")
        print(f"   Category: {result['category']} | Priority: {result['importance']}")
        print(f"   Gaps: {result['uncovered_count']} missing, {result['partial_count']} partial")
        if result['uncovered_lines']:
            print(f"   Missing lines: {', '.join(map(str, result['uncovered_lines'][:20]))}")
        if result['partial_lines']:
            print(f"   Partial lines: {', '.join(map(str, result['partial_lines'][:20]))}")
        print(f"   Estimated effort: {result['estimated_effort_minutes']} minutes")
        print()

    # Summary statistics
    total_files = len(results)
    total_gaps = sum(r['total_gaps'] for r in results)
    total_effort = sum(r['estimated_effort_minutes'] for r in results)

    print("=" * 100)
    print(f"SUMMARY: {total_files} files analyzed, {total_gaps} total gaps, ~{total_effort} minutes ({total_effort/60:.1f} hours)")
    print("=" * 100)

    # Save detailed JSON
    output_file = Path('/home/daihungpham/__projects__/4genthub/agenthub_main/scripts/coverage_analysis_tier1.json')
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nDetailed analysis saved to: {output_file}")

if __name__ == '__main__':
    main()
