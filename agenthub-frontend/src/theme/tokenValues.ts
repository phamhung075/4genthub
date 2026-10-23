import css from '../styles/theme.css?raw';

// theme.css is the only file that authors a colour value, and this module reads
// it: the MUI palette needs CONCRETE colours, not `var()` strings. `createTheme`
// accepts a `var()` string, but six of the components this app mounts run colour
// maths on the palette value and throw `MUI: Unsupported `var(--color-…)` color`
// at render - Alert, Button, Checkbox, Divider, IconButton and a TextField with
// an adornment - and src has no error boundary, so the whole tree unmounts and
// the auth pages render blank. Hence: resolve the tokens here, per mode, and let
// the palette carry the literals. Light and dark therefore differ in their
// VALUES, not only in `mode` - which is the point of a token layer.
export type TokenMode = 'light' | 'dark';

const SELECTOR: Record<TokenMode, string> = { light: ':root', dark: '.dark' };

/** Comments removed BEFORE anything is scanned: a `}` inside a comment would end a block early, and the
 * token that vanished would be reported as undeclared - the message would blame a token the file
 * declares, which is the one failure mode this module must not have (architect's nit, ruled one line). */
const stripComments = (text: string): string => text.replace(/\/\*[\s\S]*?\*\//g, '');

/** The declarations between a selector's braces. */
const blockOf = (source: string, selector: string): string => {
  const start = source.indexOf(`${selector} {`);
  if (start < 0) throw new Error(`theme.css has no ${selector} block`);
  const open = source.indexOf('{', start);
  let depth = 0;
  for (let i = open; i < source.length; i += 1) {
    if (source[i] === '{') depth += 1;
    else if (source[i] === '}') {
      depth -= 1;
      if (depth === 0) return source.slice(open + 1, i);
    }
  }
  throw new Error(`theme.css's ${selector} block is not closed`);
};

const valuesOf = (source: string, selector: string): { declared: Record<string, string>; resolved: Record<string, string> } => {
  const declared = new Map<string, string>();
  for (const match of blockOf(source, selector).matchAll(/(--[a-z0-9-]+)\s*:\s*([^;]+);/g)) {
    declared.set(match[1], match[2].trim());
  }
  // An alias is `var(--other)` and nothing else: `--color-secondary` is
  // `var(--color-accent)`. Anything else - a hex, an rgb(), a gradient - is a
  // value in its own right and passes through verbatim.
  const resolve = (name: string, seen: readonly string[] = []): string => {
    const value = declared.get(name);
    if (value === undefined) throw new Error(`${selector} declares no ${name}`);
    const alias = /^var\((--[a-z0-9-]+)\)$/.exec(value);
    if (!alias) return value;
    if (seen.includes(name)) throw new Error(`${selector}: var() cycle ${[...seen, name].join(' -> ')}`);
    return resolve(alias[1], [...seen, name]);
  };
  return {
    declared: Object.fromEntries(declared),
    resolved: Object.fromEntries([...declared.keys()].map((name) => [name, resolve(name)])),
  };
};

/** A `--name` to value map, one per mode. */
type ByMode = { light: Record<string, string>; dark: Record<string, string> };

/** The exported seam the tests drive: the same parse the module runs on the imported stylesheet, so a
 * comment containing a brace is exercised without planting graffiti in theme.css. */
export const parseTokenSource = (raw: string): { declared: ByMode; resolved: ByMode } => {
  const source = stripComments(raw);
  const light = valuesOf(source, SELECTOR.light);
  const dark = valuesOf(source, SELECTOR.dark);
  return {
    declared: { light: light.declared, dark: dark.declared },
    resolved: { light: light.resolved, dark: dark.resolved },
  };
};

const parsed = parseTokenSource(css);

/** Every custom property in `:root` (light) and `.dark`, aliases resolved. */
export const tokenValues: ByMode = parsed.resolved;

/** The same declarations as written: `var(--color-x)` for an alias, the literal otherwise. */
export const declaredValues: ByMode = parsed.declared;

/** The concrete value of a token in one mode; a name the layer does not declare throws. */
export const valueOf = (mode: TokenMode, name: string): string => {
  const value = tokenValues[mode][name];
  if (value === undefined) throw new Error(`theme.css declares no ${name} for ${mode}`);
  return value;
};
