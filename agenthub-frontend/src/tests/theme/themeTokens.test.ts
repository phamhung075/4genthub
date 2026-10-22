import { resolvedTokenOf, tokenOf } from './cssTokens';

// The arms that read the token map itself. The JS palette that used to mirror
// these values is gone: MUI now names the same tokens, so what a reader needs
// proven here is that the map owns its hues and that its surface ladder holds -
// not that a second copy agrees with it.

// R1: the palette must not own a brand hue. Primary, secondary and the buttons
// alias the accent, read here from the CSS that actually paints the app, so a
// second source cannot drift back in unnoticed.
describe('the palette owns no brand hue', () => {
  it.each([
    ['light', ':root'],
    ['dark', '.dark'],
  ])('%s: primary, secondary and the buttons alias the accent', (mode, selector) => {
    expect(tokenOf(selector, '--color-primary')).toBe('var(--color-accent)');
    expect(tokenOf(selector, '--color-secondary')).toBe('var(--color-accent)');
    expect(resolvedTokenOf(selector, '--color-button-primary-bg')).toBe(
      resolvedTokenOf(selector, '--color-accent')
    );
    expect(resolvedTokenOf(selector, '--color-button-primary-hover')).toBe(
      resolvedTokenOf(selector, '--color-accent-hover')
    );
    expect(resolvedTokenOf(selector, '--color-button-primary-text')).toBe(
      resolvedTokenOf(selector, '--color-accent-contrast')
    );
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
