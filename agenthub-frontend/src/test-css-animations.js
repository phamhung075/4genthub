/**
 * CSS Animation Tester
 *
 * This script tests if the CSS animations work independently of the WebSocket system.
 * Run this in the browser console to test CSS animation classes directly.
 */

console.log('🎨 CSS Animation Tester Started');
console.log('================================');

// Find potential task row elements
const taskRows = document.querySelectorAll('[class*="cursor-pointer"]');
console.log(`📋 Found ${taskRows.length} potential task rows`);

if (taskRows.length === 0) {
    console.warn('⚠️ No task rows found. Make sure you are on a page with tasks.');
    // Create a test element instead
    const testElement = document.createElement('div');
    testElement.style.cssText = `
        width: 200px;
        height: 50px;
        background: #3b82f6;
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 20px;
        border-radius: 8px;
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
    `;
    testElement.textContent = 'Animation Test Element';
    testElement.id = 'css-animation-test';
    document.body.appendChild(testElement);

    // Use the test element for animations
    taskRows = [testElement];
    console.log('✅ Created test element for animation testing');
}

// Test function for each animation class
function testAnimationClass(element, className, duration = 2000) {
    return new Promise((resolve) => {
        console.log(`🎬 Testing animation: ${className}`);

        // Record initial state
        const initialStyle = {
            opacity: element.style.opacity || window.getComputedStyle(element).opacity,
            transform: element.style.transform || window.getComputedStyle(element).transform
        };

        // Add animation class
        element.classList.add(className);
        console.log(`  ➕ Added class: ${className}`);

        // Check if animation is active
        setTimeout(() => {
            const computedStyle = window.getComputedStyle(element);
            const animationName = computedStyle.animationName;
            const animationDuration = computedStyle.animationDuration;

            if (animationName && animationName !== 'none') {
                console.log(`  ✅ Animation active: ${animationName} (${animationDuration})`);
            } else {
                console.log(`  ❌ No animation detected for class: ${className}`);
            }
        }, 100);

        // Remove class after animation completes
        setTimeout(() => {
            element.classList.remove(className);
            console.log(`  ➖ Removed class: ${className}`);
            resolve();
        }, duration);
    });
}

// Test all animation classes sequentially
async function runAnimationTests() {
    const testElement = taskRows[0];

    console.log('\n🎬 Starting animation tests...\n');

    const animationsToTest = [
        { className: 'fade-in-right-to-left', duration: 600 },
        { className: 'fade-out-left-to-right', duration: 800 },
        { className: 'content-update', duration: 1200 }
    ];

    for (const { className, duration } of animationsToTest) {
        await testAnimationClass(testElement, className, duration);

        // Wait a bit between animations
        await new Promise(resolve => setTimeout(resolve, 500));
    }

    console.log('\n✅ Animation tests completed!');

    // Remove test element if we created it
    const testEl = document.getElementById('css-animation-test');
    if (testEl) {
        setTimeout(() => {
            testEl.remove();
            console.log('🧹 Cleaned up test element');
        }, 2000);
    }
}

// Test CSS keyframes existence
function checkCSSKeyframes() {
    console.log('\n🔍 Checking for CSS keyframes...');

    const expectedKeyframes = [
        'fadeInRightToLeft',
        'fadeOutLeftToRight',
        'contentUpdateFlash'
    ];

    const styleSheets = Array.from(document.styleSheets);
    const foundKeyframes = [];

    try {
        for (const sheet of styleSheets) {
            try {
                const rules = Array.from(sheet.cssRules || sheet.rules || []);
                for (const rule of rules) {
                    if (rule.type === CSSRule.KEYFRAMES_RULE) {
                        foundKeyframes.push(rule.name);
                        console.log(`  ✅ Found keyframe: ${rule.name}`);
                    }
                }
            } catch (e) {
                // Cross-origin stylesheet, skip
            }
        }
    } catch (e) {
        console.warn('⚠️ Could not check CSS rules:', e.message);
    }

    expectedKeyframes.forEach(keyframe => {
        if (!foundKeyframes.includes(keyframe)) {
            console.log(`  ❌ Missing keyframe: ${keyframe}`);
        }
    });

    return foundKeyframes;
}

// Run all tests
checkCSSKeyframes();
runAnimationTests();

// Export test functions for manual testing
window.testCSSAnimations = {
    testAnimationClass,
    runAnimationTests,
    checkCSSKeyframes
};