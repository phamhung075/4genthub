import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';
import { X, CheckCircle, AlertCircle, XCircle, Info } from 'lucide-react';
import { cn } from '../../lib/utils';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface ToastContextType {
  toasts: Toast[];
  showToast: (toast: Omit<Toast, 'id'>) => string;
  dismissToast: (id: string) => void;
  dismissAll: () => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};

// Toast variants using design system colors
const toastVariants = {
  success: {
    icon: CheckCircle,
    className: "border-success bg-success-light text-success-dark dark:bg-success-dark/20 dark:text-success-light dark:border-success/50",
    iconClassName: "text-success dark:text-success-light"
  },
  error: {
    icon: XCircle,
    className: "border-error bg-error-light text-error-dark dark:bg-error-dark/20 dark:text-error-light dark:border-error/50",
    iconClassName: "text-error dark:text-error-light"
  },
  warning: {
    icon: AlertCircle,
    className: "border-warning bg-warning-light text-warning-dark dark:bg-warning-dark/20 dark:text-warning-light dark:border-warning/50",
    iconClassName: "text-warning dark:text-warning-light"
  },
  info: {
    icon: Info,
    className: "border-info bg-info-light text-info-dark dark:bg-info-dark/20 dark:text-info-light dark:border-info/50",
    iconClassName: "text-info dark:text-info-light"
  }
};

// Individual Toast Component
const ToastItem: React.FC<{ toast: Toast; onDismiss: (id: string) => void }> = ({
  toast,
  onDismiss
}) => {
  const variant = toastVariants[toast.type];
  const Icon = variant.icon;
  const [isHovered, setIsHovered] = useState(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const startTimeRef = useRef<number>(Date.now());
  const remainingTimeRef = useRef<number>(toast.duration ?? 5000);

  useEffect(() => {
    const duration = toast.duration ?? 5000; // Default 5 seconds
    if (duration > 0) {
      startTimeRef.current = Date.now();
      remainingTimeRef.current = duration;

      const startTimer = () => {
        timerRef.current = setTimeout(() => {
          onDismiss(toast.id);
        }, remainingTimeRef.current);
      };

      if (!isHovered) {
        startTimer();
      }

      return () => {
        if (timerRef.current) {
          clearTimeout(timerRef.current);
        }
      };
    }
  }, [toast.id, toast.duration, onDismiss, isHovered]);

  const handleMouseEnter = () => {
    setIsHovered(true);
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      // Calculate remaining time
      const elapsed = Date.now() - startTimeRef.current;
      remainingTimeRef.current = Math.max(0, remainingTimeRef.current - elapsed);
    }
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    startTimeRef.current = Date.now();
  };

  return (
    <div
      className={cn(
        "relative flex w-full items-start gap-3 rounded-lg border-l-4 border-t border-r border-b",
        "bg-surface shadow-lg backdrop-blur-sm",
        "p-4 transition-all duration-300 ease-in-out transform",
        "hover:scale-[1.02] hover:shadow-xl",
        "toast-slide-in",
        variant.className
      )}
      role="alert"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <div className="flex-1 space-y-1 min-w-0">
        <div className="text-sm font-semibold leading-5 text-text flex items-center gap-2">
          <Icon className={cn("h-4 w-4 flex-shrink-0", variant.iconClassName)} />
          {toast.title}
        </div>
        {toast.description && (
          <div className="text-sm text-text-secondary leading-relaxed">
            {toast.description}
          </div>
        )}
        {toast.action && (
          <div className="pt-2">
            <button
              onClick={toast.action.onClick}
              className={cn(
                "text-sm font-medium transition-colors duration-150",
                "hover:underline focus:outline-none focus:ring-2 focus:ring-primary/20 rounded",
                variant.iconClassName
              )}
            >
              {toast.action.label}
            </button>
          </div>
        )}
      </div>

      <button
        onClick={() => onDismiss(toast.id)}
        className={cn(
          "flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center",
          "text-text-tertiary hover:text-text hover:bg-surface-hover",
          "transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-primary/20"
        )}
        aria-label="Close notification"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
};

// Toast Container
export const ToastContainer: React.FC = () => {
  const { toasts, dismissToast } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-[10000] flex flex-col gap-3 w-full max-w-md pointer-events-none">
      {toasts.map((toast, index) => (
        <div
          key={toast.id}
          className="pointer-events-auto"
          style={{
            animationDelay: `${index * 100}ms`,
            zIndex: 10000 - index
          }}
        >
          <ToastItem toast={toast} onDismiss={dismissToast} />
        </div>
      ))}
    </div>
  );
};

// Toast Provider
export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = useCallback((toast: Omit<Toast, 'id'>) => {
    console.log('🍞 ToastProvider.showToast() called with:', toast);

    const id = Math.random().toString(36).substring(2, 9);
    const newToast: Toast = { ...toast, id };

    console.log('🍞 ToastProvider: Creating toast with ID:', id, 'toast:', newToast);

    setToasts(prev => {
      const newToasts = [...prev, newToast];
      console.log('🍞 ToastProvider: Updated toasts array, now have', newToasts.length, 'toasts');
      return newToasts;
    });

    return id;
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  }, []);

  const dismissAll = useCallback(() => {
    setToasts([]);
  }, []);

  // Note: Event bus listening is now handled by WebSocketToastBridge
  // This prevents duplicate toasts when both ToastProvider and WebSocketToastBridge
  // listen to the same toastEventBus events

  return (
    <ToastContext.Provider value={{ toasts, showToast, dismissToast, dismissAll }}>
      {children}
      <ToastContainer />
    </ToastContext.Provider>
  );
};

// Convenience hooks for different toast types
export const useSuccessToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    // Return a no-op function if not within provider
    return () => '';
  }
  const { showToast } = context;
  return useCallback((title: string, description?: string, action?: Toast['action']) => {
    return showToast({ type: 'success', title, description, action });
  }, [showToast]);
};

export const useErrorToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    // Return a no-op function if not within provider
    return () => '';
  }
  const { showToast } = context;
  return useCallback((title: string, description?: string, action?: Toast['action']) => {
    return showToast({ type: 'error', title, description, action, duration: 8000 }); // Longer for errors
  }, [showToast]);
};

export const useWarningToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    // Return a no-op function if not within provider
    return () => '';
  }
  const { showToast } = context;
  return useCallback((title: string, description?: string, action?: Toast['action']) => {
    return showToast({ type: 'warning', title, description, action });
  }, [showToast]);
};

export const useInfoToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    // Return a no-op function if not within provider
    return () => '';
  }
  const { showToast } = context;
  return useCallback((title: string, description?: string, action?: Toast['action']) => {
    return showToast({ type: 'info', title, description, action });
  }, [showToast]);
};