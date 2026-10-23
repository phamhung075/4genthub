import { describe, expect, it } from 'vitest';
import { declaredValues, tokenValues, type TokenMode } from '../../theme/tokenValues';
import { contrastRatio } from './cssTokens';

// The stroke family's invariants, encoded so the defect cannot come back by name.
//
// The defect this file exists for (RULING-2026-10-23-dark-border-collision, reviewer's major on 8504e73c):
// dark `--color-surface-border` was `#26314a`, the same value as `--color-background-tertiary`. Six
// `.theme-*` panels and the four TokenManagement cards paint `background-tertiary` with that stroke, so
// the border rendered at 1.000:1 - invisible by construction. Light already places its border one rung
// ABOVE the tertiary fill (tertiary `#f1f5f9`, border `#e2e8f0` = the active rung); dark had it ON the
// rung. The fix moved dark's stroke family up one step and made hover/input-border aliases, which is
// light's shape. These arms hold that and fail by the token's name when it drifts.

const FAMILY = '--color-surface-border';

// The fills a card actually takes. `--color-background` and `--color-background-active` are deliberately
// absent: both are page or transient grounds, and light's accepted design has `--color-surface-border`
// equal to the active rung - a collision the ruling records rather than removes, with its ratio asserted
// below. If this list ever grows, the ruling must grow with it.
const FILLS = [
  '--color-background-tertiary',
  '--color-background-hover',
  '--color-background-secondary',
  '--color-surface',
  '--color-surface-raised',
];

const MODES: TokenMode[] = ['light', 'dark'];

const resolved = (mode: TokenMode, name: string): string => {
  const value = tokenValues[mode][name];
  if (value === undefined) throw new Error(`theme.css declares no ${name} for ${mode}`);
  return value.toLowerCase();
};

// Derived from the token map, never listed: a `--color-surface-border-*` token added later is covered
// without touching this file (task 51e51aa8 nit 1 - the reverted branch carried a hardcoded three-name
// list, and a new stroke name would have escaped it silently).
const strokeNames = (mode: TokenMode): string[] =>
  Object.keys(tokenValues[mode])
    .filter((name) => name.startsWith(FAMILY))
    .sort();

describe('the stroke family', () => {
  it('is derived from the token map and is not the one name', () => {
    MODES.forEach((mode) => {
      expect(strokeNames(mode)).toEqual([
        '--color-surface-border',
        '--color-surface-border-hover',
        '--color-surface-border-strong',
      ]);
      FILLS.forEach((fill) => expect(declaredValues[mode][fill], `${mode} ${fill}`).toBeDefined());
    });
  });

  it('never resolves equal to a fill a card sits on, in either mode', () => {
    MODES.forEach((mode) => {
      strokeNames(mode).forEach((stroke) => {
        FILLS.forEach((fill) => {
          const ratio = contrastRatio(resolved(mode, stroke), resolved(mode, fill));
          // The message carries both names and the ratio, so the failure states the defect rather than
          // a bare inequality: "dark --color-surface-border vs --color-background-tertiary = 1:1".
          expect(ratio, `${mode} ${stroke} on ${fill} = ${ratio.toFixed(3)}:1`).toBeGreaterThan(1);
        });
      });
    });
  });

  it('separates from the tertiary fill by the hairline floor, in either mode', () => {
    MODES.forEach((mode) => {
      const border = resolved(mode, FAMILY);
      // Light's accepted design measures 1.125 here, so the floor cannot sit higher without repainting
      // light; dark measures 1.251 after the move (it was 1.000).
      expect(contrastRatio(border, resolved(mode, '--color-background-tertiary')), `${mode} on tertiary`)
        .toBeGreaterThanOrEqual(1.12);
      expect(contrastRatio(border, resolved(mode, '--color-surface')), `${mode} on surface`)
        .toBeGreaterThanOrEqual(1.2);
    });
  });

  it('resolves hover and input borders through the strong stroke in both modes', () => {
    MODES.forEach((mode) => {
      const strong = resolved(mode, '--color-surface-border-strong');
      ['--color-surface-border-hover', '--color-input-border', '--color-button-outline-border'].forEach(
        (name) => {
          expect(declaredValues[mode][name], mode).toBe('var(--color-surface-border-strong)');
          expect(resolved(mode, name), mode).toBe(strong);
        },
      );
    });
  });

  // The one pair the map cannot separate, recorded with its numbers rather than left to be rediscovered:
  // the default border IS the active rung in both modes (light since the ladder landed, dark by this
  // ruling). A border drawn on an `background-active` fill is therefore 1.000:1 by design, and the pair
  // that matters - a hovered stroke on that fill - is the strong stroke, measured here.
  it('records the accepted border-on-active pair with its ratio', () => {
    MODES.forEach((mode) => {
      expect(resolved(mode, FAMILY)).toBe(resolved(mode, '--color-background-active'));
      expect(
        contrastRatio(resolved(mode, '--color-surface-border-hover'), resolved(mode, '--color-background-active')),
        `${mode} hover on active`,
      ).toBeGreaterThanOrEqual(1.12);
    });
  });
});

// The status shade family states a ROLE, not a mode (RULING-2026-10-23-status-shade-roles): in `.dark`
// the `-light` names held deep shades and `-dark` pale ones, so toast.tsx re-applied the flip under
// `dark:` and painted the foreground tone at 20% - measured 1.48:1 against the page where the bare
// token's 1.89:1 already worked. The names are `-subtle` (the tint a surface paints) and `-strong` (the
// text it carries) in both modes; the values did not move.
const STATUS_FAMILIES = ['success', 'warning', 'error', 'info'] as const;

describe('the status shade family', () => {
  it('names a role, not a mode, in both blocks', () => {
    MODES.forEach((mode) => {
      STATUS_FAMILIES.forEach((family) => {
        [`--color-${family}-subtle`, `--color-${family}-strong`].forEach((name) =>
          expect(declaredValues[mode][name], `${mode} ${name}`).toBeDefined(),
        );
        // The mode names are what let a `dark:` compensation look correct; they must not come back.
        ['light', 'dark'].forEach((suffix) =>
          expect(declaredValues[mode][`--color-${family}-${suffix}`], `${mode} --color-${family}-${suffix}`)
            .toBeUndefined(),
        );
      });
    });
  });

  it('paints its strong foreground on its subtle tint at AA in both modes', () => {
    MODES.forEach((mode) => {
      STATUS_FAMILIES.forEach((family) => {
        const ratio = contrastRatio(
          resolved(mode, `--color-${family}-strong`),
          resolved(mode, `--color-${family}-subtle`),
        );
        // 4.5 is the floor for this application's body text; the pair sits at 4.84 minimum today.
        expect(ratio, `${mode} ${family} strong on subtle = ${ratio.toFixed(3)}:1`).toBeGreaterThanOrEqual(4.5);
      });
    });
  });
});
