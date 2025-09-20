// API service - Direct V2 API usage (no backward compatibility)
// All operations use the V2 authenticated endpoints

import {
    agentApiV2,
    branchApiV2,
    connectionApiV2,
    contextApiV2,
    getCurrentUserId,
    isAuthenticated,
    projectApiV2,
    subtaskApiV2,
    taskApiV2
} from './services/apiV2';
import logger from './utils/logger';

// --- Response Type Definitions ---
export interface ApiResponse<T = any> {
    success?: boolean;
    message?: string;
    error?: string;
    detail?: string;
    data?: T;
    [key: string]: any;
}

export interface TasksResponse extends ApiResponse {
    tasks: Task[];
}

export interface TaskResponse extends ApiResponse {
    task: Task;
}

export interface SubtasksResponse extends ApiResponse {
    subtasks: Subtask[];
}

export interface SubtaskResponse extends ApiResponse {
    subtask: Subtask;
}

export interface ProjectsResponse extends ApiResponse {
    projects: Project[];
}

export interface ProjectResponse extends ApiResponse {
    project: Project;
}

export interface BranchesResponse extends ApiResponse {
    branches: Branch[];
}

export interface BranchResponse extends ApiResponse {
    branch: Branch;
}

export interface ContextResponse extends ApiResponse {
    context: any;
}

export interface AgentsResponse extends ApiResponse {
    agents: any[];
}

export interface HealthResponse extends ApiResponse {
    status: string;
}

export interface DeleteResponse {
    success: boolean;
    message?: string;
    error?: string;
}

// --- Interfaces for Type Safety ---
export interface Task {
    id: string;
    title: string;
    description: string;
    status: string;
    priority: string;
    subtasks: string[];
    assignees?: string[];
    dependencies?: string[];
    dependency_relationships?: {
        depends_on: string[];
        blocks: string[];
        dependency_chains?: string[][];
    };
    context_data?: any;
    context_id?: string;
    git_branch_id?: string;
    details?: string;
    labels?: string[];
    estimated_effort?: string;
    due_date?: string;
    created_at?: string;
    updated_at?: string;
    progress_percentage?: number;
    [key: string]: any;
}

export interface Subtask {
    id: string;
    title: string;
    description: string;
    status: string;
    priority: string;
    parent_task_id: string;
    assignees?: string[];
    dependencies?: string[];
    progress_percentage?: number;
    progress_notes?: string;
    created_at?: string;
    updated_at?: string;
    completed_at?: string;
    [key: string]: any;
}

export interface Project {
    id: string;
    name: string;
    description: string;
    branches?: Branch[];
    created_at?: string;
    updated_at?: string;
    [key: string]: any;
}

export interface Branch {
    id: string;
    git_branch_name: string;
    description?: string;
    project_id: string;
    is_active: boolean;
    created_at?: string;
    updated_at?: string;
}

export interface Rule {
    id: string;
    name: string;
    description: string;
    condition: string;
    action: string;
    priority: number;
    is_active: boolean;
    [key: string]: any;
}

// --- Task Operations ---
export const listTasks = async (params?: { git_branch_id?: string }): Promise<Task[]> => {
    const response = await taskApiV2.getTasks(params) as TasksResponse;
    return response.tasks || [];
};

export const getTasks = async (git_branch_id: string): Promise<any> => {
    const response = await taskApiV2.getTasks({ git_branch_id }) as TasksResponse;
    return response || { tasks: [] };
};

export const getTask = async (task_id: string): Promise<Task> => {
    const response = await taskApiV2.getTask(task_id) as TaskResponse;
    return response.task || response;
};

export const createTask = async (task: Partial<Task>): Promise<Task> => {
    const response = await taskApiV2.createTask({
        title: task.title || '',
        description: task.description,
        status: task.status,
        priority: task.priority,
        git_branch_id: task.git_branch_id,
        assignees: Array.isArray(task.assignees) ? task.assignees.join(',') : task.assignees // Convert array to comma-separated string
    }) as TaskResponse;
    return response.task || response;
};

