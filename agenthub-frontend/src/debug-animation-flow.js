/**
 * Complete Animation Flow Debugger
 *
 * This script traces the entire animation flow from WebSocket message to visual effect.
 * It helps identify exactly where the animation system breaks.
 */

console.log('🔍 Animation Flow Debugger Started');
console.log('==================================');

// Create a detailed debug log
const debugLog = [];
function addLog(step, message, data = null) {
    const entry = { step, message, data, timestamp: Date.now() };
    debugLog.push(entry);
    console.log(`[${step}] ${message}`, data || '');
}

// Test 1: Verify all components are available
addLog('INIT', 'Checking component availability...');

const hasWebSocketService = !!window.webSocketAnimationService;
addLog('INIT', `WebSocketAnimationService: ${hasWebSocketService ? '✅ Available' : '❌ Missing'}`);

const taskRows = document.querySelectorAll('[class*="cursor-pointer"]');
addLog('INIT', `TaskRow elements found: ${taskRows.length}`);

// Test 2: Create a mock WebSocket message for testing
const createMockDeleteMessage = (taskId = 'test-task-123') => {
    return {
        id: `mock-${Date.now()}`,
        version: '2.0',
        type: 'update',
        timestamp: new Date().toISOString(),
        sequence: 1,
        payload: {
            entity: 'task',
            action: 'deleted',
            data: {
                primary: { id: taskId },
                cascade: {
                    tasks: [],
                    subtasks: []
                }
            }
        },
        metadata: {
            source: 'user',
            entity_id: taskId,
            task_title: 'Test Task for Animation',
            parent_branch_title: 'Test Branch'
        }
    };
};

// Test 3: Hook into WebSocket events to monitor the flow
addLog('MONITOR', 'Setting up WebSocket event monitoring...');

// Monitor custom events
const eventTypes = ['task-fade-in', 'task-fade-out', 'task-content-update', 'task-celebration'];
const eventListeners = {};

eventTypes.forEach(eventType => {
    const listener = (event) => {
        addLog('EVENT', `CustomEvent received: ${eventType}`, {
            taskId: event.detail?.taskId,
            animationType: event.detail?.animationType,
            timestamp: event.detail?.timestamp
        });
    };

    window.addEventListener(eventType, listener);
    eventListeners[eventType] = listener;
    addLog('MONITOR', `Listening for: ${eventType}`);
});

// Test 4: Monitor DOM mutations to see if classes are applied
addLog('MONITOR', 'Setting up DOM mutation observer...');

const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
            const element = mutation.target;
            const classList = Array.from(element.classList);
            const animationClasses = classList.filter(cls =>
                cls.includes('fade-') || cls.includes('content-update') || cls.includes('celebration')
            );

            if (animationClasses.length > 0) {
                addLog('DOM', `Animation classes applied to element`, {
                    element: element.tagName,
                    classes: animationClasses,
                    allClasses: classList
                });
            }
        }
    });
});

// Start observing
taskRows.forEach(row => {
    observer.observe(row, { attributes: true, attributeFilter: ['class'] });
});

