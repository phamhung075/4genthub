/**
 * Seat permission policy panel - show and change the permission policy of one seat.
 *
 * @module components/seats/SeatPermissionPolicyPanel
 */

import React, { useEffect, useState } from 'react';
import { AlertCircle, Loader2 } from 'lucide-react';
import { Alert, AlertDescription } from '../ui/alert';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Select } from '../ui/select-simple';
import { useSetSeatPermissionPolicy } from '../../hooks/useSeats';
import { SEAT_PERMISSION_POLICIES } from '../../types/seatTypes';
import type { SeatPermissionPolicy, SeatPermissionPolicyPanelProps } from '../../types/seatTypes';

export const SeatPermissionPolicyPanel: React.FC<SeatPermissionPolicyPanelProps> = ({ room, seat, canWrite }) => {
  const update = useSetSeatPermissionPolicy(room, seat.seat_key);
  const [policy, setPolicy] = useState<SeatPermissionPolicy>(seat.permission_policy);

  useEffect(() => {
    setPolicy(seat.permission_policy);
  }, [seat.permission_policy]);

  const unchanged = policy === seat.permission_policy;

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (unchanged) {
      return;
    }
    update.mutate(policy);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Permission policy</CardTitle>
        <CardDescription>
          How much the seat may do without asking. New seats start with standard.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form className="space-y-3" onSubmit={handleSubmit}>
          <div className="space-y-1">
            <label className="text-sm font-medium" htmlFor="seat-permission-policy">
              Policy
            </label>
            <Select
              id="seat-permission-policy"
              aria-label="Permission policy"
              value={policy}
              onChange={e => setPolicy(e.target.value as SeatPermissionPolicy)}
              disabled={!canWrite}
            >
              {SEAT_PERMISSION_POLICIES.map(value => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </Select>
            {policy === 'yolo' && (
              <p className="text-xs text-destructive">
                yolo launches the seat with full permission bypass; the other policies keep the harness floor.
              </p>
            )}
          </div>
          {update.isError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{update.error.message}</AlertDescription>
            </Alert>
          )}
          {canWrite && (
            <Button type="submit" disabled={unchanged || update.isPending}>
              {update.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Save
            </Button>
          )}
        </form>
      </CardContent>
    </Card>
  );
};
