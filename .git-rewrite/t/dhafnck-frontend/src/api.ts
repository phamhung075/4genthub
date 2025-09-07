// API service for MCP Task Management
// Handles CRUD for tasks, subtasks, and dependencies

import Cookies from 'js-cookie';
import { taskApiV2, projectApiV2, isAuthenticated } from './services/apiV2';
import { mcpTokenService } from './services/mcpTokenService';

const API_BASE = "http://localhost:8000/mcp/";

// Check if user isolation is enabled (user is authenticated)
const shouldUseV2Api = () => {
  const authenticated = isAuthenticated();
  console.log('shouldUseV2Api check:', { authenticated, hasToken: !!Cookies.get('access_token') });
  return authenticated;
};

// --- Interfaces for Type Safety ---
export interface Task {
    id: string;
    title: string;
    description: string;
    status: string;
    priority: string;
    subtasks: string[]; // Now just IDs following new architecture
    assignees?: string[];
    dependencies?: string[];
    dependency_relationships?: {
        depends_on: string[];
        blocks: string[];
        dependency_chains?: string[][];
    };
    context_data?: any; // Explicitly define context_data
    context_id?: string; // Context ID for the task
    git_branch_id?: string; // Git branch ID
    details?: string; // Additional details
    labels?: string[]; // Task labels
    estimated_effort?: string; // Estimated effort
    due_date?: string; // Due date
    created_at?: string; // Creation timestamp
    updated_at?: string; // Last update timestamp
    [key: string]: any;
}

export interface Subtask {
    id: string;
    title: string;
    description: string;
    status: string;
    priority: string;
    assignees?: string[];
    [key: string]: any;
}

export interface Project {
    id: string;
    name: string;
    description: string;
    git_branchs: Record<string, Branch>;
}

export interface Branch {
    id: string;
    name: string;
    description: string;
    task_count?: number;
}

// --- API Fetch Functions ---

// Function to fetch all projects
export async function fetchProjects(): Promise<Project[]> {
    return listProjects();
}

// Function to fetch details for a single project, including branches (task trees)
export async function fetchProjectDetails(projectId: string): Promise<Project | null> {
    return getProject(projectId);
}


// Function to fetch tasks for a specific project and branch
export async function fetchTasks(_projectId: string, _branchName: string): Promise<Task[]> {
    // Backend doesn't support project filtering yet, returns all tasks
    return listTasks();
}

// Function to fetch subtasks for a specific task
export async function fetchSubtasks(_projectId: string, _branchName: string, taskId: string): Promise<Subtask[]> {
    return listSubtasks(taskId);
}

export type Rule = {
  id: string;
  name: string;
  description?: string;
  type?: string;
  content?: string;
  [key: string]: any;
};

let rpcId = 1;

function getRpcId() {
  return rpcId++;
}


// --- MCP Protocol Headers Helper ---
const MCP_HEADERS = {
  "Content-Type": "application/json",
  "Accept": "application/json, text/event-stream",
  "MCP-Protocol-Version": "2025-06-18",
};

