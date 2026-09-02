/**
 * Export API — download a stored run as CSV or Excel.
 *
 * The browser no longer sends the rows it wants exported. It names a run and a
 * scope, and the server decides what may leave and how the file is labelled —
 * a gate the client enforces is not a gate. That also means the filename comes
 * back from the server, because whether a file says "approved" or "DRAFT" is
 * not the client's call.
 */

import apiClient from './client';

export type ExportScope = 'approved' | 'all';

/** Pull the server's filename out of Content-Disposition, however it encoded it. */
function filenameFrom(header: unknown, fallback: string): string {
  if (typeof header !== 'string') return fallback;
  const encoded = header.match(/filename\*=UTF-8''([^;]+)/i);
  if (encoded?.[1]) return decodeURIComponent(encoded[1]);
  const plain = header.match(/filename="?([^";]+)"?/i);
  return plain?.[1] ?? fallback;
}

async function download(url: string, scope: ExportScope, fallback: string) {
  const response = await apiClient.get(url, {
    params: { scope },
    responseType: 'blob',
  });
  const name = filenameFrom(response.headers['content-disposition'], fallback);
  const link = document.createElement('a');
  link.href = URL.createObjectURL(new Blob([response.data]));
  link.download = name;
  link.click();
  URL.revokeObjectURL(link.href);
  return name;
}

export async function exportRunCsv(runId: string, scope: ExportScope): Promise<string> {
  return download(`/export/runs/${runId}/csv`, scope, 'extraction.csv');
}

export async function exportRunExcel(runId: string, scope: ExportScope): Promise<string> {
  return download(`/export/runs/${runId}/excel`, scope, 'extraction.xlsx');
}
