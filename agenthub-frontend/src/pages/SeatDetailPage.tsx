/**
 * Seat Detail Page - One seat's modules, links, preview and occupant.
 *
 * Tabs:
 *  1. Modules - seat type module refs with the seat/room/company overlays applied
 *  2. Links   - outgoing seat links (allow flag + kind)
 *  3. Preview - the resolved snapshot (hash, files, policy)
 *  4. LLM     - runtime and model of the occupant, editable
 *
 * @module pages/SeatDetailPage
 * @version 1.0.0
 */

import React, { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  AlertCircle,
  ArrowLeft,
  Brain,
  Check,
  Copy,
  FileCode,
  Link2,
  Loader2,
  Package,
  Plus,
  Trash2,
} from 'lucide-react';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Checkbox } from '../components/ui/checkbox';
import { Input } from '../components/ui/input';
import { Select } from '../components/ui/select-simple';
import { Separator } from '../components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Textarea } from '../components/ui/textarea';
import {
  useModuleVersion,
  useResolvedSeat,
  useSeatLinks,
  useSeatOverlays,
  useSeatTypes,
  useSeats,
  useUpdateOverlay,
  useUpsertSeatLink,
} from '../hooks/useSeats';
import { SeatLlmPanel } from '../components/seats/SeatLlmPanel';
import { computeEffectiveModules } from '../lib/seatModules';
import { SEAT_LINK_KINDS } from '../types/seatTypes';
import type {
  EffectiveSeatModule,
  Seat,
  SeatLinkKind,
  SeatLinksTabProps,
  SeatModulesTabProps,
  SeatOverlayOp,
  SeatOverlayOpKind,
  SeatOverlayScope,
  SeatOverlays,
} from '../types/seatTypes';

const SCOPES: SeatOverlayScope[] = ['seat', 'room', 'company'];
const OP_KINDS: SeatOverlayOpKind[] = ['add', 'remove', 'override', 'pin'];

const changeText = (kind: SeatOverlayOpKind) => {
  switch (kind) {
    case 'add':
      return 'added';
    case 'remove':
      return 'removed';
    case 'override':
      return 'overridden';
    case 'pin':
      return 'pinned';
  }
};

const QueryError: React.FC<{ message: string; onRetry: () => void }> = ({ message, onRetry }) => (
  <Alert variant="destructive">
    <AlertCircle className="h-4 w-4" />
    <AlertDescription>
      {message}
      <Button variant="outline" size="sm" className="ml-3" onClick={onRetry}>
        Retry
      </Button>
    </AlertDescription>
  </Alert>
);

const Loading: React.FC<{ label: string }> = ({ label }) => (
  <div className="flex items-center gap-2 text-muted-foreground">
    <Loader2 className="h-4 w-4 animate-spin" /> {label}
  </div>
);

// ---------------------------------------------------------------------------
// Modules
// ---------------------------------------------------------------------------

const ModuleRow: React.FC<{ module: EffectiveSeatModule }> = ({ module }) => {
  const [showContent, setShowContent] = useState(false);
  const { module: fetched, isLoading, error } = useModuleVersion(module.slug, module.version);

  return (
    <div className="rounded-md border p-3 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium">{module.slug}</span>
          {fetched && <Badge variant="secondary">{fetched.kind}</Badge>}
          {module.removed ? (
            <Badge variant="destructive">removed</Badge>
          ) : (
            <Badge variant="outline">@{module.version}</Badge>
          )}
          {module.changes.map((change, index) => (
            <Badge key={`${change.scope}-${change.kind}-${index}`} variant="outline">
              {changeText(change.kind)} by {change.scope}
            </Badge>
          ))}
        </div>
        {!module.removed && (
          <Button variant="ghost" size="sm" onClick={() => setShowContent(prev => !prev)}>
            {showContent ? 'Hide content' : 'Show content'}
          </Button>
        )}
      </div>
      {showContent && !module.removed && (
        <div className="space-y-1">
          {module.overridden && module.contentOverride !== undefined ? (
            <pre className="max-h-64 overflow-auto rounded bg-muted p-3 text-xs whitespace-pre-wrap">
              {module.contentOverride}
            </pre>
          ) : isLoading ? (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="h-3 w-3 animate-spin" /> Loading {module.slug}@
              {module.version}...
            </div>
          ) : error ? (
            <p className="text-xs text-destructive">{error.message}</p>
          ) : fetched ? (
            <pre className="max-h-64 overflow-auto rounded bg-muted p-3 text-xs whitespace-pre-wrap">
              {fetched.content}
            </pre>
          ) : (
            <p className="text-xs text-muted-foreground">
              Content is resolved on the server when the version follows latest.
            </p>
          )}
        </div>
      )}
    </div>
  );
};

