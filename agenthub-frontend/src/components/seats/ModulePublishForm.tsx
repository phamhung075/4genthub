/**
 * Module publish form - create a module, or edit a block and publish a NEW version of it.
 *
 * WHY THE PREFILL IS NOT COSMETIC. A published version is immutable ON THE WIRE: the route refuses a
 * second PUT of the same slug@version carrying different content with a 409, and a repeat with
 * IDENTICAL content is a no-op that writes nothing. So "edit a block's text in place" cannot mean
 * rewriting a version - it means publishing a NEW one - and the two cases are therefore decided
 * HERE, before any request, rather than on the wire: an untouched block has nothing to publish, and
 * a changed block left on its original version would earn exactly the 409 the route would send back.
 * The kind is fixed while editing for the same reason: a module's kind is set on its first publish
 * and a different one is refused.
 *
 * @module components/seats/ModulePublishForm
 */

import React, { useEffect, useState } from 'react';
import { AlertCircle, Loader2 } from 'lucide-react';
import { Alert, AlertDescription } from '../ui/alert';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Select } from '../ui/select-simple';
import { Textarea } from '../ui/textarea';
import { useModuleVersion, usePublishModuleVersion } from '../../hooks/useSeats';
import {
  MODULE_CONTENT_MAX_BYTES,
  MODULE_SLUG_MESSAGE,
  MODULE_SLUG_PATTERN,
  MODULE_VERSION_MESSAGE,
  MODULE_VERSION_PATTERN,
} from '../../lib/seatNames';
import { SEAT_MODULE_KINDS } from '../../types/seatTypes';
import { parseMcpBlock } from '../../lib/mcpBlock';
import type { ModuleSummary, SeatModuleKind } from '../../types/seatTypes';

/**
 * The block shape the form needs: its REAL slug, version and kind. Exported so the callers that
 * hand a block in - a modules row and the composer's edit row - and the page's editing selection
 * name ONE type rather than repeating this Pick in three places and drifting apart.
 */
export type EditableBlock = Pick<ModuleSummary, 'slug' | 'version' | 'kind'>;

export interface ModulePublishFormProps {
  /**
   * A block to EDIT. Its REAL slug, version and kind are carried into the form, and its content is
   * loaded so the two refusals above can be decided. Absent or null creates a new module.
   */
  block?: EditableBlock | null;
  /** After a successful publish, so a caller can drop its editing selection. */
  onPublished?: () => void;
  /** When the caller's editing selection should be dropped WITHOUT publishing. */
  onCancelEdit?: () => void;
}

const EMPTY_FORM = { slug: '', version: '', kind: 'instruction' as SeatModuleKind, content: '' };

