import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { createTheme, decomposeColor, getContrastRatio, type Theme } from '@mui/material/styles';
import { darkTheme, getTheme, lightTheme, paletteTokens } from '../../theme/muiTheme';
import { tokenValues, valueOf } from '../../theme/tokenValues';
import { resolvedTokenOf, tokenOf } from './cssTokens';

// The module under test is read as source for the no-literal arm: a colour that
// comes back as a hex would not show up in any palette assertion, because
// createTheme stores whatever string it is handed.
const source = readFileSync(resolve(process.cwd(), 'src/theme/muiTheme.ts'), 'utf8');

const MODES = [
  { mode: 'light' as const, selector: ':root', theme: lightTheme },
  { mode: 'dark' as const, selector: '.dark', theme: darkTheme },
];

const COLOUR_SLOTS = ['primary', 'secondary', 'error', 'warning', 'success', 'info'] as const;
const STATUS_SLOTS = ['error', 'warning', 'success', 'info'] as const;

// Theme's palette and components are interfaces per key, with no index
// signature, so a slot named by a union in a loop cannot be read through the
// type. The two helpers below are the only place that gap is crossed, and each
// slot the loop can name is listed in COLOUR_SLOTS / the component names above.
type SlotContents = Record<string, Record<string, unknown>>;

const paletteOf = (theme: Theme): Record<string, { main: string; contrastText: string }> =>
  theme.palette as unknown as Record<string, { main: string; contrastText: string }>;

const overridesOf = (theme: Theme, component: string): SlotContents => {
  const components = theme.components as unknown as Record<string, { styleOverrides?: SlotContents }> | undefined;
  return components?.[component]?.styleOverrides ?? {};
};

const sameColour = (a: string, b: string) => {
  const left = decomposeColor(a);
  const right = decomposeColor(b);
  return left.type === right.type && JSON.stringify(left.values) === JSON.stringify(right.values);
};

// MUI's own answer for a literal main: build a throwaway theme and read what
// createTheme derived, rather than reimplementing getContrastText here.
const derivedContrast = (mode: 'light' | 'dark', slot: (typeof COLOUR_SLOTS)[number], main: string) =>
  paletteOf(createTheme({ palette: { mode, [slot]: { main } } }))[slot].contrastText;

const isDarkColour = (colour: string) =>
  getContrastRatio(colour, '#000000') > getContrastRatio(colour, '#ffffff');

