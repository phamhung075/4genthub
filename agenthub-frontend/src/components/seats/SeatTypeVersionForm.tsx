/**
 * Seat type version form - publish a new version of a seat type with its
 * module refs and default runtime. The server assigns the version number.
 *
 * @module components/seats/SeatTypeVersionForm
 */

import React, { useState } from 'react';
import { AlertCircle, Loader2 } from 'lucide-react';
import { Alert, AlertDescription } from '../ui/alert';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Select } from '../ui/select-simple';
import { Textarea } from '../ui/textarea';
import { useCreateSeatTypeVersion } from '../../hooks/useSeats';
import { MODULE_REF_MESSAGE, MODULE_REF_PATTERN } from '../../lib/seatNames';
import { SEAT_RUNTIMES } from '../../types/seatTypes';
import type { SeatRuntime, SeatType } from '../../types/seatTypes';

interface SeatTypeVersionFormProps {
  seatTypes: SeatType[];
}

const parseRefs = (text: string): string[] =>
  text
    .split('\n')
    .map(line => line.trim())
    .filter(line => line !== '');

const refsText = (seatType: SeatType) =>
  seatType.module_refs.map(ref => `${ref.slug}@${ref.version}`).join('\n');

export const SeatTypeVersionForm: React.FC<SeatTypeVersionFormProps> = ({ seatTypes }) => {
  const [slug, setSlug] = useState('');
  const [runtime, setRuntime] = useState<SeatRuntime>('claude-code');
  const [refs, setRefs] = useState('');
  const create = useCreateSeatTypeVersion(slug);

  const selectSeatType = (value: string) => {
    setSlug(value);
    const seatType = seatTypes.find(type => type.slug === value);
    if (seatType) {
      setRuntime(seatType.default_runtime as SeatRuntime);
      setRefs(refsText(seatType));
    }
  };

  const parsed = parseRefs(refs);
  const malformed = parsed.some(ref => !MODULE_REF_PATTERN.test(ref));
  const moduleSlugs = parsed.map(ref => ref.split('@')[0]);
  const duplicate = new Set(moduleSlugs).size !== moduleSlugs.length;
  const valid = slug !== '' && !malformed && !duplicate;

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!valid) {
      return;
    }
    create.mutate({ module_refs: parsed, default_runtime: runtime });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Create a seat type version</CardTitle>
        <CardDescription>
          The version number is assigned by the server (next patch of the latest). The default runtime is
          stored on the seat type and applies to all of its versions.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form className="space-y-3" onSubmit={handleSubmit}>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <label className="text-sm font-medium" htmlFor="seat-type-slug">
                Seat type
              </label>
              <Select
                id="seat-type-slug"
                aria-label="Seat type"
                value={slug}
                onChange={e => selectSeatType(e.target.value)}
              >
                <option value="">Select a seat type</option>
                {seatTypes.map(type => (
                  <option key={type.slug} value={type.slug}>
                    {type.name} ({type.slug})
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium" htmlFor="seat-type-runtime">
                Default runtime
              </label>
              <Select
                id="seat-type-runtime"
                aria-label="Default runtime"
                value={runtime}
                onChange={e => setRuntime(e.target.value as SeatRuntime)}
              >
                {SEAT_RUNTIMES.map(value => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </Select>
            </div>
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium" htmlFor="seat-type-refs">
              Module refs
            </label>
            <Textarea
              id="seat-type-refs"
              aria-label="Module refs"
              className="min-h-[100px] font-mono"
              value={refs}
              onChange={e => setRefs(e.target.value)}
              placeholder="rules@1.0.0"
            />
            {malformed && <p className="text-xs text-destructive">{MODULE_REF_MESSAGE}</p>}
            {!malformed && duplicate && (
              <p className="text-xs text-destructive">Each module may appear only once.</p>
            )}
          </div>
          {create.isError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{create.error.message}</AlertDescription>
            </Alert>
          )}
          <Button type="submit" disabled={!valid || create.isPending}>
            {create.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Create version
          </Button>
        </form>
      </CardContent>
    </Card>
  );
};
