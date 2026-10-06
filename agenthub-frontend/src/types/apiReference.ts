/**
 * The generated API reference - the docs page's reference tier (DOCS-PAGE.md, step 1).
 *
 * THE GENERATOR EMITS DATA AND IMPORTS THESE TYPES FROM HERE. There is exactly one
 * definition of this concept and it is this file: go-dev2 declares nothing, the module in
 * `src/docs` exports a const typed by these interfaces, and the page's component takes that
 * const as a prop. Two definitions would let the generator drift away from the page
 * silently, which is why the seam is a type we own rather than a type each side writes.
 *
 * The field semantics below are the generator's, taken from the Go code it reads, so the
 * prose here is a description of what is emitted rather than a proposal about it.
 *
 * @module types/apiReference
 * @version 1.0.0
 */

/** One mounted HTTP route, as the generator reads it from the `*_mount.go` files. */
export interface ApiRouteEntry {
  /** The HTTP method as registered, e.g. `GET`, `POST`, `PATCH`. */
  method: string;
  /** The path pattern EXACTLY as registered, including any `{param}` segments. */
  path: string;
  /** The parameter names extracted from the pattern, in the order they appear. */
  pathParams: string[];
  /**
   * The named function the mount registers.
   * EMPTY WHEN THE MOUNT IS AN INLINE CLOSURE - a legitimate state, not missing data.
   */
  handler: string;
  /** The named handler's Go doc comment when it has one; empty otherwise. */
  description: string;
}

/** One MCP tool, as the generator reads it from the tool's registration site. */
export interface ApiToolEntry {
  /** The tool name, as advertised. */
  name: string;
  /** The tool's description, as registered. */
  description: string;
  /**
   * The tool's parameter schema, VERBATIM as the server advertises it - the JSON schema
   * object itself rather than a translation of it, so the page cannot document a shape the
   * server does not accept.
   */
  parameters: Record<string, unknown>;
  /**
   * The enum of the schema's `action` property.
   * EMPTY WHEN THE TOOL TAKES NO ACTION PARAMETER - a legitimate state, not missing data.
   */
  actions: string[];
}

/**
 * What the generated module exports: one const of this shape, from `src/docs`.
 * Both arrays are complete by construction - the drift test fails when a route or tool
 * exists in code with no entry here, and when an entry names no route or tool.
 */
export interface ApiReference {
  routes: ApiRouteEntry[];
  tools: ApiToolEntry[];
}
