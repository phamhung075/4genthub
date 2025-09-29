/**
 * Comprehensive Animation System Debugger
 *
 * This script tests the entire animation flow to identify where the system breaks.
 * Run this in the browser console on a page with TaskRow components.
 */

console.log('🔧 Animation System Debugger Started');
console.log('==========================================');

// Global state for debugging
const debugState = {
    findings: [],
    errors: [],
    warnings: []
};

function addFinding(type, message) {
    debugState[type].push(message);
    console.log(`${type === 'findings' ? '✅' : type === 'errors' ? '❌' : '⚠️'} ${message}`);
}

// Test 1: Check if WebSocketAnimationService is available
console.log('\n1️⃣ Testing WebSocketAnimationService availability...');
if (window.webSocketAnimationService) {
    addFinding('findings', 'WebSocketAnimationService is available on window object');
} else {
    addFinding('errors', 'WebSocketAnimationService NOT found on window object');
    // Try to access via import
    try {
        const serviceModule = await import('./services/WebSocketAnimationService.js');
        if (serviceModule.webSocketAnimationService) {
            addFinding('findings', 'WebSocketAnimationService found via import');
            window.webSocketAnimationService = serviceModule.webSocketAnimationService;
        }
    } catch (e) {
        addFinding('errors', 'Cannot import WebSocketAnimationService: ' + e.message);
    }
}

// Test 2: Check DOM elements and CSS
console.log('\n2️⃣ Testing DOM structure and CSS...');

// Find TaskRow components
const taskRows = document.querySelectorAll('[class*="cursor-pointer"]');
addFinding('findings', `Found ${taskRows.length} potential TaskRow elements`);

// Check if CSS animation classes are loaded
const styleSheets = Array.from(document.styleSheets);
let animationCSSFound = false;

try {
    for (const sheet of styleSheets) {
        try {
            const rules = Array.from(sheet.cssRules || sheet.rules || []);
            for (const rule of rules) {
                if (rule.selectorText && (
                    rule.selectorText.includes('fade-in-right-to-left') ||
                    rule.selectorText.includes('fade-out-left-to-right') ||
                    rule.selectorText.includes('content-update')
                )) {
                    animationCSSFound = true;
                    addFinding('findings', `Animation CSS found: ${rule.selectorText}`);
                }
            }
        } catch (e) {
            // Cross-origin CSS, skip
        }
    }
} catch (e) {
    addFinding('warnings', 'Could not check CSS rules: ' + e.message);
}

if (!animationCSSFound) {
    addFinding('errors', 'Animation CSS classes not found in stylesheets');
}

// Test 3: Check WebSocket connection
console.log('\n3️⃣ Testing WebSocket connection...');
if (window.webSocketClient || window.globalWebSocketClient) {
    const client = window.webSocketClient || window.globalWebSocketClient;
    addFinding('findings', 'WebSocket client found');

    if (client.isConnected && client.isConnected()) {
        addFinding('findings', 'WebSocket is connected');
    } else {
        addFinding('warnings', 'WebSocket client exists but may not be connected');
    }
} else {
    addFinding('warnings', 'WebSocket client not found on window object');
}

// Test 4: Test CustomEvent system
console.log('\n4️⃣ Testing CustomEvent dispatch and listening...');

let eventReceived = false;
const testEventType = 'test-animation-debug';

// Add test listener
const testListener = (event) => {
    eventReceived = true;
    addFinding('findings', 'CustomEvent test successful - event received');
    console.log('📨 Test event detail:', event.detail);
};

window.addEventListener(testEventType, testListener);

// Dispatch test event
window.dispatchEvent(new CustomEvent(testEventType, {
    detail: { test: true, timestamp: Date.now() }
}));

// Check if event was received
setTimeout(() => {
    if (eventReceived) {
        addFinding('findings', 'CustomEvent system is working');
    } else {
        addFinding('errors', 'CustomEvent system failed - event not received');
    }

    // Cleanup
    window.removeEventListener(testEventType, testListener);
}, 100);

// Test 5: Test TaskRow event listeners
console.log('\n5️⃣ Testing TaskRow event listeners...');

// Check if any elements have animation event listeners
const taskRowsWithListeners = [];
taskRows.forEach((row, index) => {
    // Look for React props that might indicate event listeners
    const reactProps = Object.keys(row).find(key => key.startsWith('__reactInternalInstance') || key.startsWith('_reactInternalFiber'));
    if (reactProps) {
        taskRowsWithListeners.push(index);
    }
});

addFinding('findings', `Found ${taskRowsWithListeners.length} TaskRows with potential React listeners`);

// Test 6: Simulate WebSocket animation events
console.log('\n6️⃣ Testing animation event simulation...');

