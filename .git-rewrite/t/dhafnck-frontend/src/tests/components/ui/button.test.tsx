import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, beforeEach, expect, vi } from 'vitest';
import '@testing-library/jest-dom';
import { Button, ButtonProps } from '../../../components/ui/button';
import { cn } from '../../../lib/utils';

// Mock the cn utility
vi.mock('../../../lib/utils', () => ({
  cn: vi.fn((...args: any[]) => args.filter(Boolean).join(' ')),
}));

describe('Button', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Ensure the mock is working
    (cn as ReturnType<typeof vi.fn>).mockImplementation((...args: any[]) => args.filter(Boolean).join(' '));
  });

  it('renders with default props', () => {
    render(<Button>Click me</Button>);
    
    const button = screen.getByRole('button', { name: /click me/i });
    expect(button).toBeInTheDocument();
    // Check that the button's className contains the expected classes
    expect(button.className).toContain('theme-btn-primary');
    expect(button.className).toContain('h-10');
    expect(button.className).toContain('px-4');
    expect(button.className).toContain('py-2');
  });

  describe('variants', () => {
    it('renders default variant', () => {
      render(<Button variant="default">Default</Button>);
      
      const button = screen.getByRole('button');
      expect(button.className).toContain('theme-btn-primary');
    });

    it('renders outline variant', () => {
      render(<Button variant="outline">Outline</Button>);
      
      const button = screen.getByRole('button');
      expect(button.className).toContain('theme-btn-outline');
    });

    it('renders secondary variant', () => {
      render(<Button variant="secondary">Secondary</Button>);
      
      const button = screen.getByRole('button');
      expect(button.className).toContain('theme-btn-secondary');
    });

    it('renders ghost variant', () => {
      render(<Button variant="ghost">Ghost</Button>);
      
      const button = screen.getByRole('button');
      expect(button.className).toContain('theme-btn-ghost');
    });

    it('renders link variant', () => {
      render(<Button variant="link">Link</Button>);
      
      const button = screen.getByRole('button');
      expect(button.className).toContain('underline-offset-4');
      expect(button.className).toContain('hover:underline');
      expect(button.className).toContain('text-primary');
    });
  });

  describe('sizes', () => {
    it('renders default size', () => {
      render(<Button size="default">Default</Button>);
      
      const button = screen.getByRole('button');
      expect(button.className).toContain('h-10');
      expect(button.className).toContain('px-4');
      expect(button.className).toContain('py-2');
    });

    it('renders small size', () => {
      render(<Button size="sm">Small</Button>);
      
      const button = screen.getByRole('button');
      expect(button.className).toContain('h-9');
      expect(button.className).toContain('px-3');
    });

    it('renders large size', () => {
      render(<Button size="lg">Large</Button>);
      
      const button = screen.getByRole('button');
      expect(button.className).toContain('h-11');
      expect(button.className).toContain('px-8');
    });

    it('renders icon size', () => {
      render(<Button size="icon">🔥</Button>);
      
      const button = screen.getByRole('button');
      expect(button.className).toContain('h-10');
      expect(button.className).toContain('w-10');
      expect(button.className).toContain('p-0');
      expect(button.className).toContain('flex');
      expect(button.className).toContain('items-center');
      expect(button.className).toContain('justify-center');
    });
  });

  it('applies custom className', () => {
    render(<Button className="custom-class">Custom</Button>);
    
    const button = screen.getByRole('button');
    expect(button.className).toContain('custom-class');
  });

  it('forwards ref correctly', () => {
    const ref = React.createRef<HTMLButtonElement>();
    render(<Button ref={ref}>Ref Button</Button>);
    
    expect(ref.current).toBeInstanceOf(HTMLButtonElement);
    expect(ref.current?.textContent).toBe('Ref Button');
  });

  it('handles click events', () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    
    const button = screen.getByRole('button');
    fireEvent.click(button);
    
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('respects disabled state', () => {
    const handleClick = vi.fn();
    render(<Button disabled onClick={handleClick}>Disabled</Button>);
    
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
    expect(button.className).toContain('disabled:opacity-50');
    expect(button.className).toContain('disabled:pointer-events-none');
    
    fireEvent.click(button);
    expect(handleClick).not.toHaveBeenCalled();
  });

  it('applies all base classes', () => {
    render(<Button>Base Classes</Button>);
    
    const button = screen.getByRole('button');
    expect(button.className).toContain('inline-flex');
    expect(button.className).toContain('items-center');
    expect(button.className).toContain('justify-center');
    expect(button.className).toContain('rounded-md');
    expect(button.className).toContain('text-sm');
    expect(button.className).toContain('font-medium');
    expect(button.className).toContain('transition-colors');
    expect(button.className).toContain('focus-visible:outline-none');
    expect(button.className).toContain('focus-visible:ring-2');
    expect(button.className).toContain('focus-visible:ring-ring');
    expect(button.className).toContain('focus-visible:ring-offset-2');
    expect(button.className).toContain('ring-offset-background');
  });

  it('passes through HTML button attributes', () => {
    render(
      <Button
        type="submit"
        name="test-button"
        value="test-value"
        aria-label="Test Button"
        data-testid="custom-test-id"
      >
        HTML Attributes
      </Button>
    );
    
    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('type', 'submit');
    expect(button).toHaveAttribute('name', 'test-button');
    expect(button).toHaveAttribute('value', 'test-value');
    expect(button).toHaveAttribute('aria-label', 'Test Button');
    expect(button).toHaveAttribute('data-testid', 'custom-test-id');
  });

  it('combines variant and size classes correctly', () => {
    render(<Button variant="outline" size="lg">Combined</Button>);
    
    const button = screen.getByRole('button');
    expect(button.className).toContain('theme-btn-outline');
    expect(button.className).toContain('h-11');
    expect(button.className).toContain('px-8');
  });

  it('calls cn utility with correct arguments', () => {
    const customClass = 'my-custom-class';
    render(<Button variant="secondary" size="sm" className={customClass}>CN Test</Button>);
    
    expect(cn).toHaveBeenCalledWith(
      expect.stringContaining('inline-flex'),
      'theme-btn-secondary',
      'h-9 px-3',
      customClass
    );
  });

  it('renders children correctly', () => {
    render(
      <Button>
        <span>Icon</span>
        <span>Text</span>
      </Button>
    );
    
    expect(screen.getByText('Icon')).toBeInTheDocument();
    expect(screen.getByText('Text')).toBeInTheDocument();
  });

  it('has correct display name', () => {
    expect(Button.displayName).toBe('Button');
  });
});