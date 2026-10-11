/**
 * @fileoverview seatApi sends the requests the Go seat routes define - EVERY entry, with the url, verb
 * and body it sends, asserted from the register below. The guard at the bottom of this file fails when
 * the register and the exported object disagree, so this summary cannot outrun the file the way
 * "asserts 3 of 23 entries" did.
 */

import { seatApi } from '../../services/seatApi';

const fetchMock = vi.fn();

type Method = 'GET' | 'POST' | 'PUT' | 'DELETE';

interface Row {
  /** The register: a row that does not name an entry of the exported object does not compile. */
  entry: keyof typeof seatApi;
  /** Required, so the VERB is asserted for EVERY entry - the one dimension a path absorbed by a GET
   *  pattern cannot expose at runtime. */
  method: Method;
  /** Required and non-empty; the overlay pair carries its THREE. */
  paths: string[];
  /** The entry invoked with literal-safe arguments. */
  call: () => Promise<unknown>;
  /** Asserted verbatim when declared. */
  body?: string;
}

const OPENRIG = '/api/v2/openrig';

const rows: Row[] = [
  // Rooms
  { entry: 'listRooms', method: 'GET', paths: [`${OPENRIG}/rooms`], call: () => seatApi.listRooms() },
  {
    entry: 'createRoom',
    method: 'POST',
    paths: [`${OPENRIG}/rooms`],
    call: () => seatApi.createRoom({ slug: 'dev', name: 'Dev' }),
    body: JSON.stringify({ slug: 'dev', name: 'Dev' }),
  },
  {
    entry: 'deleteRoom',
    method: 'DELETE',
    paths: [`${OPENRIG}/rooms/dev%20room`],
    call: () => seatApi.deleteRoom('dev room'),
  },
  {
    entry: 'setRoomTeam',
    method: 'PUT',
    paths: [`${OPENRIG}/rooms/dev%20room/team`],
    call: () => seatApi.setRoomTeam('dev room', 'eng'),
    body: JSON.stringify({ team: 'eng' }),
  },
  {
    entry: 'listTeams',
    method: 'GET',
    paths: [`${OPENRIG}/teams`],
    call: () => seatApi.listTeams(),
  },

  // Seat types and modules
  {
    entry: 'listSeatTypes',
    method: 'GET',
    paths: [`${OPENRIG}/seat-types`],
    call: () => seatApi.listSeatTypes(),
  },
  {
    entry: 'createSeatTypeVersion',
    method: 'POST',
    paths: [`${OPENRIG}/seat-types/coder/versions`],
    call: () =>
      seatApi.createSeatTypeVersion('coder', {
        module_refs: ['instructions@1.0.0'],
        default_runtime: 'omp',
      }),
    body: JSON.stringify({ module_refs: ['instructions@1.0.0'], default_runtime: 'omp' }),
  },
  {
    entry: 'listModules',
    method: 'GET',
    paths: [`${OPENRIG}/modules`],
    call: () => seatApi.listModules(),
  },
  {
    entry: 'getModuleVersion',
    method: 'GET',
    paths: [`${OPENRIG}/modules/coder/versions/1.0.0`],
    call: () => seatApi.getModuleVersion('coder', '1.0.0'),
  },
  {
    entry: 'putModuleVersion',
    method: 'PUT',
    paths: [`${OPENRIG}/modules/coder/versions/1.0.0`],
    call: () =>
      seatApi.putModuleVersion('coder', '1.0.0', { kind: 'instruction', content: 'Be brief.' }),
    body: JSON.stringify({ kind: 'instruction', content: 'Be brief.' }),
  },

  // Seats
  {
    entry: 'listSeats',
    method: 'GET',
    paths: [`${OPENRIG}/rooms/dev/seats`],
    call: () => seatApi.listSeats('dev'),
  },
  {
    entry: 'createSeat',
    method: 'POST',
    paths: [`${OPENRIG}/rooms/dev/seats`],
    call: () =>
      seatApi.createSeat('dev', {
        seat_key: 'alice',
        seat_type: 'coder',
        runtime: 'omp',
        model: 'deepseek-flash',
      }),
    body: JSON.stringify({
      seat_key: 'alice',
      seat_type: 'coder',
      runtime: 'omp',
      model: 'deepseek-flash',
    }),
  },
  {
    entry: 'removeSeat',
    method: 'DELETE',
    paths: [`${OPENRIG}/rooms/dev/seats/alice`],
    call: () => seatApi.removeSeat('dev', 'alice'),
  },
  {
    entry: 'updateSeatOccupant',
    method: 'PUT',
    paths: [`${OPENRIG}/rooms/dev/seats/alice/occupant`],
    call: () => seatApi.updateSeatOccupant('dev', 'alice', { runtime: 'omp', model: 'deepseek-flash' }),
    body: JSON.stringify({ runtime: 'omp', model: 'deepseek-flash' }),
  },

  // Overlays - ONE function over THREE paths, so the row carries three and the call makes all three.
  {
    entry: 'getOverlay',
    method: 'GET',
    paths: [
      `${OPENRIG}/overlay`,
      `${OPENRIG}/rooms/dev/overlay`,
      `${OPENRIG}/rooms/dev/seats/alice/overlay`,
    ],
    call: () =>
      Promise.all([
        seatApi.getOverlay('company', 'dev', 'alice'),
        seatApi.getOverlay('room', 'dev', 'alice'),
        seatApi.getOverlay('seat', 'dev', 'alice'),
      ]),
  },
  {
    entry: 'putOverlay',
    method: 'PUT',
    paths: [
      `${OPENRIG}/overlay`,
      `${OPENRIG}/rooms/dev/overlay`,
      `${OPENRIG}/rooms/dev/seats/alice/overlay`,
    ],
    call: () => {
      const ops = [{ kind: 'add' as const, slug: 'instructions', version: '1.0.0', content: '' }];
      return Promise.all([
        seatApi.putOverlay('company', { ops }, 'dev', 'alice'),
        seatApi.putOverlay('room', { ops }, 'dev', 'alice'),
        seatApi.putOverlay('seat', { ops }, 'dev', 'alice'),
      ]);
    },
    body: JSON.stringify({
      ops: [{ kind: 'add', slug: 'instructions', version: '1.0.0', content: '' }],
    }),
  },

  // Links
  {
    entry: 'listLinks',
    method: 'GET',
    paths: [`${OPENRIG}/rooms/dev/seats/alice/links`],
    call: () => seatApi.listLinks('dev', 'alice'),
  },
  {
    entry: 'putLink',
    method: 'PUT',
    paths: [`${OPENRIG}/rooms/dev/seats/alice/links`],
    call: () =>
      seatApi.putLink('dev', 'alice', { to_seat: 'bob', kind: 'delegates_to', allow: true }),
    body: JSON.stringify({ to_seat: 'bob', kind: 'delegates_to', allow: true }),
  },
  {
    entry: 'putPermissionPolicy',
    method: 'PUT',
    paths: [`${OPENRIG}/rooms/dev/seats/alice/permission-policy`],
    call: () => seatApi.putPermissionPolicy('dev', 'alice', 'locked'),
    body: JSON.stringify({ permission_policy: 'locked' }),
  },
  {
    entry: 'deleteLink',
    method: 'DELETE',
    paths: [`${OPENRIG}/rooms/dev%20room/seats/alice/links/bob/delegates_to`],
    call: () => seatApi.deleteLink('dev room', 'alice', 'bob', 'delegates_to'),
  },

  // Messages. MOUNT STATUS AT THIS FOLD'S BASE: mounted - `a56e58a7` added
  // `POST /api/v2/openrig/rooms/{room}/seats/{seat}/messages` to seat_mount.go and the regenerated
  // artefact (144 routes) carries it. The path is room-scoped like every other seat route, and the verb
  // is the only thing that distinguishes its call site from the GET resolution pattern - which is why
  // `method` is a required field here rather than an optional one.
  {
    entry: 'sendSeatMessage',
    method: 'POST',
    paths: [`${OPENRIG}/rooms/dev/seats/alice/messages`],
    call: () => seatApi.sendSeatMessage('dev', 'alice', { text: 'hello' }),
    body: JSON.stringify({ text: 'hello' }),
  },

  // Bridge machines
  {
    entry: 'fetchMachines',
    method: 'GET',
    paths: [`${OPENRIG}/machines`],
    call: () => seatApi.fetchMachines(),
  },

  // Settings
  {
    entry: 'getSettings',
    method: 'GET',
    paths: [`${OPENRIG}/settings`],
    call: () => seatApi.getSettings(),
  },
  {
    entry: 'putSettings',
    method: 'PUT',
    paths: [`${OPENRIG}/settings`],
    call: () => seatApi.putSettings(true),
    body: JSON.stringify({ follow_latest: true }),
  },

  // Resolved preview
  {
    entry: 'getResolvedSeat',
    method: 'GET',
    paths: [`${OPENRIG}/seats/dev/alice`],
    call: () => seatApi.getResolvedSeat('dev', 'alice'),
  },
];

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

  for (const row of rows) {
    it(`${row.entry} sends ${row.method} to the path its row declares`, async () => {
      fetchMock.mockClear();
      await row.call();

      const calls = fetchMock.mock.calls as [string, RequestInit | undefined][];

      // One call per declared path, and every declared path is hit - together these are a bijection, so
      // a duplicate cannot stand in for a missing one.
      expect(calls).toHaveLength(row.paths.length);
      for (const path of row.paths) {
        expect(calls.some(([url]) => String(url).endsWith(path))).toBe(true);
      }

      for (const [, init] of calls) {
        // `apiRequest` passes NO method for a GET row (`{ ...init, headers }` with init undefined), and
        // fetch defaults to GET. The EFFECTIVE verb is what is asserted, which is the only place the
        // verb of a path absorbed by a GET pattern can be stated at runtime.
        expect(init?.method ?? 'GET').toBe(row.method);
        if (row.body !== undefined) {
          expect(init?.body).toBe(row.body);
        }
      }
    });
  }

  // THE GUARD. One assertion, both directions: it reads the real exported object and this table, not
  // this file's source text, so a rename or a removal moves the object and the guard follows it rather
  // than the spelling. It cannot pass vacuously - an empty or partial table fails against the sorted
  // keys, and it fails when a 24th entry has no row (the drift this row was filed for) or when a row
  // names an entry that no longer exists (the stale-register direction).
  //
  // NAMED LIMIT: the guard is ENTRY-level. It proves every entry HAS a row; it does not prove a row's
  // paths are complete. The overlay rows carry three literal paths each, covered by the compiler's
  // exhaustive switch in `overlayPath` and by those rows visibly carrying three, not by this check.
  it('has one row per seatApi entry, and every row names a real entry', () => {
    expect(rows.map((row) => row.entry).sort()).toEqual(Object.keys(seatApi).sort());
  });
});
