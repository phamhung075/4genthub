/**
 * @fileoverview apiRequest sends the Bearer token of the access_token cookie.
 * Seat screens call the Go server through apiRequest, which requires the
 * Authorization header (cookies are not read by those routes).
 */

import Cookies from 'js-cookie';
import logger from '../../utils/logger';
import { apiRequest } from '../../services/apiV2';

const fetchMock = vi.fn();

const ok = () =>
  Promise.resolve(
    new Response(JSON.stringify({ success: true }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  );

const sentHeaders = () => new Headers((fetchMock.mock.calls[0][1] as RequestInit).headers);

describe('apiRequest', () => {
  beforeEach(() => {
    fetchMock.mockReset();
    fetchMock.mockImplementation(ok);
    vi.stubGlobal('fetch', fetchMock);
    Cookies.remove('access_token');
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    Cookies.remove('access_token');
  });

  it('sends the Bearer token from the access_token cookie on a GET', async () => {
    Cookies.set('access_token', 'cookie-token');

    await apiRequest('/api/v2/openrig/rooms-get-auth');

    expect(sentHeaders().get('Authorization')).toBe('Bearer cookie-token');
    expect(sentHeaders().get('Content-Type')).toBe('application/json');
  });

  it('keeps the caller headers and method and body next to the Bearer token', async () => {
    Cookies.set('access_token', 'cookie-token');

    await apiRequest('/api/v2/openrig/rooms-post-auth', {
      method: 'POST',
      headers: { 'X-Trace': 'abc' },
      body: JSON.stringify({ slug: 'dev' }),
    });

    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe('POST');
    expect(init.body).toBe(JSON.stringify({ slug: 'dev' }));
    expect(sentHeaders().get('X-Trace')).toBe('abc');
    expect(sentHeaders().get('Authorization')).toBe('Bearer cookie-token');
  });

  it('lets the caller override a default header', async () => {
    Cookies.set('access_token', 'cookie-token');

    await apiRequest('/api/v2/openrig/rooms-override', { headers: { 'Content-Type': 'text/plain' } });

    expect(sentHeaders().get('Content-Type')).toBe('text/plain');
  });

  it('sends no Authorization header when there is no access_token cookie', async () => {
    await apiRequest('/api/v2/openrig/rooms-no-token');

    expect(sentHeaders().has('Authorization')).toBe(false);
  });

  it('retries a 401 with the caller headers and the refreshed Bearer token', async () => {
    Cookies.set('access_token', 'old-token');
    Cookies.set('refresh_token', 'refresh-token');
    fetchMock
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: 'expired' }), { status: 401 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ access_token: 'new-token' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )
      .mockImplementationOnce(ok);

    await apiRequest('/api/v2/openrig/rooms-retry', {
      method: 'PUT',
      headers: { 'X-Trace': 'abc' },
      body: JSON.stringify({ slug: 'dev' }),
    });

    expect(fetchMock).toHaveBeenCalledTimes(3);
    const retry = fetchMock.mock.calls[2][1] as RequestInit;
    const headers = new Headers(retry.headers);
    expect(retry.method).toBe('PUT');
    expect(retry.body).toBe(JSON.stringify({ slug: 'dev' }));
    expect(headers.get('Authorization')).toBe('Bearer new-token');
    expect(headers.get('Content-Type')).toBe('application/json');
    expect(headers.get('X-Trace')).toBe('abc');
  });

  it('never logs any character of the access token', async () => {
    Cookies.set('access_token', 'secret-token-xyz');
    const spies = (['debug', 'info', 'warn', 'error'] as const).map(level => vi.spyOn(logger, level));

    await apiRequest('/api/v2/openrig/rooms-log');

    const logged = JSON.stringify(spies.flatMap(spy => spy.mock.calls));
    expect(logged).not.toContain('secret');
    spies.forEach(spy => spy.mockRestore());
  });

  it('rejects a 404 with the server detail as the message', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'module rules@latest not found in catalog' }), { status: 404 })
    );

    await expect(apiRequest('/api/v2/openrig/seats/dev/alice-404-detail')).rejects.toMatchObject({
      name: 'NotFoundError',
      status: 404,
      message: 'module rules@latest not found in catalog',
    });
  });

  it('keeps the generic message for a 404 without a detail', async () => {
    fetchMock.mockResolvedValueOnce(new Response('{}', { status: 404 }));

    await expect(apiRequest('/api/v2/openrig/seats/dev/alice-404-plain')).rejects.toThrow('Resource not found');
  });
});
