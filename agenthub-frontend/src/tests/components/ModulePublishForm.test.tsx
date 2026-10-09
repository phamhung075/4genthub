/**
 * The publish form's PREFILL, and the two refusals that keep an immutable version off the wire.
 *
 * WHY THESE CASES AND NOT OTHERS. The route refuses a second PUT of the same slug@version with
 * different content (409) and treats a repeat with identical content as a no-op. Both are therefore
 * decided in the form, and BOTH are asserted here as "no request was sent" rather than as "the field
 * is disabled" alone - a disabled button that still fired the mutation would pass the weaker check.
 * The kind is asserted DISABLED while editing because the module's kind is fixed at first publish
 * and a different one is refused server-side.
 */

import React from 'react';
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { render } from '../test-utils';
import { ModulePublishForm } from '../../components/seats/ModulePublishForm';
import { seatApi } from '../../services/seatApi';
import type { ModuleVersionResponse } from '../../types/seatTypes';

vi.mock('../../services/seatApi', () => ({
  seatApi: {
    getModuleVersion: vi.fn(),
    putModuleVersion: vi.fn(),
  },
}));

const mockApi = vi.mocked(seatApi);

const BLOCK = { slug: 'guide-web-dev', kind: 'instruction' as const, version: '1.2.0', sha256: 'abc' };
const BLOCK_CONTENT = '# Web dev guide\n\nOriginal text.\n';
const EDITED_CONTENT = `${BLOCK_CONTENT}\nA new line.\n`;

const publishButton = () => screen.getByRole('button', { name: /^publish/i });

beforeEach(() => {
  vi.clearAllMocks();
  mockApi.getModuleVersion.mockResolvedValue({
    success: true,
    module: {
      slug: BLOCK.slug,
      kind: 'instruction',
      version: BLOCK.version,
      content: BLOCK_CONTENT,
      checksum: 'sum',
    },
  });
  mockApi.putModuleVersion.mockResolvedValue({
    success: true,
    module: { slug: BLOCK.slug, kind: 'instruction', version: '1.4.0', sha256: 'def' },
  });
});

describe('ModulePublishForm', () => {
  it('prefills slug, version, kind and content from the block it was handed', async () => {
    render(<ModulePublishForm block={BLOCK} />);

    await waitFor(() => expect(screen.getByLabelText('Module content')).toHaveValue(BLOCK_CONTENT));
    expect(screen.getByLabelText('Module slug')).toHaveValue(BLOCK.slug);
    expect(screen.getByLabelText('Module version')).toHaveValue(BLOCK.version);
    expect(screen.getByLabelText('Module kind')).toHaveValue('instruction');
    // The block's OWN version was read, not its latest: the form edits what the caller pointed at.
    expect(mockApi.getModuleVersion).toHaveBeenCalledWith(BLOCK.slug, BLOCK.version);
    // A module's kind is set on its first publish and a different one is refused, so it is fixed here.
    expect(screen.getByLabelText('Module kind')).toBeDisabled();
  });

  it('sends NOTHING for an unchanged block, so a no-change edit never earns the 409', async () => {
    render(<ModulePublishForm block={BLOCK} />);
    await waitFor(() => expect(screen.getByLabelText('Module content')).toHaveValue(BLOCK_CONTENT));

    expect(screen.getByText(/nothing to publish/i)).toBeInTheDocument();
    expect(publishButton()).toBeDisabled();

    fireEvent.click(publishButton());
    expect(mockApi.putModuleVersion).not.toHaveBeenCalled();
  });

  it('sends NOTHING when the content changed but the version did not, naming the version that exists', async () => {
    render(<ModulePublishForm block={BLOCK} />);
    const content = await screen.findByLabelText('Module content');
    // The fields are held until the block lands: a keystroke typed into a form that is about to be
    // seeded would be overwritten by the seed, so the edit below has to wait for the seed first.
    await waitFor(() => expect(content).toHaveValue(BLOCK_CONTENT));

    fireEvent.change(content, { target: { value: EDITED_CONTENT } });

    expect(await screen.findByText(/already exists with different content/i)).toBeInTheDocument();
    expect(screen.getByText(new RegExp(`${BLOCK.slug}@${BLOCK.version}`))).toBeInTheDocument();
    expect(publishButton()).toBeDisabled();

    fireEvent.click(publishButton());
    expect(mockApi.putModuleVersion).not.toHaveBeenCalled();
  });

  it('publishes the edit as a NEW version instead of reusing the one being edited', async () => {
    const onPublished = vi.fn();
    render(<ModulePublishForm block={BLOCK} onPublished={onPublished} />);
    const content = await screen.findByLabelText('Module content');
    await waitFor(() => expect(content).toHaveValue(BLOCK_CONTENT));

    fireEvent.change(content, { target: { value: EDITED_CONTENT } });
    fireEvent.change(screen.getByLabelText('Module version'), { target: { value: '1.4.0' } });

    const button = publishButton();
    expect(button).toBeEnabled();
    fireEvent.click(button);

    await waitFor(() =>
      expect(mockApi.putModuleVersion).toHaveBeenCalledWith(BLOCK.slug, '1.4.0', {
        kind: 'instruction',
        content: EDITED_CONTENT,
      })
    );
    // The version being edited is never the one sent: that is the whole point of the prefill.
    expect(mockApi.putModuleVersion).not.toHaveBeenCalledWith(
      BLOCK.slug,
      BLOCK.version,
      expect.anything()
    );
    await waitFor(() => expect(onPublished).toHaveBeenCalled());
  });

  it('still creates a new module when no block is being edited, and reads no block content', async () => {
    render(<ModulePublishForm />);

    // The prefill machinery must not reach for a version when there is nothing to edit.
    expect(mockApi.getModuleVersion).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText('Module slug'), { target: { value: 'new-block' } });
    fireEvent.change(screen.getByLabelText('Module version'), { target: { value: '1.0.0' } });
    fireEvent.change(screen.getByLabelText('Module content'), { target: { value: 'body\n' } });

    expect(screen.getByLabelText('Module kind')).toBeEnabled();
    fireEvent.click(publishButton());

    await waitFor(() =>
      expect(mockApi.putModuleVersion).toHaveBeenCalledWith('new-block', '1.0.0', {
        kind: 'instruction',
        content: 'body\n',
      })
    );
  });

  it('holds the fields until the block lands, so a keystroke cannot be overwritten by the seed', async () => {
    let settle: (value: ModuleVersionResponse) => void = () => {};
    mockApi.getModuleVersion.mockReturnValueOnce(
      new Promise<ModuleVersionResponse>(resolve => {
        settle = resolve;
      })
    );
    render(<ModulePublishForm block={BLOCK} />);

    expect(screen.getByLabelText('Module content')).toBeDisabled();
    expect(screen.getByLabelText('Module version')).toBeDisabled();
    expect(publishButton()).toBeDisabled();

    settle({
      success: true,
      module: {
        slug: BLOCK.slug,
        kind: 'instruction',
        version: BLOCK.version,
        content: BLOCK_CONTENT,
        checksum: 'sum',
      },
    });

    await waitFor(() => expect(screen.getByLabelText('Module content')).toHaveValue(BLOCK_CONTENT));
    expect(screen.getByLabelText('Module content')).toBeEnabled();
  });
});
