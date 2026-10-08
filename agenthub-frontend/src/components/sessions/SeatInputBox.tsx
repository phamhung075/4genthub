/**
 * SeatInputBox - the chat input of ONE seat window: a toggle in the window's chrome and the
 * input as a drawer at the window's foot.
 *
 * CLOSED ON EVERY MOUNT, BY CONSTRUCTION. `open` is component state and nothing else - no app
 * state, no URL, no storage - so a reload returns the window to watch-only. The seat key is a
 * prop, and it is the only fact this component carries about the seat it addresses.
 *
 * WHY THE DRAWER IS PORTALLED. The toggle belongs in the chrome and the drawer at the foot, and
 * the drawer must PUSH the transcript rather than cover it: a window that streams what it is
 * watching cannot have its newest lines hidden by the thing that is typing. Both placements belong
 * to one piece of state, so the drawer renders into the foot node the window hands it
 * (`drawerTarget`). With no target it renders where the toggle is, which keeps the component
 * usable on its own and is the shape the tests exercise.
 *
 * A REFUSAL IS SHOWN VERBATIM. A seat can be refused by scope, and the server's sentence is the
 * only actionable thing in that response, so it lands beside the input rather than being replaced
 * by a generic failure.
 *
 * @module components/sessions/SeatInputBox
 * @version 1.0.0
 */

import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { AlertCircle, Loader2, MessageSquare, Send, X } from 'lucide-react';
import { Alert, AlertDescription } from '../ui/alert';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { useSendSeatMessage } from '../../hooks/useSeats';
import { cn } from '../../lib/utils';

export interface SeatInputBoxProps {
  /** The seat this box addresses: the only seat fact the component carries. */
  seatKey: string;
  /** The window's foot node. The drawer renders into it; without one the drawer renders in place. */
  drawerTarget?: HTMLElement | null;
  className?: string;
}

export const SeatInputBox: React.FC<SeatInputBoxProps> = ({
  seatKey,
  drawerTarget = null,
  className,
}) => {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState('');
  const send = useSendSeatMessage(seatKey);

  const refusal = send.error instanceof Error ? send.error.message : null;
  const trimmed = text.trim();

  const toggle = () => {
    // Opening starts from a clean sheet: a refusal from the last attempt says nothing about this one.
    if (!open) {
      send.reset();
    }
    setOpen(current => !current);
  };

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!trimmed || send.isPending) {
      return;
    }
    send.mutate({ text: trimmed }, { onSuccess: () => setText('') });
  };

  const drawer = (
    <form onSubmit={submit} className="border-t border-surface-border-hover p-3">
      <label className="sr-only" htmlFor={`seat-message-${seatKey}`}>
        Message {seatKey}
      </label>
      <Textarea
        id={`seat-message-${seatKey}`}
        aria-label={`Message ${seatKey}`}
        value={text}
        rows={2}
        onChange={event => setText(event.target.value)}
        placeholder="Send a message to this seat's session"
        className="min-h-0 resize-none"
      />
      {refusal && (
        <Alert variant="destructive" className="mt-2">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{refusal}</AlertDescription>
        </Alert>
      )}
      <div className="mt-2 flex justify-end">
        <Button type="submit" size="sm" disabled={send.isPending || !trimmed}>
          {send.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
          <span className="ml-2">Send</span>
        </Button>
      </div>
    </form>
  );

  return (
    <>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        aria-label={open ? 'Hide message input' : 'Show message input'}
        aria-expanded={open}
        className={cn('shrink-0', className)}
        onClick={toggle}
      >
        {open ? <X className="h-4 w-4" /> : <MessageSquare className="h-4 w-4" />}
      </Button>
      {open ? (drawerTarget ? createPortal(drawer, drawerTarget) : drawer) : null}
    </>
  );
};
