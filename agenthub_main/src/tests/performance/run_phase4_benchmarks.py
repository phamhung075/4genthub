#!/usr/bin/env python3
"""
Phase 4 Performance Benchmarks Runner

Executable script for running Phase 4 comprehensive performance benchmarks.
Designed for CI/CD integration and manual execution.
"""

import sys
import asyncio
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from agenthub_main.src.tests.performance import setup_performance_logger
from agenthub_main.src.tests.performance.benchmarks.comprehensive_benchmark_suite import Phase4ComprehensiveBenchmarkSuite
from agenthub_main.src.tests.performance.benchmarks.response_size_tests import run_response_size_benchmark
from agenthub_main.src.tests.performance.benchmarks.ai_comprehension_tests import run_ai_comprehension_benchmark
from agenthub_main.src.tests.performance.benchmarks.load_testing_suite import run_load_testing_benchmark

logger = setup_performance_logger()


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Phase 4 Performance Benchmarks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all benchmarks
  python run_phase4_benchmarks.py --all
  
  # Run specific benchmark
  python run_phase4_benchmarks.py --benchmark response_size
  
  # Run with custom output directory
  python run_phase4_benchmarks.py --all --output /path/to/output
  
  # Run with reduced load testing for CI
  python run_phase4_benchmarks.py --all --ci-mode
        """
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all Phase 4 benchmarks (comprehensive suite)"
    )
    
    parser.add_argument(
        "--benchmark",
        choices=["response_size", "ai_comprehension", "load_testing", "comprehensive"],
        help="Run specific benchmark only"
    )
    
    parser.add_argument(
        "--output",
        type=Path,
        help="Output directory for results (default: ./results/phase4)"
    )
    
    parser.add_argument(
        "--ci-mode",
        action="store_true",
        help="Run in CI mode (reduced load testing, faster execution)"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--fail-on-target-miss",
        action="store_true",
        help="Exit with error code if performance targets are not met"
    )
    
    return parser.parse_args()


async def run_individual_benchmark(benchmark_type: str, output_dir: Path = None):
    """Run a specific benchmark type."""
    logger.info(f"Running {benchmark_type} benchmark...")
    
    try:
        if benchmark_type == "response_size":
            result = await run_response_size_benchmark()
        elif benchmark_type == "ai_comprehension":
            result = await run_ai_comprehension_benchmark()
        elif benchmark_type == "load_testing":
            result = await run_load_testing_benchmark()
        elif benchmark_type == "comprehensive":
            suite = Phase4ComprehensiveBenchmarkSuite(output_dir)
            results = await suite.run_comprehensive_benchmarks()
            return results["phase4_targets_met"], results
        else:
            logger.error(f"Unknown benchmark type: {benchmark_type}")
            return False, None
        
        # Check if targets were met
        targets_met = result.all_targets_met if hasattr(result, 'all_targets_met') else True
        
        return targets_met, result
        
    except Exception as e:
        logger.error(f"Failed to run {benchmark_type} benchmark: {str(e)}")
        return False, None


async def run_comprehensive_benchmarks(output_dir: Path = None, ci_mode: bool = False):
    """Run the complete Phase 4 comprehensive benchmark suite."""
    logger.info("Running Phase 4 Comprehensive Performance Benchmark Suite...")
    
    if ci_mode:
        logger.info("Running in CI mode - reduced load testing duration")
        # Modify load testing config for CI
        from agenthub_main.src.tests.performance import PERFORMANCE_CONFIG
        original_duration = PERFORMANCE_CONFIG["load_testing"]["test_duration_seconds"]
        original_requests = PERFORMANCE_CONFIG["load_testing"]["max_concurrent_requests"]
        
        PERFORMANCE_CONFIG["load_testing"]["test_duration_seconds"] = 60  # 1 minute instead of 5
        PERFORMANCE_CONFIG["load_testing"]["max_concurrent_requests"] = 20  # Reduced concurrency
    
    try:
        suite = Phase4ComprehensiveBenchmarkSuite(output_dir)
        results = await suite.run_comprehensive_benchmarks()
        
        phase4_targets_met = results["phase4_targets_met"]
        suite_duration = results["suite_duration"]
        
        logger.info(f"Comprehensive benchmark suite completed in {suite_duration:.2f}s")
        logger.info(f"Phase 4 targets met: {'✅ YES' if phase4_targets_met else '❌ NO'}")
        
        return phase4_targets_met, results
        
    except Exception as e:
        logger.error(f"Comprehensive benchmark suite failed: {str(e)}")
        return False, None
    
    finally:
        if ci_mode:
            # Restore original config
            PERFORMANCE_CONFIG["load_testing"]["test_duration_seconds"] = original_duration
            PERFORMANCE_CONFIG["load_testing"]["max_concurrent_requests"] = original_requests


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def print_results_summary(targets_met: bool, results: any):
    """Print a summary of benchmark results."""
    print("\n" + "="*80)
    print("PHASE 4 PERFORMANCE BENCHMARKS SUMMARY")
    print("="*80)
    
    if targets_met:
        print("🎉 SUCCESS: All Phase 4 performance targets achieved!")
    else:
        print("⚠️  WARNING: Some Phase 4 performance targets were not met")
    
    if hasattr(results, 'get') and isinstance(results, dict):
        # Comprehensive results
        phase4_analysis = results.get("results", {}).get("phase4_analysis", {})
        if "target_analysis" in phase4_analysis:
            print("\nTarget Analysis:")
            for target_data in phase4_analysis["target_analysis"].values():
                status = "✅ MET" if target_data["met"] else "❌ NOT MET"
                value_text = f" ({target_data['value']:.1f})" if target_data["value"] is not None else ""
                print(f"  {target_data['description']}: {status}{value_text}")
    elif hasattr(results, 'success_rate'):
        # Individual benchmark result
        print(f"\nBenchmark Success Rate: {results.success_rate:.2%}")
        print(f"All Targets Met: {'✅ Yes' if results.all_targets_met else '❌ No'}")
    
    print("="*80)


async def main():
    """Main execution function."""
    args = parse_arguments()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Determine output directory
    output_dir = args.output or Path("./results/phase4")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Phase 4 Performance Benchmarks - Started at {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"Output directory: {output_dir.absolute()}")
    
    if args.ci_mode:
        logger.info("Running in CI mode")
    
    # Run benchmarks
    targets_met = False
    results = None
    
    if args.all or args.benchmark == "comprehensive":
        targets_met, results = await run_comprehensive_benchmarks(output_dir, args.ci_mode)
    elif args.benchmark:
        targets_met, results = await run_individual_benchmark(args.benchmark, output_dir)
    else:
        logger.error("Must specify --all or --benchmark option")
        sys.exit(1)
    
    # Print results summary
    if results:
        print_results_summary(targets_met, results)
    
    # Exit with appropriate code
    if args.fail_on_target_miss and not targets_met:
        logger.error("Performance targets not met - exiting with error code")
        sys.exit(1)
    elif targets_met:
        logger.info("All performance targets met - success!")
        sys.exit(0)
    else:
        logger.warning("Some performance targets not met - check results")
        sys.exit(0)


if __name__ == "__main__":
    # Run the benchmarks
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Benchmark execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)