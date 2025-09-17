import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  TableCaption,
} from '../../../components/ui/table';
import { cn } from '../../../lib/utils';

// Mock the cn utility
jest.mock('../../../lib/utils', () => ({
  cn: jest.fn((...args: any[]) => args.filter(Boolean).join(' ')),
}));

describe('Table components', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Ensure the mock is working
    (cn as jest.Mock).mockImplementation((...args: any[]) => args.filter(Boolean).join(' '));
  });

  describe('Table', () => {
    it('renders with default props', () => {
      render(
        <Table>
          <tbody>
            <tr>
              <td>Table content</td>
            </tr>
          </tbody>
        </Table>
      );
      
      const table = screen.getByRole('table');
      expect(table).toBeInTheDocument();
      expect(table.className).toContain('theme-table');
      expect(table.className).toContain('w-full');
      expect(table.className).toContain('caption-bottom');
      expect(table.className).toContain('text-sm');
    });

    it('applies custom className', () => {
      render(<Table className="custom-table">
        <tbody><tr><td>Content</td></tr></tbody>
      </Table>);
      
      const table = screen.getByRole('table');
      expect(table.className).toContain('theme-table');
      expect(table.className).toContain('w-full');
      expect(table.className).toContain('caption-bottom');
      expect(table.className).toContain('text-sm');
      expect(table.className).toContain('custom-table');
    });

    it('forwards ref correctly', () => {
      const ref = React.createRef<HTMLTableElement>();
      render(<Table ref={ref}>
        <tbody><tr><td>Content</td></tr></tbody>
      </Table>);
      
      expect(ref.current).toBeInstanceOf(HTMLTableElement);
      expect(ref.current?.tagName).toBe('TABLE');
    });

    it('has correct display name', () => {
      expect(Table.displayName).toBe('Table');
    });
  });

  describe('TableHeader', () => {
    it('renders as thead element', () => {
      render(
        <table>
          <TableHeader>
            <tr>
              <th>Header</th>
            </tr>
          </TableHeader>
        </table>
      );
      
      const thead = document.querySelector('thead');
      expect(thead).toBeInTheDocument();
      expect(thead.className).toContain('theme-table-header');
      expect(thead.className).toContain('[&_tr]:border-b');
    });

    it('applies custom className', () => {
      render(
        <table>
          <TableHeader className="custom-header">
            <tr><th>Header</th></tr>
          </TableHeader>
        </table>
      );
      
      const thead = document.querySelector('thead');
      expect(thead.className).toContain('custom-header');
    });

    it('forwards ref correctly', () => {
      const ref = React.createRef<HTMLTableSectionElement>();
      render(
        <table>
          <TableHeader ref={ref}>
            <tr><th>Header</th></tr>
          </TableHeader>
        </table>
      );
      
      expect(ref.current).toBeInstanceOf(HTMLTableSectionElement);
      expect(ref.current?.tagName).toBe('THEAD');
    });

    it('has correct display name', () => {
      expect(TableHeader.displayName).toBe('TableHeader');
    });
  });

  describe('TableBody', () => {
    it('renders as tbody element', () => {
      render(
        <table>
          <TableBody>
            <tr>
              <td>Body content</td>
            </tr>
          </TableBody>
        </table>
      );
      
      const tbody = document.querySelector('tbody');
      expect(tbody).toBeInTheDocument();
      expect(tbody.className).toContain('[&_tr:last-child]:border-0');
    });

    it('applies custom className', () => {
      render(
        <table>
          <TableBody className="custom-body">
            <tr><td>Content</td></tr>
          </TableBody>
        </table>
      );
      
      const tbody = document.querySelector('tbody');
      expect(tbody.className).toContain('custom-body');
    });

    it('has correct display name', () => {
      expect(TableBody.displayName).toBe('TableBody');
    });
  });

  describe('TableRow', () => {
    it('renders as tr element', () => {
      render(
        <table>
          <tbody>
            <TableRow>
              <td>Row content</td>
            </TableRow>
          </tbody>
        </table>
      );
      
      const row = screen.getByRole('row');
      expect(row).toBeInTheDocument();
      expect(row.className).toContain('theme-table-row');
      expect(row.className).toContain('data-[state=selected]:bg-background-active');
    });

    it('applies custom className', () => {
      render(
        <table>
          <tbody>
            <TableRow className="custom-row">
              <td>Content</td>
            </TableRow>
          </tbody>
        </table>
      );
      
      const row = screen.getByRole('row');
      expect(row.className).toContain('custom-row');
    });

    it('handles data-state attribute', () => {
      render(
        <table>
          <tbody>
            <TableRow data-state="selected">
              <td>Selected row</td>
            </TableRow>
          </tbody>
        </table>
      );
      
      const row = screen.getByRole('row');
      expect(row).toHaveAttribute('data-state', 'selected');
    });

    it('has correct display name', () => {
      expect(TableRow.displayName).toBe('TableRow');
    });
  });

  describe('TableHead', () => {
    it('renders as th element', () => {
      render(
        <table>
          <thead>
            <tr>
              <TableHead>Column Header</TableHead>
            </tr>
          </thead>
        </table>
      );
      
      const th = screen.getByRole('columnheader');
      expect(th).toHaveTextContent('Column Header');
      expect(th.className).toContain('theme-table-cell');
      expect(th.className).toContain('h-12');
      expect(th.className).toContain('text-left');
      expect(th.className).toContain('align-middle');
      expect(th.className).toContain('font-medium');
      expect(th.className).toContain('text-base-secondary');
      expect(th.className).toContain('[&:has([role=checkbox])]:pr-0');
    });

    it('applies custom className', () => {
      render(
        <table>
          <thead>
            <tr>
              <TableHead className="custom-head">Header</TableHead>
            </tr>
          </thead>
        </table>
      );
      
      const th = screen.getByRole('columnheader');
      expect(th.className).toContain('custom-head');
    });

    it('passes through th attributes', () => {
      render(
        <table>
          <thead>
            <tr>
              <TableHead scope="col" colSpan={2}>Header</TableHead>
            </tr>
          </thead>
        </table>
      );
      
      const th = screen.getByRole('columnheader');
      expect(th).toHaveAttribute('scope', 'col');
      expect(th).toHaveAttribute('colspan', '2');
    });

    it('has correct display name', () => {
      expect(TableHead.displayName).toBe('TableHead');
    });
  });

  describe('TableCell', () => {
    it('renders as td element', () => {
      render(
        <table>
          <tbody>
            <tr>
              <TableCell>Cell content</TableCell>
            </tr>
          </tbody>
        </table>
      );
      
      const td = screen.getByRole('cell');
      expect(td).toHaveTextContent('Cell content');
      expect(td.className).toContain('theme-table-cell');
      expect(td.className).toContain('align-middle');
      expect(td.className).toContain('[&:has([role=checkbox])]:pr-0');
    });

    it('applies custom className', () => {
      render(
        <table>
          <tbody>
            <tr>
              <TableCell className="custom-cell">Content</TableCell>
            </tr>
          </tbody>
        </table>
      );
      
      const td = screen.getByRole('cell');
      expect(td.className).toContain('custom-cell');
    });

    it('passes through td attributes', () => {
      render(
        <table>
          <tbody>
            <tr>
              <TableCell colSpan={3} rowSpan={2}>Cell</TableCell>
            </tr>
          </tbody>
        </table>
      );
      
      const td = screen.getByRole('cell');
      expect(td).toHaveAttribute('colspan', '3');
      expect(td).toHaveAttribute('rowspan', '2');
    });

    it('has correct display name', () => {
      expect(TableCell.displayName).toBe('TableCell');
    });
  });

  describe('TableCaption', () => {
    it('renders as caption element', () => {
      render(
        <table>
          <TableCaption>Table caption text</TableCaption>
          <tbody>
            <tr>
              <td>Content</td>
            </tr>
          </tbody>
        </table>
      );
      
      const caption = screen.getByText('Table caption text');
      expect(caption.tagName).toBe('CAPTION');
      expect(caption.className).toContain('mt-4');
      expect(caption.className).toContain('text-sm');
      expect(caption.className).toContain('text-base-secondary');
    });

    it('applies custom className', () => {
      render(
        <table>
          <TableCaption className="custom-caption">Caption</TableCaption>
          <tbody><tr><td>Content</td></tr></tbody>
        </table>
      );
      
      const caption = screen.getByText('Caption');
      expect(caption.className).toContain('custom-caption');
    });

    it('has correct display name', () => {
      expect(TableCaption.displayName).toBe('TableCaption');
    });
  });

  describe('Integration', () => {
    it('renders complete table structure', () => {
      render(
        <Table>
          <TableCaption>A list of recent transactions</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Amount</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>2024-01-01</TableCell>
              <TableCell>Purchase</TableCell>
              <TableCell>$100.00</TableCell>
            </TableRow>
            <TableRow>
              <TableCell>2024-01-02</TableCell>
              <TableCell>Refund</TableCell>
              <TableCell>-$50.00</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );
      
      expect(screen.getByRole('table')).toBeInTheDocument();
      expect(screen.getByText('A list of recent transactions')).toBeInTheDocument();
      expect(screen.getAllByRole('columnheader')).toHaveLength(3);
      expect(screen.getAllByRole('row')).toHaveLength(3); // 1 header + 2 body rows
      expect(screen.getAllByRole('cell')).toHaveLength(6);
    });

    it('handles table with checkbox cells', () => {
      render(
        <Table>
          <TableBody>
            <TableRow>
              <TableCell>
                <input type="checkbox" role="checkbox" />
              </TableCell>
              <TableCell>Regular cell</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );
      
      const checkbox = screen.getByRole('checkbox');
      expect(checkbox).toBeInTheDocument();
      
      // The cell containing checkbox should have special styling
      const checkboxCell = checkbox.closest('td');
      expect(checkboxCell.className).toContain('[&:has([role=checkbox])]:pr-0');
    });

    it('calls cn utility with correct arguments', () => {
      render(
        <Table className="table-class">
          <TableCaption className="caption-class">Caption</TableCaption>
          <TableHeader className="header-class">
            <TableRow className="row-class">
              <TableHead className="head-class">Header</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody className="body-class">
            <TableRow className="row-class2">
              <TableCell className="cell-class">Cell</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );
      
      expect(cn).toHaveBeenCalledWith('theme-table w-full caption-bottom text-sm', 'table-class');
      expect(cn).toHaveBeenCalledWith('mt-4 text-sm text-base-secondary', 'caption-class');
      expect(cn).toHaveBeenCalledWith('theme-table-header [&_tr]:border-b', 'header-class');
      expect(cn).toHaveBeenCalledWith('theme-table-row data-[state=selected]:bg-background-active', 'row-class');
      expect(cn).toHaveBeenCalledWith('theme-table-cell h-12 text-left align-middle font-medium text-base-secondary [&:has([role=checkbox])]:pr-0', 'head-class');
      expect(cn).toHaveBeenCalledWith('[&_tr:last-child]:border-0', 'body-class');
      expect(cn).toHaveBeenCalledWith('theme-table-row data-[state=selected]:bg-background-active', 'row-class2');
      expect(cn).toHaveBeenCalledWith('theme-table-cell align-middle [&:has([role=checkbox])]:pr-0', 'cell-class');
    });
  });
});