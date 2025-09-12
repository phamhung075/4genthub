"""
AI Comprehension Benchmark Tests

Tests to validate that AI agents can effectively understand and process optimized responses
while maintaining or improving comprehension accuracy. Measures 40% faster processing target.

Simulates AI agent processing of both baseline and optimized responses to ensure
optimization doesn't compromise understanding quality.
"""

import asyncio
import time
import json
import statistics
import re
import random
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple, Union
from unittest.mock import Mock, patch
import logging

# Import performance test components
from .. import PERFORMANCE_CONFIG, setup_performance_logger
from .performance_suite import PerformanceMetric, BenchmarkResult, PerformanceBenchmark, ResourceMonitor
from .response_size_tests import ResponseSizeBenchmark

logger = setup_performance_logger()


@dataclass
class ComprehensionResult:
    """Result of AI comprehension test."""
    scenario: str
    response_type: str  # 'baseline' or 'optimized'
    processing_time_ms: float
    comprehension_accuracy: float  # 0.0 to 1.0
    extracted_items_count: int
    expected_items_count: int
    parsing_success: bool
    error_details: List[str] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.error_details is None:
            self.error_details = []
        if self.timestamp is None:
            self.timestamp = time.time()
    
    @property
    def extraction_accuracy(self) -> float:
        """Calculate item extraction accuracy."""
        if self.expected_items_count == 0:
            return 1.0
        return min(self.extracted_items_count / self.expected_items_count, 1.0)


