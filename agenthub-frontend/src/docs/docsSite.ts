// The /docs site's content: ai_docs/public-docs, read at BUILD time so the markdown that is
// reviewed in ai_docs IS what renders, with no copy step. The tree sits outside this app, so the
// frontend Dockerfiles copy it to /ai_docs beside the app, where this same relative path finds it.
// The layout contract (subject folders, numbered pages, relative links) is in its README.md.
const PAGE_FILES = import.meta.glob('../../../ai_docs/public-docs/*/*.md', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>;

const ASSET_FILES = import.meta.glob('../../../ai_docs/public-docs/*/*.{png,jpg,jpeg,gif,svg,webp}', {
  query: '?url',
  import: 'default',
  eager: true,
}) as Record<string, string>;

const TREE_ROOT = '../../../ai_docs/public-docs/';

export const DOCS_BASE = '/docs';

export interface DocPage {
  /** `<section>/<page>`, the path under /docs. */
  id: string;
  title: string;
  source: string;
}

export interface DocSection {
  slug: string;
  title: string;
  pages: DocPage[];
}

/** `02-five-minute-team.md` -> `five-minute-team`: the number orders a file, it never names one. */
export function stripOrder(name: string): string {
  return name.replace(/\.md$/, '').replace(/^\d+-/, '');
}

/** `architecture-and-mental-model` -> `Architecture and mental model`. */
function sectionTitle(slug: string): string {
  const words = slug.replace(/-/g, ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}

function pageTitle(source: string, fallback: string): string {
  const heading = source.match(/^# (.+)$/m);
  return heading ? heading[1].trim() : sectionTitle(fallback);
}

/** Group `<NN-section>/<NN-page>.md` files into ordered sections. Keys sort by their numbers. */
export function buildSections(files: Record<string, string>, root: string): DocSection[] {
  const sections = new Map<string, DocSection>();
  for (const path of Object.keys(files).sort()) {
    const [folder, file] = path.slice(root.length).split('/');
    const slug = stripOrder(folder);
    const section = sections.get(slug) ?? { slug, title: sectionTitle(slug), pages: [] };
    const pageSlug = stripOrder(file);
    section.pages.push({
      id: `${slug}/${pageSlug}`,
      title: pageTitle(files[path], pageSlug),
      source: files[path],
    });
    sections.set(slug, section);
  }
  return Array.from(sections.values());
}

/**
 * Resolve a link or image path written in the page `fromId` against the tree.
 * A relative `.md` link becomes a /docs route; a relative image becomes the
 * built asset's URL. Anything else (absolute paths, other sites, anchors) is
 * returned unchanged, and an unresolvable path is returned unchanged too so a
 * broken link stays visible instead of pointing somewhere wrong.
 */
export function resolveDocHref(fromId: string, href: string, assets: Record<string, string>): string {
  if (/^([a-z][a-z0-9+.-]*:|\/|#)/i.test(href)) return href;
  const [path, hash] = href.split('#');
  const segments = fromId.split('/').slice(0, 1);
  for (const part of path.split('/')) {
    if (part === '..') segments.pop();
    else if (part !== '.' && part !== '') segments.push(part);
  }
  if (path.endsWith('.md')) {
    if (segments.length !== 2) return href;
    const route = `${DOCS_BASE}/${segments.map(stripOrder).join('/')}`;
    return hash ? `${route}#${hash}` : route;
  }
  const [section, file] = segments.map((part, index) => (index === 0 ? stripOrder(part) : part));
  const asset = Object.entries(assets).find(([key]) => {
    const [assetFolder, assetFile] = key.split('/').slice(-2);
    return stripOrder(assetFolder) === section && assetFile === file;
  });
  return asset ? asset[1] : href;
}

export const docSections: DocSection[] = buildSections(PAGE_FILES, TREE_ROOT);

export const docAssets: Record<string, string> = ASSET_FILES;
