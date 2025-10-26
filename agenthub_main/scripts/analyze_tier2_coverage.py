#!/usr/bin/env python3
"""
Analyze coverage HTML report to find Tier 2 files (88-91% coverage).
Extracts files with their coverage percentages and missing line numbers.
"""

import re
import json
from pathlib import Path
from html.parser import HTMLParser

class CoverageHTMLParser(HTMLParser):
    """Parse coverage HTML to extract file coverage data."""

    def __init__(self):
        super().__init__()
        self.files = []
        self.current_file = None
        self.in_file_cell = False
        self.in_coverage_cell = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == 'tr' and attrs_dict.get('class') in ['file', 'region']:
            self.current_file = {}

        elif tag == 'td' and attrs_dict.get('class') == 'name left':
            self.in_file_cell = True

        elif tag == 'a' and self.in_file_cell:
            href = attrs_dict.get('href', '')
            if href:
                self.current_file['href'] = href

        elif tag == 'td' and attrs_dict.get('class') == 'right' and attrs_dict.get('data-ratio'):
            self.in_coverage_cell = True
            if self.current_file is not None:
                ratio = attrs_dict['data-ratio']
                if ratio:
                    parts = ratio.split()
                    if len(parts) == 2:
                        covered, total = map(int, parts)
                        if total > 0:
                            coverage = (covered / total) * 100
                            self.current_file['coverage'] = round(coverage, 2)
                            self.current_file['covered'] = covered
                            self.current_file['total'] = total

    def handle_data(self, data):
        if self.in_file_cell and self.current_file is not None and data.strip():
            if 'name' not in self.current_file:
                self.current_file['name'] = data.strip()

    def handle_endtag(self, tag):
        if tag == 'td':
            self.in_file_cell = False
            self.in_coverage_cell = False

        elif tag == 'tr' and self.current_file and 'coverage' in self.current_file:
            self.files.append(self.current_file)
            self.current_file = None

def parse_file_details(html_file_path):
    """Parse individual file HTML to get missing line numbers."""
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find all lines marked as 'mis' (missing) or 'par' (partial)
        # Pattern: <p class="mis"><span class="n"><a id="t123"
        missing_pattern = r'<p class="mis"><span class="n"><a id="t(\d+)"'
        partial_pattern = r'<p class="par[^"]*"><span class="n"><a id="t(\d+)"'

        missing_lines = [int(m) for m in re.findall(missing_pattern, content)]
        partial_lines = [int(m) for m in re.findall(partial_pattern, content)]

        return sorted(missing_lines), sorted(partial_lines)
    except Exception as e:
        print(f"Error parsing {html_file_path}: {e}")
        return [], []

def categorize_file(file_path):
    """Categorize file by its role in the system."""
    path_lower = file_path.lower()

    if '/domain/entities/' in path_lower:
        return 'Domain Entity', 'HIGH'
    elif '/domain/services/' in path_lower:
        return 'Domain Service', 'HIGH'
    elif '/application/facades/' in path_lower:
        return 'Application Facade', 'MEDIUM'
    elif '/application/services/' in path_lower:
        return 'Application Service', 'MEDIUM'
    elif '/application/use_cases/' in path_lower:
        return 'Use Case', 'HIGH'
    elif '/interface/mcp_controllers/' in path_lower or '/interface/controllers/' in path_lower:
        return 'MCP Controller', 'MEDIUM'
    elif '/infrastructure/' in path_lower:
        return 'Infrastructure', 'LOW'
    else:
        return 'Other', 'LOW'

def main():
    # Parse the main index.html
    htmlcov_dir = Path(__file__).parent.parent / 'htmlcov'
    index_file = htmlcov_dir / 'index.html'

    if not index_file.exists():
        print(f"Coverage report not found: {index_file}")
        print("Run: pytest --cov=src/fastmcp --cov-report=html")
        return

    parser = CoverageHTMLParser()
    with open(index_file, 'r', encoding='utf-8') as f:
        parser.feed(f.read())

    # Filter for Tier 2 files (88-91% coverage)
    tier2_files = []
    for file_data in parser.files:
        coverage = file_data.get('coverage', 0)
        name = file_data.get('name', '')

        # Filter: 88-91% range, exclude test files
        if 88 <= coverage <= 91 and 'src/fastmcp' in name and '/tests/' not in name:
            # Get missing lines from detail HTML
            href = file_data.get('href', '')
            if href:
                detail_file = htmlcov_dir / href
                missing_lines, partial_lines = parse_file_details(detail_file)

                # Categorize
                category, importance = categorize_file(name)

                # Calculate gaps
                total_gaps = len(missing_lines) + len(partial_lines)
                estimated_effort = max(3, total_gaps * 3)  # ~3 min per gap, min 3 min

                tier2_files.append({
                    'file': name,
                    'html_file': href,
                    'coverage': coverage,
                    'category': category,
                    'importance': importance,
                    'uncovered_lines': missing_lines[:20],  # Limit for readability
                    'partial_lines': partial_lines[:20],
                    'uncovered_count': len(missing_lines),
                    'partial_count': len(partial_lines),
                    'total_gaps': total_gaps,
                    'estimated_effort_minutes': estimated_effort
                })

    # Sort by importance and coverage (highest first)
    priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    tier2_files.sort(key=lambda x: (priority_order.get(x['importance'], 3), -x['coverage']))

    # Save results
    output_file = Path(__file__).parent / 'coverage_analysis_tier2.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(tier2_files, f, indent=2)

    print(f"\n=== Tier 2 Coverage Analysis (88-91%) ===")
    print(f"Total files found: {len(tier2_files)}")
    print(f"Output saved to: {output_file}")
    print(f"\nTop 10 files by priority:\n")

    for i, file_data in enumerate(tier2_files[:10], 1):
        print(f"{i}. {file_data['file']}")
        print(f"   Coverage: {file_data['coverage']}% | Category: {file_data['category']} | Priority: {file_data['importance']}")
        print(f"   Gaps: {file_data['total_gaps']} ({file_data['uncovered_count']} uncovered, {file_data['partial_count']} partial)")
        print(f"   Effort: ~{file_data['estimated_effort_minutes']} minutes")
        if file_data['uncovered_lines']:
            print(f"   Missing lines: {file_data['uncovered_lines'][:10]}")
        print()

if __name__ == '__main__':
    main()
