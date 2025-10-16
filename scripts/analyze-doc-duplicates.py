#!/usr/bin/env python3
"""
Documentation Duplicate Analysis Script
Phase 1: Content Analysis for Documentation Audit

Scans all markdown files in ai_docs/ to identify:
- Duplicate content (exact and semantic)
- Overlapping sections
- Similar headings and topics
- Recommended merge candidates

Author: Deep Research Agent
Date: 2025-10-16
"""

import os
import json
import hashlib
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Dict, List, Set, Tuple


class DocumentAnalyzer:
    """Analyzes documentation for duplicates and overlapping content."""

    def __init__(self, docs_root: str):
        self.docs_root = Path(docs_root)
        self.files_analyzed = 0
        self.total_size = 0

        # Analysis results
        self.content_hashes: Dict[str, List[str]] = defaultdict(list)
        self.heading_similarity: Dict[Tuple[str, str], float] = {}
        self.content_overlap: Dict[Tuple[str, str], float] = {}
        self.topic_clusters: Dict[str, List[str]] = defaultdict(list)

        # Document metadata
        self.doc_metadata: Dict[str, Dict] = {}

        # Thresholds for detection
        self.HEADING_THRESHOLD = 0.80  # 80% similarity
        self.CONTENT_THRESHOLD = 0.70  # 70% overlap
        self.EXACT_MATCH_THRESHOLD = 0.95  # 95% for near-exact

    def scan_documentation(self) -> None:
        """Scan all markdown files in ai_docs/."""
        print(f"Scanning documentation in: {self.docs_root}")
        print("=" * 80)

        # Skip these directories
        skip_dirs = {'_obsolete_docs', '.git', '__pycache__', 'node_modules'}

        for md_file in self.docs_root.rglob("*.md"):
            # Skip if in excluded directories
            if any(skip_dir in md_file.parts for skip_dir in skip_dirs):
                continue

            self.analyze_file(md_file)

        print(f"\n✅ Analyzed {self.files_analyzed} files")
        print(f"📊 Total documentation size: {self.total_size / 1024:.2f} KB")

    def analyze_file(self, file_path: Path) -> None:
        """Analyze a single markdown file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            self.files_analyzed += 1
            self.total_size += len(content)

            # Extract metadata
            relative_path = str(file_path.relative_to(self.docs_root))
            file_size = len(content)

            # Extract headings
            headings = self.extract_headings(content)

            # Extract keywords for topic clustering
            keywords = self.extract_keywords(content)

            # Calculate content hash
            content_hash = hashlib.md5(content.encode()).hexdigest()

            # Store metadata
            self.doc_metadata[relative_path] = {
                'path': relative_path,
                'size': file_size,
                'headings': headings,
                'keywords': keywords,
                'content_hash': content_hash,
                'content': content
            }

            # Track content hash for exact duplicates
            self.content_hashes[content_hash].append(relative_path)

            # Cluster by keywords
            for keyword in keywords:
                self.topic_clusters[keyword].append(relative_path)

        except Exception as e:
            print(f"⚠️  Error analyzing {file_path}: {e}")

    def extract_headings(self, content: str) -> List[str]:
        """Extract all headings from markdown content."""
        heading_pattern = r'^#{1,6}\s+(.+)$'
        headings = re.findall(heading_pattern, content, re.MULTILINE)
        return [h.strip() for h in headings]

    def extract_keywords(self, content: str) -> Set[str]:
        """Extract significant keywords for topic clustering."""
        # Key technical terms to look for
        important_terms = {
            'authentication', 'auth', 'keycloak', 'jwt', 'token',
            'context', 'hierarchy', 'global', 'project', 'branch', 'task',
            'ddd', 'domain', 'entity', 'repository', 'use case', 'application',
            'agent', 'orchestrator', 'delegation', 'mcp', 'tool',
            'docker', 'deployment', 'container', 'database', 'postgresql',
            'frontend', 'backend', 'react', 'typescript', 'python',
            'testing', 'test', 'qa', 'quality',
            'setup', 'installation', 'configuration',
            'troubleshooting', 'debug', 'error', 'issue',
            'migration', 'upgrade', 'version',
            'api', 'endpoint', 'rest', 'websocket',
            'security', 'compliance', 'audit',
            'performance', 'optimization', 'cache'
        }

        content_lower = content.lower()
        found_keywords = set()

        for term in important_terms:
            if term in content_lower:
                found_keywords.add(term)

        return found_keywords

    def compare_documents(self) -> None:
        """Compare all documents for similarity."""
        print("\n🔍 Comparing documents for similarity...")
        print("=" * 80)

        files = list(self.doc_metadata.keys())
        total_comparisons = len(files) * (len(files) - 1) // 2
        comparisons_done = 0

        for i, file1 in enumerate(files):
            for file2 in files[i + 1:]:
                self.compare_pair(file1, file2)
                comparisons_done += 1

                # Progress indicator
                if comparisons_done % 1000 == 0:
                    progress = (comparisons_done / total_comparisons) * 100
                    print(f"Progress: {progress:.1f}% ({comparisons_done}/{total_comparisons})")

        print(f"✅ Completed {comparisons_done} document comparisons")

    def compare_pair(self, file1: str, file2: str) -> None:
        """Compare two documents for similarity."""
        meta1 = self.doc_metadata[file1]
        meta2 = self.doc_metadata[file2]

        # Compare headings
        heading_sim = self.calculate_heading_similarity(
            meta1['headings'],
            meta2['headings']
        )

        if heading_sim >= self.HEADING_THRESHOLD:
            self.heading_similarity[(file1, file2)] = heading_sim

        # Compare content overlap
        content_overlap = self.calculate_content_overlap(
            meta1['content'],
            meta2['content']
        )

        if content_overlap >= self.CONTENT_THRESHOLD:
            self.content_overlap[(file1, file2)] = content_overlap

    def calculate_heading_similarity(self, headings1: List[str], headings2: List[str]) -> float:
        """Calculate similarity between two sets of headings."""
        if not headings1 or not headings2:
            return 0.0

        # Count matching headings (case-insensitive, fuzzy)
        matches = 0
        total = max(len(headings1), len(headings2))

        for h1 in headings1:
            for h2 in headings2:
                similarity = SequenceMatcher(None, h1.lower(), h2.lower()).ratio()
                if similarity >= 0.85:  # 85% similar headings count as match
                    matches += 1
                    break

        return matches / total if total > 0 else 0.0

    def calculate_content_overlap(self, content1: str, content2: str) -> float:
        """Calculate content overlap between two documents."""
        # Use sequence matcher for overall similarity
        similarity = SequenceMatcher(None, content1, content2).ratio()
        return similarity

    def identify_merge_candidates(self) -> List[Dict]:
        """Identify documents that should be merged."""
        merge_candidates = []
        processed_pairs = set()

        # Find exact duplicates
        for content_hash, files in self.content_hashes.items():
            if len(files) > 1:
                merge_candidates.append({
                    'type': 'exact_duplicate',
                    'files': files,
                    'similarity': 1.0,
                    'reason': 'Identical content (100% match)'
                })

        # Find high heading similarity
        for (file1, file2), similarity in self.heading_similarity.items():
            pair_key = tuple(sorted([file1, file2]))
            if pair_key not in processed_pairs:
                merge_candidates.append({
                    'type': 'similar_headings',
                    'files': [file1, file2],
                    'similarity': similarity,
                    'reason': f'Heading similarity: {similarity:.1%}'
                })
                processed_pairs.add(pair_key)

        # Find high content overlap
        for (file1, file2), overlap in self.content_overlap.items():
            pair_key = tuple(sorted([file1, file2]))
            if pair_key not in processed_pairs:
                merge_candidates.append({
                    'type': 'content_overlap',
                    'files': [file1, file2],
                    'similarity': overlap,
                    'reason': f'Content overlap: {overlap:.1%}'
                })
                processed_pairs.add(pair_key)

        # Sort by similarity (highest first)
        merge_candidates.sort(key=lambda x: x['similarity'], reverse=True)

        return merge_candidates

    def identify_topic_clusters(self) -> Dict[str, List[str]]:
        """Identify documents grouped by topic."""
        # Filter clusters with multiple documents
        significant_clusters = {
            topic: files
            for topic, files in self.topic_clusters.items()
            if len(files) >= 3  # At least 3 docs on same topic
        }

        return significant_clusters

    def generate_report(self, output_path: str) -> None:
        """Generate comprehensive duplicate analysis report."""
        print("\n📝 Generating report...")

        merge_candidates = self.identify_merge_candidates()
        topic_clusters = self.identify_topic_clusters()

        report_date = datetime.now().strftime("%Y%m%d")

        report = f"""# Documentation Duplicate Content Analysis
