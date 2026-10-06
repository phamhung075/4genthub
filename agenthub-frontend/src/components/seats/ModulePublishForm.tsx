/**
 * Module publish form - create a module or publish a new immutable version.
 *
 * @module components/seats/ModulePublishForm
 */

import React, { useState } from 'react';
import { AlertCircle, Loader2 } from 'lucide-react';
import { Alert, AlertDescription } from '../ui/alert';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Select } from '../ui/select-simple';
import { Textarea } from '../ui/textarea';
import { usePublishModuleVersion } from '../../hooks/useSeats';
import {
  MODULE_CONTENT_MAX_BYTES,
  MODULE_SLUG_MESSAGE,
  MODULE_SLUG_PATTERN,
  MODULE_VERSION_MESSAGE,
  MODULE_VERSION_PATTERN,
} from '../../lib/seatNames';
import { SEAT_MODULE_KINDS } from '../../types/seatTypes';
import { parseMcpBlock } from '../../lib/mcpBlock';
import type { SeatModuleKind } from '../../types/seatTypes';

const EMPTY_FORM = { slug: '', version: '', kind: 'instruction' as SeatModuleKind, content: '' };

export const ModulePublishForm: React.FC = () => {
  const publish = usePublishModuleVersion();
  const [form, setForm] = useState(EMPTY_FORM);

  const slugValid = MODULE_SLUG_PATTERN.test(form.slug);
  const versionValid = MODULE_VERSION_PATTERN.test(form.version);
  const contentBytes = new TextEncoder().encode(form.content).length;
  const contentValid = contentBytes > 0 && contentBytes <= MODULE_CONTENT_MAX_BYTES;
  // An mcp module's content is ONE server block that the renderer parses, and the publish route only
  // checks the kind, not the block - measured: `{"kind":"mcp","content":"not a block"}` is accepted
  // (200). So a plain-text publish here would be refused later, by some seat's resolve. The same mirror
  // the MCP block form uses decides it before the request.
  const mcpBlock = form.kind === 'mcp' ? parseMcpBlock(form.content) : null;
  const blockValid = mcpBlock === null || mcpBlock.ok;
  const valid = slugValid && versionValid && contentValid && blockValid;

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!valid) {
      return;
    }
    publish.mutate(form, { onSuccess: () => setForm(EMPTY_FORM) });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Publish a module version</CardTitle>
        <CardDescription>
          Versions are immutable: publishing an existing version again with different content is rejected.
          A new slug creates the module.
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
                onChange={e => setForm(prev => ({ ...prev, version: e.target.value }))}
                placeholder="1.0.0"
              />
              {form.version !== '' && !versionValid && (
                <p className="text-xs text-destructive">{MODULE_VERSION_MESSAGE}</p>
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
                onChange={e => setForm(prev => ({ ...prev, kind: e.target.value as SeatModuleKind }))}
              >
                {SEAT_MODULE_KINDS.map(kind => (
                  <option key={kind} value={kind}>
                    {kind}
                  </option>
                ))}
              </Select>
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
          {publish.isError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{publish.error.message}</AlertDescription>
            </Alert>
          )}
          <Button type="submit" disabled={!valid || publish.isPending}>
            {publish.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Publish
          </Button>
        </form>
      </CardContent>
    </Card>
  );
};
