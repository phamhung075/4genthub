export interface TocItem {
  id: string;
  text: string;
  level: 2 | 3;
}

/** Heading text to an ASCII id, matching how anchors are written by hand. */
export function slugifyHeading(text: string): string {
  return (
    text
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'section'
  );
}

/**
 * Give every h2/h3 of a RENDERED document an id and list them, so a table of
 * contents cannot drift from the markdown: a heading added to the file appears
 * with no other edit, and duplicate heading text gets -1/-2 suffixes.
 */
export function collectHeadings(container: HTMLElement): TocItem[] {
  const seen: Record<string, number> = {};
  return Array.from(container.querySelectorAll('h2, h3')).map((heading) => {
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
}