async function withMcpHeaders(extra: Record<string, string> = {}): Promise<Record<string, string>> {
  const headers: Record<string, string> = { ...MCP_HEADERS, ...extra };
  
  // Add MCP token authentication header if available
  try {
    const mcpToken = await mcpTokenService.getMCPToken();
    if (mcpToken) {
      headers['X-MCP-Token'] = mcpToken;
    }
  } catch (error) {
    console.warn('Failed to get MCP token:', error);
    // Fallback to JWT token if MCP token fails
    const token = Cookies.get('access_token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }
  
  return headers;
}

// Get task count for a branch
export async function getTaskCount(git_branch_id: string): Promise<number> {
  const tasks = await listTasks({ git_branch_id });
  return tasks.length;
}

// --- Task Management ---
export async function listTasks(params: any = {}): Promise<Task[]> {
  // Use V2 API if authenticated (same pattern as listProjects)
  const useV2 = shouldUseV2Api();
  if (useV2) {
    try {
      console.log('Attempting V2 API for listTasks with params:', params);
      
      // Extract git_branch_id from params for V2 API
      const { git_branch_id } = params;
      const v2Params = git_branch_id ? { git_branch_id } : undefined;
      
      console.log('V2 API params:', v2Params);
      const response: any = await taskApiV2.getTasks(v2Params);
      console.log('V2 API response:', response);
      
      if (response && Array.isArray(response)) {
        console.log('V2 API success: returning array response');
        return response;
      }
      if (response && response.tasks && Array.isArray(response.tasks)) {
        console.log('V2 API success: returning response.tasks');
        return response.tasks;
      }
      console.log('V2 API success but no valid tasks array, returning empty array');
      return [];
    } catch (error) {
      console.error('V2 API error, falling back to V1:', error);
      // Fall through to V1 API
    }
  }
  
  console.log('Using V1 API for listTasks...');
  
  const { git_branch_id, ...rest } = params;
  const filteredParams = {
    action: "list",
    // Remove git_branch_name as it's not a valid parameter - backend returns all tasks
    ...(git_branch_id ? { git_branch_id } : {}),
    ...rest
  };
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_task",
      arguments: filteredParams
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  console.log('Raw MCP response for listTasks:', data);
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      console.log('Parsed listTasks response:', toolResult);
      if (toolResult.success) {
        const data = extractResponseData(toolResult);
        console.log('Extracted response data:', data);
        if (Array.isArray(data.tasks)) {
          console.log('Tasks before sanitization:', data.tasks);
          // Sanitize each task to remove non-serializable properties
          const sanitizedTasks = data.tasks.map(sanitizeTask);
          console.log('Tasks after sanitization:', sanitizedTasks);
          return sanitizedTasks;
        } else if (Array.isArray(toolResult.tasks)) {
          console.log('Using fallback format - toolResult.tasks:', toolResult.tasks);
          // Fallback for older format
          return toolResult.tasks.map(sanitizeTask);
        }
      } else {
        console.log('toolResult.success is false:', toolResult);
      }
    } catch (e) {
      console.error('Error parsing listTasks response:', e);
    }
  }
  console.log('Returning empty array - no valid response');
  return [];
}

export async function getTask(task_id: string, includeContext: boolean = true): Promise<Task | null> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_task",
      arguments: { action: "get", task_id, include_context: includeContext }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      if (toolResult.success) {
        const responseData = extractResponseData(toolResult);
        if (responseData.task) {
          // Sanitize the task data
          return sanitizeTask(responseData.task);
        } else if (toolResult.task) {
          // Fallback for older format
          return sanitizeTask(toolResult.task);
        }
      }
    } catch {}
  }
  return null;
}

export async function createTask(task: Partial<Task>): Promise<Task | null> {
  // Use V2 API if authenticated
  if (shouldUseV2Api()) {
    try {
      const response = await taskApiV2.createTask({
        title: task.title || '',
        description: task.description,
        status: task.status,
        priority: task.priority,
        git_branch_id: task.git_branch_id,
      });
      return response as Task;
    } catch (error) {
      console.error('V2 API error, falling back to V1:', error);
      // Fall through to V1 API
    }
  }
  
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_task",
      arguments: { action: "create", ...task }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      if (toolResult.success) {
        const responseData = extractResponseData(toolResult);
        if (responseData.task) {
          // Sanitize the task data
          return sanitizeTask(responseData.task);
        } else if (toolResult.task) {
          // Fallback for older format
          return sanitizeTask(toolResult.task);
        }
      }
    } catch {}
  }
  return null;
}

export async function updateTask(task_id: string, updates: Partial<Task>): Promise<Task | null> {
  // Use V2 API if authenticated
  if (shouldUseV2Api()) {
    try {
      const response = await taskApiV2.updateTask(task_id, {
        title: updates.title,
        description: updates.description,
        status: updates.status,
        priority: updates.priority,
        progress_percentage: updates.progress_percentage,
      });
      return response as Task;
    } catch (error) {
      console.error('V2 API error, falling back to V1:', error);
      // Fall through to V1 API
    }
  }
  
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_task",
      arguments: { action: "update", task_id, ...updates }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  
  
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      
      // Check if success is true, even if task is not returned
      if (toolResult.success) {
        const responseData = extractResponseData(toolResult);
        // Return task from data or fallback to dummy task object
        return responseData.task || toolResult.task || { id: task_id, ...updates } as Task;
      }
      
      // If not successful, check for error message
      if (toolResult.error) {
        const errorMessage = typeof toolResult.error === 'string' 
          ? toolResult.error 
          : toolResult.error.message || JSON.stringify(toolResult.error);
        throw new Error(errorMessage);
      }
      
      // If no success and no error
      throw new Error('Unexpected response from server');
    } catch (e) {
      // If it's already an Error, throw it, otherwise create a new Error
      if (e instanceof Error) {
        throw e;
      } else {
        throw new Error(String(e));
      }
    }
  }
  
  // Check for error in response
  if (data.error) {
    throw new Error(data.error.message || 'Unknown error');
  }
  
  return null;
}

