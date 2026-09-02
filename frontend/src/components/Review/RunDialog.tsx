/**
 * RunDialog — the draft, the moment it exists.
 *
 * Running an extraction used to leave the rows in a panel below the note list
 * and a link to another page; the thing you had just asked for was somewhere
 * you had to go and find. It arrives here instead — reviewable, correctable and
 * exportable without leaving the extractor — and it is already saved on the
 * server, so closing it loses nothing.
 *
 * The header says "draft", not "done". That is the point of the whole flow: the
 * model has answered, and nothing has been reviewed yet.
 */

import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Link } from 'react-router-dom';
import { ClipboardCheck, Clock3, Database, FileUp, X } from 'lucide-react';
import type { RunDetail, RunRow } from '../../types';
import { runProgress } from '../../lib/runProgress';
import { formatRunTime } from '../../lib/time';
import ReviewTable from './ReviewTable';
import SignOffPanel from './SignOffPanel';
import ExportButtons from './ExportButtons';
import { RunStatusChip } from './StatusChip';

interface Props {
  run: RunDetail;
  onRunChange: (run: RunDetail) => void;
  onClose: () => void;
  canReview: boolean;
}

const FOCUSABLE =
  'a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])';

/** Blur a cell editor inside the dialog, committing it. True if there was one. */
function commitPendingEdit(panel: HTMLElement | null): boolean {
  const active = document.activeElement;
  if (!(active instanceof HTMLInputElement) || !panel?.contains(active)) return false;
  active.blur();
  return true;
}

export default function RunDialog({ run, onRunChange, onClose, canReview }: Props) {
  const panelRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const progress = runProgress(run);

  // Focus moves into the dialog and comes back to whatever opened it — the run
  // button, usually — so a keyboard user is not dropped at the top of the page.
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    return () => opener?.focus?.();
  }, []);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        // Escape leaves the cell being edited, not the dialog. Closing the
        // whole table because a correction was half-typed would be a bad trade,
        // and the blur commits the edit as clicking away would.
        if (commitPendingEdit(panelRef.current)) return;
        onClose();
        return;
      }
      if (e.key !== 'Tab' || !panelRef.current) return;

      // Keep Tab inside the dialog; behind it sits a whole page of controls
      // that are, for now, not reachable.
      const items = Array.from(
        panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE),
      ).filter((el) => el.offsetParent !== null);
      const first = items[0];
      const last = items[items.length - 1];
      if (!first || !last) return;
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  const SourceIcon = run.source_kind === 'database' ? Database : FileUp;

  const handleRowChange = (row: RunRow) =>
    onRunChange({
      ...run,
      rows: run.rows.map((r) => (r.id === row.id ? row : r)),
    });

  return createPortal(
    <div
      className="dialog-scrim"
      onMouseDown={(e) => {
        // mousedown, not click: a click that started inside the table and ended
        // on the scrim (a drag-select over a cell) must not close it.
        if (e.target !== e.currentTarget) return;
        // Closing unmounts the cell editor, and an unmounted input never fires
        // the blur its edit is committed on, so commit it here first.
        commitPendingEdit(panelRef.current);
        onClose();
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="run-dialog-title"
        className="dialog-panel w-full max-w-6xl max-h-full"
      >
        <header className="dialog-header">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h2 id="run-dialog-title" className="text-title-lg text-on-surface">
                {progress.status === 'approved'
                  ? 'Reviewed and signed off'
                  : progress.status === 'rejected'
                    ? 'Rejected'
                    : 'Extracted — ready for review'}
              </h2>
              <RunStatusChip status={progress.status} />
            </div>
            <p className="text-label-md text-on-surface-variant tabular mt-0.5 flex flex-wrap items-center gap-x-1.5">
              <span>
                {run.rows.length} row{run.rows.length === 1 ? '' : 's'}
              </span>
              <span className="text-outline">·</span>
              <span className="inline-flex items-center gap-1 min-w-0">
                <SourceIcon size={12} className="shrink-0" />
                <span className="truncate max-w-[22rem]">
                  {run.note_count} {run.source_kind === 'database' ? 'note' : 'file'}
                  {run.note_count === 1 ? '' : 's'} · {run.source_label}
                </span>
              </span>
              <span className="text-outline">·</span>
              <span className="inline-flex items-center gap-1">
                <Clock3 size={12} />
                {formatRunTime(run.created_at)}
              </span>
              {run.models_used && (
                <>
                  <span className="text-outline">·</span>
                  <span className="truncate max-w-[16rem]">{run.models_used}</span>
                </>
              )}
            </p>
          </div>
          <button
            ref={closeRef}
            onClick={onClose}
            className="btn-icon shrink-0"
            aria-label="Close results"
          >
            <X size={16} />
          </button>
        </header>

        <div className="p-4 space-y-3 overflow-y-auto">
          <SignOffPanel run={run} onRunChange={onRunChange} canReview={canReview} />

          {run.provenance_columns.length > 0 && (
            <p className="text-label-md text-on-surface-variant">
              Every row carries the note it came from. Those columns cannot be edited —
              one note can produce several rows, so the link back to the source is a
              record of fact rather than a value to correct.
              {run.source_kind === 'upload' && (
                <>
                  {' '}
                  This run came from an uploaded file, so its provenance is a filename:
                  there is no source system to read the original back from.
                </>
              )}
            </p>
          )}

          <ReviewTable
            run={run}
            onRowChange={handleRowChange}
            canReview={canReview && progress.status !== 'approved'}
            maxHeight="max-h-[50vh]"
          />
        </div>

        <footer className="dialog-footer">
          <p className="text-label-md text-on-surface-variant">
            Saved on the server as run <span className="mono">{run.id.slice(0, 8)}</span> —
            corrections and decisions included.
          </p>
          <div className="flex items-center gap-2">
            <ExportButtons run={run} />
            <Link to={`/review?run=${run.id}`} className="btn-outlined" onClick={onClose}>
              <ClipboardCheck size={14} />
              Full review
            </Link>
            <button onClick={onClose} className="btn-filled">
              Done
            </button>
          </div>
        </footer>
      </div>
    </div>,
    document.body,
  );
}
