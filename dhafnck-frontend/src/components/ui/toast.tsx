import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
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

// Toast variants
const toastVariants = {
  success: {
    icon: CheckCircle,
    className: "border-green-500 bg-green-50 text-green-900 dark:bg-green-950 dark:text-green-100",
    iconClassName: "text-green-500"
  },
  error: {
    icon: XCircle,
    className: "border-red-500 bg-red-50 text-red-900 dark:bg-red-950 dark:text-red-100",
    iconClassName: "text-red-500"
  },
  warning: {
    icon: AlertCircle,
    className: "border-yellow-500 bg-yellow-50 text-yellow-900 dark:bg-yellow-950 dark:text-yellow-100",
    iconClassName: "text-yellow-500"
  },
  info: {
    icon: Info,
    className: "border-blue-500 bg-blue-50 text-blue-900 dark:bg-blue-950 dark:text-blue-100",
    iconClassName: "text-blue-500"
  }
};

// Individual Toast Component
const ToastItem: React.FC<{ toast: Toast; onDismiss: (id: string) => void }> = ({
  toast,
  onDismiss
}) => {
  const variant = toastVariants[toast.type];
  const Icon = variant.icon;

  useEffect(() => {
    const duration = toast.duration ?? 5000; // Default 5 seconds
    if (duration > 0) {
      const timer = setTimeout(() => {
        onDismiss(toast.id);
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [toast.id, toast.duration, onDismiss]);

  return (
    <div
      className={cn(
        "relative flex w-full items-start gap-3 rounded-lg border p-4 shadow-lg transition-all duration-300 ease-in-out",
        "animate-in",
        variant.className
      )}
      role="alert"
    >
      <Icon className={cn("h-5 w-5 flex-shrink-0 mt-0.5", variant.iconClassName)} />
      <div className="flex-1 space-y-1">
        <div className="text-sm font-medium leading-none">
          {toast.title}
        </div>
        {toast.description && (
          <div className="text-sm opacity-80">
            {toast.description}
          </div>
        )}
        {toast.action && (
          <div className="pt-2">
            <button
              onClick={toast.action.onClick}
              className="text-sm font-medium underline hover:no-underline"
            >
              {toast.action.label}
            </button>
          </div>
        )}
      </div>
      <button
        onClick={() => onDismiss(toast.id)}
        className="absolute right-2 top-2 rounded-md p-1 opacity-70 hover:opacity-100 transition-opacity"
        aria-label="Close notification"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
};

// Toast Container
export const ToastContainer: React.FC = () => {
  const { toasts, dismissToast } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 w-full max-w-sm pointer-events-none">
      {toasts.map((toast) => (
        <div key={toast.id} className="pointer-events-auto">
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
    const id = Math.random().toString(36).substring(2, 9);
    const newToast: Toast = { ...toast, id };
    
    setToasts(prev => [...prev, newToast]);
    return id;
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  }, []);

  const dismissAll = useCallback(() => {
    setToasts([]);
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, showToast, dismissToast, dismissAll }}>
      {children}
      <ToastContainer />
    </ToastContext.Provider>
  );
};

// Convenience hooks for different toast types
export const useSuccessToast = () => {
  const { showToast } = useToast();
  return useCallback((title: string, description?: string, action?: Toast['action']) => {
    return showToast({ type: 'success', title, description, action });
  }, [showToast]);
};

export const useErrorToast = () => {
  const { showToast } = useToast();
  return useCallback((title: string, description?: string, action?: Toast['action']) => {
    return showToast({ type: 'error', title, description, action, duration: 8000 }); // Longer for errors
  }, [showToast]);
};

export const useWarningToast = () => {
  const { showToast } = useToast();
  return useCallback((title: string, description?: string, action?: Toast['action']) => {
    return showToast({ type: 'warning', title, description, action });
  }, [showToast]);
};

export const useInfoToast = () => {
  const { showToast } = useToast();
  return useCallback((title: string, description?: string, action?: Toast['action']) => {
    return showToast({ type: 'info', title, description, action });
  }, [showToast]);
};