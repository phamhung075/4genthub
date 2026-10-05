/**
 * @fileoverview McpBlockForm publishes one whole MCP server as an mcp block and
 * refuses a block that carries a credential literal.
 */

import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { McpBlockForm } from '../../components/seats/McpBlockForm';
import { seatApi } from '../../services/seatApi';

vi.mock('../../services/seatApi', () => ({
  seatApi: { putModuleVersion: vi.fn() },
}));

const mockApi = vi.mocked(seatApi);

const renderForm = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <McpBlockForm />
    </QueryClientProvider>
  );
};

const fill = (label: string, value: string) =>
  fireEvent.change(screen.getByLabelText(label), { target: { value } });

describe('McpBlockForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApi.putModuleVersion.mockResolvedValue({
      success: true,
      module: { slug: 'my-server', kind: 'mcp', version: '1.0.0', sha256: 'sum' },
    });
  });

  it('publishes one http server as a block, with the secret left as a reference', async () => {
    renderForm();

    fill('Mcp block slug', 'my-server');
    fill('Mcp block version', '1.0.0');
    fill('Server name', 'my-server');
    fill('Server url', 'https://x.test/mcp');
    fill('Server headers', 'Authorization: Bearer ${A_TOKEN}');
    fireEvent.click(screen.getByRole('button', { name: 'Publish block' }));

    await waitFor(() =>
      expect(mockApi.putModuleVersion).toHaveBeenCalledWith('my-server', '1.0.0', {
        kind: 'mcp',
        content: JSON.stringify(
          {
            name: 'my-server',
            type: 'http',
            url: 'https://x.test/mcp',
            headers: { Authorization: 'Bearer ${A_TOKEN}' },
          },
          null,
          2
        ),
      })
    );
  });

  it('keeps Publish off and names the reason when a header carries a credential literal', () => {
    renderForm();

    fill('Mcp block slug', 'my-server');
    fill('Mcp block version', '1.0.0');
    fill('Server name', 'my-server');
    fill('Server url', 'https://x.test/mcp');
    fill('Server headers', 'Authorization: Bearer sk-abcdefghijklmnopqrstuvwx');

    expect(screen.getByRole('button', { name: 'Publish block' })).toBeDisabled();
    expect(screen.getByText(/reference a secret as \$\{ENV_VAR\}/)).toBeInTheDocument();
  });

  it('loads a pasted stdio block into the fields and publishes it', async () => {
    renderForm();

    const block = JSON.stringify({
      name: 'sequential-thinking',
      type: 'stdio',
      command: 'npx',
      args: ['-y', '@modelcontextprotocol/server-sequential-thinking'],
    });
    fireEvent.change(screen.getByLabelText('Paste a block'), { target: { value: block } });
    fireEvent.click(screen.getByRole('button', { name: 'Load block' }));

    expect(await screen.findByLabelText('Server command')).toHaveValue('npx');
    expect(screen.getByLabelText('Server args')).toHaveValue(
      '-y\n@modelcontextprotocol/server-sequential-thinking'
    );

    fill('Mcp block slug', 'sequential-thinking');
    fill('Mcp block version', '1.0.0');
    fireEvent.click(screen.getByRole('button', { name: 'Publish block' }));

    await waitFor(() =>
      expect(mockApi.putModuleVersion).toHaveBeenCalledWith('sequential-thinking', '1.0.0', {
        kind: 'mcp',
        content: JSON.stringify(
          {
            name: 'sequential-thinking',
            type: 'stdio',
            command: 'npx',
            args: ['-y', '@modelcontextprotocol/server-sequential-thinking'],
          },
          null,
          2
        ),
      })
    );
  });

  it('refuses a pasted block that is not a valid server and says why', () => {
    renderForm();

    fireEvent.change(screen.getByLabelText('Paste a block'), {
      target: { value: JSON.stringify({ name: 'a', type: 'http' }) },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Load block' }));

    expect(screen.getByText(/field url is required for a "http" server/)).toBeInTheDocument();
  });

  it('surfaces the server error when the version already exists', async () => {
    mockApi.putModuleVersion.mockRejectedValue(new Error('version 1.0.0 of module my-server already exists'));
    renderForm();

    fill('Mcp block slug', 'my-server');
    fill('Mcp block version', '1.0.0');
    fill('Server name', 'my-server');
    fill('Server url', 'https://x.test/mcp');
    fireEvent.click(screen.getByRole('button', { name: 'Publish block' }));

    expect(await screen.findByText(/already exists/)).toBeInTheDocument();
  });
});
