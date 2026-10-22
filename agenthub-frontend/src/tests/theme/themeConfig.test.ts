import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { themeConfig } from '../../theme/themeConfig';

// The declarations in src/styles/theme.css, read as text: `tokenOf` returns what
// the file says (`var(--color-x)` for an alias, a hex for a literal) and
// `resolvedTokenOf` follows the alias to the literal it ends at, inside the same
// block. Comparing two roles on their raw text would read an alias and its
// literal as "different" and pass on a collision.
const css = readFileSync(resolve(process.cwd(), 'src/styles/theme.css'), 'utf8');

const tokenOf = (selector: string, name: string) => {
  const start = css.indexOf(`${selector} {`);
  expect(start, `${selector} block`).toBeGreaterThan(-1);
  const block = css.slice(start, css.indexOf('\n}', start));
  const match = block.match(new RegExp(`${name}:\\s*([^;]+);`));
  expect(match, `${name} in ${selector}`).not.toBeNull();
  return match![1].trim();
};

const resolvedTokenOf = (selector: string, name: string, seen: string[] = []): string => {
  const raw = tokenOf(selector, name);
  const alias = raw.match(/^var\((--[a-z0-9-]+)\)$/i);
  if (!alias) return raw.toLowerCase();
  if (seen.includes(name)) throw new Error(`var() cycle: ${[...seen, name].join(' -> ')}`);
  return resolvedTokenOf(selector, alias[1], [...seen, name]);
};

