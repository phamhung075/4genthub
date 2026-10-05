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

function readStringMap(value: unknown): Record<string, string> | null {
  if (value === undefined) return null;
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return null;
  const entries = Object.entries(value as Record<string, unknown>);
  if (entries.some(([, entry]) => typeof entry !== 'string')) return null;
  return Object.fromEntries(entries) as Record<string, string>;
}

function readArgs(value: unknown): string[] | null {
  if (value === undefined) return null;
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

  const raw = value as Record<string, unknown>;
  const unknown = Object.keys(raw).filter((key) => !ALLOWED_KEYS.includes(key));
  if (unknown.length > 0) {
    return { ok: false, error: `unknown field ${unknown.join(', ')}: a block carries only ${ALLOWED_KEYS.join(', ')}` };
  }

  const name = typeof raw.name === 'string' ? raw.name.trim() : '';
  if (name === '') {
    return { ok: false, error: 'field name is required: it becomes the server key in the MCP fragment' };
  }

  const type = typeof raw.type === 'string' && MCP_SERVER_TYPES.includes(raw.type as McpServerType)
    ? (raw.type as McpServerType)
    : null;
  if (type === null) {
    return { ok: false, error: `field type must be "http" or "stdio", got ${JSON.stringify(raw.type)}` };
  }

  const args = readArgs(raw.args);
  if (raw.args !== undefined && args === null) {
    return { ok: false, error: 'field args must be an array of strings' };
  }
  const headers = readStringMap(raw.headers);
  if (raw.headers !== undefined && headers === null) {
    return { ok: false, error: 'field headers must be an object of strings' };
  }
  const env = readStringMap(raw.env);
  if (raw.env !== undefined && env === null) {
    return { ok: false, error: 'field env must be an object of strings' };
  }

  if (type === 'http') {
    const url = typeof raw.url === 'string' ? raw.url : '';
    if (url === '') {
      return { ok: false, error: 'field url is required for a "http" server' };
    }
    if ((raw.command !== undefined && raw.command !== '') || (args?.length ?? 0) > 0 || (env && Object.keys(env).length > 0)) {
      return { ok: false, error: 'a "http" server takes url and headers, not command, args or env' };
    }
    const urlError = checkURL(url);
    if (urlError) return { ok: false, error: urlError };
    return { ok: true, server: { name, type, url, ...(headers ? { headers } : {}) } };
  }

  const command = typeof raw.command === 'string' ? raw.command : '';
  if (command === '') {
    return { ok: false, error: 'field command is required for a "stdio" server' };
  }
  if ((raw.url !== undefined && raw.url !== '') || (headers && Object.keys(headers).length > 0)) {
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
