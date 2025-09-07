import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../../components/ui/dialog';
import { cn } from '../../../lib/utils';

// Mock the cn utility
jest.mock('../../../lib/utils', () => ({
  cn: jest.fn((...args: any[]) => args.filter(Boolean).join(' ')),
}));

describe('Dialog components', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Ensure the mock is working
    (cn as jest.Mock).mockImplementation((...args: any[]) => args.filter(Boolean).join(' '));
    // Reset body overflow style
    document.body.style.overflow = 'unset';
  });

  describe('Dialog', () => {
    it('renders when open is true', () => {
      const onOpenChange = jest.fn();
      render(
        <Dialog open={true} onOpenChange={onOpenChange}>
          <div>Dialog content</div>
        </Dialog>
      );
      
      expect(screen.getByText('Dialog content')).toBeInTheDocument();
    });

    it('does not render when open is false', () => {
      const onOpenChange = jest.fn();
      render(
        <Dialog open={false} onOpenChange={onOpenChange}>
          <div>Dialog content</div>
        </Dialog>
      );
      
      expect(screen.queryByText('Dialog content')).not.toBeInTheDocument();
    });

    it('calls onOpenChange when clicking overlay', () => {
      const onOpenChange = jest.fn();
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
      const onOpenChange = jest.fn();
      render(
        <Dialog open={true} onOpenChange={onOpenChange}>
          <div>Dialog content</div>
        </Dialog>
      );
      
      fireEvent.keyDown(document, { key: 'Escape' });
      
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });

    it('does not add keydown listener when closed', () => {
      const onOpenChange = jest.fn();
      render(
        <Dialog open={false} onOpenChange={onOpenChange}>
          <div>Dialog content</div>
        </Dialog>
      );
      
      fireEvent.keyDown(document, { key: 'Escape' });
      
      expect(onOpenChange).not.toHaveBeenCalled();
    });

    it('sets body overflow to hidden when open', () => {
      const onOpenChange = jest.fn();
      render(
        <Dialog open={true} onOpenChange={onOpenChange}>
          <div>Dialog content</div>
        </Dialog>
      );
      
      expect(document.body.style.overflow).toBe('hidden');
    });

    it('resets body overflow when closed', () => {
      const onOpenChange = jest.fn();
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
      const onOpenChange = jest.fn();
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
      const onOpenChange = jest.fn();
      render(
        <Dialog open={true} onOpenChange={onOpenChange}>
          <div data-testid="content">Dialog content</div>
        </Dialog>
      );
      
      const overlay = document.querySelector('.theme-modal-overlay');
      expect(overlay).toBeInTheDocument();
      
      const fixedContainer = overlay?.querySelector('.fixed.inset-0.overflow-y-auto');
      expect(fixedContainer).toBeInTheDocument();
      
      const flexContainer = fixedContainer?.querySelector('.flex.min-h-full.items-center.justify-center.p-4');
      expect(flexContainer).toBeInTheDocument();
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
      const parentClick = jest.fn();
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
      const onOpenChange = jest.fn();
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
      const onOpenChange = jest.fn();
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