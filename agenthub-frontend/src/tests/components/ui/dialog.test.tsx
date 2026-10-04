import React from 'react';
import userEvent from '@testing-library/user-event';
import { render, screen, fireEvent, waitFor } from './../../test-utils';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../../components/ui/dialog';
import { cn } from '../../../lib/utils';

// Mock the cn utility
vi.mock('../../../lib/utils', () => ({
  cn: vi.fn((...args: any[]) => args.filter(Boolean).join(' ')),
}));

describe('Dialog components', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Ensure the mock is working
    (cn as any).mockImplementation((...args: any[]) => args.filter(Boolean).join(' '));
    // Reset body overflow style
    document.body.style.overflow = 'unset';
  });

  describe('Dialog', () => {
    it('renders when open is true', () => {
      const onOpenChange = vi.fn();
      render(
        <Dialog open={true} onOpenChange={onOpenChange}>
          <div>Dialog content</div>
        </Dialog>
      );

      expect(screen.getByText('Dialog content')).toBeInTheDocument();
    });

    it('does not render when open is false', () => {
      const onOpenChange = vi.fn();
      render(
        <Dialog open={false} onOpenChange={onOpenChange}>
          <div>Dialog content</div>
        </Dialog>
      );

      expect(screen.queryByText('Dialog content')).not.toBeInTheDocument();
    });

    it('calls onOpenChange when clicking overlay', () => {
      const onOpenChange = vi.fn();
      render(
        <Dialog open={true} onOpenChange={onOpenChange}>
          <div>Dialog content</div>
        </Dialog>
      );

      const overlay = screen.getByText('Dialog content').closest('.theme-modal-overlay');
      fireEvent.click(overlay!);

      expect(onOpenChange).toHaveBeenCalledWith(false);
    });

    it('closes dialog when Escape key is pressed', () => {
      const onOpenChange = vi.fn();
      render(
        <Dialog open={true} onOpenChange={onOpenChange}>
          <div>Dialog content</div>
        </Dialog>
      );

      fireEvent.keyDown(document, { key: 'Escape' });

      expect(onOpenChange).toHaveBeenCalledWith(false);
    });

    it('does not add keydown listener when closed', () => {
      const onOpenChange = vi.fn();
      render(
        <Dialog open={false} onOpenChange={onOpenChange}>
          <div>Dialog content</div>
        </Dialog>
      );

      fireEvent.keyDown(document, { key: 'Escape' });

      expect(onOpenChange).not.toHaveBeenCalled();
    });

    it('sets body overflow to hidden when open', () => {
      const onOpenChange = vi.fn();
      render(
        <Dialog open={true} onOpenChange={onOpenChange}>
          <div>Dialog content</div>
        </Dialog>
      );

      expect(document.body.style.overflow).toBe('hidden');
    });

    it('resets body overflow when closed', () => {
      const onOpenChange = vi.fn();
      const { rerender } = render(
        <Dialog open={true} onOpenChange={onOpenChange}>
          <div>Dialog content</div>
        </Dialog>
      );

      expect(document.body.style.overflow).toBe('hidden');

      rerender(
        <Dialog open={false} onOpenChange={onOpenChange}>
          <div>Dialog content</div>
        </Dialog>
      );

      expect(document.body.style.overflow).toBe('unset');
    });

    it('cleans up body overflow on unmount', () => {
      const onOpenChange = vi.fn();
      const { unmount } = render(
        <Dialog open={true} onOpenChange={onOpenChange}>
          <div>Dialog content</div>
        </Dialog>
      );

      expect(document.body.style.overflow).toBe('hidden');

      unmount();

      expect(document.body.style.overflow).toBe('unset');
    });

    it('renders with correct overlay structure', () => {
      const onOpenChange = vi.fn();
      render(
        <Dialog open={true} onOpenChange={onOpenChange}>
          <div data-testid="content">Dialog content</div>
        </Dialog>
      );

      const overlay = document.querySelector('.theme-modal-overlay');
      expect(overlay).toBeInTheDocument();

      expect(overlay).toHaveClass('flex', 'items-center', 'justify-center');

      const scrollContainer = overlay?.querySelector('.w-full.overflow-y-auto.p-4');
      expect(scrollContainer).toBeInTheDocument();
      expect(scrollContainer).toContainElement(screen.getByTestId('content'));
    });
  });

  describe('DialogContent', () => {
    it('renders children correctly', () => {
      render(
        <DialogContent>
          <div>Content text</div>
        </DialogContent>
      );

      expect(screen.getByText('Content text')).toBeInTheDocument();
    });

    it('applies default classes', () => {
      render(
        <DialogContent>
          <div>Content</div>
        </DialogContent>
      );

      const content = screen.getByText('Content').parentElement;
      expect(content.className).toContain('theme-modal');
      expect(content.className).toContain('w-full');
      expect(content.className).toContain('relative');
    });

    it('applies custom className', () => {
      render(
        <DialogContent className="custom-content">
          <div>Content</div>
        </DialogContent>
      );

      const content = screen.getByText('Content').parentElement;
      expect(content.className).toContain('theme-modal');
      expect(content.className).toContain('w-full');
      expect(content.className).toContain('relative');
      expect(content.className).toContain('custom-content');
    });

    it('stops click propagation', () => {
      const parentClick = vi.fn();
      render(
        <div onClick={parentClick}>
          <DialogContent>
            <div>Content</div>
          </DialogContent>
        </div>
      );

      const content = screen.getByText('Content').parentElement;
      fireEvent.click(content!);

      expect(parentClick).not.toHaveBeenCalled();
    });
  });

  describe('accessibility', () => {
    it('gives the content role dialog and aria-modal', () => {
      render(
        <Dialog open={true} onOpenChange={vi.fn()}>
          <DialogContent>Body</DialogContent>
        </Dialog>
      );

      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-modal', 'true');
      expect(dialog).toHaveTextContent('Body');
    });

    it('labels the dialog with its title', () => {
      render(
        <Dialog open={true} onOpenChange={vi.fn()}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Edit task</DialogTitle>
            </DialogHeader>
          </DialogContent>
        </Dialog>
      );

      const title = screen.getByRole('heading', { name: 'Edit task' });
      expect(title.id).not.toBe('');
      expect(screen.getByRole('dialog')).toHaveAttribute('aria-labelledby', title.id);
      expect(screen.getByRole('dialog', { name: 'Edit task' })).toBeInTheDocument();
    });

    it('sets no aria-labelledby without a title', () => {
      render(
        <Dialog open={true} onOpenChange={vi.fn()}>
          <DialogContent>No title</DialogContent>
        </Dialog>
      );

      expect(screen.getByRole('dialog')).not.toHaveAttribute('aria-labelledby');
    });

    it('gives two open dialogs different title ids', () => {
      render(
        <>
          <Dialog open={true} onOpenChange={vi.fn()}>
            <DialogContent><DialogTitle>First</DialogTitle></DialogContent>
          </Dialog>
          <Dialog open={true} onOpenChange={vi.fn()}>
            <DialogContent><DialogTitle>Second</DialogTitle></DialogContent>
          </Dialog>
        </>
      );

      expect(screen.getByRole('dialog', { name: 'First' })).toBeInTheDocument();
      expect(screen.getByRole('dialog', { name: 'Second' })).toBeInTheDocument();
    });
  });

  describe('focus management (aria-modal)', () => {
    const Harness = () => {
      const [open, setOpen] = React.useState(false);
      return (
        <>
          <button onClick={() => setOpen(true)}>Open</button>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogContent>
              <DialogTitle>Settings</DialogTitle>
              <input aria-label="first" />
              <button>middle</button>
              <button onClick={() => setOpen(false)}>last</button>
            </DialogContent>
          </Dialog>
        </>
      );
    };

    const openHarness = () => {
      render(<Harness />);
      const trigger = screen.getByRole('button', { name: 'Open' });
      trigger.focus();
      userEvent.click(trigger);
      return trigger;
    };

    it('moves focus to the first focusable element on open', () => {
      openHarness();

      expect(screen.getByLabelText('first')).toHaveFocus();
    });

    it('focuses the dialog itself when it has nothing focusable', () => {
      render(
        <Dialog open={true} onOpenChange={vi.fn()}>
          <DialogContent>Only text</DialogContent>
        </Dialog>
      );

      expect(screen.getByRole('dialog')).toHaveFocus();
    });

    it('keeps focus on an element that took it itself (autoFocus)', () => {
      render(
        <Dialog open={true} onOpenChange={vi.fn()}>
          <DialogContent>
            <button>one</button>
            <input aria-label="wanted" autoFocus />
          </DialogContent>
        </Dialog>
      );

      expect(screen.getByLabelText('wanted')).toHaveFocus();
    });

    it('wraps Tab from the last element to the first', () => {
      openHarness();
      screen.getByRole('button', { name: 'last' }).focus();

      userEvent.tab();

      expect(screen.getByLabelText('first')).toHaveFocus();
    });

    it('wraps Shift+Tab from the first element to the last', () => {
      openHarness();
      expect(screen.getByLabelText('first')).toHaveFocus();

      userEvent.tab({ shift: true });

      expect(screen.getByRole('button', { name: 'last' })).toHaveFocus();
    });

    it('moves Tab normally inside the dialog', () => {
      openHarness();

      userEvent.tab();

      expect(screen.getByRole('button', { name: 'middle' })).toHaveFocus();
    });

    it('restores focus to the element that had it before the dialog opened', () => {
      const trigger = openHarness();
      expect(screen.getByRole('dialog')).toBeInTheDocument();

      userEvent.click(screen.getByRole('button', { name: 'last' }));

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      expect(trigger).toHaveFocus();
    });

    it('lets only the first of two titles label the dialog', () => {
      render(
        <Dialog open={true} onOpenChange={vi.fn()}>
          <DialogContent>
            <DialogTitle>Primary</DialogTitle>
            <DialogTitle>Secondary</DialogTitle>
          </DialogContent>
        </Dialog>
      );

      const [primary, secondary] = screen.getAllByRole('heading');
      expect(primary.id).not.toBe(secondary.id);
      expect(screen.getByRole('dialog')).toHaveAttribute('aria-labelledby', primary.id);
      expect(screen.getByRole('dialog', { name: 'Primary' })).toBeInTheDocument();
    });
  });

  describe('DialogHeader', () => {
    it('renders children correctly', () => {
      render(
        <DialogHeader>
          <div>Header content</div>
        </DialogHeader>
      );

      expect(screen.getByText('Header content')).toBeInTheDocument();
    });

    it('applies default classes', () => {
      render(
        <DialogHeader>
          <div>Header</div>
        </DialogHeader>
      );

      const header = screen.getByText('Header').parentElement;
      expect(header.className).toContain('mb-4');
    });

    it('applies custom className', () => {
      render(
        <DialogHeader className="custom-header">
          <div>Header</div>
        </DialogHeader>
      );

      const header = screen.getByText('Header').parentElement;
      expect(header.className).toContain('mb-4');
      expect(header.className).toContain('custom-header');
    });
  });

  describe('DialogTitle', () => {
    it('renders as h2 element', () => {
      render(<DialogTitle>Dialog Title</DialogTitle>);

      const title = screen.getByRole('heading', { level: 2 });
      expect(title).toHaveTextContent('Dialog Title');
    });

    it('applies default classes', () => {
      render(<DialogTitle>Title</DialogTitle>);

      const title = screen.getByRole('heading', { level: 2 });
      expect(title.className).toContain('theme-modal-header');
      expect(title.className).toContain('text-left');
    });

    it('applies custom className', () => {
      render(<DialogTitle className="custom-title">Title</DialogTitle>);

      const title = screen.getByRole('heading', { level: 2 });
      expect(title.className).toContain('theme-modal-header');
      expect(title.className).toContain('text-left');
      expect(title.className).toContain('custom-title');
    });
  });

  describe('DialogFooter', () => {
    it('renders children correctly', () => {
      render(
        <DialogFooter>
          <button>Cancel</button>
          <button>Save</button>
        </DialogFooter>
      );

      expect(screen.getByText('Cancel')).toBeInTheDocument();
      expect(screen.getByText('Save')).toBeInTheDocument();
    });

    it('applies default classes', () => {
      render(
        <DialogFooter>
          <button>Action</button>
        </DialogFooter>
      );

      const footer = screen.getByText('Action').parentElement;
      expect(footer.className).toContain('mt-6');
      expect(footer.className).toContain('flex');
      expect(footer.className).toContain('justify-end');
      expect(footer.className).toContain('gap-2');
    });

    it('applies custom className', () => {
      render(
        <DialogFooter className="custom-footer">
          <button>Action</button>
        </DialogFooter>
      );

      const footer = screen.getByText('Action').parentElement;
      expect(footer.className).toContain('mt-6');
      expect(footer.className).toContain('flex');
      expect(footer.className).toContain('justify-end');
      expect(footer.className).toContain('gap-2');
      expect(footer.className).toContain('custom-footer');
    });
  });

  describe('Integration', () => {
    it('renders complete dialog structure', () => {
      const onOpenChange = vi.fn();
      render(
        <Dialog open={true} onOpenChange={onOpenChange}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Test Dialog</DialogTitle>
            </DialogHeader>
            <div>Dialog body content</div>
            <DialogFooter>
              <button>Cancel</button>
              <button>Confirm</button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      );

      expect(screen.getByRole('heading', { name: 'Test Dialog' })).toBeInTheDocument();
      expect(screen.getByText('Dialog body content')).toBeInTheDocument();
      expect(screen.getByText('Cancel')).toBeInTheDocument();
      expect(screen.getByText('Confirm')).toBeInTheDocument();
    });

    it('does not close when clicking dialog content', () => {
      const onOpenChange = vi.fn();
      render(
        <Dialog open={true} onOpenChange={onOpenChange}>
          <DialogContent>
            <div>Click me</div>
          </DialogContent>
        </Dialog>
      );

      fireEvent.click(screen.getByText('Click me'));

      expect(onOpenChange).not.toHaveBeenCalled();
    });

    it('calls cn utility with correct arguments', () => {
      render(
        <>
          <DialogContent className="content-class">Content</DialogContent>
          <DialogHeader className="header-class">Header</DialogHeader>
          <DialogTitle className="title-class">Title</DialogTitle>
          <DialogFooter className="footer-class">Footer</DialogFooter>
        </>
      );

      expect(cn).toHaveBeenCalledWith('theme-modal w-full relative', 'content-class');
      expect(cn).toHaveBeenCalledWith('mb-4', 'header-class');
      expect(cn).toHaveBeenCalledWith('theme-modal-header text-left', 'title-class');
      expect(cn).toHaveBeenCalledWith('mt-6 flex justify-end gap-2', 'footer-class');
    });
  });
});
