import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState, type MouseEvent } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';
import { ChevronLeft, ChevronRight, Menu, Moon, Sun, X } from 'lucide-react';
import Markdown from '../components/Markdown';
import { useTheme } from '../contexts/ThemeContext';
import { DOCS_BASE, docAssets, docSections, resolveDocHref, type DocPage } from '../docs/docsSite';
import { applyTokens, useDocTokenValues } from '../lib/docTokens';
import { collectHeadings, type TocItem } from '../lib/headingToc';
import { renderMermaidBlocks } from '../lib/mermaidDiagrams';

// The API reference carries the generated route and tool tables, so it loads only when opened.
const ApiDocsPage = lazy(() => import('./ApiDocsPage').then((m) => ({ default: m.ApiDocsPage })));

const API_REFERENCE_ID = 'api-reference';

interface NavEntry {
  id: string;
  title: string;
}

interface NavGroup {
  title: string;
  entries: NavEntry[];
}

// The sidebar: one group per ai_docs/public-docs subject, then the API reference, which is
// rendered from the generated module rather than from that tree.
const NAV_GROUPS: NavGroup[] = [
  ...docSections.map((section) => ({
    title: section.title,
    entries: section.pages.map(({ id, title }) => ({ id, title })),
  })),
  { title: 'API reference', entries: [{ id: API_REFERENCE_ID, title: 'REST and MCP reference' }] },
];

const NAV_ORDER: NavEntry[] = NAV_GROUPS.flatMap((group) => group.entries);

const PAGES_BY_ID = new Map<string, DocPage>(docSections.flatMap((section) => section.pages).map((page) => [page.id, page]));

