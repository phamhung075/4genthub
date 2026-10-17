/**
 * @fileoverview sessionSteps turns a stored transcript-line event into the steps a reader sees:
 * an assistant turn splits into thinking, text and tool calls; a tool result keeps its error flag;
 * a line that does not parse is shown verbatim rather than dropped.
 */

import { logicSchema, sessionSteps } from '../../utils/sessionSteps';
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

describe('logicSchema', () => {
  // The schema 3/8 fixes: four lines, in this order, keys lowercase with one space after the colon.
  const SCHEMA = 'facts: branch=main; commit=8e706e18\nrule: rows carry the four fields\ndecision: build it now\nnext: render it, fe-dev';

  it('reads the four fields a step ends with, and leaves the reasoning above them', () => {
    const [step] = sessionSteps([
      line(6, {
        type: 'message',
        message: {
          role: 'assistant',
          content: [{ type: 'thinking', thinking: `the parser has the steps\nthe view is the gap\n${SCHEMA}` }],
        },
      }),
    ]);

    expect(step.logic).toEqual({
      facts: 'branch=main; commit=8e706e18',
      rule: 'rows carry the four fields',
      decision: 'build it now',
      next: 'render it, fe-dev',
    });
    // The raw thinking is kept whole: the schema is read FROM it, never in place of it.
    expect(step.body).toContain('the view is the gap');
    expect(step.body).toContain('next: render it, fe-dev');
  });

  it('reads a step that is exactly the four lines', () => {
    expect(logicSchema(SCHEMA)).not.toBeNull();
    expect(logicSchema(`${SCHEMA}\n\n`)).not.toBeNull();
  });

  it('leaves a step raw when the fields are out of order, incomplete, or merely mentioned', () => {
    expect(logicSchema('rule: r\ndecision: d\nnext: n\nfacts: f')).toBeNull();
    expect(logicSchema('facts: f\nrule: r\ndecision: d')).toBeNull();
    expect(logicSchema('I will send next: a frame, and decision: nothing yet')).toBeNull();
    expect(logicSchema('facts: f\nrule: r\ndecision: d\nnext : n')).toBeNull();
  });

  it('refuses a value past its cap, and accepts one at it', () => {
    expect(logicSchema(`facts: ${'x'.repeat(280)}\nrule: r\ndecision: d\nnext: n`)).not.toBeNull();
    expect(logicSchema(`facts: ${'x'.repeat(281)}\nrule: r\ndecision: d\nnext: n`)).toBeNull();
    expect(logicSchema(`facts: f\nrule: ${'x'.repeat(110)}\ndecision: d\nnext: n`)).not.toBeNull();
    expect(logicSchema(`facts: f\nrule: ${'x'.repeat(111)}\ndecision: d\nnext: n`)).toBeNull();
    expect(logicSchema(`facts: f\nrule: r\ndecision: ${'x'.repeat(100)}\nnext: n`)).not.toBeNull();
    expect(logicSchema(`facts: f\nrule: r\ndecision: ${'x'.repeat(101)}\nnext: n`)).toBeNull();
    expect(logicSchema(`facts: f\nrule: r\ndecision: d\nnext: ${'x'.repeat(78)}`)).not.toBeNull();
    expect(logicSchema(`facts: f\nrule: r\ndecision: d\nnext: ${'x'.repeat(79)}`)).toBeNull();
  });
});
