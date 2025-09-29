/**
 * Test Script: Verify Animation Fix
 *
 * This script tests if the WebSocketAnimationService can now find shimmer elements
 * after updating TaskRow to use ShimmerButton components.
 *
 * Run this in browser console to test:
 * 1. Open the task list page
 * 2. Paste this script in console
 * 3. Check if shimmer elements are found
 */

console.log('🧪 Testing Animation Fix...');

// Test 1: Check if shimmer elements exist
const shimmerElements = document.querySelectorAll('.shimmer-button, [data-shimmer]');
console.log(`📊 Found ${shimmerElements.length} shimmer-capable elements`);

if (shimmerElements.length === 0) {
    console.error('❌ NO SHIMMER ELEMENTS FOUND!');
    console.log('🔍 Looking for alternatives...');

    // Check for regular buttons
    const regularButtons = document.querySelectorAll('button');
    console.log(`Found ${regularButtons.length} regular buttons`);

    // Check for TaskRow components
    const taskRows = document.querySelectorAll('[class*="cursor-pointer"]');
    console.log(`Found ${taskRows.length} potential task rows`);
} else {
    console.log('✅ Shimmer elements found!');
    shimmerElements.forEach((element, index) => {
        console.log(`  ${index + 1}. ${element.tagName} with classes: ${element.className}`);
    });
}

// Test 2: Check if WebSocketAnimationService exists
if (window.webSocketAnimationService) {
    console.log('✅ WebSocketAnimationService is available');

    // Test 3: Trigger a test animation
    try {
        console.log('🎬 Triggering test animation...');
        window.webSocketAnimationService.triggerTestAnimation('created', 'task');
        console.log('✅ Test animation triggered successfully');
    } catch (error) {
        console.error('❌ Failed to trigger test animation:', error);
    }
} else {
    console.warn('⚠️ WebSocketAnimationService not found on window object');
}

// Test 4: Check if animation classes are added
console.log('🎨 Checking for shimmer-active class...');
setTimeout(() => {
    const shimmerActiveElements = document.querySelectorAll('.shimmer-active');
    console.log(`Found ${shimmerActiveElements.length} elements with shimmer-active class`);

    if (shimmerActiveElements.length > 0) {
        console.log('✅ Animation is working! Elements are being animated.');
    } else {
        console.warn('⚠️ No shimmer-active elements found. Animation may not be triggering.');
    }
}, 1000);

console.log('🏁 Animation fix test completed. Check results above.');