function DocsSidebar({ activeId, onNavigate }: { activeId: string; onNavigate: () => void }) {
  return (
    <nav aria-label="Documentation" data-testid="docs-sidebar" className="space-y-6 text-sm">
      {NAV_GROUPS.map((group) => (
        <div key={group.title}>
          <span className="mb-2 block px-3 text-xs font-semibold uppercase tracking-wide text-text-tertiary">
            {group.title}
          </span>
          <ul className="space-y-0.5">
            {group.entries.map((entry) => {
              const active = entry.id === activeId;
              return (
                <li key={entry.id}>
                  <Link
                    to={`${DOCS_BASE}/${entry.id}`}
                    onClick={onNavigate}
                    aria-current={active ? 'page' : undefined}
                    className={`block rounded-md px-3 py-1.5 transition-colors ${
                      active
                        ? 'bg-primary/10 font-medium text-primary'
                        : 'text-base-secondary hover:bg-surface-hover hover:text-base-primary'
                    }`}
                  >
                    {entry.title}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}

function DocArticle({ page }: { page: DocPage }) {
  const navigate = useNavigate();
  const { theme } = useTheme();
  const bodyRef = useRef<HTMLElement | null>(null);
  const [toc, setToc] = useState<TocItem[]>([]);
  const tokenValues = useDocTokenValues();
  const source = useMemo(() => applyTokens(page.source, tokenValues), [page.source, tokenValues]);
  const rewriteUrl = useCallback((url: string) => resolveDocHref(page.id, url, docAssets), [page.id]);

  // Memoized for the same reason as on the API reference page: setToc re-renders this component,
  // and a new markdown element would re-inject the HTML and drop the heading ids just assigned.
  const body = useMemo(() => <Markdown source={source} rewriteUrl={rewriteUrl} />, [source, rewriteUrl]);

  useEffect(() => {
    const container = bodyRef.current;
    if (!container) return;
    setToc(collectHeadings(container));
  }, [body]);

  useEffect(() => {
    const container = bodyRef.current;
    if (!container) return;
    let cancelled = false;
    void renderMermaidBlocks(container, theme === 'dark', () => cancelled);
    return () => {
      cancelled = true;
    };
  }, [body, theme]);

  // A resolved link between pages is a plain <a href="/docs/..."> inside injected HTML, so the
  // router never sees it; this hands same-site paths to the router instead of reloading the app.
  const followInternalLink = (event: MouseEvent<HTMLElement>) => {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey) return;
    const link = (event.target as HTMLElement).closest('a');
    const href = link?.getAttribute('href');
    if (!link || !href || !href.startsWith('/') || link.target === '_blank') return;
    event.preventDefault();
    navigate(href);
  };

  return (
    <div className="flex gap-10">
      <article
        className="min-w-0 flex-1"
        ref={bodyRef}
        onClick={followInternalLink}
        data-testid="docs-body"
      >
        {body}
      </article>
      {toc.length > 0 && (
        <nav aria-label="On this page" data-testid="docs-toc" className="hidden w-56 shrink-0 xl:block">
          <div className="sticky top-24">
            <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-text-tertiary">
              On this page
            </span>
            <ul className="space-y-1 text-sm">
              {toc.map((item) => (
                <li key={item.id} className={item.level === 3 ? 'pl-3' : undefined}>
                  <a className="text-base-secondary hover:text-primary" href={`#${item.id}`}>
                    {item.text}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </nav>
      )}
    </div>
  );
}

function PagerLinks({ activeId }: { activeId: string }) {
  const index = NAV_ORDER.findIndex((entry) => entry.id === activeId);
  if (index < 0) return null;
  const previous = NAV_ORDER[index - 1];
  const next = NAV_ORDER[index + 1];
  return (
    <div className="mt-12 grid gap-4 border-t border-surface-border pt-6 sm:grid-cols-2" data-testid="docs-pager">
      {previous ? (
        <Link
          to={`${DOCS_BASE}/${previous.id}`}
          className="group rounded-lg border border-surface-border p-4 hover:border-primary"
        >
          <span className="flex items-center gap-1 text-xs text-text-tertiary">
            <ChevronLeft className="h-3 w-3" /> Previous
          </span>
          <span className="mt-1 block font-medium group-hover:text-primary">{previous.title}</span>
        </Link>
      ) : (
        <span />
      )}
      {next && (
        <Link
          to={`${DOCS_BASE}/${next.id}`}
          className="group rounded-lg border border-surface-border p-4 text-right hover:border-primary"
        >
          <span className="flex items-center justify-end gap-1 text-xs text-text-tertiary">
            Next <ChevronRight className="h-3 w-3" />
          </span>
          <span className="mt-1 block font-medium group-hover:text-primary">{next.title}</span>
        </Link>
      )}
    </div>
  );
}

export function DocsPage() {
  const activeId = (useParams()['*'] ?? '').replace(/\/+$/, '');
  const { theme, toggleTheme } = useTheme();
  const [menuOpen, setMenuOpen] = useState(false);

  // A page change starts at the top, as a new document would.
  useEffect(() => {
    if (!window.location.hash) window.scrollTo(0, 0);
  }, [activeId]);

  if (!activeId) return <Navigate to={`${DOCS_BASE}/${NAV_ORDER[0].id}`} replace />;

  const page = PAGES_BY_ID.get(activeId);
  let content;
  if (activeId === API_REFERENCE_ID) {
    content = (
      <Suspense fallback={<p className="text-text-tertiary">Loading the API reference…</p>}>
        <ApiDocsPage />
      </Suspense>
    );
  } else if (page) {
    content = <DocArticle key={page.id} page={page} />;
  } else {
    content = (
      <div data-testid="docs-not-found">
        <h1 className="mb-4 text-2xl font-bold">Page not found</h1>
        <p className="text-base-secondary">
          No page is published at <code>{`${DOCS_BASE}/${activeId}`}</code>. Pick a page from the sidebar.
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-base text-base-primary" data-testid="docs-page">
      <header className="sticky top-0 z-30 border-b border-surface-border bg-base">
        <div className="mx-auto flex h-14 max-w-screen-2xl items-center gap-3 px-4">
          <button
            type="button"
            className="rounded-md p-2 hover:bg-surface-hover lg:hidden"
            onClick={() => setMenuOpen((open) => !open)}
            aria-label={menuOpen ? 'Close the documentation menu' : 'Open the documentation menu'}
            aria-expanded={menuOpen}
          >
            {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
          <Link to="/" className="font-semibold">
            4genthub
          </Link>
          <Link to={DOCS_BASE} className="text-text-tertiary hover:text-primary">
            Docs
          </Link>
          <div className="ml-auto flex items-center gap-2">
            <Link to="/dashboard" className="rounded-md px-3 py-1.5 text-sm hover:bg-surface-hover">
              Dashboard
            </Link>
            <button
              type="button"
              onClick={toggleTheme}
              className="rounded-md p-2 hover:bg-surface-hover"
              aria-label={theme === 'dark' ? 'Light mode' : 'Dark mode'}
            >
              {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-screen-2xl">
        <aside
          className={`${
            menuOpen ? 'block' : 'hidden'
          } fixed inset-x-0 bottom-0 top-14 z-20 overflow-y-auto bg-base p-4 lg:sticky lg:block lg:h-[calc(100vh-3.5rem)] lg:w-72 lg:shrink-0 lg:border-r lg:border-surface-border`}
        >
          <DocsSidebar activeId={activeId} onNavigate={() => setMenuOpen(false)} />
        </aside>

        <main className="min-w-0 flex-1 px-4 py-8 sm:px-8 lg:px-12">
          <div className="mx-auto max-w-5xl">
            {content}
            <PagerLinks activeId={activeId} />
          </div>
        </main>
      </div>
    </div>
  );
}
