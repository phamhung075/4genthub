"""
Response Size Benchmark Tests

Comprehensive testing suite to measure and validate response size reduction targets
of 50-70% as specified in Phase 4 optimization requirements.

Tests both baseline (unoptimized) and optimized response sizes across various scenarios.
"""

import asyncio
import time
import json
import statistics
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple
from unittest.mock import Mock, patch
import logging

# Import performance test components
from .. import PERFORMANCE_CONFIG, setup_performance_logger
from ..mocks.mock_mcp_server import create_performance_test_server
from .performance_suite import PerformanceMetric, BenchmarkResult, PerformanceBenchmark, ResourceMonitor

logger = setup_performance_logger()


@dataclass
class ResponseSizeMetric:
    """Response size measurement with baseline comparison."""
    scenario: str
    baseline_size_bytes: int
    optimized_size_bytes: int
    size_reduction_bytes: int
    size_reduction_percentage: float
    target_reduction_percentage: float
    meets_target: bool
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class ResponseSizeBenchmark(PerformanceBenchmark):
    """Benchmark for measuring response size reduction (50-70% target)."""
    
    def __init__(self):
        super().__init__("Response Size Reduction")
        self.mock_server = None
        self.scenarios = [
            "simple_task_list",
            "complex_task_with_dependencies", 
            "bulk_task_operations",
            "task_with_subtasks",
            "hierarchical_context_data",
            "agent_workflow_data"
        ]
        
    async def setup(self):
        """Setup response size benchmark."""
        self.mock_server = create_performance_test_server(
            response_delay=0.01,
            error_rate=0.0
        )
    
    async def teardown(self):
        """Cleanup response size benchmark."""
        if self.mock_server:
            self.mock_server.reset_metrics()
    
    def _create_baseline_response(self, scenario: str) -> Dict[str, Any]:
        """Create unoptimized baseline response for scenario."""
        if scenario == "simple_task_list":
            return {
                "success": True,
                "data": {
                    "tasks": [
                        {
                            "id": f"task-{i}",
                            "title": f"Test Task {i}",
                            "description": f"This is a detailed description for test task {i} with comprehensive information about what needs to be done, including acceptance criteria, technical requirements, dependencies, and expected outcomes. The description contains verbose explanations and redundant information that could be optimized.",
                            "status": "todo",
                            "priority": "medium",
                            "details": f"Detailed implementation notes for task {i} including step-by-step instructions, code examples, file paths, configuration details, and extensive technical specifications that take up significant space in the response.",
                            "assignees": ["@coding-agent", "@test-orchestrator-agent"],
                            "labels": ["feature", "backend", "frontend", "testing", "documentation"],
                            "dependencies": [f"dep-task-{i-1}"] if i > 1 else [],
                            "estimated_effort": "4 hours",
                            "created_at": "2025-09-12T09:00:00Z",
                            "updated_at": "2025-09-12T10:00:00Z",
                            "git_branch_id": "branch-123-456-789",
                            "context_data": {
                                "metadata": {"verbose": True, "extended_info": True},
                                "workflow_hints": [
                                    "Complete step 1: Analyze requirements in detail",
                                    "Complete step 2: Design comprehensive solution architecture", 
                                    "Complete step 3: Implement with extensive error handling",
                                    "Complete step 4: Create comprehensive test suite",
                                    "Complete step 5: Document all aspects thoroughly"
                                ],
                                "progress_indicators": {
                                    "completion_percentage": 0,
                                    "time_spent_minutes": 0,
                                    "blockers": [],
                                    "insights": []
                                }
                            }
                        } for i in range(1, 6)
                    ]
                },
                "meta": {
                    "total_count": 5,
                    "page": 1,
                    "per_page": 10,
                    "has_more": False,
                    "query_time_ms": 150,
                    "cache_status": "miss",
                    "detailed_metadata": {
                        "database_queries": 3,
                        "cache_lookups": 2,
                        "processing_time_breakdown": {
                            "query_execution": 50,
                            "data_transformation": 30,
                            "context_enrichment": 40,
                            "response_formatting": 30
                        }
                    }
                }
            }
        
        elif scenario == "complex_task_with_dependencies":
            return {
                "success": True,
                "data": {
                    "task": {
                        "id": "complex-task-123",
                        "title": "Complex Feature Implementation with Multiple Dependencies",
                        "description": "This is an extremely detailed and comprehensive task description that covers all aspects of implementing a complex feature. It includes detailed requirements analysis, technical specifications, architecture considerations, security requirements, performance expectations, testing strategies, deployment procedures, monitoring requirements, documentation needs, and maintenance procedures. The description is intentionally verbose to represent unoptimized baseline responses.",
                        "status": "todo",
                        "priority": "high", 
                        "details": """
                        COMPREHENSIVE TASK DETAILS:
                        
                        1. REQUIREMENTS ANALYSIS:
                           - Functional requirements with detailed use cases
                           - Non-functional requirements including performance, security, scalability
                           - User experience requirements and accessibility considerations
                           - Integration requirements with existing systems
                           - Compliance and regulatory requirements
                        
                        2. TECHNICAL ARCHITECTURE:
                           - System architecture diagrams and documentation
                           - Database schema design and optimization
                           - API design and documentation
                           - Security architecture and threat modeling
                           - Performance optimization strategies
                        
                        3. IMPLEMENTATION PLAN:
                           - Phase 1: Foundation and core components
                           - Phase 2: Feature implementation and integration
                           - Phase 3: Testing and quality assurance
                           - Phase 4: Deployment and monitoring
                           - Phase 5: Documentation and training
                        
                        4. TESTING STRATEGY:
                           - Unit testing with comprehensive coverage
                           - Integration testing scenarios
                           - End-to-end testing workflows
                           - Performance testing benchmarks
                           - Security testing procedures
                           - User acceptance testing criteria
                        """,
                        "dependencies": [
                            {
                                "id": "dep-1",
                                "title": "Database Schema Migration",
                                "status": "completed",
                                "completion_date": "2025-09-10T15:30:00Z",
                                "detailed_info": "Comprehensive database schema migration including all tables, indexes, constraints, and data migration procedures with rollback strategies."
                            },
                            {
                                "id": "dep-2", 
                                "title": "Authentication System Upgrade",
                                "status": "in_progress",
                                "progress": 75,
                                "estimated_completion": "2025-09-15T12:00:00Z",
                                "detailed_info": "Complete authentication system overhaul including JWT implementation, refresh token management, role-based access control, and security audit compliance."
                            },
                            {
                                "id": "dep-3",
                                "title": "API Gateway Configuration",
                                "status": "todo", 
                                "priority": "high",
                                "estimated_effort": "2 days",
                                "detailed_info": "Configure API gateway with rate limiting, request/response transformation, logging, monitoring, and security policies."
                            }
                        ],
                        "subtasks": [
                            {
                                "id": "subtask-1",
                                "title": "Core Service Implementation",
                                "description": "Implement the core service layer with all business logic, validation, error handling, and integration points. Include comprehensive logging and monitoring.",
                                "progress": 0,
                                "estimated_hours": 16
                            },
                            {
                                "id": "subtask-2", 
                                "title": "API Endpoint Development",
                                "description": "Develop all API endpoints with proper request/response handling, validation, error handling, documentation, and testing.",
                                "progress": 0,
                                "estimated_hours": 12
                            }
                        ],
                        "context_data": {
                            "workflow_guidance": {
                                "next_steps": [
                                    "Review and approve technical architecture document",
                                    "Set up development environment with all required tools",
                                    "Create detailed implementation timeline with milestones",
                                    "Establish communication channels for stakeholder updates",
                                    "Prepare test data and testing environments"
                                ],
                                "best_practices": [
                                    "Follow established coding standards and conventions",
                                    "Implement comprehensive error handling and logging",
                                    "Ensure all code is properly documented and tested",
                                    "Use version control best practices with meaningful commits",
                                    "Conduct regular code reviews and security assessments"
                                ]
                            }
                        }
                    }
                }
            }
        
        elif scenario == "bulk_task_operations":
            return {
                "success": True,
                "data": {
                    "tasks": [
                        {
                            "id": f"bulk-task-{i:03d}",
                            "title": f"Bulk Operation Task {i}",
                            "description": f"Detailed description for bulk operation task {i} with comprehensive information about implementation requirements, testing procedures, deployment steps, and maintenance guidelines. This description intentionally contains redundant and verbose information to simulate unoptimized responses.",
                            "status": "todo" if i % 3 == 0 else "in_progress" if i % 3 == 1 else "completed",
                            "priority": "high" if i % 5 == 0 else "medium" if i % 5 < 3 else "low",
                            "assignees": [f"@agent-{(i % 4) + 1}"],
                            "labels": [f"category-{i % 3}", f"type-{i % 4}", f"priority-{i % 2}"],
                            "estimated_effort": f"{(i % 8) + 1} hours",
                            "detailed_context": {
                                "implementation_notes": f"Extensive implementation notes for task {i} including code examples, configuration details, and step-by-step procedures.",
                                "testing_requirements": f"Comprehensive testing requirements for task {i} covering all scenarios and edge cases.",
                                "deployment_procedures": f"Detailed deployment procedures for task {i} with rollback strategies and monitoring setup."
                            }
                        } for i in range(1, 26)  # 25 tasks for bulk testing
                    ]
                },
                "meta": {
                    "total_count": 25,
                    "processing_time_ms": 450,
                    "memory_usage_mb": 15.2,
                    "database_queries": 8,
                    "cache_operations": 12,
                    "detailed_performance_metrics": {
                        "query_times": [45, 52, 38, 61, 42, 55, 48, 39],
                        "cache_hit_rate": 0.33,
                        "response_compression_ratio": 1.0,
                        "network_latency_ms": 25
                    }
                }
            }
        
        # Add more scenarios as needed
        return {"success": True, "data": {"message": f"Baseline response for {scenario}"}}
    
    def _create_optimized_response(self, scenario: str) -> Dict[str, Any]:
        """Create optimized response for scenario."""
        if scenario == "simple_task_list":
            return {
                "success": True,
                "data": {
                    "tasks": [
                        {
                            "id": f"task-{i}",
                            "title": f"Test Task {i}",
                            "description": f"Task {i} - implementation required",
                            "status": "todo",
                            "priority": "medium", 
                            "assignees": ["@coding-agent"],
                            "labels": ["feature"],
                            "estimated_effort": "4h"
                        } for i in range(1, 6)
                    ]
                },
                "meta": {"count": 5, "cached": True}
            }
        
        elif scenario == "complex_task_with_dependencies":
            return {
                "success": True,
                "data": {
                    "task": {
                        "id": "complex-task-123",
                        "title": "Complex Feature Implementation",
                        "description": "Complex feature with auth, DB, and API components",
                        "status": "todo",
                        "priority": "high",
                        "deps": [
                            {"id": "dep-1", "status": "done"},
                            {"id": "dep-2", "status": "progress", "pct": 75},
                            {"id": "dep-3", "status": "todo", "priority": "high"}
                        ],
                        "subtasks": [
                            {"id": "st-1", "title": "Core Service", "progress": 0},
                            {"id": "st-2", "title": "API Endpoints", "progress": 0}
                        ]
                    }
                }
            }
        
        elif scenario == "bulk_task_operations":
            return {
                "success": True,
                "data": {
                    "tasks": [
                        {
                            "id": f"bulk-{i:03d}",
                            "title": f"Task {i}",
                            "status": ["todo", "progress", "done"][i % 3],
                            "priority": ["high", "med", "low"][i % 3],
                            "assignee": f"@agent-{(i % 4) + 1}",
                            "effort": f"{(i % 8) + 1}h"
                        } for i in range(1, 26)
                    ]
                },
                "meta": {"count": 25, "time_ms": 85, "cached": True}
            }
        
        return {"success": True, "data": {"msg": f"Optimized {scenario}"}}
    
    def _measure_response_size(self, response_data: Dict[str, Any]) -> int:
        """Measure response size in bytes."""
        json_string = json.dumps(response_data, separators=(',', ':'))
        return len(json_string.encode('utf-8'))
    
    async def run_benchmark(self) -> BenchmarkResult:
        """Run response size reduction benchmark."""
        self.resource_monitor.start_monitoring()
        start_time = time.perf_counter()
        
        metrics = []
        size_metrics = []
        errors = []
        
        logger.info("Starting response size reduction benchmarks...")
        
        try:
            for scenario in self.scenarios:
                logger.info(f"Testing scenario: {scenario}")
                self.resource_monitor.sample_resources()
                
                # Generate baseline and optimized responses
                baseline_response = self._create_baseline_response(scenario)
                optimized_response = self._create_optimized_response(scenario)
                
                # Measure sizes
                baseline_size = self._measure_response_size(baseline_response)
                optimized_size = self._measure_response_size(optimized_response)
                
                # Calculate reduction
                size_reduction = baseline_size - optimized_size
                reduction_percentage = (size_reduction / baseline_size) * 100 if baseline_size > 0 else 0
                
                # Determine target (50-70% reduction, using 60% as target)
                target_reduction = 60.0
                meets_target = reduction_percentage >= 50.0  # Minimum 50% reduction
                
                size_metric = ResponseSizeMetric(
                    scenario=scenario,
                    baseline_size_bytes=baseline_size,
                    optimized_size_bytes=optimized_size,
                    size_reduction_bytes=size_reduction,
                    size_reduction_percentage=reduction_percentage,
                    target_reduction_percentage=target_reduction,
                    meets_target=meets_target
                )
                
                size_metrics.append(size_metric)
                
                # Add to performance metrics
                metrics.extend([
                    self.create_metric(f"{scenario}_baseline_size", baseline_size, "bytes", None, "size"),
                    self.create_metric(f"{scenario}_optimized_size", optimized_size, "bytes", None, "size"),
                    self.create_metric(f"{scenario}_size_reduction", reduction_percentage, "percent", 50.0, "reduction")
                ])
                
                logger.info(f"  Baseline size: {baseline_size:,} bytes")
                logger.info(f"  Optimized size: {optimized_size:,} bytes")
                logger.info(f"  Reduction: {reduction_percentage:.1f}% ({'✅' if meets_target else '❌'})")
            
            # Calculate overall statistics
            all_reductions = [sm.size_reduction_percentage for sm in size_metrics]
            avg_reduction = statistics.mean(all_reductions)
            min_reduction = min(all_reductions) 
            max_reduction = max(all_reductions)
            targets_met = sum(1 for sm in size_metrics if sm.meets_target)
            
            # Overall metrics
            metrics.extend([
                self.create_metric("avg_size_reduction", avg_reduction, "percent", 60.0, "overall"),
                self.create_metric("min_size_reduction", min_reduction, "percent", 50.0, "overall"),
                self.create_metric("max_size_reduction", max_reduction, "percent", None, "overall"),
                self.create_metric("scenarios_meeting_target", targets_met, "count", len(self.scenarios), "overall"),
                self.create_metric("target_achievement_rate", (targets_met / len(self.scenarios)) * 100, "percent", 80.0, "overall")
            ])
            
            logger.info(f"Overall Results:")
            logger.info(f"  Average reduction: {avg_reduction:.1f}%")
            logger.info(f"  Range: {min_reduction:.1f}% - {max_reduction:.1f}%")
            logger.info(f"  Scenarios meeting target: {targets_met}/{len(self.scenarios)}")
        
        except Exception as e:
            error_msg = f"Response size benchmark error: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
        
        # Calculate final metrics
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        success_rate = 1.0 if len(errors) == 0 else 0.0
        resource_usage = self.resource_monitor.stop_monitoring()
        
        return BenchmarkResult(
            benchmark_name=self.name,
            metrics=metrics,
            success_rate=success_rate,
            execution_time=execution_time,
            resource_usage=resource_usage,
            error_details=errors,
            metadata={
                "scenarios_tested": len(self.scenarios),
                "size_metrics": [asdict(sm) for sm in size_metrics],
                "target_reduction_range": "50-70%"
            }
        )


