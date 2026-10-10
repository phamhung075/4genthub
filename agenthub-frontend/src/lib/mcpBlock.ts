/**
 * mcp block helpers - the frontend mirror of the Go contract.
 *
 * The authority is `seat_management/domain/mcpblock.Parse` (field rules) and
 * `domain/secretscan.Contains` (the eight credential shapes). This module gives
 * the same verdict early so the publish form refuses before a round trip; the
 * server still validates every write, so these are a preview, not a gate.
 *
 * @module lib/mcpBlock
 * @version 1.0.0
 */

import type { McpServerBlock, McpServerType } from '../types/seatTypes';
import { MCP_SERVER_TYPES } from '../types/seatTypes';

/** The one deployment value a block may name but never carry; RenderSeat substitutes it. */
export const PLATFORM_MCP_URL_PLACEHOLDER = '${AGENTHUB_MCP_URL}';

/** The eight shapes `domain/secretscan/secretscan.go` refuses, in the same order. */
const CREDENTIAL_PATTERNS: RegExp[] = [
  /eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/,
  /Bearer\s+[A-Za-z0-9._~+/=-]{20,}/,
  /sk-[A-Za-z0-9_-]{20,}/,
  /AKIA[0-9A-Z]{16}/,
  /gh[pousr]_[A-Za-z0-9]{30,}/,
  /-----BEGIN [A-Z ]*PRIVATE KEY-----/,
  /:\/\/[^\s/:@]*:[^\s/]+@/,
  /(password|passwd|secret|token|api[_-]?key)\s*[=:]\s*\S{6,}/i,
];

const CREDENTIAL_MESSAGE =
  'carries a credential-shaped value: reference a secret as ${ENV_VAR} instead of writing it into the block';

const ALLOWED_KEYS = ['name', 'type', 'url', 'command', 'args', 'headers', 'env'];

export type McpBlockParse = { ok: true; server: McpServerBlock } | { ok: false; error: string };

/** True when the text contains a credential-shaped value (mirror of secretscan.Contains). */
export function carriesCredentialShape(text: string): boolean {
  return CREDENTIAL_PATTERNS.some((pattern) => pattern.test(text));
}

/** A block's palette/row label: the server name and the transport it speaks. */
export function mcpServerLabel(server: McpServerBlock): string {
  return `${server.name} · ${server.type}`;
}

/** Go decodes an explicit null to the field's zero value, so for an optional field null means ABSENT. */
function isAbsent(value: unknown): boolean {
  return value === undefined || value === null;
}

/**
 * Reads Go string fields the way Go's decoder does: an absent key or an explicit null is the field's
 * ZERO VALUE (`encoding/json` leaves a string field alone for null, which is the normalisation this
 * module already needed), while a PRESENT value of another type is a DECODE ERROR. The error is
 * returned rather than a substituted "" because THAT substitution is how a wrongly-typed field gets
 * accepted here while the server refuses the whole block: `{"type":"http","url":"https://x",
 * "command":123}` fails Go's decode ("cannot unmarshal number into ... field Server.command"), and a
 * mirror that reads `command` as "" instead judges only the fields it could read.
 */
function readStringFields(
  byKey: Map<string, unknown>,
  keys: readonly string[],
): { values: Record<string, string>; error: string | null } {
  const values: Record<string, string> = {};
  for (const key of keys) {
    const raw = byKey.get(key);
    if (isAbsent(raw)) {
      values[key] = '';
      continue;
    }
    if (typeof raw !== 'string') {
      return { values, error: `field ${key} must be a string` };
    }
    values[key] = raw;
  }
  return { values, error: null };
}

function readStringMap(value: unknown): Record<string, string> | null {
  if (isAbsent(value)) return null;
  if (typeof value !== 'object' || Array.isArray(value)) return null;
  const entries = Object.entries(value as Record<string, unknown>);
  if (entries.some(([, entry]) => typeof entry !== 'string')) return null;
  return Object.fromEntries(entries) as Record<string, string>;
}

function readArgs(value: unknown): string[] | null {
  if (isAbsent(value)) return null;
  if (!Array.isArray(value) || value.some((entry) => typeof entry !== 'string')) return null;
  return value as string[];
}

/** Mirrors mcpblock.CheckURL: empty and ${VAR} pass; anything else must be http(s). */
function checkURL(url: string): string | null {
  if (url === '' || url.includes('${')) return null;
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    return `url must be http(s), got "${url}"`;
  }
  return null;
}

