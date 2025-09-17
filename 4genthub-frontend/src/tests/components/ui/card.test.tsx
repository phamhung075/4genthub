import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../../components/ui/card';
import { cn } from '../../../lib/utils';

// Mock the cn utility
jest.mock('../../../lib/utils', () => ({
  cn: jest.fn((...args: any[]) => args.filter(Boolean).join(' ')),
}));

describe('Card components', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Ensure the mock is working
    (cn as jest.Mock).mockImplementation((...args: any[]) => args.filter(Boolean).join(' '));
  });

  describe('Card', () => {
    it('renders with default props', () => {
      render(<Card>Card content</Card>);
      
      const card = screen.getByText('Card content');
      expect(card).toBeInTheDocument();
      expect(card.className).toContain('theme-card');
    });

    it('applies custom className', () => {
      render(<Card className="custom-card">Card content</Card>);
      
      const card = screen.getByText('Card content');
      expect(card.className).toContain('theme-card');
      expect(card.className).toContain('custom-card');
    });

    it('forwards ref correctly', () => {
      const ref = React.createRef<HTMLDivElement>();
      render(<Card ref={ref}>Card content</Card>);
      
      expect(ref.current).toBeInstanceOf(HTMLDivElement);
      expect(ref.current?.textContent).toBe('Card content');
    });

    it('passes through HTML div attributes', () => {
      render(
        <Card 
          id="test-card" 
          data-testid="custom-card"
          role="article"
          aria-label="Test Card"
        >
          Card content
        </Card>
      );
      
      const card = screen.getByRole('article');
      expect(card).toHaveAttribute('id', 'test-card');
      expect(card).toHaveAttribute('data-testid', 'custom-card');
      expect(card).toHaveAttribute('aria-label', 'Test Card');
    });

    it('has correct display name', () => {
      expect(Card.displayName).toBe('Card');
    });
  });

  describe('CardHeader', () => {
    it('renders with default props', () => {
      render(<CardHeader>Header content</CardHeader>);
      
      const header = screen.getByText('Header content');
      expect(header).toBeInTheDocument();
      expect(header.className).toContain('flex');
      expect(header.className).toContain('flex-col');
      expect(header.className).toContain('space-y-1.5');
      expect(header.className).toContain('p-6');
    });

    it('applies custom className', () => {
      render(<CardHeader className="custom-header">Header content</CardHeader>);
      
      const header = screen.getByText('Header content');
      expect(header.className).toContain('flex');
      expect(header.className).toContain('flex-col');
      expect(header.className).toContain('space-y-1.5');
      expect(header.className).toContain('p-6');
      expect(header.className).toContain('custom-header');
    });

    it('passes through HTML div attributes', () => {
      render(
        <CardHeader 
          id="test-header"
          data-testid="card-header"
        >
          Header content
        </CardHeader>
      );
      
      const header = screen.getByTestId('card-header');
      expect(header).toHaveAttribute('id', 'test-header');
    });
  });

  describe('CardTitle', () => {
    it('renders with children', () => {
      render(<CardTitle>Card Title</CardTitle>);
      
      const title = screen.getByRole('heading', { level: 3 });
      expect(title).toHaveTextContent('Card Title');
      expect(title.className).toContain('font-semibold');
      expect(title.className).toContain('leading-none');
      expect(title.className).toContain('tracking-tight');
      expect(title.className).toContain('text-lg');
      expect(title.className).toContain('md:text-xl');
    });

    it('renders screen reader text when no children provided', () => {
      render(<CardTitle />);
      
      const title = screen.getByRole('heading', { level: 3 });
      const srText = screen.getByText('Card title');
      expect(srText).toHaveClass('sr-only');
    });

    it('applies custom className', () => {
      render(<CardTitle className="custom-title">Title</CardTitle>);
      
      const title = screen.getByRole('heading', { level: 3 });
      expect(title.className).toContain('font-semibold');
      expect(title.className).toContain('leading-none');
      expect(title.className).toContain('tracking-tight');
      expect(title.className).toContain('text-lg');
      expect(title.className).toContain('md:text-xl');
      expect(title.className).toContain('custom-title');
    });

    it('passes through HTML heading attributes', () => {
      render(
        <CardTitle 
          id="test-title"
          data-testid="card-title"
        >
          Title
        </CardTitle>
      );
      
      const title = screen.getByRole('heading', { level: 3 });
      expect(title).toHaveAttribute('id', 'test-title');
      expect(title).toHaveAttribute('data-testid', 'card-title');
    });
  });

  describe('CardDescription', () => {
    it('renders with children', () => {
      render(<CardDescription>Card description text</CardDescription>);
      
      const description = screen.getByText('Card description text');
      expect(description).toBeInTheDocument();
      expect(description.tagName).toBe('P');
      expect(description.className).toContain('text-sm');
      expect(description.className).toContain('text-base-secondary');
    });

    it('applies custom className', () => {
      render(<CardDescription className="custom-description">Description</CardDescription>);
      
      const description = screen.getByText('Description');
      expect(description.className).toContain('text-sm');
      expect(description.className).toContain('text-base-secondary');
      expect(description.className).toContain('custom-description');
    });

    it('passes through HTML paragraph attributes', () => {
      render(
        <CardDescription 
          id="test-description"
          data-testid="card-description"
        >
          Description
        </CardDescription>
      );
      
      const description = screen.getByTestId('card-description');
      expect(description).toHaveAttribute('id', 'test-description');
    });

    it('renders without children', () => {
      render(<CardDescription />);
      
      const description = document.querySelector('p');
      expect(description).toBeInTheDocument();
      expect(description.className).toContain('text-sm');
      expect(description.className).toContain('text-base-secondary');
    });
  });

  describe('CardContent', () => {
    it('renders with default props', () => {
      render(<CardContent>Content text</CardContent>);
      
      const content = screen.getByText('Content text');
      expect(content).toBeInTheDocument();
      expect(content.className).toContain('p-6');
      expect(content.className).toContain('pt-0');
    });

    it('applies custom className', () => {
      render(<CardContent className="custom-content">Content</CardContent>);
      
      const content = screen.getByText('Content');
      expect(content.className).toContain('p-6');
      expect(content.className).toContain('pt-0');
      expect(content.className).toContain('custom-content');
    });

    it('passes through HTML div attributes', () => {
      render(
        <CardContent 
          id="test-content"
          data-testid="card-content"
        >
          Content
        </CardContent>
      );
      
      const content = screen.getByTestId('card-content');
      expect(content).toHaveAttribute('id', 'test-content');
    });
  });

  describe('Integration', () => {
    it('renders complete card structure', () => {
      render(
        <Card>
          <CardHeader>
            <CardTitle>Test Card</CardTitle>
            <CardDescription>This is a test card</CardDescription>
          </CardHeader>
          <CardContent>
            <p>Card body content</p>
          </CardContent>
        </Card>
      );
      
      expect(screen.getByRole('heading', { name: 'Test Card' })).toBeInTheDocument();
      expect(screen.getByText('This is a test card')).toBeInTheDocument();
      expect(screen.getByText('Card body content')).toBeInTheDocument();
    });

    it('calls cn utility with correct arguments', () => {
      render(
        <Card className="card-class">
          <CardHeader className="header-class">
            <CardTitle className="title-class">Title</CardTitle>
            <CardDescription className="desc-class">Description</CardDescription>
          </CardHeader>
          <CardContent className="content-class">Content</CardContent>
        </Card>
      );
      
      expect(cn).toHaveBeenCalledWith('theme-card', 'card-class');
      expect(cn).toHaveBeenCalledWith('flex flex-col space-y-1.5 p-6', 'header-class');
      expect(cn).toHaveBeenCalledWith('font-semibold leading-none tracking-tight text-lg md:text-xl', 'title-class');
      expect(cn).toHaveBeenCalledWith('text-sm text-base-secondary', 'desc-class');
      expect(cn).toHaveBeenCalledWith('p-6 pt-0', 'content-class');
    });
  });
});