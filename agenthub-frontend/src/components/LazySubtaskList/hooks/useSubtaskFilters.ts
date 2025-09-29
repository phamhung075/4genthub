// useSubtaskFilters hook - Filtering logic for LazySubtaskList
// Extracted from original LazySubtaskList.tsx during SOLID refactoring

import { useState, useMemo, useCallback } from "react";
import { SubtaskSummary } from "../../../types/taskTypes";
import type { SubtaskFilterOptions, UseSubtaskFiltersReturn } from "../types/subtaskTypes";
import { filterSubtasks, sortSubtasks } from "../utils/subtaskHelpers";

/**
 * Custom hook for managing subtask filtering and sorting
 * Provides filtered results and filter state management
 */
export function useSubtaskFilters(
  subtasks: SubtaskSummary[],
  defaultSortField: 'title' | 'status' | 'priority' | 'progress_percentage' = 'title',
  defaultSortDirection: 'asc' | 'desc' = 'asc'
): UseSubtaskFiltersReturn {

  // Filter state
  const [filterOptions, setFilterOptions] = useState<SubtaskFilterOptions>({});
  const [sortField, setSortField] = useState<'title' | 'status' | 'priority' | 'progress_percentage'>(defaultSortField);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>(defaultSortDirection);

  /**
   * Apply filters and sorting to subtasks
   */
  const filteredSubtasks = useMemo(() => {
    // First apply filters
    let filtered = filterSubtasks(subtasks, filterOptions);

    // Then apply sorting
    filtered = sortSubtasks(filtered, sortField, sortDirection);

    return filtered;
  }, [subtasks, filterOptions, sortField, sortDirection]);

  /**
   * Update filter options
   */
  const updateFilterOptions = useCallback((newOptions: SubtaskFilterOptions) => {
    setFilterOptions(prev => ({
      ...prev,
      ...newOptions
    }));
  }, []);

  /**
   * Clear all filters
   */
  const clearFilters = useCallback(() => {
    setFilterOptions({});
  }, []);

  /**
   * Update sort configuration
   */
  const updateSort = useCallback((
    field: 'title' | 'status' | 'priority' | 'progress_percentage',
    direction?: 'asc' | 'desc'
  ) => {
    setSortField(field);
    if (direction) {
      setSortDirection(direction);
    } else {
      // Toggle direction if same field
      setSortDirection(prev =>
        sortField === field && prev === 'asc' ? 'desc' : 'asc'
      );
    }
  }, [sortField]);

  /**
   * Filter by status
   */
  const filterByStatus = useCallback((statuses: string[]) => {
    updateFilterOptions({ status: statuses });
  }, [updateFilterOptions]);

  /**
   * Filter by priority
   */
  const filterByPriority = useCallback((priorities: string[]) => {
    updateFilterOptions({ priority: priorities });
  }, [updateFilterOptions]);

  /**
   * Filter by assignees
   */
  const filterByAssignees = useCallback((assignees: string[]) => {
    updateFilterOptions({ assignees });
  }, [updateFilterOptions]);

  /**
   * Search by term (title and assignees)
   */
  const searchByTerm = useCallback((searchTerm: string) => {
    updateFilterOptions({ searchTerm: searchTerm.trim() || undefined });
  }, [updateFilterOptions]);

  /**
   * Get filter statistics
   */
  const filterStats = useMemo(() => {
    const totalCount = subtasks.length;
    const filteredCount = filteredSubtasks.length;
    const isFiltered = Object.keys(filterOptions).some(key =>
      filterOptions[key as keyof SubtaskFilterOptions] !== undefined
    );

    return {
      totalCount,
      filteredCount,
      isFiltered,
      hiddenCount: totalCount - filteredCount
    };
  }, [subtasks.length, filteredSubtasks.length, filterOptions]);

  /**
   * Get available filter values from current subtasks
   */
  const availableFilterValues = useMemo(() => {
    const statuses = [...new Set(subtasks.map(s => s.status))];
    const priorities = [...new Set(subtasks.map(s => s.priority))];
    const assignees = [...new Set(subtasks.flatMap(s => s.assignees || []))];

    return {
      statuses: statuses.sort(),
      priorities: priorities.sort(),
      assignees: assignees.sort()
    };
  }, [subtasks]);

  return {
    // Filtered results
    filteredSubtasks,

    // Filter state
    filterOptions,
    sortField,
    sortDirection,

    // Filter actions
    setFilterOptions: updateFilterOptions,
    clearFilters,
    updateSort,

    // Specific filter actions
    filterByStatus,
    filterByPriority,
    filterByAssignees,
    searchByTerm,

    // Metadata
    filterStats,
    availableFilterValues
  };
}