import { beforeEach, describe, expect, it, vi } from 'vitest';

const render = vi.fn();
const initialize = vi.fn();
vi.mock('mermaid', () => ({ default: { render, initialize } }));

import { renderMermaidBlocks } from '../../lib/mermaidDiagrams';

const doc = (html: string) => {
  const container = document.createElement('div');
  container.innerHTML = html;
  document.body.appendChild(container);
  return container;
};

const FENCE = '<pre><code class="language-mermaid">sequenceDiagram\n  A->>B: hi\n</code></pre>';

describe('renderMermaidBlocks', () => {
  beforeEach(() => {
    render.mockReset();
    initialize.mockReset();
  });

  it('draws each mermaid fence beside its hidden source', async () => {
    render.mockResolvedValue({ svg: '<svg data-testid="drawn"></svg>' });
    const container = doc(FENCE);

    await renderMermaidBlocks(container, true, () => false);

    expect(render).toHaveBeenCalledWith(expect.any(String), 'sequenceDiagram\n  A->>B: hi\n');
    expect(initialize).toHaveBeenCalledWith(expect.objectContaining({ theme: 'dark', securityLevel: 'strict' }));
    expect(container.querySelector('.mermaid-diagram svg')).not.toBeNull();
    expect(container.querySelector('pre')?.hidden).toBe(true);
  });

  it('redraws without stacking a second diagram', async () => {
    render.mockResolvedValue({ svg: '<svg></svg>' });
    const container = doc(FENCE);

    await renderMermaidBlocks(container, false, () => false);
    await renderMermaidBlocks(container, true, () => false);

    expect(container.querySelectorAll('.mermaid-diagram')).toHaveLength(1);
  });

  it('leaves a fence that does not parse visible as code', async () => {
    render.mockRejectedValue(new Error('Parse error'));
    const container = doc(FENCE);

    await renderMermaidBlocks(container, false, () => false);

    expect(container.querySelector('.mermaid-diagram')).toBeNull();
    expect(container.querySelector('pre')?.hidden).toBe(false);
  });

  it('never loads mermaid for a document without a fence', async () => {
    const container = doc('<pre><code class="language-bash">ls</code></pre>');

    await renderMermaidBlocks(container, false, () => false);

    expect(initialize).not.toHaveBeenCalled();
    expect(render).not.toHaveBeenCalled();
  });
});
