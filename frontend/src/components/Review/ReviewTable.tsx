/**
 * ReviewTable — the surface a clinician actually works on.
 *
 * Three things it has to make visible at a glance, because they are what the
 * whole workflow rests on:
 *
 *   1. Which values a person changed, and what the model had said. A corrected
 *      cell is tinted and carries the original in its tooltip, one click from
 *      being put back — a correction that cannot be inspected is indistinguish-
 *      able from a mistake.
 *   2. Where each row stands. Pending is not "fine", it is "nobody has looked".
 *   3. That provenance is not editable. Which note a row came from is a record
 *      of fact; one note can produce several rows, so it is not a value to fix.
 *
 * Edits go straight to the server. There is no local buffer to lose, and no
 * save button whose absence people have to notice.
 */

import { useState } from 'react';
import toast from 'react-hot-toast';
import { Check, Undo2, X } from 'lucide-react';
import type { RowStatus, RunDetail, RunRow } from '../../types';
import { decideRow, editRow, revertRow } from '../../api/runs';
import { errorMessage } from '../../api/errors';
import EditableCell from '../DataTable/EditableCell';
import { RowStatusChip } from './StatusChip';

interface Props {
  run: RunDetail;
  /** Called with the row the server returned, so the parent stays in step. */
  onRowChange: (row: RunRow) => void;
  /** False when the run is signed off, or the viewer's role cannot review. */
  canReview: boolean;
  maxHeight?: string;
}

function display(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  if (Array.isArray(value)) return value.join(', ');
  // Matching EditableCell: a locked row rendered "false" where an editable one
  // showed ✗, so signing a run off appeared to change its values.
  if (typeof value === 'boolean') return value ? '✓' : '✗';
  return String(value);
}

