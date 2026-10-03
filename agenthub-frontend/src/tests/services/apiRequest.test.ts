/**
 * @fileoverview apiRequest sends the Bearer token of the access_token cookie.
 * Seat screens call the Go server through apiRequest, which requires the
 * Authorization header (cookies are not read by those routes).
 */

import Cookies from 'js-cookie';
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
});
