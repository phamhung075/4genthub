/**
 * mcp block form - publish ONE MCP server as a module version.
 *
 * The D4 fallback for a server the catalog does not carry: one server, named by
 * its server key, with its transport and either a URL plus headers (http) or a
 * command plus args (stdio). A block never carries a secret: a value that needs
 * one names an environment variable as ${VAR}, which the client runtime expands,
 * and the same credential scanner the server uses refuses a literal here too.
 *
 * Paste or open a .json block to fill the fields; the file is read in the browser
 * from the user's own picker - nothing is fetched and no path is sent anywhere.
 *
 * @module components/seats/McpBlockForm
 * @version 1.0.0
 */

import React, { useState } from 'react';
import { AlertCircle, FileUp, Loader2 } from 'lucide-react';
import { Alert, AlertDescription } from '../ui/alert';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Select } from '../ui/select-simple';
import { Textarea } from '../ui/textarea';
import { usePublishModuleVersion } from '../../hooks/useSeats';
import { parseMcpBlock, serializeMcpBlock } from '../../lib/mcpBlock';
import {
  MODULE_CONTENT_MAX_BYTES,
  MODULE_SLUG_MESSAGE,
  MODULE_SLUG_PATTERN,
  MODULE_VERSION_MESSAGE,
  MODULE_VERSION_PATTERN,
} from '../../lib/seatNames';
import { MCP_SERVER_TYPES, type McpServerBlock, type McpServerType } from '../../types/seatTypes';

interface McpFormState {
  slug: string;
  version: string;
  name: string;
  type: McpServerType;
  url: string;
  headersText: string;
  command: string;
  argsText: string;
  envText: string;
}

const EMPTY_FORM: McpFormState = {
  slug: '',
  version: '',
  name: '',
  type: 'http',
  url: '',
  headersText: '',
  command: '',
  argsText: '',
  envText: '',
};

const linesOf = (text: string): string[] =>
  text
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line !== '');

function keyValueFromLines(text: string, separator: ':' | '='): Record<string, string> {
  const entries: Record<string, string> = {};
  for (const line of linesOf(text)) {
    const at = line.indexOf(separator);
    if (at <= 0) continue;
    const key = line.slice(0, at).trim();
    const value = line.slice(at + 1).trim();
    if (key !== '') entries[key] = value;
  }
  return entries;
}

function serverFromForm(form: McpFormState): McpServerBlock {
  if (form.type === 'http') {
    return {
      name: form.name.trim(),
      type: 'http',
      url: form.url.trim(),
      headers: keyValueFromLines(form.headersText, ':'),
    };
  }
  return {
    name: form.name.trim(),
    type: 'stdio',
    command: form.command.trim(),
    args: linesOf(form.argsText).flatMap((line) => line.split(/\s+/)),
    env: keyValueFromLines(form.envText, '='),
  };
}

function formFromServer(slug: string, version: string, server: McpServerBlock): McpFormState {
  const pairs = (values?: Record<string, string>, separator = ':') =>
    Object.entries(values ?? {})
      .map(([key, value]) => `${key}${separator} ${value}`)
      .join('\n');
  return {
    slug,
    version,
    name: server.name,
    type: server.type,
    url: server.url ?? '',
    headersText: pairs(server.headers),
    command: server.command ?? '',
    argsText: (server.args ?? []).join('\n'),
    envText: pairs(server.env, '='),
  };
}

