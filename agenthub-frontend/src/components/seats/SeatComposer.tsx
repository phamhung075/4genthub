/**
 * SeatComposer - the block composition surface for one seat.
 *
 * Adds and removes ONE block at a time at a chosen level (company, room or seat),
 * and shows for every block where it is inherited from and what a removal at this
 * level does. The vocabulary and the refusals come from the backend resolver
 * (`resolver.go`): a block already in effect cannot be added and a block not in
 * effect cannot be removed, so neither is offered as a silent no-op.
 *
 * @module components/seats/SeatComposer
 * @version 1.0.0
 */

import React, { useMemo, useState } from 'react';
import { Boxes, Minus, Pencil, Plus, RotateCcw, Trash2 } from 'lucide-react';
import { Alert, AlertDescription } from '../ui/alert';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Select } from '../ui/select-simple';
import {
  additionOutcome,
  blocksAtScope,
  composeBlocks,
  originLabel,
  removalOutcome,
  withAddedBlock,
  withRemovedBlock,
  withRestoredBlock,
  type BlockAtScope,
} from '../../lib/blockComposition';
import { mcpServerLabel } from '../../lib/mcpBlock';
import type { McpServerEntry } from '../../hooks/useSeats';
import type { EditableBlock } from './ModulePublishForm';
import type {
  ModuleSummary,
  SeatModuleKind,
  SeatOverlayOp,
  SeatOverlayScope,
  SeatOverlays,
  SeatType,
} from '../../types/seatTypes';

export interface SeatComposerProps {
  room: string;
  seat: string;
  seatType: SeatType | undefined;
  modules: ModuleSummary[];
  overlays: SeatOverlays;
  /** Parsed mcp servers by module slug, so an mcp block is named by its server. */
  mcpServers?: Record<string, McpServerEntry>;
  isSaving: boolean;
  saveError: string | null;
  onApply: (scope: SeatOverlayScope, ops: SeatOverlayOp[]) => void;
  /**
   * Hands ONE block to an editor OUTSIDE this component - the slug the row shows, the version IN
   * EFFECT at this level, and its kind. OPTIONAL, and the affordance is rendered only when a caller
   * asks for it: the composer is otherwise a read-and-arrange surface.
   */
  onEditBlock?: (block: EditableBlock) => void;
}

const SCOPE_LABEL: Record<SeatOverlayScope, string> = {
  company: 'Company',
  room: 'Room',
  seat: 'Seat',
};

/**
 * The five purposes the composer groups blocks by, IN THIS ORDER. The order is fixed so the view
 * does not reshuffle as blocks are added, and it is asserted by the purpose test.
 */
export const BLOCK_PURPOSES = ['guide', 'policy', 'tools-mcp', 'skills', 'documents'] as const;
export type BlockPurpose = (typeof BLOCK_PURPOSES)[number];

export const PURPOSE_LABEL: Record<BlockPurpose, string> = {
  guide: 'Guide',
  policy: 'Policy',
  'tools-mcp': 'Tools / MCP',
  skills: 'Skills',
  documents: 'Documents and memory',
};

/**
 * Which kinds each purpose owns. THE UNION EQUALS SEAT_MODULE_KINDS AND NO KIND APPEARS TWICE -
 * both asserted by the purpose test, so a kind added in Go fails there instead of silently
 * vanishing from this view.
 */
const PURPOSE_KINDS: Record<BlockPurpose, SeatModuleKind[]> = {
  guide: ['instruction'],
  policy: ['policy', 'tool'],
  'tools-mcp': ['mcp'],
  skills: ['skill'],
  documents: ['document', 'memory'],
};

/**
 * The two slug families that OVERRIDE their kind, each with the reason it exists:
 *  - `mcp-*`: `mcp-usage` is KindInstruction while its own comment in seedlibrary.go calls it the
 *    seat's MCP guidance, so the kind alone would file it under Guide.
 *  - `delegate-*`: `delegate-deepseek` is KindInstruction while it tells a seat to use the deepseek
 *    tool (scripts/team/4genthub/team.json), so it belongs where the tools are.
 */
