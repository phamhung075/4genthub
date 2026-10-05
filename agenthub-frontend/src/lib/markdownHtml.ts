import { marked } from 'marked';
import DOMPurify from 'dompurify';

// ONE place owns the markdown -> sanitized HTML pipeline, so every consumer of a
// rendered document shares the same options and the same sanitizer policy.
//
// Modelled on the reference implementation in markdown-extract-service
// (app/web/src/lib/markdownHtml.js): same two dependencies, same single frozen
// policy. Adding a third dependency for admonitions or a typography plugin is
// deliberately out of scope - a callout syntax would be a third package, so the
// documents use plain markdown.
marked.setOptions({ gfm: true, breaks: true });

// The ONE sanitizer policy for the app. A rendered document is injected with
// dangerouslySetInnerHTML, so this config is the security boundary: markdown that
// carries raw HTML must not be able to bring a form, a frame, an embeddable
// object or an inline style/action into the page.
//
// FORBID_TAGS / FORBID_ATTR complement DOMPurify's allow-list. They are listed
// explicitly rather than relied on implicitly so the policy is readable and
// testable in one place; DOMPurify's defaults already drop scripts and event
// handlers, and the engine legitimately emits GFM tables and fenced code.
const SANITIZE_CONFIG = Object.freeze({
  FORBID_TAGS: [
    'style',
    'form',
    'input',
    'button',
    'select',
    'textarea',
    'option',
    'iframe',
    'object',
    'embed',
  ],
  FORBID_ATTR: ['style', 'action', 'formaction'],
});

/**
 * Render markdown to HTML and sanitize it with the shared policy.
 *
 * Callers must inject the result only through dangerouslySetInnerHTML: the
 * sanitization is what makes that safe, so it must never be skipped.
 */
export function toSanitizedHtml(source: string): string {
  if (!source) return '';
  // async: false keeps marked.parse synchronous, so the return type is string.
  return DOMPurify.sanitize(marked.parse(source, { async: false }), SANITIZE_CONFIG);
}
