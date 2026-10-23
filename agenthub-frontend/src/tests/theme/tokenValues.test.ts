import { describe, expect, it } from 'vitest';
import { parseTokenSource, tokenValues, valueOf } from '../../theme/tokenValues';

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

  it('ignores a brace inside a comment instead of ending the block on it', () => {
    // Before the strip moved to the front of the scan, a `}` inside a comment closed `:root` there and
    // every token below it read as undeclared - the message blamed the token, not the parse.
    const body = [
      '  --color-background: #ffffff;',
      '  --color-secondary: var(--color-accent);',
      '  --color-accent: #4f46e5;',
    ];
    const source = (comment: string) =>
      [':root {', ...(comment ? [`  /* ${comment} */`] : []), ...body, '}', '.dark {', '  --color-background: #0b1020;', '  --color-secondary: var(--color-accent);', '  --color-accent: #818cf8;', '}'].join('\n');
    const bare = parseTokenSource(source(''));
    // A brace in a comment changes nothing: same declarations, same resolved values, both modes.
    expect(parseTokenSource(source('the light } ground'))).toEqual(bare);
    expect(parseTokenSource(source('{ and }'))).toEqual(bare);
    expect(bare.resolved.light['--color-secondary']).toBe('#4f46e5');
    expect(bare.declared.dark['--color-secondary']).toBe('var(--color-accent)');
  });

  it('throws for a name no block declares, in either mode', () => {
    expect(() => valueOf('light', '--color-no-such-token')).toThrow(/no --color-no-such-token/);
    expect(() => valueOf('dark', '--color-no-such-token')).toThrow(/no --color-no-such-token/);
  });
});
