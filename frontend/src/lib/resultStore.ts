/**
 * resultStore — the one place that knows how the latest extraction is persisted
 * for the Results page.
 *
 * Kept in a module rather than repeated at each call site so that a field added
 * to the result (provenance_columns was the one that prompted this) cannot be
 * silently dropped by a writer that only remembered to save part of it.
 */

import type { ExtractionResponse } from '../types';

const STORAGE_KEY = 'mediextract:latest_result';

/** What the Results page reads back. A subset of ExtractionResponse. */
export interface SavedResult {
  columns: ExtractionResponse['columns'];
  rows: ExtractionResponse['rows'];
  provenance_columns?: string[];
}

export function saveResult(result: ExtractionResponse): void {
  const payload: SavedResult = {
    columns: result.columns,
    rows: result.rows,
    provenance_columns: result.provenance_columns,
  };
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // Storage can be full or blocked (private browsing). The extraction itself
    // succeeded and is on screen, so failing to cache it is not worth an error.
  }
}

export function saveEditedRows(result: SavedResult): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(result));
  } catch {
    // as above
  }
}

export function loadResult(): SavedResult | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as SavedResult) : null;
  } catch {
    return null;
  }
}
