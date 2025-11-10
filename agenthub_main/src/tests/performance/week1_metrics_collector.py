"""
Week 1 Performance Metrics Collector

Comprehensive metrics collection system for tracking performance improvements
across the Week 1 optimization phase. Provides detailed analysis, trending,
and comparison capabilities for baseline vs optimized performance.

Features:
- Real-time metrics collection
- Statistical analysis (mean, median, p95, p99)
- Trend analysis and visualization
- Export to JSON/CSV formats
- Historical comparison
- Performance regression detection
"""

from __future__ import annotations

import csv
import json
import statistics
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any


class MetricStatus(Enum):
    """Status of a performance metric."""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    PENDING = "pending"


@dataclass
class OperationMetric:
    """Detailed metrics for a single operation."""
    operation_name: str
    baseline_target_ms: float
    optimized_target_ms: float
    measurements: list[float] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def count(self) -> int:
        """Number of measurements."""
        return len(self.measurements)

    @property
    def average(self) -> float:
        """Average execution time in milliseconds."""
        return statistics.mean(self.measurements) if self.measurements else 0.0

    @property
    def median(self) -> float:
        """Median execution time in milliseconds."""
        return statistics.median(self.measurements) if self.measurements else 0.0

    @property
    def stdev(self) -> float:
        """Standard deviation of execution times."""
        return statistics.stdev(self.measurements) if len(self.measurements) > 1 else 0.0

    @property
    def min(self) -> float:
        """Minimum execution time."""
        return min(self.measurements) if self.measurements else 0.0

    @property
    def max(self) -> float:
        """Maximum execution time."""
        return max(self.measurements) if self.measurements else 0.0

    @property
    def p50(self) -> float:
        """50th percentile (median)."""
        return self.median

    @property
    def p95(self) -> float:
        """95th percentile execution time."""
        return self._percentile(0.95)

    @property
    def p99(self) -> float:
        """99th percentile execution time."""
        return self._percentile(0.99)

    def _percentile(self, percentile: float) -> float:
        """Calculate percentile value."""
        if not self.measurements:
            return 0.0
        sorted_measurements = sorted(self.measurements)
        index = int(len(sorted_measurements) * percentile)
        return sorted_measurements[min(index, len(sorted_measurements) - 1)]

    @property
    def improvement_factor(self) -> float:
        """Improvement factor vs baseline."""
        if self.average == 0:
            return 0.0
        return self.baseline_target_ms / self.average

    @property
    def meets_target(self) -> bool:
        """Check if average meets optimized target."""
        return self.average <= self.optimized_target_ms

    @property
    def status(self) -> MetricStatus:
        """Determine metric status."""
        if not self.measurements:
            return MetricStatus.PENDING

        if self.meets_target:
            return MetricStatus.PASS

        # Warning if within 10% of target
        threshold = self.optimized_target_ms * 1.1
        if self.average <= threshold:
            return MetricStatus.WARNING

        return MetricStatus.FAIL

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "operation_name": self.operation_name,
            "baseline_target_ms": self.baseline_target_ms,
            "optimized_target_ms": self.optimized_target_ms,
            "timestamp": self.timestamp,
            "statistics": {
                "count": self.count,
                "average": round(self.average, 2),
                "median": round(self.median, 2),
                "stdev": round(self.stdev, 2),
                "min": round(self.min, 2),
                "max": round(self.max, 2),
                "p50": round(self.p50, 2),
                "p95": round(self.p95, 2),
                "p99": round(self.p99, 2)
            },
            "performance": {
                "improvement_factor": round(self.improvement_factor, 2),
                "meets_target": self.meets_target,
                "status": self.status.value
            }
        }


