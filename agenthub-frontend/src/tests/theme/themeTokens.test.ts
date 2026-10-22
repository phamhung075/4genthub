import { contrastRatio, luminanceOf, resolvedTokenOf, tokenOf } from './cssTokens';

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

// RULING-2026-10-23-dark-border-collision.md. A stroke must not resolve to the
// value of a fill it can sit on: dark's border used to BE the tertiary rung
// (#26314a), so the six `.theme-*` panels and the four /tokens cards drew a
// 1.000:1 outline. The ruled fix moved the stroke family up one step rather than
// moving a fill, and this arm is what keeps it moved.
//
// Rule 1 names five fills, not "any fill", and the omission is deliberate:
// light's border IS the active rung by the design the ladder landed (#e2e8f0),
// and a hover drawn on an active fill takes the strong stroke. Both grounds are
// page/transient, and the floor below is what pins their separation.
describe('the stroke family (RULING-2026-10-23-dark-border-collision.md)', () => {
  const MODES: [string, string][] = [
    ['light', ':root'],
    ['dark', '.dark'],
  ];
  const FILLS = [
    '--color-background-secondary',
    '--color-background-tertiary',
    '--color-background-hover',
    '--color-surface',
    '--color-surface-raised',
  ];
  const STROKES = [
    '--color-surface-border',
    '--color-surface-border-strong',
    '--color-surface-border-hover',
  ];

  it.each(MODES)('%s: no stroke resolves equal to a fill a card takes', (mode, selector) => {
    const fills = FILLS.map((name) => [name, resolvedTokenOf(selector, name)] as const);
    STROKES.forEach((stroke) => {
      const value = resolvedTokenOf(selector, stroke);
      fills.forEach(([fill, fillValue]) => {
        expect(value, `${stroke} resolves equal to ${fill}`).not.toBe(fillValue);
      });
    });
  });

  // The hairline floor the ruling measured: light's accepted border is 1.125 on
  // tertiary, so the floor cannot go higher without repainting light. Dark after
  // the change is 1.251 on tertiary and 1.676 on surface.
  it.each(MODES)('%s: the border clears the hairline floor', (mode, selector) => {
    const border = resolvedTokenOf(selector, '--color-surface-border');
    expect(
      contrastRatio(border, resolvedTokenOf(selector, '--color-background-tertiary')),
      `${mode} border on a tertiary fill`
    ).toBeGreaterThanOrEqual(1.12);
    expect(
      contrastRatio(border, resolvedTokenOf(selector, '--color-surface')),
      `${mode} border on the surface`
    ).toBeGreaterThanOrEqual(1.2);
  });

  it.each(MODES)('%s: hover and input-border resolve through strong', (mode, selector) => {
    const strong = resolvedTokenOf(selector, '--color-surface-border-strong');
    expect(tokenOf(selector, '--color-surface-border-hover')).toBe('var(--color-surface-border-strong)');
    expect(tokenOf(selector, '--color-input-border')).toBe('var(--color-surface-border-strong)');
    expect(resolvedTokenOf(selector, '--color-surface-border-hover')).toBe(strong);
    expect(resolvedTokenOf(selector, '--color-input-border')).toBe(strong);
  });
});
