import React, { useState } from 'react';
import { Copy, FileText, Check } from 'lucide-react';
import { Button } from '../../ui/button';
import { copyToClipboard } from '../../../utils/idDisplayUtils';
import logger from '../../../utils/logger';

interface TaskCopyButtonsProps {
  taskId: string;
  taskName: string;
  size?: 'sm' | 'md';
  className?: string;
}

/**
 * Component for copying task ID and task name
 * Displays icon-only buttons with tooltips and visual feedback
 */
export const TaskCopyButtons: React.FC<TaskCopyButtonsProps> = ({
  taskId,
  taskName,
  size = 'sm',
  className = ''
}) => {
  const [copiedId, setCopiedId] = useState(false);
  const [copiedName, setCopiedName] = useState(false);

  const handleCopyId = async (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();

    const success = await copyToClipboard(taskId);
    if (success) {
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 2000);
      logger.debug('[TaskCopyButtons] Copied task ID:', taskId);
    } else {
      logger.error('[TaskCopyButtons] Failed to copy task ID');
    }
  };

  const handleCopyName = async (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();

    const success = await copyToClipboard(taskName);
    if (success) {
      setCopiedName(true);
      setTimeout(() => setCopiedName(false), 2000);
      logger.debug('[TaskCopyButtons] Copied task name:', taskName);
    } else {
      logger.error('[TaskCopyButtons] Failed to copy task name');
    }
  };

  const buttonSize = size === 'sm' ? 'h-6 w-6' : 'h-7 w-7';
  const iconSize = size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5';

  return (
    <div className={`inline-flex items-center gap-0.5 ${className}`}>
      {/* Copy ID Button */}
      <Button
        variant="ghost"
        size="icon"
        className={`${buttonSize} p-0 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors`}
        onClick={handleCopyId}
        title={copiedId ? 'ID Copied!' : 'Copy Task ID'}
      >
        {copiedId ? (
          <Check className={`${iconSize} text-green-600`} />
        ) : (
          <Copy className={`${iconSize} text-gray-500 dark:text-gray-400`} />
        )}
      </Button>

      {/* Copy Name Button */}
      <Button
        variant="ghost"
        size="icon"
        className={`${buttonSize} p-0 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors`}
        onClick={handleCopyName}
        title={copiedName ? 'Name Copied!' : 'Copy Task Name'}
      >
        {copiedName ? (
          <Check className={`${iconSize} text-green-600`} />
        ) : (
          <FileText className={`${iconSize} text-gray-500 dark:text-gray-400`} />
        )}
      </Button>
    </div>
  );
};