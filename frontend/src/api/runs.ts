/**
 * Runs API — the review lifecycle.
 *
 * Every extraction is a run on the server the moment the model answers, so
 * nothing here caches results in the browser: the rows a reviewer sees are the
 * rows that are stored, and a correction is a request, not a local edit that
 * might never be saved.
 */

import apiClient from './client';
import type {
  RowStatus,
  RunDetail,
  RunListResponse,
  RunRow,
  RunStats,
  RunStatus,
} from '../types';

/**
 * `awaiting_review` is not a stored status — the server reads it as "draft or
 * in_review", the two states that still need a person.
 */
export type RunFilter = RunStatus | 'awaiting_review';

export async function fetchRuns(params?: {
  page?: number;
  pageSize?: number;
  status?: RunFilter;
  mine?: boolean;
}): Promise<RunListResponse> {
  const { data } = await apiClient.get<RunListResponse>('/runs', {
    params: {
      page: params?.page ?? 1,
      page_size: params?.pageSize ?? 50,
      status: params?.status,
      mine: params?.mine,
    },
  });
  return data;
}

export async function fetchRun(runId: string): Promise<RunDetail> {
  const { data } = await apiClient.get<RunDetail>(`/runs/${runId}`);
  return data;
}

export async function fetchRunStats(): Promise<RunStats> {
  const { data } = await apiClient.get<RunStats>('/runs/stats');
  return data;
}

/** Correct one or more values on a row. Partial: send only what changed. */
export async function editRow(
  runId: string,
  rowId: string,
  values: Record<string, unknown>,
): Promise<RunRow> {
  const { data } = await apiClient.patch<RunRow>(`/runs/${runId}/rows/${rowId}`, {
    values,
  });
  return data;
}

/** Put the model's original answer back — one column, or the whole row. */
export async function revertRow(
  runId: string,
  rowId: string,
  column?: string,
): Promise<RunRow> {
  const { data } = await apiClient.post<RunRow>(
    `/runs/${runId}/rows/${rowId}/revert`,
    { column: column ?? null },
  );
  return data;
}

export async function decideRow(
  runId: string,
  rowId: string,
  status: RowStatus,
  note = '',
): Promise<RunRow> {
  const { data } = await apiClient.patch<RunRow>(
    `/runs/${runId}/rows/${rowId}/status`,
    { status, note },
  );
  return data;
}

/**
 * Sign off a run. `approvePending` is the batch case — "the rest are fine" —
 * and the server records it as exactly that rather than as row-by-row review.
 */
export async function approveRun(
  runId: string,
  approvePending: boolean,
  note = '',
): Promise<RunDetail> {
  const { data } = await apiClient.post<RunDetail>(`/runs/${runId}/approve`, {
    approve_pending: approvePending,
    note,
  });
  return data;
}

export async function rejectRun(runId: string, note = ''): Promise<RunDetail> {
  const { data } = await apiClient.post<RunDetail>(`/runs/${runId}/reject`, { note });
  return data;
}

export async function reopenRun(runId: string, note = ''): Promise<RunDetail> {
  const { data } = await apiClient.post<RunDetail>(`/runs/${runId}/reopen`, { note });
  return data;
}

export async function deleteRun(runId: string): Promise<void> {
  await apiClient.delete(`/runs/${runId}`);
}
