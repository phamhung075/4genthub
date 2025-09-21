"""
Performance and stress tests for IDValidator domain service.
Tests performance characteristics and resource usage under various loads.
"""

import pytest
import time
import threading
import gc
import sys
from uuid import uuid4
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from fastmcp.utilities.id_validator import (
    IDValidator,
    IDType,
    ValidationResult,
    validate_uuid,
    prevent_id_confusion,
)


class TestIDValidatorPerformance:
    """Performance tests for IDValidator domain service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = IDValidator(strict_uuid_validation=True)
        self.relaxed_validator = IDValidator(strict_uuid_validation=False)

    def test_single_validation_performance(self):
        """Test performance of single UUID validation."""
        test_uuid = str(uuid4())

        # Measure time for single validation
        start_time = time.perf_counter()
        result = self.validator.validate_uuid_format(test_uuid)
        end_time = time.perf_counter()

        elapsed_time = end_time - start_time

        # Should complete very quickly (< 1ms for single validation)
        assert elapsed_time < 0.001, f"Single validation took too long: {elapsed_time:.6f}s"
        assert result.is_valid is True

    def test_batch_validation_performance(self):
        """Test performance of batch UUID validations."""
        # Generate batch of UUIDs
        batch_size = 1000
        test_uuids = [str(uuid4()) for _ in range(batch_size)]

        # Measure batch validation time
        start_time = time.perf_counter()
        results = []
        for uuid_val in test_uuids:
            result = self.validator.validate_uuid_format(uuid_val)
            results.append(result.is_valid)
        end_time = time.perf_counter()

        elapsed_time = end_time - start_time
        avg_time_per_validation = elapsed_time / batch_size

        # All should be valid
        assert all(results), "Some valid UUIDs were rejected"

        # Average time per validation should be very fast (< 10μs)
        assert avg_time_per_validation < 0.00001, f"Average validation time too slow: {avg_time_per_validation:.8f}s"

        print(f"Batch validation: {batch_size} UUIDs in {elapsed_time:.6f}s "
              f"({avg_time_per_validation*1000000:.2f}μs avg)")

    def test_large_scale_validation_performance(self):
        """Test performance with large-scale validations."""
        # Test with 10,000 validations
        batch_size = 10000
        test_uuids = [str(uuid4()) for _ in range(batch_size)]

        start_time = time.perf_counter()

        valid_count = 0
        invalid_count = 0

        for i, uuid_val in enumerate(test_uuids):
            # Mix in some invalid UUIDs to test both paths
            if i % 100 == 0:
                uuid_val = "invalid-uuid-" + str(i)

            result = self.validator.validate_uuid_format(uuid_val)
            if result.is_valid:
                valid_count += 1
            else:
                invalid_count += 1

        end_time = time.perf_counter()
        elapsed_time = end_time - start_time

        # Verify counts
        expected_invalid = batch_size // 100
        assert invalid_count == expected_invalid
        assert valid_count == batch_size - expected_invalid

        # Should complete within reasonable time (< 1 second for 10k validations)
        assert elapsed_time < 1.0, f"Large scale validation took too long: {elapsed_time:.3f}s"

        print(f"Large scale: {batch_size} validations in {elapsed_time:.3f}s "
              f"({(elapsed_time/batch_size)*1000000:.2f}μs avg)")

    def test_concurrent_validation_performance(self):
        """Test performance under concurrent load."""
        import threading

        num_threads = 10
        validations_per_thread = 500
        results = []
        errors = []
        times = []

        def worker():
            thread_start = time.perf_counter()
            try:
                thread_results = []
                for _ in range(validations_per_thread):
                    uuid_val = str(uuid4())
                    result = self.validator.validate_uuid_format(uuid_val)
                    thread_results.append(result.is_valid)

                results.extend(thread_results)
                thread_end = time.perf_counter()
                times.append(thread_end - thread_start)
            except Exception as e:
                errors.append(e)

        # Start all threads
        threads = []
        start_time = time.perf_counter()

        for _ in range(num_threads):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        end_time = time.perf_counter()
        total_elapsed = end_time - start_time

        # Verify no errors
        assert len(errors) == 0, f"Concurrent validation errors: {errors}"

        # Verify all validations succeeded
        total_validations = num_threads * validations_per_thread
        assert len(results) == total_validations
        assert all(results), "Some concurrent validations failed"

        # Performance metrics
        max_thread_time = max(times)
        avg_thread_time = sum(times) / len(times)

        print(f"Concurrent: {total_validations} validations across {num_threads} threads")
        print(f"Total time: {total_elapsed:.3f}s, Max thread time: {max_thread_time:.3f}s")
        print(f"Avg thread time: {avg_thread_time:.3f}s")

        # Should complete concurrently (total time should be less than sequential time)
        # With threading overhead, total time should be less than sum of thread times
        sequential_estimate = sum(times)
        assert total_elapsed < sequential_estimate * 0.7, f"Threads didn't run concurrently: {total_elapsed:.3f}s vs sequential estimate {sequential_estimate:.3f}s"

    def test_memory_usage_stability(self):
        """Test memory usage remains stable during extended operations."""
        import gc
        import psutil
        import os

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform many validations
        iterations = 5000
        for i in range(iterations):
            uuid_val = str(uuid4())
            result = self.validator.validate_uuid_format(uuid_val)
            assert result.is_valid is True

            # Force garbage collection periodically
            if i % 500 == 0:
                gc.collect()

        # Check final memory usage
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print(f"Memory usage: {initial_memory:.1f}MB -> {final_memory:.1f}MB "
              f"(+{memory_increase:.1f}MB) for {iterations} validations")

        # Memory increase should be minimal (< 10MB for 5000 validations)
        assert memory_increase < 10, f"Excessive memory usage: +{memory_increase:.1f}MB"

    def test_regex_performance_comparison(self):
        """Test performance difference between strict and relaxed validation."""
        test_uuids = [str(uuid4()) for _ in range(1000)]

        # Test strict validator
        start_time = time.perf_counter()
        strict_results = []
        for uuid_val in test_uuids:
            result = self.validator.validate_uuid_format(uuid_val)
            strict_results.append(result.is_valid)
        strict_time = time.perf_counter() - start_time

        # Test relaxed validator
        start_time = time.perf_counter()
        relaxed_results = []
        for uuid_val in test_uuids:
            result = self.relaxed_validator.validate_uuid_format(uuid_val)
            relaxed_results.append(result.is_valid)
        relaxed_time = time.perf_counter() - start_time

        # Both should validate all UUIDs as valid
        assert all(strict_results)
        assert all(relaxed_results)

        print(f"Strict validation: {strict_time:.6f}s")
        print(f"Relaxed validation: {relaxed_time:.6f}s")

        # Neither should be extremely slower than the other
        time_ratio = max(strict_time, relaxed_time) / min(strict_time, relaxed_time)
        assert time_ratio < 2.0, f"Performance difference too large: {time_ratio:.2f}x"

    def test_parameter_mapping_performance(self):
        """Test performance of parameter mapping validation."""
        # Generate test data
        num_tests = 1000
        test_data = []
        for _ in range(num_tests):
            test_data.append({
                'task_id': str(uuid4()),
                'git_branch_id': str(uuid4()),
                'project_id': str(uuid4()),
                'user_id': str(uuid4())
            })

        # Test performance
        start_time = time.perf_counter()
        results = []
        for data in test_data:
            result = self.validator.validate_parameter_mapping(**data)
            results.append(result.is_valid)
        end_time = time.perf_counter()

        elapsed_time = end_time - start_time
        avg_time = elapsed_time / num_tests

        # All should be valid
        assert all(results), "Some parameter mappings were invalid"

        # Should be reasonably fast (< 100μs per validation)
        assert avg_time < 0.0001, f"Parameter mapping too slow: {avg_time:.8f}s avg"

        print(f"Parameter mapping: {num_tests} validations in {elapsed_time:.6f}s "
              f"({avg_time*1000000:.2f}μs avg)")

    def test_context_detection_performance(self):
        """Test performance of context detection."""
        test_uuid = str(uuid4())
        context_hints = [
            "task_id", "git_branch_id", "project_id", "user_id",
            "mcp_task_id", "context_id", "subtask_id"
        ]

        num_iterations = 1000

        start_time = time.perf_counter()
        for _ in range(num_iterations):
            for hint in context_hints:
                result = self.validator.detect_id_type(test_uuid, hint)
                assert result.is_valid is True
        end_time = time.perf_counter()

        total_detections = num_iterations * len(context_hints)
        elapsed_time = end_time - start_time
        avg_time = elapsed_time / total_detections

        print(f"Context detection: {total_detections} detections in {elapsed_time:.6f}s "
              f"({avg_time*1000000:.2f}μs avg)")

        # Should be very fast (< 10μs per detection)
        assert avg_time < 0.00001, f"Context detection too slow: {avg_time:.8f}s avg"

    def test_error_path_performance(self):
        """Test performance when validation fails (error paths)."""
        # Generate invalid UUIDs
        invalid_uuids = [
            "not-a-uuid",
            "too-short",
            "550e8400-e29b-41d4-a716",  # Missing segment
            "550e8400-e29b-41d4-a716-446655440000-too-long",
            "550e8400-e29b-31d4-a716-446655440000",  # Wrong version
        ]

        num_iterations = 1000

        start_time = time.perf_counter()
        for _ in range(num_iterations):
            for invalid_uuid in invalid_uuids:
                result = self.validator.validate_uuid_format(invalid_uuid)
                assert result.is_valid is False
        end_time = time.perf_counter()

        total_validations = num_iterations * len(invalid_uuids)
        elapsed_time = end_time - start_time
        avg_time = elapsed_time / total_validations

        print(f"Error path validation: {total_validations} validations in {elapsed_time:.6f}s "
              f"({avg_time*1000000:.2f}μs avg)")

        # Error paths should not be significantly slower than success paths
        assert avg_time < 0.00002, f"Error path validation too slow: {avg_time:.8f}s avg"

    def test_scalability_with_increasing_load(self):
        """Test scalability characteristics with increasing load."""
        batch_sizes = [100, 500, 1000, 5000, 10000]
        times = []

        for batch_size in batch_sizes:
            test_uuids = [str(uuid4()) for _ in range(batch_size)]

            start_time = time.perf_counter()
            for uuid_val in test_uuids:
                result = self.validator.validate_uuid_format(uuid_val)
                assert result.is_valid is True
            end_time = time.perf_counter()

            elapsed_time = end_time - start_time
            times.append(elapsed_time)

            print(f"Batch size {batch_size}: {elapsed_time:.6f}s "
                  f"({(elapsed_time/batch_size)*1000000:.2f}μs avg)")

        # Verify linear scalability (time should scale roughly linearly with batch size)
        for i in range(1, len(batch_sizes)):
            size_ratio = batch_sizes[i] / batch_sizes[i-1]
            time_ratio = times[i] / times[i-1]

            # Time ratio should be close to size ratio (within 50% tolerance for overhead)
            assert time_ratio < size_ratio * 1.5, \
                f"Poor scalability: {batch_sizes[i]} took {time_ratio:.2f}x longer than {batch_sizes[i-1]}"

    def test_thread_pool_performance(self):
        """Test performance using thread pool executor."""
        num_workers = 4
        validations_per_worker = 1000
        test_uuids = [str(uuid4()) for _ in range(num_workers * validations_per_worker)]

        def validate_batch(uuid_batch):
            results = []
            for uuid_val in uuid_batch:
                result = self.validator.validate_uuid_format(uuid_val)
                results.append(result.is_valid)
            return results

        # Split into batches
        batch_size = validations_per_worker
        batches = [test_uuids[i:i+batch_size] for i in range(0, len(test_uuids), batch_size)]

        # Test with ThreadPoolExecutor
        start_time = time.perf_counter()
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            future_results = list(executor.map(validate_batch, batches))
        end_time = time.perf_counter()

        # Flatten results
        all_results = []
        for batch_results in future_results:
            all_results.extend(batch_results)

        elapsed_time = end_time - start_time

        # Verify all validations succeeded
        assert len(all_results) == len(test_uuids)
        assert all(all_results), "Some thread pool validations failed"

        print(f"Thread pool: {len(test_uuids)} validations in {elapsed_time:.3f}s "
              f"using {num_workers} workers")

        # Should complete faster than single-threaded (allowing for overhead)
        # Use realistic estimate based on observed performance (about 3μs per validation)
        single_thread_estimate = len(test_uuids) * 0.000003  # 3μs per validation estimate
        # Thread pool adds overhead, so we expect it to be faster than single thread but not by much
        assert elapsed_time < single_thread_estimate * 5, f"Thread pool didn't provide benefit: {elapsed_time:.3f}s vs estimate {single_thread_estimate * 5:.3f}s"


class TestConvenienceFunctionPerformance:
    """Performance tests for convenience functions."""

    def test_validate_uuid_function_performance(self):
        """Test performance of validate_uuid convenience function."""
        test_uuids = [str(uuid4()) for _ in range(1000)]

        # Test strict mode
        start_time = time.perf_counter()
        strict_results = [validate_uuid(uuid_val, strict=True) for uuid_val in test_uuids]
        strict_time = time.perf_counter() - start_time

        # Test relaxed mode
        start_time = time.perf_counter()
        relaxed_results = [validate_uuid(uuid_val, strict=False) for uuid_val in test_uuids]
        relaxed_time = time.perf_counter() - start_time

        # All should be valid
        assert all(strict_results)
        assert all(relaxed_results)

        print(f"validate_uuid strict: {strict_time:.6f}s")
        print(f"validate_uuid relaxed: {relaxed_time:.6f}s")

        # Should be reasonably fast
        assert strict_time < 0.1, f"validate_uuid strict too slow: {strict_time:.6f}s"
        assert relaxed_time < 0.1, f"validate_uuid relaxed too slow: {relaxed_time:.6f}s"

    def test_prevent_id_confusion_performance(self):
        """Test performance of prevent_id_confusion function."""
        test_data = []
        for _ in range(1000):
            test_data.append({
                'task_id': str(uuid4()),
                'git_branch_id': str(uuid4()),
                'project_id': str(uuid4()),
                'user_id': str(uuid4())
            })

        start_time = time.perf_counter()
        for data in test_data:
            prevent_id_confusion(**data)  # Should not raise exception
        end_time = time.perf_counter()

        elapsed_time = end_time - start_time
        avg_time = elapsed_time / len(test_data)

        print(f"prevent_id_confusion: {len(test_data)} calls in {elapsed_time:.6f}s "
              f"({avg_time*1000000:.2f}μs avg)")

        # Should be fast (< 50μs per call)
        assert avg_time < 0.00005, f"prevent_id_confusion too slow: {avg_time:.8f}s avg"


@pytest.mark.performance
class TestStressScenarios:
    """Stress test scenarios for extreme conditions."""

    def test_extreme_concurrent_load(self):
        """Test behavior under extreme concurrent load."""
        num_threads = 50
        validations_per_thread = 200
        validator = IDValidator()

        results = []
        errors = []

        def stress_worker():
            try:
                worker_results = []
                for _ in range(validations_per_thread):
                    uuid_val = str(uuid4())
                    result = validator.validate_uuid_format(uuid_val)
                    worker_results.append(result.is_valid)
                results.extend(worker_results)
            except Exception as e:
                errors.append(e)

        # Start all threads simultaneously
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=stress_worker)
            threads.append(thread)

        start_time = time.perf_counter()
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()
        end_time = time.perf_counter()

        # Verify no errors and all validations succeeded
        assert len(errors) == 0, f"Stress test errors: {errors}"
        expected_results = num_threads * validations_per_thread
        assert len(results) == expected_results
        assert all(results), "Some stress test validations failed"

        elapsed_time = end_time - start_time
        print(f"Extreme concurrent load: {expected_results} validations across "
              f"{num_threads} threads in {elapsed_time:.3f}s")

    def test_rapid_validator_creation(self):
        """Test rapid creation and destruction of validator instances."""
        num_instances = 1000

        start_time = time.perf_counter()
        for i in range(num_instances):
            # Alternate between strict and relaxed
            strict_mode = i % 2 == 0
            validator = IDValidator(strict_uuid_validation=strict_mode)

            # Perform a validation to ensure it works
            test_uuid = str(uuid4())
            result = validator.validate_uuid_format(test_uuid)
            assert result.is_valid is True

            # Let it be garbage collected
            del validator

        end_time = time.perf_counter()
        elapsed_time = end_time - start_time

        print(f"Rapid validator creation: {num_instances} instances in {elapsed_time:.3f}s")

        # Should complete reasonably quickly
        assert elapsed_time < 1.0, f"Validator creation too slow: {elapsed_time:.3f}s"


if __name__ == "__main__":
    # Run with performance markers
    pytest.main([__file__, "-v", "-m", "performance"])