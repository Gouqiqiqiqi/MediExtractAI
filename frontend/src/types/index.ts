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

// ── Data sources ──

export type DbEngine = 'postgresql' | 'mssql' | 'sqlite';

/** Which column in the customer's table means what to us. */
export interface ColumnMapping {
  id: string;
  patient_id: string;
  date: string;
  author: string;
  note_text: string;
  /** Optional — the column holding the kind of note. Empty if the source has none. */
  note_type: string;
}

export interface DataSource {
  id: string;
  name: string;
  description: string;
  engine: DbEngine;
  host: string;
  port: number | null;
  database_name: string;
  username: string;
  table_name: string;
  columns: ColumnMapping;
  is_default: boolean;
  /** Whether a password is stored. The password itself is never returned. */
  has_password: boolean;
}

export interface DataSourceCreate {
  name: string;
  description?: string;
  engine: DbEngine;
  host: string;
  port?: number | null;
  database_name: string;
  username: string;
  password: string;
  table_name: string;
  columns: ColumnMapping;
}

export interface DataSourceTestResult {
  ok: boolean;
  message: string;
  note_count: number | null;
  sample: NotePreview[];
}

// ── Notes ──

export interface NotePreview {
  id: string;
  patient_id: string | null;
  date: string | null;
  author: string | null;
  note_type: string | null;
  text_preview: string;
  char_count: number;
}

/** Values present in a data source, for populating the filter menus. */
export interface NoteFilterOptions {
  note_types: string[];
  authors: string[];
  has_note_type: boolean;
}

/** What the note browser is currently narrowed to. */
export interface NoteFilters {
  search: string;
  noteType: string;
  author: string;
  dateFrom: string;
  dateTo: string;
}

export interface NoteListResponse {
  items: NotePreview[];
  total: number;
  page: number;
  page_size: number;
}

// ── Extraction ──

export interface ExtractionRequest {
  /** Omit to use the default data source. */
  source_id?: string;
  note_ids: string[];
  columns: ColumnDefinition[];
}

export interface FileExtractionRequest {
  text: string;
  columns: ColumnDefinition[];
  /** Where the text came from — an uploaded filename, typically. */
  source_name?: string;
}

export interface ExtractionResponse {
  /** Provenance columns first, then the user's requested schema. */
  columns: ColumnDefinition[];
  rows: Record<string, unknown>[];
  source: string;
  note_count: number;
  /**
   * Names of the leading columns that record where a row came from rather than
   * what was extracted. Rendered read-only: a reviewer corrects extracted
   * values, never the record of which note produced them.
   */
  provenance_columns?: string[];
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
