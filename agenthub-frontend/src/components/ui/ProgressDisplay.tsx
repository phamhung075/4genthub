import React from "react";
import { ProgressStepper, getProgressStateFromTask, type ProgressState } from "./progress-stepper";
import { getProgressSummary, cleanProgressText, getLatestProgress } from "../../utils/progressHistoryUtils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "./tooltip";
import { cn } from "../../lib/utils";

interface ProgressDisplayProps {
  status?: string;
  progressPercentage?: number;
  progressState?: ProgressState;
  progressHistory?: string | object;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'compact';
  showLabels?: boolean;
  animate?: boolean;
  className?: string;
  maxTextLength?: number;
}

export function ProgressDisplay({
  status,
  progressPercentage,
  progressState,
  progressHistory,
  size = 'sm',
  variant = 'compact',
  showLabels = false,
  animate = true,
  className,
  maxTextLength = 80
}: ProgressDisplayProps) {
  const currentState = getProgressStateFromTask(status, progressPercentage, progressState);
  const progressSummary = getProgressSummary(progressHistory, maxTextLength);

  // Get full progress text for tooltip
  const fullProgressText = React.useMemo(() => {
    const latestProgress = getLatestProgress(progressHistory);
    if (!latestProgress) return '';
    return cleanProgressText(latestProgress);
  }, [progressHistory]);

  const hasProgressText = progressSummary && progressSummary.trim() !== '';
  const hasFullText = fullProgressText && fullProgressText.trim() !== '';

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div>
              <ProgressStepper
                currentState={currentState}
                size={size}
                variant={variant}
                showLabels={showLabels}
                animate={animate}
              />
            </div>
          </TooltipTrigger>
          {hasFullText && (
            <TooltipContent side="top" className="max-w-sm">
              <div className="space-y-2">
                <div className="font-medium text-sm">
                  Progress Status: {currentState.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </div>
                {progressPercentage !== undefined && (
                  <div className="text-xs text-muted-foreground">
                    {progressPercentage}% complete
                  </div>
                )}
                <div className="text-xs whitespace-pre-wrap">
                  {fullProgressText.length > 200
                    ? fullProgressText.substring(0, 200) + '...'
                    : fullProgressText
                  }
                </div>
              </div>
            </TooltipContent>
          )}
        </Tooltip>
      </TooltipProvider>

      {hasProgressText && (
        <div className="text-xs text-muted-foreground italic flex-1 truncate">
          {progressSummary}
        </div>
      )}
    </div>
  );
}

// Enhanced version with more visual elements
interface ProgressDisplayEnhancedProps extends ProgressDisplayProps {
  showPercentage?: boolean;
  compactLayout?: boolean;
}

export function ProgressDisplayEnhanced({
  status,
  progressPercentage,
  progressState,
  progressHistory,
  size = 'sm',
  variant = 'compact',
  showLabels = false,
  animate = true,
  className,
  maxTextLength = 60,
  showPercentage = false,
  compactLayout = true
}: ProgressDisplayEnhancedProps) {
  const currentState = getProgressStateFromTask(status, progressPercentage, progressState);
  const progressSummary = getProgressSummary(progressHistory, maxTextLength);

  // Get full progress text for tooltip
  const fullProgressText = React.useMemo(() => {
    const latestProgress = getLatestProgress(progressHistory);
    if (!latestProgress) return '';
    return cleanProgressText(latestProgress);
  }, [progressHistory]);

  const hasProgressText = progressSummary && progressSummary.trim() !== '';
  const hasFullText = fullProgressText && fullProgressText.trim() !== '';

  if (compactLayout) {
    return (
      <div className={cn("flex items-center gap-2", className)}>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-1.5">
                <ProgressStepper
                  currentState={currentState}
                  size={size}
                  variant={variant}
                  showLabels={false}
                  animate={animate}
                />
                {showPercentage && progressPercentage !== undefined && (
                  <span className="text-xs font-mono text-muted-foreground">
                    {progressPercentage}%
                  </span>
                )}
              </div>
            </TooltipTrigger>
            {hasFullText && (
              <TooltipContent side="top" className="max-w-sm">
                <div className="space-y-2">
                  <div className="font-medium text-sm">
                    {currentState.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </div>
                  {progressPercentage !== undefined && (
                    <div className="text-xs text-muted-foreground">
                      {progressPercentage}% complete
                    </div>
                  )}
                  <div className="text-xs whitespace-pre-wrap">
                    {fullProgressText.length > 300
                      ? fullProgressText.substring(0, 300) + '...'
                      : fullProgressText
                    }
                  </div>
                </div>
              </TooltipContent>
            )}
          </Tooltip>
        </TooltipProvider>

        {hasProgressText && (
          <div className="text-xs text-muted-foreground italic flex-1 truncate">
            {progressSummary}
          </div>
        )}
      </div>
    );
  }

  // Full layout
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <div className="flex items-center gap-2">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div>
                <ProgressStepper
                  currentState={currentState}
                  size={size}
                  variant={variant}
                  showLabels={showLabels}
                  animate={animate}
                />
              </div>
            </TooltipTrigger>
            {hasFullText && (
              <TooltipContent side="top" className="max-w-sm">
                <div className="space-y-2">
                  <div className="font-medium text-sm">
                    Progress Status: {currentState.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </div>
                  {progressPercentage !== undefined && (
                    <div className="text-xs text-muted-foreground">
                      {progressPercentage}% complete
                    </div>
                  )}
                  <div className="text-xs whitespace-pre-wrap">
                    {fullProgressText}
                  </div>
                </div>
              </TooltipContent>
            )}
          </Tooltip>
        </TooltipProvider>

        {showPercentage && progressPercentage !== undefined && (
          <span className="text-xs font-mono text-muted-foreground">
            {progressPercentage}%
          </span>
        )}
      </div>

      {hasProgressText && (
        <div className="text-xs text-muted-foreground italic">
          {progressSummary}
        </div>
      )}
    </div>
  );
}