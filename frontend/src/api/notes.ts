/**
 * Notes API — fetch medical notes from the SQL database.
 */

import apiClient from './client';
import type { NoteListResponse, NotePreview } from '../types';

export async function fetchNotes(
  page = 1,
  pageSize = 20,
  search?: string,
  sourceId?: string,
): Promise<NoteListResponse> {
  const params: Record<string, string | number> = { page, page_size: pageSize };
  if (search) params.search = search;
  if (sourceId) params.source_id = sourceId;
  const { data } = await apiClient.get<NoteListResponse>('/notes/', { params });
  return data;
}

export async function fetchNote(noteId: string): Promise<NotePreview> {
  const { data } = await apiClient.get<NotePreview>(`/notes/${noteId}`);
  return data;
}
