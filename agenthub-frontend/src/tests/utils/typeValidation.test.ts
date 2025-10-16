import { describe, it, expect } from "vitest";
import {
  isTask,
  isSubtask,
  isTaskArray,
  isSubtaskArray,
  ensureTask,
  ensureSubtask,
  ensureTaskArray,
  ensureSubtaskArray
} from "../../utils/typeValidation";
import { Task, Subtask } from "../../types/taskTypes";

describe("typeValidation", () => {
  const validTask: Task = {
    id: "task-1",
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
    subtask_count: 0,
    context_id: null,
    completion_summary: null
  };

  const validSubtask: Subtask = {
    id: "subtask-1",
    title: "Test Subtask",
    description: "Test Description",
    status: "todo",
    priority: "medium",
    assignees: ["user1"],
    progress_notes: null,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    task_id: "task-1",
    parent_title: "Parent Task"
  };

  describe("isTask", () => {
    it("should return true for valid task", () => {
      expect(isTask(validTask)).toBe(true);
    });

    it("should return false for null", () => {
      expect(isTask(null)).toBe(false);
    });

    it("should return false for undefined", () => {
      expect(isTask(undefined)).toBe(false);
    });

    it("should return false for non-object", () => {
      expect(isTask("not a task")).toBe(false);
      expect(isTask(123)).toBe(false);
      expect(isTask(true)).toBe(false);
    });

    it("should return false for object missing required fields", () => {
      const invalidTask = { ...validTask };
      delete (invalidTask as any).id;
      expect(isTask(invalidTask)).toBe(false);
    });

    it("should return false for object with wrong field types", () => {
      const invalidTask = { ...validTask, id: 123 };
      expect(isTask(invalidTask)).toBe(false);
    });

    it("should return false for subtask object", () => {
      expect(isTask(validSubtask)).toBe(false);
    });
  });

  describe("isSubtask", () => {
    it("should return true for valid subtask", () => {
      expect(isSubtask(validSubtask)).toBe(true);
    });

    it("should return false for null", () => {
      expect(isSubtask(null)).toBe(false);
    });

    it("should return false for undefined", () => {
      expect(isSubtask(undefined)).toBe(false);
    });

    it("should return false for non-object", () => {
      expect(isSubtask("not a subtask")).toBe(false);
      expect(isSubtask(456)).toBe(false);
      expect(isSubtask(false)).toBe(false);
    });

    it("should return false for object missing required fields", () => {
      const invalidSubtask = { ...validSubtask };
      delete (invalidSubtask as any).task_id;
      expect(isSubtask(invalidSubtask)).toBe(false);
    });

    it("should return false for object with wrong field types", () => {
      const invalidSubtask = { ...validSubtask, task_id: 123 };
      expect(isSubtask(invalidSubtask)).toBe(false);
    });

    it("should return false for task object", () => {
      expect(isSubtask(validTask)).toBe(false);
    });
  });

  describe("isTaskArray", () => {
    it("should return true for array of valid tasks", () => {
      expect(isTaskArray([validTask, validTask])).toBe(true);
    });

    it("should return true for empty array", () => {
      expect(isTaskArray([])).toBe(true);
    });

    it("should return false for non-array", () => {
      expect(isTaskArray(validTask)).toBe(false);
      expect(isTaskArray("not an array")).toBe(false);
      expect(isTaskArray(null)).toBe(false);
      expect(isTaskArray(undefined)).toBe(false);
    });

    it("should return false for array with invalid tasks", () => {
      expect(isTaskArray([validTask, { invalid: true }])).toBe(false);
    });

    it("should return false for array with subtasks", () => {
      expect(isTaskArray([validSubtask])).toBe(false);
    });
  });

  describe("isSubtaskArray", () => {
    it("should return true for array of valid subtasks", () => {
      expect(isSubtaskArray([validSubtask, validSubtask])).toBe(true);
    });

    it("should return true for empty array", () => {
      expect(isSubtaskArray([])).toBe(true);
    });

    it("should return false for non-array", () => {
      expect(isSubtaskArray(validSubtask)).toBe(false);
      expect(isSubtaskArray("not an array")).toBe(false);
      expect(isSubtaskArray(null)).toBe(false);
      expect(isSubtaskArray(undefined)).toBe(false);
    });

    it("should return false for array with invalid subtasks", () => {
      expect(isSubtaskArray([validSubtask, { invalid: true }])).toBe(false);
    });

    it("should return false for array with tasks", () => {
      expect(isSubtaskArray([validTask])).toBe(false);
    });
  });

  describe("ensureTask", () => {
    it("should return task for valid task", () => {
      expect(ensureTask(validTask)).toBe(validTask);
    });

    it("should throw error for invalid task", () => {
      expect(() => ensureTask(null)).toThrow("Expected Task object");
      expect(() => ensureTask(undefined)).toThrow("Expected Task object");
      expect(() => ensureTask({ invalid: true })).toThrow("Expected Task object");
      expect(() => ensureTask(validSubtask)).toThrow("Expected Task object");
    });
  });

  describe("ensureSubtask", () => {
    it("should return subtask for valid subtask", () => {
      expect(ensureSubtask(validSubtask)).toBe(validSubtask);
    });

    it("should throw error for invalid subtask", () => {
      expect(() => ensureSubtask(null)).toThrow("Expected Subtask object");
      expect(() => ensureSubtask(undefined)).toThrow("Expected Subtask object");
      expect(() => ensureSubtask({ invalid: true })).toThrow("Expected Subtask object");
      expect(() => ensureSubtask(validTask)).toThrow("Expected Subtask object");
    });
  });

  describe("ensureTaskArray", () => {
    it("should return array for valid task array", () => {
      const tasks = [validTask, validTask];
      expect(ensureTaskArray(tasks)).toBe(tasks);
    });

    it("should return empty array for empty array", () => {
      expect(ensureTaskArray([])).toEqual([]);
    });

    it("should throw error for invalid array", () => {
      expect(() => ensureTaskArray(null)).toThrow("Expected array of Task objects");
      expect(() => ensureTaskArray(undefined)).toThrow("Expected array of Task objects");
      expect(() => ensureTaskArray("not an array")).toThrow("Expected array of Task objects");
      expect(() => ensureTaskArray([validTask, null])).toThrow("Expected array of Task objects");
      expect(() => ensureTaskArray([validSubtask])).toThrow("Expected array of Task objects");
    });
  });

  describe("ensureSubtaskArray", () => {
    it("should return array for valid subtask array", () => {
      const subtasks = [validSubtask, validSubtask];
      expect(ensureSubtaskArray(subtasks)).toBe(subtasks);
    });

    it("should return empty array for empty array", () => {
      expect(ensureSubtaskArray([])).toEqual([]);
    });

    it("should throw error for invalid array", () => {
      expect(() => ensureSubtaskArray(null)).toThrow("Expected array of Subtask objects");
      expect(() => ensureSubtaskArray(undefined)).toThrow("Expected array of Subtask objects");
      expect(() => ensureSubtaskArray("not an array")).toThrow("Expected array of Subtask objects");
      expect(() => ensureSubtaskArray([validSubtask, null])).toThrow("Expected array of Subtask objects");
      expect(() => ensureSubtaskArray([validTask])).toThrow("Expected array of Subtask objects");
    });
  });
});