export async function deleteTask(task_id: string): Promise<boolean> {
  // Use V2 API if authenticated
  if (shouldUseV2Api()) {
    try {
      await taskApiV2.deleteTask(task_id);
      return true;
    } catch (error) {
      console.error('V2 API error, falling back to V1:', error);
      // Fall through to V1 API
    }
  }
  
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_task",
      arguments: { action: "delete", task_id }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      if (toolResult.success) {
        return true;
      }
    } catch {}
  }
  return false;
}

// Complete a task with completion summary and testing notes
export async function completeTask(task_id: string, completion_summary: string, testing_notes?: string): Promise<Task | null> {
  // Use V2 API if authenticated
  if (shouldUseV2Api()) {
    try {
      const response = await taskApiV2.completeTask(task_id, {
        completion_summary,
        testing_notes,
      });
      return response as Task;
    } catch (error) {
      console.error('V2 API error, falling back to V1:', error);
      // Fall through to V1 API
    }
  }
  
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_task",
      arguments: { 
        action: "complete", 
        task_id,
        completion_summary,
        ...(testing_notes && { testing_notes })
      }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      if (toolResult.success) {
        const responseData = extractResponseData(toolResult);
        if (responseData.task) {
          return sanitizeTask(responseData.task);
        } else if (toolResult.task) {
          return sanitizeTask(toolResult.task);
        }
        // If no task returned but success, return a basic completed task
        return { id: task_id, status: 'done' } as Task;
      }
    } catch {}
  }
  return null;
}

// --- Helper Functions ---
// Helper function to sanitize subtask data by removing non-serializable properties
function sanitizeSubtask(subtask: any): Subtask {
  const { _events, _eventsCount, _maxListeners, ...cleanSubtask } = subtask;
  
  // Ensure all string fields are actually strings and not objects
  const sanitized = { ...cleanSubtask };
  
  // Fields that should be strings
  const stringFields = ['id', 'title', 'description', 'status', 'priority', 'due_date', 'parent_task_id'];
  for (const field of stringFields) {
    if (sanitized[field] !== undefined && sanitized[field] !== null) {
      // If it's an object with a 'value' property, extract the value
      if (typeof sanitized[field] === 'object' && 'value' in sanitized[field]) {
        sanitized[field] = String(sanitized[field].value);
      } else if (typeof sanitized[field] !== 'string') {
        // Convert to string if it's not already
        sanitized[field] = String(sanitized[field]);
      }
    }
  }
  
  // Ensure assignees is an array of strings
  if (sanitized.assignees) {
    if (!Array.isArray(sanitized.assignees)) {
      sanitized.assignees = [String(sanitized.assignees)];
    } else {
      sanitized.assignees = sanitized.assignees.map((a: any) => {
        if (typeof a === 'object' && 'value' in a) {
          return String(a.value);
        }
        return String(a);
      });
    }
  }
  
  return sanitized;
}

// Helper function to extract data from nested response structure
function extractResponseData(toolResult: any): any {
  // Handle new nested data structure from backend
  if (toolResult && toolResult.data) {
    return toolResult.data;
  }
  return toolResult;
}

