import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { vi } from "vitest";
import TaskRowDesktop from "../../../../components/TaskRow/components/TaskRowDesktop";
import { Task } from "../../../../types/taskTypes";
import { useAuth } from "../../../../hooks/useAuth";
import { formatDistanceToNow } from "date-fns";

// Mock dependencies
vi.mock("../../../../hooks/useAuth", () => ({
  useAuth: vi.fn()
}));

vi.mock("date-fns", () => ({
  formatDistanceToNow: vi.fn()
}));

vi.mock("../../../../components/ui/badge", () => ({
  Badge: ({ children, variant, className }: any) => (
    <span data-testid="badge" data-variant={variant} className={className}>
      {children}
    </span>
  )
}));

vi.mock("../../../../components/ui/button", () => ({
  Button: ({ children, onClick, disabled, variant, size }: any) => (
    <button 
      onClick={onClick} 
      disabled={disabled}
      data-variant={variant}
      data-size={size}
    >
      {children}
    </button>
  )
}));

vi.mock("lucide-react", () => ({
  Calendar: () => <span data-testid="calendar-icon">Calendar</span>,
  CheckCircle2: () => <span data-testid="check-icon">Check</span>,
  Clock: () => <span data-testid="clock-icon">Clock</span>,
  AlertCircle: () => <span data-testid="alert-icon">Alert</span>,
  Circle: () => <span data-testid="circle-icon">Circle</span>,
  Loader2: () => <span data-testid="loader-icon">Loader</span>,
  ChevronRight: () => <span data-testid="chevron-icon">Chevron</span>,
  ChevronDown: () => <span data-testid="chevron-down-icon">ChevronDown</span>,
  MoreVertical: () => <span data-testid="more-icon">More</span>
}));