export default function ReviewTable({
  run,
  onRowChange,
  canReview,
  maxHeight = 'max-h-[32rem]',
}: Props) {
  const provenance = new Set(run.provenance_columns);
  // Rows mid-request, so a second click cannot race the first.
  const [busy, setBusy] = useState<Set<string>>(new Set());

  const withBusy = async (rowId: string, action: () => Promise<RunRow>) => {
    if (busy.has(rowId)) return;
    setBusy((prev) => new Set(prev).add(rowId));
    try {
      onRowChange(await action());
    } catch (err) {
      toast.error(errorMessage(err, 'That change could not be saved'));
    } finally {
      setBusy((prev) => {
        const next = new Set(prev);
        next.delete(rowId);
        return next;
      });
    }
  };

  const handleEdit = (row: RunRow, column: string, value: unknown) =>
    withBusy(row.id, () => editRow(run.id, row.id, { [column]: value }));

  const handleRevert = (row: RunRow, column: string) =>
    withBusy(row.id, () => revertRow(run.id, row.id, column));

  const handleDecide = (row: RunRow, status: RowStatus) =>
    withBusy(row.id, () => decideRow(run.id, row.id, status));

  if (run.rows.length === 0) {
    return (
      <div className="card px-6 py-12 text-center">
        <p className="text-body-md text-on-surface-variant">
          This extraction produced no rows — the model found nothing matching the
          schema in the text it was given.
        </p>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      <div className={`overflow-auto ${maxHeight}`}>
        <table className="w-full border-collapse">
          <thead className="sticky top-0 z-10">
            <tr className="bg-surface-dim">
              <th className="text-left px-3 py-2 border-b border-outline w-10">
                <span className="text-on-surface-variant/70">#</span>
              </th>
              <th className="text-left px-3 py-2 border-b border-outline w-24">
                <span className="text-label-sm text-on-surface-variant/80">Review</span>
              </th>
              {run.columns.map((col) => (
                <th
                  key={col.name}
                  className="text-left px-3 py-2 border-b border-outline font-normal"
                >
                  <span className="flex items-baseline gap-1.5 whitespace-nowrap">
                    <span className="text-title-sm text-on-surface">{col.name}</span>
                    <span className="text-label-sm text-on-surface-variant/70 normal-case">
                      {provenance.has(col.name) ? 'source' : col.data_type}
                    </span>
                  </span>
                </th>
              ))}
              {canReview && (
                // Pinned: a wide schema pushes this off the right edge, and the
                // one control the whole page exists for must not be the thing
                // you have to scroll sideways to find.
                <th
                  className="text-right px-3 py-2 border-b border-l border-outline w-24
                             sticky right-0 z-20 bg-surface-dim"
                >
                  <span className="text-label-sm text-on-surface-variant/80">Decide</span>
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {run.rows.map((row, index) => {
              const locked = !canReview || row.status === 'approved';
              // The pinned cell needs its own opaque background, and it has to
              // track the row's — a transparent sticky cell shows the text it
              // is scrolling over.
              const rowBackground =
                row.status === 'rejected'
                  ? 'bg-gm-red-light'
                  : 'bg-surface group-hover:bg-surface-dim';
              return (
                <tr
                  key={row.id}
                  className={`group border-b border-outline-variant last:border-0
                              transition-colors duration-100 ${
                                row.status === 'rejected'
                                  ? 'bg-gm-red-light/40'
                                  : 'hover:bg-surface-dim'
                              } ${busy.has(row.id) ? 'opacity-60' : ''}`}
                >
                  <td className="px-3 py-1.5 align-top">
                    <span className="text-label-md text-on-surface-variant tabular">
                      {index + 1}
                    </span>
                  </td>
                  <td className="px-3 py-1.5 align-top">
                    <RowStatusChip status={row.status} />
                    {row.decided_by && (
                      <span
                        className="block text-label-sm text-on-surface-variant/70 truncate mt-0.5"
                        title={`${row.decided_by}${row.review_note ? ` — ${row.review_note}` : ''}`}
                      >
                        {row.decided_by}
                      </span>
                    )}
                  </td>

                  {run.columns.map((col) => {
                    const isProvenance = provenance.has(col.name);
                    const corrected = row.corrected_columns.includes(col.name);
                    return (
                      <td
                        key={col.name}
                        className={`px-3 py-1.5 align-top group/cell ${
                          corrected ? 'bg-gm-yellow-light' : ''
                        }`}
                      >
                        {isProvenance ? (
                          <span className="mono text-on-surface-variant whitespace-nowrap">
                            {display(row.data[col.name])}
                          </span>
                        ) : locked ? (
                          <span className="text-body-md text-on-surface">
                            {display(row.data[col.name])}
                          </span>
                        ) : (
                          <span className="flex items-start gap-1">
                            <EditableCell
                              value={row.data[col.name]}
                              dataType={col.data_type}
                              onChange={(value) => void handleEdit(row, col.name, value)}
                            />
                            {corrected && (
                              <button
                                onClick={() => void handleRevert(row, col.name)}
                                className="btn-icon w-5 h-5 shrink-0 opacity-0
                                           group-hover/cell:opacity-100 focus-visible:opacity-100
                                           transition-opacity"
                                title={`Model said: ${display(row.ai_data[col.name])}`}
                                aria-label={`Revert ${col.name} to the model's answer`}
                              >
                                <Undo2 size={11} />
                              </button>
                            )}
                          </span>
                        )}
                        {corrected && (
                          <span
                            className="block text-label-sm text-gm-yellow truncate max-w-[16rem]"
                            title={display(row.ai_data[col.name])}
                          >
                            was: {display(row.ai_data[col.name])}
                          </span>
                        )}
                      </td>
                    );
                  })}

                  {canReview && (
                    <td
                      className={`px-3 py-1.5 align-top sticky right-0 z-10 border-l
                                  border-outline-variant ${rowBackground}`}
                    >
                      <div className="flex items-center justify-end gap-1">
                        {row.status === 'pending' ? (
                          <>
                            <button
                              onClick={() => void handleDecide(row, 'approved')}
                              className="btn-icon w-7 h-7 hover:text-gm-green"
                              aria-label="Approve this row"
                              title="Approve this row"
                            >
                              <Check size={14} />
                            </button>
                            <button
                              onClick={() => void handleDecide(row, 'rejected')}
                              className="btn-icon w-7 h-7 hover:text-gm-red"
                              aria-label="Reject this row"
                              title="Reject this row — the model got it wrong"
                            >
                              <X size={14} />
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => void handleDecide(row, 'pending')}
                            className="btn-icon w-7 h-7"
                            aria-label="Reopen this row"
                            title="Reopen this row for correction"
                          >
                            <Undo2 size={13} />
                          </button>
                        )}
                      </div>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="px-3 py-2 border-t border-outline bg-surface-dim flex flex-wrap items-center gap-x-2">
        <span className="text-label-md text-on-surface-variant tabular">
          {run.rows.length} row{run.rows.length === 1 ? '' : 's'}
        </span>
        <span className="text-label-md text-on-surface-variant/80">
          {canReview
            ? '· click a cell to correct it — corrections are saved as you make them, with the model’s answer kept beside them'
            : '· read-only'}
        </span>
      </div>
    </div>
  );
}