**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Script**: analyze-doc-duplicates.py
**Phase**: 1 - Content Analysis

## Executive Summary

### Analysis Scope
- **Total files analyzed**: {self.files_analyzed}
- **Total documentation size**: {self.total_size / 1024:.2f} KB
- **Documentation root**: {self.docs_root}

### Key Findings
- **Exact duplicates**: {sum(1 for c in merge_candidates if c['type'] == 'exact_duplicate')}
- **Similar headings**: {sum(1 for c in merge_candidates if c['type'] == 'similar_headings')}
- **Content overlap**: {sum(1 for c in merge_candidates if c['type'] == 'content_overlap')}
- **Total merge candidates**: {len(merge_candidates)}
- **Topic clusters**: {len(topic_clusters)}

---

## 1. Exact Duplicates (100% Match)

These files have identical content and should be consolidated immediately.

"""

        # Exact duplicates section
        exact_dupes = [c for c in merge_candidates if c['type'] == 'exact_duplicate']
        if exact_dupes:
            for idx, candidate in enumerate(exact_dupes, 1):
                report += f"### Duplicate Set {idx}\n\n"
                report += f"**Files** ({len(candidate['files'])} identical copies):\n"
                for file in candidate['files']:
                    size = self.doc_metadata[file]['size']
                    report += f"- `{file}` ({size} bytes)\n"
                report += f"\n**Recommendation**: Keep the most recent or appropriately located version, archive others.\n\n"
        else:
            report += "✅ No exact duplicates found.\n\n"

        # Similar headings section
        report += """---

