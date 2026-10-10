import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Clock, MessageSquare } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from './ui/collapsible';
import { parseProgressHistory, formatProgressEntryForDisplay } from '../utils/progressHistoryUtils';
import type { ProgressHistoryObject } from '../types/utilityTypes';

interface ProgressHistoryTimelineProps {
  progressHistory?: string | ProgressHistoryObject;
  progressCount?: number;
  variant?: 'full' | 'compact' | 'summary';
  maxHeight?: string;
  className?: string;
}

/**
 * Component to display progress history in a timeline format
 */
export const ProgressHistoryTimeline: React.FC<ProgressHistoryTimelineProps> = ({
  progressHistory,
  progressCount,
  variant = 'full',
  maxHeight = 'max-h-96',
  className = ''
}) => {
  const [isExpanded, setIsExpanded] = useState(variant === 'full');
  const entries = parseProgressHistory(progressHistory);

  // If no progress history, return null
  if (!entries.length) {
    return null;
  }

  // 4a0a8c7a stopped serving progress_count, and the count that is true to what is rendered is
  // how many entries the SERVED text parses into. Callers may still pass one explicitly.
  const displayCount = progressCount ?? entries.length;

  // Summary variant - just show count and latest
  if (variant === 'summary') {
    const latestEntry = entries[entries.length - 1];
    const summary = latestEntry.content.split('\n')[0];
    const truncatedSummary = summary.length > 80 ? summary.substring(0, 77) + '...' : summary;

    return (
      <div className={`text-sm text-muted-foreground ${className}`}>
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4" />
          <span>{displayCount} progress {displayCount === 1 ? 'entry' : 'entries'}</span>
          {truncatedSummary && (
            <>
              <span>·</span>
              <span className="italic">{truncatedSummary}</span>
            </>
          )}
        </div>
      </div>
    );
  }

  // Compact variant - collapsible with header
  if (variant === 'compact') {
    return (
      <div className={className}>
        <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
          <CollapsibleTrigger asChild>
            <Button
              variant="ghost"
              className="flex w-full justify-between p-0 h-auto font-normal"
            >
              <div className="flex items-center gap-2 text-sm">
                <Clock className="w-4 h-4" />
                <span>Progress History</span>
                <Badge variant="secondary" className="text-xs">
                  {displayCount}
                </Badge>
              </div>
              {isExpanded ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-3">
            <ProgressTimelineContent entries={entries} maxHeight={maxHeight} />
          </CollapsibleContent>
        </Collapsible>
      </div>
    );
  }

  // Full variant - always expanded
  return (
    <div className={className}>
      <div className="flex items-center gap-2 mb-3">
        <Clock className="w-4 h-4" />
        <h4 className="font-semibold text-sm">Progress History</h4>
        <Badge variant="secondary" className="text-xs">
          {displayCount} {displayCount === 1 ? 'entry' : 'entries'}
        </Badge>
      </div>
      <ProgressTimelineContent entries={entries} maxHeight={maxHeight} />
    </div>
  );
};

/**
 * Internal component for rendering the timeline content
 */
const ProgressTimelineContent: React.FC<{
  entries: ReturnType<typeof parseProgressHistory>;
  maxHeight: string;
}> = ({ entries, maxHeight }) => {
  return (
    <div className={`${maxHeight} overflow-y-auto space-y-3`}>
      {entries.map((entry, index) => {
        const formattedEntry = formatProgressEntryForDisplay(entry, index);

        return (
          <div
            key={entry.number}
            className={`
              p-3 rounded-md transition-colors duration-200
              ${formattedEntry.cssClasses}
              ${formattedEntry.borderClasses}
              pl-4
            `}
          >
            {/* Progress Entry Header */}
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="outline" className="text-xs font-mono">
                Progress {entry.number}
              </Badge>
              {entry.timestamp && (
                <span className="text-xs text-muted-foreground">
                  {entry.timestamp}
                </span>
              )}
            </div>

            {/* Progress Entry Content */}
            <div className="text-sm leading-relaxed whitespace-pre-wrap">
              {entry.content}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default ProgressHistoryTimeline;
