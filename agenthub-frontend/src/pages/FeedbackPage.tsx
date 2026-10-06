/**
 * Seat Friction Page - the read side of the friction channel (Directive H).
 *
 * ENTRIES ARE GROUPED BY LAYER, and the grouping IS the page rather than a filter over a
 * flat list. The backend sends the groups already in canonical order and omits a layer it
 * has no reports for; the page renders ALL SIX headings anyway, in that order, and a layer
 * with no group gets its own empty state. The distinction is the point: a heading that
 * disappeared would read as "this layer was not considered", while "nothing reported for
 * this layer" is the truth.
 *
 * IT IS A VIEWER AND NOTHING MORE: it reads one table and shows it. There is no moderation,
 * no status transition and no escalate affordance, because the backend has none - the only
 * control here is Refresh, which re-runs the same GET.
 *
 * @module pages/FeedbackPage
 * @version 1.0.0
 */

import React from 'react';
import { RefreshCw } from 'lucide-react';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { useFeedback } from '../hooks/useFeedback';
import { cn } from '../lib/utils';
import {
  FEEDBACK_LAYERS,
  FEEDBACK_LAYER_MEANING,
  type FeedbackLayer,
  type FeedbackReport,
} from '../types/feedback';

/** The layer as a heading reads it; the wire value keeps its hyphen and is shown beside it. */
const LAYER_LABEL: Record<FeedbackLayer, string> = {
  runtime: 'Runtime',
  openrig: 'OpenRig',
  cloud: 'Cloud',
  'seat-context': 'Seat context',
  workspace: 'Workspace',
  other: 'Other',
};

const isKnownLayer = (value: string): value is FeedbackLayer =>
  (FEEDBACK_LAYERS as readonly string[]).includes(value);

/** One report, rendered from the row's own fields and nothing else. */
const ReportRow: React.FC<{ report: FeedbackReport }> = ({ report }) => {
  const context = report.room && report.seat ? `${report.room}/${report.seat}` : report.room || report.seat;
  return (
    <li className="border-t border-surface-border-hover px-3 py-3 first:border-t-0">
      <div className="flex flex-wrap items-baseline gap-2">
        <time dateTime={report.created_at} className="font-mono text-xs text-base-secondary">
          {report.created_at}
        </time>
        {context && <Badge variant="outline">{context}</Badge>}
        {report.session && (
          <span className="font-mono text-xs text-base-secondary">{report.session}</span>
        )}
        {report.machine_id && (
          <span className="font-mono text-xs text-base-secondary">{report.machine_id}</span>
        )}
      </div>
      <p className="mt-1 whitespace-pre-wrap text-sm text-base-primary">{report.text}</p>
    </li>
  );
};

export const FeedbackPage: React.FC = () => {
  const { groups, total, isLoading, error, refetch } = useFeedback();

  const groupByLayer = new Map(groups.map((group) => [group.layer as string, group]));
  const unlisted = groups.filter((group) => !isKnownLayer(group.layer));

  return (
    <div className="mx-auto w-full max-w-4xl p-4 md:p-6">
      <header className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-base-primary">Seat friction</h1>
          <p className="text-sm text-base-secondary">
            {total} {total === 1 ? 'entry' : 'entries'}, grouped by the layer it was reported against.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading}>
          <RefreshCw className={cn('mr-2 h-4 w-4', isLoading && 'animate-spin')} />
          Refresh
        </Button>
      </header>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>
            Could not load the friction entries:{' '}
            {error instanceof Error ? error.message : 'unknown error'}
          </AlertDescription>
        </Alert>
      )}

      {isLoading && total === 0 ? (
        <p className="py-10 text-center text-sm text-base-secondary">Loading friction entries…</p>
      ) : (
        <>
          {total === 0 && !error && (
            <p className="mb-4 rounded-md border border-surface-border-hover px-3 py-6 text-center text-sm text-base-secondary">
              No friction entries reported yet.
            </p>
          )}

          <div className="space-y-4">
            {FEEDBACK_LAYERS.map((layer) => {
              const group = groupByLayer.get(layer);
              const reports = group?.reports ?? [];
              const count = group?.count ?? 0;
              return (
                <section
                  key={layer}
                  aria-labelledby={`feedback-layer-${layer}`}
                  className="rounded-md border border-surface-border-hover"
                >
                  <div className="flex flex-wrap items-baseline gap-2 px-3 py-2">
                    <h2
                      id={`feedback-layer-${layer}`}
                      className="text-sm font-semibold text-base-primary"
                    >
                      {LAYER_LABEL[layer]}
                    </h2>
                    <span className="font-mono text-xs text-base-secondary">{layer}</span>
                    <Badge variant={count > 0 ? 'default' : 'secondary'}>{count}</Badge>
                    <p className="w-full text-xs text-base-secondary">{FEEDBACK_LAYER_MEANING[layer]}</p>
                  </div>
                  {reports.length === 0 ? (
                    <p className="border-t border-surface-border-hover px-3 py-3 text-sm text-base-secondary">
                      Nothing reported for this layer.
                    </p>
                  ) : (
                    <ul role="list">
                      {reports.map((report) => (
                        <ReportRow key={report.id} report={report} />
                      ))}
                    </ul>
                  )}
                </section>
              );
            })}
          </div>

          {unlisted.length > 0 && (
            <div className="mt-4 space-y-4">
              {unlisted.map((group) => (
                <section
                  key={group.layer}
                  aria-labelledby={`feedback-unlisted-${group.layer}`}
                  className="rounded-md border border-destructive/50"
                >
                  <div className="px-3 py-2">
                    <h2
                      id={`feedback-unlisted-${group.layer}`}
                      className="text-sm font-semibold text-base-primary"
                    >
                      Unrecognised layer: <span className="font-mono">{group.layer}</span>
                    </h2>
                    <p className="text-xs text-base-secondary">
                      The API grouped these under a layer outside the closed set, so they are shown as
                      sent rather than filed under another layer.
                    </p>
                  </div>
                  <ul role="list">
                    {group.reports.map((report) => (
                      <ReportRow key={report.id} report={report} />
                    ))}
                  </ul>
                </section>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
};
