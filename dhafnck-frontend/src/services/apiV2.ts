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
    console.log('API V2: Adding auth header with token starting:', token.substring(0, 50) + '...');
  } else {
    console.warn('API V2: No auth token found in cookies!');
  }
  
  return headers;
};

// Handle API responses with automatic token refresh
const handleResponse = async <T>(response: Response, originalUrl?: string, originalInit?: RequestInit): Promise<T> => {
  // Handle 204 No Content responses (successful deletion with no body)
  if (response.status === 204) {
    return { success: true, message: 'Operation completed successfully' } as T;
  }
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    
    if (response.status === 401) {
      console.log('V2 API: Got 401, attempting token refresh...');
      
      // Try to refresh the token
      try {
        await refreshTokenAndRetry();
        
        // Retry the original request with new token if we have the original request info
        if (originalUrl && originalInit) {
          const newToken = Cookies.get('access_token');
          if (newToken) {
            const newHeaders = { ...originalInit.headers };
            newHeaders['Authorization'] = `Bearer ${newToken}`;
            
            const retryResponse = await fetch(originalUrl, {
              ...originalInit,
              headers: newHeaders
            });
            
            if (retryResponse.ok) {
              return retryResponse.json();
            }
          }
        }
      } catch (refreshError) {
        console.log('V2 API: Token refresh failed, clearing tokens...');
        Cookies.remove('access_token');
        Cookies.remove('refresh_token');
        // Dispatch event to notify AuthContext to logout
        window.dispatchEvent(new CustomEvent('auth-logout'));
        throw new Error('Authentication required. Please log in again.');
      }
      
      throw new Error('Authentication required. Please log in again.');
    }
    
    throw new Error(error.detail || `Request failed with status ${response.status}`);
  }
  
  return response.json();
};

// Token refresh function
const refreshTokenAndRetry = async (): Promise<void> => {
  const refresh_token = Cookies.get('refresh_token');
  
  if (!refresh_token) {
    throw new Error('No refresh token available');
  }

  const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ refresh_token }),
  });

  if (!response.ok) {
    // If refresh fails, clear tokens and redirect to login
    if (response.status === 401) {
      console.error('V2 API: Refresh token expired or invalid, clearing tokens');
      Cookies.remove('access_token');
      Cookies.remove('refresh_token');
      // The handleResponse function will redirect to login
    }
    throw new Error('Token refresh failed');
  }

  const data = await response.json();
  
  // Update cookies with new tokens
  Cookies.set('access_token', data.access_token, { 
    expires: 7,
    sameSite: 'strict',
    secure: import.meta.env.MODE === 'production'
  });
  
  // Only update refresh token if a new one is provided
  if (data.refresh_token) {
    Cookies.set('refresh_token', data.refresh_token, { 
      expires: 30,
      sameSite: 'strict',
      secure: import.meta.env.MODE === 'production'
    });
  }
  
  console.log('V2 API: Token refreshed successfully');
};

