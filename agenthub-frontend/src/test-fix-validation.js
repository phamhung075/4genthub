// Test Validation Script for Duplicate Request Fix
// Run this in browser console after implementing the fixes

(function() {
  console.log('🧪 Testing LazySubtaskList Duplicate Request Fix');
  console.log('━'.repeat(60));

  // Test 1: Check if request deduplication utility is available
  console.log('📋 Test 1: Request Deduplication Infrastructure');
  if (typeof window.getRequestDeduplicationStats === 'function') {
    console.log('✅ Request deduplication utility available');
    const stats = window.getRequestDeduplicationStats();
    console.log('📊 Current deduplication stats:', stats);
  } else {
    console.log('❌ Request deduplication utility not found');
  }

  // Test 2: Monitor network activity
  console.log('\n📋 Test 2: Network Activity Monitoring');
  console.log('🔧 Installing network monitor...');

  const originalFetch = window.fetch;
  const apiCalls = [];
  let callCounter = 0;

  window.fetch = function(...args) {
    const [url, options] = args;
    const callId = ++callCounter;
    const timestamp = Date.now();

    // Track subtask-related API calls
    if (url.includes('/subtasks') || url.includes('/subtask')) {
      const apiCall = {
        id: callId,
        timestamp,
        url,
        method: options?.method || 'GET',
        timeFromStart: timestamp - window.testStartTime
      };

      apiCalls.push(apiCall);
      console.log(`🌐 Subtask API Call #${callId}:`, {
        url: url.substring(url.lastIndexOf('/') + 1),
        method: apiCall.method,
        timeFromStart: `${apiCall.timeFromStart}ms`
      });

      // Check for duplicates within 500ms
      const recentDuplicates = apiCalls.filter(call =>
        call.url === url &&
        Math.abs(timestamp - call.timestamp) < 500 &&
        call.id !== callId
      );

      if (recentDuplicates.length > 0) {
        console.warn(`⚠️ DUPLICATE DETECTED! Call #${callId} duplicates:`,
          recentDuplicates.map(c => c.id));
      }
    }

    return originalFetch.apply(this, args);
  };

  // Test 3: Set up test environment
  window.testStartTime = Date.now();
  window.testApiCalls = apiCalls;

  // Utility functions for testing
  window.getSubtaskApiCalls = function() {
    return apiCalls;
  };

  window.checkForDuplicates = function() {
    const duplicates = [];
    const urlMap = {};

    apiCalls.forEach(call => {
      if (!urlMap[call.url]) {
        urlMap[call.url] = [];
      }
      urlMap[call.url].push(call);
    });

    Object.entries(urlMap).forEach(([url, calls]) => {
      if (calls.length > 1) {
        // Check if calls are within the deduplication window (500ms)
        for (let i = 0; i < calls.length - 1; i++) {
          for (let j = i + 1; j < calls.length; j++) {
            const timeDiff = Math.abs(calls[j].timestamp - calls[i].timestamp);
            if (timeDiff < 500) {
              duplicates.push({
                url,
                call1: calls[i],
                call2: calls[j],
                timeDiff
              });
            }
          }
        }
      }
    });

    return duplicates;
  };

  window.runDuplicateTest = function() {
    console.log('\n🔍 Running duplicate request test...');
    console.log('📝 Instructions:');
    console.log('1. Navigate to a task page');
    console.log('2. Click to expand subtasks');
    console.log('3. Wait 2 seconds');
    console.log('4. Run window.checkTestResults()');
    console.log('\n⏱️ Test timer started...');

    // Clear previous calls
    apiCalls.length = 0;
    callCounter = 0;
    window.testStartTime = Date.now();
  };

  window.checkTestResults = function() {
    const duplicates = window.checkForDuplicates();
    const totalCalls = apiCalls.length;

    console.log('\n📊 TEST RESULTS');
    console.log('━'.repeat(40));
    console.log(`📈 Total subtask API calls: ${totalCalls}`);
    console.log(`🔄 Duplicate calls detected: ${duplicates.length}`);

    if (duplicates.length === 0) {
      console.log('✅ SUCCESS: No duplicate requests detected!');
      console.log('🎯 Fix is working correctly');
    } else {
      console.log('❌ FAILURE: Duplicate requests still occurring');
      console.log('📋 Duplicate details:', duplicates);
    }

    // Show deduplication stats if available
    if (typeof window.getRequestDeduplicationStats === 'function') {
      console.log('📊 Deduplication stats:', window.getRequestDeduplicationStats());
    }

    return {
      totalCalls,
      duplicates: duplicates.length,
      success: duplicates.length === 0,
      details: duplicates
    };
  };

  console.log('\n✅ Test environment ready!');
  console.log('🚀 Run window.runDuplicateTest() to start testing');
  console.log('📊 Run window.checkTestResults() after testing');
  console.log('📈 Run window.getSubtaskApiCalls() to see all calls');
  console.log('🔧 Run window.getRequestDeduplicationStats() for deduplication info');

})();