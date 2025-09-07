#!/usr/bin/env python3
"""
Performance Test for Task Loading
Tests the API response time for loading tasks
"""

import time
import requests
import json
from statistics import mean, stdev

API_URL = "http://localhost:8000/mcp"

def test_list_tasks(git_branch_id=None):
    """Test the list tasks API endpoint"""
    
    # Prepare the request
    body = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "manage_task",
            "arguments": {
                "action": "list",
                "limit": 10
            }
        },
        "id": 1
    }
    
    if git_branch_id:
        body["params"]["arguments"]["git_branch_id"] = git_branch_id
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-06-18"
    }
    
    # Measure response time
    start_time = time.time()
    
    try:
        response = requests.post(API_URL, json=body, headers=headers, timeout=10)
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            if data.get("result"):
                result_content = json.loads(data["result"]["content"][0]["text"])
                task_count = result_content.get("count", 0)
                return elapsed_time, task_count, "success"
            else:
                return elapsed_time, 0, f"error: {data.get('error', 'unknown')}"
        else:
            return elapsed_time, 0, f"http_{response.status_code}"
    except requests.exceptions.Timeout:
        return 10.0, 0, "timeout"
    except Exception as e:
        return time.time() - start_time, 0, f"exception: {str(e)}"

def run_performance_test(iterations=5):
    """Run multiple iterations of the performance test"""
    
    print("="*60)
    print("TASK LOADING PERFORMANCE TEST")
    print("="*60)
    print()
    
    print("Testing API endpoint: http://localhost:8000/mcp")
    print(f"Running {iterations} iterations...")
    print()
    
    times = []
    results = []
    
    for i in range(iterations):
        print(f"Test {i+1}/{iterations}: ", end="", flush=True)
        elapsed, count, status = test_list_tasks()
        
        if status == "success":
            times.append(elapsed)
            results.append((elapsed, count))
            print(f"✅ {elapsed*1000:.2f}ms ({count} tasks)")
        else:
            print(f"❌ {status} ({elapsed*1000:.2f}ms)")
    
    print()
    print("-"*60)
    print("RESULTS:")
    print("-"*60)
    
    if times:
        avg_time = mean(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"Average response time: {avg_time*1000:.2f}ms")
        print(f"Minimum response time: {min_time*1000:.2f}ms")
        print(f"Maximum response time: {max_time*1000:.2f}ms")
        
        if len(times) > 1:
            std_dev = stdev(times)
            print(f"Standard deviation: {std_dev*1000:.2f}ms")
        
        print()
        
        # Performance assessment
        if avg_time < 0.1:  # < 100ms
            print("🚀 EXCELLENT: Performance is optimal (<100ms)")
        elif avg_time < 0.5:  # < 500ms
            print("✅ GOOD: Performance is acceptable (<500ms)")
        elif avg_time < 1.0:  # < 1s
            print("⚠️ WARNING: Performance needs improvement (<1s)")
        else:
            print("❌ CRITICAL: Severe performance issue (>1s)")
        
        # Compare to original issue
        print()
        print("Original issue: 5 seconds for 5 tasks")
        print(f"Current performance: {avg_time:.2f}s average")
        
        if avg_time < 1.0:
            improvement = ((5.0 - avg_time) / 5.0) * 100
            print(f"✅ IMPROVEMENT: {improvement:.1f}% faster!")
        
    else:
        print("❌ All tests failed")
    
    print()
    print("="*60)

if __name__ == "__main__":
    # Wait for server to be ready after restart
    print("Waiting for server to be ready...")
    time.sleep(3)
    
    # Run the test
    run_performance_test(iterations=5)