// Draws the ```mermaid fences of a document that is already in the DOM. Mermaid is a large
// library, so it is imported only when the document has a fence. Each fence's <pre> stays in
// place, hidden, beside its diagram: a redraw (a theme change) reads the source from it, and a
// fence that does not parse stays visible as code instead of disappearing.
let renderCount = 0;

export async function renderMermaidBlocks(
  container: HTMLElement,
  dark: boolean,
  isCancelled: () => boolean,
): Promise<void> {
  const fences = Array.from(container.querySelectorAll<HTMLElement>('pre > code.language-mermaid'));
  if (fences.length === 0) return;
  const { default: mermaid } = await import('mermaid');
  if (isCancelled()) return;
  mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: dark ? 'dark' : 'default' });
  container.querySelectorAll('.mermaid-diagram').forEach((diagram) => diagram.remove());

  for (const fence of fences) {
    const pre = fence.parentElement as HTMLElement;
    const id = `doc-mermaid-${++renderCount}`;
    try {
      const { svg } = await mermaid.render(id, fence.textContent ?? '');
      if (isCancelled()) return;
      const diagram = document.createElement('div');
      diagram.className = 'mermaid-diagram';
      diagram.innerHTML = svg;
      pre.after(diagram);
      pre.hidden = true;
    } catch {
      // Mermaid can leave its scratch element behind on a parse error; the fence stays shown.
      document.getElementById(`d${id}`)?.remove();
      pre.hidden = false;
    }
  }
}
