/**
 * Test Script for Fixed Animation System
 *
 * This script tests the fixed animation system that coordinates between
 * callback-based and WebSocket-based animations.
 */

console.log('🔧 Testing Fixed Animation System');
console.log('================================');

const testResults = {
    webSocketServiceAvailable: false,
    taskRowsFound: 0,
    coordinationTest: false,
    doubleAnimationPrevention: false,
    webSocketEventTest: false,
    callbackEventTest: false,
    animationTiming: {}
};

// Test 1: Check basic availability
console.log('\n1️⃣ Checking component availability...');

testResults.webSocketServiceAvailable = !!window.webSocketAnimationService;
console.log(`WebSocketAnimationService: ${testResults.webSocketServiceAvailable ? '✅' : '❌'}`);

const taskRows = document.querySelectorAll('[class*="cursor-pointer"]');
testResults.taskRowsFound = taskRows.length;
console.log(`TaskRow elements: ${testResults.taskRowsFound}`);

if (!testResults.webSocketServiceAvailable) {
    console.error('❌ Cannot test - WebSocketAnimationService not available');
    console.log('📝 Make sure the page has loaded and animation service is initialized');
} else {
    // Test 2: Test coordination system
    console.log('\n2️⃣ Testing animation coordination...');

    const testTaskId = 'coordination-test-123';

    // Track animation events
    const animationEvents = [];
    const eventTypes = ['task-fade-in', 'task-fade-out', 'task-content-update'];

    eventTypes.forEach(eventType => {
        const listener = (event) => {
            animationEvents.push({
                type: eventType,
                taskId: event.detail?.taskId,
                timestamp: Date.now(),
                source: 'websocket'
            });
            console.log(`📨 Received ${eventType} for task: ${event.detail?.taskId}`);
        };
        window.addEventListener(eventType, listener);
    });

    // Test 3: Test WebSocket animation dispatch
    console.log('\n3️⃣ Testing WebSocket animation dispatch...');

    try {
        // Create a mock delete message
        const mockMessage = {
            id: `test-${Date.now()}`,
            version: '2.0',
            type: 'update',
            timestamp: new Date().toISOString(),
            sequence: 1,
            payload: {
                entity: 'task',
                action: 'deleted',
                data: {
                    primary: { id: testTaskId }
                }
            },
            metadata: {
                source: 'user',
                entity_id: testTaskId,
                task_title: 'Test Task for Fixed Animation'
            }
        };

        // Dispatch through WebSocket service
        window.webSocketAnimationService.handleWebSocketMessage(mockMessage);
        console.log('✅ WebSocket message dispatched');

        // Wait for events
        setTimeout(() => {
            const webSocketEvents = animationEvents.filter(e => e.source === 'websocket');
            testResults.webSocketEventTest = webSocketEvents.length > 0;
            console.log(`WebSocket events received: ${webSocketEvents.length}`);

            // Test 4: Test double animation prevention
            console.log('\n4️⃣ Testing double animation prevention...');

            if (taskRows.length > 0) {
                const testRow = taskRows[0];

                // Monitor DOM changes
                let classChanges = 0;
                const observer = new MutationObserver((mutations) => {
                    mutations.forEach((mutation) => {
                        if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                            const classList = Array.from(mutation.target.classList);
                            if (classList.some(cls => cls.includes('fade-') || cls.includes('content-update'))) {
                                classChanges++;
                                console.log(`📝 Animation class applied (change #${classChanges})`);
                            }
                        }
                    });
                });

                observer.observe(testRow, { attributes: true, attributeFilter: ['class'] });

                // Try to trigger multiple animations rapidly
                const rapidAnimationTest = () => {
                    // First, try rapid WebSocket events
                    window.dispatchEvent(new CustomEvent('task-fade-out', {
                        detail: { taskId: 'rapid-test', timestamp: Date.now() }
                    }));

                    setTimeout(() => {
                        window.dispatchEvent(new CustomEvent('task-fade-out', {
                            detail: { taskId: 'rapid-test', timestamp: Date.now() }
                        }));
                    }, 50); // 50ms later

                    // Check results after animations
                    setTimeout(() => {
                        observer.disconnect();
                        testResults.doubleAnimationPrevention = classChanges <= 1;
                        console.log(`Animation coordination test: ${testResults.doubleAnimationPrevention ? '✅ Passed' : '❌ Failed'}`);
                        console.log(`Class changes detected: ${classChanges} (should be 1 or less)`);

                        // Test 5: Manual CSS animation test
                        console.log('\n5️⃣ Testing CSS animations directly...');
                        testCSSAnimations();
                    }, 1000);
                };

                rapidAnimationTest();
            }
        }, 500);

    } catch (error) {
        console.error('❌ WebSocket animation test failed:', error.message);
        testResults.webSocketEventTest = false;
    }
}