describe('themeConfig', () => {
  describe('theme structure', () => {
    it('has light and dark theme configurations', () => {
      expect(themeConfig).toHaveProperty('light');
      expect(themeConfig).toHaveProperty('dark');
    });

    it('light theme has all required color properties', () => {
      const requiredProperties = [
        'primary', 'primaryHover', 'primaryLight', 'primaryDark',
        'background', 'backgroundSecondary', 'backgroundTertiary', 'backgroundHover', 'backgroundActive',
        'surface', 'surfaceHover', 'surfaceBorder', 'surfaceBorderHover',
        'text', 'textSecondary', 'textTertiary', 'textDisabled', 'textInverse',
        'inputBackground', 'inputBorder', 'inputBorderFocus', 'inputBorderError', 'inputText', 'inputPlaceholder',
        'buttonPrimaryBg', 'buttonPrimaryHover', 'buttonPrimaryText',
        'buttonSecondaryBg', 'buttonSecondaryHover', 'buttonSecondaryText',
        'buttonOutlineBorder', 'buttonOutlineHover', 'buttonDangerBg', 'buttonDangerHover',
        'success', 'successLight', 'successDark',
        'warning', 'warningLight', 'warningDark',
        'error', 'errorLight', 'errorDark',
        'info', 'infoLight', 'infoDark',
        'shadow', 'shadowMedium', 'shadowLarge', 'overlay',
        'scrollbarTrack', 'scrollbarThumb', 'scrollbarThumbHover',
        'codeBackground', 'codeBorder', 'codeText',
        'navBackground', 'navText', 'navTextHover', 'navTextActive', 'navBorder'
      ];

      requiredProperties.forEach(prop => {
        expect(themeConfig.light).toHaveProperty(prop);
      });
    });

    it('dark theme has all required color properties', () => {
      const lightKeys = Object.keys(themeConfig.light);
      const darkKeys = Object.keys(themeConfig.dark);

      expect(darkKeys).toEqual(lightKeys);
    });

    it('all color values are valid strings', () => {
      Object.values(themeConfig.light).forEach(value => {
        expect(typeof value).toBe('string');
        expect(value).toBeTruthy();
      });

      Object.values(themeConfig.dark).forEach(value => {
        expect(typeof value).toBe('string');
        expect(value).toBeTruthy();
      });
    });
  });

  describe('color values', () => {
    it('light theme uses appropriate light colors', () => {
      expect(themeConfig.light.background).toBe('#ffffff');
      expect(themeConfig.light.text).toBe('#111827'); // gray-900
      expect(themeConfig.light.primary).toBe('#4f46e5'); // the token layer's --color-accent
    });

    it('dark theme uses appropriate dark colors', () => {
      expect(themeConfig.dark.background).toBe('#0f172a'); // slate-900
      expect(themeConfig.dark.text).toBe('#f1f5f9'); // slate-100
      expect(themeConfig.dark.primary).toBe('#818cf8'); // the token layer's dark --color-accent
    });

    it('maintains contrast between background and text', () => {
      // Light theme: dark text on light background
      expect(themeConfig.light.background).toBe('#ffffff');
      expect(themeConfig.light.text).toBe('#111827');

      // Dark theme: light text on dark background
      expect(themeConfig.dark.background).toBe('#0f172a');
      expect(themeConfig.dark.text).toBe('#f1f5f9');
    });
  });

  describe('theme consistency', () => {
    it('button colors match primary colors', () => {
      // Light theme
      expect(themeConfig.light.buttonPrimaryBg).toBe(themeConfig.light.primary);
      expect(themeConfig.light.buttonPrimaryHover).toBe(themeConfig.light.primaryHover);

      // Dark theme
      expect(themeConfig.dark.buttonPrimaryBg).toBe('#818cf8'); // the dark accent
      expect(themeConfig.dark.buttonPrimaryHover).toBe(themeConfig.dark.primaryHover);
    });

    it('info colors relate to primary colors', () => {
      // Light theme: info should be similar to primary
      expect(themeConfig.light.info).toBe(themeConfig.light.primary);
      expect(themeConfig.light.infoLight).toBe(themeConfig.light.primaryLight);
      expect(themeConfig.light.infoDark).toBe(themeConfig.light.primaryHover);
    });

    it('maintains color hierarchy in backgrounds', () => {
      // Light theme: background colors get progressively darker
      expect(themeConfig.light.background).toBe('#ffffff');
      expect(themeConfig.light.backgroundSecondary).toBe('#f9fafb'); // gray-50
      expect(themeConfig.light.backgroundTertiary).toBe('#f3f4f6'); // gray-100

      // Dark theme: background colors get progressively lighter
      expect(themeConfig.dark.background).toBe('#0f172a'); // slate-900
      expect(themeConfig.dark.backgroundSecondary).toBe('#1e293b'); // slate-800
      expect(themeConfig.dark.backgroundTertiary).toBe('#334155'); // slate-700
    });
  });

  // R1: the palette must not own a brand hue. Every primary entry is the token
  // layer's accent, read here from the CSS that actually paints the app, so a
  // second source cannot drift back in unnoticed.
  describe('token parity with src/styles/theme.css', () => {
    it.each([
      ['light', ':root'],
      ['dark', '.dark'],
    ])('%s palette primary is the %s accent', (mode, selector) => {
      const palette = themeConfig[mode as 'light' | 'dark'];
      expect(palette.primary).toBe(tokenOf(selector, '--color-accent'));
      expect(palette.primaryHover).toBe(tokenOf(selector, '--color-accent-hover'));
      expect(palette.buttonPrimaryBg).toBe(palette.primary);
      expect(palette.buttonPrimaryHover).toBe(palette.primaryHover);
      expect(palette.info).toBe(palette.primary);
      expect(palette.infoDark).toBe(palette.primaryHover);
    });
  });

  // The ruling's rule, asserted where it lives - in the token map. A future
  // re-aliasing of hover onto raised, or a dark value swapped back, fails here
  // by name instead of on a page nobody re-measured.
  describe('surface role ladder (RULING-2026-10-23-surface-role-ladder.md)', () => {
    const RUNGS = [
      '--color-background',
      '--color-surface',
      '--color-surface-raised',
      '--color-background-tertiary',
      '--color-background-active',
    ];

    const luminanceOf = (hex: string) => {
      expect(hex, 'a rung resolves to a literal hex').toMatch(/^#[0-9a-f]{6}$/);
      const channels = [1, 3, 5]
        .map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
        .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
      return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
    };

    it.each([
      ['light', ':root'],
      ['dark', '.dark'],
    ])('%s: the five rungs are monotone and every alias shares its own', (mode, selector) => {
      // A card on a panel separates by fill: raised and secondary are ONE rung,
      // and it is not the panel's.
      const raised = resolvedTokenOf(selector, '--color-surface-raised');
      expect(resolvedTokenOf(selector, '--color-background-secondary')).toBe(raised);
      expect(raised).not.toBe(resolvedTokenOf(selector, '--color-surface'));

      // A hover takes the rung above the ground it paints on, in BOTH modes: the
      // light-mode no-op this ruling fixes was hover aliasing onto raised.
      const tertiary = resolvedTokenOf(selector, '--color-background-tertiary');
      expect(resolvedTokenOf(selector, '--color-background-hover')).toBe(tertiary);
      expect(tertiary).not.toBe(resolvedTokenOf(selector, '--color-background-secondary'));

      // Monotone, one direction per mode: non-increasing away from the page in
      // light (background == surface is the one equality the ladder allows),
      // strictly increasing in dark.
      const steps = RUNGS.map((name) => luminanceOf(resolvedTokenOf(selector, name)));
      if (mode === 'light') {
        expect(steps[0]).toBeCloseTo(steps[1], 10);
        steps.slice(2).forEach((value, i) => expect(value).toBeLessThan(steps[i + 1]));
      } else {
        steps.slice(1).forEach((value, i) => expect(value).toBeGreaterThan(steps[i]));
      }
    });
  });
});
