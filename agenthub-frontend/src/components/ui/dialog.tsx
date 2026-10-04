import * as React from "react";
import { cn } from "../../lib/utils";

export interface DialogProps extends React.HTMLAttributes<HTMLDivElement> {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
}

export function Dialog({ open, onOpenChange, children }: DialogProps) {
  React.useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onOpenChange(false);
    }
    if (open) document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onOpenChange]);

  React.useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [open]);

  if (!open) return null;
  return (
    <div className="theme-modal-overlay flex items-center justify-center" onClick={() => onOpenChange(false)}>
      <div className="w-full max-h-[90vh] overflow-y-auto p-4">
        {children}
      </div>
    </div>
  );
}

// DialogContent names itself after the DialogTitle rendered inside it.
const DialogTitleContext = React.createContext<{ titleId: string; setHasTitle: (hasTitle: boolean) => void } | null>(null);

export function DialogContent({ children, className }: { children: React.ReactNode; className?: string }) {
  const titleId = React.useId();
  const [hasTitle, setHasTitle] = React.useState(false);
  const titleContext = React.useMemo(() => ({ titleId, setHasTitle }), [titleId]);

  return (
    <DialogTitleContext.Provider value={titleContext}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={hasTitle ? titleId : undefined}
        className={cn(
          "theme-modal w-full relative",
          className
        )}
        onClick={e => e.stopPropagation()}
      >
        {children}
      </div>
    </DialogTitleContext.Provider>
  );
}

export function DialogHeader({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("mb-4", className)}>{children}</div>;
}

export function DialogTitle({ children, className }: { children: React.ReactNode; className?: string }) {
  const titleContext = React.useContext(DialogTitleContext);
  const setHasTitle = titleContext?.setHasTitle;

  React.useEffect(() => {
    setHasTitle?.(true);
    return () => setHasTitle?.(false);
  }, [setHasTitle]);

  return <h2 id={titleContext?.titleId} className={cn("theme-modal-header text-left", className)}>{children}</h2>;
}

export function DialogFooter({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("mt-6 flex justify-end gap-2", className)}>{children}</div>;
}

export function DialogDescription({ children, className }: { children: React.ReactNode; className?: string }) {
  return <p className={cn("text-sm text-muted-foreground mb-4", className)}>{children}</p>;
}

export function DialogTrigger({ children, asChild }: { children: React.ReactNode; asChild?: boolean }) {
  return <>{children}</>;
}
