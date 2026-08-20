/**
 * Export API — download extraction results as CSV / Excel.
 */

import apiClient from './client';
import type { ExportRequest } from '../types';

async function downloadBlob(url: string, body: ExportRequest, filename: string) {
  const { data } = await apiClient.post(url, body, { responseType: 'blob' });
  const blob = new Blob([data]);
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

export async function exportCsv(request: ExportRequest): Promise<void> {
  await downloadBlob('/export/csv', request, 'extraction.csv');
}

export async function exportExcel(request: ExportRequest): Promise<void> {
  await downloadBlob('/export/excel', request, 'extraction.xlsx');
}

export async function exportJson(request: ExportRequest): Promise<Record<string, unknown>> {
  const { data } = await apiClient.post('/export/json', request);
  return data;
}
