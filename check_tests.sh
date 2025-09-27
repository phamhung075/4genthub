#!/bin/bash

# Check first 10 tests from the failed list
count=0
passed=0
failed=0

echo "Checking tests from .test_cache/failed_tests.txt..."
echo "==========================================="

while read test; do
    if [ -n "$test" ] && [ -f "$test" ]; then
        count=$((count + 1))
        echo -n "[$count] $(basename $test): "

        result=$(timeout 10 python -m pytest "$test" --tb=no -q 2>&1)
        if echo "$result" | grep -q "passed"; then
            echo "✓ PASSED"
            passed=$((passed + 1))
        elif echo "$result" | grep -q "failed"; then
            echo "✗ FAILED"
            failed=$((failed + 1))
        else
            echo "? UNKNOWN"
        fi

        if [ $count -ge 10 ]; then
            break
        fi
    fi
done < .test_cache/failed_tests.txt

echo "==========================================="
echo "Summary: $passed passed, $failed failed out of $count tested"