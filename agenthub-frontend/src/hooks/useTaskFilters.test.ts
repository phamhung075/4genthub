import { renderHook, act } from '@testing-library/react';
import { useTaskFilters } from './useTaskFilters';
import { TaskSummary } from '../types/taskTypes';

const mockTasks: TaskSummary[] = [
  {
    id: '1',
    title: 'Task 1',
    status: 'todo',
    priority: 'high',
    subtask_count: 0,
    assignees_count: 1,
    assignees: ['john.doe'],
    has_dependencies: false,
    has_context: false,
    created_at: '2024-01-01T00:00:00Z'
  },
  {
    id: '2',
    title: 'Task 2',
    status: 'in_progress',
    priority: 'medium',
    subtask_count: 2,
    assignees_count: 2,
    assignees: ['jane.smith', 'bob.jones'],
    has_dependencies: true,
    has_context: true,
    created_at: '2024-01-02T00:00:00Z'
  },
  {
    id: '3',
    title: 'Bug Fix',
    status: 'done',
    priority: 'critical',
    subtask_count: 0,
    assignees_count: 1,
    assignees: ['john.doe'],
    has_dependencies: false,
    has_context: false,
    created_at: '2024-01-03T00:00:00Z'
  }
];

describe('useTaskFilters', () => {
  it('should initialize with default filters', () => {
    const { result } = renderHook(() => useTaskFilters(mockTasks));

    expect(result.current.filters).toEqual({
      search: '',
      status: 'all',
      priority: 'all',
      assignee: 'all'
    });
    expect(result.current.filteredTaskCount).toBe(3);
  });

  it('should filter tasks by search term', () => {
    const { result } = renderHook(() => useTaskFilters(mockTasks));

    act(() => {
      result.current.setSearchFilter('Bug');
    });

    const filteredTasks = result.current.applyFilters(mockTasks);
    expect(filteredTasks).toHaveLength(1);
    expect(filteredTasks[0].title).toBe('Bug Fix');
  });

  it('should filter tasks by status', () => {
    const { result } = renderHook(() => useTaskFilters(mockTasks));

    act(() => {
      result.current.setStatusFilter('in_progress');
    });

    const filteredTasks = result.current.applyFilters(mockTasks);
    expect(filteredTasks).toHaveLength(1);
    expect(filteredTasks[0].status).toBe('in_progress');
  });

  it('should filter tasks by priority', () => {
    const { result } = renderHook(() => useTaskFilters(mockTasks));

    act(() => {
      result.current.setPriorityFilter('high');
    });

    const filteredTasks = result.current.applyFilters(mockTasks);
    expect(filteredTasks).toHaveLength(1);
    expect(filteredTasks[0].priority).toBe('high');
  });

  it('should filter tasks by assignee', () => {
    const { result } = renderHook(() => useTaskFilters(mockTasks));

    act(() => {
      result.current.setAssigneeFilter('john.doe');
    });

    const filteredTasks = result.current.applyFilters(mockTasks);
    expect(filteredTasks).toHaveLength(2);
    expect(filteredTasks.every(task => task.assignees?.includes('john.doe'))).toBe(true);
  });

  it('should clear all filters', () => {
    const { result } = renderHook(() => useTaskFilters(mockTasks));

    act(() => {
      result.current.setSearchFilter('test');
      result.current.setStatusFilter('done');
      result.current.setPriorityFilter('high');
      result.current.setAssigneeFilter('john.doe');
    });

    act(() => {
      result.current.clearFilters();
    });

    expect(result.current.filters).toEqual({
      search: '',
      status: 'all',
      priority: 'all',
      assignee: 'all'
    });
  });

  it('should apply multiple filters simultaneously', () => {
    const { result } = renderHook(() => useTaskFilters(mockTasks));

    act(() => {
      result.current.setStatusFilter('todo');
      result.current.setPriorityFilter('high');
    });

    const filteredTasks = result.current.applyFilters(mockTasks);
    expect(filteredTasks).toHaveLength(1);
    expect(filteredTasks[0].status).toBe('todo');
    expect(filteredTasks[0].priority).toBe('high');
  });
});