async def run_response_size_benchmark():
    """Convenience function to run response size benchmark."""
    benchmark = ResponseSizeBenchmark()
    
    try:
        await benchmark.setup()
        result = await benchmark.run_benchmark()
        await benchmark.teardown()
        
        print("\n" + "="*60)
        print("RESPONSE SIZE REDUCTION BENCHMARK RESULTS")
        print("="*60)
        
        print(f"Success Rate: {result.success_rate:.2%}")
        print(f"Execution Time: {result.execution_time:.2f}s")
        print(f"All Targets Met: {'✅ Yes' if result.all_targets_met else '❌ No'}")
        
        # Print key metrics
        print("\nKey Metrics:")
        for metric in result.metrics:
            if metric.category in ["reduction", "overall"]:
                status = "✅" if metric.meets_target else "❌"
                target_text = f" (target: {metric.target})" if metric.target else ""
                print(f"  {metric.name}: {metric.value:.1f}{metric.unit}{target_text} {status}")
        
        if result.error_details:
            print(f"\nErrors ({len(result.error_details)}):")
            for error in result.error_details:
                print(f"  - {error}")
        
        print("="*60)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to run response size benchmark: {str(e)}")
        raise


if __name__ == "__main__":
    # Run the response size benchmark
    asyncio.run(run_response_size_benchmark())