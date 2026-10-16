/**
 * sessionSteps - turns the stored events of a session into the steps a person reads.
 *
 * A connector uploads each transcript line of a seat as one `message` event whose payload is
 * `{text: <the line as JSON>}`. One line can hold several steps (an assistant turn carries
 * thinking, text and tool calls), so one event yields zero or more steps. A line that does
 * not parse is shown verbatim as a `text` step; nothing is dropped.
 *
 * @module utils/sessionSteps
 */

import type { SessionEvent } from '../types/sessionTypes';

export type SessionStepKind =
  | 'user'
  | 'assistant'
  | 'thinking'
  | 'tool_call'
  | 'tool_result'
  | 'meta'
  | 'withheld'
  | 'text';

export interface SessionStep {
  /** Unique within a session: the event seq plus the step's index inside the event. */
  key: string;
  seq: number;
  kind: SessionStepKind;
  /** The label on the step's header: a tool name, a role, or a meta label. */
  title: string;
  ts: string | null;
  /** The text a reader sees first. */
  body: string;
  /** Collapsed by default: tool arguments, or the reason a line was withheld. */
  detail?: string;
  isError?: boolean;
}

type Json = Record<string, unknown>;

const isObject = (value: unknown): value is Json =>
  value !== null && typeof value === 'object' && !Array.isArray(value);

const asString = (value: unknown): string => (typeof value === 'string' ? value : '');

function pretty(value: unknown): string {
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

// The text blocks of a message's content, joined; a bare string content is the text itself.
function contentText(content: unknown): string {
  if (typeof content === 'string') return content;
  if (!Array.isArray(content)) return '';
  return content
    .filter(isObject)
    .map((block) => asString(block.text))
    .filter((text) => text !== '')
    .join('\n');
}

function metaStep(base: Omit<SessionStep, 'kind' | 'title' | 'body'>, line: Json): SessionStep {
  const kind = asString(line.type);
  const summary: Record<string, string> = {
    session: asString(line.cwd),
    model_change: asString(line.model),
    thinking_level_change: asString(line.thinkingLevel),
    title: asString(line.title),
    custom: asString(line.customType),
  };
  return {
    ...base,
    kind: 'meta',
    title: kind.replace(/_/g, ' '),
    body: summary[kind] ?? '',
  };
}

function messageSteps(base: Omit<SessionStep, 'kind' | 'title' | 'body'>, line: Json): SessionStep[] {
  const message = line.message;
  if (!isObject(message)) return [metaStep(base, line)];
  const role = asString(message.role);

  if (role === 'user') {
    return [{ ...base, kind: 'user', title: 'User', body: contentText(message.content) }];
  }

  if (role === 'toolResult') {
    return [
      {
        ...base,
        kind: 'tool_result',
        title: asString(message.toolName) || 'tool result',
        body: contentText(message.content),
        isError: message.isError === true,
      },
    ];
  }

  if (role === 'assistant' && Array.isArray(message.content)) {
    const steps: SessionStep[] = [];
    message.content.filter(isObject).forEach((block, index) => {
      const key = `${base.key}.${index}`;
      const blockType = asString(block.type);
      if (blockType === 'thinking') {
        steps.push({ ...base, key, kind: 'thinking', title: 'Thinking', body: asString(block.thinking) });
      } else if (blockType === 'text') {
        steps.push({ ...base, key, kind: 'assistant', title: 'Assistant', body: asString(block.text) });
      } else if (blockType === 'toolCall') {
        steps.push({
          ...base,
          key,
          kind: 'tool_call',
          title: asString(block.name) || 'tool call',
          body: asString(block.intent),
          detail: pretty(block.arguments),
        });
      }
    });
    return steps;
  }

  // fileMention and any other role: a muted line naming the role.
  return [{ ...base, kind: 'meta', title: role || 'message', body: contentText(message.content) }];
}

/** The steps one event shows, in reading order. */
export function eventSteps(event: SessionEvent): SessionStep[] {
  const base = { key: String(event.seq), seq: event.seq, ts: event.ts };
  const payload = isObject(event.payload) ? event.payload : null;

  if (event.type === 'redaction_withheld') {
    const reason = payload ? asString(payload.reason) : '';
    return [{ ...base, kind: 'withheld', title: 'Withheld locally', body: reason, detail: payload ? pretty(payload) : undefined }];
  }

  if (event.type === 'message' && typeof event.payload === 'string') {
    return [{ ...base, kind: 'text', title: 'Output', body: event.payload }];
  }

  if (event.type === 'message' && payload) {
    if (payload.truncated === true) {
      return [{ ...base, kind: 'meta', title: 'truncated', body: 'The line exceeded the stored size and was cut.' }];
    }
    const raw = asString(payload.text);
    let line: unknown;
    try {
      line = JSON.parse(raw);
    } catch {
      return [{ ...base, kind: 'text', title: 'Output', body: raw }];
    }
    if (!isObject(line)) return [{ ...base, kind: 'text', title: 'Output', body: raw }];
    return line.type === 'message' ? messageSteps(base, line) : [metaStep(base, line)];
  }

  return [{ ...base, kind: 'meta', title: event.type, body: pretty(event.payload) }];
}

/** Every step of the events, oldest first. */
export function sessionSteps(events: SessionEvent[]): SessionStep[] {
  return events.flatMap(eventSteps);
}
