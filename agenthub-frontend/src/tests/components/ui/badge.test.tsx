import React from 'react';
import { render, screen } from '@testing-library/react';
import { Badge, BadgeProps } from '../../../components/ui/badge';

// Mock the utils module
jest.mock('../../../lib/utils', () => ({
  cn: (...classes: any[]) => classes.filter(Boolean).join(' ')
}));

describe('Badge', () => {
  const renderBadge = (props: Partial<BadgeProps> = {}) => {
    const defaultProps: BadgeProps = {
      children: 'Test Badge',
      ...props
    };
    return render(<Badge {...defaultProps} />);
  };

  describe('Rendering', () => {
    it('renders with default variant', () => {
      renderBadge();
      const badge = screen.getByText('Test Badge');
      expect(badge).toBeInTheDocument();
      expect(badge.className).toContain('bg-primary');
      expect(badge.className).toContain('text-primary-foreground');
    });

    it('renders with secondary variant', () => {
      renderBadge({ variant: 'secondary' });
      const badge = screen.getByText('Test Badge');
      expect(badge.className).toContain('bg-secondary');
      expect(badge.className).toContain('text-secondary-foreground');
    });

    it('renders with destructive variant', () => {
      renderBadge({ variant: 'destructive' });
      const badge = screen.getByText('Test Badge');
      expect(badge.className).toContain('bg-destructive');
      expect(badge.className).toContain('text-destructive-foreground');
    });

    it('renders with outline variant', () => {
      renderBadge({ variant: 'outline' });
      const badge = screen.getByText('Test Badge');
      expect(badge.className).toContain('border');
      expect(badge.className).toContain('border-input');
    });

    it('applies custom className', () => {
      renderBadge({ className: 'custom-class' });
      const badge = screen.getByText('Test Badge');
      expect(badge.className).toContain('custom-class');
    });

    it('renders children correctly', () => {
      renderBadge({ children: <span>Custom Content</span> });
      expect(screen.getByText('Custom Content')).toBeInTheDocument();
    });

    it('renders with base styling classes', () => {
      renderBadge();
      const badge = screen.getByText('Test Badge');
      expect(badge.className).toContain('inline-flex');
      expect(badge.className).toContain('items-center');
      expect(badge.className).toContain('rounded-full');
      expect(badge.className).toContain('border');
      expect(badge.className).toContain('px-2.5');
      expect(badge.className).toContain('py-0.5');
      expect(badge.className).toContain('text-xs');
      expect(badge.className).toContain('font-semibold');
      expect(badge.className).toContain('transition-colors');
    });

    it('renders with focus styling classes', () => {
      renderBadge();
      const badge = screen.getByText('Test Badge');
      expect(badge.className).toContain('focus:outline-none');
      expect(badge.className).toContain('focus:ring-2');
      expect(badge.className).toContain('focus:ring-ring');
      expect(badge.className).toContain('focus:ring-offset-2');
    });
  });

  describe('Variant Validation', () => {
    it('handles invalid variant string by defaulting to default variant', () => {
      renderBadge({ variant: 'invalid' as any });
      const badge = screen.getByText('Test Badge');
      expect(badge.className).toContain('bg-primary');
      expect(badge.className).toContain('text-primary-foreground');
    });

    it('handles non-string variant by defaulting to default variant', () => {
      renderBadge({ variant: {} as any });
      const badge = screen.getByText('Test Badge');
      expect(badge.className).toContain('bg-primary');
      expect(badge.className).toContain('text-primary-foreground');
    });

    it('handles null variant by defaulting to default variant', () => {
      renderBadge({ variant: null as any });
      const badge = screen.getByText('Test Badge');
      expect(badge.className).toContain('bg-primary');
      expect(badge.className).toContain('text-primary-foreground');
    });

    it('handles undefined variant by defaulting to default variant', () => {
      renderBadge({ variant: undefined });
      const badge = screen.getByText('Test Badge');
      expect(badge.className).toContain('bg-primary');
      expect(badge.className).toContain('text-primary-foreground');
    });

    it('handles number variant by defaulting to default variant', () => {
      renderBadge({ variant: 123 as any });
      const badge = screen.getByText('Test Badge');
      expect(badge.className).toContain('bg-primary');
      expect(badge.className).toContain('text-primary-foreground');
    });

    it('handles array variant by defaulting to default variant', () => {
      renderBadge({ variant: ['secondary'] as any });
      const badge = screen.getByText('Test Badge');
      expect(badge.className).toContain('bg-primary');
      expect(badge.className).toContain('text-primary-foreground');
    });
  });

  describe('Props Forwarding', () => {
    it('forwards HTML attributes to the span element', () => {
      renderBadge({ 
        'data-testid': 'test-badge',
        'aria-label': 'Test Label',
        title: 'Test Title'
      });
      
      const badge = screen.getByText('Test Badge');
      expect(badge).toHaveAttribute('data-testid', 'test-badge');
      expect(badge).toHaveAttribute('aria-label', 'Test Label');
      expect(badge).toHaveAttribute('title', 'Test Title');
    });

    it('forwards event handlers', () => {
      const handleClick = jest.fn();
      const handleMouseEnter = jest.fn();
      
      renderBadge({ 
        onClick: handleClick,
        onMouseEnter: handleMouseEnter
      });
      
      const badge = screen.getByText('Test Badge');
      badge.click();
      expect(handleClick).toHaveBeenCalledTimes(1);
      
      badge.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
      expect(handleMouseEnter).toHaveBeenCalledTimes(1);
    });

    it('forwards style prop', () => {
      renderBadge({ 
        style: { backgroundColor: 'red', color: 'white' }
      });
      
      const badge = screen.getByText('Test Badge');
      expect(badge).toHaveStyle({ backgroundColor: 'red', color: 'white' });
    });
  });

  describe('Ref Forwarding', () => {
    it('forwards ref to the span element', () => {
      const ref = React.createRef<HTMLSpanElement>();
      render(<Badge ref={ref}>Test Badge</Badge>);
      
      expect(ref.current).toBeInstanceOf(HTMLSpanElement);
      expect(ref.current?.textContent).toBe('Test Badge');
    });
  });

  describe('Edge Cases', () => {
    it('renders empty badge', () => {
      renderBadge({ children: '' });
      const badge = screen.getByRole('generic');
      expect(badge).toBeInTheDocument();
      expect(badge.textContent).toBe('');
    });

    it('renders with complex children', () => {
      renderBadge({ 
        children: (
          <div>
            <span>Complex</span>
            <strong>Content</strong>
          </div>
        )
      });
      
      expect(screen.getByText('Complex')).toBeInTheDocument();
      expect(screen.getByText('Content')).toBeInTheDocument();
    });

    it('maintains all variants in badgeVariants object', () => {
      const variants: BadgeProps['variant'][] = ['default', 'secondary', 'destructive', 'outline'];
      
      variants.forEach(variant => {
        const { container } = renderBadge({ variant, children: `${variant} badge` });
        const badge = container.querySelector('span');
        expect(badge).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('renders as inline element', () => {
      renderBadge();
      const badge = screen.getByText('Test Badge');
      expect(badge.tagName).toBe('SPAN');
    });

    it('supports ARIA attributes', () => {
      renderBadge({ 
        'aria-label': 'Status Badge',
        'aria-describedby': 'status-description',
        role: 'status'
      });
      
      const badge = screen.getByRole('status');
      expect(badge).toHaveAttribute('aria-label', 'Status Badge');
      expect(badge).toHaveAttribute('aria-describedby', 'status-description');
    });
  });

  describe('Display Name', () => {
    it('has correct display name for debugging', () => {
      expect(Badge.displayName).toBe('Badge');
    });
  });
});