// Helper function to sanitize task data by removing non-serializable properties
function sanitizeTask(task: any): Task {
  const { _events, _eventsCount, _maxListeners, ...cleanTask } = task;
  
  // Ensure string fields are actually strings and not objects
  const stringFields = ['id', 'title', 'description', 'status', 'priority', 'due_date', 'details', 'estimated_effort'];
  for (const field of stringFields) {
    if (cleanTask[field] !== undefined && cleanTask[field] !== null) {
      // If it's an object with a 'value' property, extract the value
      if (typeof cleanTask[field] === 'object' && 'value' in cleanTask[field]) {
        cleanTask[field] = String(cleanTask[field].value);
      } else if (typeof cleanTask[field] === 'object') {
        // Convert object to string if needed
        cleanTask[field] = JSON.stringify(cleanTask[field]);
      }
    }
  }
  
  // Debug logging for assignees
  if (cleanTask.assignees !== undefined) {
    console.log('Sanitizing task assignees:', {
      taskId: cleanTask.id,
      taskTitle: cleanTask.title,
      assignees: cleanTask.assignees,
      assigneesType: typeof cleanTask.assignees,
      isArray: Array.isArray(cleanTask.assignees)
    });
  }
  
  // Ensure assignees is properly handled as an array of strings
  if (cleanTask.assignees) {
    if (Array.isArray(cleanTask.assignees)) {
      // Filter out any invalid entries and ensure all are strings
      cleanTask.assignees = cleanTask.assignees
        .map((assignee: any) => {
          // If it's already a string, keep it
          if (typeof assignee === 'string' && assignee.trim().length > 0) {
            return assignee.trim();
          }
          // If it's an object with 'id', 'name', or 'value', extract it
          if (assignee && typeof assignee === 'object') {
            if (assignee.value && typeof assignee.value === 'string') {
              return assignee.value;
            }
            if (assignee.id && typeof assignee.id === 'string') {
              return assignee.id;
            }
            if (assignee.name && typeof assignee.name === 'string') {
              return assignee.name;
            }
            if (assignee.assignee_id && typeof assignee.assignee_id === 'string') {
              return assignee.assignee_id;
            }
          }
          return null;
        })
        .filter((assignee: string | null) => assignee !== null && assignee !== '[' && assignee !== ']');
    } else if (typeof cleanTask.assignees === 'string') {
      // If it's a string, try to parse it or use as single assignee
      try {
        const parsed = JSON.parse(cleanTask.assignees);
        if (Array.isArray(parsed)) {
          cleanTask.assignees = parsed.filter((a: any) => typeof a === 'string' && a.trim().length > 0);
        } else {
          cleanTask.assignees = [cleanTask.assignees];
        }
      } catch {
        // Not JSON, treat as single assignee
        cleanTask.assignees = cleanTask.assignees.trim() ? [cleanTask.assignees.trim()] : [];
      }
    } else {
      // Convert to empty array if not valid
      cleanTask.assignees = [];
    }
  } else {
    // Ensure assignees is always an array
    cleanTask.assignees = [];
  }
  
  // Ensure subtasks is an array of IDs, not objects
  if (cleanTask.subtasks && Array.isArray(cleanTask.subtasks)) {
    cleanTask.subtasks = cleanTask.subtasks
      .map((subtask: any) => {
        // If it's already a string, keep it
        if (typeof subtask === 'string' && subtask.length > 0) {
          return subtask;
        }
        // If it's an object with a 'value' property, extract the UUID
        if (subtask && typeof subtask === 'object' && subtask.value && typeof subtask.value === 'string') {
          return subtask.value;
        }
        // If it's an object with an 'id' property, try that
        if (subtask && typeof subtask === 'object' && subtask.id && typeof subtask.id === 'string') {
          return subtask.id;
        }
        return null;
      })
      .filter((id: string | null) => id !== null); // Remove any null values
  }
  
  return cleanTask;
}

// --- Subtask Management ---

export async function listSubtasks(task_id: string): Promise<any[]> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_subtask",
      arguments: { action: "list", task_id }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      if (toolResult.success) {
        const responseData = extractResponseData(toolResult);
        if (Array.isArray(responseData.subtasks)) {
          // Sanitize each subtask to remove non-serializable properties
          return responseData.subtasks.map(sanitizeSubtask);
        } else if (Array.isArray(toolResult.subtasks)) {
          // Fallback for older format
          return toolResult.subtasks.map(sanitizeSubtask);
        }
      }
    } catch {}
  }
  return [];
}

export async function createSubtask(task_id: string, subtask: any): Promise<any> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_subtask",
      arguments: { action: "create", task_id, ...subtask }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      if (toolResult.success) {
        const responseData = extractResponseData(toolResult);
        if (responseData.subtask) {
          // Sanitize the returned subtask
          return sanitizeSubtask(responseData.subtask);
        } else if (toolResult.subtask) {
          // Fallback for older format
          return sanitizeSubtask(toolResult.subtask);
        }
      }
    } catch {}
  }
  return null;
}

export async function updateSubtask(task_id: string, id: string, updates: any): Promise<any> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_subtask",
      arguments: { action: "update", task_id, subtask_id: id, ...updates }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  
  
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      
      if (toolResult.success) {
        const responseData = extractResponseData(toolResult);
        // Handle nested subtask structure from API response
        if (responseData.subtask) {
          // Check if subtask has nested subtask property
          if (responseData.subtask.subtask) {
            return sanitizeSubtask(responseData.subtask.subtask);
          }
          return sanitizeSubtask(responseData.subtask);
        } else if (toolResult.subtask) {
          // Fallback for older format
          if (toolResult.subtask.subtask) {
            return sanitizeSubtask(toolResult.subtask.subtask);
          }
          return sanitizeSubtask(toolResult.subtask);
        }
        return { id, ...updates };
      }
      
      if (toolResult.error) {
        const errorMessage = typeof toolResult.error === 'string' 
          ? toolResult.error 
          : toolResult.error.message || JSON.stringify(toolResult.error);
        throw new Error(errorMessage);
      }
      
      throw new Error('Unexpected response from server');
    } catch (e) {
      if (e instanceof Error) {
        throw e;
      } else {
        throw new Error(String(e));
      }
    }
  }
  
  if (data.error) {
    throw new Error(data.error.message || 'Unknown error');
  }
  
  return null;
}

