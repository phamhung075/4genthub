/**
 * Seat Authoring Page - modules and seat types.
 *
 * Lists and publishes immutable module versions, lists seat types and
 * creates seat type versions that compose modules into a role.
 *
 * @module pages/SeatAuthoringPage
 * @version 1.0.0
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, Loader2 } from 'lucide-react';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { ModulePublishForm } from '../components/seats/ModulePublishForm';
import { SeatTypeVersionForm } from '../components/seats/SeatTypeVersionForm';
import { useModules, useSeatTypes } from '../hooks/useSeats';

export const SeatAuthoringPage: React.FC = () => {
  const navigate = useNavigate();
  const { seatTypes, isLoading, error, refetch } = useSeatTypes();
  const { modules, isLoading: modulesLoading, error: modulesError, refetch: refetchModules } = useModules();

  return (
    <div className="container mx-auto space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Seat authoring</h1>
          <p className="text-muted-foreground mt-2">
            Modules are versioned building blocks; a seat type lists the module versions a role is made of.
          </p>
        </div>
        <Button variant="outline" onClick={() => navigate('/seats')}>
          Back to seats
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Modules</CardTitle>
          <CardDescription>The latest published version of each module.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {modulesLoading && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading modules...
            </div>
          )}
          {modulesError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {modulesError.message}
                <Button variant="outline" size="sm" className="ml-3" onClick={() => refetchModules()}>
                  Retry
                </Button>
              </AlertDescription>
            </Alert>
          )}
          {!modulesLoading && !modulesError && modules.length === 0 && (
            <p className="text-sm text-muted-foreground">No modules yet.</p>
          )}
          {modules.map(module => (
            <div key={module.slug} className="flex flex-wrap items-center gap-2 rounded-md border p-3">
              <span className="font-mono font-medium">{module.slug}</span>
              <Badge variant="secondary">{module.kind}</Badge>
              <Badge variant="outline">{module.version}</Badge>
              <code className="text-xs text-muted-foreground">{module.sha256.slice(0, 8)}</code>
            </div>
          ))}
        </CardContent>
      </Card>

      <ModulePublishForm />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Seat types</CardTitle>
          <CardDescription>Each seat type, its default runtime and its latest version's modules.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoading && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading seat types...
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
          {!isLoading && !error && seatTypes.length === 0 && (
            <p className="text-sm text-muted-foreground">No seat types yet.</p>
          )}
          {seatTypes.map(type => (
            <div key={type.slug} className="rounded-md border p-3 space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{type.name}</span>
                <code className="text-xs text-muted-foreground">{type.slug}</code>
                <Badge variant="secondary">{type.default_runtime ?? 'no runtime'}</Badge>
                <Badge variant="outline">{type.latest_version ?? 'no version'}</Badge>
              </div>
              {type.description && <p className="text-sm text-muted-foreground">{type.description}</p>}
              <div className="flex flex-wrap gap-1">
                {type.module_refs.map(ref => (
                  <Badge key={`${ref.slug}@${ref.version}`} variant="outline" className="font-mono">
                    {ref.slug}@{ref.version}
                  </Badge>
                ))}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <SeatTypeVersionForm seatTypes={seatTypes} />
    </div>
  );
};
