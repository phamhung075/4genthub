import { useEffect, useMemo, useRef, useState } from 'react';
import Markdown from '../components/Markdown';
import { collectHeadings, type TocItem } from '../lib/headingToc';
import { ApiReferenceView } from '../components/docs/ApiReferenceView';
import { API_BASE_URL } from '../config/environment';
import { applyTokens, TOKEN_VERSION, useDocTokenValues } from '../lib/docTokens';
// The generated reference tier (DOCS-PAGE.md step 1). A BUILD-TIME import, like the document
// below: the module is produced from the running code by the generator, so this page renders
// what the server advertises rather than a table someone typed. An absent module is a compile
// error at this import, which is why neither this page nor the view has a loading or a failure
// state - there is no runtime step in which the reference can be missing.
import { apiReference } from '../docs/apiReference';
// The WRITTEN half of the reference: the prose a generator cannot produce, imported raw from
// the app source tree so the reviewed file IS what renders, with no copy step. It lives
// beside the generated module it completes, not in ai_docs/public-docs. The generated
// tables beside it come from the module above, and the two are the "output plus prose" the
// spec names; this file carries no route rows and no restated counts, which is what lets the
// generated tier be the only place a route or a tool is enumerated.
import apiReferenceProse from '../docs/api-reference-prose.en.md?raw';

export function ApiDocsPage() {
  const bodyRef = useRef<HTMLElement | null>(null);
  const [toc, setToc] = useState<TocItem[]>([]);
  const tokenValues = useDocTokenValues();
  const version = tokenValues[TOKEN_VERSION];
  const source = useMemo(() => applyTokens(apiReferenceProse, tokenValues), [tokenValues]);

  // The body ELEMENT is memoized on the source, not just the html inside it: the
  // effect below calls setToc, which re-renders this component, and re-rendering
  // the markdown subtree re-applies dangerouslySetInnerHTML - which would throw
  // away the heading ids the effect has just assigned. A stable element makes
  // React skip that subtree, so the ids and the list stay in step.
  const body = useMemo(() => <Markdown source={source} />, [source]);

  // The table of contents is built from the RENDERED document (lib/headingToc).
  useEffect(() => {
    const container = bodyRef.current;
    if (!container) return;
    setToc(collectHeadings(container));
  }, [source]);

  return (
    // A div, not a main: the page renders inside the docs site's layout, which owns the main landmark.
    <div data-testid="api-docs-page">
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
    </div>
  );
}