export async function deleteSubtask(task_id: string, id: string): Promise<boolean> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_subtask",
      arguments: { action: "delete", task_id, subtask_id: id }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      if (toolResult.success) {
        return true;
      }
    } catch {}
  }
  return false;
}

// Complete a subtask with completion summary
export async function completeSubtask(
  task_id: string, 
  subtask_id: string, 
  completion_summary: string,
  impact_on_parent?: string,
  challenges_overcome?: string[]
): Promise<any> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_subtask",
      arguments: { 
        action: "complete", 
        task_id, 
        subtask_id,
        completion_summary,
        ...(impact_on_parent && { impact_on_parent }),
        ...(challenges_overcome && { challenges_overcome })
      }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      if (toolResult.success) {
        const responseData = extractResponseData(toolResult);
        if (responseData.subtask) {
          return sanitizeSubtask(responseData.subtask);
        } else if (toolResult.subtask) {
          return sanitizeSubtask(toolResult.subtask);
        }
        return { id: subtask_id, status: 'done' };
      }
    } catch {}
  }
  return null;
}

// --- Dependency Management ---
export async function addDependency(task_id: string, dependency_id: string): Promise<boolean> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_task",
      arguments: { action: "add_dependency", task_id, dependency_id }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      if (toolResult.success) {
        return true;
      }
    } catch {}
  }
  return false;
}

export async function removeDependency(task_id: string, dependency_id: string): Promise<boolean> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_task",
      arguments: { action: "remove_dependency", task_id, dependency_id }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      if (toolResult.success) {
        return true;
      }
    } catch {}
  }
  return false;
}

export async function searchTasks(query: string, git_branch_id?: string, limit: number = 50): Promise<Task[]> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_task",
      arguments: { 
        action: "search", 
        query,
        ...(git_branch_id && { git_branch_id }),
        limit
      }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      if (toolResult.success) {
        const responseData = extractResponseData(toolResult);
        if (Array.isArray(responseData.tasks)) {
          return responseData.tasks.map(sanitizeTask);
        } else if (Array.isArray(toolResult.tasks)) {
          return toolResult.tasks.map(sanitizeTask);
        }
      }
    } catch {}
  }
  return [];
}

// --- Context Management - Updated to use unified manage_context ---
export async function getTaskContext(task_id: string): Promise<any> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_context",
      arguments: { 
        action: "resolve",
        level: "task",
        context_id: task_id,
        force_refresh: false,
        include_inherited: true  // Include inherited context from parent levels
      }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      // Check if the response indicates an error
      if (toolResult.success === false || toolResult.status === 'failure') {
        console.error('Context not found:', toolResult.error?.message || 'Unknown error');
        return null;
      }
      return toolResult;
    } catch (e) {
      console.error('Error parsing task context:', e);
    }
  }
  return null;
}

export async function getProjectContext(project_id: string): Promise<any> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_context",
      arguments: { 
        action: "resolve",
        level: "project",
        context_id: project_id,
        force_refresh: false,
        include_inherited: true  // Include inherited context from parent levels
      }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      return toolResult;
    } catch (e) {
      console.error('Error parsing project context:', e);
    }
  }
  return null;
}

export async function getBranchContext(branch_id: string): Promise<any> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_context",
      arguments: { 
        action: "resolve",
        level: "branch",
        context_id: branch_id,
        force_refresh: false,
        include_inherited: true  // Include inherited context from parent levels
      }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      return toolResult;
    } catch (e) {
      console.error('Error parsing branch context:', e);
    }
  }
  return null;
}

export async function getGlobalContext(): Promise<any> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_context",
      arguments: { 
        action: "resolve",
        level: "global",
        context_id: "7fa54328-bfb4-523c-ab6f-465e05e1bba5", // Actual user's global context ID
        force_refresh: false,
        include_inherited: false  // Global has no parents to inherit from
      }
    },
    id: getRpcId(),
  };
  
  const headers = await withMcpHeaders();
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: headers,
    body: JSON.stringify(body),
  });
  
  console.log('Fetched global context:', await res.clone().json());
  
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      return toolResult;
    } catch (e) {
      console.error('Error parsing global context:', e);
    }
  }
  return null;
}