export const updateTask = async (task_id: string, updates: Partial<Task>): Promise<Task> => {
    const response = await taskApiV2.updateTask(task_id, {
        title: updates.title,
        description: updates.description,
        status: updates.status,
        priority: updates.priority,
        progress_percentage: updates.progress_percentage
    }) as TaskResponse;
    return response.task || response;
};

export const deleteTask = async (task_id: string): Promise<void> => {
    await taskApiV2.deleteTask(task_id);
};

export const completeTask = async (
    task_id: string,
    completion_data: { completion_summary: string; testing_notes?: string }
): Promise<Task> => {
    const response = await taskApiV2.completeTask(task_id, completion_data) as TaskResponse;
    return response.task || response;
};

export const searchTasks = async (query: string, params?: { git_branch_id?: string }): Promise<Task[]> => {
    // Search functionality can be implemented on frontend by filtering list results
    const tasks = await listTasks(params);
    const searchLower = query.toLowerCase();
    return tasks.filter(task => 
        task.title.toLowerCase().includes(searchLower) ||
        task.description?.toLowerCase().includes(searchLower)
    );
};

// --- Subtask Operations ---
export const listSubtasks = async (task_id: string): Promise<Subtask[]> => {
    const response = await subtaskApiV2.listSubtasksForTask(task_id) as SubtasksResponse;
    return response.subtasks || [];
};

export const getSubtask = async (task_id: string, subtask_id: string): Promise<Subtask> => {
    // Use nested subtask endpoint for complete data with proper parent task routing
    const response = await subtaskApiV2.getSubtask(task_id, subtask_id) as SubtaskResponse;
    return response.subtask || response;
};

export const createSubtask = async (task_id: string, subtask: Partial<Subtask>): Promise<Subtask> => {
    const response = await subtaskApiV2.createSubtask(task_id, {
        title: subtask.title || '',
        description: subtask.description
    }) as SubtaskResponse;
    return response.subtask || response;
};

export const updateSubtask = async (subtask_id: string, updates: Partial<Subtask>): Promise<Subtask> => {
    const response = await subtaskApiV2.updateSubtask(subtask_id, {
        title: updates.title,
        description: updates.description,
        status: updates.status,
        progress_percentage: updates.progress_percentage
    }) as SubtaskResponse;
    return response.subtask || response;
};

export const deleteSubtask = async (subtask_id: string): Promise<void> => {
    await subtaskApiV2.deleteSubtask(subtask_id);
};

export const completeSubtask = async (
    subtask_id: string,
    completion_notes?: string
): Promise<Subtask> => {
    const response = await subtaskApiV2.completeSubtask(subtask_id, completion_notes) as SubtaskResponse;
    return response.subtask || response;
};

// --- Project Operations ---
export const listProjects = async (): Promise<Project[]> => {
    try {
        const response = await projectApiV2.getProjects() as ProjectsResponse;
        return response.projects || [];
    } catch (error) {
        logger.error('listProjects: Error fetching projects:', error);
        throw error;
    }
};

export const createProject = async (project: Partial<Project>): Promise<Project> => {
    const response = await projectApiV2.createProject({
        name: project.name || '',
        description: project.description
    }) as ProjectResponse;
    return response.project || response;
};

export const updateProject = async (project_id: string, updates: Partial<Project>): Promise<Project> => {
    const response = await projectApiV2.updateProject(project_id, {
        name: updates.name,
        description: updates.description
    }) as ProjectResponse;
    return response.project || response;
};

export const deleteProject = async (project_id: string): Promise<DeleteResponse> => {
    const response = await projectApiV2.deleteProject(project_id) as DeleteResponse;
    return response;
};

// --- Branch Operations ---
export const listBranches = async (project_id: string): Promise<Branch[]> => {
    const response = await branchApiV2.getBranches(project_id) as BranchesResponse;
    return response.branches || [];
};

