/**
 * Notes API — browse the clinical notes in a configured data source.
 */

import apiClient from './client';
import type {
  NoteFilterOptions,
  NoteFilters,
  NoteListResponse,
  NotePreview,
} from '../types';

/** Only send the filters that are actually set. */
function filterParams(filters?: Partial<NoteFilters>): Record<string, string> {
  const params: Record<string, string> = {};
  if (!filters) return params;
  if (filters.search) params.search = filters.search;
  if (filters.noteType) params.note_type = filters.noteType;
  if (filters.author) params.author = filters.author;
  if (filters.dateFrom) params.date_from = filters.dateFrom;
  if (filters.dateTo) params.date_to = filters.dateTo;
  return params;
}

export async function fetchNotes(
  page = 1,
  pageSize = 20,
  filters?: Partial<NoteFilters>,
  sourceId?: string,
): Promise<NoteListResponse> {
  const params: Record<string, string | number> = {
    page,
    page_size: pageSize,
    ...filterParams(filters),
  };
  if (sourceId) params.source_id = sourceId;
  const { data } = await apiClient.get<NoteListResponse>('/notes/', { params });
  return data;
}

export async function fetchNoteFilterOptions(
  sourceId?: string,
): Promise<NoteFilterOptions> {
  const params: Record<string, string> = {};
  if (sourceId) params.source_id = sourceId;
  const { data } = await apiClient.get<NoteFilterOptions>('/notes/filters', { params });
  return data;
}

export async function fetchNote(
  noteId: string,
  sourceId?: string,
): Promise<NotePreview> {
  const params: Record<string, string> = {};
  if (sourceId) params.source_id = sourceId;
  const { data } = await apiClient.get<NotePreview>(`/notes/${noteId}`, { params });
  return data;
}