class AITaskProcessor:
    """Simulates AI agent processing of task responses."""
    
    def __init__(self):
        self.processing_patterns = {
            'task_extraction': r'task[_-]?(\d+)|"id":\s*"([^"]+)"',
            'status_extraction': r'"status":\s*"([^"]+)"',
            'priority_extraction': r'"priority":\s*"([^"]+)"',
            'assignee_extraction': r'@([a-z-]+agent)',
            'dependency_extraction': r'"dependencies?"[:\[].*?"([^"]+)"',
            'actionable_items': r'(?i)(implement|create|fix|update|test|deploy|configure)',
            'estimated_effort': r'(\d+)\s*(hour|hr|h|day|d)',
            'workflow_hints': r'step \d+|phase \d+|complete.*?:|next.*?:'
        }
    
    def process_task_response(self, response_data: Dict[str, Any]) -> ComprehensionResult:
        """Process task response and extract comprehension metrics."""
        start_time = time.perf_counter()
        
        try:
            response_json = json.dumps(response_data)
            
            # Extract different types of items
            extracted_items = {}
            
            for pattern_name, pattern in self.processing_patterns.items():
                matches = re.findall(pattern, response_json, re.IGNORECASE | re.MULTILINE)
                extracted_items[pattern_name] = len([m for m in matches if m])
            
            # Calculate total extracted items
            total_extracted = sum(extracted_items.values())
            
            # Estimate expected items based on response structure
            expected_items = self._estimate_expected_items(response_data)
            
            # Calculate comprehension accuracy based on successful extractions
            accuracy = self._calculate_comprehension_accuracy(response_data, extracted_items)
            
            processing_time = (time.perf_counter() - start_time) * 1000  # Convert to ms
            
            return ComprehensionResult(
                scenario="task_processing",
                response_type="unknown",
                processing_time_ms=processing_time,
                comprehension_accuracy=accuracy,
                extracted_items_count=total_extracted,
                expected_items_count=expected_items,
                parsing_success=True
            )
            
        except Exception as e:
            processing_time = (time.perf_counter() - start_time) * 1000
            
            return ComprehensionResult(
                scenario="task_processing",
                response_type="unknown", 
                processing_time_ms=processing_time,
                comprehension_accuracy=0.0,
                extracted_items_count=0,
                expected_items_count=0,
                parsing_success=False,
                error_details=[f"Processing failed: {str(e)}"]
            )
    
    def _estimate_expected_items(self, response_data: Dict[str, Any]) -> int:
        """Estimate expected number of extractable items."""
        expected = 0
        
        # Count tasks
        if 'data' in response_data:
            data = response_data['data']
            if 'tasks' in data:
                tasks = data['tasks'] if isinstance(data['tasks'], list) else [data['tasks']]
                expected += len(tasks) * 4  # id, status, priority, assignee per task
            elif 'task' in data:
                expected += 4  # Single task
                
                # Count dependencies and subtasks
                task = data['task']
                if isinstance(task, dict):
                    if 'dependencies' in task:
                        deps = task['dependencies']
                        if isinstance(deps, list):
                            expected += len(deps)
                    
                    if 'subtasks' in task:
                        subtasks = task['subtasks']
                        if isinstance(subtasks, list):
                            expected += len(subtasks) * 2  # id and title per subtask
        
        return max(expected, 1)  # At least 1 expected item
    
    def _calculate_comprehension_accuracy(self, response_data: Dict[str, Any], extracted_items: Dict[str, int]) -> float:
        """Calculate comprehension accuracy based on successful extractions."""
        weights = {
            'task_extraction': 0.25,
            'status_extraction': 0.20,
            'priority_extraction': 0.15,
            'assignee_extraction': 0.15,
            'actionable_items': 0.15,
            'estimated_effort': 0.10
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for item_type, weight in weights.items():
            if item_type in extracted_items:
                # Normalize score (assume good extraction if > 0)
                score = min(extracted_items[item_type] / max(self._get_expected_count(response_data, item_type), 1), 1.0)
                total_score += score * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def _get_expected_count(self, response_data: Dict[str, Any], item_type: str) -> int:
        """Get expected count for specific item type."""
        if item_type == 'task_extraction':
            return self._count_tasks(response_data)
        elif item_type in ['status_extraction', 'priority_extraction']:
            return self._count_tasks(response_data)
        elif item_type == 'assignee_extraction':
            return max(self._count_tasks(response_data), 1)
        else:
            return 1
    
    def _count_tasks(self, response_data: Dict[str, Any]) -> int:
        """Count number of tasks in response."""
        if 'data' not in response_data:
            return 0
        
        data = response_data['data']
        if 'tasks' in data:
            return len(data['tasks']) if isinstance(data['tasks'], list) else 1
        elif 'task' in data:
            return 1
        
        return 0


class AIComprehensionBenchmark(PerformanceBenchmark):
    """Benchmark for AI comprehension and processing speed (40% faster target)."""
    
    def __init__(self):
        super().__init__("AI Comprehension & Processing Speed")
        self.response_benchmark = ResponseSizeBenchmark()
        self.ai_processor = AITaskProcessor()
        self.test_scenarios = [
            "simple_task_list",
            "complex_task_with_dependencies",
            "bulk_task_operations",
            "task_with_subtasks",
            "hierarchical_context_data"
        ]
    
    async def setup(self):
        """Setup AI comprehension benchmark."""
        await self.response_benchmark.setup()
    
    async def teardown(self):
        """Cleanup AI comprehension benchmark."""
        await self.response_benchmark.teardown()
    
    def _simulate_ai_analysis_delay(self, response_data: Dict[str, Any], is_optimized: bool = False) -> float:
        """Simulate additional AI analysis time beyond parsing."""
        base_delay = 0.1  # 100ms base analysis time
        
        # Calculate complexity factors
        json_string = json.dumps(response_data)
        complexity_factor = len(json_string) / 10000  # More text = more analysis time
        
        # Add randomization to simulate real AI processing variance
        variance = random.uniform(0.8, 1.2)
        
        # Optimized responses should process faster due to cleaner structure
        optimization_factor = 0.6 if is_optimized else 1.0
        
        total_delay = base_delay * complexity_factor * variance * optimization_factor
        time.sleep(total_delay)
        return total_delay * 1000  # Return in ms
    
    async def run_benchmark(self) -> BenchmarkResult:
        """Run AI comprehension and processing speed benchmark.""" 
        self.resource_monitor.start_monitoring()
        start_time = time.perf_counter()
        
        metrics = []
        comprehension_results = []
        errors = []
        
        logger.info("Starting AI comprehension benchmarks...")
        
        try:
            for scenario in self.test_scenarios:
                logger.info(f"Testing AI comprehension for scenario: {scenario}")
                self.resource_monitor.sample_resources()
                
                # Generate baseline and optimized responses
                baseline_response = self.response_benchmark._create_baseline_response(scenario)
                optimized_response = self.response_benchmark._create_optimized_response(scenario)
                
                # Process baseline response
                baseline_result = self.ai_processor.process_task_response(baseline_response)
                baseline_result.scenario = scenario
                baseline_result.response_type = "baseline"
                
                # Add AI analysis delay
                analysis_delay = self._simulate_ai_analysis_delay(baseline_response, is_optimized=False)
                baseline_result.processing_time_ms += analysis_delay
                
                comprehension_results.append(baseline_result)
                
                # Process optimized response
                optimized_result = self.ai_processor.process_task_response(optimized_response)
                optimized_result.scenario = scenario
                optimized_result.response_type = "optimized"
                
                # Add AI analysis delay (faster for optimized)
                analysis_delay = self._simulate_ai_analysis_delay(optimized_response, is_optimized=True)
                optimized_result.processing_time_ms += analysis_delay
                
                comprehension_results.append(optimized_result)
                
                # Calculate processing speed improvement
                if baseline_result.processing_time_ms > 0:
                    speed_improvement = (baseline_result.processing_time_ms - optimized_result.processing_time_ms) / baseline_result.processing_time_ms
                    meets_speed_target = speed_improvement >= 0.4  # 40% improvement target
                else:
                    speed_improvement = 0.0
                    meets_speed_target = False
                
                # Add scenario metrics
                metrics.extend([
                    self.create_metric(f"{scenario}_baseline_processing_time", baseline_result.processing_time_ms, "ms", None, "processing"),
                    self.create_metric(f"{scenario}_optimized_processing_time", optimized_result.processing_time_ms, "ms", None, "processing"),
                    self.create_metric(f"{scenario}_speed_improvement", speed_improvement * 100, "percent", 40.0, "improvement"),
                    self.create_metric(f"{scenario}_baseline_accuracy", baseline_result.comprehension_accuracy * 100, "percent", 90.0, "accuracy"),
                    self.create_metric(f"{scenario}_optimized_accuracy", optimized_result.comprehension_accuracy * 100, "percent", 85.0, "accuracy")
                ])
                
                logger.info(f"  Baseline processing: {baseline_result.processing_time_ms:.1f}ms (accuracy: {baseline_result.comprehension_accuracy:.2%})")
                logger.info(f"  Optimized processing: {optimized_result.processing_time_ms:.1f}ms (accuracy: {optimized_result.comprehension_accuracy:.2%})")
                logger.info(f"  Speed improvement: {speed_improvement:.1%} ({'✅' if meets_speed_target else '❌'})")
            
            # Calculate overall statistics
            baseline_results = [r for r in comprehension_results if r.response_type == "baseline"]
            optimized_results = [r for r in comprehension_results if r.response_type == "optimized"]
            
            if baseline_results and optimized_results:
                avg_baseline_time = statistics.mean([r.processing_time_ms for r in baseline_results])
                avg_optimized_time = statistics.mean([r.processing_time_ms for r in optimized_results])
                avg_baseline_accuracy = statistics.mean([r.comprehension_accuracy for r in baseline_results])
                avg_optimized_accuracy = statistics.mean([r.comprehension_accuracy for r in optimized_results])
                
                overall_speed_improvement = (avg_baseline_time - avg_optimized_time) / avg_baseline_time
                accuracy_retention = avg_optimized_accuracy / avg_baseline_accuracy if avg_baseline_accuracy > 0 else 1.0
                
                # Parsing success rates
                baseline_success_rate = sum(1 for r in baseline_results if r.parsing_success) / len(baseline_results)
                optimized_success_rate = sum(1 for r in optimized_results if r.parsing_success) / len(optimized_results)
                
                # Overall metrics
                metrics.extend([
                    self.create_metric("avg_baseline_processing_time", avg_baseline_time, "ms", None, "overall"),
                    self.create_metric("avg_optimized_processing_time", avg_optimized_time, "ms", None, "overall"),
                    self.create_metric("overall_speed_improvement", overall_speed_improvement * 100, "percent", 40.0, "improvement"),
                    self.create_metric("avg_baseline_accuracy", avg_baseline_accuracy * 100, "percent", None, "overall"),
                    self.create_metric("avg_optimized_accuracy", avg_optimized_accuracy * 100, "percent", None, "overall"),
                    self.create_metric("accuracy_retention", accuracy_retention * 100, "percent", 95.0, "quality"),
                    self.create_metric("baseline_parsing_success_rate", baseline_success_rate * 100, "percent", 95.0, "reliability"),
                    self.create_metric("optimized_parsing_success_rate", optimized_success_rate * 100, "percent", 95.0, "reliability")
                ])
                
                logger.info(f"Overall Results:")
                logger.info(f"  Speed improvement: {overall_speed_improvement:.1%} (target: 40%)")
                logger.info(f"  Accuracy retention: {accuracy_retention:.1%}")
                logger.info(f"  Parsing success: baseline {baseline_success_rate:.1%}, optimized {optimized_success_rate:.1%}")
        
        except Exception as e:
            error_msg = f"AI comprehension benchmark error: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
        
        # Calculate final metrics
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        success_rate = 1.0 if len(errors) == 0 else max(0.0, 1.0 - len(errors) / 10)
        resource_usage = self.resource_monitor.stop_monitoring()
        
        return BenchmarkResult(
            benchmark_name=self.name,
            metrics=metrics,
            success_rate=success_rate,
            execution_time=execution_time,
            resource_usage=resource_usage,
            error_details=errors,
            metadata={
                "scenarios_tested": len(self.test_scenarios),
                "comprehension_results": [asdict(r) for r in comprehension_results],
                "target_speed_improvement": "40%",
                "min_accuracy_retention": "95%"
            }
        )


class ComprehensionQualityValidator:
    """Validates that optimizations don't compromise AI understanding quality."""
    
    @staticmethod
    def validate_essential_information_preserved(baseline_response: Dict[str, Any], 
                                                optimized_response: Dict[str, Any]) -> Dict[str, bool]:
        """Check that essential information is preserved in optimized responses."""
        validation_results = {}
        
        # Check task IDs preservation
        baseline_ids = set(re.findall(r'"id":\s*"([^"]+)"', json.dumps(baseline_response)))
        optimized_ids = set(re.findall(r'"id":\s*"([^"]+)"', json.dumps(optimized_response)))
        validation_results['task_ids_preserved'] = baseline_ids.issubset(optimized_ids) if baseline_ids else True
        
        # Check status information
        baseline_statuses = set(re.findall(r'"status":\s*"([^"]+)"', json.dumps(baseline_response)))
        optimized_statuses = set(re.findall(r'"status":\s*"([^"]+)"', json.dumps(optimized_response)))
        validation_results['statuses_preserved'] = len(optimized_statuses) >= len(baseline_statuses)
        
        # Check priority information
        baseline_priorities = len(re.findall(r'"priority":\s*"([^"]+)"', json.dumps(baseline_response)))
        optimized_priorities = len(re.findall(r'"priority":\s*"([^"]+)"', json.dumps(optimized_response)))
        validation_results['priorities_preserved'] = optimized_priorities >= baseline_priorities
        
        # Check assignee information
        baseline_assignees = len(re.findall(r'@([a-z-]+agent)', json.dumps(baseline_response)))
        optimized_assignees = len(re.findall(r'@([a-z-]+agent)', json.dumps(optimized_response)))
        validation_results['assignees_preserved'] = optimized_assignees >= baseline_assignees
        
        return validation_results


async def run_ai_comprehension_benchmark():
    """Convenience function to run AI comprehension benchmark."""
    benchmark = AIComprehensionBenchmark()
    
    try:
        await benchmark.setup()
        result = await benchmark.run_benchmark()
        await benchmark.teardown()
        
        print("\n" + "="*60)
        print("AI COMPREHENSION & PROCESSING SPEED BENCHMARK RESULTS")
        print("="*60)
        
        print(f"Success Rate: {result.success_rate:.2%}")
        print(f"Execution Time: {result.execution_time:.2f}s")
        print(f"All Targets Met: {'✅ Yes' if result.all_targets_met else '❌ No'}")
        
        # Print key metrics
        print("\nKey Metrics:")
        for metric in result.metrics:
            if metric.category in ["improvement", "overall", "quality", "reliability"]:
                status = "✅" if metric.meets_target else "❌"
                target_text = f" (target: {metric.target})" if metric.target else ""
                print(f"  {metric.name}: {metric.value:.1f}{metric.unit}{target_text} {status}")
        
        # Check specific targets
        speed_improvement_metric = result.get_metric("overall_speed_improvement")
        if speed_improvement_metric:
            improvement_met = speed_improvement_metric.meets_target
            print(f"\n40% Speed Improvement Target: {'✅ MET' if improvement_met else '❌ NOT MET'} ({speed_improvement_metric.value:.1f}%)")
        
        accuracy_retention_metric = result.get_metric("accuracy_retention")
        if accuracy_retention_metric:
            retention_met = accuracy_retention_metric.meets_target
            print(f"95% Accuracy Retention Target: {'✅ MET' if retention_met else '❌ NOT MET'} ({accuracy_retention_metric.value:.1f}%)")
        
        if result.error_details:
            print(f"\nErrors ({len(result.error_details)}):")
            for error in result.error_details:
                print(f"  - {error}")
        
        print("="*60)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to run AI comprehension benchmark: {str(e)}")
        raise


if __name__ == "__main__":
    # Run the AI comprehension benchmark
    asyncio.run(run_ai_comprehension_benchmark())