const MCP_FAMILY_PREFIXES = ['mcp-', 'delegate-'];

/**
 * The purpose a block belongs to: the slug family first, then the kind.
 *
 * The `guide` fallback cannot be reached while the mirror holds - the purpose test fails first if a
 * kind has no purpose - and it exists so an unrecognised kind still renders somewhere rather than
 * throwing inside the list.
 */
export function purposeOf(slug: string, kind: SeatModuleKind): BlockPurpose {
  if (MCP_FAMILY_PREFIXES.some((prefix) => slug.startsWith(prefix))) {
    return 'tools-mcp';
  }
  return BLOCK_PURPOSES.find((purpose) => PURPOSE_KINDS[purpose].includes(kind)) ?? 'guide';
}

/** The kinds one purpose owns, exported so the test asserts against the SAME source the view uses. */
export function kindsOfPurpose(purpose: BlockPurpose): SeatModuleKind[] {
  return PURPOSE_KINDS[purpose];
}

const ABSENT_BLOCK: BlockAtScope = { slug: '', present: false, block: null, removedHere: false };

export const SeatComposer: React.FC<SeatComposerProps> = ({
  room,
  seat,
  seatType,
  modules,
  overlays,
  mcpServers = {},
  isSaving,
  saveError,
  onApply,
  onEditBlock,
}) => {
  const [scope, setScope] = useState<SeatOverlayScope>('seat');
  const [addSlug, setAddSlug] = useState('');
  const [addVersion, setAddVersion] = useState('');

  const composition = useMemo(
    () => composeBlocks(seatType?.module_refs ?? [], overlays),
    [seatType, overlays]
  );
  const rows = useMemo(() => blocksAtScope(composition, scope), [composition, scope]);
  const bySlug = useMemo(() => {
    const lookup: Record<string, BlockAtScope> = {};
    rows.forEach((row) => {
      lookup[row.slug] = row;
    });
    return lookup;
  }, [rows]);

  const kindBySlug = useMemo(() => {
    const lookup: Record<string, string> = {};
    modules.forEach((module) => {
      lookup[module.slug] = module.kind;
    });
    return lookup;
  }, [modules]);

  const scopeOps = overlays[scope]?.ops ?? [];
  const presentRows = rows.filter((row) => row.present);
  const absentRows = rows.filter((row) => !row.present);

  // Blocks are grouped by PURPOSE for the view, not by kind: two purposes own two kinds each, and
  // the slug families above override the kind. A block whose kind the modules list does not carry
  // falls back to `instruction` here and lands in Guide, which is where an unknown block was
  // rendered before this grouping existed.
  const rowsByPurpose = useMemo(() => {
    const grouped: Record<BlockPurpose, BlockAtScope[]> = {
      guide: [],
      policy: [],
      'tools-mcp': [],
      skills: [],
      documents: [],
    };
    presentRows.forEach((row) => {
      const kind = (kindBySlug[row.slug] ?? 'instruction') as SeatModuleKind;
      grouped[purposeOf(row.slug, kind)].push(row);
    });
    return grouped;
  }, [presentRows, kindBySlug]);

  const selectedEntry = addSlug ? bySlug[addSlug] ?? { ...ABSENT_BLOCK, slug: addSlug } : ABSENT_BLOCK;
  const addOutcome = additionOutcome(selectedEntry, scope);
  const canAdd = addSlug !== '' && addVersion.trim() !== '' && addOutcome.allowed;

  const handleAdd = () => {
    onApply(scope, withAddedBlock(scopeOps, addSlug, addVersion.trim()));
    setAddSlug('');
    setAddVersion('');
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Compose this seat</CardTitle>
        <CardDescription>
          Blocks resolve in order - company, then room, then seat. Add or remove one block at a time at the level
          below; each block shows where it is inherited from and what removing it here does.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-end gap-3">
          <div className="w-48">
            <label className="text-sm font-medium" htmlFor="composer-scope">
              Level
            </label>
            <Select
              id="composer-scope"
              aria-label="Compose level"
              value={scope}
              onChange={(event) => setScope(event.target.value as SeatOverlayScope)}
            >
              <option value="company">Company</option>
              <option value="room">Room · {room}</option>
              <option value="seat">Seat · {seat}</option>
            </Select>
          </div>
          <p className="text-xs text-base-secondary">
            Editing the <strong>{SCOPE_LABEL[scope]}</strong> overlay. Removals here apply to this seat; blocks
            still defined above stay defined for everyone below them.
          </p>
        </div>

        {saveError && (
          <Alert variant="destructive">
            <AlertDescription>{saveError}</AlertDescription>
          </Alert>
        )}

        <ul
          role="list"
          aria-label="Composed blocks"
          className="divide-y divide-surface-border-hover rounded-md border border-surface-border-hover"
        >
          {BLOCK_PURPOSES.map((purpose) => (
            <React.Fragment key={purpose}>
              <li className="px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-base-secondary">
                {PURPOSE_LABEL[purpose]}
              </li>
              {rowsByPurpose[purpose].length === 0 && (
                <li className="px-3 py-2 text-sm text-base-secondary">
                  No {PURPOSE_LABEL[purpose]} blocks at this level.
                </li>
              )}
              {rowsByPurpose[purpose].map((row) => {
            const block = row.block;
            if (!block) return null;
            const outcome = removalOutcome(row, scope);
            const editKind = kindBySlug[row.slug] as SeatModuleKind | undefined;
            const mcpEntry = mcpServers[row.slug];
            const mcpLabel =
              kindBySlug[row.slug] === 'mcp'
                ? mcpEntry && mcpEntry.parse.ok
                  ? mcpServerLabel(mcpEntry.parse.server)
                  : 'mcp server (unparsed)'
                : null;
            return (
              <li key={row.slug} className="px-3 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Boxes className="h-4 w-4 shrink-0 text-teal-500" />
                  <span className="font-medium text-base-primary">
                    {row.slug}@{block.version}
                  </span>
                  <Badge variant={block.origin === scope ? 'default' : 'secondary'}>
                    {block.origin === scope
                      ? `added at ${scope}`
                      : `inherited from ${originLabel(block.origin)}`}
                  </Badge>
                  {mcpLabel && <Badge variant="outline">{mcpLabel}</Badge>}
                  {block.pinnedAt && (
                    // `data-pinned-at` is an automation hook, not user-facing copy: the property
                    // test asserts WHICH SCOPE the label names and that it claims nothing more,
                    // so the wording itself stays free to change without rewriting the test.
                    <Badge variant="outline" data-pinned-at={block.pinnedAt}>
                      pinned at {originLabel(block.pinnedAt)}
                    </Badge>
                  )}
                  {block.overridden && <Badge variant="outline">overridden</Badge>}
                  <div className="ml-auto flex items-center gap-2">
                    {/* WHAT AN EDIT CARRIES, and why it is the ROW's version rather than the modules
                        list's: the list holds each module's LATEST published version, while a
                        composed block is the version IN EFFECT here - so a pinned block would be
                        edited, and republished, from a tree the user is not looking at. The KIND
                        comes from the list because a composed block carries none; a slug the list
                        does not carry gets NO affordance rather than one that opens a form which
                        cannot be filled. The visible label matches the Modules row's; the
                        accessible name carries the version so the two entry points stay apart. */}
                    {onEditBlock && editKind && (
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        aria-label={`Edit and publish block ${row.slug}@${block.version}`}
                        onClick={() =>
                          onEditBlock({ slug: row.slug, version: block.version, kind: editKind })
                        }
                      >
                        <Pencil className="h-4 w-4" />
                        Edit and publish
                      </Button>
                    )}
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      disabled={isSaving}
                      onClick={() => onApply(scope, withRemovedBlock(scopeOps, row.slug))}
                    >
                      <Minus className="h-4 w-4" />
                      Remove here
                    </Button>
                  </div>
                </div>
                <p className="mt-1 text-xs text-base-secondary">Removing here: {outcome.label}</p>
                {block.pinnedAt && (
                  <p className="mt-1 text-xs text-base-secondary">
                    A pin sets the version in effect at {originLabel(block.pinnedAt)} for this block and
                    does nothing else - it is not a lock, so removing the block still removes it.
                  </p>
                )}
              </li>
            );
              })}
            </React.Fragment>
          ))}

          {absentRows.map((row) => {
            const outcome = removalOutcome(row, scope);
            return (
              <li key={row.slug} className="flex flex-wrap items-center gap-2 px-3 py-2 text-sm text-base-secondary">
                <Boxes className="h-4 w-4 shrink-0 opacity-40" />
                <span className="font-medium">{row.slug}</span>
                <span className="text-xs">{outcome.reason}</span>
                {row.removedHere && (
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="ml-auto"
                    disabled={isSaving}
                    onClick={() => onApply(scope, withRestoredBlock(scopeOps, row.slug))}
                  >
                    <RotateCcw className="h-4 w-4" />
                    Restore
                  </Button>
                )}
              </li>
            );
          })}

          {presentRows.length === 0 && absentRows.length === 0 && (
            <li className="px-3 py-3 text-sm text-base-secondary">
              No blocks yet. Add one below, or publish a module and add it to the seat type.
            </li>
          )}
        </ul>

        <div className="flex flex-wrap items-end gap-3 rounded-md border border-surface-border-hover p-3">
          <div className="w-56">
            <label className="text-sm font-medium" htmlFor="composer-add-slug">
              Add a block
            </label>
            <Select
              id="composer-add-slug"
              aria-label="Add a block"
              value={addSlug}
              onChange={(event) => setAddSlug(event.target.value)}
            >
              <option value="">Choose a module…</option>
              {modules.map((module) => {
                const outcome = additionOutcome(
                  bySlug[module.slug] ?? { ...ABSENT_BLOCK, slug: module.slug },
                  scope
                );
                const entry = mcpServers[module.slug];
                const mcpInvalid = module.kind === 'mcp' && entry !== undefined && !entry.parse.ok;
                const label =
                  module.kind === 'mcp' && entry && entry.parse.ok
                    ? `${module.slug} — ${mcpServerLabel(entry.parse.server)}`
                    : module.slug;
                return (
                  <option
                    key={module.slug}
                    value={module.slug}
                    disabled={!outcome.allowed || mcpInvalid}
                  >
                    {label}
                    {mcpInvalid ? ' (invalid server)' : outcome.allowed ? '' : ' (already in effect)'}
                  </option>
                );
              })}
            </Select>
          </div>
          <div className="w-32">
            <label className="text-sm font-medium" htmlFor="composer-add-version">
              Version
            </label>
            <Input
              id="composer-add-version"
              aria-label="Block version"
              value={addVersion}
              placeholder="1.0.0"
              onChange={(event) => setAddVersion(event.target.value)}
            />
          </div>
          <Button type="button" disabled={!canAdd || isSaving} onClick={handleAdd}>
            <Plus className="h-4 w-4" />
            Add at {SCOPE_LABEL[scope]}
          </Button>
          {!addOutcome.allowed && addSlug !== '' && (
            <p className="w-full text-xs text-base-secondary">{addOutcome.reason}</p>
          )}
        </div>

        {scopeOps.length > 0 && (
          <div>
            <p className="mb-1 text-xs uppercase tracking-wide text-base-secondary">
              {SCOPE_LABEL[scope]} overlay ops ({scopeOps.length})
            </p>
            <ul role="list" className="space-y-1">
              {scopeOps.map((op, index) => (
                <li key={`${op.kind}-${op.slug}-${index}`} className="flex items-center gap-2 text-sm">
                  <Badge variant="outline">{op.kind}</Badge>
                  <span className="font-mono text-xs">
                    {op.slug}
                    {op.version ? `@${op.version}` : ''}
                  </span>
                  <Button
                    type="button"
                    size="icon"
                    variant="ghost"
                    aria-label={`Delete ${op.kind} ${op.slug}`}
                    disabled={isSaving}
                    onClick={() => onApply(scope, scopeOps.filter((_, i) => i !== index))}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
