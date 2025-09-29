// Manual test for real-time updates fix
// Run this in browser console to test WebSocket real-time updates

console.log('🧪 Testing Real-time Updates Fix');

// Simulate a WebSocket notification for task creation
function testTaskCreation() {
  console.log('📤 Testing task creation...');

  const createNotification = {
    entityType: 'task',
    entityId: 'test-task-' + Date.now(),
    eventType: 'created',
    userId: 'test-user',
    data: {
      id: 'test-task-' + Date.now(),
      title: 'Real-time Test Task',
      status: 'todo',
      priority: 'high',
      subtasks: [],
      assignees: ['test-agent'],
      dependencies: [],
      context_id: 'test-ctx',
      created_at: new Date().toISOString()
    },
    metadata: {
      git_branch_id: 'current-branch',  // Should match current LazyTaskList branch
      project_id: 'current-project'
    },
    timestamp: new Date().toISOString()
  };

  // Access the changePoolService globally (should be available)
  if (window.changePoolService) {
    window.changePoolService.processChange(createNotification);
    console.log('✅ Create notification sent');
  } else {
    console.error('❌ changePoolService not found on window');
  }
}

// Simulate a WebSocket notification for task update
function testTaskUpdate() {
  console.log('📤 Testing task update...');

  // Get first task ID from current list
  const taskRows = document.querySelectorAll('[data-testid*="task-"]');
  if (taskRows.length === 0) {
    console.error('❌ No tasks found to update');
    return;
  }

  const firstTaskId = taskRows[0].getAttribute('data-testid')?.replace('task-row-', '');
  if (!firstTaskId) {
    console.error('❌ Could not extract task ID');
    return;
  }

  const updateNotification = {
    entityType: 'task',
    entityId: firstTaskId,
    eventType: 'updated',
    userId: 'test-user',
    data: {
      id: firstTaskId,
      title: 'UPDATED VIA WEBSOCKET - ' + new Date().toLocaleTimeString(),
      status: 'in_progress',
      priority: 'critical',
      subtasks: [],
      assignees: ['updated-agent'],
      dependencies: [],
      context_id: 'updated-ctx'
    },
    metadata: {
      git_branch_id: 'current-branch',
      project_id: 'current-project'
    },
    timestamp: new Date().toISOString()
  };

  if (window.changePoolService) {
    window.changePoolService.processChange(updateNotification);
    console.log('✅ Update notification sent for task:', firstTaskId);
  } else {
    console.error('❌ changePoolService not found on window');
  }
}

// Simulate a WebSocket notification for task deletion
function testTaskDeletion() {
  console.log('📤 Testing task deletion...');

  // Get last task ID from current list
  const taskRows = document.querySelectorAll('[data-testid*="task-"]');
  if (taskRows.length === 0) {
    console.error('❌ No tasks found to delete');
    return;
  }

  const lastTaskId = taskRows[taskRows.length - 1].getAttribute('data-testid')?.replace('task-row-', '');
  if (!lastTaskId) {
    console.error('❌ Could not extract task ID');
    return;
  }

  const deleteNotification = {
    entityType: 'task',
    entityId: lastTaskId,
    eventType: 'deleted',
    userId: 'test-user',
    metadata: {
      git_branch_id: 'current-branch',
      project_id: 'current-project'
    },
    timestamp: new Date().toISOString()
  };

  if (window.changePoolService) {
    window.changePoolService.processChange(deleteNotification);
    console.log('✅ Delete notification sent for task:', lastTaskId);
  } else {
    console.error('❌ changePoolService not found on window');
  }
}

// Export functions to window for manual testing
window.testTaskCreation = testTaskCreation;
window.testTaskUpdate = testTaskUpdate;
window.testTaskDeletion = testTaskDeletion;

console.log('🎮 Manual test functions available:');
console.log('- testTaskCreation(): Create a new task via WebSocket');
console.log('- testTaskUpdate(): Update first task via WebSocket');
console.log('- testTaskDeletion(): Delete last task via WebSocket');
console.log('');
console.log('📋 Instructions:');
console.log('1. Open LazyTaskList component in browser');
console.log('2. Open console and run this script');
console.log('3. Call test functions to see real-time updates');
console.log('4. Tasks should update WITHOUT page refresh!');