## 2. Documents with Similar Headings (80%+ Match)

These documents have very similar heading structures, suggesting overlapping content.

"""

        similar_headings = [c for c in merge_candidates if c['type'] == 'similar_headings']
        if similar_headings:
            for idx, candidate in enumerate(similar_headings[:20], 1):  # Top 20
                file1, file2 = candidate['files']
                similarity = candidate['similarity']
                report += f"### Match {idx}: {similarity:.1%} similar\n\n"
                report += f"**File 1**: `{file1}`\n"
                report += f"- Headings: {', '.join(self.doc_metadata[file1]['headings'][:3])}...\n\n"
                report += f"**File 2**: `{file2}`\n"
                report += f"- Headings: {', '.join(self.doc_metadata[file2]['headings'][:3])}...\n\n"
                report += f"**Recommendation**: Review for consolidation or differentiation.\n\n"

            if len(similar_headings) > 20:
                report += f"\n*... and {len(similar_headings) - 20} more similar heading pairs.*\n\n"
        else:
            report += "✅ No significant heading similarities found.\n\n"

        # Content overlap section
        report += """---

## 3. Documents with Content Overlap (70%+ Match)

These documents share significant content sections.

"""

        content_overlaps = [c for c in merge_candidates if c['type'] == 'content_overlap']
        if content_overlaps:
            for idx, candidate in enumerate(content_overlaps[:20], 1):  # Top 20
                file1, file2 = candidate['files']
                overlap = candidate['similarity']
                report += f"### Overlap {idx}: {overlap:.1%} similar content\n\n"
                report += f"**File 1**: `{file1}` ({self.doc_metadata[file1]['size']} bytes)\n"
                report += f"**File 2**: `{file2}` ({self.doc_metadata[file2]['size']} bytes)\n\n"

                # Show shared keywords
                shared_keywords = (
                    self.doc_metadata[file1]['keywords'] &
                    self.doc_metadata[file2]['keywords']
                )
                if shared_keywords:
                    report += f"**Shared topics**: {', '.join(sorted(shared_keywords))}\n\n"

                report += f"**Recommendation**: Merge into single comprehensive document.\n\n"

            if len(content_overlaps) > 20:
                report += f"\n*... and {len(content_overlaps) - 20} more content overlaps.*\n\n"
        else:
            report += "✅ No significant content overlaps found.\n\n"

        # Topic clusters section
        report += """---

