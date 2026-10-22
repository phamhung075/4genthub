/**
 * Reading a computed colour, both spellings.
 *
 * A computed colour arrives as `rgb(r, g, b)` for a plain custom property, and as
 * `color(srgb r g b / a)` for a colour Chrome resolved through `color-mix()` or
 * relative-colour syntax - which is how Tailwind's alpha channel now reaches a
 * theme class (the registration landed with task 470c7439). A reader that knows
 * only the legacy spelling sees an empty or default value, so every test that
 * asserts on a theme colour goes through this module rather than matching one
 * text form: `expect(el).toHaveCSS('border-color', 'rgb(...)')` on a color-mix
 * token fails for the spelling, not for the colour.
 *
 * Node side. `e2e/shell.spec.ts` holds the same rule inside its page-evaluated
 * collector (a function handed to `page.evaluate` cannot close over an import),
 * and states that it is the same rule; this module is the definition to copy
 * when that spec is next touched.
 */

export type Painted = { r: number; g: number; b: number; a: number };

/**
 * `rgb(79, 70, 229)` / `rgba(79, 70, 229, 0.4)` / `color(srgb 0.309804 0.27451 0.898039 / 0.4)`
 * to channels in 0-255 and an alpha in 0-1, or null when the token is not a colour.
 */
export const parsePaintedColour = (token: string): Painted | null => {
  const value = (token ?? '').trim();
  if (value.startsWith('color(')) {
    const [channels, alphaPart] = value
      .slice(value.indexOf('(') + 1, -1)
      .replace(/^\s*srgb\s*/, '')
      .split('/');
    const nums = (channels.match(/-?[\d.]+%?/g) ?? []).map((n) =>
      n.endsWith('%') ? Number(n.slice(0, -1)) / 100 : Number(n)
    );
    if (nums.length < 3) return null;
    const alphaRaw = alphaPart?.trim();
    const alpha =
      alphaRaw === undefined
        ? 1
        : alphaRaw.endsWith('%')
          ? Number(alphaRaw.slice(0, -1)) / 100
          : Number(alphaRaw);
    return { r: nums[0] * 255, g: nums[1] * 255, b: nums[2] * 255, a: alpha };
  }
  const parts = value.match(/[\d.]+/g)?.map(Number) ?? [];
  if (parts.length < 3) return null;
  return { r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1 };
};

/** `#4f46e5` (what theme.css holds) to channels, so a computed colour can be compared to the token. */
export const parseHexColour = (hex: string): Painted | null => {
  const value = (hex ?? '').trim().replace(/^#/, '');
  const full = value.length === 3 ? value.split('').map((c) => c + c).join('') : value;
  if (!/^[0-9a-f]{6}$/i.test(full)) return null;
  return {
    r: parseInt(full.slice(0, 2), 16),
    g: parseInt(full.slice(2, 4), 16),
    b: parseInt(full.slice(4, 6), 16),
    a: 1,
  };
};

/** `rgb(79, 70, 229)` for a channel triple - the form a failure message should read. */
export const formatChannels = ({ r, g, b }: Painted): string =>
  `rgb(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)})`;

/** True when two painted colours are the same hue within a channel tolerance. */
export const sameHue = (left: Painted, right: Painted, tolerance = 1): boolean =>
  Math.abs(left.r - right.r) <= tolerance &&
  Math.abs(left.g - right.g) <= tolerance &&
  Math.abs(left.b - right.b) <= tolerance;
