// API service - Direct V2 API usage (no backward compatibility)
// All operations use the V2 authenticated endpoints

import {
    branchApiV2,
    contextApiV2,
    getCurrentUserId,
    isAuthenticated,
    projectApiV2,
    subtaskApiV2,
    taskApiV2
} from './services/apiV2';
import { seatApi } from './services/seatApi';
import type {
    ApiResponse,
    Branch,
    BranchesResponse,
    BranchRequestOptions,
    BranchResponse,
    ContextResponse,
    DeleteResponse,
    HealthResponse,
    Project,
    ProjectRequestOptions,
    ProjectResponse,
    ProjectsResponse,
    Rule,
    Subtask,
    SubtaskRequestOptions,
    SubtaskResponse,
    SubtasksResponse,
    Task,
    TaskRequestOptions,
    TaskResponse,
    TasksResponse
} from './types/api.types';
import type { TaskEvent, TaskEventsResponse } from './types/taskTypes';
import logger from './utils/logger';

export type {
    ApiResponse, Branch, BranchRequestOptions, BranchesResponse,
    BranchResponse,
    ContextResponse, DeleteResponse, HealthResponse, Project, ProjectRequestOptions, ProjectResponse, ProjectsResponse, Rule, Subtask, SubtaskRequestOptions, SubtaskResponse, SubtasksResponse, Task, TaskRequestOptions, TaskResponse, TasksResponse
};

// --- Task Operations ---
export const listTasks = async (params?: { git_branch_id?: string; includeContext?: boolean }): Promise<Task[]> => {
    const response = await taskApiV2.getTasks(params) as TasksResponse;
    return response.tasks || [];
};

export const getTasks = async (git_branch_id: string, options?: TaskRequestOptions): Promise<any> => {
    const response = await taskApiV2.getTasks({
        git_branch_id,
        includeContext: options?.includeContext
    }) as TasksResponse;
    return response || { tasks: [] };
};

export const getTask = async (task_id: string, options?: TaskRequestOptions): Promise<Task> => {
    const response = await taskApiV2.getTask(task_id, options?.includeContext) as TaskResponse;
    return response.task || response;
};

/**
 * The task's EXECUTION LEDGER, straight from `GET /api/v2/tasks/{id}/events`.
 *
 * Returns the route's body rather than unwrapping it, unlike its neighbours: there is nothing to
 * unwrap here (`events` IS the payload) and the body also carries the exclusive `after_seq` cursor
 * and the row count, which is what a caller walking a ledger the server caps at 100 rows needs.
 */
export const getTaskEvents = async (task_id: string, after_seq: number = 0): Promise<TaskEventsResponse> => {
    const response = await taskApiV2.getTaskEvents(task_id, after_seq) as TaskEventsResponse;
    // The route serializes an OrderedMap, so `events` is present on a 200; an absent one is a broken
    // response rather than an empty ledger, and normalizing it here keeps every caller's map simple.
    const events: TaskEvent[] = response.events ?? [];
    return { ...response, events };
};

export const createTask = async (task: Partial<Task>): Promise<Task> => {
    const response = await taskApiV2.createTask({
        title: task.title || '',
        description: task.description,
        status: task.status,
        priority: task.priority,
        git_branch_id: task.git_branch_id,
        assignees: task.assignees || [] // Pass as array, backend expects List[str]
    }) as TaskResponse;
    return response.task || response;
};

export const updateTask = async (task_id: string, updates: Partial<Task>): Promise<Task> => {
    logger.debug('=== UPDATE TASK DEBUG ===');
    logger.debug('Task ID:', task_id);
    logger.debug('Updates received:', updates);

    // Filter out undefined values and only send defined fields
    const updatePayload: any = {};
    if (updates.title !== undefined) updatePayload.title = updates.title;
    if (updates.description !== undefined) updatePayload.description = updates.description;
    if (updates.status !== undefined) updatePayload.status = updates.status;
    if (updates.priority !== undefined) updatePayload.priority = updates.priority;
    if (updates.progress_percentage !== undefined) updatePayload.progress_percentage = updates.progress_percentage;
    if (updates.assignees !== undefined) updatePayload.assignees = updates.assignees;
    if (updates.labels !== undefined) updatePayload.labels = updates.labels;
    if (updates.estimated_effort !== undefined) updatePayload.estimated_effort = updates.estimated_effort;
    if (updates.due_date !== undefined) updatePayload.due_date = updates.due_date;
    if (updates.dependencies !== undefined) updatePayload.dependencies = updates.dependencies;
    if (updates.context_data !== undefined) updatePayload.context_data = updates.context_data;
    // Add progress_notes - maps to 'details' field in backend
    if ((updates as any).progress_notes !== undefined) updatePayload.details = (updates as any).progress_notes;

    logger.debug('=== Progress 1 ===');
    logger.debug('Sending update payload to backend:', updatePayload);

    try {
        const response = await taskApiV2.updateTask(task_id, updatePayload) as TaskResponse;

        logger.debug('=== Progress 2 ===');
        logger.debug('Response from backend:', response);

        const result = response.task || response;

        logger.debug('=== Progress 3 ===');
        logger.debug('Returning updated task:', result);

        return result;
    } catch (error) {
        logger.error('=== UPDATE ERROR ===');
        logger.error('Error updating task:', error);
        throw error;
    }
};

export const deleteTask = async (task_id: string): Promise<void> => {
    logger.debug('🚀 DELETE DEBUG: API deleteTask called for task_id:', task_id);
    logger.debug('🚀 DELETE DEBUG: About to call taskApiV2.deleteTask');
    await taskApiV2.deleteTask(task_id);
    logger.debug('🚀 DELETE DEBUG: taskApiV2.deleteTask completed for task_id:', task_id);
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
export const listSubtasks = async (task_id: string, options?: SubtaskRequestOptions): Promise<Subtask[]> => {
    const response = await subtaskApiV2.listSubtasksForTask(task_id, options?.includeContext) as SubtasksResponse;
    return response.subtasks || [];
};

export const getSubtask = async (_task_id: string, subtask_id: string, options?: SubtaskRequestOptions): Promise<Subtask> => {
    // Use simple endpoint with authentication - task_id kept for API consistency but not used
    const response = await subtaskApiV2.getSubtask(subtask_id, options?.includeContext) as SubtaskResponse;
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
// Get bulk summaries using the new optimized endpoint
export const createBranch = async (project_id: string, branch: Partial<Branch>): Promise<Branch> => {
    const response = await branchApiV2.createBranch(project_id, {
        git_branch_name: branch.git_branch_name || '',
        description: branch.description
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
// The names an assignee picker offers are the user's seat keys, collected over every room
// the Seats page lists. A seat is assigned as "@<seat_key>": the backend keeps an assignee
// that starts with "@" as given and rejects an unknown bare name.
export const getAvailableAgents = async (): Promise<string[]> => {
    const { rooms } = await seatApi.listRooms();
    const perRoom = await Promise.all(rooms.map(room => seatApi.listSeats(room.slug)));
    const assignees = perRoom.flatMap(({ seats }) => seats.map(seat => `@${seat.seat_key}`));
    return [...new Set(assignees)].sort();
};

// --- Connection Operations ---
// (Health check handled via connectionApiV2 directly in components)

// Export utility functions and bulk API functions
export { getCurrentUserId, isAuthenticated };
