/**
 * @fileoverview MachinesPanel degrades ONE seat row when a producer omits `pinned_hash` instead of
 * taking the panel down.
 *
 * The crash this pins was real and reached production: `hash.slice(0, 8)` on an undefined hash threw
 * `Cannot read properties of undefined (reading 'slice')` and the whole seats page went blank
 * (recorded at `OWNER-STATUS.md:1562-1563`). The fix, `cd163bb7` ("an absent hash degrades one row
 * instead of taking the panel down"), changed the read to `(hash ?? '').slice(0, 8)` and shipped
 * WITHOUT a case of its own - so before this file, removing the guard left the suite green.
 *
 * WHAT IS PINNED IS THE ABSENCE THE TYPE CANNOT CATCH. `MachineSeatStatus.pinned_hash` is required,
 * but the type is only a claim about the producer: the fixture below DELETES the key at runtime while
 * keeping the declared type, which is exactly what a second client or a proxy that drops the field
 * sends. `pinned_hash: undefined` would not be the same shape - the key would still be present.
 *
 * THE HEALTHY ROW IN THE SAME RENDER IS THE POSITIVE CONTROL. Without it, an assertion that the
 * degraded row shows nothing would also pass against a panel that rendered no rows at all.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { MachinesPanel } from '../../components/seats/MachinesPanel';

// Inside the factory, not outside it: vi.mock is HOISTED above the module body, so a factory that
// closed over a top-level const would run before that const is initialized.
vi.mock('../../hooks/useSeats', () => {
  const reportedAt = '2026-10-10T15:00:00Z';

  const healthy = {
    room: 'dev',
    seat: 'alice',
    state: 'running',
    runtime: 'omp',
    pinned_hash: 'aaaa1111bbbb2222',
    expected_hash: 'aaaa1111bbbb2222',
    sync: 'in_sync',
    detail: 'ok',
    redacted: false,
    reported_at: reportedAt,
  };

  // A seat as a producer that DROPS the field sends it: the declared type is intact, the runtime
  // value carries no pinned_hash key at all. Its sync is 'drift' so the badge path reads the absent
  // hash a second time, through shortHash(seat.pinned_hash).
  const dropped = {
    room: 'dev',
    seat: 'bob',
    state: 'running',
    runtime: 'omp',
    expected_hash: 'cccc3333dddd4444',
    sync: 'drift',
    detail: 'drifted',
    redacted: false,
    reported_at: reportedAt,
  };

  const machines = [
    { machine_id: 'rig-box', last_seen: reportedAt, online: true, seats: [healthy, dropped], agents: [] },
  ];

  return {
    useMachines: () => ({ machines, isLoading: false, error: null, refetch: () => {} }),
  };
});

describe('MachinesPanel', () => {
  it('renders a seat whose pinned_hash key is absent instead of taking the panel down', () => {
    render(<MachinesPanel />);

    // The panel and its heading survived, which is the crash's actual shape: the whole page went down.
    expect(screen.getByText('Bridge machines')).toBeInTheDocument();

    // Both rows rendered: the healthy one is the positive control for the assertions below.
    expect(screen.getByText('dev/alice')).toBeInTheDocument();
    expect(screen.getByText('dev/bob')).toBeInTheDocument();
    expect(screen.getByText('aaaa1111')).toBeInTheDocument();

    // And the absent hash degraded to the empty short hash in the drift badge - the second call site -
    // rather than throwing on the way to the Hash column.
    expect(screen.getByText(/drift · running\s+· expected cccc3333/)).toBeInTheDocument();
  });
});
