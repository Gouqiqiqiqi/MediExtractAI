/**
 * Review — every extraction this deployment has run, and what has been done
 * with it.
 *
 * This replaces a "Results" page that showed one table: the most recent run,
 * held in the browser, with nothing to say when it ran, who ran it, or whether
 * anyone had checked it. That is a demo's idea of results. A run is a piece of
 * clinical work — it gets a history, a reviewer, a decision on every row, and a
 * signature before its rows are allowed to leave as anything but a draft.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  ClipboardCheck,
  Clock3,
  Database,
  FileUp,
  Pencil,
  Trash2,
  User,
} from 'lucide-react';
import type { RunDetail, RunRow, RunSummary } from '../types';
import { deleteRun, fetchRun, fetchRuns } from '../api/runs';
import { errorMessage } from '../api/errors';
import { useRole } from '../auth/RoleContext';
import EmptyState from '../components/common/EmptyState';
import { SkeletonRows } from '../components/common/Skeleton';
import ReviewTable from '../components/Review/ReviewTable';
import SignOffPanel from '../components/Review/SignOffPanel';
import ExportButtons from '../components/Review/ExportButtons';
import { RunStatusChip } from '../components/Review/StatusChip';
import { runProgress } from '../lib/runProgress';
import { runsChanged } from '../lib/runEvents';
import { formatRunTime, relativeTime } from '../lib/time';

type Filter = 'all' | 'awaiting_review' | 'approved';

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'awaiting_review', label: 'Awaiting review' },
  { key: 'approved', label: 'Signed off' },
  { key: 'all', label: 'All' },
];

export default function Review() {
  const { canExtract } = useRole();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedId = searchParams.get('run');

  const [filter, setFilter] = useState<Filter>('all');
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(requestedId);
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // ── The list ──
  const loadRuns = useCallback(async (which: Filter) => {
    try {
      const { items } = await fetchRuns({
        status: which === 'all' ? undefined : which,
      });
      return items;
    } catch (err) {
      toast.error(errorMessage(err, 'Could not load the extraction history'));
      return [];
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    setRuns(null);
    void loadRuns(filter).then((items) => {
      if (cancelled) return;
      setRuns(items);
      // Keep whatever is open if it survived the filter; otherwise open the
      // newest, so the panel is never blank next to a populated list.
      setSelectedId((current) => {
        if (current && items.some((r) => r.id === current)) return current;
        return items[0]?.id ?? null;
      });
    });
    return () => {
      cancelled = true;
    };
  }, [filter, loadRuns]);

  // ── The open run ──
  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setLoadingDetail(true);
    fetchRun(selectedId)
      .then((d) => !cancelled && setDetail(d))
      .catch((err) => {
        if (cancelled) return;
        setDetail(null);
        toast.error(errorMessage(err, 'Could not open that run'));
      })
      .finally(() => !cancelled && setLoadingDetail(false));
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  const select = (id: string) => {
    setSelectedId(id);
    setSearchParams({ run: id }, { replace: true });
  };

  // A change inside the run also changes its line in the list — the counts
  // there are the reason anyone picks one run over another.
  const applyDetail = (updated: RunDetail) => {
    setDetail(updated);
    const progress = runProgress(updated);
    setRuns(
      (prev) =>
        prev?.map((r) =>
          r.id === updated.id
            ? {
                ...r,
                status: progress.status,
                pending_rows: progress.pending,
                approved_rows: progress.approved,
                rejected_rows: progress.rejected,
                corrected_rows: progress.corrected,
                approved_by: updated.approved_by,
                approved_at: updated.approved_at,
              }
            : r,
        ) ?? null,
    );
  };

  const handleRowChange = (row: RunRow) => {
    if (!detail) return;
    applyDetail({
      ...detail,
      rows: detail.rows.map((r) => (r.id === row.id ? row : r)),
    });
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteRun(id);
      const remaining = (runs ?? []).filter((r) => r.id !== id);
      setRuns(remaining);
      if (id === selectedId) {
        const next = remaining[0]?.id ?? null;
        setSelectedId(next);
        setSearchParams(next ? { run: next } : {}, { replace: true });
      }
      runsChanged();
      toast.success('Draft discarded');
    } catch (err) {
      toast.error(errorMessage(err, 'That run could not be discarded'));
    }
  };

  const progress = useMemo(() => (detail ? runProgress(detail) : null), [detail]);

  return (
    <div className="max-w-7xl mx-auto space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-title">Review</h1>
          <p className="page-subtitle">
            Every extraction is saved as a draft. Correct what the model got wrong, then
            sign it off — only then does it leave as reviewed data.
          </p>
        </div>
        <div className="flex gap-1 p-0.5 rounded-gm-md bg-surface-container">
          {FILTERS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`px-2.5 py-1 rounded-gm-sm text-label-lg transition-colors duration-150 ${
                filter === key
                  ? 'bg-surface text-on-surface shadow-gm-1'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {runs === null ? (
        <div className="card p-4">
          <SkeletonRows rows={5} />
        </div>
      ) : runs.length === 0 ? (
        <div className="card">
          <EmptyState
            icon={ClipboardCheck}
            title={filter === 'all' ? 'Nothing extracted yet' : 'Nothing here'}
            description={
              filter === 'all'
                ? 'Run an extraction — the rows appear the moment it finishes, and every run is kept here for review.'
                : 'No run is in this state right now.'
            }
            action={
              filter === 'all' && canExtract ? (
                <Link to="/database" className="btn-filled">
                  <Database size={14} />
                  Go to Database Extractor
                </Link>
              ) : undefined
            }
          />
        </div>
      ) : (
        <div className="flex items-start gap-4">
          {/* ── The history ── */}
          <nav
            className="card w-72 shrink-0 overflow-hidden divide-y divide-outline-variant"
            aria-label="Extraction history"
          >
            {runs.map((run) => {
              const Icon = run.source_kind === 'database' ? Database : FileUp;
              const isSelected = run.id === selectedId;
              const canDiscard = run.status !== 'approved' && canExtract;
              return (
                <div key={run.id} className="group relative">
                  <button
                    onClick={() => select(run.id)}
                    aria-current={isSelected}
                    className={`w-full text-left px-3 py-2.5 pr-8 transition-colors duration-150 ${
                      isSelected ? 'bg-gm-blue-light' : 'hover:bg-surface-dim'
                    }`}
                  >
                    <span className="flex items-center gap-1.5">
                      <Icon
                        size={13}
                        className={`shrink-0 ${
                          isSelected ? 'text-gm-blue' : 'text-on-surface-variant'
                        }`}
                      />
                      <span
                        className={`text-title-sm tabular ${
                          isSelected ? 'text-gm-blue' : 'text-on-surface'
                        }`}
                      >
                        {formatRunTime(run.created_at)}
                      </span>
                      <span className="ml-auto">
                        <RunStatusChip status={run.status} />
                      </span>
                    </span>
                    <span
                      className="block text-label-md text-on-surface-variant truncate mt-0.5"
                      title={run.source_label}
                    >
                      {run.source_label}
                    </span>
                    <span className="block text-label-md text-on-surface-variant/80 tabular truncate">
                      {run.row_count} row{run.row_count === 1 ? '' : 's'}
                      {run.pending_rows > 0 && (
                        <span className="text-gm-yellow"> · {run.pending_rows} pending</span>
                      )}
                      {run.corrected_rows > 0 && ` · ${run.corrected_rows} corrected`}
                    </span>
                  </button>
                  {canDiscard && (
                    <button
                      onClick={() => void handleDelete(run.id)}
                      className="btn-icon w-6 h-6 absolute bottom-2 right-1.5 hover:text-gm-red
                                 opacity-0 group-hover:opacity-100 focus-visible:opacity-100
                                 transition-opacity"
                      aria-label={`Discard the draft from ${formatRunTime(run.created_at)}`}
                    >
                      <Trash2 size={12} />
                    </button>
                  )}
                </div>
              );
            })}
          </nav>

          {/* ── The open run ── */}
          <div className="flex-1 min-w-0 space-y-3">
            {loadingDetail && !detail ? (
              <div className="card p-4">
                <SkeletonRows rows={6} />
              </div>
            ) : !detail || !progress ? (
              <div className="card">
                <EmptyState
                  icon={ClipboardCheck}
                  title="Choose a run"
                  description="Pick an extraction on the left to review it."
                  compact
                />
              </div>
            ) : (
              <>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="text-headline-md text-on-surface truncate">
                      {detail.source_label}
                    </h2>
                    <p className="text-label-md text-on-surface-variant tabular mt-0.5 flex flex-wrap items-center gap-x-1.5">
                      <span>
                        {detail.source_kind === 'database'
                          ? 'Database extraction'
                          : 'File extraction'}
                      </span>
                      <span className="text-outline">·</span>
                      <span>
                        {detail.note_count}{' '}
                        {detail.source_kind === 'database' ? 'note' : 'file'}
                        {detail.note_count === 1 ? '' : 's'} → {detail.row_count} row
                        {detail.row_count === 1 ? '' : 's'}
                      </span>
                      <span className="text-outline">·</span>
                      <span className="inline-flex items-center gap-1">
                        <User size={11} />
                        {detail.created_by}
                      </span>
                      <span className="text-outline">·</span>
                      <span className="inline-flex items-center gap-1">
                        <Clock3 size={11} />
                        {relativeTime(detail.created_at)}
                      </span>
                      {detail.models_used && (
                        <>
                          <span className="text-outline">·</span>
                          <span className="truncate max-w-[18rem]">{detail.models_used}</span>
                        </>
                      )}
                      {progress.corrected > 0 && (
                        <>
                          <span className="text-outline">·</span>
                          <span className="inline-flex items-center gap-1 text-gm-yellow">
                            <Pencil size={11} />
                            {progress.corrected} corrected
                          </span>
                        </>
                      )}
                    </p>
                  </div>
                  <ExportButtons run={detail} />
                </div>

                <SignOffPanel
                  run={detail}
                  onRunChange={applyDetail}
                  canReview={canExtract}
                />

                {detail.provenance_columns.length > 0 && (
                  <p className="text-label-md text-on-surface-variant">
                    Every row carries the note it came from. Those columns cannot be
                    edited — one note can produce several rows, so the link back to the
                    source is a record of fact rather than a value to correct.
                    {detail.source_kind === 'upload' && (
                      <>
                        {' '}
                        This run came from an uploaded file, so its provenance is a
                        filename: there is no source system to read the original back
                        from.
                      </>
                    )}
                  </p>
                )}

                <ReviewTable
                  run={detail}
                  onRowChange={handleRowChange}
                  canReview={canExtract && progress.status !== 'approved'}
                  maxHeight="max-h-[36rem]"
                />
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