/** Validate one block's content exactly as mcpblock.Parse does, and return the server. */
export function parseMcpBlock(content: string): McpBlockParse {
  if (carriesCredentialShape(content)) {
    return { ok: false, error: CREDENTIAL_MESSAGE };
  }

  let value: unknown;
  try {
    value = JSON.parse(content);
  } catch {
    return { ok: false, error: 'content is not one JSON value' };
  }
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    return { ok: false, error: 'content is not a server object' };
  }

  // Go's decoder matches object keys to struct tags CASE-INSENSITIVELY, and a later duplicate wins, so a
  // block the renderer accepts may arrive as {"Name": ...}. Normalise once and read by the tag names; the
  // unknown-field refusal keeps Go's meaning, compared without case.
  //
  // ONE KNOWN DIVERGENCE, left here rather than papered over: JSON.parse collapses a DUPLICATE KEY to its
  // last value before this map is built, and Go lets a JSON null leave the field it already decoded. So
  // {"url":"https://x.test","url":null} reads as "no url" here and as "https://x.test" in Go - the mirror
  // refuses a block the server accepts. It refuses rather than accepts, and it needs a duplicated key whose
  // last value is null, so reproducing Go would mean re-scanning the raw text instead of parsing it.
  const raw = value as Record<string, unknown>;
  const byKey = new Map<string, unknown>();
  for (const [key, entry] of Object.entries(raw)) {
    byKey.set(key.toLowerCase(), entry);
  }
  const unknown = Object.keys(raw).filter((key) => !ALLOWED_KEYS.includes(key.toLowerCase()));
  if (unknown.length > 0) {
    return { ok: false, error: `unknown field ${unknown.join(', ')}: a block carries only ${ALLOWED_KEYS.join(', ')}` };
  }

  // GO'S DECODE RUNS BEFORE ANY FIELD RULE, and it REFUSES a wrongly-typed field rather than dropping it.
  // So the four string fields are read first, as a decode would, and a present-but-not-a-string value
  // refuses here with the reason Go gives; absent and explicit null stay the zero value.
  const strings = readStringFields(byKey, ['name', 'type', 'url', 'command']);
  if (strings.error !== null) {
    return { ok: false, error: strings.error };
  }

  // GO KEEPS THE NAME VERBATIM and only CHECKS it for content, so the palette's label and the server's
  // fragment key are the same string; trimming it here would make "  x  " two different server names.
  const name = strings.values['name'];
  if (name.trim() === '') {
    return { ok: false, error: 'field name is required: it becomes the server key in the MCP fragment' };
  }

  const declaredType = byKey.get('type');
  const type = MCP_SERVER_TYPES.includes(strings.values['type'] as McpServerType)
    ? (strings.values['type'] as McpServerType)
    : null;
  if (type === null) {
    return { ok: false, error: `field type must be "http" or "stdio", got ${JSON.stringify(declaredType)}` };
  }

  const rawArgs = byKey.get('args');
  const args = readArgs(rawArgs);
  if (!isAbsent(rawArgs) && args === null) {
    return { ok: false, error: 'field args must be an array of strings' };
  }
  const rawHeaders = byKey.get('headers');
  const headers = readStringMap(rawHeaders);
  if (!isAbsent(rawHeaders) && headers === null) {
    return { ok: false, error: 'field headers must be an object of strings' };
  }
  const rawEnv = byKey.get('env');
  const env = readStringMap(rawEnv);
  if (!isAbsent(rawEnv) && env === null) {
    return { ok: false, error: 'field env must be an object of strings' };
  }

  // Read above with the other string fields, as Go's decode reads them; what is left for the cross-field
  // rules below is only whether each is empty.
  const url = strings.values['url'];
  const command = strings.values['command'];

  if (type === 'http') {
    if (url === '') {
      return { ok: false, error: 'field url is required for a "http" server' };
    }
    if (command !== '' || (args?.length ?? 0) > 0 || (env && Object.keys(env).length > 0)) {
      return { ok: false, error: 'a "http" server takes url and headers, not command, args or env' };
    }
    const urlError = checkURL(url);
    if (urlError) return { ok: false, error: urlError };
    return { ok: true, server: { name, type, url, ...(headers ? { headers } : {}) } };
  }

  if (command === '') {
    return { ok: false, error: 'field command is required for a "stdio" server' };
  }
  if (url !== '' || (headers && Object.keys(headers).length > 0)) {
    return { ok: false, error: 'a "stdio" server takes command, args and env, not url or headers' };
  }
  return {
    ok: true,
    server: { name, type, command, ...(args ? { args } : {}), ...(env ? { env } : {}) },
  };
}

/** Serialize a block in the key order the seed blocks use, omitting empty fields. */
export function serializeMcpBlock(server: McpServerBlock): string {
  const ordered: Record<string, unknown> = { name: server.name, type: server.type };
  if (server.url !== undefined && server.url !== '') ordered.url = server.url;
  if (server.command !== undefined && server.command !== '') ordered.command = server.command;
  if (server.args !== undefined && server.args.length > 0) ordered.args = server.args;
  if (server.headers !== undefined && Object.keys(server.headers).length > 0) ordered.headers = server.headers;
  if (server.env !== undefined && Object.keys(server.env).length > 0) ordered.env = server.env;
  return JSON.stringify(ordered, null, 2);
}