export const createBranch = async (project_id: string, branch: Partial<Branch>): Promise<Branch> => {
    const response = await branchApiV2.createBranch(project_id, {
        git_branch_name: branch.git_branch_name || '',
        description: branch.description
    }) as BranchResponse;
    return response.branch || response;
};

export const updateBranch = async (branch_id: string, updates: Partial<Branch>): Promise<Branch> => {
    const response = await branchApiV2.updateBranch(branch_id, {
        git_branch_name: updates.git_branch_name,
        description: updates.description,
        is_active: updates.is_active
    }) as BranchResponse;
    return response.branch || response;
};

export const deleteBranch = async (branch_id: string): Promise<DeleteResponse> => {
    try {
        const response = await branchApiV2.deleteBranch(branch_id) as unknown;

        // Handle different response formats
        if (response === null || response === undefined) {
            // If response is null/undefined, assume success (204 No Content)
            return { success: true, message: 'Branch deleted successfully' };
        }

        if (typeof response === 'object' && response !== null) {
            const responseObj = response as Record<string, any>;

            // If response has a success field, use it
            if ('success' in responseObj) {
                return {
                    success: Boolean(responseObj.success),
                    message: responseObj.message,
                    error: responseObj.error
                };
            }

            // If response has no error indication, assume success
            if (!responseObj.error && !responseObj.detail) {
                return {
                    success: true,
                    message: responseObj.message || 'Branch deleted successfully'
                };
            }

            // If there's an error
            return {
                success: false,
                error: responseObj.error || responseObj.detail || 'Failed to delete branch'
            };
        }

        // For any other response type, assume success
        return { success: true, message: 'Branch deleted successfully' };
    } catch (error: any) {
        logger.error('Delete branch error:', error);
        return {
            success: false,
            error: error.message || 'Failed to delete branch'
        };
    }
};

// --- Context Operations ---
export const getTaskContext = async (task_id: string): Promise<any> => {
    try {
        const response = await contextApiV2.getContext('task', task_id, true) as ContextResponse;
        return response.context || response;
    } catch (error) {
        logger.error('Error getting task context:', error);
        return null;
    }
};

export const getBranchContext = async (branch_id: string): Promise<any> => {
    try {
        const response = await contextApiV2.getContext('branch', branch_id, true) as ContextResponse;
        return response.context || response;
    } catch (error) {
        logger.error('Error getting branch context:', error);
        return null;
    }
};

export const getProjectContext = async (project_id: string): Promise<any> => {
    try {
        const response = await contextApiV2.getContext('project', project_id, true) as ContextResponse;
        return response.context || response;
    } catch (error) {
        logger.error('Error getting project context:', error);
        return null;
    }
};

export const getGlobalContext = async (): Promise<any> => {
    try {
        // For global context, use any dummy value - server ignores it and uses token user
        const response = await contextApiV2.getContext('global', 'global', false) as ContextResponse;
        return response.context || response;
    } catch (error) {
        logger.error('Error getting global context:', error);
        return null;
    }
};

export const updateGlobalContext = async (data: any): Promise<any> => {
    try {
        // For global context, use any dummy value - server ignores it and uses token user
        const response = await contextApiV2.updateContext('global', 'global', data) as ContextResponse;
        return response.context || response;
    } catch (error) {
        logger.error('Error updating global context:', error);
        return null;
    }
};

export const updateProjectContext = async (project_id: string, data: any): Promise<any> => {
    try {
        const response = await contextApiV2.updateContext('project', project_id, data) as ContextResponse;
        return response.context || response;
    } catch (error) {
        logger.error('Error updating project context:', error);
        return null;
    }
};

export const updateBranchContext = async (branch_id: string, data: any): Promise<any> => {
    try {
        const response = await contextApiV2.updateContext('branch', branch_id, data) as ContextResponse;
        return response.context || response;
    } catch (error) {
        logger.error('Error updating branch context:', error);
        return null;
    }
};

