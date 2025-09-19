// Component for displaying parent task reference information

import React from 'react';
import { Badge } from './badge';
import { CopyableId } from './CopyableId';
import { useParentTaskInfo } from '../../hooks/useParentTaskInfo';
import { Link } from 'lucide-react';

interface ParentTaskReferenceProps {
  parentTaskId: string;
  variant?: 'inline' | 'block' | 'badge';
  showId?: boolean;
  className?: string;
}

/**
 * Component for displaying parent task information
 * Shows parent task title and optionally the ID
 */
export const ParentTaskReference: React.FC<ParentTaskReferenceProps> = ({
  parentTaskId,
  variant = 'inline',
  showId = false,
  className = ''
}) => {
  const { parentTaskInfo, loading, error } = useParentTaskInfo(parentTaskId);

  if (loading) {
    return (
      <div className={`inline-flex items-center gap-1 text-xs text-gray-500 ${className}`}>
        <Link className="w-3 h-3" />
        <span>Loading parent task...</span>
      </div>
    );
  }

  if (error || !parentTaskInfo) {
    return (
      <div className={`inline-flex items-center gap-1 text-xs text-gray-500 ${className}`}>
        <Link className="w-3 h-3" />
        <span>Parent: Unknown</span>
        {showId && (
          <CopyableId
            id={parentTaskId}
            variant="inline"
            size="xs"
            label=""
            abbreviated={true}
            showCopyButton={false}
          />
        )}
      </div>
    );
  }

  if (variant === 'badge') {
    return (
      <div className={`inline-flex items-center gap-1 ${className}`}>
        <Badge variant="outline" className="text-xs bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-700">
          <Link className="w-3 h-3 mr-1" />
          Parent: {parentTaskInfo.title}
        </Badge>
        {showId && (
          <CopyableId
            id={parentTaskInfo.id}
            variant="badge"
            size="xs"
            label=""
            abbreviated={true}
            showCopyButton={false}
          />
        )}
      </div>
    );
  }

  if (variant === 'block') {
    return (
      <div className={`p-2 rounded bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 ${className}`}>
        <div className="flex items-center gap-2">
          <Link className="w-4 h-4 text-blue-600 dark:text-blue-400" />
          <div className="flex-1">
            <div className="text-sm font-medium text-blue-800 dark:text-blue-200">
              Parent Task: {parentTaskInfo.title}
            </div>
            {showId && (
              <div className="mt-1">
                <CopyableId
                  id={parentTaskInfo.id}
                  variant="inline"
                  size="xs"
                  label="ID:"
                  abbreviated={true}
                  showCopyButton={true}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Inline variant (default)
  return (
    <div className={`inline-flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400 ${className}`}>
      <Link className="w-3 h-3" />
      <span>Parent: {parentTaskInfo.title}</span>
      {showId && (
        <CopyableId
          id={parentTaskInfo.id}
          variant="inline"
          size="xs"
          label=""
          abbreviated={true}
          showCopyButton={false}
          className="ml-1"
        />
      )}
    </div>
  );
};