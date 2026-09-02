/**
 * Review progress, derived from the rows on screen.
 *
 * The server sends these tallies with every run, but a detail view already
 * holds every row, and re-fetching the whole run after each approval to learn
 * that one counter moved would make reviewing feel like filling in a form that
 * saves on every keystroke. Deriving them keeps the numbers honest between
 * requests without asking for anything.
 */

import type { RunDetail, RunStatus } from '../types';

export interface RunProgress {
  pending: number;
  approved: number;
  rejected: number;
  corrected: number;
  total: number;
  /** Every row has a decision — the precondition for a clean sign-off. */
  allDecided: boolean;
  /**
   * What the run's status effectively is. A run leaves "draft" server-side the
   * moment someone edits or decides a row; the row endpoints return the row,
   * not the run, so the transition is reflected here rather than re-fetched.
   */
  status: RunStatus;
}

export function runProgress(run: RunDetail): RunProgress {
  const rows = run.rows;
  const pending = rows.filter((r) => r.status === 'pending').length;
  const approved = rows.filter((r) => r.status === 'approved').length;
  const rejected = rows.filter((r) => r.status === 'rejected').length;
  const corrected = rows.filter((r) => r.corrected_columns.length > 0).length;

  const touched = corrected > 0 || approved > 0 || rejected > 0;
  const status: RunStatus =
    run.status === 'draft' && touched ? 'in_review' : run.status;

  return {
    pending,
    approved,
    rejected,
    corrected,
    total: rows.length,
    allDecided: rows.length > 0 && pending === 0,
    status,
  };
}

/** Whether the run is open to correction at all. */
export function isOpen(status: RunStatus): boolean {
  return status === 'draft' || status === 'in_review';
}
