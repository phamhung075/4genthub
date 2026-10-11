import * as React from "react";
import { cn } from "../../lib/utils";

export interface DialogProps extends React.HTMLAttributes<HTMLDivElement> {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
}

// Escape must reach ONLY the topmost open dialog. The listener used to sit on `document` once per
// open dialog, so one keypress reached every mounted dialog and a nested pair closed together, the
// parent silently discarding what it held. The registry is read at event time rather than trusted in
// registration order, because React runs effects CHILD-FIRST: a nested dialog registers BEFORE its
// parent, so mount order cannot answer which one is on top. Depth is read from the DOM instead, and
// this primitive renders in place (no portal), so a nested overlay IS a descendant of its parent's.
const openDialogs: HTMLElement[] = [];

function topmostOpenDialog(): HTMLElement | undefined {
  return openDialogs.reduce<HTMLElement | undefined>((best, overlay) => {
    if (!best) return overlay;
    if (best.contains(overlay)) return overlay; // the candidate sits inside the incumbent: it is above
    if (overlay.contains(best)) return best;    // the incumbent sits inside the candidate: it stays above
    return overlay;                             // siblings: the more recently opened one is on top
  }, undefined);
}

export function Dialog({ open, onOpenChange, children }: DialogProps) {
  const overlayRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const overlay = overlayRef.current;
    if (!open || !overlay) return;
    openDialogs.push(overlay);
    function onKeyDown(e: KeyboardEvent) {
      // Only the dialog the user is on answers; otherwise every open dialog answers and all close.
      if (e.key === "Escape" && topmostOpenDialog() === overlay) onOpenChange(false);
    }
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      const i = openDialogs.indexOf(overlay);
      if (i !== -1) openDialogs.splice(i, 1);
    };
  }, [open, onOpenChange]);

  React.useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
    } else if (openDialogs.length === 0) {
      document.body.style.overflow = 'unset';
    }
    return () => {
      // Only the last dialog to close may unlock the page: a nested dialog closing used to unlock
      // it while its parent was still open.
      if (openDialogs.length === 0) document.body.style.overflow = 'unset';
    };
  }, [open]);

  if (!open) return null;
  return (
    <div ref={overlayRef} className="theme-modal-overlay flex items-center justify-center" onClick={() => onOpenChange(false)}>
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
  // Read while rendering, before any child's autoFocus has moved focus into the dialog.
  const [opener] = React.useState(() => document.activeElement as HTMLElement | null);

  // Controls that are hidden (the hidden attribute, display: none on the control or an ancestor
  // inside the dialog, visibility: hidden) cannot take focus, so the trap must not land on them.
  // Computed style rather than offsetParent or getClientRects: jsdom has no layout.
  const isRendered = (el: HTMLElement) => {
    if (getComputedStyle(el).visibility === "hidden") return false;
    for (let node: HTMLElement | null = el; node && node !== contentRef.current; node = node.parentElement) {
      if (node.hidden || getComputedStyle(node).display === "none") return false;
    }
    return true;
  };

  const getFocusable = () =>
    Array.from(contentRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR) ?? []).filter(isRendered);

  // aria-modal: move focus in on open (unless a child already took it, e.g. autoFocus) and give it
  // back to the element that was focused before the dialog rendered on close.
  React.useEffect(() => {
    const content = contentRef.current;
    if (content && !content.contains(document.activeElement)) {
      (getFocusable()[0] ?? content).focus();
    }
    return () => {
      if (opener?.isConnected) opener.focus();
    };
  }, [opener]);

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
