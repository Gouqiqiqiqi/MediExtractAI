/**
 * Upload API — send files for text extraction.
 */

import apiClient from './client';
import type { UploadResponse } from '../types';

export async function uploadFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const { data } = await apiClient.post<UploadResponse>('/upload/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120_000, // 2 min for large files
  });
  return data;
}
