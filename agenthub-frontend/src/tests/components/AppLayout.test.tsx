import React from 'react';
import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import { AppLayout } from '../../components/AppLayout';

// Mock the Header component
vi.mock('../../components/Header', () => ({
  Header: () => <header data-testid="mock-header">Mock Header</header>
}));

describe('AppLayout', () => {
  it('renders without crashing', () => {
    render(
      <AppLayout>
        <div>Test Content</div>
      </AppLayout>
    );
  });

  it('renders the Header component', () => {
    render(
      <AppLayout>
        <div>Test Content</div>
      </AppLayout>
    );

    expect(screen.getByTestId('mock-header')).toBeInTheDocument();
  });

  it('renders children content', () => {
    const testContent = 'This is test content';
    
    render(
      <AppLayout>
        <div>{testContent}</div>
      </AppLayout>
    );

    expect(screen.getByText(testContent)).toBeInTheDocument();
  });

  it('applies correct layout structure', () => {
    const { container } = render(
      <AppLayout>
        <div>Test Content</div>
      </AppLayout>
    );

    const layoutDiv = container.firstChild as HTMLElement;
    expect(layoutDiv).toHaveClass('flex', 'flex-col', 'h-screen', 'bg-background', 'text-foreground');
  });

  it('main element has correct classes', () => {
    render(
      <AppLayout>
        <div>Test Content</div>
      </AppLayout>
    );

    const mainElement = screen.getByRole('main');
    expect(mainElement).toHaveClass('flex-1', 'overflow-y-auto');
  });

  it('renders multiple children correctly', () => {
    render(
      <AppLayout>
        <div>First Child</div>
        <div>Second Child</div>
        <div>Third Child</div>
      </AppLayout>
    );

    expect(screen.getByText('First Child')).toBeInTheDocument();
    expect(screen.getByText('Second Child')).toBeInTheDocument();
    expect(screen.getByText('Third Child')).toBeInTheDocument();
  });

  it('maintains layout structure with no children', () => {
    const { container } = render(<AppLayout>{null}</AppLayout>);

    const layoutDiv = container.firstChild as HTMLElement;
    expect(layoutDiv).toHaveClass('flex', 'flex-col', 'h-screen');
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('renders complex children components', () => {
    const ComplexChild = () => (
      <div>
        <h1>Title</h1>
        <p>Paragraph</p>
        <button>Button</button>
      </div>
    );

    render(
      <AppLayout>
        <ComplexChild />
      </AppLayout>
    );

    expect(screen.getByText('Title')).toBeInTheDocument();
    expect(screen.getByText('Paragraph')).toBeInTheDocument();
    expect(screen.getByText('Button')).toBeInTheDocument();
  });
});