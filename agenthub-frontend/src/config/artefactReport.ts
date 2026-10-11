// The two INDEPENDENT axes of a frontend build's artefact, as pure functions (row 2dd4448e).
//
// WHY THIS IS NOT ONE QUESTION. The mistake this module exists to prevent is printing a CONFIGURED
// value as though it described the artefact. There are two axes, and each has a cause and an
// observation of its own:
//
//   REACT RESOLUTION   cause: NODE_ENV          observation: the `Minified React error` marker
//   MINIFICATION       cause: build.minify      observation: mean bytes per line
//
// MINIFICATION IS NOT DECIDED BY NODE_ENV. Vite defaults `build.minify` to 'esbuild'
// (node_modules/vite/dist/node/index.d.ts: "Set to `false` to disable minification", "@default
// 'esbuild'") and nothing in this config sets it, so BOTH of this repo's families are minified.
// That is why this tree's development build is minified, and why the retired 100-newline threshold
// confirmed the false `unminified` label instead of catching it: 245 newlines IS the minified
// reading for development React.
//
// THE OBSERVATION IS A MEAN, AND ONLY EVER A MEAN. Measured bytes per line:
//
//   development React, minified     2,290   (561,199 B / 245)
//   production React,  minified     7,668   (299,046 B / 39; the served entry is 7,726)
//   production React,  unminified      41   (758,581 B / 18,313)
//   development React, unminified    42.9   (1,308,462 B / 30,472)
//
// so the floor clears 4.6x below the minified floor and 11.6x above the unminified ceiling. TWO
// PROPERTIES OF THE MEAN FOLLOW FROM THOSE FOUR POINTS, and the constant depends on both:
//
//   - UNMINIFIED the mean is nearly family-INDEPENDENT: 41.4 (production content) against 42.9
//     (development content).
//   - MINIFIED it is family-DEPENDENT: 2,290 (development) against 7,726 (served production), a
//     3.4x spread.
//
// so the TIGHTEST margin above the floor is the minified development side at 4.6x, and that is the
// number to keep if anyone proposes moving the constant DOWN.
//
// A MEAN
// and a MAXIMUM are different instruments that can disagree in principle - one enormous line among
// thousands of short ones reads high by longest-line and low by mean - so longest-line readings
// (122,845 / 95,067 / 2,714) are NOT on this scale and must never be quoted against this floor.
//
// A LIMIT THAT MUST TRAVEL WITH IT: the ratio observes the minifier's OUTPUT, not its DECISION. A
// minifier configured to emit one statement per line defeats any density threshold. That is exactly
// why the resolved lever is reported as the CAUSE beside it and the guard compares the two, rather
// than either standing alone.

export const MINIFIED_BYTES_PER_LINE_FLOOR = 500

export type ReactResolution = 'production' | 'development'

/** What `build.minify` is typed as; `false` is the only value that turns minification off. */
export type MinifyLever = boolean | 'terser' | 'esbuild' | undefined

export interface ArtefactInput {
  bytes: number
  newlines: number
  /** The `Minified React error` string, which only the production React build contains. */
  markerPresent: boolean
  nodeEnv: string | undefined
  /** Read from the resolved config (`config.build.minify`), never inferred. */
  configuredMinify: MinifyLever
}

export interface ArtefactReport {
  bytes: number
  newlines: number
  markerPresent: boolean
  bytesPerLine: number
  reactFromNodeEnv: ReactResolution
  reactObserved: ReactResolution
  configuredSaysMinified: boolean
  observedMinified: boolean
  /** The deployable shape: production React AND minified. */
  isDeployShape: boolean
  familyLabel: string
  /** Cause-versus-observation disagreements, on either axis. Empty when the two agree. */
  mismatches: string[]
}

export function describeArtefact(input: ArtefactInput): ArtefactReport {
  // A single-line file has no newline to divide by; its whole size is its one line.
  const bytesPerLine = input.newlines > 0 ? input.bytes / input.newlines : input.bytes
  const reactFromNodeEnv: ReactResolution = input.nodeEnv === 'production' ? 'production' : 'development'
  const reactObserved: ReactResolution = input.markerPresent ? 'production' : 'development'
  // `false` is the only lever position that disables minification - in a real build this is the
  // resolved 'esbuild' (measured), so there is no default to supply here.
  const configuredSaysMinified = input.configuredMinify !== false
  const observedMinified = bytesPerLine >= MINIFIED_BYTES_PER_LINE_FLOOR
  const isDeployShape = reactObserved === 'production' && observedMinified

  const mismatches: string[] = []
  if (configuredSaysMinified !== observedMinified) {
    mismatches.push(
      `build.minify ${configuredSaysMinified ? 'says minified' : 'says unminified'} but the entry reads ` +
        `${bytesPerLine.toFixed(1)} bytes/line (floor ${MINIFIED_BYTES_PER_LINE_FLOOR}) - the configured decision did not take effect.`
    )
  }
  if (reactFromNodeEnv !== reactObserved) {
    mismatches.push(
      `NODE_ENV ${input.nodeEnv ?? '(unset)'} says ${reactFromNodeEnv} React but the ` +
        `'Minified React error' marker is ${input.markerPresent ? 'present' : 'absent'} - the bundle does not carry it.`
    )
  }

  return {
    bytes: input.bytes,
    newlines: input.newlines,
    markerPresent: input.markerPresent,
    bytesPerLine,
    reactFromNodeEnv,
    reactObserved,
    configuredSaysMinified,
    observedMinified,
    isDeployShape,
    // The label reads the OBSERVATION. It names the React resolution and deployability and asserts
    // nothing about minification, so it cannot be false when the configured value is right.
    familyLabel: `${reactObserved.toUpperCase()} React - ${isDeployShape ? 'the deploy family' : 'NOT the deploy family'}`,
    mismatches
  }
}
