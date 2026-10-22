import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

// The declarations in src/styles/theme.css, read as text. `tokenOf` returns what
// the file says (`var(--color-x)` for an alias, a hex for a literal) and
// `resolvedTokenOf` follows the alias to the literal it ends at, inside the same
// block. Comparing two roles on their raw text would read an alias and its
// literal as "different" and pass on a collision.
export const css = readFileSync(resolve(process.cwd(), 'src/styles/theme.css'), 'utf8');

export const tokenOf = (selector: string, name: string): string => {
  const start = css.indexOf(`${selector} {`);
  if (start === -1) throw new Error(`${selector} block not found in src/styles/theme.css`);
  const block = css.slice(start, css.indexOf('\n}', start));
  const match = block.match(new RegExp(`${name}:\\s*([^;]+);`));
  if (!match) throw new Error(`${name} is not declared in ${selector}`);
  return match[1].trim();
};

export const resolvedTokenOf = (selector: string, name: string, seen: string[] = []): string => {
  const raw = tokenOf(selector, name);
  const alias = raw.match(/^var\((--[a-z0-9-]+)\)$/i);
  if (!alias) return raw.toLowerCase();
  if (seen.includes(name)) throw new Error(`var() cycle: ${[...seen, name].join(' -> ')}`);
  return resolvedTokenOf(selector, alias[1], [...seen, name]);
};
