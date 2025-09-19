"use client"
import { AlertCircle, CheckCircle, Clock, Layers, ListTodo, Search as SearchIcon, X } from 'lucide-react';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { listSubtasks, listTasks, searchTasks, Subtask, Task } from '../api';
import logger from '../utils/logger';
import { debounce } from '../lib/utils';
import { Badge } from './ui/badge';

// --- SVG ICONS ---
const CommandIcon = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-gray-500 dark:text-gray-400">
        <path d="M18 3a3 3 0 0 0-3 3v12a3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0-3-3H6a3 3 0 0 0-3 3 3 3 0 0 0 3 3 3 3 0 0 0 3-3V6a3 3 0 0 0-3-3 3 3 0 0 0-3 3 3 3 0 0 0 3 3h12a3 3 0 0 0 3-3 3 3 0 0 0-3-3z" />
    </svg>
);

interface TaskSearchProps {
  projectId: string;
  taskTreeId: string;
  onTaskSelect?: (task: Task) => void;
  onSubtaskSelect?: (subtask: Subtask, parentTask: Task) => void;
}

interface SearchResult {
  tasks: Task[];
  subtasksWithParent: Array<{
    subtask: Subtask;
    parentTask: Task;
  }>;
}

// --- UTILITY FUNCTIONS ---
const getStatusIcon = (status: string) => {
  switch (status) {
    case 'done':
      return <CheckCircle className="w-4 h-4 text-green-500" />;
    case 'in_progress':
      return <Clock className="w-4 h-4 text-blue-500" />;
    case 'blocked':
      return <AlertCircle className="w-4 h-4 text-red-500" />;
    default:
      return <ListTodo className="w-4 h-4 text-gray-500" />;
  }
};

const getStatusColor = (status: string) => {
  switch (status) {
    case 'done':
      return '#10B981';
    case 'in_progress':
      return '#3B82F6';
    case 'blocked':
      return '#EF4444';
    default:
      return '#6B7280';
  }
};

const getPriorityColor = (priority: string) => {
  switch (priority) {
    case 'urgent':
      return '#DC2626';
    case 'high':
      return '#F59E0B';
    case 'medium':
      return '#3B82F6';
    default:
      return '#6B7280';
  }
};

