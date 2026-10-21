import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

/**
 * The colour census: every theme colour the config registers must compile to a
 * declaration, with its solid form AND with an opacity modifier.
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
 * It is self-maintaining: a token added to the config is a class the run must
 * emit, with no list to update here.
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

/** The CSS class escape Tailwind writes for a utility it emitted: `bg-accent/50`
 *  becomes `.bg-accent\/50`, so each special character is matched as a literal
 *  backslash followed by itself. */
const escapedSelector = (utility: string): RegExp =>
  new RegExp(
    `\\.${utility.replace(/[./[\]()%,#:]/g, (character) => `\\\\${character}`)}\\s*\\{([^}]*)\\}`
  );

describe('theme colour census: every registered colour emits its alpha form', () => {
  let css = '';
  let classes: string[] = [];

  beforeAll(() => {
    const config = require(configPath) as Record<string, any>;
    classes = candidates(config);

    const scratch = mkdtempSync(join(tmpdir(), 'tw-census-'));
    try {
      const input = join(scratch, 'in.css');
      const probe = join(scratch, 'probe.html');
      const output = join(scratch, 'out.css');
      writeFileSync(input, '@tailwind base;\n@tailwind components;\n@tailwind utilities;\n');
      writeFileSync(probe, `<div class="${classes.join(' ')}"></div>`);
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
  });

  it('emits a rule for every colour, solid and at 50%', () => {
    const missing = classes.filter((utility) => {
      const rule = escapedSelector(utility).exec(css);
      return rule === null || !rule[1].includes('color');
    });

    if (missing.length > 0) {
      throw new Error(
        `${missing.length} theme utilities compile to NO declaration: ${missing.join(', ')}. ` +
          'The usual cause is a colour registered as a bare var(--color-*) string - Tailwind v3 ' +
          'cannot put an alpha on it - or an alias key that replaces a nested colour tree. ' +
          'Fix the entry in tailwind.config.js; do not drop the class.'
      );
    }
  });
});
