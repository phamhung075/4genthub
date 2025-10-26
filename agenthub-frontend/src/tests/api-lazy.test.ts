import { TaskResponse, SubtaskResponse } from "../types/taskTypes";
import { createLazyTaskLoader, createLazySubtaskLoader } from "../api-lazy";
import { authFetch } from "../services/apiV2";
import type { Mock } from "vitest";

// Mock apiV2
vi.mock("../services/apiV2", () => ({
  authFetch: vi.fn()
}));

const mockAuthFetch = authFetch as Mock;

describe("api-lazy", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("createLazyTaskLoader", () => {
    const mockTaskResponse: TaskResponse = {
      task: {
        id: "test-task-1",
        title: "Test Task",
        description: "Test Description",
        status: "todo",
        priority: "medium",
        details: null,
        assignees: ["user1"],
        labels: [],
        estimated_effort: null,
        due_date: null,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
        git_branch_id: "branch-1",
        project_id: "project-1",
        parent_task_id: null,
        dependencies: [],
        blocking_tasks: [],
        subtask_ids: [],
        context_id: null,
        completion_summary: null
      },
      success: true
    };

    it("should fetch tasks successfully", async () => {
      mockAuthFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          tasks: [mockTaskResponse.task],
          status: "success",
          success: true
        })
      });

      const loader = createLazyTaskLoader();
      const result = await loader.loadTasks("branch-1", 0, 10);

      expect(mockAuthFetch).toHaveBeenCalledWith(
        "/api/tasks?git_branch_id=branch-1&offset=0&limit=10"
      );
      expect(result).toEqual([mockTaskResponse.task]);
    });

    it("should handle empty results", async () => {
      mockAuthFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          tasks: [],
          status: "success",
          success: true
        })
      });

      const loader = createLazyTaskLoader();
      const result = await loader.loadTasks("branch-1", 0, 10);

      expect(result).toEqual([]);
    });

    it("should throw error on failed response", async () => {
      mockAuthFetch.mockResolvedValueOnce({
        ok: false,
        statusText: "Not Found"
      });

      const loader = createLazyTaskLoader();
      
      await expect(loader.loadTasks("branch-1", 0, 10)).rejects.toThrow("Failed to load tasks: Not Found");
    });

    it("should throw error when response is not ok", async () => {
      mockAuthFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: "error",
          error: "Something went wrong"
        })
      });

      const loader = createLazyTaskLoader();
      
      await expect(loader.loadTasks("branch-1", 0, 10)).rejects.toThrow("Failed to load tasks");
    });

    it("should handle network errors", async () => {
      mockAuthFetch.mockRejectedValueOnce(new Error("Network error"));

      const loader = createLazyTaskLoader();
      
      await expect(loader.loadTasks("branch-1", 0, 10)).rejects.toThrow("Network error");
    });
  });

  describe("createLazySubtaskLoader", () => {
    // Phase 2: Standalone subtask response KEEPS parent_task_id
    const mockSubtaskResponse: SubtaskResponse = {
      subtask: {
        id: "subtask-1",
        title: "Test Subtask",
        description: "Subtask Description",
        status: "todo",
        priority: "medium",
        assignees: ["user1"],
        progress_notes: null,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
        parent_task_id: "task-1",  // ✅ Included when standalone
        task_id: "task-1",
        parent_title: "Parent Task"
      },
      success: true
    };

    it("should fetch subtasks successfully", async () => {
      mockAuthFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          subtasks: [mockSubtaskResponse.subtask],
          status: "success",
          success: true
        })
      });

      const loader = createLazySubtaskLoader();
      const result = await loader.loadSubtasks("task-1", 0, 10);

      expect(mockAuthFetch).toHaveBeenCalledWith(
        "/api/tasks/task-1/subtasks?offset=0&limit=10"
      );
      expect(result).toEqual([mockSubtaskResponse.subtask]);
    });

    it("should handle empty subtasks", async () => {
      mockAuthFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          subtasks: [],
          status: "success",
          success: true
        })
      });

      const loader = createLazySubtaskLoader();
      const result = await loader.loadSubtasks("task-1", 0, 10);

      expect(result).toEqual([]);
    });

    it("should throw error on failed response", async () => {
      mockAuthFetch.mockResolvedValueOnce({
        ok: false,
        statusText: "Forbidden"
      });

      const loader = createLazySubtaskLoader();
      
      await expect(loader.loadSubtasks("task-1", 0, 10)).rejects.toThrow("Failed to load subtasks: Forbidden");
    });

    it("should throw error when response is not ok", async () => {
      mockAuthFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: "error",
          error: "Access denied"
        })
      });

      const loader = createLazySubtaskLoader();
      
      await expect(loader.loadSubtasks("task-1", 0, 10)).rejects.toThrow("Failed to load subtasks");
    });

    it("should handle network errors", async () => {
      mockAuthFetch.mockRejectedValueOnce(new Error("Connection timeout"));

      const loader = createLazySubtaskLoader();
      
      await expect(loader.loadSubtasks("task-1", 0, 10)).rejects.toThrow("Connection timeout");
    });
  });
});