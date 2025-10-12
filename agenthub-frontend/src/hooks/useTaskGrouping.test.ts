import { renderHook, act } from '@testing-library/react';
import { useTaskGrouping } from './useTaskGrouping';
import { TaskSummary } from '../types/taskTypes';

const mockTasks: TaskSummary[] = [
  {
    id: '1',
    title: 'Alpha Task',
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
    title: 'Beta Task',
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
    title: 'Charlie Task',
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

describe('useTaskGrouping', () => {
  it('should initialize with default settings', () => {
    const { result } = renderHook(() => useTaskGrouping(mockTasks));

    expect(result.current.groupBy).toBe('none');
    expect(result.current.sorting).toEqual({
      sortBy: 'created_at',
      sortOrder: 'desc'
    });
    expect(result.current.isGrouped).toBe(false);
  });

  it('should sort tasks by title ascending', () => {
    const { result } = renderHook(() => useTaskGrouping(mockTasks));

    act(() => {
      result.current.setSorting({ sortBy: 'title', sortOrder: 'asc' });
    });

    const sortedTasks = result.current.sortTasks(mockTasks);
    expect(sortedTasks[0].title).toBe('Alpha Task');
    expect(sortedTasks[1].title).toBe('Beta Task');
    expect(sortedTasks[2].title).toBe('Charlie Task');
  });

  it('should sort tasks by title descending', () => {
    const { result } = renderHook(() => useTaskGrouping(mockTasks));

    act(() => {
      result.current.setSorting({ sortBy: 'title', sortOrder: 'desc' });
    });

    const sortedTasks = result.current.sortTasks(mockTasks);
    expect(sortedTasks[0].title).toBe('Charlie Task');
    expect(sortedTasks[1].title).toBe('Beta Task');
    expect(sortedTasks[2].title).toBe('Alpha Task');
  });

  it('should sort tasks by status in natural order', () => {
    const { result } = renderHook(() => useTaskGrouping(mockTasks));

    act(() => {
      result.current.setSorting({ sortBy: 'status', sortOrder: 'asc' });
    });

    const sortedTasks = result.current.sortTasks(mockTasks);
    expect(sortedTasks[0].status).toBe('todo');
    expect(sortedTasks[1].status).toBe('in_progress');
    expect(sortedTasks[2].status).toBe('done');
  });

  it('should sort tasks by priority in natural order', () => {
    const { result } = renderHook(() => useTaskGrouping(mockTasks));

    act(() => {
      result.current.setSorting({ sortBy: 'priority', sortOrder: 'asc' });
    });

    const sortedTasks = result.current.sortTasks(mockTasks);
    expect(sortedTasks[0].priority).toBe('critical');
    expect(sortedTasks[1].priority).toBe('high');
    expect(sortedTasks[2].priority).toBe('medium');
  });

  it('should group tasks by status', () => {
    const { result } = renderHook(() => useTaskGrouping(mockTasks));

    act(() => {
      result.current.setGroupBy('status');
    });

    const groups = result.current.groupTasks(mockTasks);
    expect(groups).toHaveLength(3);

    const todoGroup = groups.find(g => g.groupKey === 'todo');
    const inProgressGroup = groups.find(g => g.groupKey === 'in_progress');
    const doneGroup = groups.find(g => g.groupKey === 'done');

    expect(todoGroup?.count).toBe(1);
    expect(inProgressGroup?.count).toBe(1);
    expect(doneGroup?.count).toBe(1);
  });

  it('should group tasks by priority', () => {
    const { result } = renderHook(() => useTaskGrouping(mockTasks));

    act(() => {
      result.current.setGroupBy('priority');
    });

    const groups = result.current.groupTasks(mockTasks);
    expect(groups).toHaveLength(3);

    const criticalGroup = groups.find(g => g.groupKey === 'critical');
    const highGroup = groups.find(g => g.groupKey === 'high');
    const mediumGroup = groups.find(g => g.groupKey === 'medium');

    expect(criticalGroup?.count).toBe(1);
    expect(highGroup?.count).toBe(1);
    expect(mediumGroup?.count).toBe(1);
  });

  it('should group tasks by assignee', () => {
    const { result } = renderHook(() => useTaskGrouping(mockTasks));

    act(() => {
      result.current.setGroupBy('assignee');
    });

    const groups = result.current.groupTasks(mockTasks);
    expect(groups).toHaveLength(2); // john.doe and jane.smith (first assignee)

    const johnGroup = groups.find(g => g.groupKey === 'john.doe');
    const janeGroup = groups.find(g => g.groupKey === 'jane.smith');

    expect(johnGroup?.count).toBe(2);
    expect(janeGroup?.count).toBe(1);
  });

  it('should provide correct group labels', () => {
    const { result } = renderHook(() => useTaskGrouping(mockTasks));

    act(() => {
      result.current.setGroupBy('status');
    });

    const groups = result.current.groupTasks(mockTasks);
    const todoGroup = groups.find(g => g.groupKey === 'todo');
    const inProgressGroup = groups.find(g => g.groupKey === 'in_progress');
    const doneGroup = groups.find(g => g.groupKey === 'done');

    expect(todoGroup?.groupLabel).toBe('To Do');
    expect(inProgressGroup?.groupLabel).toBe('In Progress');
    expect(doneGroup?.groupLabel).toBe('Done');
  });

  it('should return flat sorted tasks when groupBy is none', () => {
    const { result } = renderHook(() => useTaskGrouping(mockTasks));

    expect(result.current.isGrouped).toBe(false);
    expect(Array.isArray(result.current.processedTasks)).toBe(true);
    expect((result.current.processedTasks as TaskSummary[]).length).toBe(3);
  });

  it('should return grouped tasks when groupBy is set', () => {
    const { result } = renderHook(() => useTaskGrouping(mockTasks));

    act(() => {
      result.current.setGroupBy('status');
    });

    expect(result.current.isGrouped).toBe(true);
    expect(Array.isArray(result.current.processedTasks)).toBe(true);
    expect((result.current.processedTasks as any[]).length).toBe(3); // 3 groups
    expect((result.current.processedTasks as any[])[0]).toHaveProperty('groupKey');
  });
});