"""Performance Benchmarker for MCP Response Optimization

This module provides comprehensive performance benchmarking and measurement
for the MCP response optimization system.
"""

import logging
import time
import statistics
import json
import sys
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager
from enum import Enum

logger = logging.getLogger(__name__)


class BenchmarkCategory(Enum):
    """Benchmark categories"""
    RESPONSE_OPTIMIZATION = "response_optimization"
    CONTEXT_SELECTION = "context_selection" 
    TEMPLATE_PROCESSING = "template_processing"
    CACHE_PERFORMANCE = "cache_performance"
    END_TO_END = "end_to_end"


@dataclass
class BenchmarkResult:
    """Single benchmark result"""
    name: str
    category: BenchmarkCategory
    execution_time_ms: float
    memory_usage_mb: float
    input_size_bytes: int
    output_size_bytes: int
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def compression_ratio(self) -> float:
        """Calculate compression ratio"""
        if self.input_size_bytes == 0:
            return 0.0
        return (1 - self.output_size_bytes / self.input_size_bytes) * 100
    
    @property
    def throughput_mb_per_sec(self) -> float:
        """Calculate throughput in MB/sec"""
        if self.execution_time_ms == 0:
            return 0.0
        return (self.input_size_bytes / (1024 * 1024)) / (self.execution_time_ms / 1000)


@dataclass
class BenchmarkSuite:
    """Complete benchmark suite results"""
    suite_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    results: List[BenchmarkResult] = field(default_factory=list)
    
    def add_result(self, result: BenchmarkResult) -> None:
        """Add benchmark result"""
        self.results.append(result)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        if not self.results:
            return {"error": "No results available"}
        
        successful_results = [r for r in self.results if r.success]
        
        if not successful_results:
            return {"error": "No successful results"}
        
        execution_times = [r.execution_time_ms for r in successful_results]
        compression_ratios = [r.compression_ratio for r in successful_results]
        throughputs = [r.throughput_mb_per_sec for r in successful_results]
        
        return {
            "total_benchmarks": len(self.results),
            "successful_benchmarks": len(successful_results),
            "success_rate_percent": (len(successful_results) / len(self.results)) * 100,
            "performance": {
                "avg_execution_time_ms": statistics.mean(execution_times),
                "median_execution_time_ms": statistics.median(execution_times),
                "p95_execution_time_ms": statistics.quantiles(execution_times, n=20)[18] if len(execution_times) >= 20 else max(execution_times),
                "min_execution_time_ms": min(execution_times),
                "max_execution_time_ms": max(execution_times)
            },
            "compression": {
                "avg_compression_ratio_percent": statistics.mean(compression_ratios),
                "median_compression_ratio_percent": statistics.median(compression_ratios),
                "min_compression_ratio_percent": min(compression_ratios),
                "max_compression_ratio_percent": max(compression_ratios)
            },
            "throughput": {
                "avg_throughput_mb_per_sec": statistics.mean(throughputs),
                "median_throughput_mb_per_sec": statistics.median(throughputs),
                "max_throughput_mb_per_sec": max(throughputs)
            }
        }


