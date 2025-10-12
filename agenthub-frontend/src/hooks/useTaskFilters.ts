import { useState, useMemo, useCallback } from 'react';
import type { TaskSummary, TaskStatus, TaskPriority } from '../types/taskTypes';
import type { TaskFilters, UseTaskFiltersReturn } from '../types/hookTypes';

const defaultFilters: TaskFilters = {
  search: '',
  status: 'all',
  priority: 'all',
  assignee: 'all'
};

export function useTaskFilters(tasks: TaskSummary[]): UseTaskFiltersReturn {
  const [filters, setFilters] = useState<TaskFilters>(defaultFilters);

  const setSearchFilter = useCallback((search: string) => {
    setFilters(prev => ({ ...prev, search }));
  }, []);

  const setStatusFilter = useCallback((status: TaskStatus | 'all') => {
    setFilters(prev => ({ ...prev, status }));
  }, []);

  const setPriorityFilter = useCallback((priority: TaskPriority | 'all') => {
    setFilters(prev => ({ ...prev, priority }));
  }, []);

  const setAssigneeFilter = useCallback((assignee: string | 'all') => {
    setFilters(prev => ({ ...prev, assignee }));
  }, []);

  const clearFilters = useCallback(() => {
    setFilters(defaultFilters);
  }, []);

  const applyFilters = useCallback((tasksToFilter: TaskSummary[]): TaskSummary[] => {
    return tasksToFilter.filter(task => {
      // Search filter - check title and assignees
      if (filters.search) {
        const searchTerm = filters.search.toLowerCase();
        const titleMatch = task.title.toLowerCase().includes(searchTerm);
        const assigneeMatch = task.assignees?.some(assignee =>
          assignee.toLowerCase().includes(searchTerm)
        ) || false;

        if (!titleMatch && !assigneeMatch) {
          return false;
        }
      }

      // Status filter
      if (filters.status !== 'all' && task.status !== filters.status) {
        return false;
      }

      // Priority filter
      if (filters.priority !== 'all' && task.priority !== filters.priority) {
        return false;
      }

      // Assignee filter
      if (filters.assignee !== 'all') {
        if (!task.assignees || !task.assignees.includes(filters.assignee)) {
          return false;
        }
      }

      return true;
    });
  }, [filters]);

  const filteredTasks = useMemo(() => {
    return applyFilters(tasks);
  }, [tasks, applyFilters]);

  const filteredTaskCount = filteredTasks.length;

  return {
    filters,
    setSearchFilter,
    setStatusFilter,
    setPriorityFilter,
    setAssigneeFilter,
    clearFilters,
    applyFilters,
    filteredTaskCount
  };
}