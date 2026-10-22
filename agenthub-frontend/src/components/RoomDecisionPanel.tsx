import React, { useState } from "react";
import { useLocation } from "react-router-dom";
import { Button } from "./ui/button";
import { RefreshButton } from "./ui/refresh-button";
import { Select } from "./ui/select-simple";
import { useAnswerRoomDecision, useRoomDecisions, useRooms } from "../hooks/useSeats";
import type { DecisionState, HumanAnswers, HumanQuestion, RoomDecision } from "../types/seatTypes";

/**
 * Room decision requests - the sidebar's lower half.
 *
 * A room lead's ask is mirrored up to the cloud by that room's daemon; the owner answers here, one
 * click per question, and the daemon applies the answer and closes the row. Three consequences,
 * from the room decision channel's contract:
 *
 * - The stored `questions` are rendered VERBATIM - the panel never re-spells an option.
 * - A row that is `answered` stays in the list. It is still with the room; only the daemon's
 *   `resolved`/`superseded` closes it.
 * - A refusal (unknown option, not pending any more, not the asked human) is rendered. It is never
 *   swallowed into a no-op.
 */

/** The room the URL names (`/seats/:room/:seat`), or "" on a page that names none. */
const roomFromPath = (pathname: string): string => {
  const match = /^\/seats\/([^/]+)\/[^/]+/.exec(pathname);
  return match ? decodeURIComponent(match[1]) : "";
};

const stateLabel = (state: DecisionState): string => {
  switch (state) {
    case "pending":
      return "waiting for you";
    case "answered":
      return "awaiting the room";
    case "resolved":
      return "resolved";
    default:
      return "superseded";
  }
};

/** What the row already carries for one question: a chosen option id, or a typed reply's text. */
const storedAnswer = (
  answers: HumanAnswers,
  questionId: string
): { optionId?: string; typedReply?: string } => {
  const stored = answers[questionId];
  if (typeof stored === "string") return { optionId: stored };
  if (stored) return { typedReply: stored.text };
  return {};
};

interface QuestionChoiceProps {
  question: HumanQuestion;
  chosen?: string;
  stored: { optionId?: string; typedReply?: string };
  busy: boolean;
  onChoose: (optionId: string) => void;
  onSend: (optionId: string) => void;
}

const QuestionChoice: React.FC<QuestionChoiceProps> = ({
  question,
  chosen,
  stored,
  busy,
  onChoose,
  onSend,
}) => {
  const recorded = chosen ?? stored.optionId;
  const alreadyRecorded = Boolean(stored.optionId ?? stored.typedReply);

  return (
    <fieldset className="space-y-1">
      <legend className="text-xs font-medium">{question.question}</legend>
      <div className="flex flex-col gap-1">
        {question.options.map((option) => {
          const selected = chosen === option.id || (!chosen && stored.optionId === option.id);
          return (
            <Button
              key={option.id}
              type="button"
              size="sm"
              variant={selected ? "default" : "outline"}
              className="h-auto justify-start py-1.5 text-left whitespace-normal"
              aria-pressed={selected}
              onClick={() => onChoose(option.id)}
            >
              <span>
                {option.label}
                {option.recommended ? (
                  <span className="ml-1 opacity-70">(recommended)</span>
                ) : null}
              </span>
            </Button>
          );
        })}
      </div>
      {stored.typedReply ? (
        <p className="text-[11px] text-base-secondary">Answered in words: {stored.typedReply}</p>
      ) : null}
      <Button
        size="sm"
        variant="secondary"
        disabled={busy || alreadyRecorded || !recorded}
        onClick={() => {
          if (recorded) onSend(recorded);
        }}
      >
        {alreadyRecorded ? "Answer recorded" : "Send answer"}
      </Button>
    </fieldset>
  );
};

