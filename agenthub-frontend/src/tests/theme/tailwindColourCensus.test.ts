import { execFileSync } from 'node:child_process';
import { mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import { extname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

/**
 * The colour census: every theme colour the config registers must compile to a
 * declaration, with its solid form AND with an opacity modifier - and, the other way, every colour
 * utility the source uses must compile to a declaration too.
 *
 * WHY IT JUDGES EMISSION AND NOT THE CONFIG OBJECT. Tailwind v3 only injects an
 * alpha channel into a colour it can parse; a plain `var(--color-x)` string is
 * dropped silently, so `border-accent/40` compiles to no rule at all while the
 * config still reads correctly. A walk over `theme.colors` therefore passes on a
 * shape that ships nothing - that is exactly how this defect reached production
 * (board task 470c7439, finding F1). The instrument is the compiler itself: one
 * CLI run over a probe file naming every candidate class, then a declaration
 * required for each name.
 *
 * The first direction is self-maintaining: a token added to the config is a class the run must emit,
 * with no list to update here. The second direction - a class the source uses must emit - is what the
 * config-side walk cannot see: the 13 shadcn names (task 20778989, RULING 2026-10-22
 * `RULING-2026-10-22-retire-the-shadcn-palette.md`) named colours the config never registered, so they
 * passed the config walk silently. Its candidate filter is a stoplist: a source token counts when its
 * base form is a registered colour path behind a colour-bearing prefix, or when it is one of the retired
 * names below - so `text-sm`, `border-t` and `ring-offset-2` never reach the verdict. A brand-new shadcn
 * name is recognised once it joins that list (one line); the emission check itself never weakens.
 *
 * TW_CENSUS_CONFIG points the census at another config file. It exists so the
 * mutation check is demonstrable - copy the config, revert one entry to a bare
 * `var(--color-primary)`, and the census fails naming `primary` - without editing
 * the tracked file. Unset, it reads `tailwind.config.js`.
 */

// vite-node does not reliably hand the module a file:// URL. The root is taken
// from the module URL when that is a file URL and from the runner's cwd otherwise
// (vitest runs with agenthub-frontend as its cwd).
const frontendRoot = (() => {
  try {
    const here = new URL('.', import.meta.url);
    if (here.protocol === 'file:') return fileURLToPath(new URL('../../../', here));
  } catch {
    // not a file URL: fall through to the cwd
  }
  return process.cwd();
})();
const configPath = process.env.TW_CENSUS_CONFIG ?? join(frontendRoot, 'tailwind.config.js');
const require = createRequire(join(frontendRoot, 'package.json'));

type ColourTree = { [key: string]: string | ColourTree };

/** Every `<path>` a nested colour object registers, `DEFAULT` mapping to its parent. */
const colourPaths = (tree: ColourTree, path = ''): string[] => {
  const paths: string[] = [];
  for (const [key, value] of Object.entries(tree)) {
    if (key === 'DEFAULT') {
      if (path) paths.push(path);
      continue;
    }
    const next = path ? `${path}-${key}` : key;
    if (typeof value === 'string') {
      // Only the colours backed by a theme custom property are in scope: the
      // literal Tailwind palette needs no alpha work.
      if (value.includes('var(--color-')) paths.push(next);
    } else {
      paths.push(...colourPaths(value as ColourTree, next));
    }
  }
  return paths;
};

/** The utility class Tailwind builds for a colour path, per property block. */
const candidates = (config: Record<string, any>): string[] => {
  const theme = config.theme?.extend ?? {};
  const blocks: Array<[string, string]> = [
    ['colors', 'bg'],
    ['backgroundColor', 'bg'],
    ['textColor', 'text'],
    ['borderColor', 'border'],
  ];
  const classes: string[] = [];
  for (const [block, prefix] of blocks) {
    const tree = theme[block] as ColourTree | undefined;
    if (!tree) continue;
    for (const path of colourPaths(tree)) {
      classes.push(`${prefix}-${path}`, `${prefix}-${path}/50`);
    }
  }
  return classes;
};

/** The colour paths the config registers under `colors`, behind whatever property prefix a utility
 *  uses (`from-primary`, `ring-offset-*`). */
const registeredColourPaths = (config: Record<string, any>): string[] => {
  const tree = (config.theme?.extend?.colors ?? config.theme?.colors) as ColourTree | undefined;
  return tree ? colourPaths(tree) : [];
};

/** Every base utility the config builds, as one set. The source scan counts a token when this set
 *  holds its base form, so a colour a block registers only under `textColor` (`text-base-secondary`)
 *  is scanned too: a walk over `theme.colors` alone cannot see it. */
const registeredUtilities = (config: Record<string, any>): Set<string> => new Set(candidates(config));

/** The characters Tailwind backslash-escapes in a class selector (`bg-accent/50` -> `.bg-accent\/50`). */
const CSS_SELECTOR_SPECIALS = /[./[\]()%,#:>=&*+~'"!$^|]/g;

const regexEscape = (text: string): string => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/** The selector Tailwind writes for a utility it emitted, as a pattern: every special character is a
 *  literal backslash plus itself, and a parent-selector variant appends its own suffix
 *  (`[&>svg]:text-error` compiles to `.…>svg { … }`). */
const selectorPattern = (utility: string): RegExp =>
  new RegExp(
    `\\.${regexEscape(utility.replace(CSS_SELECTOR_SPECIALS, (character) => `\\${character}`))}[^,{]*\\{([^}]*)\\}`
  );

/** Every rule body the sheet emits for one utility. A class that is both a colour and a font size
 *  (`text-base`, tailwind.config.js:145) emits two rules, so the verdict reads all of them. */
const emittedBlocks = (utility: string, sheet: string): string[] => [
  ...sheet.matchAll(new RegExp(selectorPattern(utility).source, 'g')),
].map((match) => match[1]);

/** Whether a rule body paints a colour at all: `color`, `background-color`, `border-color`,
 *  `--tw-ring-color`, `--tw-gradient-from/to`, `fill` and `stroke`. A body carrying only `font-size`
 *  does not. */
const hasColourDeclaration = (block: string): boolean =>
  /(?:^|[\s;])(?:color|fill|stroke)\s*:/.test(block) ||
  block.includes('-color:') ||
  block.includes('--tw-gradient-');

/**
 * The retired shadcn palette. RULING 2026-10-22 (`RULING-2026-10-22-retire-the-shadcn-palette.md`,
 * architect): these names were never registered in `tailwind.config.js`, so each compiled to no rule,
 * and every call site was migrated onto the theme token beside it. The ruling's map carries 13 rows;
 * `text-destructive-foreground` is the fourteenth name the same measurement found and the map's count
 * left out - one call site in `shimmer-button.tsx`, migrated here too. Deleting an entry is only right
 * if the palette is deliberately reintroduced.
 */
const REPLACEMENT_BY_RETIRED_NAME: Record<string, string> = {
  'text-muted-foreground': 'text-base-secondary',
  'text-destructive': 'text-error',
  'text-foreground': 'text-base-primary',
  'bg-muted': 'bg-base-tertiary',
  'ring-ring': 'ring-primary',
  'bg-destructive': 'bg-error',
  'border-destructive': 'border-error',
  'border-input': 'border-input-border',
  'border-border': 'border-surface-border',
  'text-primary-foreground': 'text-accent-contrast',
  'border-muted-foreground': 'border-text-secondary',
  'bg-border': 'bg-surface-border',
  'text-accent-foreground': 'text-accent-contrast',
  'text-destructive-foreground': 'text-accent-contrast',
};

const IS_SOURCE_EXTENSION: Record<string, true> = {
  '.ts': true, '.tsx': true, '.js': true, '.jsx': true, '.css': true, '.scss': true,
};

/** Colour-bearing utility prefixes, longest first so `ring-offset-` is tried before `ring-`. */
const COLOUR_UTILITY_PREFIXES = [
  'ring-offset-', 'placeholder-', 'decoration-', 'outline-', 'border-', 'stroke-', 'accent-',
  'divide-', 'shadow-', 'caret-', 'bg-', 'text-', 'ring-', 'fill-', 'from-', 'via-', 'to-',
];

const walkSources = (dir: string, found: string[] = []): string[] => {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) walkSources(path, found);
    else if (IS_SOURCE_EXTENSION[extname(entry.name)]) found.push(path);
  }
  return found;
};

/** The utility a class token names, variants stripped: `dark:hover:text-error` -> `text-error`.
 *  Arbitrary variants may hold a colon of their own (`[&:hover]:…`), so only bracket depth 0 splits. */
const baseUtility = (token: string): string => {
  let depth = 0;
  let start = 0;
  for (let index = 0; index < token.length; index += 1) {
    const character = token[index];
    if (character === '[') depth += 1;
    else if (character === ']') depth = Math.max(0, depth - 1);
    else if (character === ':' && depth === 0) start = index + 1;
  }
  return token.slice(start);
};

/** `<name>/50` -> `<name>`; a leading `!` (important) is not part of the name. */
const withoutAlpha = (utility: string): string =>
  (utility.startsWith('!') ? utility.slice(1) : utility).split('/')[0];

/**
 * The source classes the emission verdict is owed for, as `token -> file`. A token qualifies when it is
 * one of the retired names, or when its base form is a utility the config builds behind a colour prefix,
 * or when the name behind that prefix is a colour path the config registers (`from-primary`).
 */
const sourceColourClasses = (config: Record<string, any>): Map<string, string> => {
  const found = new Map<string, string>();
  const knownUtilities = registeredUtilities(config);
  const registeredPaths: Record<string, true> = {};
  for (const path of registeredColourPaths(config)) registeredPaths[path] = true;
  // This file holds the retired list and the prefixes, so it is its own only allowed occurrence.
  const self = fileURLToPath(import.meta.url);

  for (const file of walkSources(join(frontendRoot, 'src'))) {
    if (file === self) continue;
    const text = readFileSync(file, 'utf8');
    for (const match of text.matchAll(/[^\s"'`{}();,]+/g)) {
      const raw = match[0];
      const token = raw.startsWith('.') ? raw.slice(1) : raw;
      const utility = withoutAlpha(baseUtility(token));
      const isRetired = Object.hasOwn(REPLACEMENT_BY_RETIRED_NAME, utility);
      const prefix = COLOUR_UTILITY_PREFIXES.find((candidate) => utility.startsWith(candidate));
      const isRegisteredColour =
        prefix !== undefined &&
        (knownUtilities.has(utility) || registeredPaths[utility.slice(prefix.length)] === true);
      if (isRetired || isRegisteredColour) {
        if (!found.has(token)) found.set(token, file.slice(frontendRoot.length));
      }
    }
  }
  return found;
};

describe('theme colour census: every registered colour emits its alpha form', () => {
  let css = '';
  let classes: string[] = [];
  let sourceClasses = new Map<string, string>();

  beforeAll(() => {
    const config = require(configPath) as Record<string, any>;
    classes = candidates(config);

    sourceClasses = sourceColourClasses(config);

    const scratch = mkdtempSync(join(tmpdir(), 'tw-census-'));
    try {
      const input = join(scratch, 'in.css');
      const probe = join(scratch, 'probe.html');
      const output = join(scratch, 'out.css');
      writeFileSync(input, '@tailwind base;\n@tailwind components;\n@tailwind utilities;\n');
      writeFileSync(
        probe,
        `<div class="${[
          ...classes,
          ...sourceClasses.keys(),
          ...Object.values(REPLACEMENT_BY_RETIRED_NAME),
        ].join(' ')}"></div>`
      );
      execFileSync(
        join(frontendRoot, 'node_modules/.bin/tailwindcss'),
        ['-c', configPath, '-i', input, '-o', output, '--content', probe],
        { cwd: frontendRoot, stdio: 'pipe' }
      );
      css = readFileSync(output, 'utf8');
    } finally {
      rmSync(scratch, { recursive: true, force: true });
    }
  }, 120_000);

  it('finds the colours the config registers', () => {
    expect(classes.length).toBeGreaterThan(100);
    expect(sourceClasses.size).toBeGreaterThan(100);
  });

  it('emits a rule for every colour, solid and at 50%', () => {
    const missing = classes.filter(
      (utility) => !emittedBlocks(utility, css).some((block) => block.includes('color'))
    );

    if (missing.length > 0) {
      throw new Error(
        `${missing.length} theme utilities compile to NO declaration: ${missing.join(', ')}. ` +
          'The usual cause is a colour registered as a bare var(--color-*) string - Tailwind v3 ' +
          'cannot put an alpha on it - or an alias key that replaces a nested colour tree. ' +
          'Fix the entry in tailwind.config.js; do not drop the class.'
      );
    }
  });

  it('emits a rule for every colour utility the source uses', () => {
    const missing: string[] = [];

    for (const [token, file] of sourceClasses) {
      if (emittedBlocks(token, css).some(hasColourDeclaration)) continue;
      const replacement = REPLACEMENT_BY_RETIRED_NAME[withoutAlpha(baseUtility(token))];
      missing.push(
        `${file} uses \`${token}\`` +
          (replacement ? ` - that is a retired shadcn name, use \`${replacement}\`` : '')
      );
    }

    if (missing.length > 0) {
      throw new Error(
        `${missing.length} colour utility class(es) in src compile to NO declaration:\n  ${missing.join(
          '\n  '
        )}\nA class naming a colour the config does not register emits nothing at all - register the ` +
          'colour in tailwind.config.js or use a theme token that compiles. ' +
          'See RULING-2026-10-22-retire-the-shadcn-palette.md for the retired names.'
      );
    }
  });

  /**
   * The map's targets are the point of the migration: if one stops compiling, every call site the map
   * sent to it paints nothing while the class name still reads like a theme token. `text-base-primary`
   * did exactly that - the map named it, no block registered it, and 31 migrated call sites plus 31
   * older ones drew nothing. This arm probes the map itself rather than the source, so a row is caught
   * even when it has no call site yet.
   */
  it('emits a colour declaration for every replacement the retired map names', () => {
    const dead = Object.entries(REPLACEMENT_BY_RETIRED_NAME)
      .filter(([, replacement]) => !emittedBlocks(replacement, css).some(hasColourDeclaration))
      .map(([retired, replacement]) => `${retired} -> ${replacement}`);

    if (dead.length > 0) {
      throw new Error(
        `${dead.length} replacement(s) in the retired map compile to NO colour declaration: ` +
          `${dead.join(', ')}. The map points at a token the config does not build - register it in ` +
          'tailwind.config.js or point the row at a token that paints.'
      );
    }
  });
});
