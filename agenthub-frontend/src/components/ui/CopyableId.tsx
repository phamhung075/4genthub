// Reusable component for displaying IDs with copy functionality

import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import { Button } from './button';
import { Badge } from './badge';
import { abbreviateId, copyToClipboard } from '../../utils/idDisplayUtils';
import logger from '../../utils/logger';

interface CopyableIdProps {
  id: string;
  label?: string;
  abbreviated?: boolean;
  variant?: 'badge' | 'inline' | 'block';
  size?: 'xs' | 'sm' | 'md';
  className?: string;
  showCopyButton?: boolean;
}

/**
 * Component for displaying IDs with copy functionality
 * Supports different display variants and automatic abbreviation
 */
export const CopyableId: React.FC<CopyableIdProps> = ({
  id,
  label = '',
  abbreviated = true,
  variant = 'badge',
  size = 'xs',
  className = '',
  showCopyButton = true
}) => {
  const [copied, setCopied] = useState(false);

  const displayId = abbreviated ? abbreviateId(id) : id;
  const displayText = label ? `${label} ${displayId}` : displayId;

  const handleCopy = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    const success = await copyToClipboard(id);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      logger.debug('[CopyableId] Copied ID to clipboard:', id);
    } else {
      logger.error('[CopyableId] Failed to copy ID to clipboard:', id);
    }
  };

  const getTextSizeClass = () => {
    switch (size) {
      case 'xs': return 'text-xs';
      case 'sm': return 'text-sm';
      case 'md': return 'text-base';
      default: return 'text-xs';
    }
  };

  if (variant === 'badge') {
    return (
      <div className={`inline-flex items-center gap-1 ${className}`}>
        <Badge
          variant="outline"
          className={`${getTextSizeClass()} font-mono bg-gray-50 dark:bg-gray-800/50 border-gray-300 dark:border-gray-600 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors`}
          onClick={handleCopy}
          title={abbreviated ? `Full ID: ${id} (Click to copy)` : 'Click to copy'}
        >
          {displayText}
        </Badge>
        {showCopyButton && (
          <Button
            variant="ghost"
            size="sm"
            className="h-5 w-5 p-0 hover:bg-gray-100 dark:hover:bg-gray-700"
            onClick={handleCopy}
            title={copied ? 'Copied!' : 'Copy full ID'}
          >
            {copied ? (
              <Check className="w-3 h-3 text-green-600" />
            ) : (
              <Copy className="w-3 h-3 text-gray-500" />
            )}
          </Button>
        )}
      </div>
    );
  }

  if (variant === 'inline') {
    return (
      <span
        className={`inline-flex items-center gap-1 font-mono ${getTextSizeClass()} text-gray-600 dark:text-gray-400 cursor-pointer hover:text-gray-800 dark:hover:text-gray-200 transition-colors ${className}`}
        onClick={handleCopy}
        title={abbreviated ? `Full ID: ${id} (Click to copy)` : 'Click to copy'}
      >
        {displayText}
        {showCopyButton && (
          copied ? (
            <Check className="w-3 h-3 text-green-600 ml-1" />
          ) : (
            <Copy className="w-3 h-3 text-gray-400 ml-1" />
          )
        )}
      </span>
    );
  }

  // Block variant
  return (
    <div
      className={`flex items-center gap-2 p-2 rounded bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors ${className}`}
      onClick={handleCopy}
      title={abbreviated ? `Full ID: ${id} (Click to copy)` : 'Click to copy'}
    >
      <span className={`font-mono ${getTextSizeClass()} text-gray-700 dark:text-gray-300 flex-1`}>
        {displayText}
      </span>
      {showCopyButton && (
        <Button
          variant="ghost"
          size="sm"
          className="h-6 w-6 p-0"
          onClick={handleCopy}
          title={copied ? 'Copied!' : 'Copy full ID'}
        >
          {copied ? (
            <Check className="w-3 h-3 text-green-600" />
          ) : (
            <Copy className="w-3 h-3 text-gray-500" />
          )}
        </Button>
      )}
    </div>
  );
};