describe('muiTheme', () => {
  describe('the file names tokens, never colours', () => {
    it('carries no hex and no rgb()/rgba() literal', () => {
      expect(source).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
      expect(source).not.toMatch(/\brgba?\(/);
    });

    it('names only tokens the token layer declares, in both modes', () => {
      const named = [...new Set([...source.matchAll(/'(--color-[a-z-]+)'/g)].map((m) => m[1]))];
      expect(named.length).toBeGreaterThan(20);
      named.forEach((name) => {
        expect(() => tokenOf(':root', name), `${name} in :root`).not.toThrow();
        expect(() => tokenOf('.dark', name), `${name} in .dark`).not.toThrow();
      });
    });
  });

  describe("both themes carry the token layer's values, not var() strings", () => {
    // MUI accepts a `var()` in createTheme and then throws where it runs colour
    // maths on it (Alert, Button, Checkbox, Divider, IconButton, a TextField with
    // an adornment) - the six that unmounted the auth pages. So the palette is
    // walked, not sampled: one var() anywhere is the crash back.
    const leaves = (node: Record<string, unknown>, path: string[] = []): Array<{ path: string[]; value: unknown }> =>
      Object.entries(node).flatMap(([key, value]) =>
        value !== null && typeof value === 'object'
          ? leaves(value as Record<string, unknown>, [...path, key])
          : [{ path: [...path, key], value }],
      );

    MODES.forEach(({ mode, selector, theme }) => {
      it(`${mode}: no palette value is a var() string`, () => {
        leaves(theme.palette as unknown as Record<string, unknown>).forEach(({ path, value }) => {
          if (typeof value === 'string') expect(value, path.join('.')).not.toContain('var(');
        });
      });

      it(`${mode}: every palette leaf is the value theme.css declares`, () => {
        leaves(paletteTokens).forEach(({ path, value }) => {
          const token = value as string;
          const actual = path.reduce<unknown>(
            (node, key) => (node as Record<string, unknown> | undefined)?.[key],
            theme.palette as unknown as Record<string, unknown>,
          );
          expect(tokenValues[mode][token], `${token} declared for ${mode}`).toBeDefined();
          expect(actual, path.join('.')).toBe(tokenValues[mode][token]);
        });
      });

      it(`${mode}: the palette's own colour tests read concrete values`, () => {
        // getContrastRatio is the maths the six throwing components do; a var()
        // here throws the same way, so this arm fails on the defect itself.
        expect(() => getContrastRatio(theme.palette.primary.contrastText, theme.palette.primary.main)).not.toThrow();
        expect(theme.palette.divider).toBe(valueOf(mode, '--color-surface-border'));
      });

      it(`${mode}: createTheme accepted the palette for ${mode}`, () => {
        expect(theme.palette.mode).toBe(mode);
      });

      it(`${mode}: the secondary slot reads the accent family`, () => {
        expect(theme.palette.secondary).toMatchObject({
          main: valueOf(mode, '--color-secondary'),
          light: valueOf(mode, '--color-secondary-light'),
          dark: valueOf(mode, '--color-secondary-dark'),
          contrastText: valueOf(mode, '--color-accent-contrast'),
        });
        // Secondary is the same colour the accent paints: a component that asks
        // for one and gets the other is not a near miss, it is the wrong paint.
        expect(resolvedTokenOf(selector, '--color-secondary')).toBe(resolvedTokenOf(selector, '--color-primary'));
      });

      it(`${mode}: each status contrastText is that slot's own token`, () => {
        // The four light contrast tokens are all #ffffff, so a value arm alone
        // cannot tell a swapped pair from a correct one; the mapping is the
        // cause, and it is asserted by name against the one table the palette is
        // filled from.
        STATUS_SLOTS.forEach((slot) => {
          expect(paletteTokens[slot]).toMatchObject({ contrastText: `--color-${slot}-contrast` });
          expect(theme.palette[slot].contrastText).toBe(valueOf(mode, `--color-${slot}-contrast`));
        });
      });

      it(`${mode}: every palette colour carries an all-four-keys literal`, () => {
        COLOUR_SLOTS.forEach((slot) => {
          ['main', 'light', 'dark', 'contrastText'].forEach((key) => {
            const contents = (theme.palette[slot] ?? {}) as unknown as Record<string, unknown>;
            const value = contents[key];
            expect(typeof value, `${slot}.${key}`).toBe('string');
            // A literal MUI can decompose: that is what the six throwing
            // components need, and what a var() is not.
            expect(() => decomposeColor(String(value)), `${slot}.${key}`).not.toThrow();
          });
        });
      });
    });
  });

  // The retired theme config (src/theme's second palette, deleted) held its own
  // hexes for these leaves, which is how the auth screens painted a near-miss of
  // the token layer. The leaves below are the ones where that copy disagreed,
  // so this arm pins the value the TOKEN LAYER owns against the leaf, by name -
  // walking paletteTokens (as the arm above does) only proves the table agrees
  // with itself, and a leaf pointed at the wrong token stays green that way.
  // `was` is the retired source, for the failure message only.
  const DRIFTED: Record<string, { light: string; dark: string; was: [string, string] }> = {
    'primary.light': { light: '#e0e7ff', dark: '#312e81', was: ['#dbeafe', '#1e3a8a'] },
    'primary.dark': { light: '#3730a3', dark: '#c7d2fe', was: ['#1e40af', '#93c5fd'] },
    'primary.contrastText': { light: '#ffffff', dark: '#0b1020', was: ["MUI's derivation", "MUI's derivation"] },
    'secondary.main': { light: '#4f46e5', dark: '#818cf8', was: ["MUI's default", "MUI's default"] },
    'secondary.light': { light: '#e0e7ff', dark: '#312e81', was: ["MUI's default", "MUI's default"] },
    'secondary.dark': { light: '#3730a3', dark: '#c7d2fe', was: ["MUI's default", "MUI's default"] },
    'secondary.contrastText': { light: '#ffffff', dark: '#0b1020', was: ["MUI's derivation", "MUI's derivation"] },
    'background.default': { light: '#ffffff', dark: '#0b1020', was: ['#ffffff', '#0f172a'] },
    'background.paper': { light: '#ffffff', dark: '#131a2b', was: ['#ffffff', '#1e293b'] },
    'text.primary': { light: '#0f172a', dark: '#f1f5f9', was: ['#111827', '#f1f5f9'] },
    'text.secondary': { light: '#475569', dark: '#94a3b8', was: ['#6b7280', '#94a3b8'] },
    'text.disabled': { light: '#cbd5e1', dark: '#475569', was: ['#d1d5db', '#475569'] },
    'error.main': { light: '#dc2626', dark: '#f87171', was: ['#ef4444', '#ef4444'] },
    'error.dark': { light: '#b91c1c', dark: '#fca5a5', was: ['#dc2626', '#f87171'] },
    'error.contrastText': { light: '#ffffff', dark: 'rgba(0, 0, 0, 0.87)', was: ["MUI's derivation", "MUI's derivation"] },
    'warning.main': { light: '#b45309', dark: '#fbbf24', was: ['#f59e0b', '#f59e0b'] },
    'warning.dark': { light: '#92400e', dark: '#fcd34d', was: ['#d97706', '#fbbf24'] },
    'warning.contrastText': { light: '#ffffff', dark: 'rgba(0, 0, 0, 0.87)', was: ["MUI's derivation", "MUI's derivation"] },
    'success.main': { light: '#059669', dark: '#34d399', was: ['#10b981', '#10b981'] },
    'success.dark': { light: '#047857', dark: '#6ee7b7', was: ['#059669', '#34d399'] },
    'success.contrastText': { light: '#ffffff', dark: 'rgba(0, 0, 0, 0.87)', was: ["MUI's derivation", "MUI's derivation"] },
    'info.main': { light: '#2563eb', dark: '#60a5fa', was: ['#4f46e5', '#818cf8'] },
    'info.dark': { light: '#1d4ed8', dark: '#93c5fd', was: ['#4338ca', '#a5b4fc'] },
    'info.contrastText': { light: '#ffffff', dark: 'rgba(0, 0, 0, 0.87)', was: ["MUI's derivation", "MUI's derivation"] },
    divider: { light: '#e2e8f0', dark: '#26314a', was: ['#e5e7eb', '#334155'] },
  };

  describe('the leaves the retired config owned carry the ladder\'s values', () => {
    MODES.forEach(({ mode, theme }, index) => {
      it(`${mode}: every drifted leaf is the token layer's value, not the retired one`, () => {
        Object.entries(DRIFTED).forEach(([leaf, expected]) => {
          const actual = leaf
            .split('.')
            .reduce<unknown>(
              (node, key) => (node as Record<string, unknown> | undefined)?.[key],
              theme.palette as unknown as Record<string, unknown>,
            );
          const want = index === 0 ? expected.light : expected.dark;
          expect(typeof actual, `${leaf} is a colour`).toBe('string');
          expect(sameColour(String(actual), want), `${leaf}: ${String(actual)}, the retired config had ${expected.was[index]}`).toBe(
            true,
          );
        });
      });
    });
  });

  describe('contrastText is the derivation MUI itself makes', () => {
    MODES.forEach(({ mode, selector, theme }) => {
      it(`${mode}: each status contrast text is exactly what MUI derives`, () => {
        STATUS_SLOTS.forEach((slot) => {
          const main = resolvedTokenOf(selector, `--color-${slot}`);
          const ours = resolvedTokenOf(selector, `--color-${slot}-contrast`);
          const mui = derivedContrast(mode, slot, main);
          expect(sameColour(ours, mui), `${slot}: token ${ours}, MUI ${mui}`).toBe(true);
        });
      });

      // The accent's contrast token is the product's own choice, not MUI's
      // black at 87%: it is the background rung in dark (#0b1020, 6.40:1 on the
      // accent against MUI's 7.04:1). So the invariant asserted here is the
      // SIDE - the token stays light-on-dark or dark-on-light as MUI derives it,
      // which is what a changed accent would break.
      it(`${mode}: the primary contrast text picks the side MUI picks`, () => {
        const main = resolvedTokenOf(selector, '--color-primary');
        const ours = resolvedTokenOf(selector, '--color-accent-contrast');
        expect(isDarkColour(ours)).toBe(isDarkColour(derivedContrast(mode, 'primary', main)));
        expect(theme.palette.primary.contrastText).toBe(valueOf(mode, '--color-accent-contrast'));
      });
    });
  });

  describe('lightTheme', () => {
    it('uses the background and text tokens', () => {
      expect(lightTheme.palette.background).toMatchObject({
        default: valueOf('light', '--color-background'),
        paper: valueOf('light', '--color-surface'),
      });
      expect(lightTheme.palette.text).toMatchObject({
        primary: valueOf('light', '--color-text'),
        secondary: valueOf('light', '--color-text-secondary'),
        disabled: valueOf('light', '--color-text-disabled'),
      });
      expect(lightTheme.palette.divider).toBe(valueOf('light', '--color-surface-border'));
    });

    it('configures MuiButton component correctly', () => {
      const button = overridesOf(lightTheme, 'MuiButton');
      expect(button.root).toEqual({ textTransform: 'none' });
      expect(button.contained).toMatchObject({
        backgroundColor: 'var(--color-button-primary-bg)',
        color: 'var(--color-button-primary-text)',
        '&:hover': { backgroundColor: 'var(--color-button-primary-hover)' },
      });
      expect(button.outlined).toMatchObject({
        borderColor: 'var(--color-button-outline-border)',
        '&:hover': { backgroundColor: 'var(--color-button-outline-hover)' },
      });
    });

    it('configures MuiTextField component correctly', () => {
      const textField = overridesOf(lightTheme, 'MuiTextField');
      expect(textField.root['& .MuiOutlinedInput-root']).toMatchObject({
        backgroundColor: 'var(--color-input-background)',
      });
    });

    it('sets correct typography', () => {
      expect(lightTheme.typography.fontFamily).toBe('"Inter", "Roboto", "Helvetica", "Arial", sans-serif');
      expect(lightTheme.typography.h1.color).toBe('var(--color-text)');
      expect(lightTheme.typography.body1.color).toBe('var(--color-text)');
      expect(lightTheme.typography.body2.color).toBe('var(--color-text-secondary)');
    });
  });

  describe('darkTheme', () => {
    it('removes background images in dark mode', () => {
      expect(overridesOf(darkTheme, 'MuiPaper').root.backgroundImage).toBe('none');
      expect(overridesOf(darkTheme, 'MuiCard').root.backgroundImage).toBe('none');
      expect(overridesOf(darkTheme, 'MuiAppBar').root.backgroundImage).toBe('none');
      expect(overridesOf(darkTheme, 'MuiDrawer').paper.backgroundImage).toBe('none');
    });

    it('configures additional dark mode components', () => {
      expect(overridesOf(darkTheme, 'MuiIconButton').root.color).toBe('var(--color-text)');
      expect(overridesOf(darkTheme, 'MuiCheckbox').root.color).toBe('var(--color-text-secondary)');
      expect(overridesOf(darkTheme, 'MuiRadio').root.color).toBe('var(--color-text-secondary)');
      expect(overridesOf(darkTheme, 'MuiSwitch').root['& .MuiSwitch-track']).toMatchObject({
        backgroundColor: 'var(--color-background-tertiary)',
      });
      expect(overridesOf(darkTheme, 'MuiLinearProgress').root.backgroundColor).toBe(
        'var(--color-background-tertiary)'
      );
      expect(overridesOf(darkTheme, 'MuiCircularProgress').root.color).toBe('var(--color-primary)');
    });

    it('configures TextField with dark theme specific styles', () => {
      const textField = overridesOf(darkTheme, 'MuiTextField');
      expect(textField.root['& .MuiInputLabel-root']).toMatchObject({
        color: 'var(--color-text-secondary)',
      });
      expect(textField.root['& .MuiInputLabel-root']['&.Mui-focused']).toMatchObject({
        color: 'var(--color-primary)',
      });
    });
  });

  describe('getTheme', () => {
    it('returns lightTheme for light mode', () => {
      expect(getTheme('light')).toBe(lightTheme);
    });

    it('returns darkTheme for dark mode', () => {
      expect(getTheme('dark')).toBe(darkTheme);
    });
  });

  describe('component consistency', () => {
    it('has consistent component overrides between themes', () => {
      const commonComponents = [
        'MuiPaper',
        'MuiCard',
        'MuiButton',
        'MuiTextField',
        'MuiAlert',
        'MuiAppBar',
        'MuiDrawer',
        'MuiDivider',
        'MuiTableCell',
        'MuiChip',
      ];

      commonComponents.forEach((component) => {
        expect(Object.keys(overridesOf(lightTheme, component)).length, `light ${component}`).toBeGreaterThan(0);
        expect(Object.keys(overridesOf(darkTheme, component)).length, `dark ${component}`).toBeGreaterThan(0);
      });
    });

    it('has consistent typography configuration', () => {
      const typographyKeys: (keyof typeof lightTheme.typography)[] = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'body1', 'body2'];

      typographyKeys.forEach((key) => {
        expect(lightTheme.typography[key]).toBeDefined();
        expect(darkTheme.typography[key]).toBeDefined();
      });
    });
  });
});
