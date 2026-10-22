import { describe, expect, it } from 'vitest';
import { tokenValues, valueOf } from '../../theme/tokenValues';

describe('tokenValues', () => {
  it('resolves an alias to its target value in both modes', () => {
    expect(tokenValues.dark['--color-secondary']).toBe(tokenValues.dark['--color-accent']);
    expect(tokenValues.light['--color-secondary']).toBe(tokenValues.light['--color-accent']);
  });

  it('leaves no var() behind, in either mode', () => {
    Object.entries(tokenValues).forEach(([mode, values]) => {
      Object.entries(values).forEach(([name, value]) => {
        expect(value, `${mode} ${name}`).not.toContain('var(');
      });
    });
  });

  it('reads each mode from its own block', () => {
    expect(tokenValues.dark['--color-background']).not.toBe(tokenValues.light['--color-background']);
    expect(tokenValues.light['--color-background']).toMatch(/^#[0-9a-f]{6}$/i);
    expect(tokenValues.dark['--color-background']).toMatch(/^#[0-9a-f]{6}$/i);
  });

  it('throws for a name no block declares, in either mode', () => {
    expect(() => valueOf('light', '--color-no-such-token')).toThrow(/no --color-no-such-token/);
    expect(() => valueOf('dark', '--color-no-such-token')).toThrow(/no --color-no-such-token/);
  });
});
