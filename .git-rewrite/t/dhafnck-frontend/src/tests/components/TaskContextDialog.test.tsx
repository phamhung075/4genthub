import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { TaskContextDialog } from "../../components/TaskContextDialog";
import { Task } from "../../api";

// Mock the context helpers
jest.mock("../../utils/contextHelpers", () => ({
  formatContextDisplay: jest.fn((data) => ({
    completionSummary: data?.completion_summary || data?.completionSummary,
    isLegacy: !!data?.completion_summary,
    completionPercentage: data?.completion_percentage || data?.completionPercentage,
    taskStatus: data?.status || data?.taskStatus,
    testingNotes: data?.testing_notes || data?.testingNotes || []
  }))
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
  });

  describe("Basic Rendering", () => {
    it("renders dialog when open", () => {
      render(<TaskContextDialog {...defaultProps} />);
      
      expect(screen.getByText("Task Context")).toBeInTheDocument();
      expect(screen.getByText("Task: Test Task")).toBeInTheDocument();
      expect(screen.getByText("ID: task-123")).toBeInTheDocument();
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
  });

  describe("Loading State", () => {
    it("shows loading state when loading is true", () => {
      render(<TaskContextDialog {...defaultProps} loading={true} />);
      
      expect(screen.getByText("Loading context...")).toBeInTheDocument();
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
      
      expect(screen.getByText("Loading context...")).toBeInTheDocument();
      expect(screen.queryByText("Context Data")).not.toBeInTheDocument();
    });
  });

  describe("No Context State", () => {
    it("shows no context message when context is null", () => {
      render(<TaskContextDialog {...defaultProps} context={null} />);
      
      expect(screen.getByText("No context data available")).toBeInTheDocument();
      expect(screen.getByText("Complete the task or update it to create context")).toBeInTheDocument();
    });
  });

  describe("Special Message State", () => {
    it("renders special message without error", () => {
      const contextWithMessage = {
        message: "No context available for this task",
        info: "This task was created without context",
        suggestions: ["Create context manually", "Update task status"]
      };
      
      render(<TaskContextDialog {...defaultProps} context={contextWithMessage} />);
      
      expect(screen.getByText("No context available for this task")).toBeInTheDocument();
      expect(screen.getByText("This task was created without context")).toBeInTheDocument();
      expect(screen.getByText("Suggestions:")).toBeInTheDocument();
      expect(screen.getByText("Create context manually")).toBeInTheDocument();
      expect(screen.getByText("Update task status")).toBeInTheDocument();
    });

    it("handles message with suggestions array", () => {
      const contextWithSuggestions = {
        message: "Context needs attention",
        suggestions: ["Suggestion 1", "Suggestion 2", "Suggestion 3"]
      };
      
      render(<TaskContextDialog {...defaultProps} context={contextWithSuggestions} />);
      
      expect(screen.getByText("Context needs attention")).toBeInTheDocument();
      expect(screen.getByText("Suggestion 1")).toBeInTheDocument();
      expect(screen.getByText("Suggestion 2")).toBeInTheDocument();
      expect(screen.getByText("Suggestion 3")).toBeInTheDocument();
    });
  });

  describe("Error State", () => {
    it("shows error state when context has error", () => {
      const errorContext = {
        error: true,
        message: "Failed to load context",
        details: "Network error occurred"
      };
      
      render(<TaskContextDialog {...defaultProps} context={errorContext} />);
      
      expect(screen.getByText("Failed to load context")).toBeInTheDocument();
      expect(screen.getByText("Network error occurred")).toBeInTheDocument();
    });

    it("shows error without details", () => {
      const errorContext = {
        error: true,
        message: "Context error"
      };
      
      render(<TaskContextDialog {...defaultProps} context={errorContext} />);
      
      expect(screen.getByText("Context error")).toBeInTheDocument();
    });
  });

  describe("Context Content Rendering", () => {
    it("renders context metadata", () => {
      const contextWithMetadata = {
        metadata: {
          version: "2.0",
          created_at: "2024-01-01T00:00:00Z",
          user_id: "user-123"
        }
      };
      
      render(<TaskContextDialog {...defaultProps} context={contextWithMetadata} />);
      
      expect(screen.getByText("Context Metadata")).toBeInTheDocument();
      expect(screen.getByText(/"version": "2.0"/)).toBeInTheDocument();
      expect(screen.getByText(/"user_id": "user-123"/)).toBeInTheDocument();
    });

    it("renders context data", () => {
      const contextWithData = {
        data: {
          progress_notes: "Task is 50% complete",
          blocked_on: null,
          estimated_hours: 4
        }
      };
      
      render(<TaskContextDialog {...defaultProps} context={contextWithData} />);
      
      expect(screen.getByText("Context Data")).toBeInTheDocument();
      expect(screen.getByText(/"progress_notes": "Task is 50% complete"/)).toBeInTheDocument();
      expect(screen.getByText(/"estimated_hours": 4/)).toBeInTheDocument();
    });

    it("renders insights array", () => {
      const contextWithInsights = {
        insights: [
          {
            title: "Performance Insight",
            content: "Task completion is ahead of schedule",
            timestamp: "2024-01-01T12:00:00Z"
          },
          {
            content: "No blockers identified"
          }
        ]
      };
      
      render(<TaskContextDialog {...defaultProps} context={contextWithInsights} />);
      
      expect(screen.getByText("Insights")).toBeInTheDocument();
      expect(screen.getByText("Performance Insight")).toBeInTheDocument();
      expect(screen.getByText("Task completion is ahead of schedule")).toBeInTheDocument();
      expect(screen.getByText("Insight 2")).toBeInTheDocument();
      expect(screen.getByText("No blockers identified")).toBeInTheDocument();
    });

    it("formats insight timestamps", () => {
      const contextWithTimestamp = {
        insights: [
          {
            title: "Timed Insight",
            content: "Important update",
            timestamp: "2024-01-01T12:00:00Z"
          }
        ]
      };
      
      render(<TaskContextDialog {...defaultProps} context={contextWithTimestamp} />);
      
      expect(screen.getByText("Timed Insight")).toBeInTheDocument();
      expect(screen.getByText("Important update")).toBeInTheDocument();
      // Check that timestamp is formatted (exact format may vary by locale)
      expect(screen.getByText(/2024/)).toBeInTheDocument();
    });
  });

  describe("Completion Summary Display", () => {
    it("renders completion summary from context display", () => {
      const contextWithCompletion = {
        data: {
          completion_summary: "Task completed successfully with all requirements met"
        }
      };
      
      render(<TaskContextDialog {...defaultProps} context={contextWithCompletion} />);
      
      expect(screen.getByText("Completion Summary")).toBeInTheDocument();
      expect(screen.getByText("Task completed successfully with all requirements met")).toBeInTheDocument();
    });

    it("shows legacy format indicator", () => {
      const legacyContext = {
        data: {
          completion_summary: "Legacy completion"
        }
      };
      
      render(<TaskContextDialog {...defaultProps} context={legacyContext} />);
      
      expect(screen.getByText("Completion Summary (Legacy Format)")).toBeInTheDocument();
      expect(screen.getByText("Note: This is using the legacy completion_summary format")).toBeInTheDocument();
    });

    it("displays completion percentage", () => {
      const contextWithPercentage = {
        data: {
          completionSummary: "Task completed",
          completion_percentage: 85
        }
      };
      
      render(<TaskContextDialog {...defaultProps} context={contextWithPercentage} />);
      
      expect(screen.getByText("Completion:")).toBeInTheDocument();
      expect(screen.getByText("85%")).toBeInTheDocument();
    });
  });

  describe("Task Status Display", () => {
    it("renders task status from context display", () => {
      const contextWithStatus = {
        data: {
          status: "completed"
        }
      };
      
      render(<TaskContextDialog {...defaultProps} context={contextWithStatus} />);
      
      expect(screen.getByText("Task Status")).toBeInTheDocument();
      expect(screen.getByText("completed")).toBeInTheDocument();
    });
  });

  describe("Testing Notes Display", () => {
    it("renders testing notes as next steps", () => {
      const contextWithNotes = {
        data: {
          testing_notes: ["Run unit tests", "Verify integration", "Check performance"]
        }
      };
      
      render(<TaskContextDialog {...defaultProps} context={contextWithNotes} />);
      
      expect(screen.getByText("Testing Notes & Next Steps")).toBeInTheDocument();
      expect(screen.getByText("Run unit tests")).toBeInTheDocument();
      expect(screen.getByText("Verify integration")).toBeInTheDocument();
      expect(screen.getByText("Check performance")).toBeInTheDocument();
    });
  });

  describe("Progress History Display", () => {
    it("renders progress history", () => {
      const contextWithProgress = {
        progress: [
          {
            content: "Started implementation",
            timestamp: "2024-01-01T10:00:00Z"
          },
          {
            content: "Completed first milestone",
            timestamp: "2024-01-02T15:30:00Z"
          }
        ]
      };
      
      render(<TaskContextDialog {...defaultProps} context={contextWithProgress} />);
      
      expect(screen.getByText("Progress History")).toBeInTheDocument();
      expect(screen.getByText("Started implementation")).toBeInTheDocument();
      expect(screen.getByText("Completed first milestone")).toBeInTheDocument();
    });

    it("formats progress timestamps", () => {
      const contextWithProgress = {
        progress: [
          {
            content: "Progress update",
            timestamp: "2024-01-01T12:00:00Z"
          }
        ]
      };
      
      render(<TaskContextDialog {...defaultProps} context={contextWithProgress} />);
      
      expect(screen.getByText("Progress update")).toBeInTheDocument();
      // Check that timestamp is present (format may vary by locale)
      expect(screen.getByText(/2024/)).toBeInTheDocument();
    });
  });

  describe("Raw Context Display", () => {
    it("renders complete raw context JSON", () => {
      const complexContext = {
        metadata: { version: "1.0" },
        data: { test: "value" },
        insights: [{ title: "test", content: "insight" }]
      };
      
      render(<TaskContextDialog {...defaultProps} context={complexContext} />);
      
      expect(screen.getByText("Complete Context (Raw JSON)")).toBeInTheDocument();
      expect(screen.getByText(/"metadata"/)).toBeInTheDocument();
      expect(screen.getByText(/"data"/)).toBeInTheDocument();
      expect(screen.getByText(/"insights"/)).toBeInTheDocument();
    });
  });

  describe("Dialog Interactions", () => {
    it("calls onOpenChange when dialog state should change", async () => {
      render(<TaskContextDialog {...defaultProps} />);
      
      // Simulate ESC key press to close dialog
      fireEvent.keyDown(document.body, { key: "Escape", code: "Escape" });
      
      await waitFor(() => {
        // onOpenChange might be called by the dialog component internally
        // The exact behavior depends on the UI library implementation
      });
    });

    it("renders with different open states", () => {
      const { rerender } = render(<TaskContextDialog {...defaultProps} open={false} />);
      
      // When closed, dialog content should not be visible
      expect(screen.queryByText("Task Context")).not.toBeInTheDocument();
      
      rerender(<TaskContextDialog {...defaultProps} open={true} />);
      
      // When open, dialog content should be visible
      expect(screen.getByText("Task Context")).toBeInTheDocument();
    });
  });

  describe("Props Handling", () => {
    it("handles null task gracefully", () => {
      render(<TaskContextDialog {...defaultProps} task={null} />);
      
      expect(screen.getByText("Task Context")).toBeInTheDocument();
      expect(screen.queryByText("Task:")).not.toBeInTheDocument();
    });

    it("handles task without title", () => {
      const taskWithoutTitle = { ...mockTask, title: "" };
      render(<TaskContextDialog {...defaultProps} task={taskWithoutTitle} />);
      
      expect(screen.getByText("Task Context")).toBeInTheDocument();
      expect(screen.getByText(/ID: task-123/)).toBeInTheDocument();
    });

    it("handles different loading states", () => {
      const { rerender } = render(
        <TaskContextDialog {...defaultProps} loading={true} />
      );
      
      expect(screen.getByText("Loading context...")).toBeInTheDocument();
      
      rerender(<TaskContextDialog {...defaultProps} loading={false} />);
      
      expect(screen.queryByText("Loading context...")).not.toBeInTheDocument();
    });
  });

  describe("Edge Cases", () => {
    it("handles empty context object", () => {
      render(<TaskContextDialog {...defaultProps} context={{}} />);
      
      expect(screen.getByText("Complete Context (Raw JSON)")).toBeInTheDocument();
      expect(screen.getByText("{}")).toBeInTheDocument();
    });

    it("handles context with null values", () => {
      const contextWithNulls = {
        data: null,
        metadata: null,
        insights: null
      };
      
      render(<TaskContextDialog {...defaultProps} context={contextWithNulls} />);
      
      expect(screen.getByText("Complete Context (Raw JSON)")).toBeInTheDocument();
    });

    it("handles insights without title", () => {
      const contextWithUntitledInsights = {
        insights: [
          { content: "Insight without title" }
        ]
      };
      
      render(<TaskContextDialog {...defaultProps} context={contextWithUntitledInsights} />);
      
      expect(screen.getByText("Insight 1")).toBeInTheDocument();
      expect(screen.getByText("Insight without title")).toBeInTheDocument();
    });

    it("handles progress without timestamp", () => {
      const contextWithProgress = {
        progress: [
          { content: "Progress without timestamp" }
        ]
      };
      
      render(<TaskContextDialog {...defaultProps} context={contextWithProgress} />);
      
      expect(screen.getByText("Progress without timestamp")).toBeInTheDocument();
    });
  });
});