// --- New context operations available with unified system ---
export async function addTaskInsight(
  task_id: string, 
  content: string, 
  category: string = "general",
  importance: string = "medium"
): Promise<any> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_context",
      arguments: {
        action: "add_insight",
        level: "task",
        context_id: task_id,
        content: content,
        category: category,
        importance: importance,
      }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      return toolResult;
    } catch (e) {
      console.error('Error adding task insight:', e);
    }
  }
  return null;
}

export async function addTaskProgress(task_id: string, content: string): Promise<any> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_context",
      arguments: {
        action: "add_progress",
        level: "task",
        context_id: task_id,
        content: content,
      }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      return toolResult;
    } catch (e) {
      console.error('Error adding task progress:', e);
    }
  }
  return null;
}

export async function listContexts(
  level: string = "task",
  filters?: Record<string, any>
): Promise<any> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_context",
      arguments: {
        action: "list",
        level: level,
        filters: filters,
      }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      return toolResult;
    } catch (e) {
      console.error('Error listing contexts:', e);
    }
  }
  return null;
}

// --- Project Management ---
export async function listProjects(): Promise<Project[]> {
  // Use V2 API if authenticated
  if (shouldUseV2Api()) {
    try {
      const response: any = await projectApiV2.getProjects();
      if (Array.isArray(response)) {
        return response;
      }
      if (response && response.projects) {
        return response.projects;
      }
      return [];
    } catch (error) {
      console.error('V2 API error, falling back to V1:', error);
      // Fall through to V1 API
    }
  }
  
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_project",
      arguments: { action: "list" }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      if (toolResult.success) {
        const responseData = extractResponseData(toolResult);
        const projects = responseData.projects || toolResult.projects;
        if (Array.isArray(projects)) {
          // Backend now includes git_branchs in the response, no need for separate API calls
          // Just ensure the format is correct (object with branch IDs as keys)
          const projectsWithBranches = projects.map((project: any) => {
            // If git_branchs is already in the correct format, use it directly
            // Otherwise, ensure it's an object (not an array)
            const branchesObj = project.git_branchs || {};
            return {
              ...project,
              git_branchs: branchesObj
            };
          });
          return projectsWithBranches;
        }
      }
    } catch {}
  }
  return [];
}

export async function getProject(project_id: string): Promise<Project | null> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_project",
      arguments: { action: "get", project_id }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      if (toolResult.success) {
        const responseData = extractResponseData(toolResult);
        if (responseData.project) {
          return responseData.project;
        } else if (toolResult.project) {
          return toolResult.project;
        }
      }
    } catch {}
  }
  return null;
}

export async function createProject(project: Partial<Project>): Promise<Project | null> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_project",
      arguments: { action: "create", ...project }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      if (toolResult.success) {
        const responseData = extractResponseData(toolResult);
        if (responseData.project) {
          return responseData.project;
        } else if (toolResult.project) {
          return toolResult.project;
        }
      }
    } catch {}
  }
  return null;
}

export async function updateProject(project_id: string, updates: Partial<Project>): Promise<Project | null> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_project",
      arguments: { action: "update", project_id, ...updates }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      if (toolResult.success) {
        const responseData = extractResponseData(toolResult);
        if (responseData.project) {
          return responseData.project;
        } else if (toolResult.project) {
          return toolResult.project;
        }
      }
    } catch {}
  }
  return null;
}

export async function deleteProject(project_id: string): Promise<{ success: boolean; message?: string; error?: string }> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_project",
      arguments: { action: "delete", project_id }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      return {
        success: toolResult.success || false,
        message: toolResult.message,
        error: toolResult.error
      };
    } catch (e) {
      return { success: false, error: "Failed to parse response" };
    }
  }
  return { success: false, error: "No response from server" };
}

// --- Branch (Task Tree) Management ---
export async function listGitBranches(project_id: string): Promise<Branch[]> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_git_branch",
      arguments: { 
        action: "list",
        project_id: project_id
      }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      if (toolResult.success) {
        const responseData = extractResponseData(toolResult);
        const branches = responseData.git_branchs || toolResult.git_branchs || [];
        return branches;
      }
    } catch {}
  }
  return [];
}