export const RoomDecisionPanel: React.FC = () => {
  const { pathname } = useLocation();
  const { rooms } = useRooms();
  const [pickedRoom, setPickedRoom] = useState("");
  const [choices, setChoices] = useState<Record<string, Record<string, string>>>({});

  const room = pickedRoom || roomFromPath(pathname) || rooms[0]?.slug || "";
  const { decisions, isLoading, error, refetch } = useRoomDecisions(room);
  const answer = useAnswerRoomDecision(room);

  const open = decisions.filter(
    (decision: RoomDecision) => decision.state === "pending" || decision.state === "answered"
  );

  const choose = (decisionId: string, questionId: string, optionId: string) =>
    setChoices((previous) => ({
      ...previous,
      [decisionId]: { ...(previous[decisionId] ?? {}), [questionId]: optionId },
    }));

  const pendingCount = decisions.filter((d: RoomDecision) => d.state === "pending").length;

  return (
    <section
      className="space-y-2.5"
      aria-label="Room decision requests"
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h2 className="text-xs font-semibold tracking-wide uppercase text-base-secondary">
            Decision requests
          </h2>
          {pendingCount > 0 ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-accent/15 px-1.5 py-0.5 text-[10px] font-semibold text-accent">
              <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
              {pendingCount}
            </span>
          ) : null}
        </div>
        <RefreshButton
          onClick={() => {
            void refetch();
          }}
          loading={isLoading}
          title="Refresh decision requests"
        />
      </div>

      {rooms.length > 1 ? (
        <Select
          value={room}
          aria-label="Room"
          className="rounded-lg bg-surface/80 border-surface-border-hover focus:border-accent"
          onChange={(event) => setPickedRoom(event.target.value)}
        >
          {rooms.map((option) => (
            <option key={option.id} value={option.slug}>
              {option.name} ({option.slug})
            </option>
          ))}
        </Select>
      ) : null}

      {!room ? (
        <p className="text-xs text-base-secondary">
          No room yet - decision requests appear once a room exists.
        </p>
      ) : isLoading ? (
        <p className="text-xs text-base-secondary">Reading decision requests for {room}...</p>
      ) : error ? (
        <p className="text-xs text-error" role="alert">
          Could not read {room}'s decision requests: {error.message}
        </p>
      ) : open.length === 0 ? (
        <p className="text-xs text-base-secondary">No open decision requests for {room}.</p>
      ) : (
        open.map((decision) => {
          const isPendingValidation = decision.state === "pending";
          return (
            <article
              key={decision.id}
              className={`space-y-2 rounded-lg border p-2.5 ${
                isPendingValidation
                  ? "border-accent/40 bg-accent/[0.03] shadow-sm"
                  : "border-surface-border-hover bg-surface/40"
              }`}
            >
              <header className="space-y-0.5">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-1.5">
                    {isPendingValidation ? (
                      <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
                    ) : null}
                    <span className="text-xs font-medium text-base-primary">
                      {decision.summary ?? "Decision request"}
                    </span>
                  </div>
                  <span
                    className={`text-[10px] font-medium uppercase tracking-wider px-1.5 py-0.5 rounded ${
                      isPendingValidation
                        ? "bg-accent/15 text-accent"
                        : "bg-surface-hover text-base-secondary"
                    }`}
                  >
                    {stateLabel(decision.state)}
                  </span>
                </div>
                <p className="text-[11px] text-base-secondary">
                  {decision.author_seat_key} · {new Date(decision.created_at).toLocaleString()}
                </p>
              </header>
              {decision.detail ? (
                <p className="text-xs text-base-secondary whitespace-pre-wrap rounded bg-surface/50 p-1.5">
                  {decision.detail}
                </p>
              ) : null}
              {decision.questions.map((question) => (
                <QuestionChoice
                  key={question.id}
                  question={question}
                  chosen={choices[decision.id]?.[question.id]}
                  stored={storedAnswer(decision.answers ?? {}, question.id)}
                  busy={answer.isPending}
                  onChoose={(optionId) => choose(decision.id, question.id, optionId)}
                  onSend={(optionId) =>
                    answer.mutate({
                      decisionId: decision.id,
                      answer: { question_id: question.id, option_id: optionId },
                    })
                  }
                />
              ))}
            </article>
          );
        })
      )}

      {answer.isError ? (
        <p className="text-xs text-error" role="alert">
          The answer was refused: {answer.error.message}
        </p>
      ) : null}

      {answer.isSuccess && answer.data.complete ? (
        <p className="text-[11px] text-base-secondary">
          All questions answered - waiting for the room to apply it.
        </p>
      ) : null}
    </section>
  );
};

export default RoomDecisionPanel;
