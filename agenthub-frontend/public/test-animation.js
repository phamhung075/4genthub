/**
 * Animation Debug Test Script
 *
 * This script can be run in the browser console to test animations manually
 * and observe the debug logging output.
 */

console.log('🧪 Animation Debug Test Script Loaded');

// Test function to trigger a fade-in animation
function testFadeInAnimation() {
  console.log('🧪 [TEST] Starting fade-in animation test...');

  // Check if the service is available
  if (!window.webSocketAnimationService) {
    console.error('❌ webSocketAnimationService not found on window');
    return;
  }

  console.log('✅ Found webSocketAnimationService on window');

  // Trigger a test animation
  window.webSocketAnimationService.triggerTestAnimation('created', 'task');

  console.log('🧪 [TEST] Test animation triggered');
}

// Test function to simulate a real task creation
function testTaskCreationAnimation(taskId = 'test-task-123') {
  console.log('🧪 [TEST] Starting task creation animation test with task ID:', taskId);

  // Manually dispatch the event that would normally come from WebSocket
  const eventDetail = {
    animationType: 'fade-in-right-to-left',
    timestamp: Date.now(),
    taskId: taskId
  };

  console.log('🧪 [TEST] Dispatching task-fade-in event:', eventDetail);

  const customEvent = new CustomEvent('task-fade-in', { detail: eventDetail });
  window.dispatchEvent(customEvent);

  console.log('🧪 [TEST] Event dispatched, check for TaskRow responses');
}

// Test function to list all tasks on the page
function listVisibleTasks() {
  console.log('🧪 [TEST] Listing all visible tasks on the page...');

  // Look for elements that might be TaskRows
  const tableRows = document.querySelectorAll('[class*="cursor-pointer"]');
  const cardElements = document.querySelectorAll('[class*="rounded-lg"]');

  console.log('🧪 [TEST] Found potential task elements:');
  console.log('- Table rows with cursor-pointer:', tableRows.length);
  console.log('- Card elements:', cardElements.length);

  // Try to extract task IDs from elements
  const allElements = [...tableRows, ...cardElements];
  allElements.forEach((element, index) => {
    console.log(`🧪 [TEST] Element ${index}:`, {
      tagName: element.tagName,
      classes: element.className,
      id: element.id,
      innerHTML: element.innerHTML.substring(0, 100) + '...'
    });
  });
}

// Test function to check if animation CSS is loaded
function checkAnimationCSS() {
  console.log('🧪 [TEST] Checking if animation CSS classes are available...');

  // Create a test element to check if CSS classes work
  const testDiv = document.createElement('div');
  testDiv.style.position = 'fixed';
  testDiv.style.top = '-1000px';
  testDiv.style.left = '-1000px';
  testDiv.style.width = '100px';
  testDiv.style.height = '100px';
  testDiv.style.background = 'red';

  document.body.appendChild(testDiv);

  // Check base animation class
  testDiv.className = 'fade-in-right-to-left';
  const computedStyle = window.getComputedStyle(testDiv);

  console.log('🧪 [TEST] CSS check results:', {
    animation: computedStyle.animation,
    animationName: computedStyle.animationName,
    animationDuration: computedStyle.animationDuration,
    transform: computedStyle.transform,
    opacity: computedStyle.opacity
  });

  document.body.removeChild(testDiv);
}

// Main test function
function runAnimationDebugTests() {
  console.log('🧪 [TEST] Starting comprehensive animation debug tests...');

  checkAnimationCSS();
  listVisibleTasks();

  // Wait a bit then test animations
  setTimeout(() => {
    testFadeInAnimation();

    setTimeout(() => {
      testTaskCreationAnimation();
    }, 2000);
  }, 1000);
}

// Expose functions to window for manual testing
window.animationDebugTests = {
  testFadeInAnimation,
  testTaskCreationAnimation,
  listVisibleTasks,
  checkAnimationCSS,
  runAnimationDebugTests
};

console.log('🧪 Animation Debug Test Functions Available:');
console.log('- window.animationDebugTests.runAnimationDebugTests()');
console.log('- window.animationDebugTests.testFadeInAnimation()');
console.log('- window.animationDebugTests.testTaskCreationAnimation("your-task-id")');
console.log('- window.animationDebugTests.listVisibleTasks()');
console.log('- window.animationDebugTests.checkAnimationCSS()');