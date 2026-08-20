/**
 * Extraction API — send notes or text for AI-powered structured extraction.
 */

import apiClient from './client';
import type {
  ExtractionRequest,
  ExtractionResponse,
  FileExtractionRequest,
} from '../types';

export async function extractFromDatabase(
  request: ExtractionRequest,
): Promise<ExtractionResponse> {
  const { data } = await apiClient.post<ExtractionResponse>(
    '/extraction/from-database',
    request,
  );
  return data;
}

export async function extractFromText(
  request: FileExtractionRequest,
): Promise<ExtractionResponse> {
  const { data } = await apiClient.post<ExtractionResponse>(
    '/extraction/from-text',
    request,
  );
  return data;
}
