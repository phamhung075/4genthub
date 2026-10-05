/**
 * @fileoverview seatApi sends the requests the Go seat routes define.
 */

import { seatApi } from '../../services/seatApi';

const fetchMock = vi.fn();

describe('seatApi', () => {
  beforeEach(() => {
    fetchMock.mockReset();
    fetchMock.mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify({ success: true }), {
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

  it('deletes a link with DELETE /rooms/{room}/seats/{seat}/links/{to}/{kind}', async () => {
    await seatApi.deleteLink('dev room', 'alice', 'bob', 'delegates_to');

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/api/v2/openrig/rooms/dev%20room/seats/alice/links/bob/delegates_to');
    expect(init.method).toBe('DELETE');
  });

  it('sets a permission policy with PUT .../permission-policy and the policy in the body', async () => {
    await seatApi.putPermissionPolicy('dev', 'alice', 'locked');

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/api\/v2\/openrig\/rooms\/dev\/seats\/alice\/permission-policy$/);
    expect(init.method).toBe('PUT');
    expect(init.body).toBe(JSON.stringify({ permission_policy: 'locked' }));
  });

  it('deletes a room with DELETE /rooms/{room}', async () => {
    await seatApi.deleteRoom('dev room');

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/api\/v2\/openrig\/rooms\/dev%20room$/);
    expect(init.method).toBe('DELETE');
  });
});
