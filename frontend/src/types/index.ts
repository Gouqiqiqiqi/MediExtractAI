/**
 * Shared TypeScript types matching the backend Pydantic schemas.
 */

// ── Column / Schema ──

export type ColumnDataType =
  | 'text'
  | 'integer'
  | 'float'
  | 'boolean'
  | 'date'
  | 'datetime'
  | 'text[]';

export interface ColumnDefinition {
  name: string;
  data_type: ColumnDataType;
  description: string;
  required: boolean;
}

// ── Notes ──

export interface NotePreview {
  id: string;
  patient_id: string | null;
  date: string | null;
  author: string | null;
  text_preview: string;
  char_count: number;
}

export interface NoteListResponse {
  items: NotePreview[];
  total: number;
  page: number;
  page_size: number;
}

// ── Extraction ──

export interface ExtractionRequest {
  note_ids: string[];
  columns: ColumnDefinition[];
}

export interface FileExtractionRequest {
  text: string;
  columns: ColumnDefinition[];
}

export interface ExtractionResponse {
  columns: ColumnDefinition[];
  rows: Record<string, unknown>[];
  source: string;
  note_count: number;
}

// ── Upload ──

export interface UploadResponse {
  filename: string;
  size_bytes: number;
  extracted_text: string;
  char_count: number;
}

// ── Export ──

export interface ExportRequest {
  columns: ColumnDefinition[];
  rows: Record<string, unknown>[];
}

// ── Auth ──

export interface UserClaims {
  sub: string;
  name: string;
  email: string;
  roles: string[];
}