export async function listBranches(project_id: string): Promise<Branch[]> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_project",
      arguments: { action: "list" }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      if (toolResult.success && Array.isArray(toolResult.projects)) {
        const project = toolResult.projects.find((p: any) => p.id === project_id);
        if (project && project.git_branchs) {
          return Object.values(project.git_branchs);
        }
      }
    } catch {}
  }
  return [];
}

// Function to create a new branch (task tree) for a project
export async function createBranch(projectId: string, branchName: string, description?: string): Promise<any> {
    const body = {
        jsonrpc: "2.0",
        method: "tools/call",
        params: {
            name: "manage_git_branch",
            arguments: { 
                action: "create",
                project_id: projectId,
                git_branch_name: branchName.toLowerCase().replace(/\s+/g, '-'), // Create a git-friendly name
                git_branch_description: description
            }
        },
        id: getRpcId(),
    };
    const res = await fetch(`${API_BASE}`, {
        method: "POST",
        headers: withMcpHeaders(),
        body: JSON.stringify(body),
    });
    const data = await res.json();
    if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
        try {
            const toolResult = JSON.parse(data.result.content[0].text);
            if (toolResult.success) {
                const responseData = extractResponseData(toolResult);
                if (responseData.git_branch) {
                    return responseData.git_branch;
                } else if (toolResult.git_branch) {
                    return toolResult.git_branch;
                }
            }
        } catch {}
    }
    return null;
}

// NOTE: No update/delete branch API is documented. If MCP adds support, implement here.
export async function updateBranch(/* project_id: string, branch_id: string, updates: Partial<Branch> */): Promise<null> {
  // Not supported by MCP as of now
  return null;
}

export async function deleteBranch(project_id: string, branch_id: string): Promise<boolean> {
  try {
    const body = {
      jsonrpc: "2.0",
      method: "tools/call",
      params: {
        name: "manage_git_branch",
        arguments: {
          action: "delete",
          project_id,
          git_branch_id: branch_id
        }
      },
      id: getRpcId(),
    };
    console.log('Sending delete branch request:', body);
    const res = await fetch(`${API_BASE}`, {
      method: "POST",
      headers: withMcpHeaders(),
      body: JSON.stringify(body),
    });
    const data = await res.json();
    console.log('Delete branch response:', data);
    const success = data?.result?.content?.[0]?.text ? 
      JSON.parse(data.result.content[0].text).success || false : false;
    console.log('Delete branch success:', success);
    return success;
  } catch (error) {
    console.error('Error deleting branch:', error);
    return false;
  }
}

// --- Rule Management ---
export async function listRules(): Promise<Rule[]> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_rule",
      arguments: { action: "list" }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      if (toolResult.success && Array.isArray(toolResult.rules)) {
        return toolResult.rules;
      }
    } catch {}
  }
  return [];
}

export async function getRule(rule_id: string): Promise<Rule | null> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_rule",
      arguments: { action: "info", target: rule_id }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      if (toolResult.success && toolResult.rule) {
        return toolResult.rule;
      }
    } catch {}
  }
  return null;
}

export async function createRule(rule: Partial<Rule>): Promise<Rule | null> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_rule",
      arguments: { action: "create", ...rule }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      if (toolResult.success && toolResult.rule) {
        return toolResult.rule;
      }
    } catch {}
  }
  return null;
}

export async function updateRule(rule_id: string, updates: Partial<Rule>): Promise<Rule | null> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_rule",
      arguments: { action: "update", target: rule_id, ...updates }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      if (toolResult.success && toolResult.rule) {
        return toolResult.rule;
      }
    } catch {}
  }
  return null;
}

export async function deleteRule(rule_id: string): Promise<boolean> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_rule",
      arguments: { action: "delete", target: rule_id }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      if (toolResult.success) {
        return true;
      }
    } catch {}
  }
  return false;
}

export async function validateRule(rule_id: string): Promise<any> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_rule",
      arguments: { action: "validate_rule_hierarchy", target: rule_id }
    },
    id: getRpcId(),
  };
  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      if (toolResult.success) {
        return toolResult;
      }
    } catch {}
  }
  return null;
}

// --- Agent Management ---
export async function listAgents(project_id: string): Promise<any[]> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_agent",
      arguments: { 
        action: "list",
        project_id: project_id
      }
    },
    id: getRpcId(),
  };

  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      return toolResult.agents || [];
    } catch {
      return [];
    }
  }
  
  return [];
}

