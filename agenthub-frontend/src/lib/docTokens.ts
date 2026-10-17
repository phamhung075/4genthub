import { useEffect, useMemo, useState } from 'react';
import { API_BASE_URL, MCP_URL } from '../config/environment';

/**
 * Tokens a document may carry. They are substituted at render time so any
 * deployment documents itself. A token whose value cannot be obtained is LEFT
 * VISIBLE: an empty string looks like a styling bug, a visible token is a
 * finding. Unknown tokens are untouched, so braces are safe for nothing else -
 * which is also the agreement with whoever writes the document.
 *
 * The MCP endpoint comes from config (VITE_MCP_URL, see config/environment.ts).
 * It is unset by default because this repository is not a deployment, and an
 * unset value leaves {{MCP_URL}} visible rather than rendering an empty string.
 */
export const TOKEN_API_ORIGIN = 'API_ORIGIN';
export const TOKEN_MCP_URL = 'MCP_URL';
export const TOKEN_VERSION = 'VERSION';

/** Replace {{TOKEN}} with a value, leaving the token when there is no value. */
export function applyTokens(source: string, values: Record<string, string | undefined>): string {
  return source.replace(/\{\{\s*([A-Z_]+)\s*\}\}/g, (match, name: string) => {
    const value = values[name];
    return value === undefined || value === '' ? match : value;
  });
}

/** The deployment's token values. The version comes from /health at runtime, never from a build-time constant. */
export function useDocTokenValues(): Record<string, string | undefined> {
  const [version, setVersion] = useState<string | undefined>(undefined);

  useEffect(() => {
    let cancelled = false;
    const readVersion = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (!response.ok) return;
        const data = await response.json();
        if (!cancelled && data && typeof data.version === 'string') {
          setVersion(data.version);
        }
      } catch {
        // Unreachable backend: {{VERSION}} stays visible rather than showing a lie.
      }
    };
    void readVersion();
    return () => {
      cancelled = true;
    };
  }, []);

  return useMemo(
    () => ({
      [TOKEN_API_ORIGIN]: API_BASE_URL,
      [TOKEN_MCP_URL]: MCP_URL,
      [TOKEN_VERSION]: version,
    }),
    [version],
  );
}