class Week1MetricsCollector:
    """
    Comprehensive metrics collector for Week 1 performance optimization.

    Collects, analyzes, and reports on performance metrics across all
    optimization targets. Supports historical comparison and regression
    detection.
    """

    def __init__(self, output_dir: Path | None = None):
        """
        Initialize metrics collector.

        Args:
            output_dir: Directory for saving metrics reports
        """
        self.metrics: dict[str, OperationMetric] = {}
        self.output_dir = output_dir or Path("./performance_reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.start_time = time.time()
        self.test_id = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

    def register_operation(
        self,
        operation_name: str,
        baseline_target_ms: float,
        optimized_target_ms: float
    ) -> None:
        """
        Register a new operation for tracking.

        Args:
            operation_name: Unique name for the operation
            baseline_target_ms: Baseline performance target
            optimized_target_ms: Optimized performance target (3x improvement)
        """
        self.metrics[operation_name] = OperationMetric(
            operation_name=operation_name,
            baseline_target_ms=baseline_target_ms,
            optimized_target_ms=optimized_target_ms
        )

    def record_measurement(self, operation_name: str, duration_ms: float) -> None:
        """
        Record a performance measurement.

        Args:
            operation_name: Name of the operation
            duration_ms: Execution time in milliseconds
        """
        if operation_name not in self.metrics:
            raise ValueError(f"Operation '{operation_name}' not registered")

        self.metrics[operation_name].measurements.append(duration_ms)

    def get_metric(self, operation_name: str) -> OperationMetric | None:
        """Get metrics for a specific operation."""
        return self.metrics.get(operation_name)

    def get_all_metrics(self) -> dict[str, OperationMetric]:
        """Get all collected metrics."""
        return self.metrics

    def generate_summary(self) -> dict[str, Any]:
        """
        Generate comprehensive summary report.

        Returns:
            Dictionary containing detailed performance summary
        """
        total_operations = len(self.metrics)
        passing = sum(1 for m in self.metrics.values() if m.status == MetricStatus.PASS)
        warning = sum(1 for m in self.metrics.values() if m.status == MetricStatus.WARNING)
        failing = sum(1 for m in self.metrics.values() if m.status == MetricStatus.FAIL)
        pending = sum(1 for m in self.metrics.values() if m.status == MetricStatus.PENDING)

        operations_data = {
            name: metric.to_dict()
            for name, metric in self.metrics.items()
        }

        return {
            "test_id": self.test_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "duration_seconds": round(time.time() - self.start_time, 2),
            "summary": {
                "total_operations": total_operations,
                "passing": passing,
                "warning": warning,
                "failing": failing,
                "pending": pending,
                "success_rate": round(passing / total_operations * 100, 2) if total_operations > 0 else 0.0,
                "overall_success": failing == 0 and pending == 0
            },
            "operations": operations_data
        }

    def export_json(self, filename: str | None = None) -> Path:
        """
        Export metrics to JSON file.

        Args:
            filename: Optional custom filename

        Returns:
            Path to the exported file
        """
        if filename is None:
            filename = f"week1_metrics_{self.test_id}.json"

        filepath = self.output_dir / filename
        summary = self.generate_summary()

        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)

        return filepath

    def export_csv(self, filename: str | None = None) -> Path:
        """
        Export metrics to CSV file.

        Args:
            filename: Optional custom filename

        Returns:
            Path to the exported file
        """
        if filename is None:
            filename = f"week1_metrics_{self.test_id}.csv"

        filepath = self.output_dir / filename

        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'Operation',
                'Baseline Target (ms)',
                'Optimized Target (ms)',
                'Count',
                'Average (ms)',
                'Median (ms)',
                'StdDev (ms)',
                'Min (ms)',
                'Max (ms)',
                'P95 (ms)',
                'P99 (ms)',
                'Improvement Factor',
                'Meets Target',
                'Status'
            ])

            # Data rows
            for metric in self.metrics.values():
                writer.writerow([
                    metric.operation_name,
                    metric.baseline_target_ms,
                    metric.optimized_target_ms,
                    metric.count,
                    round(metric.average, 2),
                    round(metric.median, 2),
                    round(metric.stdev, 2),
                    round(metric.min, 2),
                    round(metric.max, 2),
                    round(metric.p95, 2),
                    round(metric.p99, 2),
                    round(metric.improvement_factor, 2),
                    metric.meets_target,
                    metric.status.value
                ])

        return filepath

    def print_report(self) -> None:
        """Print formatted metrics report to console."""
        summary = self.generate_summary()

        print("\n" + "="*100)
        print("WEEK 1 PERFORMANCE METRICS REPORT")
        print("="*100)
        print(f"Test ID: {summary['test_id']}")
        print(f"Timestamp: {summary['timestamp']}")
        print(f"Duration: {summary['duration_seconds']}s")
        print()

        print("SUMMARY:")
        print("-"*100)
        s = summary['summary']
        print(f"  Total Operations: {s['total_operations']}")
        print(f"  Passing: {s['passing']} ✅")
        print(f"  Warning: {s['warning']} ⚠️")
        print(f"  Failing: {s['failing']} ❌")
        print(f"  Pending: {s['pending']} ⏳")
        print(f"  Success Rate: {s['success_rate']}%")
        print(f"  Overall Success: {'✅ YES' if s['overall_success'] else '❌ NO'}")
        print()

        print("OPERATION DETAILS:")
        print("-"*100)

        for op_name, op_data in summary['operations'].items():
            status_icon = {
                'pass': '✅',
                'warning': '⚠️',
                'fail': '❌',
                'pending': '⏳'
            }[op_data['performance']['status']]

            print(f"\n{status_icon} {op_name.upper().replace('_', ' ')}:")
            print(f"  Baseline Target: {op_data['baseline_target_ms']}ms")
            print(f"  Optimized Target: {op_data['optimized_target_ms']}ms")

            stats = op_data['statistics']
            print(f"  Measurements: {stats['count']}")
            print(f"  Average: {stats['average']}ms")
            print(f"  Median: {stats['median']}ms")
            print(f"  StdDev: {stats['stdev']}ms")
            print(f"  Range: {stats['min']}ms - {stats['max']}ms")
            print(f"  P95: {stats['p95']}ms")
            print(f"  P99: {stats['p99']}ms")

            perf = op_data['performance']
            print(f"  Improvement Factor: {perf['improvement_factor']}x")
            print(f"  Meets Target: {'✅ Yes' if perf['meets_target'] else '❌ No'}")

        print("\n" + "="*100)

    def compare_with_baseline(self, baseline_file: Path) -> dict[str, Any]:
        """
        Compare current metrics with a baseline report.

        Args:
            baseline_file: Path to baseline JSON report

        Returns:
            Comparison analysis dictionary
        """
        with open(baseline_file) as f:
            baseline_data = json.load(f)

        current_summary = self.generate_summary()
        comparison = {
            "baseline_test_id": baseline_data.get("test_id"),
            "current_test_id": current_summary["test_id"],
            "timestamp": datetime.now(UTC).isoformat(),
            "improvements": {},
            "regressions": {},
            "summary": {}
        }

        for op_name in self.metrics.keys():
            if op_name not in baseline_data.get("operations", {}):
                continue

            baseline_avg = baseline_data["operations"][op_name]["statistics"]["average"]
            current_avg = current_summary["operations"][op_name]["statistics"]["average"]

            delta_ms = current_avg - baseline_avg
            delta_percent = (delta_ms / baseline_avg * 100) if baseline_avg > 0 else 0.0

            comparison_data = {
                "baseline_avg_ms": baseline_avg,
                "current_avg_ms": current_avg,
                "delta_ms": round(delta_ms, 2),
                "delta_percent": round(delta_percent, 2)
            }

            if delta_percent < -5:  # 5% improvement threshold
                comparison["improvements"][op_name] = comparison_data
            elif delta_percent > 5:  # 5% regression threshold
                comparison["regressions"][op_name] = comparison_data

        comparison["summary"] = {
            "improvements_count": len(comparison["improvements"]),
            "regressions_count": len(comparison["regressions"]),
            "stable_count": len(self.metrics) - len(comparison["improvements"]) - len(comparison["regressions"])
        }

        return comparison


if __name__ == "__main__":
    """Example usage of metrics collector."""
    collector = Week1MetricsCollector()

    # Register operations
    collector.register_operation("task_creation", 150.0, 50.0)
    collector.register_operation("task_retrieval", 100.0, 33.0)
    collector.register_operation("task_listing", 200.0, 67.0)

    # Simulate measurements
    import random
    for _ in range(50):
        collector.record_measurement("task_creation", random.uniform(40, 60))
        collector.record_measurement("task_retrieval", random.uniform(25, 40))
        collector.record_measurement("task_listing", random.uniform(55, 75))

    # Generate and print report
    collector.print_report()

    # Export to files
    json_file = collector.export_json()
    csv_file = collector.export_csv()

    print("\nReports exported:")
    print(f"  JSON: {json_file}")
    print(f"  CSV: {csv_file}")
