import { useMemo } from 'react';
import { toSanitizedHtml } from '../lib/markdownHtml';

interface MarkdownProps {
  /** Markdown source. Already-sanitized HTML is injected, never raw source. */
  source: string;
  className?: string;
}

/**
 * Render a markdown document. The sanitizer policy lives in lib/markdownHtml, so
 * this component holds no policy of its own.
 */
export default function Markdown({ source, className }: MarkdownProps) {
  const html = useMemo(() => toSanitizedHtml(source), [source]);
  return (
    <div
      className={className ? `markdown-body ${className}` : 'markdown-body'}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
