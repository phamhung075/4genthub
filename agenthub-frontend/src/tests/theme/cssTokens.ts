import { declaredValues, tokenValues, type TokenMode } from '../../theme/tokenValues';

// The test-side view of the token layer, read through src/theme/tokenValues.ts -
// the one parser the palette also reads - so an arm here can never disagree with
// the theme about what theme.css declares. `tokenOf` returns what the file says
// (`var(--color-x)` for an alias, a hex for a literal); `resolvedTokenOf` follows
// the alias to the literal it ends at. Comparing two roles on their raw text
// would read an alias and its literal as "different" and pass on a collision.
const modeOf = (selector: string): TokenMode => {
  if (selector === ':root') return 'light';
  if (selector === '.dark') return 'dark';
  throw new Error(`unknown token block ${selector}`);
};

export const tokenOf = (selector: string, name: string): string => {
  const value = declaredValues[modeOf(selector)][name];
  if (value === undefined) throw new Error(`${name} is not declared in ${selector}`);
  return value;
};

export const resolvedTokenOf = (selector: string, name: string): string => {
  const value = tokenValues[modeOf(selector)][name];
  if (value === undefined) throw new Error(`${name} is not declared in ${selector}`);
  return value.toLowerCase();
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
