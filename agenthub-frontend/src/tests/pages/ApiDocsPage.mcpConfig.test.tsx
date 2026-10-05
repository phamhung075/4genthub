import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from './../test-utils';

// The SET half of the {{MCP_URL}} behaviour. The unset half - no VITE_MCP_URL, so
// the token stays visible - is asserted in ApiDocsPage.test.tsx against the real
// config, which is empty because this repository is not a deployment.
//
// The whole config module is deliberately NOT mocked: it is imported by the app
// shell and by WebSocketClient, so replacing it would test a different app. The
// env var is stubbed and the page re-imported instead, which exercises the real
// loader in config/environment.ts.
const CONFIGURED_MCP_URL = 'https://mcp.deployment.test/mcp';

describe('ApiDocsPage with a configured MCP URL', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.stubEnv('VITE_MCP_URL', CONFIGURED_MCP_URL);
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it('substitutes {{MCP_URL}} with the configured value instead of leaving it visible', async () => {
    // Dynamic import is the documented exception for a module-loading boundary:
    // config/environment.ts reads import.meta.env when it is first evaluated, so
    // the page must be imported AFTER the env is stubbed. A static import would
    // evaluate the config once, unconfigured, and this test would assert the
    // unset state while claiming to test the set one.
    const { ApiDocsPage } = await import('../../pages/ApiDocsPage');

    render(<ApiDocsPage />);

    await waitFor(() => {
      expect(screen.getByTestId('api-docs-body').textContent).toContain(CONFIGURED_MCP_URL);
    });
    const body = screen.getByTestId('api-docs-body').textContent ?? '';
    expect(body).not.toContain('{{MCP_URL}}');
    // The same pass substitutes the configured origin.
    expect(body).not.toContain('{{API_ORIGIN}}');
  });
});
