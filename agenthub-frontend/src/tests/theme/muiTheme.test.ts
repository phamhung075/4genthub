import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { createTheme, decomposeColor, getContrastRatio, type Theme } from '@mui/material/styles';
import { darkTheme, getTheme, lightTheme } from '../../theme/muiTheme';
import { resolvedTokenOf, tokenOf } from './cssTokens';

// The module under test is read as source for the no-literal arm: a colour that
// comes back as a hex would not show up in any palette assertion, because
// createTheme stores whatever string it is handed.
const source = readFileSync(resolve(process.cwd(), 'src/theme/muiTheme.ts'), 'utf8');

const MODES = [
  { mode: 'light' as const, selector: ':root', theme: lightTheme },
  { mode: 'dark' as const, selector: '.dark', theme: darkTheme },
];

const COLOUR_SLOTS = ['primary', 'error', 'warning', 'success', 'info'] as const;
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
      const named = [...new Set([...source.matchAll(/var\((--color-[a-z-]+)\)/g)].map((m) => m[1]))];
      expect(named.length).toBeGreaterThan(20);
      named.forEach((name) => {
        expect(() => tokenOf(':root', name), `${name} in :root`).not.toThrow();
        expect(() => tokenOf('.dark', name), `${name} in .dark`).not.toThrow();
      });
    });
  });

  describe('both themes build from the tokens', () => {
    MODES.forEach(({ mode, theme }) => {
      it(`${mode}: createTheme accepted every var() value`, () => {
        expect(theme.palette.mode).toBe(mode);
      });

      it(`${mode}: every palette colour carries all four keys`, () => {
        COLOUR_SLOTS.forEach((slot) => {
          ['main', 'light', 'dark', 'contrastText'].forEach((key) => {
            const contents = (theme.palette[slot] ?? {}) as unknown as Record<string, unknown>;
            expect(contents[key], `${slot}.${key}`).toMatch(/^var\(--color-[a-z-]+\)$/);
          });
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
        expect(theme.palette.primary.contrastText).toBe('var(--color-accent-contrast)');
      });
    });
  });

  describe('lightTheme', () => {
    it('uses the background and text tokens', () => {
      expect(lightTheme.palette.background).toMatchObject({
        default: 'var(--color-background)',
        paper: 'var(--color-surface)',
      });
      expect(lightTheme.palette.text).toMatchObject({
        primary: 'var(--color-text)',
        secondary: 'var(--color-text-secondary)',
        disabled: 'var(--color-text-disabled)',
      });
      expect(lightTheme.palette.divider).toBe('var(--color-surface-border)');
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
