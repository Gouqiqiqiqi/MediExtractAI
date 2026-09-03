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
  /** Pages of scanned documents, read by the model directly. */
  images?: DocumentImage[];
  columns: ColumnDefinition[];
  /** Where the text came from — an uploaded filename, typically. */
  source_name?: string;
}

export interface ExtractionResponse {
  /** The run this result was recorded as — every extraction is persisted. */
  run_id: string;
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

// ── Runs: the review lifecycle ──

/** Where a run sits between "the model answered" and "a clinician signed". */
export type RunStatus = 'draft' | 'in_review' | 'approved' | 'rejected';

export type RowStatus = 'pending' | 'approved' | 'rejected';

export interface RunRow {
  id: string;
  row_index: number;
  note_id: string;
  patient_id: string;
  data: Record<string, unknown>;
  /** The model's untouched answer, kept so a correction can be seen and undone. */
  ai_data: Record<string, unknown>;
  corrected_columns: string[];
  status: RowStatus;
  review_note: string;
  edited_by: string;
  edited_at: string | null;
  decided_by: string;
  decided_at: string | null;
}

export interface RunSummary {
  id: string;
  created_at: string;
  created_by: string;
  /** "database" — rows point at notes we can read back. "upload" — a file. */
  source_kind: 'database' | 'upload';
  source_label: string;
  note_count: number;
  row_count: number;
  status: RunStatus;
  models_used: string;
  approved_by: string;
  approved_at: string | null;
  pending_rows: number;
  approved_rows: number;
  rejected_rows: number;
  corrected_rows: number;
}

export interface RunDetail extends RunSummary {
  columns: ColumnDefinition[];
  provenance_columns: string[];
  rows: RunRow[];
  sign_off_note: string;
}

export interface RunListResponse {
  items: RunSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface RunStats {
  total: number;
  draft: number;
  in_review: number;
  approved: number;
  rejected: number;
  awaiting_review: number;
  pending_rows: number;
}

// ── Upload ──

/** One page of a scanned document, ready to be sent to a vision model. */
export interface DocumentImage {
  mime_type: string;
  /** Base64-encoded image bytes, with no `data:` prefix. */
  data: string;
  page: number;
}

export interface UploadResponse {
  filename: string;
  size_bytes: number;
  extracted_text: string;
  char_count: number;
  /**
   * Present when the file had no text layer and was rendered to images
   * instead — a scan, or a photo saved as a PDF. These go back to the server
   * with the extraction request and are read by a vision-capable model.
   */
  page_images: DocumentImage[];
  page_count: number;
  /** How the file was handled, when that is worth saying. Shown in the list. */
  warning: string;
}

// ── Export ──
// No request type: a file is produced from a stored run, so what leaves is
// what was reviewed rather than what the browser posted back.

// ── Auth ──

export interface UserClaims {
  sub: string;
  name: string;
  email: string;
  roles: string[];
}
