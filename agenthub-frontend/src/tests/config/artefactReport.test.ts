import { describe, it, expect } from 'vitest';

import { describeArtefact, MINIFIED_BYTES_PER_LINE_FLOOR, type ArtefactInput } from '../../config/artefactReport';

// The measured artefacts the axis was calibrated on, held as inputs rather than prose: every case
// below is one of these four, or one field moved off one of them, so a failure names a real build.
const SHARED_TREE_DEV = {
  bytes: 561_199,
  newlines: 245,
  markerPresent: false,
  nodeEnv: 'development',
  configuredMinify: 'esbuild',
} satisfies ArtefactInput;

const DEPLOY_PRODUCTION = {
  bytes: 299_046,
  newlines: 39,
  markerPresent: true,
  nodeEnv: 'production',
  configuredMinify: 'esbuild',
} satisfies ArtefactInput;

const PRODUCTION_MINIFY_FALSE = {
  bytes: 758_581,
  newlines: 18_313,
  markerPresent: true,
  nodeEnv: 'production',
  configuredMinify: false,
} satisfies ArtefactInput;

const DEV_REACT_MINIFY_FALSE = {
  bytes: 1_308_462,
  newlines: 30_472,
  markerPresent: false,
  nodeEnv: 'development',
  configuredMinify: false,
} satisfies ArtefactInput;

describe('describeArtefact', () => {
  it('reads the mean from bytes and newlines, and never divides by zero', () => {
    expect(describeArtefact(SHARED_TREE_DEV).bytesPerLine).toBeCloseTo(2290.6, 1);
    expect(describeArtefact(DEPLOY_PRODUCTION).bytesPerLine).toBeCloseTo(7668, 0);
    const singleLine = describeArtefact({ ...SHARED_TREE_DEV, newlines: 0 });
    expect(Number.isFinite(singleLine.bytesPerLine)).toBe(true);
    expect(singleLine.observedMinified).toBe(true);
  });

  // THE LIVE CASE THE ONE-DIRECTIONAL GUARD MISSED: development React, MINIFIED. The retired guard
  // fired only on `isProduction && newlines > 100`, so this artefact went unremarked while the report
  // called it "(unminified)" - 245 newlines IS the minified reading for development React.
  it('calls a minified development-React entry minified, and never labels it unminified', () => {
    const report = describeArtefact(SHARED_TREE_DEV);
    expect(report.observedMinified).toBe(true);
    expect(report.reactObserved).toBe('development');
    expect(report.familyLabel).not.toMatch(/unminified/);
    expect(report.familyLabel).toBe('DEVELOPMENT React - NOT the deploy family');
    // The configuration and the observation agree, so there is nothing to warn about on this axis.
    expect(report.mismatches).toEqual([]);
  });

  it('calls the deploy artefact the deploy shape, with both causes agreeing', () => {
    const report = describeArtefact(DEPLOY_PRODUCTION);
    expect(report.isDeployShape).toBe(true);
    expect(report.familyLabel).toBe('PRODUCTION React - the deploy family');
    expect(report.mismatches).toEqual([]);
  });

  // THE CASE THAT SEPARATES "not deployable" FROM "configuration and observation disagree": the
  // recorded --minify false run. The lever says unminified and the entry IS unminified, so the guard
  // must stay silent here and only the not-the-deploy-artefact warning applies.
  it('does not call production React built with --minify false a mismatch', () => {
    const report = describeArtefact(PRODUCTION_MINIFY_FALSE);
    expect(report.observedMinified).toBe(false);
    expect(report.configuredSaysMinified).toBe(false);
    expect(report.isDeployShape).toBe(false);
    expect(report.mismatches).toEqual([]);
  });

  // BOTH DIRECTIONS, so a one-sided guard cannot pass this suite.
  it('reports a mismatch when the configured minifier did not take effect', () => {
    const report = describeArtefact({ ...PRODUCTION_MINIFY_FALSE, configuredMinify: 'esbuild' });
    expect(report.mismatches).toHaveLength(1);
    expect(report.mismatches[0]).toContain('build.minify says minified');
    expect(report.mismatches[0]).toContain('41.4 bytes/line');
  });

  it('reports a mismatch in the other direction, when a minified entry was configured off', () => {
    const report = describeArtefact({ ...SHARED_TREE_DEV, configuredMinify: false });
    expect(report.mismatches).toHaveLength(1);
    expect(report.mismatches[0]).toContain('build.minify says unminified');
  });

  it('watches the React axis, because the family label is read from the marker', () => {
    const report = describeArtefact({ ...DEPLOY_PRODUCTION, markerPresent: false });
    expect(report.reactFromNodeEnv).toBe('production');
    expect(report.reactObserved).toBe('development');
    expect(report.mismatches).toHaveLength(1);
    expect(report.mismatches[0]).toContain("'Minified React error' marker is absent");
    expect(report.familyLabel).toBe('DEVELOPMENT React - NOT the deploy family');
  });

  it('places the floor between the measured families, with the margin on the minified dev side', () => {
    expect(describeArtefact(SHARED_TREE_DEV).bytesPerLine).toBeGreaterThan(MINIFIED_BYTES_PER_LINE_FLOOR * 4);
    expect(describeArtefact(DEV_REACT_MINIFY_FALSE).bytesPerLine).toBeLessThan(MINIFIED_BYTES_PER_LINE_FLOOR / 11);
    expect(describeArtefact(DEPLOY_PRODUCTION).bytesPerLine).toBeGreaterThan(MINIFIED_BYTES_PER_LINE_FLOOR);
    // Exactly on the floor counts as minified.
    expect(describeArtefact({ ...SHARED_TREE_DEV, bytes: 50_000, newlines: 100 }).observedMinified).toBe(true);
    expect(describeArtefact({ ...SHARED_TREE_DEV, bytes: 49_999, newlines: 100 }).observedMinified).toBe(false);
  });
});
