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
    // THE WRONGLY-TYPED FIELD, on the transport that does not use it. Go's typed decode refuses the WHOLE
    // block for these, so reading the field as "" and judging only the fields the mirror could read is how
    // it accepted content the server refuses - see the dedicated case below for the two measured strings.
    ['an http block whose command is a number', JSON.stringify({ name: 'n', type: 'http', url: 'https://x/mcp', command: 123 }), 'field command must be a string'],
    ['a stdio block whose url is a number', JSON.stringify({ name: 'n', type: 'stdio', command: 'npx', url: 123 }), 'field url must be a string'],
    ['a name that is not a string', JSON.stringify({ name: 123, type: 'stdio', command: 'x' }), 'field name must be a string'],
    ['a type that is not a string', JSON.stringify({ name: 'a', type: 123, command: 'x' }), 'field type must be a string'],
    ['args carrying a non-string entry', JSON.stringify({ name: 'a', type: 'stdio', command: 'x', args: [1] }), 'field args must be an array of strings'],
  ];

  it.each(rejected)('refuses %s with the reason', (_case, content, expected) => {
    const result = parseMcpBlock(content);

    expect(result.ok).toBe(false);
    if (result.ok) return;
    expect(result.error).toContain(expected);
  });

  // The Go parser matches struct tags CASE-INSENSITIVELY and decodes an explicit null to the field's zero
  // value, so both shapes below are blocks the RENDERER accepts. A form that refuses them is a false
  // refusal, which is the direction that makes this a defect rather than a note; both need hand-written JSON,
  // which is why nothing exercised them.
  it('accepts the shapes Go accepts: capitalised tags, and an explicit null on an optional field', () => {
    const result = parseMcpBlock(
      JSON.stringify({ Name: 'probe', Type: 'stdio', Command: 'npx', Args: null, Env: null })
    );

    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.server.name).toBe('probe');
    expect(result.server.command).toBe('npx');
    expect(result.server.args).toBeUndefined();
    expect(result.server.env).toBeUndefined();
  });

  // THE PARITY PIN, with the two strings the gate measured: the delivered mirror returned ok:true for both
  // while mcpblock.Parse refused them ("json: cannot unmarshal number into Go struct field Server.command
  // of type string"), because the null-normalisation above swept in every non-string value. THE MESSAGE IS
  // ASSERTED, not just the refusal, so this cannot pass by refusing for some other field's rule.
  it('refuses the gate two wrongly-typed blocks for the TYPE reason, as Go refuses them at decode', () => {
    const httpNumericCommand = parseMcpBlock(
      '{"name":"n","type":"http","url":"https://x/mcp","command":123}'
    );
    expect(httpNumericCommand.ok).toBe(false);
    if (httpNumericCommand.ok) return;
    expect(httpNumericCommand.error).toBe('field command must be a string');

    const stdioNumericUrl = parseMcpBlock('{"name":"n","type":"stdio","command":"npx","url":123}');
    expect(stdioNumericUrl.ok).toBe(false);
    if (stdioNumericUrl.ok) return;
    expect(stdioNumericUrl.error).toBe('field url must be a string');

    // The control the gate ran beside them: the same blocks with STRINGS are refused for the CONTRADICTION,
    // which is what shows the pair above is refused by the TYPE rather than by the field being non-empty.
    const httpStringCommand = parseMcpBlock(
      '{"name":"n","type":"http","url":"https://x/mcp","command":"npx"}'
    );
    expect(httpStringCommand.ok).toBe(false);
    if (httpStringCommand.ok) return;
    expect(httpStringCommand.error).toContain('takes url and headers');
  });

  // THE OTHER HALF OF THAT RULE: an explicit null stays ABSENT, because Go leaves the field at its zero
  // value rather than failing. Fixing the pair above must not turn the null normalisation back into the
  // false refusal it was added to end.
  it('keeps an explicit null on a string field absent, on the used and the unused transport alike', () => {
    const stdioNullUrl = parseMcpBlock('{"name":"a","type":"stdio","command":"npx","url":null}');
    expect(stdioNullUrl.ok).toBe(true);
    if (!stdioNullUrl.ok) return;
    expect(stdioNullUrl.server.url).toBeUndefined();

    const httpNullCommand = parseMcpBlock(
      '{"name":"a","type":"http","url":"https://x.test","command":null}'
    );
    expect(httpNullCommand.ok).toBe(true);
    if (!httpNullCommand.ok) return;
    expect(httpNullCommand.server.command).toBeUndefined();
  });

  it('keeps the name verbatim, because Go stores it as written', () => {
    // Go checks `strings.TrimSpace(server.Name) == ""` and then keeps the value, so padding is legal and
    // the palette's label must not read as a different server than the fragment's own key.
    const padded = parseMcpBlock(JSON.stringify({ name: '  x  ', type: 'stdio', command: 'npx' }));

    expect(padded.ok).toBe(true);
    if (!padded.ok) return;
    expect(padded.server.name).toBe('  x  ');
  });

  // Complements the rejection table's lowercase entry: matching without case must not turn an UNKNOWN field
  // into an allowed one, which is the obvious way to get this alignment wrong.
  it('still refuses an unknown field written in capitals', () => {
    const result = parseMcpBlock(
      JSON.stringify({ Name: 'x', Type: 'stdio', Command: 'npx', Tools: [] })
    );

    expect(result.ok).toBe(false);
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
