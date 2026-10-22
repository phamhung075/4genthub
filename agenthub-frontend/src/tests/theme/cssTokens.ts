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

// WCAG relative luminance of a resolved literal. A token that resolves to
// anything but a six-digit hex (rgba, a named colour) is a shape these arms do
// not measure, so they say so rather than comparing NaN.
export const luminanceOf = (colour: string): number => {
  if (!/^#[0-9a-f]{6}$/.test(colour)) throw new Error(`not a literal hex: ${colour}`);
  const channels = [1, 3, 5]
    .map((i) => parseInt(colour.slice(i, i + 2), 16) / 255)
    .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
};

export const contrastRatio = (a: string, b: string): number => {
  const [lighter, darker] = [luminanceOf(a), luminanceOf(b)].sort((x, y) => y - x);
  return (lighter + 0.05) / (darker + 0.05);
};