export const TaskSearch: React.FC<TaskSearchProps> = ({
  projectId: _projectId, // Currently unused but kept for compatibility
  taskTreeId,
  onTaskSelect,
  onSubtaskSelect
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchResult>({
    tasks: [],
    subtasksWithParent: []
  });
  const [showResults, setShowResults] = useState(false);
  const [recentSearches, setRecentSearches] = useState<Array<Task | { subtask: Subtask; parentTask: Task }>>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  // Load recent searches from localStorage
  useEffect(() => {
    const stored = localStorage.getItem('recentTaskSearches_' + taskTreeId);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        setRecentSearches(parsed.slice(0, 5));
      } catch (e) {
        logger.error('Failed to load recent searches from localStorage', { error: e, taskTreeId, component: 'TaskSearch' });
      }
    }
  }, [taskTreeId]);

  // Search function
  const performSearch = useCallback(async (query: string) => {
    if (!query.trim()) {
      setSearchResults({ tasks: [], subtasksWithParent: [] });
      setShowResults(false);
      return;
    }

    setIsSearching(true);
    setShowResults(true);

    try {
      // Search tasks using the search API
      const taskResults = await searchTasks(query, { git_branch_id: taskTreeId });
      
      // For subtasks, we need to get all tasks and then search through their subtasks
      const allTasks = await listTasks({ git_branch_id: taskTreeId });
      const subtaskResults: SearchResult['subtasksWithParent'] = [];
      
      // Search through all tasks' subtasks
      for (const task of allTasks) {
        if (task.subtasks && task.subtasks.length > 0) {
          try {
            const subtasks = await listSubtasks(task.id);
            const matchingSubtasks = subtasks.filter(subtask => {
              const queryLower = query.toLowerCase();
              return (
                subtask.title.toLowerCase().includes(queryLower) ||
                subtask.id.toLowerCase().includes(queryLower) ||
                (subtask.description && subtask.description.toLowerCase().includes(queryLower))
              );
            });
            
            matchingSubtasks.forEach(subtask => {
              subtaskResults.push({ subtask, parentTask: task });
            });
          } catch (error) {
            logger.error('Failed to fetch subtasks for task', { error, taskId: task.id, component: 'TaskSearch' });
          }
        }
      }
      
      setSearchResults({
        tasks: taskResults,
        subtasksWithParent: subtaskResults
      });
    } catch (error) {
      logger.error('Task search operation failed', { error, query, taskTreeId, component: 'TaskSearch' });
      setSearchResults({ tasks: [], subtasksWithParent: [] });
    } finally {
      setIsSearching(false);
    }
  }, [taskTreeId]);

  // Debounced search
  const debouncedSearch = useMemo(
    () => debounce((query: string) => performSearch(query), 300),
    [performSearch]
  );

  // Handle input change
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const query = e.target.value;
    setSearchQuery(query);
    if (query.trim()) {
      debouncedSearch(query);
    } else {
      setShowResults(false);
    }
  };

  // Clear search
  const clearSearch = () => {
    setSearchQuery('');
    setSearchResults({ tasks: [], subtasksWithParent: [] });
    setShowResults(false);
  };

  // Clear recent searches
  const clearRecentSearches = () => {
    setRecentSearches([]);
    localStorage.removeItem('recentTaskSearches_' + taskTreeId);
  };

  // Add to recent searches
  const addToRecentSearches = (item: Task | { subtask: Subtask; parentTask: Task }) => {
    const updated = [item, ...recentSearches.filter(i => {
      if ('subtask' in i && 'subtask' in item) {
        return i.subtask.id !== item.subtask.id;
      }
      if (!('subtask' in i) && !('subtask' in item)) {
        return (i as Task).id !== (item as Task).id;
      }
      return true;
    })].slice(0, 5);
    
    setRecentSearches(updated);
    localStorage.setItem('recentTaskSearches_' + taskTreeId, JSON.stringify(updated));
  };

  // Handle task selection
  const handleTaskClick = (task: Task) => {
    addToRecentSearches(task);
    if (onTaskSelect) {
      onTaskSelect(task);
    }
    clearSearch();
  };

  // Handle subtask selection
  const handleSubtaskClick = (subtask: Subtask, parentTask: Task) => {
    addToRecentSearches({ subtask, parentTask });
    if (onSubtaskSelect) {
      onSubtaskSelect(subtask, parentTask);
    }
    clearSearch();
  };

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl/Cmd + K to focus search
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
        setShowResults(true);
      }
      
      // Escape to clear search
      if (e.key === 'Escape' && showResults) {
        clearSearch();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showResults]);

  const totalResults = searchResults.tasks.length + searchResults.subtasksWithParent.length;

  return (
    <div className="w-full">
      <div className="relative flex items-center justify-center font-sans w-full">
        
        {/* Search Modal */}
        <div className="w-full space-y-6 bg-white/30 dark:bg-black/30 backdrop-blur-3xl border border-black/10 dark:border-white/5 rounded-3xl shadow-lg dark:shadow-2xl dark:shadow-purple-500/15 p-4">
          
          {/* Search Input with Enhanced Gradient Border and Glow */}
          <div className="relative p-px rounded-2xl bg-gradient-to-r from-orange-500 via-purple-600 to-pink-600 shadow-lg shadow-purple-500/20 dark:shadow-purple-600/30 transition-shadow duration-300 hover:shadow-purple-500/40 dark:hover:shadow-purple-600/50 focus-within:shadow-purple-500/40 dark:focus-within:shadow-purple-600/50">
              <div className="flex items-center w-full px-4 py-2 bg-white/80 dark:bg-gray-900/90 rounded-[15px]">
                  <SearchIcon className="w-5 h-5 text-gray-500 dark:text-gray-400 flex-shrink-0" />
                  <input
                      ref={inputRef}
                      type="text"
                      placeholder="Search tasks and subtasks by ID or name..."
                      value={searchQuery}
                      onChange={handleInputChange}
                      onFocus={() => {
                        if (!searchQuery && recentSearches.length > 0) {
                          setShowResults(true);
                        }
                      }}
                      className="w-full px-3 py-1 text-lg text-gray-800 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500 bg-transparent focus:outline-none flex-1 min-w-0"
                  />
                  <div className="flex items-center gap-2 flex-shrink-0">
                      {searchQuery && (
                        <button
                          onClick={clearSearch}
                          className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
                        >
                          <X className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                        </button>
                      )}
                      <div className="flex items-center justify-center p-1.5 bg-gray-200 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-md shadow-inner">
                          <CommandIcon />
                      </div>
                      <div className="flex items-center justify-center w-6 h-6 p-1 bg-gray-200 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-md shadow-inner">
                          <span className="text-sm font-semibold text-gray-600 dark:text-gray-300">K</span>
                      </div>
                  </div>
              </div>
          </div>

          {/* Results or Recent Searches */}
          {showResults && (
            <div className="px-2 space-y-4">
              {isSearching ? (
                <div className="text-center py-4">
                  <div className="inline-block w-6 h-6 border-2 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
                  <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Searching...</p>
                </div>
              ) : searchQuery ? (
                <>
                  {/* Search Results */}
                  {totalResults === 0 ? (
                    <p className="text-center text-gray-400 dark:text-gray-500 py-4">
                      No results found for &quot;{searchQuery}&quot;
                    </p>
                  ) : (
                    <>
                      {/* Tasks Section */}
                      {searchResults.tasks.length > 0 && (
                        <div className="space-y-2">
                          <h2 className="text-xs font-semibold tracking-wider text-gray-500 dark:text-gray-400 uppercase">
                            Tasks ({searchResults.tasks.length})
                          </h2>
                          <ul className="space-y-2">
                            {searchResults.tasks.map(task => (
                              <li
                                key={task.id}
                                onClick={() => handleTaskClick(task)}
                                className="flex items-center justify-between p-3 transition-all duration-300 ease-in-out bg-black/5 dark:bg-gray-500/10 hover:bg-black/10 dark:hover:bg-gray-500/20 rounded-xl hover:scale-[1.02] cursor-pointer"
                              >
                                <div className="flex items-center gap-4">
                                  {getStatusIcon(task.status)}
                                  <div className="flex flex-col">
                                    <span className="text-gray-700 dark:text-gray-200 font-medium">{task.title}</span>
                                    <span className="text-xs text-gray-500 dark:text-gray-400">ID: {task.id.substring(0, 8)}...</span>
                                  </div>
                                </div>
                                <div className="flex items-center gap-3">
                                  <span 
                                    className="px-2 py-0.5 rounded-full text-xs font-medium text-white"
                                    style={{ backgroundColor: getPriorityColor(task.priority) }}
                                  >
                                    {task.priority}
                                  </span>
                                  <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                                    <span 
                                      style={{ 
                                        backgroundColor: getStatusColor(task.status), 
                                        boxShadow: `0 0 8px ${getStatusColor(task.status)}` 
                                      }} 
                                      className="w-2 h-2 rounded-full"
                                    />
                                    <span className="text-xs">{task.status.replace('_', ' ')}</span>
                                  </div>
                                </div>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Subtasks Section */}
                      {searchResults.subtasksWithParent.length > 0 && (
                        <div className="space-y-2">
                          <h2 className="text-xs font-semibold tracking-wider text-gray-500 dark:text-gray-400 uppercase">
                            Subtasks ({searchResults.subtasksWithParent.length})
                          </h2>
                          <ul className="space-y-2">
                            {searchResults.subtasksWithParent.map(({ subtask, parentTask }) => (
                              <li
                                key={`${parentTask.id}-${subtask.id}`}
                                onClick={() => handleSubtaskClick(subtask, parentTask)}
                                className="flex items-center justify-between p-3 transition-all duration-300 ease-in-out bg-black/5 dark:bg-gray-500/10 hover:bg-black/10 dark:hover:bg-gray-500/20 rounded-xl hover:scale-[1.02] cursor-pointer"
                              >
                                <div className="flex items-center gap-4">
                                  <Layers className="w-4 h-4 text-purple-500" />
                                  <div className="flex flex-col">
                                    <span className="text-gray-700 dark:text-gray-200 font-medium">{subtask.title}</span>
                                    <span className="text-xs text-gray-500 dark:text-gray-400">
                                      Parent: {parentTask.title}
                                    </span>
                                  </div>
                                </div>
                                <div className="flex items-center gap-3">
                                  <span 
                                    className="px-2 py-0.5 rounded-full text-xs font-medium text-white"
                                    style={{ backgroundColor: getPriorityColor(subtask.priority) }}
                                  >
                                    {subtask.priority}
                                  </span>
                                  <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                                    <span 
                                      style={{ 
                                        backgroundColor: getStatusColor(subtask.status), 
                                        boxShadow: `0 0 8px ${getStatusColor(subtask.status)}` 
                                      }} 
                                      className="w-2 h-2 rounded-full"
                                    />
                                    <span className="text-xs">{subtask.status.replace('_', ' ')}</span>
                                  </div>
                                </div>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </>
                  )}
                </>
              ) : (
                <>
                  {/* Recent Searches */}
                  {recentSearches.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <h2 className="text-xs font-semibold tracking-wider text-gray-500 dark:text-gray-400 uppercase">
                          Recent searches
                        </h2>
                        <button
                          onClick={clearRecentSearches}
                          className="px-3 py-1 text-sm text-gray-500 dark:text-gray-400 transition-colors duration-200 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700/50 hover:text-black dark:hover:text-white"
                        >
                          Clear all
                        </button>
                      </div>
                      <ul className="space-y-2">
                        {recentSearches.map((item, index) => {
                          if ('subtask' in item) {
                            const { subtask, parentTask } = item;
                            return (
                              <li
                                key={`recent-${index}`}
                                onClick={() => handleSubtaskClick(subtask, parentTask)}
                                className="flex items-center justify-between p-3 transition-all duration-300 ease-in-out bg-black/5 dark:bg-gray-500/10 hover:bg-black/10 dark:hover:bg-gray-500/20 rounded-xl hover:scale-[1.02] cursor-pointer"
                              >
                                <div className="flex items-center gap-4">
                                  <Layers className="w-4 h-4 text-purple-500" />
                                  <div className="flex flex-col">
                                    <span className="text-gray-700 dark:text-gray-200 font-medium">{subtask.title}</span>
                                    <span className="text-xs text-gray-500 dark:text-gray-400">
                                      Parent: {parentTask.title}
                                    </span>
                                  </div>
                                </div>
                                <Badge variant="outline" className="text-xs">Recent</Badge>
                              </li>
                            );
                          } else {
                            const task = item as Task;
                            return (
                              <li
                                key={`recent-${index}`}
                                onClick={() => handleTaskClick(task)}
                                className="flex items-center justify-between p-3 transition-all duration-300 ease-in-out bg-black/5 dark:bg-gray-500/10 hover:bg-black/10 dark:hover:bg-gray-500/20 rounded-xl hover:scale-[1.02] cursor-pointer"
                              >
                                <div className="flex items-center gap-4">
                                  {getStatusIcon(task.status)}
                                  <span className="text-gray-700 dark:text-gray-200 font-medium">{task.title}</span>
                                </div>
                                <Badge variant="outline" className="text-xs">Recent</Badge>
                              </li>
                            );
                          }
                        })}
                      </ul>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TaskSearch;