// Get available agents from the agent library folder
export async function getAvailableAgents(): Promise<string[]> {
  // These are the agent names from the dhafnck_mcp_main/agent-library/agents folder
  // In a real implementation, this would be fetched from the backend
  return [
    "@adaptive_deployment_strategist_agent",
    "@algorithmic_problem_solver_agent",
    "@analytics_setup_agent",
    "@brainjs_ml_agent",
    "@branding_agent",
    "@campaign_manager_agent",
    "@code_reviewer_agent",
    "@coding_agent",
    "@community_strategy_agent",
    "@compliance_scope_agent",
    "@compliance_testing_agent",
    "@content_strategy_agent",
    "@core_concept_agent",
    "@debugger_agent",
    "@deep_research_agent",
    "@design_qa_analyst",
    "@design_qa_analyst_agent",
    "@design_system_agent",
    "@development_orchestrator_agent",
    "@devops_agent",
    "@documentation_agent",
    "@efficiency_optimization_agent",
    "@elicitation_agent",
    "@ethical_review_agent",
    "@exploratory_tester_agent",
    "@functional_tester_agent",
    "@generic_purpose_agent",
    "@graphic_design_agent",
    "@growth_hacking_idea_agent",
    "@health_monitor_agent",
    "@idea_generation_agent",
    "@idea_refinement_agent",
    "@incident_learning_agent",
    "@knowledge_evolution_agent",
    "@lead_testing_agent",
    "@market_research_agent",
    "@marketing_strategy_orchestrator",
    "@marketing_strategy_orchestrator_agent",
    "@mcp_configuration_agent",
    "@mcp_researcher_agent",
    "@nlu_processor_agent",
    "@performance_load_tester_agent",
    "@prd_architect_agent",
    "@project_initiator_agent",
    "@prototyping_agent",
    "@remediation_agent",
    "@root_cause_analysis_agent",
    "@scribe_agent",
    "@security_auditor_agent",
    "@security_penetration_tester_agent",
    "@seo_sem_agent",
    "@social_media_setup_agent",
    "@swarm_scaler_agent",
    "@system_architect_agent",
    "@task_deep_manager_agent",
    "@task_planning_agent",
    "@task_sync_agent",
    "@tech_spec_agent",
    "@technology_advisor_agent",
    "@test_case_generator_agent",
    "@test_orchestrator_agent",
    "@uat_coordinator_agent",
    "@uber_orchestrator_agent",
    "@ui_designer_agent",
    "@ui_designer_expert_shadcn_agent",
    "@usability_heuristic_agent",
    "@user_feedback_collector_agent",
    "@ux_researcher_agent",
    "@video_production_agent",
    "@visual_regression_testing_agent",
    "@workflow_architect_agent"
  ];
}

// Call/activate an agent
export async function callAgent(name_agent: string): Promise<any> {
  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "call_agent",
      arguments: { 
        name_agent: name_agent
      }
    },
    id: getRpcId(),
  };

  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const data = await res.json();
  
  if (data.result && data.result.content && Array.isArray(data.result.content) && data.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(data.result.content[0].text);
      return toolResult;
    } catch (e) {
      console.error('Error parsing call agent response:', e);
      return { success: false, error: 'Failed to parse response' };
    }
  }
  
  return { success: false, error: 'No response from server' };
}

export async function updateGlobalContext(data: any): Promise<any> {
  // Transform frontend data structure to backend expected format
  const transformedData = {
    global_settings: {
      autonomous_rules: data.organizationSettings || {},
      security_policies: {},  // Could be part of organizationSettings
      coding_standards: {},   // Could be part of organizationSettings
      workflow_templates: data.globalPatterns || {},
      delegation_rules: data.metadata || {}
    }
  };

  const body = {
    jsonrpc: "2.0",
    method: "tools/call",
    params: {
      name: "manage_context",
      arguments: { 
        action: "update",
        level: "global",
        context_id: "7fa54328-bfb4-523c-ab6f-465e05e1bba5", // Use the actual global context ID
        data: transformedData,
        propagate_changes: true
      }
    },
    id: getRpcId(),
  };

  const res = await fetch(`${API_BASE}`, {
    method: "POST",
    headers: await withMcpHeaders(),
    body: JSON.stringify(body),
  });
  const responseData = await res.json();
  
  if (responseData.result && responseData.result.content && Array.isArray(responseData.result.content) && responseData.result.content.length > 0) {
    try {
      const toolResult = JSON.parse(responseData.result.content[0].text);
      return toolResult;
    } catch (e) {
      console.error('Error parsing update global context response:', e);
      throw new Error('Failed to parse response');
    }
  }
  
  throw new Error('Failed to update global context');
}