describe("TaskRowDesktop", () => {
  const mockTask: Task = {
    id: "task-1",
    title: "Test Task",
    description: "Test Description",
    status: "todo",
    priority: "medium",
    details: null,
    assignees: ["user1", "user2"],
    labels: ["frontend", "bug"],
    estimated_effort: "2 hours",
    due_date: "2024-12-31T00:00:00Z",
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    git_branch_id: "branch-1",
    project_id: "project-1",
    parent_task_id: null,
    dependencies: [],
    blocking_tasks: [],
    subtask_ids: ["sub1", "sub2"],
    subtasks: ["sub1", "sub2"], // Array of subtask IDs
    context_id: null,
    completion_summary: null
  };

  const defaultProps = {
    task: mockTask,
    isExpanded: false,
    isEditing: false,
    editTitle: "",
    isSaving: false,
    onToggleExpand: vi.fn(),
    onStartEdit: vi.fn(),
    onCancelEdit: vi.fn(),
    onSaveEdit: vi.fn(),
    onEditTitleChange: vi.fn(),
    onKeyPress: vi.fn(),
    onStatusChange: vi.fn(),
    onDelete: vi.fn(),
    onOpenDetails: vi.fn(),
    getStatusIcon: vi.fn().mockReturnValue(<span data-testid="status-icon">Status</span>),
    getStatusColor: vi.fn().mockReturnValue("text-gray-500"),
    getPriorityColor: vi.fn().mockReturnValue("text-blue-500"),
    getPriorityBadgeVariant: vi.fn().mockReturnValue("default" as const),
    getDueDateColor: vi.fn().mockReturnValue("text-gray-500")
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (useAuth as any).mockReturnValue({
      user: { id: "user1", email: "user@example.com" }
    });
    (formatDistanceToNow as any).mockReturnValue("2 days ago");
  });

  it("should render task row with all elements", () => {
    render(<TaskRowDesktop {...defaultProps} />);

    expect(screen.getByText("Test Task")).toBeInTheDocument();
    expect(screen.getByText("medium")).toBeInTheDocument();
    expect(screen.getByText("todo")).toBeInTheDocument();
    expect(screen.getByText("user1, user2")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument(); // subtask count
    expect(screen.getByTestId("status-icon")).toBeInTheDocument();
  });

  it("should render edit mode when isEditing is true", () => {
    const props = { ...defaultProps, isEditing: true, editTitle: "Edited Title" };
    render(<TaskRowDesktop {...props} />);

    const input = screen.getByDisplayValue("Edited Title");
    expect(input).toBeInTheDocument();
    expect(screen.getByText("Save")).toBeInTheDocument();
    expect(screen.getByText("Cancel")).toBeInTheDocument();
  });

  it("should call onEditTitleChange when input changes", () => {
    const props = { ...defaultProps, isEditing: true, editTitle: "Test" };
    render(<TaskRowDesktop {...props} />);

    const input = screen.getByDisplayValue("Test");
    fireEvent.change(input, { target: { value: "New Title" } });

    expect(defaultProps.onEditTitleChange).toHaveBeenCalled();
  });

  it("should call onKeyPress when key is pressed in input", () => {
    const props = { ...defaultProps, isEditing: true };
    render(<TaskRowDesktop {...props} />);

    const input = screen.getByRole("textbox");
    fireEvent.keyPress(input, { key: "Enter" });

    expect(defaultProps.onKeyPress).toHaveBeenCalled();
  });

  it("should call onSaveEdit when save button is clicked", () => {
    const props = { ...defaultProps, isEditing: true };
    render(<TaskRowDesktop {...props} />);

    fireEvent.click(screen.getByText("Save"));

    expect(defaultProps.onSaveEdit).toHaveBeenCalled();
  });

  it("should call onCancelEdit when cancel button is clicked", () => {
    const props = { ...defaultProps, isEditing: true };
    render(<TaskRowDesktop {...props} />);

    fireEvent.click(screen.getByText("Cancel"));

    expect(defaultProps.onCancelEdit).toHaveBeenCalled();
  });

  it("should show loading state when isSaving is true", () => {
    const props = { ...defaultProps, isEditing: true, isSaving: true };
    render(<TaskRowDesktop {...props} />);

    expect(screen.getByTestId("loader-icon")).toBeInTheDocument();
    expect(screen.getByText("Save").closest("button")).toBeDisabled();
  });

  it("should call onToggleExpand when expand button is clicked", () => {
    render(<TaskRowDesktop {...defaultProps} />);

    const expandButton = screen.getByTestId("chevron-icon").closest("button");
    fireEvent.click(expandButton!);

    expect(defaultProps.onToggleExpand).toHaveBeenCalled();
  });

  it("should show chevron down icon when expanded", () => {
    const props = { ...defaultProps, isExpanded: true };
    render(<TaskRowDesktop {...props} />);

    expect(screen.getByTestId("chevron-down-icon")).toBeInTheDocument();
  });

  it("should render labels as badges", () => {
    render(<TaskRowDesktop {...defaultProps} />);

    const badges = screen.getAllByTestId("badge");
    expect(badges).toHaveLength(2);
    expect(badges[0]).toHaveTextContent("frontend");
    expect(badges[1]).toHaveTextContent("bug");
  });

  it("should render due date", () => {
    render(<TaskRowDesktop {...defaultProps} />);

    expect(screen.getByTestId("calendar-icon")).toBeInTheDocument();
    expect(screen.getByText("2 days ago")).toBeInTheDocument();
  });

  it("should render estimated effort when present", () => {
    render(<TaskRowDesktop {...defaultProps} />);

    expect(screen.getByTestId("clock-icon")).toBeInTheDocument();
    expect(screen.getByText("2 hours")).toBeInTheDocument();
  });

  it("should not render subtask count when zero", () => {
    const props = {
      ...defaultProps,
      task: { ...mockTask, subtasks: [] }
    };
    render(<TaskRowDesktop {...props} />);

    // The badge with "0" should not be present
    const badges = screen.getAllByTestId("badge");
    const subtaskBadge = badges.find(badge => badge.textContent === "0");
    expect(subtaskBadge).toBeUndefined();
  });

  it("should handle missing assignees", () => {
    const props = {
      ...defaultProps,
      task: { ...mockTask, assignees: [] }
    };
    render(<TaskRowDesktop {...props} />);

    expect(screen.getByText("-")).toBeInTheDocument();
  });

  it("should handle missing due date", () => {
    const props = {
      ...defaultProps,
      task: { ...mockTask, due_date: null }
    };
    render(<TaskRowDesktop {...props} />);

    expect(screen.queryByTestId("calendar-icon")).not.toBeInTheDocument();
  });

  it("should apply correct status color", () => {
    defaultProps.getStatusColor.mockReturnValue("text-green-500");
    render(<TaskRowDesktop {...defaultProps} />);

    expect(defaultProps.getStatusColor).toHaveBeenCalledWith("todo");
    expect(screen.getByText("todo")).toHaveClass("text-green-500");
  });

  it("should apply correct priority color and variant", () => {
    defaultProps.getPriorityColor.mockReturnValue("text-red-500");
    defaultProps.getPriorityBadgeVariant.mockReturnValue("destructive" as const);
    render(<TaskRowDesktop {...defaultProps} />);

    expect(defaultProps.getPriorityColor).toHaveBeenCalledWith("medium");
    expect(defaultProps.getPriorityBadgeVariant).toHaveBeenCalledWith("medium");
    
    const priorityBadge = screen.getByText("medium");
    expect(priorityBadge).toHaveAttribute("data-variant", "destructive");
  });
});