export const ModulePublishForm: React.FC<ModulePublishFormProps> = ({
  block = null,
  onPublished,
  onCancelEdit,
}) => {
  const publish = usePublishModuleVersion();
  const [form, setForm] = useState(EMPTY_FORM);
  /** The block AS LOADED: what "unchanged" and "the original version" are measured against. */
  const [baseline, setBaseline] = useState<{ version: string; content: string } | null>(null);

  const editing = block !== null;
  const { module: loaded, isLoading, error } = useModuleVersion(block?.slug ?? null, block?.version ?? null);

  // The seed is read as PRIMITIVES so the effect's dependencies are stable across keystrokes: keying
  // on the block OBJECT would re-seed the form on every render for a caller that rebuilds an
  // equivalent object, and the kind comes from the loaded module rather than the row that asked for
  // it, so the form carries the kind the server will actually check.
  const seedSlug = block?.slug ?? '';
  const seedVersion = block?.version ?? '';
  const seedKind = loaded?.kind ?? block?.kind ?? null;
  const seedContent = loaded ? loaded.content : null;

  useEffect(() => {
    if (!seedSlug) {
      setForm(EMPTY_FORM);
      setBaseline(null);
      return;
    }
    if (seedKind === null || seedContent === null) {
      return;
    }
    setForm({ slug: seedSlug, version: seedVersion, kind: seedKind, content: seedContent });
    setBaseline({ version: seedVersion, content: seedContent });
  }, [seedSlug, seedVersion, seedKind, seedContent]);

  const slugValid = MODULE_SLUG_PATTERN.test(form.slug);
  const versionValid = MODULE_VERSION_PATTERN.test(form.version);
  const contentBytes = new TextEncoder().encode(form.content).length;
  const contentValid = contentBytes > 0 && contentBytes <= MODULE_CONTENT_MAX_BYTES;
  // An mcp module's content is ONE server block that the renderer parses. THE PUBLISH ROUTE REFUSES AN
  // UNRENDERABLE CONTENT ITSELF (`ValidateModuleContent`, seat_admin_mount.go:926 - a 400, or a 422 when it
  // carries a credential shape), so this mirror is a PREVIEW of that gate rather than the only check: it
  // decides before the request what the server would decide with a 400, from the same rule set. That was
  // not always so - when this guard was written the route checked only the KIND (measured then: 200 for
  // `{"kind":"mcp","content":"not a block"}`), so the mirror WAS the whole gate, and that history is why
  // its parity with mcpblock.Parse is pinned by tests rather than assumed.
  const mcpBlock = form.kind === 'mcp' ? parseMcpBlock(form.content) : null;
  const blockValid = mcpBlock === null || mcpBlock.ok;

  // THE TWO REFUSALS, decided before the request. Both mirror a rule the route enforces, so the wire
  // answer would be a 409 either way; deciding here is what keeps the user out of it.
  const contentChanged = baseline !== null && form.content !== baseline.content;
  const versionReused = baseline !== null && form.version === baseline.version;
  const nothingToPublish = baseline !== null && !contentChanged && versionReused;
  const needsNewVersion = baseline !== null && contentChanged && versionReused;
  /** Editing a block whose content never loaded: there is no baseline to compare an edit against. */
  const awaitingBaseline = editing && baseline === null;

  const valid = slugValid && versionValid && contentValid && blockValid;
  const publishable = valid && !nothingToPublish && !needsNewVersion && !awaitingBaseline;

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!publishable) {
      return;
    }
    publish.mutate(form, {
      onSuccess: () => {
        setForm(EMPTY_FORM);
        setBaseline(null);
        onPublished?.();
      },
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          {editing ? `Publish a new version of ${block.slug}` : 'Publish a module version'}
        </CardTitle>
        <CardDescription>
          {editing
            ? 'Prefilled from the block. Versions are immutable, so an edit is published as a NEW version - the version below must differ from the one being edited.'
            : 'Versions are immutable: publishing an existing version again with different content is rejected. A new slug creates the module.'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form className="space-y-3" onSubmit={handleSubmit}>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-1">
              <label className="text-sm font-medium" htmlFor="module-slug">
                Slug
              </label>
              <Input
                id="module-slug"
                aria-label="Module slug"
                value={form.slug}
                disabled={awaitingBaseline}
                onChange={e => setForm(prev => ({ ...prev, slug: e.target.value }))}
                placeholder="code-review-rules"
              />
              {form.slug !== '' && !slugValid && (
                <p className="text-xs text-destructive">{MODULE_SLUG_MESSAGE}</p>
              )}
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium" htmlFor="module-version">
                Version
              </label>
              <Input
                id="module-version"
                aria-label="Module version"
                value={form.version}
                disabled={awaitingBaseline}
                onChange={e => setForm(prev => ({ ...prev, version: e.target.value }))}
                placeholder="1.0.0"
              />
              {form.version !== '' && !versionValid && (
                <p className="text-xs text-destructive">{MODULE_VERSION_MESSAGE}</p>
              )}
              {needsNewVersion && (
                <p className="text-xs text-destructive">
                  {block ? `${block.slug}@${block.version}` : 'This version'} already exists with different
                  content, and publishing is refused unless the version changes.
                </p>
              )}
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium" htmlFor="module-kind">
                Kind
              </label>
              <Select
                id="module-kind"
                aria-label="Module kind"
                value={form.kind}
                disabled={editing}
                onChange={e => setForm(prev => ({ ...prev, kind: e.target.value as SeatModuleKind }))}
              >
                {SEAT_MODULE_KINDS.map(kind => (
                  <option key={kind} value={kind}>
                    {kind}
                  </option>
                ))}
              </Select>
              {editing && (
                <p className="text-xs text-muted-foreground">
                  A module&apos;s kind is set on its first publish; a different one is refused.
                </p>
              )}
            </div>
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium" htmlFor="module-content">
              Content
            </label>
            <Textarea
              id="module-content"
              aria-label="Module content"
              className="min-h-[160px] font-mono"
              value={form.content}
              disabled={awaitingBaseline}
              onChange={e => setForm(prev => ({ ...prev, content: e.target.value }))}
            />
            {contentBytes > MODULE_CONTENT_MAX_BYTES && (
              <p className="text-xs text-destructive">
                Content is {contentBytes} bytes; the limit is {MODULE_CONTENT_MAX_BYTES}.
              </p>
            )}
            {mcpBlock && !mcpBlock.ok && (
              <p className="text-xs text-destructive">Not a server block: {mcpBlock.error}</p>
            )}
          </div>
          {editing && isLoading && (
            <p className="text-sm text-muted-foreground" role="status">
              Loading the block&apos;s content...
            </p>
          )}
          {editing && error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error.message}</AlertDescription>
            </Alert>
          )}
          {nothingToPublish && (
            <p className="text-sm text-muted-foreground" role="status">
              Nothing to publish: this block&apos;s content and version are unchanged.
            </p>
          )}
          {publish.isError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{publish.error.message}</AlertDescription>
            </Alert>
          )}
          <div className="flex items-center gap-2">
            <Button type="submit" disabled={!publishable || publish.isPending}>
              {publish.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              {editing ? 'Publish new version' : 'Publish'}
            </Button>
            {editing && (
              <Button type="button" variant="outline" onClick={() => onCancelEdit?.()}>
                Stop editing
              </Button>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
};
