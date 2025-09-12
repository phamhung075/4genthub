"""
Comprehensive Performance Benchmark Suite - Phase 4

Integrates all performance benchmarks including response size reduction,
AI comprehension testing, load testing, and existing performance validations
to provide complete Phase 4 optimization validation.
"""

import asyncio
import time
import json
import statistics
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

# Import all benchmark components
from .. import PERFORMANCE_CONFIG, setup_performance_logger
from .performance_suite import PerformanceSuite, BenchmarkResult, PerformanceMetric
from .response_size_tests import ResponseSizeBenchmark
from .ai_comprehension_tests import AIComprehensionBenchmark
from .load_testing_suite import LoadTestingBenchmark
from fastmcp.task_management.infrastructure.monitoring.metrics_collector import MetricsCollector, start_global_collection, stop_global_collection

logger = setup_performance_logger()


class Phase4ComprehensiveBenchmarkSuite:
    """Complete Phase 4 performance benchmark suite."""
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path(__file__).parent / "results" / "phase4"
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # Initialize all benchmark components
        self.response_size_benchmark = ResponseSizeBenchmark()
        self.ai_comprehension_benchmark = AIComprehensionBenchmark()
        self.load_testing_benchmark = LoadTestingBenchmark()
        
        # Original benchmarks from existing suite
        self.original_suite = PerformanceSuite(self.output_dir)
        
        # Metrics collector for comprehensive monitoring
        self.metrics_collector = MetricsCollector(output_directory=self.output_dir)
        
        # Phase 4 performance targets
        self.phase4_targets = {
            "response_size_reduction": PERFORMANCE_CONFIG["response_size_targets"]["min_reduction_percent"],
            "ai_processing_improvement": PERFORMANCE_CONFIG["ai_comprehension_targets"]["speed_improvement"],
            "context_injection_time": PERFORMANCE_CONFIG["response_time_targets"]["context_injection"],
            "cache_hit_rate": PERFORMANCE_CONFIG["cache_hit_rate_target"],
            "load_test_success_rate": 95.0,
            "memory_usage_limit": PERFORMANCE_CONFIG["load_testing"]["memory_usage_limit_mb"],
            "cpu_usage_limit": PERFORMANCE_CONFIG["load_testing"]["cpu_usage_limit_percent"]
        }
    
    async def run_comprehensive_benchmarks(self) -> Dict[str, Any]:
        """Run all Phase 4 benchmarks and return comprehensive results."""
        logger.info("=== Starting Phase 4 Comprehensive Performance Benchmark Suite ===")
        suite_start = time.perf_counter()
        
        # Start metrics collection
        await start_global_collection()
        
        all_results = {}
        benchmark_summaries = []
        overall_metrics = []
        
        try:
            # 1. Response Size Reduction Benchmarks
            logger.info("\n--- Phase 4.1: Response Size Reduction Benchmarks ---")
            response_size_result = await self._run_response_size_benchmarks()
            all_results["response_size_reduction"] = response_size_result
            benchmark_summaries.append(self._create_benchmark_summary("Response Size Reduction", response_size_result))
            
            # 2. AI Comprehension & Processing Speed Benchmarks  
            logger.info("\n--- Phase 4.2: AI Comprehension & Processing Speed Benchmarks ---")
            ai_comprehension_result = await self._run_ai_comprehension_benchmarks()
            all_results["ai_comprehension"] = ai_comprehension_result
            benchmark_summaries.append(self._create_benchmark_summary("AI Comprehension", ai_comprehension_result))
            
            # 3. Load Testing & Concurrent Request Handling
            logger.info("\n--- Phase 4.3: Load Testing & Concurrent Request Handling ---")
            load_testing_result = await self._run_load_testing_benchmarks()
            all_results["load_testing"] = load_testing_result
            benchmark_summaries.append(self._create_benchmark_summary("Load Testing", load_testing_result))
            
            # 4. Original Performance Validation (40% improvement target)
            logger.info("\n--- Phase 4.4: Original Performance Validation Benchmarks ---")
            original_results = await self.original_suite.run_all_benchmarks()
            all_results["original_benchmarks"] = [result.to_dict() for result in original_results]
            
            for result in original_results:
                benchmark_summaries.append(self._create_benchmark_summary(result.benchmark_name, result))
            
            # 5. Calculate Overall Phase 4 Results
            logger.info("\n--- Phase 4.5: Overall Results Analysis ---")
            phase4_analysis = self._analyze_phase4_results(all_results)
            all_results["phase4_analysis"] = phase4_analysis
            
            suite_end = time.perf_counter()
            suite_duration = suite_end - suite_start
            
            # Create comprehensive report
            comprehensive_report = self._generate_comprehensive_report(
                all_results, 
                benchmark_summaries, 
                suite_duration
            )
            
            # Save all results
            await self._save_comprehensive_results(all_results, comprehensive_report)
            
            logger.info(f"=== Phase 4 Comprehensive Benchmark Suite Completed in {suite_duration:.2f}s ===")
            
            return {
                "results": all_results,
                "report": comprehensive_report,
                "suite_duration": suite_duration,
                "phase4_targets_met": phase4_analysis["overall_targets_met"],
                "summary": phase4_analysis["summary"]
            }
        
        finally:
            await stop_global_collection()
    
    async def _run_response_size_benchmarks(self) -> BenchmarkResult:
        """Run response size reduction benchmarks."""
        try:
            await self.response_size_benchmark.setup()
            result = await self.response_size_benchmark.run_benchmark()
            await self.response_size_benchmark.teardown()
            
            # Log key results
            avg_reduction_metric = result.get_metric("avg_size_reduction")
            if avg_reduction_metric:
                logger.info(f"  Average response size reduction: {avg_reduction_metric.value:.1f}%")
                logger.info(f"  Target met: {'✅ Yes' if avg_reduction_metric.meets_target else '❌ No'}")
            
            return result
        except Exception as e:
            logger.error(f"Response size benchmark failed: {str(e)}")
            return self._create_error_result("Response Size Reduction", str(e))
    
    async def _run_ai_comprehension_benchmarks(self) -> BenchmarkResult:
        """Run AI comprehension and processing speed benchmarks."""
        try:
            await self.ai_comprehension_benchmark.setup()
            result = await self.ai_comprehension_benchmark.run_benchmark()
            await self.ai_comprehension_benchmark.teardown()
            
            # Log key results
            speed_improvement_metric = result.get_metric("overall_speed_improvement")
            accuracy_retention_metric = result.get_metric("accuracy_retention")
            
            if speed_improvement_metric:
                logger.info(f"  AI processing speed improvement: {speed_improvement_metric.value:.1f}%")
                logger.info(f"  Target met: {'✅ Yes' if speed_improvement_metric.meets_target else '❌ No'}")
            
            if accuracy_retention_metric:
                logger.info(f"  AI comprehension accuracy retention: {accuracy_retention_metric.value:.1f}%")
                logger.info(f"  Target met: {'✅ Yes' if accuracy_retention_metric.meets_target else '❌ No'}")
            
            return result
        except Exception as e:
            logger.error(f"AI comprehension benchmark failed: {str(e)}")
            return self._create_error_result("AI Comprehension", str(e))
    
    async def _run_load_testing_benchmarks(self) -> BenchmarkResult:
        """Run load testing and concurrent request handling benchmarks."""
        try:
            await self.load_testing_benchmark.setup()
            result = await self.load_testing_benchmark.run_benchmark()
            await self.load_testing_benchmark.teardown()
            
            # Log key results
            success_rate_metric = result.get_metric("overall_success_rate")
            response_time_metric = result.get_metric("overall_avg_response_time")
            memory_metric = result.get_metric("max_memory_usage")
            
            if success_rate_metric:
                logger.info(f"  Load test success rate: {success_rate_metric.value:.1f}%")
                logger.info(f"  Target met: {'✅ Yes' if success_rate_metric.meets_target else '❌ No'}")
            
            if response_time_metric:
                logger.info(f"  Average response time under load: {response_time_metric.value:.1f}ms")
            
            if memory_metric:
                logger.info(f"  Peak memory usage: {memory_metric.value:.1f}MB")
                logger.info(f"  Memory limit met: {'✅ Yes' if memory_metric.meets_target else '❌ No'}")
            
            return result
        except Exception as e:
            logger.error(f"Load testing benchmark failed: {str(e)}")
            return self._create_error_result("Load Testing", str(e))
    
    def _create_error_result(self, benchmark_name: str, error_message: str) -> BenchmarkResult:
        """Create error result for failed benchmark."""
        return BenchmarkResult(
            benchmark_name=benchmark_name,
            metrics=[],
            success_rate=0.0,
            execution_time=0.0,
            resource_usage={},
            error_details=[f"Benchmark failed: {error_message}"]
        )
    
    def _create_benchmark_summary(self, name: str, result: BenchmarkResult) -> Dict[str, Any]:
        """Create summary for a benchmark result."""
        return {
            "name": name,
            "success_rate": result.success_rate,
            "execution_time": result.execution_time,
            "all_targets_met": result.all_targets_met,
            "error_count": len(result.error_details),
            "metric_count": len(result.metrics),
            "key_metrics": self._extract_key_metrics(result)
        }
    
    def _extract_key_metrics(self, result: BenchmarkResult) -> Dict[str, Any]:
        """Extract key metrics from benchmark result."""
        key_metrics = {}
        
        for metric in result.metrics:
            if metric.category in ["overall", "improvement", "reduction"]:
                key_metrics[metric.name] = {
                    "value": metric.value,
                    "unit": metric.unit,
                    "target": metric.target,
                    "meets_target": metric.meets_target
                }
        
        return key_metrics
    
    def _analyze_phase4_results(self, all_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze overall Phase 4 results against targets."""
        analysis = {
            "target_analysis": {},
            "overall_targets_met": True,
            "targets_met_count": 0,
            "total_targets": 0,
            "summary": "",
            "recommendations": []
        }
        
        # Analyze each target
        targets = [
            ("response_size_reduction", "Response Size Reduction (≥50%)", "response_size_reduction", "avg_size_reduction"),
            ("ai_processing_improvement", "AI Processing Speed Improvement (≥40%)", "ai_comprehension", "overall_speed_improvement"),
            ("load_test_success_rate", "Load Test Success Rate (≥95%)", "load_testing", "overall_success_rate"),
            ("memory_usage", "Memory Usage Limit", "load_testing", "max_memory_usage"),
            ("cpu_usage", "CPU Usage Limit", "load_testing", "max_cpu_usage")
        ]
        
        for target_key, target_description, result_key, metric_name in targets:
            analysis["total_targets"] += 1
            target_met = False
            target_value = None
            
            try:
                if result_key in all_results and hasattr(all_results[result_key], 'get_metric'):
                    metric = all_results[result_key].get_metric(metric_name)
                    if metric:
                        target_met = metric.meets_target
                        target_value = metric.value
                elif result_key in all_results and isinstance(all_results[result_key], dict):
                    # Handle dict results
                    if "metrics" in all_results[result_key]:
                        for metric_dict in all_results[result_key]["metrics"]:
                            if metric_dict.get("name") == metric_name:
                                target_met = metric_dict.get("meets_target", False)
                                target_value = metric_dict.get("value")
                                break
            except Exception as e:
                logger.warning(f"Could not analyze target {target_key}: {str(e)}")
            
            analysis["target_analysis"][target_key] = {
                "description": target_description,
                "met": target_met,
                "value": target_value
            }
            
            if target_met:
                analysis["targets_met_count"] += 1
            else:
                analysis["overall_targets_met"] = False
        
        # Create summary
        success_rate = (analysis["targets_met_count"] / analysis["total_targets"]) * 100 if analysis["total_targets"] > 0 else 0
        
        if analysis["overall_targets_met"]:
            analysis["summary"] = f"🎉 All Phase 4 performance targets achieved! ({analysis['targets_met_count']}/{analysis['total_targets']} targets met)"
        elif success_rate >= 80:
            analysis["summary"] = f"⚠️ Most Phase 4 targets met with areas for improvement ({analysis['targets_met_count']}/{analysis['total_targets']} targets met, {success_rate:.0f}%)"
        else:
            analysis["summary"] = f"🚨 Phase 4 targets not met - optimization required ({analysis['targets_met_count']}/{analysis['total_targets']} targets met, {success_rate:.0f}%)"
        
        # Generate recommendations
        if not analysis["overall_targets_met"]:
            for target_key, target_data in analysis["target_analysis"].items():
                if not target_data["met"]:
                    if "response_size" in target_key:
                        analysis["recommendations"].append("Consider additional response payload optimization and data compression")
                    elif "ai_processing" in target_key:
                        analysis["recommendations"].append("Optimize AI processing pipelines and implement better caching strategies")
                    elif "load_test" in target_key:
                        analysis["recommendations"].append("Improve system stability and error handling under load")
                    elif "memory" in target_key:
                        analysis["recommendations"].append("Optimize memory usage and implement better resource management")
                    elif "cpu" in target_key:
                        analysis["recommendations"].append("Optimize CPU-intensive operations and improve algorithmic efficiency")
        
        return analysis
    
    def _generate_comprehensive_report(self, 
                                     all_results: Dict[str, Any], 
                                     benchmark_summaries: List[Dict[str, Any]],
                                     suite_duration: float) -> str:
        """Generate comprehensive Phase 4 performance report."""
        report_lines = []
        
        # Header
        report_lines.extend([
            "# Phase 4 Comprehensive Performance Validation Report",
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"Suite Duration: {suite_duration:.2f} seconds",
            ""
        ])
        
        # Executive Summary
        phase4_analysis = all_results.get("phase4_analysis", {})
        report_lines.extend([
            "## Executive Summary",
            phase4_analysis.get("summary", "Analysis not available"),
            ""
        ])
        
        if phase4_analysis.get("targets_met_count") is not None:
            targets_met = phase4_analysis["targets_met_count"]
            total_targets = phase4_analysis["total_targets"]
            success_percentage = (targets_met / total_targets) * 100 if total_targets > 0 else 0
            
            report_lines.extend([
                f"- **Performance Targets Met**: {targets_met}/{total_targets} ({success_percentage:.0f}%)",
                f"- **Overall Success**: {'✅ PASSED' if phase4_analysis.get('overall_targets_met') else '❌ FAILED'}",
                ""
            ])
        
        # Phase 4 Targets Analysis
        report_lines.append("## Phase 4 Target Analysis")
        target_analysis = phase4_analysis.get("target_analysis", {})
        
        for target_key, target_data in target_analysis.items():
            status = "✅ MET" if target_data["met"] else "❌ NOT MET"
            value_text = f" (achieved: {target_data['value']:.1f})" if target_data["value"] is not None else ""
            report_lines.append(f"- **{target_data['description']}**: {status}{value_text}")
        
        report_lines.append("")
        
        # Benchmark Results Summary
        report_lines.append("## Benchmark Results Summary")
        
        for summary in benchmark_summaries:
            report_lines.extend([
                f"### {summary['name']}",
                f"- Success Rate: {summary['success_rate']:.2%}",
                f"- Execution Time: {summary['execution_time']:.2f}s",
                f"- All Targets Met: {'✅ Yes' if summary['all_targets_met'] else '❌ No'}",
                f"- Metrics Collected: {summary['metric_count']}",
                f"- Errors: {summary['error_count']}",
                ""
            ])
            
            # Key metrics
            if summary.get("key_metrics"):
                report_lines.append("#### Key Metrics:")
                for metric_name, metric_data in summary["key_metrics"].items():
                    status = "✅" if metric_data["meets_target"] else "❌"
                    target_text = f" (target: {metric_data['target']})" if metric_data["target"] else ""
                    report_lines.append(f"  - {metric_name}: {metric_data['value']:.2f}{metric_data['unit']}{target_text} {status}")
                report_lines.append("")
        
        # Recommendations
        recommendations = phase4_analysis.get("recommendations", [])
        if recommendations:
            report_lines.append("## Recommendations")
            for i, recommendation in enumerate(recommendations, 1):
                report_lines.append(f"{i}. {recommendation}")
            report_lines.append("")
        
        # Performance Targets Reference
        report_lines.extend([
            "## Phase 4 Performance Targets Reference",
            f"- **Response Size Reduction**: {self.phase4_targets['response_size_reduction']}% minimum",
            f"- **AI Processing Improvement**: {self.phase4_targets['ai_processing_improvement']*100}% faster",
            f"- **Context Injection Time**: ≤{self.phase4_targets['context_injection_time']*1000}ms",
            f"- **Cache Hit Rate**: ≥{self.phase4_targets['cache_hit_rate']*100}%",
            f"- **Load Test Success Rate**: ≥{self.phase4_targets['load_test_success_rate']}%",
            f"- **Memory Usage Limit**: ≤{self.phase4_targets['memory_usage_limit']}MB",
            f"- **CPU Usage Limit**: ≤{self.phase4_targets['cpu_usage_limit']}%",
            ""
        ])
        
        # Conclusion
        if phase4_analysis.get("overall_targets_met"):
            report_lines.extend([
                "## Conclusion",
                "🎉 **Phase 4 optimization successfully achieved all performance targets!**",
                "The system demonstrates significant improvements in response size reduction,",
                "AI processing speed, and system stability under load. Ready for production deployment.",
                ""
            ])
        else:
            report_lines.extend([
                "## Conclusion", 
                "⚠️ **Phase 4 optimization requires additional work to meet all targets.**",
                "While some improvements have been achieved, further optimization is needed",
                "in specific areas before production deployment. See recommendations above.",
                ""
            ])
        
        return "\n".join(report_lines)
    
    async def _save_comprehensive_results(self, all_results: Dict[str, Any], report: str):
        """Save comprehensive results to files."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON results
        results_file = self.output_dir / f"phase4_comprehensive_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(all_results, f, indent=2, default=str)
        
        # Save markdown report
        report_file = self.output_dir / f"phase4_comprehensive_report_{timestamp}.md"
        with open(report_file, 'w') as f:
            f.write(report)
        
        # Save metrics from global collector
        metrics_report = self.metrics_collector.generate_performance_report(1)  # Last hour
        metrics_file = self.output_dir / f"phase4_metrics_report_{timestamp}.json"
        with open(metrics_file, 'w') as f:
            json.dump(metrics_report, f, indent=2, default=str)
        
        logger.info(f"Phase 4 comprehensive results saved:")
        logger.info(f"  Results: {results_file}")
        logger.info(f"  Report: {report_file}")
        logger.info(f"  Metrics: {metrics_file}")


async def run_phase4_comprehensive_validation():
    """Run the complete Phase 4 comprehensive performance validation."""
    suite = Phase4ComprehensiveBenchmarkSuite()
    results = await suite.run_comprehensive_benchmarks()
    
    # Print summary to console
    print("\n" + "="*80)
    print("PHASE 4 COMPREHENSIVE PERFORMANCE VALIDATION RESULTS")
    print("="*80)
    
    phase4_analysis = results["results"].get("phase4_analysis", {})
    print(phase4_analysis.get("summary", "Analysis not available"))
    print("")
    
    if "target_analysis" in phase4_analysis:
        print("Performance Targets:")
        for target_data in phase4_analysis["target_analysis"].values():
            status = "✅ MET" if target_data["met"] else "❌ NOT MET"
            value_text = f" ({target_data['value']:.1f})" if target_data["value"] is not None else ""
            print(f"  {target_data['description']}: {status}{value_text}")
    
    print("")
    print(f"Suite Duration: {results['suite_duration']:.2f} seconds")
    print(f"Phase 4 Targets Met: {'✅ YES' if results['phase4_targets_met'] else '❌ NO'}")
    print("="*80)
    
    return results


if __name__ == "__main__":
    # Run the Phase 4 comprehensive performance validation
    asyncio.run(run_phase4_comprehensive_validation())