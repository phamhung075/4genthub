import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import { Input } from '../../../components/ui/input';
import { cn } from '../../../lib/utils';

// Mock the cn utility
jest.mock('../../../lib/utils', () => ({
  cn: jest.fn((...args: any[]) => args.filter(Boolean).join(' ')),
}));

describe('Input', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Ensure the mock is working
    (cn as jest.Mock).mockImplementation((...args: any[]) => args.filter(Boolean).join(' '));
  });

  it('renders with default props', () => {
    render(<Input />);
    
    const input = screen.getByRole('textbox');
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute('type', 'text');
    expect(input.className).toContain('theme-input');
    expect(input.className).toContain('flex');
    expect(input.className).toContain('h-10');
    expect(input.className).toContain('w-full');
    expect(input.className).toContain('text-sm');
    expect(input.className).toContain('disabled:opacity-50');
    expect(input.className).toContain('disabled:pointer-events-none');
  });

  it('renders with custom type', () => {
    render(<Input type="email" />);
    
    const input = document.querySelector('input[type="email"]');
    expect(input).toBeInTheDocument();
  });

  it('renders with different input types', () => {
    const types = ['password', 'number', 'tel', 'url', 'search', 'date'];
    
    types.forEach(type => {
      const { container } = render(<Input type={type as any} />);
      const input = container.querySelector(`input[type="${type}"]`);
      expect(input).toBeInTheDocument();
    });
  });

  it('applies custom className', () => {
    render(<Input className="custom-input" />);
    
    const input = screen.getByRole('textbox');
    expect(input.className).toContain('theme-input');
    expect(input.className).toContain('flex');
    expect(input.className).toContain('h-10');
    expect(input.className).toContain('w-full');
    expect(input.className).toContain('text-sm');
    expect(input.className).toContain('disabled:opacity-50');
    expect(input.className).toContain('disabled:pointer-events-none');
    expect(input.className).toContain('custom-input');
  });

  it('forwards ref correctly', () => {
    const ref = React.createRef<HTMLInputElement>();
    render(<Input ref={ref} />);
    
    expect(ref.current).toBeInstanceOf(HTMLInputElement);
    expect(ref.current?.tagName).toBe('INPUT');
  });

  it('handles value and onChange', () => {
    const handleChange = jest.fn();
    render(<Input value="test" onChange={handleChange} />);
    
    const input = screen.getByRole('textbox');
    expect(input).toHaveValue('test');
    
    userEvent.type(input, 'a');
    expect(handleChange).toHaveBeenCalled();
  });

  it('handles placeholder', () => {
    render(<Input placeholder="Enter text here" />);
    
    const input = screen.getByPlaceholderText('Enter text here');
    expect(input).toBeInTheDocument();
  });

  it('respects disabled state', () => {
    render(<Input disabled />);
    
    const input = screen.getByRole('textbox');
    expect(input).toBeDisabled();
    expect(input.className).toContain('disabled:opacity-50');
    expect(input.className).toContain('disabled:pointer-events-none');
  });

  it('handles readonly state', () => {
    render(<Input readOnly value="readonly text" />);
    
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('readonly');
    expect(input).toHaveValue('readonly text');
  });

  it('handles required attribute', () => {
    render(<Input required />);
    
    const input = screen.getByRole('textbox');
    expect(input).toBeRequired();
  });

  it('handles autofocus', () => {
    render(<Input autoFocus />);
    
    const input = screen.getByRole('textbox');
    expect(input).toHaveFocus();
  });

  it('handles maxLength and minLength', () => {
    render(<Input maxLength={10} minLength={5} />);
    
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('maxLength', '10');
    expect(input).toHaveAttribute('minLength', '5');
  });

  it('handles pattern attribute', () => {
    render(<Input pattern="[0-9]*" />);
    
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('pattern', '[0-9]*');
  });

  it('handles name and id attributes', () => {
    render(<Input name="username" id="user-input" />);
    
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('name', 'username');
    expect(input).toHaveAttribute('id', 'user-input');
  });

  it('handles autoComplete attribute', () => {
    render(<Input autoComplete="email" />);
    
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('autocomplete', 'email');
  });

  it('handles onFocus and onBlur events', () => {
    const handleFocus = jest.fn();
    const handleBlur = jest.fn();
    
    render(<Input onFocus={handleFocus} onBlur={handleBlur} />);
    
    const input = screen.getByRole('textbox');
    
    fireEvent.focus(input);
    expect(handleFocus).toHaveBeenCalledTimes(1);
    
    fireEvent.blur(input);
    expect(handleBlur).toHaveBeenCalledTimes(1);
  });

  it('handles onKeyDown event', () => {
    const handleKeyDown = jest.fn();
    render(<Input onKeyDown={handleKeyDown} />);
    
    const input = screen.getByRole('textbox');
    fireEvent.keyDown(input, { key: 'Enter' });
    
    expect(handleKeyDown).toHaveBeenCalledTimes(1);
    expect(handleKeyDown).toHaveBeenCalledWith(
      expect.objectContaining({
        key: 'Enter',
      })
    );
  });

  it('passes through aria attributes', () => {
    render(
      <Input
        aria-label="Test input"
        aria-describedby="input-help"
        aria-invalid="true"
        aria-required="true"
      />
    );
    
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('aria-label', 'Test input');
    expect(input).toHaveAttribute('aria-describedby', 'input-help');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input).toHaveAttribute('aria-required', 'true');
  });

  it('passes through data attributes', () => {
    render(<Input data-testid="custom-input" data-value="test" />);
    
    const input = screen.getByTestId('custom-input');
    expect(input).toHaveAttribute('data-value', 'test');
  });

  it('has correct display name', () => {
    expect(Input.displayName).toBe('Input');
  });

  it('calls cn utility with correct arguments', () => {
    const customClass = 'my-custom-class';
    render(<Input className={customClass} />);
    
    expect(cn).toHaveBeenCalledWith(
      'theme-input flex h-10 w-full text-sm disabled:opacity-50 disabled:pointer-events-none',
      customClass
    );
  });

  it('handles form submission', () => {
    const handleSubmit = jest.fn((e) => e.preventDefault());
    render(
      <form onSubmit={handleSubmit}>
        <Input name="test" defaultValue="test value" />
        <button type="submit">Submit</button>
      </form>
    );
    
    const button = screen.getByRole('button', { name: 'Submit' });
    fireEvent.click(button);
    
    expect(handleSubmit).toHaveBeenCalledTimes(1);
  });
});