// Test 5: Function to simulate complete animation flow
async function simulateAnimationFlow(taskId = 'test-task-456') {
    addLog('TEST', '🎬 Starting complete animation flow simulation...');

    if (!window.webSocketAnimationService) {
        addLog('ERROR', 'Cannot test - WebSocketAnimationService not available');
        return;
    }

    // Step 1: Create mock message
    const mockMessage = createMockDeleteMessage(taskId);
    addLog('TEST', 'Created mock WebSocket message', mockMessage);

    // Step 2: Simulate WebSocket message processing
    try {
        addLog('TEST', 'Simulating WebSocket message processing...');

        // Call the same method that would be called by the WebSocket
        window.webSocketAnimationService.handleWebSocketMessage(mockMessage);
        addLog('TEST', '✅ WebSocket message processed');

    } catch (error) {
        addLog('ERROR', 'Failed to process WebSocket message', error.message);
    }

    // Step 3: Wait and check for CustomEvent
    await new Promise(resolve => setTimeout(resolve, 100));

    // Step 4: Manually dispatch CustomEvent to test listener registration
    addLog('TEST', 'Manually dispatching CustomEvent...');

    window.dispatchEvent(new CustomEvent('task-fade-out', {
        detail: {
            animationType: 'fade-out-left-to-right',
            timestamp: Date.now(),
            taskId: taskId
        }
    }));

    // Step 5: Wait and check for DOM changes
    await new Promise(resolve => setTimeout(resolve, 500));

    // Step 6: Try to manually add animation class to test CSS
    if (taskRows.length > 0) {
        addLog('TEST', 'Testing manual CSS class application...');
        const testRow = taskRows[0];

        testRow.classList.add('fade-out-left-to-right');
        addLog('TEST', 'Added fade-out-left-to-right class manually');

        // Check if animation is active
        setTimeout(() => {
            const computedStyle = window.getComputedStyle(testRow);
            const animationName = computedStyle.animationName;

            if (animationName && animationName !== 'none') {
                addLog('TEST', '✅ CSS animation is working', { animationName });
            } else {
                addLog('ERROR', '❌ CSS animation not detected');
            }

            // Clean up
            testRow.classList.remove('fade-out-left-to-right');
        }, 200);
    }
}

// Test 6: Function to generate detailed report
function generateReport() {
    console.log('\n📊 ANIMATION FLOW DEBUG REPORT');
    console.log('===============================');

    // Group logs by step
    const groupedLogs = {};
    debugLog.forEach(log => {
        if (!groupedLogs[log.step]) {
            groupedLogs[log.step] = [];
        }
        groupedLogs[log.step].push(log);
    });

    // Display grouped logs
    Object.keys(groupedLogs).forEach(step => {
        console.log(`\n[${step}]`);
        groupedLogs[step].forEach(log => {
            console.log(`  ${log.message}`, log.data || '');
        });
    });

    // Identify potential issues
    console.log('\n🔍 POTENTIAL ISSUES:');

    const hasWebSocketService = debugLog.some(log =>
        log.step === 'INIT' && log.message.includes('WebSocketAnimationService') && log.message.includes('✅')
    );

    const hasTaskRows = debugLog.some(log =>
        log.step === 'INIT' && log.message.includes('TaskRow elements') && log.data > 0
    );

    const hasCustomEvents = debugLog.some(log => log.step === 'EVENT');
    const hasDOMChanges = debugLog.some(log => log.step === 'DOM');

    if (!hasWebSocketService) {
        console.log('  ❌ WebSocketAnimationService not available');
    }

    if (!hasTaskRows) {
        console.log('  ⚠️ No TaskRow elements found on page');
    }

    if (!hasCustomEvents) {
        console.log('  ❌ No CustomEvents detected');
    }

    if (!hasDOMChanges) {
        console.log('  ❌ No DOM class changes detected');
    }

    // Recommendations
    console.log('\n💡 RECOMMENDATIONS:');

    if (!hasWebSocketService) {
        console.log('  • Ensure WebSocketAnimationService is properly imported and initialized');
    }

    if (!hasCustomEvents) {
        console.log('  • Check if WebSocketAnimationService is correctly dispatching events');
        console.log('  • Verify CustomEvent names match between service and TaskRow listeners');
    }

    if (!hasDOMChanges) {
        console.log('  • Check if TaskRow components are listening for CustomEvents');
        console.log('  • Verify animation CSS classes are being applied');
    }

    return groupedLogs;
}

// Test 7: Run the complete test
console.log('\n🚀 Running complete animation flow test...');

// Wait a bit for initial setup, then run simulation
setTimeout(() => {
    simulateAnimationFlow().then(() => {
        // Wait for all async operations to complete
        setTimeout(() => {
            const report = generateReport();

            // Cleanup
            eventTypes.forEach(eventType => {
                window.removeEventListener(eventType, eventListeners[eventType]);
            });
            observer.disconnect();

            // Export results
            window.animationFlowDebugResults = {
                logs: debugLog,
                report: report,
                simulateAnimationFlow,
                generateReport
            };

            console.log('\n✅ Animation flow debug complete!');
            console.log('Results available in: window.animationFlowDebugResults');

        }, 1000);
    });
}, 500);