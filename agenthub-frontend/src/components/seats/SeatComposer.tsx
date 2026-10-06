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
import { Boxes, Minus, Plus, RotateCcw, Trash2 } from 'lucide-react';
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
import type {
  ModuleSummary,
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
}

const SCOPE_LABEL: Record<SeatOverlayScope, string> = {
  company: 'Company',
  room: 'Room',
  seat: 'Seat',
};

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
          {presentRows.map((row) => {
            const block = row.block;
            if (!block) return null;
            const outcome = removalOutcome(row, scope);
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
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="ml-auto"
                    disabled={isSaving}
                    onClick={() => onApply(scope, withRemovedBlock(scopeOps, row.slug))}
                  >
                    <Minus className="h-4 w-4" />
                    Remove here
                  </Button>
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
