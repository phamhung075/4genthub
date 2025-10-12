import { useState, useMemo, useCallback } from 'react';
import type { TaskSummary, TaskStatus, TaskPriority } from '../types/taskTypes';
import type {
  GroupBy,
  SortBy,
  SortOrder,
  TaskGroup,
  TaskSorting,
  UseTaskGroupingReturn
} from '../types/hookTypes';

const defaultSorting: TaskSorting = {
  sortBy: 'created_at',
  sortOrder: 'desc'
};

const STATUS_ORDER: TaskStatus[] = ['todo', 'in_progress', 'review', 'testing', 'blocked', 'done', 'cancelled'];
const PRIORITY_ORDER: TaskPriority[] = ['critical', 'urgent', 'high', 'medium', 'low'];

export function useTaskGrouping(tasks: TaskSummary[]): UseTaskGroupingReturn {
  const [groupBy, setGroupBy] = useState<GroupBy>('none');
  const [sorting, setSortingState] = useState<TaskSorting>(defaultSorting);

  const setSorting = useCallback((partialSorting: Partial<TaskSorting>) => {
    setSortingState(prev => ({ ...prev, ...partialSorting }));
  }, []);

  const sortTasks = useCallback((tasksToSort: TaskSummary[]): TaskSummary[] => {
    return [...tasksToSort].sort((a, b) => {
      let comparison = 0;

      switch (sorting.sortBy) {
        case 'title':
          comparison = a.title.localeCompare(b.title);
          break;
        case 'status':
          const aStatusIndex = STATUS_ORDER.indexOf(a.status as TaskStatus);
          const bStatusIndex = STATUS_ORDER.indexOf(b.status as TaskStatus);
          comparison = aStatusIndex - bStatusIndex;
          break;
        case 'priority':
          const aPriorityIndex = PRIORITY_ORDER.indexOf(a.priority as TaskPriority);
          const bPriorityIndex = PRIORITY_ORDER.indexOf(b.priority as TaskPriority);
          comparison = aPriorityIndex - bPriorityIndex;
          break;
        case 'created_at':
          const aCreated = new Date(a.created_at || 0).getTime();
          const bCreated = new Date(b.created_at || 0).getTime();
          comparison = aCreated - bCreated;
          break;
        case 'updated_at':
          const aUpdated = new Date(a.updated_at || 0).getTime();
          const bUpdated = new Date(b.updated_at || 0).getTime();
          comparison = aUpdated - bUpdated;
          break;
        default:
          comparison = 0;
      }

      return sorting.sortOrder === 'asc' ? comparison : -comparison;
    });
  }, [sorting]);

  const getGroupLabel = useCallback((groupKey: string, groupByField: GroupBy): string => {
    switch (groupByField) {
      case 'status':
        const statusLabels: Record<string, string> = {
          'todo': 'To Do',
          'in_progress': 'In Progress',
          'review': 'Review',
          'testing': 'Testing',
          'blocked': 'Blocked',
          'done': 'Done',
          'cancelled': 'Cancelled'
        };
        return statusLabels[groupKey] || groupKey;
      case 'priority':
        const priorityLabels: Record<string, string> = {
          'critical': 'Critical',
          'urgent': 'Urgent',
          'high': 'High',
          'medium': 'Medium',
          'low': 'Low'
        };
        return priorityLabels[groupKey] || groupKey;
      case 'assignee':
        return groupKey || 'Unassigned';
      default:
        return groupKey;
    }
  }, []);

  const groupTasks = useCallback((tasksToGroup: TaskSummary[]): TaskGroup[] => {
    if (groupBy === 'none') {
      return [];
    }

    const groups = new Map<string, TaskSummary[]>();

    tasksToGroup.forEach(task => {
      let groupKey: string;

      switch (groupBy) {
        case 'status':
          groupKey = task.status;
          break;
        case 'priority':
          groupKey = task.priority;
          break;
        case 'assignee':
          // Group by first assignee, or 'unassigned' if no assignees
          groupKey = task.assignees && task.assignees.length > 0
            ? task.assignees[0]
            : 'unassigned';
          break;
        default:
          groupKey = 'default';
      }

      if (!groups.has(groupKey)) {
        groups.set(groupKey, []);
      }
      groups.get(groupKey)!.push(task);
    });

    // Convert to array of TaskGroup objects and sort groups
    const groupArray = Array.from(groups.entries()).map(([groupKey, groupTasks]) => ({
      groupKey,
      groupLabel: getGroupLabel(groupKey, groupBy),
      tasks: sortTasks(groupTasks),
      count: groupTasks.length
    }));

    // Sort groups by their natural order
    return groupArray.sort((a, b) => {
      switch (groupBy) {
        case 'status':
          const aIndex = STATUS_ORDER.indexOf(a.groupKey as TaskStatus);
          const bIndex = STATUS_ORDER.indexOf(b.groupKey as TaskStatus);
          return aIndex - bIndex;
        case 'priority':
          const aPriorityIndex = PRIORITY_ORDER.indexOf(a.groupKey as TaskPriority);
          const bPriorityIndex = PRIORITY_ORDER.indexOf(b.groupKey as TaskPriority);
          return aPriorityIndex - bPriorityIndex;
        case 'assignee':
          // Sort alphabetically, with 'unassigned' last
          if (a.groupKey === 'unassigned') return 1;
          if (b.groupKey === 'unassigned') return -1;
          return a.groupKey.localeCompare(b.groupKey);
        default:
          return a.groupKey.localeCompare(b.groupKey);
      }
    });
  }, [groupBy, sortTasks, getGroupLabel]);

  const processedTasks = useMemo(() => {
    if (groupBy === 'none') {
      return sortTasks(tasks);
    } else {
      return groupTasks(tasks);
    }
  }, [tasks, groupBy, sortTasks, groupTasks]);

  const isGrouped = groupBy !== 'none';

  return {
    groupBy,
    sorting,
    setGroupBy,
    setSorting,
    sortTasks,
    groupTasks,
    processedTasks,
    isGrouped
  };
}