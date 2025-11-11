#!/usr/bin/env python3
"""
Coverage Analysis Script for Strategic Planning

Usage:
    python3 scripts/analyze_coverage_json.py --range 0-30 --top 50
    python3 scripts/analyze_coverage_json.py --range 30-50 --top 20
    python3 scripts/analyze_coverage_json.py --file session_store.py
"""

import argparse
import json


def load_coverage_data(coverage_file="coverage_final.json"):
    try:
        with open(coverage_file) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Coverage file not found: {coverage_file}")
        print("Run: pytest --cov=src --cov-report=json:coverage_final.json")
        exit(1)


def analyze_by_range(data, coverage_range, top_n=50):
    range_map = {
        "0-30": (0, 30),
        "30-50": (30, 50),
        "50-70": (50, 70),
        "70-85": (70, 85),
        "85-95": (85, 95),
        "95-100": (95, 100),
    }

    if coverage_range not in range_map:
        print(f"❌ Invalid range. Use: {', '.join(range_map.keys())}")
        exit(1)

    min_cov, max_cov = range_map[coverage_range]
    files_in_range = []

    for filepath, filedata in data["files"].items():
        if "src/fastmcp" not in filepath or "__pycache__" in filepath:
            continue

        coverage = filedata["summary"]["percent_covered"]
        statements = filedata["summary"]["num_statements"]
        missing = filedata["summary"]["missing_lines"]

        if min_cov <= coverage < max_cov:
            filename = filepath.split("/")[-1]
            files_in_range.append(
                {
                    "file": filename,
                    "path": filepath,
                    "coverage": coverage,
                    "statements": statements,
                    "missing": missing,
                }
            )

    files_in_range.sort(key=lambda x: x["missing"], reverse=True)
    top_files = files_in_range[:top_n]

    print("\n" + "=" * 80)
    print(f"📊 COVERAGE ANALYSIS: {coverage_range}% Range")
    print("=" * 80)
    print(f"Total Files in Range: {len(files_in_range)}")
    print(f"Showing Top {len(top_files)} by Missing Lines")
    print("=" * 80)

    total_statements = sum(f["statements"] for f in top_files)
    total_missing = sum(f["missing"] for f in top_files)

    print("\n📈 Summary Statistics:")
    print(f"   Total Statements: {total_statements:,}")
    print(f"   Total Missing Lines: {total_missing:,}")
    print(
        f"   Potential Coverage Gain: {(total_missing / data['totals']['num_statements'] * 100):.2f}%"
    )

    print(f"\n📋 Top {len(top_files)} Files:\n")
    print(f"{'#':<4} {'File':<45} {'Cov%':<8} {'Missing':<10} {'Stmts':<8}")
    print("-" * 80)

    for i, file_info in enumerate(top_files, 1):
        print(
            f"{i:<4} {file_info['file']:<45} {file_info['coverage']:<7.1f}% {file_info['missing']:<10} {file_info['statements']:<8}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Analyze test coverage for strategic planning"
    )
    parser.add_argument("--range", help="Coverage range (e.g., 0-30)", default=None)
    parser.add_argument("--top", type=int, help="Number of top files", default=50)
    parser.add_argument(
        "--coverage-file", help="Coverage JSON file", default="coverage_final.json"
    )

    args = parser.parse_args()
    data = load_coverage_data(args.coverage_file)

    print(f"\n📊 Total Project Coverage: {data['totals']['percent_covered']:.2f}%")
    print(f"📊 Total Statements: {data['totals']['num_statements']:,}")
    print(f"📊 Missing Lines: {data['totals']['missing_lines']:,}")

    if args.range:
        analyze_by_range(data, args.range, args.top)
    else:
        print("\n❌ Please specify --range")
        print("Example: python3 scripts/analyze_coverage_json.py --range 0-30 --top 50")


if __name__ == "__main__":
    main()
