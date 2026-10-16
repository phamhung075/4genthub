/**
 * @fileoverview sessionSteps turns a stored transcript-line event into the steps a reader sees:
 * an assistant turn splits into thinking, text and tool calls; a tool result keeps its error flag;
 * a line that does not parse is shown verbatim rather than dropped.
 */

import { sessionSteps } from '../../utils/sessionSteps';
import type { SessionEvent } from '../../types/sessionTypes';

const line = (seq: number, entry: unknown): SessionEvent => ({
  seq,
  type: 'message',
  payload: { text: JSON.stringify(entry) },
  ts: null,
});

describe('sessionSteps', () => {
  it('splits an assistant turn into thinking, text and a tool call with its arguments', () => {
    const steps = sessionSteps([
      line(1, {
        type: 'message',
        message: {
          role: 'assistant',
          content: [
            { type: 'thinking', thinking: 'plan it' },
            { type: 'text', text: 'Running the tests.' },
            { type: 'toolCall', name: 'bash', intent: 'Run tests', arguments: { command: 'go test' } },
          ],
        },
      }),
    ]);

    expect(steps.map((step) => step.kind)).toEqual(['thinking', 'assistant', 'tool_call']);
    expect(new Set(steps.map((step) => step.key)).size).toBe(3);
    expect(steps[2]).toMatchObject({ title: 'bash', body: 'Run tests' });
    expect(steps[2].detail).toContain('go test');
  });

  it('keeps a tool result with its tool name and error flag', () => {
    const [step] = sessionSteps([
      line(2, {
        type: 'message',
        message: { role: 'toolResult', toolName: 'bash', isError: true, content: [{ type: 'text', text: 'boom' }] },
      }),
    ]);

    expect(step).toMatchObject({ kind: 'tool_result', title: 'bash', body: 'boom', isError: true });
  });

  it('shows a line that is not JSON verbatim and a withheld event as a withheld step', () => {
    const steps = sessionSteps([
      { seq: 3, type: 'message', payload: { text: 'plain output' }, ts: null },
      { seq: 4, type: 'redaction_withheld', payload: { reason: 'unsure', bytes: 90 }, ts: null },
    ]);

    expect(steps[0]).toMatchObject({ kind: 'text', body: 'plain output' });
    expect(steps[1]).toMatchObject({ kind: 'withheld', body: 'unsure' });
  });

  it('renders session bookkeeping as a meta step', () => {
    const [step] = sessionSteps([line(5, { type: 'model_change', model: 'deepseek-flash' })]);

    expect(step).toMatchObject({ kind: 'meta', title: 'model change', body: 'deepseek-flash' });
  });
});
