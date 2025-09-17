import * as hooks from '../../hooks/index';
import { useTheme } from '../../hooks/useTheme';

// Mock the useTheme hook
jest.mock('../../hooks/useTheme', () => ({
  useTheme: jest.fn(),
}));

describe('hooks/index', () => {
  it('exports useTheme hook', () => {
    expect(hooks.useTheme).toBeDefined();
    expect(hooks.useTheme).toBe(useTheme);
  });

  it('only exports expected hooks', () => {
    const exportedHooks = Object.keys(hooks);
    expect(exportedHooks).toEqual(['useTheme']);
  });

  it('maintains the same reference to imported hooks', () => {
    const { useTheme: firstImport } = hooks;
    const { useTheme: secondImport } = hooks;
    
    expect(firstImport).toBe(secondImport);
    expect(firstImport).toBe(useTheme);
  });

  it('exports are functions (when not mocked)', () => {
    // This test verifies the type of exports
    expect(typeof hooks.useTheme).toBe('function');
  });

  it('can be destructured', () => {
    const { useTheme: destructuredHook } = hooks;
    expect(destructuredHook).toBe(useTheme);
  });

  it('can be imported with namespace', () => {
    const allHooks = hooks;
    expect(allHooks.useTheme).toBe(useTheme);
  });
});