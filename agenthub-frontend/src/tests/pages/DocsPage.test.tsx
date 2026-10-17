import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ThemeProvider } from '../../contexts/ThemeContext';
import { DocsPage } from '../../pages/DocsPage';

function renderAt(path: string) {
  return render(
    <ThemeProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/docs/*" element={<DocsPage />} />
        </Routes>
      </MemoryRouter>
    </ThemeProvider>,
  );
}

describe('DocsPage', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
    window.scrollTo = vi.fn();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('opens the first page at /docs and lists every subject in the sidebar', async () => {
    renderAt('/docs');

    const body = await screen.findByTestId('docs-body');
    expect(body.querySelector('h1')?.textContent).toBe('Overview');
    const sidebar = screen.getByTestId('docs-sidebar');
    expect(sidebar.textContent).toContain('Quickstart');
    expect(sidebar.textContent).toContain('API reference');
    expect(sidebar.querySelector('[aria-current="page"]')?.textContent).toBe('Overview');
  });

  it('rewrites relative page links to routes and follows them inside the app', async () => {
    renderAt('/docs/quickstart/overview');

    const body = await screen.findByTestId('docs-body');
    const link = Array.from(body.querySelectorAll('a')).find((a) => a.textContent === 'Prerequisites');
    expect(link?.getAttribute('href')).toBe('/docs/quickstart/prerequisites');

    fireEvent.click(link as HTMLAnchorElement);
    expect((await screen.findByTestId('docs-body')).querySelector('h1')?.textContent).toBe('Prerequisites');
  });

  it('renders the API reference inside the same layout at /docs/api-reference', async () => {
    renderAt('/docs/api-reference');

    expect(await screen.findByTestId('api-docs-page')).toBeInTheDocument();
    expect(screen.getByTestId('docs-sidebar').textContent).toContain('API reference');
  });

  it('shows not found for a path with no page, and keeps the sidebar', () => {
    renderAt('/docs/quickstart/no-such-page');

    expect(screen.getByTestId('docs-not-found')).toBeInTheDocument();
    expect(screen.getByTestId('docs-sidebar')).toBeInTheDocument();
  });
});