## 4. Topic Clusters (3+ Documents)

Documents grouped by shared topics that may benefit from consolidation.

"""

        if topic_clusters:
            for topic, files in sorted(topic_clusters.items(), key=lambda x: len(x[1]), reverse=True)[:15]:
                report += f"### Topic: {topic.upper()} ({len(files)} documents)\n\n"
                report += "**Files**:\n"
                for file in sorted(files)[:10]:  # Show up to 10 files
                    report += f"- `{file}`\n"
                if len(files) > 10:
                    report += f"- *... and {len(files) - 10} more*\n"
                report += f"\n**Recommendation**: Consider creating a single comprehensive guide for '{topic}'.\n\n"

            if len(topic_clusters) > 15:
                report += f"\n*... and {len(topic_clusters) - 15} more topic clusters.*\n\n"
        else:
            report += "✅ No significant topic clustering found.\n\n"

        # Consolidation recommendations
        report += """---

## 5. Consolidation Recommendations

### Priority 1: Exact Duplicates (Immediate Action)
"""

        if exact_dupes:
            report += f"\n{len(exact_dupes)} sets of exact duplicates should be resolved immediately:\n\n"
            for idx, candidate in enumerate(exact_dupes, 1):
                report += f"{idx}. Consolidate {len(candidate['files'])} copies into one file\n"
        else:
            report += "\n✅ No exact duplicates to consolidate.\n"

        report += """
### Priority 2: High Overlap (Review This Week)
"""

        high_overlap = [c for c in merge_candidates if c['similarity'] >= self.EXACT_MATCH_THRESHOLD]
        if high_overlap:
            report += f"\n{len(high_overlap)} document pairs with 95%+ similarity:\n\n"
            for candidate in high_overlap[:10]:
                files_str = " + ".join(candidate['files'][:2])
                report += f"- {files_str} ({candidate['similarity']:.1%})\n"
        else:
            report += "\n✅ No high overlap documents requiring immediate merge.\n"

        report += """
### Priority 3: Topic Consolidation (Plan This Month)
"""

        if topic_clusters:
            top_topics = sorted(topic_clusters.items(), key=lambda x: len(x[1]), reverse=True)[:5]
            report += f"\nTop 5 topics with multiple documents:\n\n"
            for topic, files in top_topics:
                report += f"- **{topic}**: {len(files)} documents → Consolidate to 1-2 comprehensive guides\n"
        else:
            report += "\n✅ Topics are well-organized.\n"

        # Action plan section
        report += """
---

## 6. Suggested Action Plan

### Week 1: Exact Duplicates
1. Review each exact duplicate set
2. Choose the best version (most recent, best location, most complete)
3. Archive other versions to `_obsolete_docs/{date}/consolidated/`
4. Update any cross-references

