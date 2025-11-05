import { vi } from 'vitest';
import React from 'react';

// Mock implementation of ProgressDisplay component
// Used in tests to avoid rendering complex ProgressStepper and Tooltip components

interface ProgressDisplayProps {
  status?: string;
  progressPercentage?: number;
  progressState?: any;
  progressHistory?: string | object;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'compact';
  showLabels?: boolean;
  animate?: boolean;
  className?: string;
  maxTextLength?: number;
}

export function ProgressDisplay({
  status = 'todo',
  progressPercentage = 0,
  size = 'sm',
  variant = 'default',
  showLabels = true,
  className = "",
}: ProgressDisplayProps) {
  return (
    <div
      data-testid="progress-display"
      className={className}
      data-status={status}
      data-percentage={progressPercentage}
      data-size={size}
      data-variant={variant}
    >
      {showLabels && (
        <span data-testid="progress-label">
          {progressPercentage}% - {status}
        </span>
      )}
      <div
        data-testid="progress-bar"
        role="progressbar"
        aria-valuenow={progressPercentage}
        aria-valuemin={0}
        aria-valuemax={100}
        style={{ width: `${progressPercentage}%` }}
      />
    </div>
  );
}

// Mock the module
vi.mock('../../components/ui/ProgressDisplay', () => ({
  ProgressDisplay: vi.fn((props: ProgressDisplayProps) => {
    const status = props.status || 'todo';
    const progressPercentage = props.progressPercentage || 0;
    const showLabels = props.showLabels !== false;

    return (
      <div
        data-testid="progress-display"
        className={props.className}
        data-status={status}
        data-percentage={progressPercentage}
        data-size={props.size || 'sm'}
        data-variant={props.variant || 'default'}
      >
        {showLabels && (
          <span data-testid="progress-label">
            {progressPercentage}% - {status}
          </span>
        )}
        <div
          data-testid="progress-bar"
          role="progressbar"
          aria-valuenow={progressPercentage}
          aria-valuemin={0}
          aria-valuemax={100}
          style={{ width: `${progressPercentage}%` }}
        />
      </div>
    );
  })
}));

export default ProgressDisplay;
