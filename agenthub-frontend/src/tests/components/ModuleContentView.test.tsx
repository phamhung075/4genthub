/**
 * @fileoverview ModuleContentView reads a module's content string as a human:
 * a skill block's one-line JSON becomes labelled sections with the SKILL.md text
 * intact, the exact stored string stays reachable behind a Raw toggle, and
 * content that is not JSON keeps the plain reading rather than crashing.
 */

import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { ModuleContentView } from '../../components/seats/ModuleContentView';

// The shape a skill module stores: one JSON object whose `content` is the whole
// SKILL.md, newlines escaped. This is what the old raw <pre> showed as one line.
const SKILL_BLOCK = JSON.stringify({
  content: '# Pod\n\nSlices are the unit.\n',
  source_path: 'skills/_canonical/pods/orchestration-team/SKILL.md',
  sha256: 'd13e08782a64b92b4db3f51d083f11fd6753f06e68052dbf2da174ab5618fa90',
});

describe('ModuleContentView', () => {
  it('renders a skill block as labelled sections, not as the escaped JSON line', () => {
    const { container } = render(<ModuleContentView content={SKILL_BLOCK} />);

    expect(screen.getByText('content')).toBeInTheDocument();
    expect(screen.getByText('source_path')).toBeInTheDocument();
    expect(screen.getByText('sha256')).toBeInTheDocument();
    expect(screen.getByText(/skills\/_canonical\/pods\/orchestration-team\/SKILL\.md/)).toBeInTheDocument();

    // The SKILL.md text keeps its own line breaks: the heading and the sentence are
    // both present, and no escaped "\n" is left in the rendered text.
    expect(screen.getByText(/# Pod/)).toBeInTheDocument();
    expect(container.textContent).not.toContain('\\n');
  });

  it('keeps the exact stored string behind the Raw toggle', () => {
    const { container } = render(<ModuleContentView content={SKILL_BLOCK} />);

    fireEvent.click(screen.getByRole('button', { name: 'Raw' }));

    expect(container.querySelector('pre')?.textContent).toBe(SKILL_BLOCK);
    expect(screen.getByRole('button', { name: 'Raw' })).toHaveAttribute('aria-pressed', 'true');

    fireEvent.click(screen.getByRole('button', { name: 'Formatted' }));

    expect(container.querySelector('pre')).toBeNull();
    expect(screen.getByText(/# Pod/)).toBeInTheDocument();
  });

  it('renders nested objects and arrays level by level', () => {
    render(
      <ModuleContentView
        content={JSON.stringify({
          name: 'mission-slice-sop',
          checks: ['plan', 'slice', 'close'],
          limits: { slices: 3, parallel: false },
        })}
      />
    );

    expect(screen.getByText('name')).toBeInTheDocument();
    expect(screen.getByText('plan')).toBeInTheDocument();
    expect(screen.getByText('slice')).toBeInTheDocument();
    expect(screen.getByText('close')).toBeInTheDocument();
    expect(screen.getByText('limits')).toBeInTheDocument();
    expect(screen.getByText('parallel')).toBeInTheDocument();
  });

  it('renders non-JSON content as plain text, with no toggle and no crash', () => {
    const { container } = render(<ModuleContentView content={'plain words\nsecond line'} />);

    expect(container.querySelector('pre')?.textContent).toBe('plain words\nsecond line');
    expect(screen.queryByRole('button', { name: 'Raw' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Formatted' })).not.toBeInTheDocument();
  });

  it('says empty content is empty instead of drawing an empty pane', () => {
    const { container } = render(<ModuleContentView content={'   '} />);

    expect(screen.getByText(/carries no content/)).toBeInTheDocument();
    expect(container.querySelector('pre')).toBeNull();
  });
});