class PerformanceBenchmarker:
    """Comprehensive performance benchmarker"""
    
    def __init__(self):
        """Initialize benchmarker"""
        self.current_suite: Optional[BenchmarkSuite] = None
        self.completed_suites: List[BenchmarkSuite] = []
        
    def start_suite(self, name: str) -> BenchmarkSuite:
        """Start a new benchmark suite"""
        self.current_suite = BenchmarkSuite(
            suite_name=name,
            started_at=datetime.now()
        )
        return self.current_suite
    
    def complete_suite(self) -> Optional[BenchmarkSuite]:
        """Complete current benchmark suite"""
        if self.current_suite:
            self.current_suite.completed_at = datetime.now()
            self.completed_suites.append(self.current_suite)
            completed = self.current_suite
            self.current_suite = None
            return completed
        return None
    
    @contextmanager
    def benchmark(
        self,
        name: str,
        category: BenchmarkCategory,
        input_data: Any = None
    ):
        """Context manager for benchmarking operations"""
        # Measure memory before
        try:
            import tracemalloc
            tracemalloc.start()
            memory_before = tracemalloc.get_traced_memory()[0]
        except:
            memory_before = 0
        
        # Calculate input size
        input_size = 0
        if input_data:
            try:
                input_size = len(json.dumps(input_data, default=str).encode('utf-8'))
            except:
                input_size = sys.getsizeof(input_data)
        
        # Start timing
        start_time = time.perf_counter()
        
        result = BenchmarkResult(
            name=name,
            category=category,
            execution_time_ms=0,
            memory_usage_mb=0,
            input_size_bytes=input_size,
            output_size_bytes=0,
            success=False
        )
        
        try:
            yield result
            result.success = True
        except Exception as e:
            result.error_message = str(e)
            logger.error(f"Benchmark {name} failed: {e}")
        finally:
            # Calculate execution time
            end_time = time.perf_counter()
            result.execution_time_ms = (end_time - start_time) * 1000
            
            # Measure memory after
            try:
                memory_after = tracemalloc.get_traced_memory()[0]
                result.memory_usage_mb = (memory_after - memory_before) / (1024 * 1024)
                tracemalloc.stop()
            except:
                result.memory_usage_mb = 0
            
            # Add to current suite
            if self.current_suite:
                self.current_suite.add_result(result)
    
    def benchmark_response_optimization(
        self,
        optimizer: Any,
        test_responses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Benchmark response optimization performance"""
        results = {}
        
        # Test different response sizes
        for i, response in enumerate(test_responses):
            with self.benchmark(
                f"response_optimization_test_{i+1}",
                BenchmarkCategory.RESPONSE_OPTIMIZATION,
                response
            ) as benchmark:
                
                # Run optimization
                optimized = optimizer.optimize_response(response.copy())
                
                # Calculate output size
                try:
                    benchmark.output_size_bytes = len(json.dumps(optimized, default=str).encode('utf-8'))
                except:
                    benchmark.output_size_bytes = sys.getsizeof(optimized)
                
                benchmark.metadata = {
                    "original_fields": len(response),
                    "optimized_fields": len(optimized),
                    "profile_used": getattr(optimized, '_profile_used', 'unknown')
                }
        
        return self._get_category_summary(BenchmarkCategory.RESPONSE_OPTIMIZATION)
    
    def benchmark_context_selection(
        self,
        field_selector: Any,
        template_manager: Any,
        test_contexts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Benchmark context field selection performance"""
        from fastmcp.task_management.application.services.context_field_selector import FieldSet
        from fastmcp.task_management.application.services.context_template_manager import OperationType
        
        # Test different field sets
        field_sets = [FieldSet.MINIMAL, FieldSet.SUMMARY, FieldSet.DETAIL]
        operations = [OperationType.TASK_GET, OperationType.TASK_LIST, OperationType.TASK_UPDATE]
        
        for context in test_contexts:
            for field_set in field_sets:
                for operation in operations:
                    test_name = f"context_selection_{field_set.value}_{operation.value}"
                    
                    with self.benchmark(
                        test_name,
                        BenchmarkCategory.CONTEXT_SELECTION,
                        context
                    ) as benchmark:
                        
                        # Get template
                        template = template_manager.get_template(operation)
                        
                        # Get minimal context
                        minimal = template_manager.get_minimal_context(operation, context)
                        
                        # Calculate savings
                        try:
                            benchmark.output_size_bytes = len(json.dumps(minimal, default=str).encode('utf-8'))
                        except:
                            benchmark.output_size_bytes = sys.getsizeof(minimal)
                        
                        benchmark.metadata = {
                            "field_set": field_set.value,
                            "operation": operation.value,
                            "template_fields": len(template),
                            "context_types": list(context.keys())
                        }
        
        return self._get_category_summary(BenchmarkCategory.CONTEXT_SELECTION)
    
    def benchmark_cache_performance(
        self,
        cache_optimizer: Any,
        test_data: List[Tuple[str, Any]]
    ) -> Dict[str, Any]:
        """Benchmark cache performance"""
        
        # Warm up cache
        with self.benchmark(
            "cache_warmup",
            BenchmarkCategory.CACHE_PERFORMANCE
        ) as benchmark:
            warmed = 0
            for key, data in test_data[:10]:  # Warm with first 10 items
                if cache_optimizer.put(key, data, "benchmark"):
                    warmed += 1
            
            benchmark.metadata = {"entries_warmed": warmed}
            benchmark.output_size_bytes = warmed
        
        # Test cache hits
        with self.benchmark(
            "cache_hit_performance",
            BenchmarkCategory.CACHE_PERFORMANCE
        ) as benchmark:
            hits = 0
            for key, _ in test_data[:10]:
                if cache_optimizer.get(key, "benchmark"):
                    hits += 1
            
            benchmark.metadata = {"cache_hits": hits}
            benchmark.output_size_bytes = hits
        
        # Test cache misses
        with self.benchmark(
            "cache_miss_performance", 
            BenchmarkCategory.CACHE_PERFORMANCE
        ) as benchmark:
            misses = 0
            for i in range(100, 110):  # Keys that don't exist
                if cache_optimizer.get(f"nonexistent_{i}", "benchmark") is None:
                    misses += 1
            
            benchmark.metadata = {"cache_misses": misses}
        
        # Test cache optimization
        with self.benchmark(
            "cache_optimization",
            BenchmarkCategory.CACHE_PERFORMANCE
        ) as benchmark:
            optimization_result = cache_optimizer.optimize_cache()
            benchmark.metadata = optimization_result
        
        return self._get_category_summary(BenchmarkCategory.CACHE_PERFORMANCE)
    
    def benchmark_end_to_end(
        self,
        optimizer: Any,
        template_manager: Any,
        test_scenarios: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Benchmark complete end-to-end optimization pipeline"""
        
        for i, scenario in enumerate(test_scenarios):
            with self.benchmark(
                f"end_to_end_scenario_{i+1}",
                BenchmarkCategory.END_TO_END,
                scenario
            ) as benchmark:
                
                # Step 1: Get template for operation
                operation = scenario.get('operation', 'task.get')
                try:
                    from fastmcp.task_management.application.services.context_template_manager import OperationType
                    op_enum = OperationType(operation)
                    template = template_manager.get_template(op_enum)
                except:
                    template = {}
                
                # Step 2: Extract minimal context
                context_data = scenario.get('context', {})
                if template and context_data:
                    minimal_context = template_manager.get_minimal_context(op_enum, context_data)
                else:
                    minimal_context = context_data
                
                # Step 3: Create response
                response = {
                    "status": "success",
                    "operation": operation,
                    "data": scenario.get('data', {}),
                    "context": minimal_context,
                    "metadata": scenario.get('metadata', {}),
                    "workflow_guidance": scenario.get('workflow_guidance', {})
                }
                
                # Step 4: Optimize response
                optimized = optimizer.optimize_response(response.copy())
                
                # Calculate metrics
                try:
                    benchmark.output_size_bytes = len(json.dumps(optimized, default=str).encode('utf-8'))
                    original_size = len(json.dumps(response, default=str).encode('utf-8'))
                    
                    benchmark.metadata = {
                        "operation": operation,
                        "original_response_size": original_size,
                        "optimized_response_size": benchmark.output_size_bytes,
                        "compression_achieved": (1 - benchmark.output_size_bytes / original_size) * 100,
                        "context_types_processed": len(minimal_context),
                        "template_fields": len(template)
                    }
                except:
                    benchmark.output_size_bytes = sys.getsizeof(optimized)
        
        return self._get_category_summary(BenchmarkCategory.END_TO_END)
    
    def _get_category_summary(self, category: BenchmarkCategory) -> Dict[str, Any]:
        """Get summary for specific category"""
        if not self.current_suite:
            return {"error": "No active benchmark suite"}
        
        category_results = [
            r for r in self.current_suite.results 
            if r.category == category
        ]
        
        if not category_results:
            return {"error": f"No results for category {category.value}"}
        
        successful = [r for r in category_results if r.success]
        
        if not successful:
            return {"error": f"No successful results for category {category.value}"}
        
        execution_times = [r.execution_time_ms for r in successful]
        compression_ratios = [r.compression_ratio for r in successful if r.input_size_bytes > 0]
        
        summary = {
            "category": category.value,
            "total_tests": len(category_results),
            "successful_tests": len(successful),
            "success_rate_percent": (len(successful) / len(category_results)) * 100,
            "avg_execution_time_ms": statistics.mean(execution_times),
            "median_execution_time_ms": statistics.median(execution_times),
            "total_execution_time_ms": sum(execution_times)
        }
        
        if compression_ratios:
            summary.update({
                "avg_compression_ratio_percent": statistics.mean(compression_ratios),
                "median_compression_ratio_percent": statistics.median(compression_ratios),
                "max_compression_ratio_percent": max(compression_ratios)
            })
        
        return summary
    
    def generate_report(
        self,
        suite: Optional[BenchmarkSuite] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive benchmark report"""
        target_suite = suite or self.current_suite
        
        if not target_suite:
            return {"error": "No benchmark suite available"}
        
        report = {
            "suite_name": target_suite.suite_name,
            "started_at": target_suite.started_at.isoformat(),
            "completed_at": target_suite.completed_at.isoformat() if target_suite.completed_at else None,
            "summary": target_suite.get_summary(),
            "category_summaries": {},
            "performance_comparison": self._compare_with_baseline(),
            "recommendations": self._generate_recommendations(target_suite)
        }
        
        # Add category summaries
        categories = set(r.category for r in target_suite.results)
        for category in categories:
            report["category_summaries"][category.value] = self._get_category_summary(category)
        
        return report
    
    def _compare_with_baseline(self) -> Dict[str, Any]:
        """Compare current results with baseline performance"""
        # Define baseline metrics (before optimization)
        baseline = {
            "response_processing_ms": 100,  # 100ms baseline
            "response_size_bytes": 5000,    # 5KB baseline
            "compression_ratio_percent": 0,  # No compression baseline
            "cache_hit_rate_percent": 0      # No cache baseline
        }
        
        if not self.current_suite or not self.current_suite.results:
            return {"error": "No current results to compare"}
        
        successful_results = [r for r in self.current_suite.results if r.success]
        
        if not successful_results:
            return {"error": "No successful results to compare"}
        
        # Calculate current metrics
        avg_execution_time = statistics.mean([r.execution_time_ms for r in successful_results])
        avg_output_size = statistics.mean([r.output_size_bytes for r in successful_results])
        compression_ratios = [r.compression_ratio for r in successful_results if r.input_size_bytes > 0]
        avg_compression = statistics.mean(compression_ratios) if compression_ratios else 0
        
        # Calculate improvements
        return {
            "baseline_metrics": baseline,
            "current_metrics": {
                "avg_execution_time_ms": avg_execution_time,
                "avg_output_size_bytes": avg_output_size,
                "avg_compression_ratio_percent": avg_compression
            },
            "improvements": {
                "execution_time_improvement_percent": max(0, (baseline["response_processing_ms"] - avg_execution_time) / baseline["response_processing_ms"] * 100),
                "size_reduction_percent": max(0, (baseline["response_size_bytes"] - avg_output_size) / baseline["response_size_bytes"] * 100),
                "compression_achievement_percent": avg_compression
            }
        }
    
    def _generate_recommendations(
        self,
        suite: BenchmarkSuite
    ) -> List[str]:
        """Generate optimization recommendations based on results"""
        recommendations = []
        
        successful_results = [r for r in suite.results if r.success]
        
        if not successful_results:
            return ["No successful benchmarks to analyze"]
        
        # Analyze execution times
        execution_times = [r.execution_time_ms for r in successful_results]
        avg_time = statistics.mean(execution_times)
        max_time = max(execution_times)
        
        if avg_time > 50:
            recommendations.append("Consider optimizing response processing - average time exceeds 50ms")
        
        if max_time > 200:
            recommendations.append("Some operations are very slow (>200ms) - investigate bottlenecks")
        
        # Analyze compression ratios
        compression_ratios = [r.compression_ratio for r in successful_results if r.input_size_bytes > 0]
        if compression_ratios:
            avg_compression = statistics.mean(compression_ratios)
            
            if avg_compression < 50:
                recommendations.append("Compression ratio below 50% - review optimization strategies")
            elif avg_compression > 80:
                recommendations.append("Excellent compression ratio achieved - current optimization is effective")
        
        # Analyze memory usage
        memory_usage = [r.memory_usage_mb for r in successful_results if r.memory_usage_mb > 0]
        if memory_usage:
            avg_memory = statistics.mean(memory_usage)
            if avg_memory > 10:
                recommendations.append("High memory usage detected - consider memory optimization")
        
        # Category-specific recommendations
        categories = set(r.category for r in successful_results)
        
        if BenchmarkCategory.CACHE_PERFORMANCE in categories:
            cache_results = [r for r in successful_results if r.category == BenchmarkCategory.CACHE_PERFORMANCE]
            cache_times = [r.execution_time_ms for r in cache_results]
            avg_cache_time = statistics.mean(cache_times)
            
            if avg_cache_time > 10:
                recommendations.append("Cache operations are slow - consider cache optimization")
        
        return recommendations if recommendations else ["Performance looks good - no specific recommendations"]