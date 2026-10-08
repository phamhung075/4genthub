import { useEffect, useMemo, useRef, useState } from 'react';
import Markdown from '../components/Markdown';
import { ApiReferenceView } from '../components/docs/ApiReferenceView';
import { API_BASE_URL, MCP_URL } from '../config/environment';
// The generated reference tier (DOCS-PAGE.md step 1). A BUILD-TIME import, like the document
// below: the module is produced from the running code by the generator, so this page renders
// what the server advertises rather than a table someone typed. An absent module is a compile
// error at this import, which is why neither this page nor the view has a loading or a failure
// state - there is no runtime step in which the reference can be missing.
import { apiReference } from '../docs/apiReference';
// The WRITTEN half of the reference: the prose a generator cannot produce, imported raw from
// the app source tree so the reviewed file IS what renders, with no copy step. It must live
// inside this tree because the production image copies only agenthub-frontend. The generated
// tables beside it come from the module above, and the two are the "output plus prose" the
// spec names; this file carries no route rows and no restated counts, which is what lets the
// generated tier be the only place a route or a tool is enumerated.
import apiReferenceProse from '../docs/api-reference-prose.en.md?raw';

interface TocItem {
  id: string;
  text: string;
  level: 2 | 3;
}

/**
 * Tokens the document may carry. They are substituted at render time so any
 * deployment documents itself. A token whose value cannot be obtained is LEFT
 * VISIBLE: an empty string looks like a styling bug, a visible token is a
 * finding. Unknown tokens are untouched, so braces are safe for nothing else -
 * which is also the agreement with whoever writes the document.
 */
const TOKEN_API_ORIGIN = 'API_ORIGIN';
const TOKEN_MCP_URL = 'MCP_URL';
const TOKEN_VERSION = 'VERSION';

/**
 * The MCP endpoint comes from config (VITE_MCP_URL, see config/environment.ts).
 * It is unset by default because this repository is not a deployment, and an
 * unset value leaves {{MCP_URL}} visible rather than rendering an empty string.
 */

/** Replace {{TOKEN}} with a value, leaving the token when there is no value. */
export function applyTokens(source: string, values: Record<string, string | undefined>): string {
  return source.replace(/\{\{\s*([A-Z_]+)\s*\}\}/g, (match, name: string) => {
    const value = values[name];
    return value === undefined || value === '' ? match : value;
  });
}

/** Heading text to an ASCII id, matching how anchors are written by hand. */
export function slugifyHeading(text: string): string {
  return (
    text
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'section'
  );
}

export function ApiDocsPage() {
  const bodyRef = useRef<HTMLElement | null>(null);
  const [toc, setToc] = useState<TocItem[]>([]);
  const [version, setVersion] = useState<string | undefined>(undefined);

  // The version comes from /health at runtime, never from a build-time constant.
  useEffect(() => {
    let cancelled = false;
    const readVersion = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (!response.ok) return;
        const data = await response.json();
        if (!cancelled && data && typeof data.version === 'string') {
          setVersion(data.version);
        }
      } catch {
        // Unreachable backend: {{VERSION}} stays visible rather than showing a lie.
      }
    };
    void readVersion();
    return () => {
      cancelled = true;
    };
  }, []);

  const source = useMemo(
    () =>
      applyTokens(apiReferenceProse, {
        [TOKEN_API_ORIGIN]: API_BASE_URL,
        [TOKEN_MCP_URL]: MCP_URL,
        [TOKEN_VERSION]: version,
      }),
    [version],
  );

  // The body ELEMENT is memoized on the source, not just the html inside it: the
  // effect below calls setToc, which re-renders this component, and re-rendering
  // the markdown subtree re-applies dangerouslySetInnerHTML - which would throw
  // away the heading ids the effect has just assigned. A stable element makes
  // React skip that subtree, so the ids and the list stay in step.
  const body = useMemo(() => <Markdown source={source} />, [source]);

  // The table of contents is built from the RENDERED document, so it cannot
  // drift from the markdown: a heading added to the file appears here with no
  // other edit, and duplicate heading text gets -1/-2 suffixes.
  useEffect(() => {
    const container = bodyRef.current;
    if (!container) return;
    const seen: Record<string, number> = {};
    const items = Array.from(container.querySelectorAll('h2, h3')).map((heading) => {
      const base = slugifyHeading(heading.textContent ?? '');
      const count = seen[base] ?? 0;
      seen[base] = count + 1;
      const id = count ? `${base}-${count}` : base;
      heading.id = id;
      return {
        id,
        text: heading.textContent ?? '',
        level: heading.tagName === 'H2' ? (2 as const) : (3 as const),
      };
    });
    setToc(items);
  }, [source]);

  return (
    <main className="container mx-auto px-4 py-8" data-testid="api-docs-page">
      <div className="mb-6 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
        <span className="text-text-tertiary">Base URL</span>
        <code className="rounded bg-surface-hover px-2 py-1" data-testid="api-docs-origin">
          {API_BASE_URL}
        </code>
        <span className="text-text-tertiary">Version</span>
        <code className="rounded bg-surface-hover px-2 py-1" data-testid="api-docs-version">
          {version ?? `{{${TOKEN_VERSION}}}`}
        </code>
      </div>

      {/* THE GENERATED REFERENCE TIER, FIRST, because it is the tier produced FROM THE CODE and
          cannot go stale the way a hand-written table does: every mounted route and every MCP
          tool, read out of the running server by the generator. The view takes the reference as
          a REQUIRED prop, so there is no loading state and no failure state to write here - an
          absent reference is a compile error at the import above, not a runtime branch. */}
      <section
        className="mb-10"
        aria-labelledby="api-docs-generated-reference"
        data-testid="api-docs-reference"
      >
        <h2
          id="api-docs-generated-reference"
          className="mb-3 text-xl font-semibold text-base-primary"
        >
          Generated reference
        </h2>
        <ApiReferenceView reference={apiReference} />
      </section>

      <div className="flex flex-col gap-8 lg:flex-row">
        {toc.length > 0 && (
          <nav
            className="lg:w-64 lg:shrink-0"
            aria-label="On this page"
            data-testid="api-docs-toc"
          >
            <span className="mb-2 block text-xs font-medium uppercase tracking-wide text-text-tertiary">
              On this page
            </span>
            <ul className="space-y-1 text-sm">
              {toc.map((item) => (
                <li key={item.id} className={item.level === 3 ? 'pl-4' : undefined}>
                  <a className="hover:underline" href={`#${item.id}`}>
                    {item.text}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
        )}

        <article className="min-w-0 flex-1" ref={bodyRef} data-testid="api-docs-body">
          {body}
        </article>
      </div>
    </main>
  );
}
