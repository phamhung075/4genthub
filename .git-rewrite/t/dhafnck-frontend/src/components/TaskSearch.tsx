import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Search, X } from 'lucide-react';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Card } from './ui/card';
import { debounce } from '../lib/utils';
import { searchTasks, listTasks, listSubtasks, Task, Subtask } from '../api';

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

export const TaskSearch: React.FC<TaskSearchProps> = ({
  projectId,
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
      const taskResults = await searchTasks(query, taskTreeId);
      
      // For subtasks, we need to get all tasks and then search through their subtasks
      // This is because subtasks don't have a direct search API
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
            console.error(`Error fetching subtasks for task ${task.id}:`, error);
          }
        }
      }
      
      setSearchResults({
        tasks: taskResults,
        subtasksWithParent: subtaskResults
      });
    } catch (error) {
      console.error('Search error:', error);
      setSearchResults({ tasks: [], subtasksWithParent: [] });
    } finally {
      setIsSearching(false);
    }
  }, [taskTreeId]);

  // Debounced search - using useMemo to properly handle the debounced function
  const debouncedSearch = useMemo(
    () => debounce((query: string) => performSearch(query), 300),
    [performSearch]
  );

  // Handle input change
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const query = e.target.value;
    setSearchQuery(query);
    debouncedSearch(query);
  };

  // Clear search
  const clearSearch = () => {
    setSearchQuery('');
    setSearchResults({ tasks: [], subtasksWithParent: [] });
    setShowResults(false);
  };

  // Handle task selection
  const handleTaskClick = (task: Task) => {
    if (onTaskSelect) {
      onTaskSelect(task);
    }
    clearSearch();
  };

  // Handle subtask selection
  const handleSubtaskClick = (subtask: Subtask, parentTask: Task) => {
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
        const searchInput = document.getElementById('task-search-input');
        searchInput?.focus();
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
    <div className="relative">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
        <Input
          id="task-search-input"
          type="text"
          placeholder="Search tasks and subtasks by ID or name... (Ctrl+K)"
          value={searchQuery}
          onChange={handleInputChange}
          className="pl-10 pr-10"
        />
        {searchQuery && (
          <Button
            variant="ghost"
            size="icon"
            className="absolute right-1 top-1/2 transform -translate-y-1/2 h-7 w-7"
            onClick={clearSearch}
          >
            <X className="w-4 h-4" />
          </Button>
        )}
      </div>

      {showResults && (
        <Card className="absolute top-full mt-2 w-full max-h-96 overflow-y-auto z-50 shadow-lg">
          {isSearching ? (
            <div className="p-4 text-center text-sm text-gray-500">
              Searching...
            </div>
          ) : totalResults === 0 ? (
            <div className="p-4 text-center text-sm text-gray-500">
              No results found for "{searchQuery}"
            </div>
          ) : (
            <div className="p-2">
              {/* Tasks Section */}
              {searchResults.tasks.length > 0 && (
                <div className="mb-3">
                  <h3 className="text-xs font-semibold text-gray-500 uppercase px-2 mb-2">
                    Tasks ({searchResults.tasks.length})
                  </h3>
                  {searchResults.tasks.map(task => (
                    <div
                      key={task.id}
                      className="px-2 py-2 hover:bg-gray-100 cursor-pointer rounded-md transition-colors"
                      onClick={() => handleTaskClick(task)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{task.title}</p>
                          <p className="text-xs text-gray-500 truncate">ID: {task.id}</p>
                        </div>
                        <div className="flex gap-1 ml-2">
                          <Badge variant="outline" className="text-xs">{task.status}</Badge>
                          <Badge variant="secondary" className="text-xs">{task.priority}</Badge>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Subtasks Section */}
              {searchResults.subtasksWithParent.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-gray-500 uppercase px-2 mb-2">
                    Subtasks ({searchResults.subtasksWithParent.length})
                  </h3>
                  {searchResults.subtasksWithParent.map(({ subtask, parentTask }) => (
                    <div
                      key={`${parentTask.id}-${subtask.id}`}
                      className="px-2 py-2 hover:bg-gray-100 cursor-pointer rounded-md transition-colors"
                      onClick={() => handleSubtaskClick(subtask, parentTask)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{subtask.title}</p>
                          <p className="text-xs text-gray-500">
                            Parent: {parentTask.title}
                          </p>
                          <p className="text-xs text-gray-400 truncate">ID: {subtask.id}</p>
                        </div>
                        <div className="flex gap-1 ml-2">
                          <Badge variant="outline" className="text-xs">{subtask.status}</Badge>
                          <Badge variant="secondary" className="text-xs">{subtask.priority}</Badge>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </Card>
      )}
    </div>
  );
};

export default TaskSearch;