// Function to test CSS animations directly
function testCSSAnimations() {
    if (taskRows.length === 0) {
        console.warn('⚠️ No task rows available for CSS testing');
        return;
    }

    const testRow = taskRows[0];
    const originalClass = testRow.className;

    console.log('🎨 Testing CSS animation classes...');

    const animationClasses = [
        'fade-in-right-to-left',
        'fade-out-left-to-right',
        'content-update'
    ];

    let currentIndex = 0;

    function testNextAnimation() {
        if (currentIndex >= animationClasses.length) {
            // All tests complete
            testRow.className = originalClass;
            generateFinalReport();
            return;
        }

        const className = animationClasses[currentIndex];
        console.log(`Testing ${className}...`);

        // Add the class
        testRow.classList.add(className);

        // Check if animation is active
        setTimeout(() => {
            const computedStyle = window.getComputedStyle(testRow);
            const animationName = computedStyle.animationName;
            const isAnimating = animationName && animationName !== 'none';

            console.log(`  ${className}: ${isAnimating ? '✅ Working' : '❌ Not working'}`);
            testResults.animationTiming[className] = isAnimating;

            // Remove class and test next
            testRow.classList.remove(className);
            currentIndex++;

            setTimeout(() => testNextAnimation(), 300);
        }, 100);
    }

    testNextAnimation();
}

// Generate final report
function generateFinalReport() {
    console.log('\n📊 FINAL TEST REPORT');
    console.log('====================');

    console.log('\n✅ PASSED TESTS:');
    Object.entries(testResults).forEach(([test, result]) => {
        if (result === true || (typeof result === 'number' && result > 0)) {
            console.log(`  • ${test}: ${result}`);
        }
    });

    console.log('\n❌ FAILED TESTS:');
    Object.entries(testResults).forEach(([test, result]) => {
        if (result === false || (typeof result === 'number' && result === 0)) {
            console.log(`  • ${test}: ${result}`);
        }
    });

    console.log('\n🔍 CSS ANIMATION TESTS:');
    Object.entries(testResults.animationTiming).forEach(([className, working]) => {
        console.log(`  • ${className}: ${working ? '✅' : '❌'}`);
    });

    // Overall assessment
    const totalTests = Object.keys(testResults).length - 1; // Exclude animationTiming object
    const passedTests = Object.values(testResults).filter(r => r === true || (typeof r === 'number' && r > 0)).length;

    console.log(`\n🎯 OVERALL: ${passedTests}/${totalTests} tests passed`);

    if (passedTests === totalTests && Object.values(testResults.animationTiming).every(r => r)) {
        console.log('🎉 ALL TESTS PASSED! Animation system is working correctly.');
    } else {
        console.log('⚠️ Some tests failed. Check the issues above for troubleshooting.');
    }

    // Export results for further analysis
    window.fixedAnimationTestResults = testResults;
}

console.log('\n🚀 Starting fixed animation system tests...');

// Start the test after a brief delay
setTimeout(() => {
    if (!testResults.webSocketServiceAvailable) {
        generateFinalReport();
    }
    // Other tests are triggered in the chain above
}, 500);