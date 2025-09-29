# Animation Debug Test Instructions

## Current Status
Enhanced debug logging has been added to both WebSocketAnimationService and TaskRow components. The development server is running with hot reload enabled.

## How to Test the Animation System

### Step 1: Open the Browser
1. Navigate to http://localhost:3800
2. Open browser Developer Tools (F12)
3. Go to the Console tab

### Step 2: Check for TaskRow Components
Look for these log messages in the console:
```
🎬 [TaskRow] EVENT LISTENERS SETUP for task: {taskId: "...", componentMounted: true, ...}
```
This confirms TaskRow components are mounted and listening for events.

### Step 3: Manual Animation Test
In the browser console, run:
```javascript
// Test 1: Check if WebSocketAnimationService is available
console.log('WebSocket Animation Service:', window.webSocketAnimationService);

// Test 2: Trigger a test animation
window.webSocketAnimationService.triggerTestAnimation('created', 'task');

// Test 3: Manual event dispatch with specific task ID
// (Replace 'ACTUAL_TASK_ID' with a real task ID from the page)
window.dispatchEvent(new CustomEvent('task-fade-in', {
  detail: {
    animationType: 'fade-in-right-to-left',
    timestamp: Date.now(),
    taskId: 'ACTUAL_TASK_ID'  // Use a real task ID from the page
  }
}));
```

### Step 4: Check Debug Output
Look for these debug messages after running the test:

1. **WebSocketAnimationService dispatch:**
```
🎬 [WebSocketAnimationService] DISPATCHING task-fade-in event: {eventType: "task-fade-in", taskId: "...", ...}
```

2. **TaskRow event reception:**
```
🎬 [TaskRow] WEBSOCKET FADE-IN EVENT RECEIVED: {thisTaskId: "...", eventTaskId: "...", matches: true/false}
```

3. **Animation coordination check:**
```
🎬 [TaskRow] ANIMATION COORDINATION CHECK: {condition1: "PASS/FAIL", condition2: "PASS/FAIL", finalDecision: "ALLOW/BLOCK"}
```

4. **Animation state changes:**
```
🎬 [TaskRow] Animation state changed: {taskId: "...", newState: "creating", isVisible: true}
```

5. **CSS class application:**
```
🎬 [TaskRow] CSS CLASSES for "creating" animation: {classes: "transition-all duration-200 fade-in-right-to-left"}
```

### Step 5: Find Actual Task IDs
To get real task IDs from the page, run:
```javascript
// Look for TaskRow event listener setups
// The console should show: 🎬 [TaskRow] EVENT LISTENERS SETUP for task: {taskId: "actual-id"}
```

### Expected Results

**✅ Working Animation:**
- Event dispatched by WebSocketAnimationService
- Event received by matching TaskRow component
- Animation coordination allows the animation
- Animation state changes to "creating"
- CSS classes applied: "fade-in-right-to-left"
- Visual animation occurs in the UI

**❌ Broken Animation (what we're debugging):**
- Event dispatched by WebSocketAnimationService ✅
- Event NOT received by TaskRow components ❌
- OR Event received but coordination blocks it ❌
- OR State changes but CSS classes not applied ❌

### Debugging Guide

**If no TaskRow components found:**
- No task list is rendered
- Navigate to a page with tasks
- Check that tasks are loaded

**If events dispatched but not received:**
- Task ID mismatch between event and components
- Event listeners not properly attached
- Component unmounted before event arrives

**If events received but animation blocked:**
- Animation coordination logic preventing execution
- Check the coordination check logs for details

**If state changes but no visual animation:**
- CSS classes not properly applied
- CSS animation styles not loaded
- DOM element not responding to class changes

## Current Suspected Issues

Based on analysis, the most likely issues are:

1. **Timing Issue**: WebSocket events fire before TaskRow components mount
2. **Task ID Mismatch**: Event task IDs don't match component task IDs
3. **Animation Coordination**: `shouldAllowAnimation()` incorrectly blocking WebSocket animations
4. **CSS Loading**: Animation classes applied but CSS not working

The enhanced debug logging will help identify which of these is the actual root cause.