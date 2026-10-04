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

// DialogContent names itself after the first DialogTitle rendered inside it. A second title keeps
// its own id and does not label the dialog; if the first title unmounts the dialog is unlabelled.
const DialogTitleContext = React.createContext<{ setTitleId: React.Dispatch<React.SetStateAction<string | undefined>> } | null>(null);

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

export function DialogContent({ children, className }: { children: React.ReactNode; className?: string }) {
  const contentRef = React.useRef<HTMLDivElement>(null);
  const [titleId, setTitleId] = React.useState<string | undefined>(undefined);
  const titleContext = React.useMemo(() => ({ setTitleId }), []);

  const getFocusable = () =>
    Array.from(contentRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR) ?? []);

  // aria-modal: move focus in on open (unless a child already took it, e.g. autoFocus) and give it
  // back to the previously focused element on close.
  React.useEffect(() => {
    const content = contentRef.current;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    if (content && !content.contains(document.activeElement)) {
      (getFocusable()[0] ?? content).focus();
    }
    return () => {
      if (previouslyFocused?.isConnected) previouslyFocused.focus();
    };
  }, []);

  // aria-modal: Tab and Shift+Tab wrap inside the dialog.
  const trapTab = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key !== "Tab") return;
    const focusable = getFocusable();
    const active = document.activeElement;
    if (focusable.length === 0) {
      e.preventDefault();
      contentRef.current?.focus();
    } else if (e.shiftKey && (active === focusable[0] || active === contentRef.current)) {
      e.preventDefault();
      focusable[focusable.length - 1].focus();
    } else if (!e.shiftKey && active === focusable[focusable.length - 1]) {
      e.preventDefault();
      focusable[0].focus();
    }
  };

  return (
    <DialogTitleContext.Provider value={titleContext}>
      <div
        ref={contentRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={cn(
          "theme-modal w-full relative",
          className
        )}
        onClick={e => e.stopPropagation()}
        onKeyDown={trapTab}
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
  const setTitleId = titleContext?.setTitleId;
  const id = React.useId();

  React.useEffect(() => {
    setTitleId?.(current => current ?? id);
    return () => setTitleId?.(current => (current === id ? undefined : current));
  }, [setTitleId, id]);

  return <h2 id={id} className={cn("theme-modal-header text-left", className)}>{children}</h2>;
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
