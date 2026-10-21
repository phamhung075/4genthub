/**
 * Seat occupant history - every recorded change of one seat's STORED occupant.
 *
 * The rows come from `GET .../occupant-history`, newest first, and are rendered in the order the
 * server returned them: the route orders by `at DESC` and holds no cap, so re-sorting or truncating
 * here would be a second, weaker copy of that rule.
 *
 * A row says the stored occupant changed. A running seat keeps the snapshot it launched with,
 * so the panel never reads a row as
 * "this seat is running X now"; the current pair is the LLM panel's job.
 *
 * @module components/seats/SeatOccupantHistoryPanel
 */

import React from 'react';
import { AlertCircle, ArrowRight, Loader2 } from 'lucide-react';
import { Alert, AlertDescription } from '../ui/alert';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { useSeatOccupantHistory } from '../../hooks/useSeats';
import type { SeatOccupantChange, SeatOccupantHistoryPanelProps } from '../../types/seatTypes';

const ChangeRow: React.FC<{ change: SeatOccupantChange }> = ({ change }) => (
  <li className="rounded-md border p-3 space-y-1">
    <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary">{change.from_runtime}</Badge>
        <span className="font-mono text-xs">{change.from_model.trim() || 'default model'}</span>
        <ArrowRight className="h-3 w-3 text-muted-foreground" aria-label="changed to" />
        <Badge variant="secondary">{change.to_runtime}</Badge>
        <span className="font-mono text-xs">{change.to_model.trim() || 'default model'}</span>
      </div>
      <time dateTime={change.at} className="text-xs text-muted-foreground">
        {new Date(change.at).toLocaleString()}
      </time>
    </div>
    <p className="text-xs text-muted-foreground">
      by <span className="font-mono">{change.actor}</span>
    </p>
  </li>
);

export const SeatOccupantHistoryPanel: React.FC<SeatOccupantHistoryPanelProps> = ({ room, seatKey }) => {
  const { changes, isLoading, error, refetch } = useSeatOccupantHistory(room, seatKey);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Occupant history</CardTitle>
        <CardDescription>
          Every recorded change of this seat's stored occupant, newest first. A running seat keeps the
          occupant it launched with until the room is restarted.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading occupant history...
          </div>
        )}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {error.message}
              <Button variant="outline" size="sm" className="ml-3" onClick={() => refetch()}>
                Retry
              </Button>
            </AlertDescription>
          </Alert>
        )}
        {!isLoading && !error && changes.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No occupant change has been recorded for this seat.
          </p>
        )}
        {!isLoading && !error && changes.length > 0 && (
          <ol className="space-y-2">
            {changes.map(change => (
              <ChangeRow key={`${change.seat}-${change.at}-${change.to_runtime}`} change={change} />
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  );
};
