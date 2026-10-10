/**
 * @fileoverview SeatInputBox - the sessions page's chat input.
 *
 * Three properties are the whole point of this file, and each one is a way the component could be
 * wrong while looking right: it must render NO input on first mount; a refusal must arrive in the
 * SERVER's words rather than a generic failure; and opening it must not disturb the transcript the
 * window is streaming.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '../test-utils';
import { SeatInputBox } from '../../components/sessions/SeatInputBox';
import { SessionLiveView } from '../../components/sessions/SessionLiveView';
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
    const first = render(<SeatInputBox seatKey="web-dev" />);
    fireEvent.click(screen.getByRole('button', { name: 'Show message input' }));
    expect(screen.getByRole('textbox')).toBeInTheDocument();
    first.unmount();

    render(<SeatInputBox room="dev" seatKey="web-dev" />);

    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });
});

describe('SessionLiveView chat input', () => {
  const renderWindow = () =>
    render(
      <SessionLiveView
        sessionName="4genthub-min-web-dev@4genthub-min"
        room="4genthub-min"
        seatKey="web-dev"
        status="live"
        error={null}
        events={[
          { seq: 7, type: 'message', payload: 'the transcript line', ts: '2026-10-07T21:00:00Z' },
        ]}
      />
    );

  it('keeps rendering the transcript while the input drawer is open', () => {
    renderWindow();
    expect(screen.getByText('the transcript line')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Show message input' }));

    // Both at once: the drawer is open AND the read is untouched, which is what "the toggle does
    // not touch the transcript" means as an observation rather than as a hope.
    expect(screen.getByRole('textbox')).toBeInTheDocument();
    expect(screen.getByText('#7')).toBeInTheDocument();
    expect(screen.getByText('the transcript line')).toBeInTheDocument();
  });

  it('renders no chat input when the window has no seat', () => {
    render(
      <SessionLiveView sessionName={null} status="live" error={null} events={[]} />
    );

    expect(screen.queryByRole('button', { name: 'Show message input' })).not.toBeInTheDocument();
  });

  it('renders no chat input when the window has a seat but no room to address it in', () => {
    render(
      <SessionLiveView
        sessionName="4genthub-min-web-dev@4genthub-min"
        seatKey="web-dev"
        status="live"
        error={null}
        events={[]}
      />
    );

    // The route is room-scoped, so a seat with no room cannot be addressed at all. The window
    // stays watch-only rather than posting to a room it would have to guess.
    expect(screen.queryByRole('button', { name: 'Show message input' })).not.toBeInTheDocument();
  });
});