### Week 2: High Overlap Documents
1. Review documents with 95%+ similarity
2. Create consolidated versions combining unique content
3. Archive source documents
4. Update index.json and cross-references

### Week 3: Topic Clustering
1. Review top 5 topic clusters
2. Plan consolidation strategy for each topic
3. Create comprehensive topic guides
4. Archive fragmented documentation

### Week 4: Validation
1. Verify no broken links
2. Update documentation index
3. Test navigation and discoverability
4. Update CHANGELOG.md

---

## 7. Technical Notes

### Analysis Parameters
- **Heading similarity threshold**: {self.HEADING_THRESHOLD:.0%}
- **Content overlap threshold**: {self.CONTENT_THRESHOLD:.0%}
- **Exact match threshold**: {self.EXACT_MATCH_THRESHOLD:.0%}
- **Topic cluster minimum**: 3 documents

### Files Excluded from Analysis
- `_obsolete_docs/` - Already archived
- `.git/` - Version control
- `__pycache__/` - Python cache
- `node_modules/` - Dependencies

---

## 8. Next Steps

1. **Phase 2**: Run `scripts/audit-architecture-accuracy.py` to identify outdated architecture references
2. **Phase 3**: Create merge strategy based on both Phase 1 and Phase 2 findings
3. **Phase 4**: Execute consolidation with documentation-agent
4. **Phase 5**: Architecture update pass
5. **Phase 6**: Final validation and quality check

---

**Report generated by**: Deep Research Agent
**Script version**: 1.0.0
**Date**: {datetime.now().strftime("%Y-%m-%d")}
"""

        # Write report
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"✅ Report generated: {output_path}")

        # Also generate JSON data for programmatic access
        json_path = output_path.replace('.md', '.json')
        json_data = {
            'generated': datetime.now().isoformat(),
            'analysis_summary': {
                'files_analyzed': self.files_analyzed,
                'total_size_bytes': self.total_size,
                'exact_duplicates': len([c for c in merge_candidates if c['type'] == 'exact_duplicate']),
                'similar_headings': len([c for c in merge_candidates if c['type'] == 'similar_headings']),
                'content_overlaps': len([c for c in merge_candidates if c['type'] == 'content_overlap']),
                'total_merge_candidates': len(merge_candidates),
                'topic_clusters': len(topic_clusters)
            },
            'merge_candidates': merge_candidates,
            'topic_clusters': {k: v for k, v in topic_clusters.items()}
        }

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)

        print(f"✅ JSON data generated: {json_path}")


def main():
    """Main execution function."""
    print("=" * 80)
    print("Documentation Duplicate Analysis - Phase 1")
    print("=" * 80)
    print()

    # Configuration
    project_root = Path(__file__).parent.parent
    docs_root = project_root / "ai_docs"
    report_date = datetime.now().strftime("%Y%m%d")
    output_path = docs_root / "reports-status" / f"duplicate-content-analysis-{report_date}.md"

    # Ensure reports directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"📂 Project root: {project_root}")
    print(f"📚 Documentation root: {docs_root}")
    print(f"📄 Output report: {output_path}")
    print()

    # Create analyzer and run analysis
    analyzer = DocumentAnalyzer(str(docs_root))

    # Step 1: Scan all documentation
    analyzer.scan_documentation()

    # Step 2: Compare documents for similarity
    analyzer.compare_documents()

    # Step 3: Generate comprehensive report
    analyzer.generate_report(str(output_path))

    print()
    print("=" * 80)
    print("✅ Analysis complete!")
    print("=" * 80)
    print()
    print(f"📊 Report: {output_path}")
    print(f"📊 JSON data: {str(output_path).replace('.md', '.json')}")
    print()
    print("Next steps:")
    print("1. Review the generated report")
    print("2. Run Phase 2: scripts/audit-architecture-accuracy.py")
    print("3. Create consolidation plan based on findings")


if __name__ == "__main__":
    main()
