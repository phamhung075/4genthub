// Debug script to trace multiple backend API calls
// Add this to the browser console to monitor API calls

(function() {
  console.log('🔍 API Call Tracer - Starting monitoring for multiple backend calls...');

  // Store original fetch function
  const originalFetch = window.fetch;
  const apiCalls = [];
  let callCounter = 0;

  // Override fetch to log all API calls
  window.fetch = function(...args) {
    const [url, options] = args;
    const callId = ++callCounter;
    const timestamp = new Date().toISOString();

    // Check if this is a subtask or task API call
    const isSubtaskCall = url.includes('/subtasks') || url.includes('/subtask');
    const isTaskCall = url.includes('/tasks') || url.includes('/task');

    if (isSubtaskCall || isTaskCall) {
      const stack = new Error().stack;
      const apiCall = {
        id: callId,
        timestamp,
        url,
        method: options?.method || 'GET',
        type: isSubtaskCall ? 'subtask' : 'task',
        stack: stack.split('\n').slice(2, 8).join('\n') // Get caller stack
      };

      apiCalls.push(apiCall);

      console.log(`🌐 API Call #${callId} [${apiCall.type.toUpperCase()}]:`, {
        url,
        method: apiCall.method,
        timestamp,
        stack: apiCall.stack
      });

      // Check for potential duplicates (same URL called within 1 second)
      const recentCalls = apiCalls.filter(call =>
        call.url === url &&
        (new Date(timestamp) - new Date(call.timestamp)) < 1000 &&
        call.id !== callId
      );

      if (recentCalls.length > 0) {
        console.warn(`⚠️ POTENTIAL DUPLICATE CALL detected!`, {
          currentCall: callId,
          duplicatesWith: recentCalls.map(c => c.id),
          url,
          timeDiff: `${(new Date(timestamp) - new Date(recentCalls[0].timestamp))}ms`
        });
      }
    }

    // Call original fetch
    return originalFetch.apply(this, args);
  };

  // Utility functions to check call patterns
  window.getApiCallStats = function() {
    const taskCalls = apiCalls.filter(c => c.type === 'task');
    const subtaskCalls = apiCalls.filter(c => c.type === 'subtask');

    console.log('📊 API Call Statistics:', {
      totalCalls: apiCalls.length,
      taskCalls: taskCalls.length,
      subtaskCalls: subtaskCalls.length,
      duplicateDetected: apiCalls.length > new Set(apiCalls.map(c => c.url)).size
    });

    return { taskCalls, subtaskCalls, all: apiCalls };
  };

  window.findDuplicateCalls = function() {
    const urlGroups = {};
    apiCalls.forEach(call => {
      if (!urlGroups[call.url]) urlGroups[call.url] = [];
      urlGroups[call.url].push(call);
    });

    const duplicates = Object.entries(urlGroups)
      .filter(([url, calls]) => calls.length > 1)
      .map(([url, calls]) => ({ url, calls, count: calls.length }));

    console.log('🔍 Duplicate API Calls Found:', duplicates);
    return duplicates;
  };

  window.clearApiCallLog = function() {
    apiCalls.length = 0;
    callCounter = 0;
    console.log('🧹 API call log cleared');
  };

  console.log('✅ API Call Tracer installed! Use these commands:');
  console.log('- getApiCallStats() - View call statistics');
  console.log('- findDuplicateCalls() - Find duplicate API calls');
  console.log('- clearApiCallLog() - Clear the log');
  console.log('\n🎯 Now click on tasks/subtasks and watch for duplicate call warnings!');
})();