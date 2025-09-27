"""
Performance Suite Base Classes and Utilities

Provides base classes and utilities for performance benchmarking across
the agenthub system including metrics collection, resource monitoring,
and result reporting.
"""

import time
import psutil
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Individual performance metric with validation against targets."""
    name: str
    value: float
    unit: str
    target: Optional[float] = None
    category: str = "general"
    timestamp: float = field(default_factory=time.time)
    
    @property
    def meets_target(self) -> bool:
        """Check if metric meets target threshold."""
        if self.target is None:
            return True
        return self.value <= self.target if self.unit in ['ms', 's', 'bytes'] else self.value >= self.target


@dataclass
class ResourceUsage:
    """System resource usage snapshot."""
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class BenchmarkResult:
    """Results from a performance benchmark."""
    benchmark_name: str
    metrics: List[PerformanceMetric]
    success_rate: float
    execution_time: float
    resource_usage: List[ResourceUsage] = field(default_factory=list)
    error_details: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    @property
    def all_targets_met(self) -> bool:
        """Check if all metrics with targets meet their thresholds."""
        return all(metric.meets_target for metric in self.metrics if metric.target is not None)
    
    def get_metric(self, name: str) -> Optional[PerformanceMetric]:
        """Get specific metric by name."""
        for metric in self.metrics:
            if metric.name == name:
                return metric
        return None
    
    def get_metrics_by_category(self, category: str) -> List[PerformanceMetric]:
        """Get all metrics in specific category."""
        return [metric for metric in self.metrics if metric.category == category]


class ResourceMonitor:
    """System resource monitoring utility."""
    
    def __init__(self):
        self.samples: List[ResourceUsage] = []
        self.monitoring = False
        
    def start_monitoring(self):
        """Start resource monitoring."""
        self.monitoring = True
        self.samples.clear()
        self.sample_resources()
        
    def stop_monitoring(self) -> List[ResourceUsage]:
        """Stop monitoring and return samples."""
        if self.monitoring:
            self.sample_resources()
            self.monitoring = False
        return self.samples.copy()
        
    def sample_resources(self):
        """Take a resource usage sample."""
        if not self.monitoring:
            return
            
        try:
            process = psutil.Process()
            cpu_percent = process.cpu_percent()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            memory_percent = process.memory_percent()
            
            sample = ResourceUsage(
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                memory_percent=memory_percent
            )
            self.samples.append(sample)
        except Exception as e:
            logger.warning(f"Failed to sample resources: {e}")
    
    def get_peak_usage(self) -> Optional[ResourceUsage]:
        """Get peak resource usage."""
        if not self.samples:
            return None
        return max(self.samples, key=lambda s: s.memory_mb)
    
    def get_average_usage(self) -> Optional[ResourceUsage]:
        """Get average resource usage."""
        if not self.samples:
            return None
            
        avg_cpu = statistics.mean(s.cpu_percent for s in self.samples)
        avg_memory_mb = statistics.mean(s.memory_mb for s in self.samples)
        avg_memory_percent = statistics.mean(s.memory_percent for s in self.samples)
        
        return ResourceUsage(
            cpu_percent=avg_cpu,
            memory_mb=avg_memory_mb,
            memory_percent=avg_memory_percent
        )


class PerformanceBenchmark:
    """Base class for performance benchmarks."""
    
    def __init__(self, name: str):
        self.name = name
        self.resource_monitor = ResourceMonitor()
        
    async def setup(self):
        """Setup benchmark environment."""
        pass
        
    async def teardown(self):
        """Clean up after benchmark."""
        pass
        
    async def run_benchmark(self) -> BenchmarkResult:
        """Run the benchmark and return results."""
        raise NotImplementedError("Subclasses must implement run_benchmark")
    
    def create_metric(self, name: str, value: float, unit: str, 
                     target: Optional[float] = None, category: str = "general") -> PerformanceMetric:
        """Create a performance metric."""
        return PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            target=target,
            category=category
        )


class PerformanceSuite:
    """Collection of performance benchmarks with comprehensive reporting."""
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.benchmarks: List[PerformanceBenchmark] = []
        self.output_dir = output_dir or Path(__file__).parent / "results"
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
    def add_benchmark(self, benchmark: PerformanceBenchmark):
        """Add benchmark to suite."""
        self.benchmarks.append(benchmark)
        
    async def run_all_benchmarks(self) -> List[BenchmarkResult]:
        """Run all benchmarks in suite."""
        results = []
        
        for benchmark in self.benchmarks:
            logger.info(f"Running benchmark: {benchmark.name}")
            
            try:
                await benchmark.setup()
                result = await benchmark.run_benchmark()
                await benchmark.teardown()
                results.append(result)
                
                logger.info(f"✅ Completed {benchmark.name}: "
                           f"{result.success_rate:.1%} success rate, "
                           f"{result.execution_time:.2f}s execution time")
                           
            except Exception as e:
                logger.error(f"❌ Failed {benchmark.name}: {str(e)}")
                # Create failed result
                failed_result = BenchmarkResult(
                    benchmark_name=benchmark.name,
                    metrics=[],
                    success_rate=0.0,
                    execution_time=0.0,
                    error_details=[f"Benchmark failed: {str(e)}"]
                )
                results.append(failed_result)
                
        return results
    
    def save_results(self, results: List[BenchmarkResult], filename: str = None):
        """Save benchmark results to file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_results_{timestamp}.json"
            
        output_file = self.output_dir / filename
        
        # Convert results to JSON-serializable format
        results_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_benchmarks": len(results),
                "successful_benchmarks": sum(1 for r in results if r.success_rate > 0.5),
                "overall_success_rate": statistics.mean([r.success_rate for r in results]) if results else 0.0,
                "total_execution_time": sum(r.execution_time for r in results)
            },
            "benchmarks": [
                {
                    "name": result.benchmark_name,
                    "success_rate": result.success_rate,
                    "execution_time": result.execution_time,
                    "all_targets_met": result.all_targets_met,
                    "metrics": [
                        {
                            "name": metric.name,
                            "value": metric.value,
                            "unit": metric.unit,
                            "target": metric.target,
                            "meets_target": metric.meets_target,
                            "category": metric.category
                        } for metric in result.metrics
                    ],
                    "error_details": result.error_details,
                    "metadata": result.metadata
                } for result in results
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(results_data, f, indent=2)
            
        logger.info(f"📊 Results saved to: {output_file}")
        return output_file
    
    def generate_report(self, results: List[BenchmarkResult]) -> str:
        """Generate human-readable performance report."""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("PERFORMANCE BENCHMARK RESULTS")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        # Summary
        successful = sum(1 for r in results if r.success_rate > 0.5)
        overall_success = statistics.mean([r.success_rate for r in results]) if results else 0.0
        total_time = sum(r.execution_time for r in results)
        
        report_lines.append(f"Summary:")
        report_lines.append(f"  Total Benchmarks: {len(results)}")
        report_lines.append(f"  Successful: {successful}/{len(results)}")
        report_lines.append(f"  Overall Success Rate: {overall_success:.1%}")
        report_lines.append(f"  Total Execution Time: {total_time:.2f}s")
        report_lines.append("")
        
        # Individual benchmark results
        for result in results:
            report_lines.append(f"Benchmark: {result.benchmark_name}")
            report_lines.append(f"  Success Rate: {result.success_rate:.1%}")
            report_lines.append(f"  Execution Time: {result.execution_time:.2f}s")
            report_lines.append(f"  All Targets Met: {'✅ Yes' if result.all_targets_met else '❌ No'}")
            
            if result.metrics:
                report_lines.append("  Key Metrics:")
                for metric in result.metrics:
                    status = "✅" if metric.meets_target else "❌"
                    target_text = f" (target: {metric.target})" if metric.target else ""
                    report_lines.append(f"    {metric.name}: {metric.value:.2f}{metric.unit}{target_text} {status}")
            
            if result.error_details:
                report_lines.append("  Errors:")
                for error in result.error_details:
                    report_lines.append(f"    - {error}")
            
            report_lines.append("")
        
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)


__all__ = [
    'PerformanceMetric',
    'ResourceUsage', 
    'BenchmarkResult',
    'ResourceMonitor',
    'PerformanceBenchmark',
    'PerformanceSuite'
]