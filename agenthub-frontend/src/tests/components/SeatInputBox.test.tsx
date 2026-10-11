/**
 * @fileoverview SeatInputBox - the sessions page's chat input, KEPT FOR PHASE 2.
 *
 * The component is NOT mounted in phase 1: the ruled boundaries
 * (`ai_docs/core-architecture/rigd-boundaries.md`, section 3) make commands a phase-2 surface with
 * their own scope, a human-only issuer and a local opt-in, so the Sessions page ships no input and
 * `SessionLiveView` mounts none. These cases therefore exercise the component ON ITS OWN - the
 * cases that drove it through the window were removed with the mount, not re-pinned.
 *
 * Two properties are the whole point of this file, and each is a way the component could be wrong
 * while looking right: it must render NO input on first mount, and a refusal must arrive in the
 * SERVER's words rather than as a generic failure.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '../test-utils';
import { SeatInputBox } from '../../components/sessions/SeatInputBox';
import { seatApi } from '../../services/seatApi';

vi.mock('../../services/seatApi', () => ({
  seatApi: { sendSeatMessage: vi.fn() },
}));

const mockApi = vi.mocked(seatApi);

const openAndType = (text: string) => {
  fireEvent.click(screen.getByRole('button', { name: 'Show message input' }));
  fireEvent.change(screen.getByRole('textbox'), { target: { value: text } });
};

describe('SeatInputBox', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApi.sendSeatMessage.mockResolvedValue({ success: true });
  });

  it('renders no input on the first mount: a fresh window is watch-only', () => {
    render(<SeatInputBox room="dev" seatKey="web-dev" />);

    // queryBy, not getBy: the assertion IS the absence, and a getBy-shaped assertion for absence
    // is the wrong instrument - it throws rather than reporting, so it cannot express this.
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /send/i })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Show message input' })).toHaveAttribute(
      'aria-expanded',
      'false'
    );
    expect(mockApi.sendSeatMessage).not.toHaveBeenCalled();
  });

  it("sends the typed text to the seat's messages endpoint and clears the box", async () => {
    render(<SeatInputBox room="dev" seatKey="web-dev" />);
    openAndType('  hello from the window  ');

    fireEvent.click(screen.getByRole('button', { name: /send/i }));

    await waitFor(() =>
      expect(mockApi.sendSeatMessage).toHaveBeenCalledWith('dev', 'web-dev', {
        text: 'hello from the window',
      })
    );
    await waitFor(() => expect(screen.getByRole('textbox')).toHaveValue(''));
  });

  it("renders the server's refusal sentence verbatim, and keeps the text so it can be retried", async () => {
    mockApi.sendSeatMessage.mockRejectedValue(
      Object.assign(new Error('seat "web-dev" cannot be messaged: refused by scope'), { status: 403 })
    );
    render(<SeatInputBox room="dev" seatKey="web-dev" />);
    openAndType('hello');

    fireEvent.click(screen.getByRole('button', { name: /send/i }));

    expect(
      await screen.findByText('seat "web-dev" cannot be messaged: refused by scope')
    ).toBeInTheDocument();
    expect(screen.getByRole('textbox')).toHaveValue('hello');
  });

  it('closes on a fresh mount after a previous one was opened', () => {
    const first = render(<SeatInputBox room="dev" seatKey="web-dev" />);
    fireEvent.click(screen.getByRole('button', { name: 'Show message input' }));
    expect(screen.getByRole('textbox')).toBeInTheDocument();
    first.unmount();

    render(<SeatInputBox room="dev" seatKey="web-dev" />);

    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });
});
