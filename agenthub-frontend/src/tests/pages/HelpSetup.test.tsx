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

    // The section teaches the command twice on purpose - the copyable box under "Step 3: Send a session"
    // and the connector guide's own one-shot line - so the query takes every occurrence, as the scope
    // assertion below does.
    expect(screen.getAllByText('4genteam sync connector --session <session-name>').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/sessions:write/).length).toBeGreaterThan(0);
    expect(screen.getByText('AGENTHUB_CONNECTOR_TOKEN=<your connector token>')).toBeInTheDocument();
    expect(screen.getByText('AGENTHUB_TOKEN=<your MCP token>')).toBeInTheDocument();
  });
});
