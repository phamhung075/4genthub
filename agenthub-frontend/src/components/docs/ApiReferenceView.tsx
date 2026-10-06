/**
 * ApiReferenceView - the docs page's reference tier, rendered (DOCS-PAGE.md step 1).
 *
 * IT RENDERS THE DATA IT IS GIVEN AND NOTHING ELSE. The generated module is a BUILD-TIME
 * import, so the reference is a REQUIRED prop: an absent reference is a compile error at the
 * caller, and there is deliberately no loading state and no failure state here. A branch for
 * a failure that cannot happen is unreachable code that reads as diligence.
 *
 * TWO STATES ARE LEGITIMATE RATHER THAN MISSING, and both render as ABSENT rather than as an
 * error or a placeholder: `handler` is empty when a mount registers an inline closure, and
 * `actions` is empty when a tool takes no `action` parameter. Nothing on this page may claim
 * that an absence of data is a failure, or the other way round.
 *
 * THE SCHEMA IS RENDERED VERBATIM, WITH A SUMMARY DERIVED FROM THAT SAME SCHEMA - never a
 * hand-typed list and never a translation that could disagree with the server: the JSON block
 * is what the server advertises, and the property table is read out of that block, so this
 * component cannot become a second source of truth about a shape.
 *
 * @module components/docs/ApiReferenceView
 * @version 1.0.0
 */

import React from 'react';
import { Badge } from '../ui/badge';
import type { ApiReference } from '../../types/apiReference';

export interface ApiReferenceViewProps {
  /** The generated reference. REQUIRED - see the module note: an absent reference is a compile error. */
  reference: ApiReference;
}

/** One row of the property summary, DERIVED from the schema rather than declared. */
interface PropertyRow {
  name: string;
  /** The schema's `type` for this property, or null when it states none - never invented. */
  type: string | null;
  required: boolean;
}

/**
 * Read the property summary out of a parameter schema. Returns an empty list when the schema
 * is not an object with `properties`, which is a legitimate shape rather than a defect: the
 * verbatim block below still carries whatever the server advertised.
 */
export function summariseProperties(parameters: Record<string, unknown>): PropertyRow[] {
  const statedProperties = parameters.properties;
  if (typeof statedProperties !== 'object' || statedProperties === null || Array.isArray(statedProperties)) {
    return [];
  }
  const requiredNames = Array.isArray(parameters.required)
    ? parameters.required.filter((name): name is string => typeof name === 'string')
    : [];
  return Object.entries(statedProperties).map(([name, schema]) => {
    const statedType =
      typeof schema === 'object' && schema !== null && 'type' in schema ? schema.type : undefined;
    return {
      name,
      type: typeof statedType === 'string' ? statedType : null,
      required: requiredNames.includes(name),
    };
  });
}

export const ApiReferenceView: React.FC<ApiReferenceViewProps> = ({ reference }) => (
  <div className="space-y-10">
    <section aria-labelledby="api-reference-routes">
      <h2 id="api-reference-routes" className="text-lg font-semibold text-base-primary">
        HTTP routes
      </h2>
      <p className="mb-3 text-sm text-base-secondary">
        {reference.routes.length} {reference.routes.length === 1 ? 'route' : 'routes'}, generated from the
        mounts rather than typed by hand.
      </p>
      <ul role="list" className="divide-y divide-surface-border-hover rounded-md border border-surface-border-hover">
        {reference.routes.map((route) => (
          <li key={`${route.method} ${route.path}`} className="px-3 py-2">
            <div className="flex flex-wrap items-baseline gap-2">
              <Badge variant="outline">{route.method}</Badge>
              <span className="font-mono text-sm text-base-primary">{route.path}</span>
              {/* Absent when the mount is an inline closure: omitted, never filled with a placeholder. */}
              {route.handler && (
                <span className="font-mono text-xs text-base-secondary">{route.handler}</span>
              )}
            </div>
            {route.description && (
              <p className="mt-1 text-sm text-base-secondary">{route.description}</p>
            )}
          </li>
        ))}
      </ul>
    </section>

    <section aria-labelledby="api-reference-tools">
      <h2 id="api-reference-tools" className="text-lg font-semibold text-base-primary">
        MCP tools
      </h2>
      <p className="mb-3 text-sm text-base-secondary">
        {reference.tools.length} {reference.tools.length === 1 ? 'tool' : 'tools'}, with the parameters the
        server advertises.
      </p>
      <div className="space-y-4">
        {reference.tools.map((tool) => {
          const properties = summariseProperties(tool.parameters);
          return (
            <article
              key={tool.name}
              aria-labelledby={`api-reference-tool-${tool.name}`}
              className="rounded-md border border-surface-border-hover px-3 py-3"
            >
              <h3
                id={`api-reference-tool-${tool.name}`}
                className="font-mono text-sm font-semibold text-base-primary"
              >
                {tool.name}
              </h3>
              {tool.description && (
                <p className="mt-1 text-sm text-base-secondary">{tool.description}</p>
              )}
              {/* Absent when the tool takes no action parameter: no badges are rendered at all. */}
              {tool.actions.length > 0 && (
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <span className="text-xs uppercase tracking-wide text-base-secondary">Actions</span>
                  {tool.actions.map((action) => (
                    <Badge key={action} variant="secondary">
                      {action}
                    </Badge>
                  ))}
                </div>
              )}

              <p className="mt-3 text-xs uppercase tracking-wide text-base-secondary">Parameters</p>
              {/* The server's own schema, verbatim: the page cannot document a shape it does not have. */}
              <pre className="mt-1 overflow-x-auto rounded bg-surface-hover p-2 font-mono text-xs text-base-primary">
                {JSON.stringify(tool.parameters, null, 2)}
              </pre>

              {properties.length > 0 && (
                <ul role="list" className="mt-2 space-y-1">
                  {properties.map((property) => (
                    <li key={property.name} className="flex flex-wrap items-baseline gap-2 text-sm">
                      <span className="font-mono text-base-primary">{property.name}</span>
                      {property.type && (
                        <span className="font-mono text-xs text-base-secondary">{property.type}</span>
                      )}
                      {property.required && <Badge variant="outline">required</Badge>}
                    </li>
                  ))}
                </ul>
              )}
            </article>
          );
        })}
      </div>
    </section>
  </div>
);