const ModulesTab: React.FC<SeatModulesTabProps> = ({ seatType }) => {
  const { room = '', seat = '' } = useParams<{ room: string; seat: string }>();
  const { overlays, isLoading, error, refetch } = useSeatOverlays(room, seat);
  const updateOverlay = useUpdateOverlay(room, seat);

  const [scope, setScope] = useState<SeatOverlayScope>('seat');
  const [opKind, setOpKind] = useState<SeatOverlayOpKind>('add');
  const [slug, setSlug] = useState('');
  const [version, setVersion] = useState('');
  const [content, setContent] = useState('');

  const effective = useMemo(
    () => computeEffectiveModules(seatType?.module_refs ?? [], overlays ?? emptyOverlays()),
    [seatType, overlays]
  );

  const scopeOps = overlays ? overlays[scope].ops : [];
  const canAdd =
    !!slug.trim() && (opKind !== 'override' || !!content.trim()) && (opKind !== 'pin' || !!version.trim());

  const handleAddOp = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!canAdd) {
      return;
    }
    const op: SeatOverlayOp = {
      kind: opKind,
      slug: slug.trim(),
      version: opKind === 'add' || opKind === 'pin' ? version.trim() : '',
      content: opKind === 'override' ? content : '',
    };
    await updateOverlay.mutateAsync({ scope, ops: [...scopeOps, op] });
    setSlug('');
    setVersion('');
    setContent('');
  };

  const handleDeleteOp = async (index: number) => {
    await updateOverlay.mutateAsync({ scope, ops: scopeOps.filter((_, i) => i !== index) });
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Effective modules</CardTitle>
          <CardDescription>
            Seat type {seatType ? `${seatType.name} (${seatType.slug})` : 'unknown'} with the company,
            room and seat overlays applied. Changed modules are tagged with the overlay that touched them.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {isLoading && <Loading label="Loading overlays..." />}
          {error && <QueryError message={error.message} onRetry={() => refetch()} />}
          {!isLoading && !error && effective.length === 0 && (
            <p className="text-sm text-muted-foreground">This seat type has no modules.</p>
          )}
          {!isLoading &&
            !error &&
            effective.map(module => <ModuleRow key={module.slug} module={module} />)}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Edit an overlay</CardTitle>
          <CardDescription>
            Ops are applied in order and saved as the full ordered list for one scope. Read the current
            ops first, append or delete one, then save.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="space-y-1">
              <label className="text-sm font-medium" htmlFor="overlay-scope">
                Overlay scope
              </label>
              <Select
                id="overlay-scope"
                aria-label="Overlay scope"
                value={scope}
                onChange={e => setScope(e.target.value as SeatOverlayScope)}
              >
                {SCOPES.map(value => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <h4 className="text-sm font-medium">
              Current {scope} ops ({scopeOps.length})
            </h4>
            {scopeOps.length === 0 && (
              <p className="text-sm text-muted-foreground">No {scope} overlay ops yet.</p>
            )}
            {scopeOps.map((op, index) => (
              <div
                key={`${op.kind}-${op.slug}-${index}`}
                className="flex items-center justify-between gap-2 rounded border p-2 text-sm"
              >
                <span className="flex items-center gap-2 flex-wrap">
                  <Badge variant="secondary">{op.kind}</Badge>
                  <span className="font-mono">{op.slug}</span>
                  {op.version && <span className="text-muted-foreground">@{op.version}</span>}
                  {op.content && (
                    <span className="text-muted-foreground truncate max-w-xs">{op.content}</span>
                  )}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label={`Delete op ${index + 1}`}
                  disabled={updateOverlay.isPending}
                  onClick={() => handleDeleteOp(index)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>

          <Separator />

          <form className="space-y-3" onSubmit={handleAddOp}>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="space-y-1">
                <label className="text-sm font-medium" htmlFor="op-kind">
                  Op kind
                </label>
                <Select
                  id="op-kind"
                  aria-label="Op kind"
                  value={opKind}
                  onChange={e => setOpKind(e.target.value as SeatOverlayOpKind)}
                >
                  {OP_KINDS.map(kind => (
                    <option key={kind} value={kind}>
                      {kind}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium" htmlFor="op-slug">
                  Module slug
                </label>
                <Input
                  id="op-slug"
                  aria-label="Module slug"
                  value={slug}
                  onChange={e => setSlug(e.target.value)}
                  placeholder="rules"
                />
              </div>
              {(opKind === 'add' || opKind === 'pin') && (
                <div className="space-y-1">
                  <label className="text-sm font-medium" htmlFor="op-version">
                    Version
                  </label>
                  <Input
                    id="op-version"
                    aria-label="Version"
                    value={version}
                    onChange={e => setVersion(e.target.value)}
                    placeholder="1.2.0"
                  />
                </div>
              )}
            </div>
            {opKind === 'override' && (
              <div className="space-y-1">
                <label className="text-sm font-medium" htmlFor="op-content">
                  Content
                </label>
                <Textarea
                  id="op-content"
                  aria-label="Content"
                  value={content}
                  onChange={e => setContent(e.target.value)}
                  placeholder="Replacement module content"
                />
              </div>
            )}
            {updateOverlay.isError && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{updateOverlay.error.message}</AlertDescription>
              </Alert>
            )}
            <Button type="submit" disabled={!canAdd || updateOverlay.isPending}>
              {updateOverlay.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              Add op
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

const emptyOverlays = (): SeatOverlays => ({
  company: { scope: 'company', ops: [] },
  room: { scope: 'room', ops: [] },
  seat: { scope: 'seat', ops: [] },
});

// ---------------------------------------------------------------------------
// Links
// ---------------------------------------------------------------------------

const LinksTab: React.FC<SeatLinksTabProps> = ({ roomSeats }) => {
  const { room = '', seat = '' } = useParams<{ room: string; seat: string }>();
  const { links, isLoading, error, refetch } = useSeatLinks(room, seat);
  const upsertLink = useUpsertSeatLink(room, seat);

  const [target, setTarget] = useState('');
  const [kind, setKind] = useState<SeatLinkKind>('delegates_to');
  const [allow, setAllow] = useState(true);

  const others = roomSeats.filter(candidate => candidate.seat_key !== seat);
  const seatKeyById = useMemo(() => {
    const map = new Map<string, string>();
    roomSeats.forEach(candidate => map.set(candidate.id, candidate.seat_key));
    return map;
  }, [roomSeats]);

  const handleAddLink = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!target) {
      return;
    }
    await upsertLink.mutateAsync({ to_seat: target, kind, allow });
    setTarget('');
    setAllow(true);
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Outgoing links</CardTitle>
          <CardDescription>
            Links cannot be deleted through the API. Turn Allow off to block a link instead; an allowed
            link is a normal edge and a blocked one is an explicit deny.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoading && <Loading label="Loading links..." />}
          {error && <QueryError message={error.message} onRetry={() => refetch()} />}
          {!isLoading && !error && links.length === 0 && (
            <p className="text-sm text-muted-foreground">This seat has no outgoing links yet.</p>
          )}
          {!isLoading &&
            !error &&
            links.map(link => {
              const targetKey = seatKeyById.get(link.to_seat_id) ?? link.to_seat_id;
              return (
                <div
                  key={link.id}
                  className="flex items-center justify-between gap-2 rounded border p-2 text-sm"
                >
                  <span className="flex items-center gap-2">
                    <Link2 className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">{targetKey}</span>
                    <Badge variant="secondary">{link.kind}</Badge>
                  </span>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <Checkbox
                      aria-label={`Allow ${targetKey} (${link.kind})`}
                      checked={link.allow}
                      disabled={upsertLink.isPending}
                      onCheckedChange={checked =>
                        upsertLink.mutate({ to_seat: targetKey, kind: link.kind, allow: checked })
                      }
                    />
                    <span className="text-muted-foreground">Allow</span>
                  </label>
                </div>
              );
            })}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Add or replace a link</CardTitle>
          <CardDescription>
            Saving replaces the link to that seat and kind, or creates it when it does not exist.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Task messages are allowed by delegates_to; escalations and reports by escalates_to;
            questions and notices by collaborates_with. can_observe and spawned_by never allow
            sending.
          </p>
          <ul className="space-y-1 text-xs text-muted-foreground">
            {SEAT_LINK_KINDS.map(({ kind: optionKind, label, hint }) => (
              <li key={optionKind}>
                <span className="font-medium text-foreground">{label}</span> ({optionKind}) — {hint}
              </li>
            ))}
          </ul>
          <form className="flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={handleAddLink}>
            <div className="space-y-1">
              <label className="text-sm font-medium" htmlFor="link-target">
                Link target
              </label>
              <Select
                id="link-target"
                aria-label="Link target"
                value={target}
                onChange={e => setTarget(e.target.value)}
              >
                <option value="">Select a seat</option>
                {others.map(candidate => (
                  <option key={candidate.id} value={candidate.seat_key}>
                    {candidate.seat_key}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium" htmlFor="link-kind">
                Link kind
              </label>
              <Select
                id="link-kind"
                aria-label="Link kind"
                value={kind}
                onChange={e => setKind(e.target.value as SeatLinkKind)}
              >
                {SEAT_LINK_KINDS.map(({ kind: optionKind, label }) => (
                  <option key={optionKind} value={optionKind}>
                    {label} ({optionKind})
                  </option>
                ))}
              </Select>
            </div>
            <label className="flex items-center gap-2 text-sm cursor-pointer sm:pb-2">
              <Checkbox
                aria-label="Allow link"
                checked={allow}
                onCheckedChange={checked => setAllow(checked)}
              />
              Allow
            </label>
            <Button type="submit" disabled={!target || upsertLink.isPending}>
              {upsertLink.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              Add link
            </Button>
          </form>
          {upsertLink.isError && (
            <Alert variant="destructive" className="mt-3">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{upsertLink.error.message}</AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Preview
// ---------------------------------------------------------------------------

const PreviewTab: React.FC = () => {
  const { room = '', seat = '' } = useParams<{ room: string; seat: string }>();
  const { resolvedSeat, isLoading, error, refetch } = useResolvedSeat(room, seat);
  const [fileIndex, setFileIndex] = useState(0);
  const [copied, setCopied] = useState(false);

  const files = resolvedSeat?.files ?? [];
  const activeFile = files[fileIndex];
  const command = `scripts/openrig_seat_sync.py pull ${room} ${seat}`;

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
          {isLoading && <Loading label="Loading snapshot..." />}
          {error && <QueryError message={error.message} onRetry={() => refetch()} />}
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

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export const SeatDetailPage: React.FC = () => {
  const { room = '', seat = '' } = useParams<{ room: string; seat: string }>();
  const navigate = useNavigate();
  const { seats, isLoading, error, refetch } = useSeats(room);
  const { seatTypes } = useSeatTypes();

  const currentSeat = seats.find(candidate => candidate.seat_key === seat);
  const seatType = currentSeat
    ? seatTypes.find(type => type.slug === currentSeat.seat_type)
    : undefined;

  return (
    <div className="container mx-auto space-y-6 p-6">
      <div className="flex items-center gap-3">
        <Button variant="outline" size="sm" onClick={() => navigate('/seats')}>
          <ArrowLeft className="h-4 w-4" /> Back to seats
        </Button>
      </div>

      <div>
        <h1 className="text-4xl font-bold tracking-tight">{seat}</h1>
        <p className="text-muted-foreground mt-2">
          Room {room}
          {currentSeat && ` · ${currentSeat.seat_type}`}
          {currentSeat && ` · ${currentSeat.pinned_version ? `pinned ${currentSeat.pinned_version}` : 'follows latest'}`}
          {currentSeat && ` · ${currentSeat.runtime} / ${currentSeat.model || 'default model'}`}
        </p>
      </div>

      {isLoading && <Loading label="Loading seat..." />}
      {error && <QueryError message={error.message} onRetry={() => refetch()} />}
      {!isLoading && !error && !currentSeat && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>Seat "{seat}" was not found in room "{room}".</AlertDescription>
        </Alert>
      )}

      {currentSeat && (
        <Tabs defaultValue="modules">
          <TabsList>
            <TabsTrigger value="modules">
              <Package className="mr-1 h-4 w-4" /> Modules
            </TabsTrigger>
            <TabsTrigger value="links">
              <Link2 className="mr-1 h-4 w-4" /> Links
            </TabsTrigger>
            <TabsTrigger value="preview">
              <FileCode className="mr-1 h-4 w-4" /> Preview
            </TabsTrigger>
            <TabsTrigger value="llm">
              <Brain className="mr-1 h-4 w-4" /> LLM
            </TabsTrigger>
          </TabsList>

          <TabsContent value="modules">
            <ModulesTab seatType={seatType} />
          </TabsContent>
          <TabsContent value="links">
            <LinksTab roomSeats={seats} />
          </TabsContent>
          <TabsContent value="preview">
            <PreviewTab />
          </TabsContent>
          <TabsContent value="llm">
            <SeatLlmPanel room={room} seat={currentSeat} />
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
};
