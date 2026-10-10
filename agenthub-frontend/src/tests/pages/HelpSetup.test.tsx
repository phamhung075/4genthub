/**
 * @fileoverview HelpSetup lists the "Connect your machine" section, and its command is the one the
 * installed client answers to.
 */

import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { HelpSetup } from '../../pages/HelpSetup';

describe('HelpSetup', () => {
  it('lists the connect-your-machine section and shows the connector command when expanded', () => {
    render(
      <MemoryRouter>
        <HelpSetup />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByText('Connect your machine'));

    expect(screen.getByText('4genteam sync connector --session <rig-session-name>')).toBeInTheDocument();
    expect(screen.getAllByText(/sessions:write/).length).toBeGreaterThan(0);
  });
});
