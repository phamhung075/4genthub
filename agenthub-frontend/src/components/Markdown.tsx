import { useMemo } from 'react';
import { rewriteUrls, toSanitizedHtml } from '../lib/markdownHtml';

interface MarkdownProps {
  /** Markdown source. Already-sanitized HTML is injected, never raw source. */
  source: string;
  className?: string;
  /** Maps each link href and image src, for documents whose relative paths need resolving. */
  rewriteUrl?: (url: string) => string;
}

/**
 * Render a markdown document. The sanitizer policy lives in lib/markdownHtml, so
 * this component holds no policy of its own.
 */
export default function Markdown({ source, className, rewriteUrl }: MarkdownProps) {
  const html = useMemo(() => {
    const sanitized = toSanitizedHtml(source);
    return rewriteUrl ? rewriteUrls(sanitized, rewriteUrl) : sanitized;
  }, [source, rewriteUrl]);
  return (
    <div
      className={className ? `markdown-body ${className}` : 'markdown-body'}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
