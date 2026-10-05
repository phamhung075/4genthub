/**
 * @fileoverview sessionApi sends the requests the Go session routes define.
 */

import { sessionApi } from '../../services/sessionApi';

const fetchMock = vi.fn();

describe('sessionApi', () => {
  beforeEach(() => {
    fetchMock.mockReset();
    fetchMock.mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify({ sessions: [] }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )
    );
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('lists the user sessions with GET /api/v2/sessions and returns the parsed body', async () => {
    const response = await sessionApi.listSessions();

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/api/v2/sessions');
    expect(url.endsWith('/api/v2/sessions')).toBe(true);
    expect(init.method ?? 'GET').toBe('GET');
    expect(response.sessions).toEqual([]);
  });
});