if (window.webSocketAnimationService) {
    try {
        // Test different animation types
        const testAnimations = [
            { type: 'created', eventName: 'task-fade-in' },
            { type: 'updated', eventName: 'task-content-update' },
            { type: 'deleted', eventName: 'task-fade-out' }
        ];

        testAnimations.forEach(({ type, eventName }) => {
            console.log(`🎬 Testing ${type} animation...`);

            // Listen for the dispatched event
            let eventCaught = false;
            const animationListener = (event) => {
                eventCaught = true;
                addFinding('findings', `${type} animation event dispatched successfully`);
                console.log(`📨 ${eventName} event detail:`, event.detail);
            };

            window.addEventListener(eventName, animationListener);

            // Trigger the animation
            if (window.webSocketAnimationService.triggerTestAnimation) {
                window.webSocketAnimationService.triggerTestAnimation(type, 'task');
            }

            // Check and cleanup
            setTimeout(() => {
                if (!eventCaught) {
                    addFinding('errors', `${type} animation event was NOT dispatched`);
                }
                window.removeEventListener(eventName, animationListener);
            }, 500);
        });
    } catch (error) {
        addFinding('errors', 'Animation simulation failed: ' + error.message);
    }
} else {
    addFinding('errors', 'Cannot test animations - WebSocketAnimationService not available');
}

// Test 7: Check for CSS class application
console.log('\n7️⃣ Testing CSS class application...');

// Try to manually add animation classes to see if they work
if (taskRows.length > 0) {
    const testRow = taskRows[0];
    const originalClasses = testRow.className;

    // Test fade-in animation
    testRow.classList.add('fade-in-right-to-left');
    addFinding('findings', 'Added fade-in-right-to-left class to first TaskRow');

    setTimeout(() => {
        // Check if styles are applied
        const computedStyle = window.getComputedStyle(testRow);
        const hasAnimation = computedStyle.animationName !== 'none';

        if (hasAnimation) {
            addFinding('findings', 'CSS animation is active on test element');
        } else {
            addFinding('errors', 'CSS animation class added but no animation detected');
        }

        // Restore original classes
        testRow.className = originalClasses;
    }, 100);
}

// Test 8: Check task ID extraction from mock WebSocket message
console.log('\n8️⃣ Testing task ID extraction...');

const mockMessage = {
    id: 'test-message-123',
    version: '2.0',
    type: 'update',
    timestamp: new Date().toISOString(),
    sequence: 1,
    payload: {
        entity: 'task',
        action: 'deleted',
        data: {
            primary: { id: 'test-task-456' },
            id: 'fallback-task-789'
        }
    },
    metadata: {
        source: 'user',
        entity_id: 'metadata-task-101',
        task_title: 'Test Task',
        parent_branch_title: 'Test Branch'
    }
};

// Test the same ID extraction logic as WebSocketAnimationService
const primaryId = mockMessage.payload?.data?.primary?.id;
const directDataId = mockMessage.payload?.data?.id;
const metadataId = mockMessage.metadata?.entity_id;
const extractedTaskId = primaryId || directDataId || metadataId;

addFinding('findings', `Task ID extraction test: ${extractedTaskId} (from ${primaryId ? 'primary' : directDataId ? 'data' : 'metadata'})`);

// Test 9: Summary and Recommendations
console.log('\n9️⃣ Generating summary and recommendations...');

setTimeout(() => {
    console.log('\n🔍 DEBUG SUMMARY');
    console.log('================');

    console.log('\n✅ FINDINGS:');
    debugState.findings.forEach(finding => console.log(`  • ${finding}`));

    console.log('\n❌ ERRORS:');
    debugState.errors.forEach(error => console.log(`  • ${error}`));

    console.log('\n⚠️ WARNINGS:');
    debugState.warnings.forEach(warning => console.log(`  • ${warning}`));

    console.log('\n🔧 RECOMMENDATIONS:');

    if (debugState.errors.includes('WebSocketAnimationService NOT found on window object')) {
        console.log('  • Export webSocketAnimationService to window object for global access');
    }

    if (debugState.errors.includes('Animation CSS classes not found in stylesheets')) {
        console.log('  • Verify websocket-animations.css is properly imported');
    }

    if (debugState.errors.some(e => e.includes('animation event was NOT dispatched'))) {
        console.log('  • Check WebSocketAnimationService event dispatch logic');
    }

    if (debugState.errors.some(e => e.includes('no animation detected'))) {
        console.log('  • Verify CSS animation keyframes are properly defined');
    }

    console.log('\n🏁 Animation Debug Complete');
}, 2000);

// Export debug results for further analysis
window.animationDebugResults = debugState;