export const updateTaskContext = async (task_id: string, data: any): Promise<any> => {
    try {
        const response = await contextApiV2.updateContext('task', task_id, data) as ContextResponse;
        return response.context || response;
    } catch (error) {
        logger.error('Error updating task context:', error);
        return null;
    }
};

// --- Agent Operations ---
export const listAgents = async (): Promise<any[]> => {
    try {
        const response = await agentApiV2.getAgentsMetadata() as AgentsResponse;
        return response.agents || [];
    } catch (error) {
        logger.error('Error listing agents:', error);
        return [];
    }
};

export const getAvailableAgents = async (): Promise<string[]> => {
    // Return all 42 available agents from the agent library
    return [
        'coding-agent',
        'debugger-agent',
        'code-reviewer-agent',
        '@prototyping-agent',
        '@test-orchestrator-agent',
        '@uat-coordinator-agent',
        '@performance-load-tester-agent',
        'system-architect-agent',
        '@design-system-agent',
        '@ui-designer-expert-shadcn-agent',
        '@core-concept-agent',
        'devops-agent',
        '@adaptive-deployment-strategist-agent',
        '@swarm-scaler-agent',
        'documentation-agent',
        '@tech-spec-agent',
        '@prd-architect-agent',
        '@project-initiator-agent',
        '@task-planning-agent',
        '@master-orchestrator-agent',
        '@elicitation-agent',
        '@security-auditor-agent',
        '@compliance-scope-agent',
        '@ethical-review-agent',
        '@analytics-setup-agent',
        '@efficiency-optimization-agent',
        '@health-monitor-agent',
        '@marketing-strategy-orchestrator-agent',
        '@seo-sem-agent',
        '@growth-hacking-idea-agent',
        '@content-strategy-agent',
        '@community-strategy-agent',
        'branding-agent',
        'deep-research-agent',
        '@mcp-researcher-agent',
        '@root-cause-analysis-agent',
        '@technology-advisor-agent',
        '@brainjs-ml-agent',
        '@mcp-configuration-agent',
        '@idea-generation-agent',
        '@idea-refinement-agent',
        '@remediation-agent'
    ];
};

export const callAgent = async (agent_name: string, params?: any): Promise<any> => {
    try {
        const response = await agentApiV2.callAgent(agent_name, params);
        return response;
    } catch (error: any) {
        logger.error('Error calling agent:', error);
        const errorMessage = error?.message || error?.detail || 'Failed to call agent';
        return { 
            success: false, 
            message: errorMessage,
            error: error?.toString() || 'Unknown error'
        };
    }
};

// --- Rule Operations (Placeholder) ---
export const listRules = async (): Promise<Rule[]> => {
    logger.warn('Rule operations not yet implemented in V2 API');
    return [];
};

export const createRule = async (_rule: Partial<Rule>): Promise<Rule> => {
    logger.warn('Rule operations not yet implemented in V2 API');
    throw new Error('Rule operations not available');
};

export const updateRule = async (_rule_id: string, _updates: Partial<Rule>): Promise<Rule> => {
    logger.warn('Rule operations not yet implemented in V2 API');
    throw new Error('Rule operations not available');
};

export const deleteRule = async (_rule_id: string): Promise<void> => {
    logger.warn('Rule operations not yet implemented in V2 API');
    throw new Error('Rule operations not available');
};

export const validateRule = async (_rule: Partial<Rule>): Promise<any> => {
    logger.warn('Rule operations not yet implemented in V2 API');
    return { valid: false, errors: ['Rule operations not available'] };
};

// --- Connection Operations ---
export const checkHealth = async (): Promise<boolean> => {
    try {
        const response = await connectionApiV2.healthCheck() as HealthResponse;
        return response.status === 'healthy';
    } catch (error) {
        logger.error('Health check failed:', error);
        return false;
    }
};

// Export utility functions
export { getCurrentUserId, isAuthenticated };
