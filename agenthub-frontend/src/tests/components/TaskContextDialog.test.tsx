import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import "@testing-library/jest-dom";
import { TaskContextDialog } from "../../components/TaskContextDialog";
import { Task } from "../../api";
import { getTaskContext, updateTaskContext, getBranchContext, getProjectContext, getGlobalContext } from "../../api";
import { useEntityChanges } from "../../hooks/useChangeSubscription";

// Mock the API functions
jest.mock("../../api", () => ({
  getTaskContext: jest.fn(),
  updateTaskContext: jest.fn(),
  getBranchContext: jest.fn(),
  getProjectContext: jest.fn(),
  getGlobalContext: jest.fn()
}));

// Mock the WebSocket hook
jest.mock("../../hooks/useChangeSubscription", () => ({
  useEntityChanges: jest.fn()
}));

// Mock the logger
jest.mock("../../utils/logger", () => ({
  default: {
    debug: jest.fn(),
    info: jest.fn(),
    error: jest.fn()
  }
}));

describe("TaskContextDialog", () => {
  const mockTask: Task = {
    id: "task-123",
    title: "Test Task",
    description: "Test Description",
    status: "in_progress",
    priority: "high",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    completion_percentage: 50,
    assignees: [],
    dependencies: [],
    labels: [],
    estimated_effort: "2 hours",
    git_branch_id: "branch-123",
    project_id: "project-123",
    subtasks: []
  };

  const mockOnClose = jest.fn();
  const mockOnOpenChange = jest.fn();

  const defaultProps = {
    open: true,
    onOpenChange: mockOnOpenChange,
    task: mockTask,
    context: null,
    onClose: mockOnClose,
    loading: false
  };

  beforeEach(() => {
    jest.clearAllMocks();
    // Setup default mock implementations
    (getTaskContext as jest.Mock).mockResolvedValue(null);
    (getBranchContext as jest.Mock).mockResolvedValue(null);
    (getProjectContext as jest.Mock).mockResolvedValue(null);
    (getGlobalContext as jest.Mock).mockResolvedValue(null);
    (updateTaskContext as jest.Mock).mockResolvedValue({});
    (useEntityChanges as jest.Mock).mockImplementation(() => {});
  });

  describe("Basic Rendering", () => {
    it("renders dialog when open", () => {
      render(<TaskContextDialog {...defaultProps} />);
      
      expect(screen.getByText("Task Context Management")).toBeInTheDocument();
    });

    it("renders close button", () => {
      render(<TaskContextDialog {...defaultProps} />);
      
      const closeButton = screen.getByRole("button", { name: /close/i });
      expect(closeButton).toBeInTheDocument();
    });

    it("calls onClose when close button is clicked", () => {
      render(<TaskContextDialog {...defaultProps} />);
      
      const closeButton = screen.getByRole("button", { name: /close/i });
      fireEvent.click(closeButton);
      
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it("renders all tab buttons", () => {
      render(<TaskContextDialog {...defaultProps} />);
      
      expect(screen.getByRole("button", { name: /Task Info/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Progress/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Completion/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Testing/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Blockers/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Insights/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Next Steps/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Metadata/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Inheritance/i })).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("shows loading state when loading is true", () => {
      render(<TaskContextDialog {...defaultProps} loading={true} />);
      
      expect(screen.getByText("Loading task context...")).toBeInTheDocument();
    });

    it("does not show context content when loading", () => {
      const contextWithData = {
        data: { test: "data" },
        metadata: { version: "1.0" }
      };
      
      render(
        <TaskContextDialog
          {...defaultProps}
          loading={true}
          context={contextWithData}
        />
      );
      
      expect(screen.getByText("Loading task context...")).toBeInTheDocument();
      expect(screen.queryByText("No task_info defined yet.")).not.toBeInTheDocument();
    });
  });

  describe("No Context State", () => {
    it("shows no context message when context is null", () => {
      render(<TaskContextDialog {...defaultProps} context={null} />);
      
      expect(screen.getByText("No Task Context Available")).toBeInTheDocument();
      expect(screen.getByText("Task context has not been initialized yet.")).toBeInTheDocument();
      expect(screen.getByText(`Task: ${mockTask.title} (ID: ${mockTask.id})`)).toBeInTheDocument();
    });

    it("shows initialize button when no context", () => {
      render(<TaskContextDialog {...defaultProps} context={null} />);
      
      const initButton = screen.getByRole("button", { name: /Initialize Task Context/i });
      expect(initButton).toBeInTheDocument();
    });

    it("enters edit mode when initialize button clicked", () => {
      render(<TaskContextDialog {...defaultProps} context={null} />);
      
      const initButton = screen.getByRole("button", { name: /Initialize Task Context/i });
      fireEvent.click(initButton);
      
      expect(screen.getByRole("button", { name: /Save All/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Cancel/i })).toBeInTheDocument();
    });
  });

  describe("Context API Integration", () => {
    it("fetches task context when dialog opens", async () => {
      const mockContext = {
        data: {
          task_info: { title: "Test Task", status: "in_progress" },
          task_progress: { percentage: 50 },
          completion_summary: "Test summary",
          testing_notes: "Test notes",
          blockers: ["Blocker 1", "Blocker 2"],
          insights: ["Insight 1"],
          next_steps: ["Step 1"],
          task_metadata: { created_by: "user123" }
        }
      };
      
      (getTaskContext as jest.Mock).mockResolvedValue(mockContext);
      
      render(<TaskContextDialog {...defaultProps} />);
      
      await waitFor(() => {
        expect(getTaskContext).toHaveBeenCalledWith(mockTask.id);
      });
    });

    it("fetches inherited contexts", async () => {
      render(<TaskContextDialog {...defaultProps} />);
      
      await waitFor(() => {
        expect(getBranchContext).toHaveBeenCalledWith(mockTask.git_branch_id);
        expect(getProjectContext).toHaveBeenCalledWith(mockTask.project_id);
        expect(getGlobalContext).toHaveBeenCalled();
      });
    });

    it("handles API errors gracefully", async () => {
      (getTaskContext as jest.Mock).mockRejectedValue(new Error("API Error"));
      
      render(<TaskContextDialog {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText("No Task Context Available")).toBeInTheDocument();
      });
    });
  });

  describe("Edit Mode", () => {
    it("enters edit mode when Edit button is clicked", async () => {
      const mockContext = {
        data: {
          task_info: { title: "Test" },
          task_progress: {},
          completion_summary: "",
          testing_notes: "",
          blockers: [],
          insights: [],
          next_steps: [],
          task_metadata: {}
        }
      };
      
      (getTaskContext as jest.Mock).mockResolvedValue(mockContext);
      
      render(<TaskContextDialog {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByRole("button", { name: /Edit/i })).toBeInTheDocument();
      });
      
      fireEvent.click(screen.getByRole("button", { name: /Edit/i }));
      
      expect(screen.getByRole("button", { name: /Save All/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Cancel/i })).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/Add task information/i)).toBeInTheDocument();
    });

    it("saves context changes", async () => {
      const mockContext = {
        data: {
          task_info: { title: "Test" },
          task_progress: {},
          completion_summary: "",
          testing_notes: "",
          blockers: [],
          insights: [],
          next_steps: [],
          task_metadata: {}
        }
      };
      
      (getTaskContext as jest.Mock).mockResolvedValue(mockContext);
      (updateTaskContext as jest.Mock).mockResolvedValue({});
      
      render(<TaskContextDialog {...defaultProps} />);
      
      await waitFor(() => {
        fireEvent.click(screen.getByRole("button", { name: /Edit/i }));
      });
      
      // Modify task info
      const textarea = screen.getByPlaceholderText(/Add task information/i);
      fireEvent.change(textarea, { target: { value: "title: Updated Test\nstatus: completed" } });
      
      // Save changes
      fireEvent.click(screen.getByRole("button", { name: /Save All/i }));
      
      await waitFor(() => {
        expect(updateTaskContext).toHaveBeenCalledWith(mockTask.id, expect.objectContaining({
          task_info: { title: "Updated Test", status: "completed" }
        }));
      });
    });

    it("cancels edit mode", async () => {
      const mockContext = {
        data: { task_info: { title: "Original" } }
      };
      
      (getTaskContext as jest.Mock).mockResolvedValue(mockContext);
      
      render(<TaskContextDialog {...defaultProps} />);
      
      await waitFor(() => {
        fireEvent.click(screen.getByRole("button", { name: /Edit/i }));
      });
      
      const textarea = screen.getByPlaceholderText(/Add task information/i);
      fireEvent.change(textarea, { target: { value: "title: Changed" } });
      
      fireEvent.click(screen.getByRole("button", { name: /Cancel/i }));
      
      // Should exit edit mode
      expect(screen.queryByRole("button", { name: /Save All/i })).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Edit/i })).toBeInTheDocument();
    });
  });

  describe("Tab Navigation", () => {
    it("switches between tabs", async () => {
      const mockContext = {
        data: {
          task_info: { title: "Test Task" },
          task_progress: { percentage: 50 },
          completion_summary: "Summary text",
          testing_notes: "Testing notes",
          blockers: ["Blocker 1"],
          insights: ["Insight 1"],
          next_steps: ["Step 1"],
          task_metadata: { version: "1.0" }
        }
      };
      
      (getTaskContext as jest.Mock).mockResolvedValue(mockContext);
      
      render(<TaskContextDialog {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText("Test Task")).toBeInTheDocument();
      });
      
      // Click Progress tab
      fireEvent.click(screen.getByRole("button", { name: /Progress/i }));
      expect(screen.getByText("50")).toBeInTheDocument();
      
      // Click Completion tab
      fireEvent.click(screen.getByRole("button", { name: /Completion/i }));
      expect(screen.getByText("Summary text")).toBeInTheDocument();
      
      // Click Testing tab
      fireEvent.click(screen.getByRole("button", { name: /Testing/i }));
      expect(screen.getByText("Testing notes")).toBeInTheDocument();
      
      // Click Blockers tab
      fireEvent.click(screen.getByRole("button", { name: /Blockers/i }));
      expect(screen.getByText("Blocker 1")).toBeInTheDocument();
      
      // Click Insights tab
      fireEvent.click(screen.getByRole("button", { name: /Insights/i }));
      expect(screen.getByText("Insight 1")).toBeInTheDocument();
      
      // Click Next Steps tab
      fireEvent.click(screen.getByRole("button", { name: /Next Steps/i }));
      expect(screen.getByText("Step 1")).toBeInTheDocument();
      
      // Click Metadata tab
      fireEvent.click(screen.getByRole("button", { name: /Metadata/i }));
      expect(screen.getByText("1.0")).toBeInTheDocument();
    });

    it("shows inheritance view", async () => {
      const mockBranchContext = { data: { branch_setting: "value" } };
      const mockProjectContext = { data: { project_setting: "value" } };
      const mockGlobalContext = { data: { global_setting: "value" } };
      
      (getBranchContext as jest.Mock).mockResolvedValue(mockBranchContext);
      (getProjectContext as jest.Mock).mockResolvedValue(mockProjectContext);
      (getGlobalContext as jest.Mock).mockResolvedValue(mockGlobalContext);
      
      render(<TaskContextDialog {...defaultProps} />);
      
      await waitFor(() => {
        fireEvent.click(screen.getByRole("button", { name: /Inheritance/i }));
      });
      
      expect(screen.getByText("How Inheritance Works")).toBeInTheDocument();
      expect(screen.getByText("Global Context")).toBeInTheDocument();
      expect(screen.getByText("Project Context")).toBeInTheDocument();
      expect(screen.getByText("Branch Context")).toBeInTheDocument();
      expect(screen.getByText("Task Context (Current Level)")).toBeInTheDocument();
    });
  });

  describe("WebSocket Integration", () => {
    it("subscribes to task changes when dialog opens", () => {
      render(<TaskContextDialog {...defaultProps} />);
      
      expect(useEntityChanges).toHaveBeenCalledWith(
        'TaskContextDialog',
        'task',
        expect.any(Function),
        {
          entityIds: [mockTask.id],
          enabled: true
        }
      );
    });

    it("unsubscribes when dialog closes", () => {
      const { rerender } = render(<TaskContextDialog {...defaultProps} />);
      
      rerender(<TaskContextDialog {...defaultProps} open={false} />);
      
      expect(useEntityChanges).toHaveBeenLastCalledWith(
        'TaskContextDialog',
        'task',
        expect.any(Function),
        {
          entityIds: [mockTask.id],
          enabled: false
        }
      );
    });

    it("refreshes context on WebSocket task update", async () => {
      const mockContext = {
        data: { task_info: { title: "Initial" } }
      };
      
      (getTaskContext as jest.Mock)
        .mockResolvedValueOnce(mockContext)
        .mockResolvedValueOnce({
          data: { 
            task_info: { title: "Updated via WebSocket" },
            progress_history: [{ timestamp: "2024-01-01", content: "Progress update" }]
          }
        });
      
      let websocketHandler: ((notification: any) => void) | null = null;
      (useEntityChanges as jest.Mock).mockImplementation((_, __, handler) => {
        websocketHandler = handler;
      });
      
      render(<TaskContextDialog {...defaultProps} />);
      
      await waitFor(() => {
        expect(getTaskContext).toHaveBeenCalledTimes(1);
      });
      
      // Simulate WebSocket notification
      await act(async () => {
        if (websocketHandler) {
          await websocketHandler({
            entityId: mockTask.id,
            entityType: 'task',
            eventType: 'update'
          });
        }
      });
      
      await waitFor(() => {
        expect(getTaskContext).toHaveBeenCalledTimes(2);
      });
    });

    it("ignores WebSocket updates for different tasks", async () => {
      let websocketHandler: ((notification: any) => void) | null = null;
      (useEntityChanges as jest.Mock).mockImplementation((_, __, handler) => {
        websocketHandler = handler;
      });
      
      render(<TaskContextDialog {...defaultProps} />);
      
      await waitFor(() => {
        expect(getTaskContext).toHaveBeenCalledTimes(1);
      });
      
      // Simulate WebSocket notification for different task
      await act(async () => {
        if (websocketHandler) {
          await websocketHandler({
            entityId: 'different-task-id',
            entityType: 'task',
            eventType: 'update'
          });
        }
      });
      
      // Should not refetch
      expect(getTaskContext).toHaveBeenCalledTimes(1);
    });
  });

  describe("Copy JSON Feature", () => {
    it("copies context JSON to clipboard", async () => {
      const mockContext = {
        data: { task_info: { title: "Test" } }
      };
      
      (getTaskContext as jest.Mock).mockResolvedValue(mockContext);
      
      // Mock clipboard API
      Object.assign(navigator, {
        clipboard: {
          writeText: jest.fn().mockResolvedValue(undefined)
        }
      });
      
      render(<TaskContextDialog {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByRole("button", { name: /Copy JSON/i })).toBeInTheDocument();
      });
      
      fireEvent.click(screen.getByRole("button", { name: /Copy JSON/i }));
      
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        JSON.stringify(mockContext, null, 2)
      );
      
      // Should show "Copied!" temporarily
      expect(screen.getByText("Copied!")).toBeInTheDocument();
    });
  });

  describe("Raw JSON Expansion", () => {
    it("toggles raw JSON view", async () => {
      const mockContext = {
        data: { task_info: { title: "Test" } }
      };
      
      (getTaskContext as jest.Mock).mockResolvedValue(mockContext);
      
      render(<TaskContextDialog {...defaultProps} />);
      
      await waitFor(() => {
        expect(screen.getByText("View Complete JSON Context")).toBeInTheDocument();
      });
      
      // Initially collapsed
      expect(screen.queryByText(JSON.stringify(mockContext, null, 2))).not.toBeInTheDocument();
      
      // Click to expand
      fireEvent.click(screen.getByText("View Complete JSON Context"));
      
      // Should show JSON
      expect(screen.getByText(JSON.stringify(mockContext, null, 2))).toBeInTheDocument();
      
      // Click to collapse
      fireEvent.click(screen.getByText("View Complete JSON Context"));
      
      // Should hide JSON
      expect(screen.queryByText(JSON.stringify(mockContext, null, 2))).not.toBeInTheDocument();
    });
  });

  describe("Edge Cases", () => {
    it("handles null task gracefully", () => {
      render(<TaskContextDialog {...defaultProps} task={null} />);
      
      expect(screen.getByText("Task Context Management")).toBeInTheDocument();
      expect(useEntityChanges).toHaveBeenCalledWith(
        'TaskContextDialog',
        'task',
        expect.any(Function),
        {
          entityIds: undefined,
          enabled: false
        }
      );
    });

    it("handles markdown parsing for different formats", async () => {
      const mockContext = {
        data: { task_info: { title: "Test" } }
      };
      
      (getTaskContext as jest.Mock).mockResolvedValue(mockContext);
      
      render(<TaskContextDialog {...defaultProps} />);
      
      await waitFor(() => {
        fireEvent.click(screen.getByRole("button", { name: /Edit/i }));
      });
      
      const textarea = screen.getByPlaceholderText(/Add task information/i);
      
      // Test key:value format
      fireEvent.change(textarea, { target: { value: "key1: value1\nkey2: value2" } });
      
      // Test list format for blockers
      fireEvent.click(screen.getByRole("button", { name: /Blockers/i }));
      const blockersTextarea = screen.getByPlaceholderText(/Add blockers/i);
      fireEvent.change(blockersTextarea, { target: { value: "- Blocker 1\n- Blocker 2\n* Blocker 3" } });
      
      fireEvent.click(screen.getByRole("button", { name: /Save All/i }));
      
      await waitFor(() => {
        expect(updateTaskContext).toHaveBeenCalledWith(mockTask.id, expect.objectContaining({
          task_info: { key1: "value1", key2: "value2" },
          blockers: ["Blocker 1", "Blocker 2", "Blocker 3"]
        }));
      });
    });
  });
});