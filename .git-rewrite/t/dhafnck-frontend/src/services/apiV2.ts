// API V2 Service - User-Isolated Endpoints with JWT Authentication
import Cookies from 'js-cookie';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Get current auth token
const getAuthToken = (): string | null => {
  return Cookies.get('access_token') || null;
};

// Create headers with authentication
const getAuthHeaders = (): HeadersInit => {
  const token = getAuthToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  return headers;
};

// Handle API responses
const handleResponse = async <T>(response: Response): Promise<T> => {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    
    if (response.status === 401) {
      // Token expired or invalid - clear cookies to force fallback to V1 API
      console.log('V2 API authentication failed, clearing tokens...');
      import('js-cookie').then(Cookies => {
        Cookies.default.remove('access_token');
        Cookies.default.remove('refresh_token');
      });
      throw new Error('Authentication required. Please log in again.');
    }
    
    throw new Error(error.detail || `Request failed with status ${response.status}`);
  }
  
  return response.json();
};

// Task API V2 - User-isolated endpoints
export const taskApiV2 = {
  // Get all tasks for current user, optionally filtered by git_branch_id
  getTasks: async (params?: { git_branch_id?: string }) => {
    const url = new URL(`${API_BASE_URL}/api/v2/tasks/`);
    
    // Add git_branch_id as query parameter if provided
    if (params?.git_branch_id) {
      url.searchParams.set('git_branch_id', params.git_branch_id);
    }
    
    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  // Get a specific task (only if owned by user)
  getTask: async (taskId: string) => {
    const response = await fetch(`${API_BASE_URL}/api/v2/tasks/${taskId}`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  // Create a new task (automatically assigned to user)
  createTask: async (taskData: {
    title: string;
    description?: string;
    status?: string;
    priority?: string;
    git_branch_id?: string;
  }) => {
    const response = await fetch(`${API_BASE_URL}/api/v2/tasks/`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(taskData),
    });
    return handleResponse(response);
  },

  // Update a task (only if owned by user)
  updateTask: async (taskId: string, updates: {
    title?: string;
    description?: string;
    status?: string;
    priority?: string;
    progress_percentage?: number;
  }) => {
    const response = await fetch(`${API_BASE_URL}/api/v2/tasks/${taskId}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(updates),
    });
    return handleResponse(response);
  },

  // Delete a task (only if owned by user)
  deleteTask: async (taskId: string) => {
    const response = await fetch(`${API_BASE_URL}/api/v2/tasks/${taskId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  // Complete a task
  completeTask: async (taskId: string, completionData: {
    completion_summary: string;
    testing_notes?: string;
  }) => {
    const response = await fetch(`${API_BASE_URL}/api/v2/tasks/${taskId}/complete`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(completionData),
    });
    return handleResponse(response);
  },
};

// Project API V2 - User-isolated endpoints
export const projectApiV2 = {
  // Get all projects for current user
  getProjects: async () => {
    const response = await fetch(`${API_BASE_URL}/api/v2/projects/`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  // Create a new project (automatically assigned to user)
  createProject: async (projectData: {
    name: string;
    description?: string;
  }) => {
    const response = await fetch(`${API_BASE_URL}/api/v2/projects/`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(projectData),
    });
    return handleResponse(response);
  },

  // Update a project (only if owned by user)
  updateProject: async (projectId: string, updates: {
    name?: string;
    description?: string;
    status?: string;
  }) => {
    const response = await fetch(`${API_BASE_URL}/api/v2/projects/${projectId}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(updates),
    });
    return handleResponse(response);
  },

  // Delete a project (only if owned by user)
  deleteProject: async (projectId: string) => {
    const response = await fetch(`${API_BASE_URL}/api/v2/projects/${projectId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },
};

// Agent API V2 - User-isolated endpoints
export const agentApiV2 = {
  // Get all agents for current user
  getAgents: async () => {
    const response = await fetch(`${API_BASE_URL}/api/v2/agents/`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  // Register a new agent (automatically assigned to user)
  registerAgent: async (agentData: {
    name: string;
    project_id: string;
    call_agent?: string;
  }) => {
    const response = await fetch(`${API_BASE_URL}/api/v2/agents/`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(agentData),
    });
    return handleResponse(response);
  },
};

// Export a function to check if user is authenticated
export const isAuthenticated = (): boolean => {
  return !!getAuthToken();
};

// Export a function to get current user ID from token
export const getCurrentUserId = (): string | null => {
  const token = getAuthToken();
  if (!token) return null;
  
  try {
    // Decode JWT token (basic base64 decode of payload)
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    
    const payload = JSON.parse(atob(parts[1]));
    return payload.sub || payload.user_id || null;
  } catch (error) {
    console.error('Error decoding token:', error);
    return null;
  }
};