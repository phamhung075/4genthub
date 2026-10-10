/**
 * Seat Preview - one seat's resolved snapshot: the hash, the rendered files and the policy.
 *
 * Extracted from SeatDetailPage's page-local PreviewTab so the seat-detail page and the
 * seat-authoring page render the SAME preview instead of two copies of it.
 *
 * `room` and `seat` are REQUIRED props and the component deliberately does not call useParams:
 * the authoring route is /seats/authoring and carries no :room/:seat params, so reading them
 * from the route would render an empty preview there and read as a data bug.
 *
 * The read is the existing useResolvedSeat hook - there is one resolved-seat query, not two.
 *
 * @module components/seats/SeatPreview
 * @version 1.0.0
 */

import React, { useState } from 'react';
import { AlertCircle, Check, Copy, FileCode, Loader2 } from 'lucide-react';
import { Alert, AlertDescription } from '../ui/alert';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { useResolvedSeat } from '../../hooks/useSeats';

export interface SeatPreviewProps {
  room: string;
  seat: string;
}

export const SeatPreview: React.FC<SeatPreviewProps> = ({ room, seat }) => {
  const { resolvedSeat, isLoading, error, refetch } = useResolvedSeat(room, seat);
  const [fileIndex, setFileIndex] = useState(0);
  const [copied, setCopied] = useState(false);

  const files = resolvedSeat?.files ?? [];
  const activeFile = files[fileIndex];
  const command = `4genteam sync pull ${room} ${seat}`;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(command);
    setCopied(true);
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Resolved snapshot</CardTitle>
          <CardDescription>
            The snapshot is immutable: the same seat definition always returns the same hash.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-3 flex-wrap text-sm">
            <span className="text-muted-foreground">Hash</span>
            <code className="rounded bg-muted px-2 py-1 font-mono">{resolvedSeat?.hash ?? '—'}</code>
            <span className="text-muted-foreground">Runtime</span>
            <Badge variant="secondary">{resolvedSeat?.runtime ?? '—'}</Badge>
          </div>
          <div className="flex items-center gap-2">
            <code className="rounded bg-muted px-2 py-1 font-mono text-xs">{command}</code>
            <Button variant="outline" size="sm" onClick={handleCopy}>
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              Copy pull command
            </Button>
          </div>
          {/* WHAT IS TRUE TODAY, and it is measured rather than promised: delivery is the MANUAL pull
              above, so the files reach the machine when they are pulled and the seat relaunches,
              and a session already running keeps what it loaded. AND THE RENDERER'S STARTUP HINT IS
              NOT UNREAD - ITS READER IS OUTSIDE THIS REPO: OpenRig's own daemon resolves
              startupFileYAML{DeliveryHint} at launch (codex-runtime-adapter.js:230 and :594 with its
              own detectDeliveryHint, claude-code-adapter.js:131 and :553, pi-runtime-adapter.js:95,
              agy-runtime-adapter.js:93, stub-runtime-adapter.js:72; the enum is declared at
              domain/types.d.ts:1277 - auto | guidance_merge | skill_install | send_text), so the
              emit is load-bearing and must not be deleted, and it is live on this rig:
              the rig's own agents/<seat>/agent.yaml carries delivery_hint: send_text, including
              this seat's own file. WHAT AN EARLIER WORDING OF THIS COMMENT GOT WRONG WAS THE SCOPE OF ITS SEARCH,
              NOT THE CLIENTS: agenthub_client/ and the Go port (agenthub_go/internal/clientsync,
              clientcmd, clientbridge, apiref and cmd/agenthubclient) do treat a resolved file as
              path + content and read no hint - but the launcher that reads it is not in this repo,
              so "no reader anywhere, in either client" was false of the tree. The hint delivers the
              role text into the pane AFTER launch; it is not what carries these files to a machine,
              so the sentence above stands as written. */}
          <p className="text-xs text-muted-foreground">
            A running session keeps what it loaded; the files reach the machine when they are pulled
            and the seat relaunches.
          </p>
          {isLoading && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading snapshot...
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
          {!isLoading && !error && !resolvedSeat && (
            <p className="text-sm text-muted-foreground">No resolved snapshot yet.</p>
          )}
        </CardContent>
      </Card>

      {resolvedSeat && (
        <div className="grid gap-4 lg:grid-cols-[240px_1fr]">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <FileCode className="h-4 w-4" /> Files ({files.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1">
              {files.length === 0 && <p className="text-sm text-muted-foreground">No files rendered.</p>}
              {files.map((file, index) => (
                <button
                  key={file.path}
                  type="button"
                  onClick={() => setFileIndex(index)}
                  className={`block w-full truncate rounded px-2 py-1 text-left text-sm ${
                    index === fileIndex ? 'bg-primary/10 text-primary' : 'hover:bg-muted'
                  }`}
                >
                  {file.path}
                </button>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">{activeFile?.path ?? 'File'}</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="max-h-[28rem] overflow-auto rounded bg-muted p-3 text-xs whitespace-pre-wrap">
                {activeFile?.content ?? ''}
              </pre>
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-base">Policy</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="max-h-72 overflow-auto rounded bg-muted p-3 text-xs whitespace-pre-wrap">
                {JSON.stringify(resolvedSeat.policy, null, 2)}
              </pre>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};
