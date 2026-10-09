/**
 * Seat LLM panel - switch the runtime and model of one seat's occupant.
 *
 * @module components/seats/SeatLlmPanel
 */

import React, { useEffect, useState } from 'react';
import { AlertCircle, Loader2 } from 'lucide-react';
import { Alert, AlertDescription } from '../ui/alert';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Select } from '../ui/select-simple';
import { useUpdateSeatOccupant } from '../../hooks/useSeats';
import { isValidSeatModel, SEAT_MODEL_MESSAGE } from '../../lib/seatNames';
import { SEAT_RUNTIMES } from '../../types/seatTypes';
import type { SeatLlmPanelProps, SeatRuntime } from '../../types/seatTypes';

export const SeatLlmPanel: React.FC<SeatLlmPanelProps> = ({ room, seat }) => {
  const update = useUpdateSeatOccupant(room, seat.seat_key);
  const [runtime, setRuntime] = useState(seat.runtime);
  const [model, setModel] = useState(seat.model);

  useEffect(() => {
    setRuntime(seat.runtime);
    setModel(seat.model);
  }, [seat.runtime, seat.model]);

  const trimmed = model.trim();
  const valid = isValidSeatModel(trimmed);
  const unchanged = runtime === seat.runtime && trimmed === seat.model;

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!valid || unchanged) {
      return;
    }
    update.mutate({ runtime: runtime as SeatRuntime, model: trimmed });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">LLM</CardTitle>
        <CardDescription>The runtime and model that occupy this seat.</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="space-y-3" onSubmit={handleSubmit}>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <label className="text-sm font-medium" htmlFor="llm-runtime">
                Runtime
              </label>
              <Select
                id="llm-runtime"
                aria-label="LLM runtime"
                value={runtime}
                onChange={e => setRuntime(e.target.value)}
              >
                {SEAT_RUNTIMES.map(value => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium" htmlFor="llm-model">
                Model
              </label>
              <Input
                id="llm-model"
                aria-label="LLM model"
                value={model}
                onChange={e => setModel(e.target.value)}
                placeholder="default"
              />
              <p className="text-xs text-muted-foreground">
                Model id for this runtime, for example claude-opus-4-6. An empty box changes nothing:
                the seat keeps the model it already has.
              </p>
              {!valid && <p className="text-xs text-destructive">{SEAT_MODEL_MESSAGE}</p>}
            </div>
          </div>
          {update.isError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{update.error.message}</AlertDescription>
            </Alert>
          )}
          <Button type="submit" disabled={!valid || unchanged || update.isPending}>
            {update.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Save
          </Button>
        </form>
        <p className="mt-4 text-xs text-muted-foreground">
          Saved in 4genthub. A model change is applied to the running seat with{' '}
          <code className="rounded bg-muted px-1 font-mono">
            4genteam sync switch &lt;room&gt; &lt;seat&gt; --model &lt;id&gt;
          </code>
          ; a runtime change takes effect after the room is restarted with{' '}
          <code className="rounded bg-muted px-1 font-mono">rig up</code>.
        </p>
      </CardContent>
    </Card>
  );
};