// Enhanced fetch with automatic retry
const fetchWithRetry = async (url: string, init?: RequestInit) => {
  const response = await fetch(url, init);
  return handleResponse(response, url, init);
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
    
    return fetchWithRetry(url.toString(), {
      method: 'GET',
      headers: getAuthHeaders(),
    });
  },

  // Get a specific task (only if owned by user)
  getTask: async (taskId: string) => {
    return fetchWithRetry(`${API_BASE_URL}/api/v2/tasks/${taskId}`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
  },

  // Create a new task (automatically assigned to user)
  createTask: async (taskData: {
    title: string;
    description?: string;
    status?: string;
    priority?: string;
    git_branch_id?: string;
  }) => {
    return fetchWithRetry(`${API_BASE_URL}/api/v2/tasks/`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(taskData),
    });
  },

  // Update a task (only if owned by user)
  updateTask: async (taskId: string, updates: {
    title?: string;
    description?: string;
    status?: string;
    priority?: string;
    progress_percentage?: number;
  }) => {
    return fetchWithRetry(`${API_BASE_URL}/api/v2/tasks/${taskId}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(updates),
    });
  },

  // Delete a task (only if owned by user)
  deleteTask: async (taskId: string) => {
    return fetchWithRetry(`${API_BASE_URL}/api/v2/tasks/${taskId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
  },

  // Complete a task - fix parameter format for backend
  completeTask: async (taskId: string, completionData: {
    completion_summary: string;
    testing_notes?: string;
  }) => {
    const formData = new URLSearchParams();
    formData.append('completion_summary', completionData.completion_summary);
    if (completionData.testing_notes) {
      formData.append('testing_notes', completionData.testing_notes);
    }

    return fetchWithRetry(`${API_BASE_URL}/api/v2/tasks/${taskId}/complete`, {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });
  },
};

// Project API V2 - User-isolated endpoints
export const projectApiV2 = {
  // Get all projects for current user
  getProjects: async () => {
    return fetchWithRetry(`${API_BASE_URL}/api/v2/projects/`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
  },

  // Create a new project (automatically assigned to user)
  createProject: async (projectData: {
    name: string;
    description?: string;
  }) => {
    const formData = new URLSearchParams();
    formData.append('name', projectData.name);
    if (projectData.description) {
      formData.append('description', projectData.description);
    }

    return fetchWithRetry(`${API_BASE_URL}/api/v2/projects/`, {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });
  },

  // Update a project (only if owned by user)
  updateProject: async (projectId: string, updates: {
    name?: string;
    description?: string;
  }) => {
    const formData = new URLSearchParams();
    if (updates.name) {
      formData.append('name', updates.name);
    }
    if (updates.description) {
      formData.append('description', updates.description);
    }

    const response = await fetch(`${API_BASE_URL}/api/v2/projects/${projectId}`, {
      method: 'PUT',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
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

// Subtask API V2 - User-isolated endpoints
export const subtaskApiV2 = {
  // Create a new subtask
  createSubtask: async (taskId: string, subtaskData: {
    title: string;
    description?: string;
  }) => {
    const formData = new URLSearchParams();
    formData.append('task_id', taskId);
    formData.append('title', subtaskData.title);
    if (subtaskData.description) {
      formData.append('description', subtaskData.description);
    }

    const response = await fetch(`${API_BASE_URL}/api/v2/subtasks`, {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });
    return handleResponse(response);
  },

  // Get a specific subtask
  getSubtask: async (subtaskId: string) => {
    const response = await fetch(`${API_BASE_URL}/api/v2/subtasks/${subtaskId}`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  // Update a subtask
  updateSubtask: async (subtaskId: string, updates: {
    title?: string;
    description?: string;
    status?: string;
    progress_percentage?: number;
  }) => {
    const formData = new URLSearchParams();
    if (updates.title) formData.append('title', updates.title);
    if (updates.description) formData.append('description', updates.description);
    if (updates.status) formData.append('status', updates.status);
    if (updates.progress_percentage !== undefined) {
      formData.append('progress_percentage', updates.progress_percentage.toString());
    }

    const response = await fetch(`${API_BASE_URL}/api/v2/subtasks/${subtaskId}`, {
      method: 'PUT',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });
    return handleResponse(response);
  },

  // Delete a subtask
  deleteSubtask: async (subtaskId: string) => {
    const response = await fetch(`${API_BASE_URL}/api/v2/subtasks/${subtaskId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  // List subtasks for a task
  listSubtasksForTask: async (taskId: string) => {
    const response = await fetch(`${API_BASE_URL}/api/v2/subtasks/task/${taskId}`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  // Complete a subtask
  completeSubtask: async (subtaskId: string, completionNotes?: string) => {
    const formData = new URLSearchParams();
    if (completionNotes) {
      formData.append('completion_notes', completionNotes);
    }

    const response = await fetch(`${API_BASE_URL}/api/v2/subtasks/${subtaskId}/complete`, {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });
    return handleResponse(response);
  },
};

// Context API V2 - User-isolated endpoints
export const contextApiV2 = {
  // Get context at specified level
  getContext: async (level: string, contextId: string, includeInherited?: boolean) => {
    const url = new URL(`${API_BASE_URL}/api/v2/contexts/${level}/${contextId}`);
    if (includeInherited) {
      url.searchParams.set('include_inherited', 'true');
    }

    return fetchWithRetry(url.toString(), {
      method: 'GET',
      headers: getAuthHeaders(),
    });
  },

  // Create or update context
  updateContext: async (level: string, contextId: string, data: any) => {
    const response = await fetch(`${API_BASE_URL}/api/v2/contexts/${level}/${contextId}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  },

  // Delete context
  deleteContext: async (level: string, contextId: string) => {
    const response = await fetch(`${API_BASE_URL}/api/v2/contexts/${level}/${contextId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  // Resolve context with inheritance
  resolveContext: async (level: string, contextId: string) => {
    const response = await fetch(`${API_BASE_URL}/api/v2/contexts/${level}/${contextId}/resolve`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },
};

// Branch API V2 - User-isolated endpoints
export const branchApiV2 = {
  // List branches for a project
  getBranches: async (projectId: string) => {
    const response = await fetch(`${API_BASE_URL}/api/v2/branches/project/${projectId}`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  // Get a specific branch
  getBranch: async (branchId: string) => {
    const response = await fetch(`${API_BASE_URL}/api/v2/branches/${branchId}`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  // Create a new branch
  createBranch: async (projectId: string, branchData: {
    git_branch_name: string;
    description?: string;
  }) => {
    const formData = new URLSearchParams();
    formData.append('project_id', projectId);
    formData.append('git_branch_name', branchData.git_branch_name);
    if (branchData.description) {
      formData.append('description', branchData.description);
    }

    const response = await fetch(`${API_BASE_URL}/api/v2/branches`, {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });
    return handleResponse(response);
  },

  // Update a branch
  updateBranch: async (branchId: string, updates: {
    git_branch_name?: string;
    description?: string;
    is_active?: boolean;
  }) => {
    const formData = new URLSearchParams();
    if (updates.git_branch_name) formData.append('git_branch_name', updates.git_branch_name);
    if (updates.description) formData.append('description', updates.description);
    if (updates.is_active !== undefined) {
      formData.append('is_active', updates.is_active.toString());
    }

    const response = await fetch(`${API_BASE_URL}/api/v2/branches/${branchId}`, {
      method: 'PUT',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });
    return handleResponse(response);
  },

  // Delete a branch
  deleteBranch: async (branchId: string) => {
    const response = await fetch(`${API_BASE_URL}/api/v2/branches/${branchId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  // Assign agent to branch
  assignAgent: async (branchId: string, agentId: string) => {
    const formData = new URLSearchParams();
    formData.append('agent_id', agentId);

    const response = await fetch(`${API_BASE_URL}/api/v2/branches/${branchId}/assign-agent`, {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });
    return handleResponse(response);
  },

  // Get branch health
  getBranchHealth: async (branchId: string) => {
    const response = await fetch(`${API_BASE_URL}/api/v2/branches/${branchId}/health`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },
};

// Connection API V2 - User-isolated endpoints
export const connectionApiV2 = {
  // Health check
  healthCheck: async () => {
    const response = await fetch(`${API_BASE_URL}/api/v2/connections/health`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  // System status
  systemStatus: async () => {
    const response = await fetch(`${API_BASE_URL}/api/v2/connections/status`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  // Test connection
  testConnection: async () => {
    const response = await fetch(`${API_BASE_URL}/api/v2/connections/test`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },
};

// Agent API V2 - User-isolated endpoints
export const agentApiV2 = {
  // Get metadata for all agents
  getAgentsMetadata: async () => {
    const response = await fetch(`${API_BASE_URL}/api/v2/agents/metadata`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  // Get metadata for a specific agent
  getAgentMetadata: async (agentName: string) => {
    const response = await fetch(`${API_BASE_URL}/api/v2/agents/${agentName}`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  // Assign agent to branch
  assignAgentToBranch: async (branchId: string, agentId: string) => {
    const formData = new URLSearchParams();
    formData.append('branch_id', branchId);
    formData.append('agent_id', agentId);

    const response = await fetch(`${API_BASE_URL}/api/v2/agents/assign`, {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });
    return handleResponse(response);
  },

  // Unassign agent from branch
  unassignAgentFromBranch: async (branchId: string) => {
    const response = await fetch(`${API_BASE_URL}/api/v2/agents/unassign/${branchId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  // Get branch agent assignment
  getBranchAgentAssignment: async (branchId: string) => {
    const response = await fetch(`${API_BASE_URL}/api/v2/agents/branch/${branchId}/assignment`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  // Get project agent assignments
  getProjectAgentAssignments: async (projectId: string) => {
    const response = await fetch(`${API_BASE_URL}/api/v2/agents/project/${projectId}/assignments`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  // Get agent capabilities
  getAgentCapabilities: async () => {
    const response = await fetch(`${API_BASE_URL}/api/v2/agents/capabilities`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  // Call an agent
  callAgent: async (agentName: string, params?: any) => {
    const response = await fetch(`${API_BASE_URL}/api/v2/agents/call`, {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        agent_name: agentName,
        params: params || {}
      }),
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