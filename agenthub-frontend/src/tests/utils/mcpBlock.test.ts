/**
 * @fileoverview mcpBlock mirrors the Go mcpblock.Parse rules and the eight
 * credential shapes secretscan refuses, so a bad block is refused in the form.
 */

import {
  carriesCredentialShape,
  mcpServerLabel,
  parseMcpBlock,
  serializeMcpBlock,
  PLATFORM_MCP_URL_PLACEHOLDER,
} from '../../lib/mcpBlock';

const HTTP_BLOCK = JSON.stringify({
  name: 'agenthub_http',
  type: 'http',
  url: PLATFORM_MCP_URL_PLACEHOLDER,
  headers: { Accept: 'application/json, text/event-stream', Authorization: 'Bearer ${AGENTHUB_TOKEN}' },
});

const STDIO_BLOCK = JSON.stringify({
  name: 'sequential-thinking',
  type: 'stdio',
  command: 'npx',
  args: ['-y', '@modelcontextprotocol/server-sequential-thinking'],
});

describe('parseMcpBlock', () => {
  it('accepts an http server whose url and header reference the platform and an env var', () => {
    const result = parseMcpBlock(HTTP_BLOCK);

    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.server).toEqual({
      name: 'agenthub_http',
      type: 'http',
      url: PLATFORM_MCP_URL_PLACEHOLDER,
      headers: { Accept: 'application/json, text/event-stream', Authorization: 'Bearer ${AGENTHUB_TOKEN}' },
    });
  });

  it('accepts a stdio server with a command and args', () => {
    const result = parseMcpBlock(STDIO_BLOCK);

    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.server.name).toBe('sequential-thinking');
    expect(result.server.type).toBe('stdio');
    expect(result.server.args).toEqual(['-y', '@modelcontextprotocol/server-sequential-thinking']);
  });

  const rejected: Array<[string, string, string]> = [
    ['not JSON', 'not json', 'content is not one JSON value'],
    ['an array', '[1,2]', 'content is not a server object'],
    ['an unknown field', JSON.stringify({ name: 'a', type: 'stdio', command: 'x', tools: [] }), 'unknown field tools'],
    ['a missing name', JSON.stringify({ type: 'stdio', command: 'x' }), 'field name is required'],
    ['a bad type', JSON.stringify({ name: 'a', type: 'socket', command: 'x' }), 'field type must be "http" or "stdio"'],
    ['an http server without a url', JSON.stringify({ name: 'a', type: 'http' }), 'field url is required for a "http" server'],
    ['an http server with a command', JSON.stringify({ name: 'a', type: 'http', url: 'https://x.test', command: 'npx' }), 'takes url and headers'],
    ['a stdio server without a command', JSON.stringify({ name: 'a', type: 'stdio' }), 'field command is required for a "stdio" server'],
    ['a stdio server with a url', JSON.stringify({ name: 'a', type: 'stdio', command: 'npx', url: 'https://x.test' }), 'takes command, args and env'],
    ['a url that is neither http(s) nor a reference', JSON.stringify({ name: 'a', type: 'http', url: 'ftp://x.test' }), 'url must be http(s)'],
  ];

  it.each(rejected)('refuses %s with the reason', (_case, content, expected) => {
    const result = parseMcpBlock(content);

    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error).toContain(expected);
  });

  it('accepts an EMPTY string on the transport the block does not use, as the Go parser does', () => {
    // Go tests server.Command != "" and server.URL != "", so an empty string on the
    // unused transport is not a contradiction. Presence alone was the TS divergence.
    const stdioWithEmptyUrl = parseMcpBlock(
      JSON.stringify({ name: 'a', type: 'stdio', command: 'x', url: '' })
    );
    expect(stdioWithEmptyUrl.ok).toBe(true);

    const httpWithEmptyCommand = parseMcpBlock(
      JSON.stringify({ name: 'a', type: 'http', url: 'https://x.test', command: '' })
    );
    expect(httpWithEmptyCommand.ok).toBe(true);
  });

  it('still refuses a NON-empty field on the wrong transport, and the empty-headers control keeps agreeing', () => {
    expect(
      parseMcpBlock(JSON.stringify({ name: 'a', type: 'stdio', command: 'x', url: 'https://x.test' })).ok
    ).toBe(false);
    expect(
      parseMcpBlock(JSON.stringify({ name: 'a', type: 'http', url: 'https://x.test', command: 'npx' })).ok
    ).toBe(false);
    // The control: Go's len(server.Headers) > 0 is false for {}, so this agrees.
    expect(
      parseMcpBlock(JSON.stringify({ name: 'a', type: 'stdio', command: 'x', headers: {} })).ok
    ).toBe(true);
  });

  it('refuses a credential-shaped value with the reference-a-secret message', () => {
    const result = parseMcpBlock(
      JSON.stringify({ name: 'a', type: 'http', url: 'https://x.test', headers: { Authorization: 'Bearer sk-abcdefghijklmnopqrstuvwx' } })
    );

    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error).toContain('reference a secret as ${ENV_VAR}');
  });
});

describe('carriesCredentialShape', () => {
  const credentialShapes = [
    'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.signature',
    'Bearer abcdefghijklmnopqrstuvwx',
    'sk-abcdefghijklmnopqrstuvwx',
    'AKIAIOSFODNN7EXAMPLE',
    'ghp_abcdefghijklmnopqrstuvwxyz0123456789',
    '-----BEGIN RSA PRIVATE KEY-----',
    'postgres://user:hunter2@db.test/app',
    'api_key = abcdef123456',
  ];

  it.each(credentialShapes)('flags %s', (text) => {
    expect(carriesCredentialShape(text)).toBe(true);
  });

  it('does not flag an environment reference', () => {
    expect(carriesCredentialShape('Bearer ${AGENTHUB_TOKEN}')).toBe(false);
    expect(carriesCredentialShape('https://example.test/mcp')).toBe(false);
  });
});

describe('serializeMcpBlock', () => {
  it('writes the seed key order and omits the fields the transport does not use', () => {
    expect(
      serializeMcpBlock({ name: 'a', type: 'stdio', command: 'npx', args: ['-y', 'pkg'], headers: {} })
    ).toBe(JSON.stringify({ name: 'a', type: 'stdio', command: 'npx', args: ['-y', 'pkg'] }, null, 2));
  });

  it('round-trips through parse', () => {
    const result = parseMcpBlock(serializeMcpBlock({ name: 'a', type: 'http', url: 'https://x.test' }));

    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.server).toEqual({ name: 'a', type: 'http', url: 'https://x.test' });
  });
});

describe('mcpServerLabel', () => {
  it('names the server and its transport, never a list of tools', () => {
    expect(mcpServerLabel({ name: 'agenthub_http', type: 'http' })).toBe('agenthub_http · http');
  });
});