export const McpBlockForm: React.FC = () => {
  const publish = usePublishModuleVersion();
  const [form, setForm] = useState<McpFormState>(EMPTY_FORM);
  const [pasteText, setPasteText] = useState('');
  const [loadError, setLoadError] = useState<string | null>(null);

  const content = serializeMcpBlock(serverFromForm(form));
  const parsed = parseMcpBlock(content);
  const slugValid = MODULE_SLUG_PATTERN.test(form.slug);
  const versionValid = MODULE_VERSION_PATTERN.test(form.version);
  const contentBytes = new TextEncoder().encode(content).length;
  const valid = slugValid && versionValid && parsed.ok && contentBytes <= MODULE_CONTENT_MAX_BYTES;

  const loadBlock = (text: string, source: 'paste' | 'file') => {
    let slug = form.slug;
    let version = form.version;
    try {
      const parsedJson = JSON.parse(text) as unknown;
      if (parsedJson !== null && typeof parsedJson === 'object' && !Array.isArray(parsedJson)) {
        const record = parsedJson as Record<string, unknown>;
        if (typeof record.slug === 'string') slug = record.slug;
        if (typeof record.version === 'string') version = record.version;
      }
    } catch {
      // A block's own JSON is the server object; a slug/version wrapper is optional.
    }
    const result = parseMcpBlock(text);
    if (!result.ok) {
      setLoadError(result.error);
      return;
    }
    setLoadError(null);
    setForm(formFromServer(slug, version, result.server));
    if (source === 'paste') setPasteText(text);
  };

  const handleFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    loadBlock(await file.text(), 'file');
    event.target.value = '';
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!valid || !parsed.ok) return;
    publish.mutate(
      { slug: form.slug, version: form.version, kind: 'mcp', content },
      {
        onSuccess: () => {
          setForm(EMPTY_FORM);
          setPasteText('');
          setLoadError(null);
        },
      }
    );
  };

  const set = <K extends keyof McpFormState>(key: K, value: McpFormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Publish one MCP server as a block</CardTitle>
        <CardDescription>
          One block mounts one whole server. A secret is never typed into a block: reference it as{' '}
          <code>{'${ENV_VAR}'}</code> (for example <code>Authorization: Bearer {'${AGENTHUB_TOKEN}'}</code>), and{' '}
          <code>{'${AGENTHUB_MCP_URL}'}</code> is the platform endpoint the server substitutes when it renders the
          seat. Per-tool narrowing stays in the permission layer and is not part of a block.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-end gap-3 rounded-md border border-surface-border-hover p-3">
          <div className="w-56 space-y-1">
            <label className="text-sm font-medium" htmlFor="mcp-paste">
              Paste a block (JSON)
            </label>
            <Textarea
              id="mcp-paste"
              aria-label="Paste a block"
              className="min-h-[64px] font-mono"
              value={pasteText}
              onChange={(event) => setPasteText(event.target.value)}
            />
          </div>
          <Button type="button" variant="outline" onClick={() => loadBlock(pasteText, 'paste')} disabled={!pasteText.trim()}>
            Load block
          </Button>
          <label className="flex items-center gap-2 text-sm">
            <FileUp className="h-4 w-4" />
            <input type="file" accept=".json,application/json" aria-label="Upload a block file" onChange={handleFile} />
          </label>
        </div>

        {loadError && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{loadError}</AlertDescription>
          </Alert>
        )}

        <form className="space-y-3" onSubmit={handleSubmit}>
          <div className="grid gap-3 sm:grid-cols-4">
            <div className="space-y-1">
              <label className="text-sm font-medium" htmlFor="mcp-slug">
                Mcp block slug
              </label>
              <Input
                id="mcp-slug"
                aria-label="Mcp block slug"
                value={form.slug}
                onChange={(event) => set('slug', event.target.value)}
                placeholder="my-server"
              />
              {form.slug !== '' && !slugValid && <p className="text-xs text-destructive">{MODULE_SLUG_MESSAGE}</p>}
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium" htmlFor="mcp-version">
                Mcp block version
              </label>
              <Input
                id="mcp-version"
                aria-label="Mcp block version"
                value={form.version}
                onChange={(event) => set('version', event.target.value)}
                placeholder="1.0.0"
              />
              {form.version !== '' && !versionValid && (
                <p className="text-xs text-destructive">{MODULE_VERSION_MESSAGE}</p>
              )}
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium" htmlFor="mcp-name">
                Server name
              </label>
              <Input
                id="mcp-name"
                aria-label="Server name"
                value={form.name}
                onChange={(event) => set('name', event.target.value)}
                placeholder="my-server"
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium" htmlFor="mcp-type">
                Type
              </label>
              <Select
                id="mcp-type"
                aria-label="Server type"
                value={form.type}
                onChange={(event) => set('type', event.target.value as McpServerType)}
              >
                {MCP_SERVER_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          {form.type === 'http' ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <label className="text-sm font-medium" htmlFor="mcp-url">
                  URL
                </label>
                <Input
                  id="mcp-url"
                  aria-label="Server url"
                  value={form.url}
                  onChange={(event) => set('url', event.target.value)}
                  placeholder="https://example.test/mcp"
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium" htmlFor="mcp-headers">
                  Headers (one <code>Name: value</code> per line)
                </label>
                <Textarea
                  id="mcp-headers"
                  aria-label="Server headers"
                  className="min-h-[64px] font-mono"
                  value={form.headersText}
                  onChange={(event) => set('headersText', event.target.value)}
                  placeholder={'Authorization: Bearer ${AGENTHUB_TOKEN}'}
                />
              </div>
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="space-y-1">
                <label className="text-sm font-medium" htmlFor="mcp-command">
                  Command
                </label>
                <Input
                  id="mcp-command"
                  aria-label="Server command"
                  value={form.command}
                  onChange={(event) => set('command', event.target.value)}
                  placeholder="npx"
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium" htmlFor="mcp-args">
                  Args (one per line)
                </label>
                <Textarea
                  id="mcp-args"
                  aria-label="Server args"
                  className="min-h-[64px] font-mono"
                  value={form.argsText}
                  onChange={(event) => set('argsText', event.target.value)}
                  placeholder={'-y\n@modelcontextprotocol/server-sequential-thinking'}
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium" htmlFor="mcp-env">
                  Env (one <code>NAME=value</code> per line)
                </label>
                <Textarea
                  id="mcp-env"
                  aria-label="Server env"
                  className="min-h-[64px] font-mono"
                  value={form.envText}
                  onChange={(event) => set('envText', event.target.value)}
                  placeholder={'API_KEY=${MY_KEY}'}
                />
              </div>
            </div>
          )}

          <div className="space-y-1">
            <p className="text-xs text-base-secondary">Block content that will be published</p>
            <pre aria-label="Block content" className="overflow-x-auto rounded-md border border-surface-border-hover p-3 font-mono text-xs">
              {content}
            </pre>
            {!parsed.ok && <p className="text-xs text-destructive">{parsed.error}</p>}
            {contentBytes > MODULE_CONTENT_MAX_BYTES && (
              <p className="text-xs text-destructive">
                Content is {contentBytes} bytes; the limit is {MODULE_CONTENT_MAX_BYTES}.
              </p>
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
            Publish block
          </Button>
        </form>
      </CardContent>
    </Card>
  );
};
