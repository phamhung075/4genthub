/**
 * ModuleContentView - one module's content string, read as a human.
 *
 * A module's `content` is free text whose shape depends on its kind: a skill
 * block is one JSON line carrying the whole SKILL.md inside `content`, so the
 * old raw <pre> showed escaped `\n` and a single unreadable line. This renders
 * the parsed value as labelled key/value sections (a string value keeps its own
 * line breaks) and offers the exact stored string behind a Raw toggle for
 * copy and debug.
 *
 * Content that is not JSON keeps the plain reading, and empty content says so
 * rather than drawing an empty pane.
 *
 * @module components/seats/ModuleContentView
 */

import React, { useMemo, useState } from 'react';
import { Button } from '../ui/button';

const SCROLL = 'max-h-64 overflow-auto rounded bg-muted p-3 text-xs';
const PLAIN = `${SCROLL} whitespace-pre-wrap`;
const KEY = 'text-[11px] font-medium uppercase tracking-wide text-muted-foreground';

/** `value` is present only when JSON.parse accepted the whole string. */
type Parsed = { ok: true; value: unknown } | { ok: false };

const Scalar: React.FC<{ value: string | number | boolean | null }> = ({ value }) => {
  if (value === null) return <span className="italic text-muted-foreground">null</span>;
  if (typeof value === 'string') return <span className="whitespace-pre-wrap break-words">{value}</span>;
  return <code className="font-mono">{String(value)}</code>;
};

/**
 * One JSON value as nested sections. Objects become a key/value list, arrays a
 * bulleted list, and every level indents under a left rule so depth is visible
 * without reading braces.
 */
const JsonNode: React.FC<{ value: unknown }> = ({ value }) => {
  if (value === null || typeof value !== 'object') {
    return <Scalar value={value as string | number | boolean | null} />;
  }

  if (Array.isArray(value)) {
    return (
      <ul className="list-disc space-y-1 pl-4">
        {value.map((entry, index) => (
          <li key={index}>
            <JsonNode value={entry} />
          </li>
        ))}
      </ul>
    );
  }

  const entries = Object.entries(value as Record<string, unknown>);
  // An empty object still needs a mark; a blank dd would read as a failed read.
  if (entries.length === 0) return <span className="italic text-muted-foreground">{'{}'}</span>;

  return (
    <dl className="space-y-2 border-l border-border/60 pl-3">
      {entries.map(([key, entry]) => (
        <div key={key} className="space-y-0.5">
          <dt className={KEY}>{key}</dt>
          <dd className="min-w-0">
            <JsonNode value={entry} />
          </dd>
        </div>
      ))}
    </dl>
  );
};

export const ModuleContentView: React.FC<{ content: string }> = ({ content }) => {
  const [raw, setRaw] = useState(false);
  const parsed = useMemo<Parsed>(() => {
    try {
      return { ok: true, value: JSON.parse(content) };
    } catch {
      return { ok: false };
    }
  }, [content]);

  if (content.trim() === '') {
    return <p className="text-xs text-muted-foreground">This module version carries no content.</p>;
  }

  if (!parsed.ok) {
    return <pre className={PLAIN}>{content}</pre>;
  }

  return (
    <div className="space-y-2">
      <div className="flex justify-end gap-1">
        <Button
          variant={raw ? 'ghost' : 'secondary'}
          size="sm"
          aria-pressed={!raw}
          onClick={() => setRaw(false)}
        >
          Formatted
        </Button>
        <Button variant={raw ? 'secondary' : 'ghost'} size="sm" aria-pressed={raw} onClick={() => setRaw(true)}>
          Raw
        </Button>
      </div>
      {raw ? (
        <pre className={PLAIN}>{content}</pre>
      ) : (
        <div className={SCROLL}>
          <JsonNode value={parsed.value} />
        </div>
      )}
    </div>
  );
};
