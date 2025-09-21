import React from "react";
import { Circle, Timer, CheckCircle2 } from "lucide-react";
import { cn } from "../../lib/utils";

export type ProgressState = 'initial' | 'in_progress' | 'complete';

interface ProgressStepperProps {
  currentState: ProgressState;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  showLabels?: boolean;
  variant?: 'default' | 'compact';
  animate?: boolean;
}

interface StepConfig {
  state: ProgressState;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  iconFallback: string; // Fallback for accessibility
}

const STEPS: StepConfig[] = [
  { state: 'initial', label: 'To Do', icon: Circle, iconFallback: '○' },
  { state: 'in_progress', label: 'In Progress', icon: Timer, iconFallback: '◐' },
  { state: 'complete', label: 'Complete', icon: CheckCircle2, iconFallback: '●' }
];

export function ProgressStepper({
  currentState,
  size = 'md',
  className,
  showLabels = false,
  variant = 'default',
  animate = true
}: ProgressStepperProps) {
  const getCurrentStepIndex = (state: ProgressState): number => {
    return STEPS.findIndex(step => step.state === state);
  };

  const currentStepIndex = getCurrentStepIndex(currentState);

  const getSizeClasses = () => {
    switch (size) {
      case 'sm':
        return {
          step: 'w-5 h-5',
          icon: 'w-3 h-3',
          connector: 'h-0.5 flex-1 mx-1',
          container: 'text-xs',
          label: 'text-xs mt-1'
        };
      case 'lg':
        return {
          step: 'w-10 h-10',
          icon: 'w-6 h-6',
          connector: 'h-1 flex-1 mx-2',
          container: 'text-lg',
          label: 'text-sm mt-2'
        };
      default: // md
        return {
          step: 'w-7 h-7',
          icon: 'w-4 h-4',
          connector: 'h-0.5 flex-1 mx-1.5',
          container: 'text-sm',
          label: 'text-xs mt-1'
        };
    }
  };

  const sizes = getSizeClasses();

  const getStepColor = (stepIndex: number) => {
    if (stepIndex < currentStepIndex) {
      return {
        wrapper: 'text-emerald-600 bg-emerald-50 border-emerald-200 shadow-sm shadow-emerald-100 dark:text-emerald-400 dark:bg-emerald-900/20 dark:border-emerald-700',
        text: 'text-emerald-600 dark:text-emerald-400'
      };
    } else if (stepIndex === currentStepIndex) {
      const baseClasses = animate ? 'animate-pulse' : '';
      return {
        wrapper: `text-blue-600 bg-blue-50 border-blue-200 shadow-sm shadow-blue-100 dark:text-blue-400 dark:bg-blue-900/20 dark:border-blue-700 ${baseClasses}`,
        text: 'text-blue-600 dark:text-blue-400'
      };
    } else {
      return {
        wrapper: 'text-gray-400 bg-gray-50 border-gray-200 dark:text-gray-500 dark:bg-gray-800 dark:border-gray-700',
        text: 'text-gray-400 dark:text-gray-500'
      };
    }
  };

  const getConnectorColor = (stepIndex: number) => {
    if (stepIndex < currentStepIndex) {
      return 'bg-emerald-300 dark:bg-emerald-600';
    } else {
      return 'bg-gray-200 dark:bg-gray-700';
    }
  };

  if (variant === 'compact') {
    // Compact version: just show current state with icon and text
    const currentStep = STEPS[currentStepIndex];
    const stepColors = getStepColor(currentStepIndex);
    const IconComponent = currentStep.icon;

    return (
      <div className={cn("flex items-center space-x-2", sizes.container, className)}>
        <div
          className={cn(
            "inline-flex items-center justify-center rounded-full border transition-all duration-200 ease-in-out",
            sizes.step,
            stepColors.wrapper
          )}
          title={currentStep.label}
          aria-label={`Task status: ${currentStep.label}`}
        >
          <IconComponent
            className={cn(sizes.icon, "transition-all duration-200")}
            aria-hidden="true"
          />
        </div>
        {showLabels && (
          <span className={cn("font-medium transition-colors duration-200", stepColors.text)}>
            {currentStep.label}
          </span>
        )}
      </div>
    );
  }

  // Full stepper visualization
  return (
    <div className={cn("flex items-center", sizes.container, className)}>
      {STEPS.map((step, index) => {
        const stepColors = getStepColor(index);
        const IconComponent = step.icon;

        return (
          <React.Fragment key={step.state}>
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  "inline-flex items-center justify-center rounded-full border transition-all duration-200 ease-in-out",
                  sizes.step,
                  stepColors.wrapper
                )}
                title={step.label}
                aria-label={`Step ${index + 1}: ${step.label}`}
              >
                <IconComponent
                  className={cn(sizes.icon, "transition-all duration-200")}
                  aria-hidden="true"
                />
              </div>
              {showLabels && (
                <span className={cn(
                  "text-center font-medium whitespace-nowrap transition-colors duration-200",
                  sizes.label,
                  stepColors.text
                )}>
                  {step.label}
                </span>
              )}
            </div>

            {/* Connector line between steps */}
            {index < STEPS.length - 1 && (
              <div
                className={cn(
                  "transition-colors duration-200 rounded-full",
                  sizes.connector,
                  getConnectorColor(index)
                )}
                aria-hidden="true"
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// Helper function to get progress state from task status or percentage
export function getProgressStateFromTask(
  status?: string,
  progressPercentage?: number,
  progressState?: ProgressState
): ProgressState {
  // If we have explicit progress_state, use it
  if (progressState) {
    return progressState;
  }

  // Fallback to legacy logic for backward compatibility
  if (status) {
    const statusLower = status.toLowerCase();
    if (statusLower === 'done' || statusLower === 'completed' || statusLower === 'finished') {
      return 'complete';
    }
    if (statusLower === 'in_progress' || statusLower === 'in-progress' || statusLower === 'active') {
      return 'in_progress';
    }
    if (statusLower === 'todo' || statusLower === 'pending') {
      if (progressPercentage && progressPercentage > 0) {
        return 'in_progress';
      }
      return 'initial';
    }
  }

  // Fallback to progress percentage
  if (progressPercentage !== undefined) {
    if (progressPercentage === 100) return 'complete';
    if (progressPercentage > 0) return 'in_progress';
    return 'initial';
  }

  return 'initial';
}