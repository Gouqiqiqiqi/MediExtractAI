/**
 * DatabaseExtractor — select notes from SQL and extract structured fields.
 * Features: data preview panel, multi-select with bulk actions, Google Material styling.
 */

import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { Play, Search, Eye, EyeOff, CheckSquare, Square, X, ChevronLeft, ChevronRight } from 'lucide-react';
import type { ColumnDefinition, DataSource, ExtractionResponse, NotePreview } from '../types';
import { fetchNotes } from '../api/notes';
import { fetchDataSources } from '../api/dataSources';
import { extractFromDatabase } from '../api/extraction';
import SchemaBuilder from '../components/SchemaBuilder/SchemaBuilder';
import DataTable from '../components/DataTable/DataTable';
import { saveResult } from '../lib/resultStore';
import Loading from '../components/common/Loading';

export default function DatabaseExtractor() {
  // Schema
  const [columns, setColumns] = useState<ColumnDefinition[]>([]);

  // Data source
  const [sources, setSources] = useState<DataSource[]>([]);
  const [sourceId, setSourceId] = useState<string>('');

  // Notes browser
  const [notes, setNotes] = useState<NotePreview[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [searchTerm, setSearchTerm] = useState('');
  const [loadingNotes, setLoadingNotes] = useState(false);
  const [totalNotes, setTotalNotes] = useState(0);
  const [page, setPage] = useState(1);

  // Data preview
  const [previewNote, setPreviewNote] = useState<NotePreview | null>(null);
  const [showPreview, setShowPreview] = useState(true);

  // Extraction
  const [result, setResult] = useState<ExtractionResponse | null>(null);
  const [extracting, setExtracting] = useState(false);

  const selectedSource = sources.find((s) => s.id === sourceId);

  // ── Load the data sources this deployment can read ──
  useEffect(() => {
    fetchDataSources()
      .then((list) => {
        setSources(list);
        // Default to whichever the administrator marked as default.
        const preferred = list.find((s) => s.is_default) ?? list[0];
        if (preferred) setSourceId(preferred.id);
      })
      .catch(() => toast.error('Could not load data sources'));
  }, []);

  // ── Load notes ──
  const loadNotes = async (p = 1) => {
    setLoadingNotes(true);
    try {
      const data = await fetchNotes(p, 20, searchTerm || undefined, sourceId || undefined);
      setNotes(data.items);
      setTotalNotes(data.total);
      setPage(p);
    } catch {
      toast.error('Failed to load notes from database');
    } finally {
      setLoadingNotes(false);
    }
  };

  // A note ID from one system means nothing in another, so changing source
  // must not carry a stale selection across.
  const changeSource = (id: string) => {
    setSourceId(id);
    setSelectedIds(new Set());
    setNotes([]);
    setPreviewNote(null);
  };

  // ── Toggle single selection ──
  const toggle = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  // ── Select / deselect all on current page ──
  const toggleAll = () => {
    if (selectedIds.size === notes.length && notes.length > 0) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(notes.map((n) => n.id)));
    }
  };

  // ── Clear selection ──
  const clearSelection = () => {
    setSelectedIds(new Set());
  };

  // ── Run extraction ──
  const runExtraction = async () => {
    if (selectedIds.size === 0) {
      toast.error('Select at least one note');
      return;
    }
    if (columns.length === 0 || columns.some((c) => !c.name.trim())) {
      toast.error('Define at least one named column');
      return;
    }

    setExtracting(true);
    try {
      const res = await extractFromDatabase({
        source_id: sourceId || undefined,
        note_ids: Array.from(selectedIds),
        columns,
      });
      setResult(res);
      saveResult(res);
      toast.success(`Extracted ${res.rows.length} rows from ${res.note_count} notes`);
    } catch {
      toast.error('Extraction failed — check API logs');
    } finally {
      setExtracting(false);
    }
  };

  const allSelected = notes.length > 0 && selectedIds.size === notes.length;
  const someSelected = selectedIds.size > 0 && selectedIds.size < notes.length;

  return (
    <div className="max-w-7xl mx-auto space-y-5">
      <h1 className="text-display-sm font-bold text-on-surface">Database Extractor</h1>

      {/* Step 1: Define schema */}
      <SchemaBuilder columns={columns} onChange={setColumns} />

      {/* Step 2: Browse & select notes */}
      <div className="card-elevated">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-title-md font-semibold text-on-surface">Select Notes</h3>
          {notes.length > 0 && (
            <button
              onClick={() => setShowPreview(!showPreview)}
              className="btn-text flex items-center gap-1.5 text-label-md"
            >
              {showPreview ? <EyeOff size={16} /> : <Eye size={16} />}
              {showPreview ? 'Hide Preview' : 'Show Preview'}
            </button>
          )}
        </div>

        {/* Data source */}
        <div className="mb-4">
          <label className="block text-label-md text-on-surface-variant mb-1">
            Data source
          </label>
          {sources.length === 0 ? (
            <p className="text-body-md text-on-surface-variant">
              No data source configured yet — an administrator adds one under Data Sources.
            </p>
          ) : (
            <>
              <select
                value={sourceId}
                onChange={(e) => changeSource(e.target.value)}
                className="w-full px-3 py-2 bg-surface-container rounded-gm-lg text-body-md
                           text-on-surface border-0 focus:outline-none focus:ring-2 focus:ring-gm-blue/40"
              >
                {sources.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                    {s.is_default ? ' (default)' : ''}
                  </option>
                ))}
              </select>
              <p className="text-label-md text-on-surface-variant mt-1">
                Reading <span className="font-mono">{selectedSource?.table_name}</span> — notes
                come from the column mapped as{' '}
                <span className="font-mono">{selectedSource?.columns.note_text}</span>.
              </p>
            </>
          )}
        </div>

        {/* Search bar */}
        <div className="flex gap-2 mb-4">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && loadNotes(1)}
              placeholder="Search notes by keyword, patient ID, or author..."
              className="input-field pl-9"
            />
          </div>
          <button onClick={() => loadNotes(1)} className="btn-filled">
            Search
          </button>
        </div>

        {/* Selection action bar */}
        {selectedIds.size > 0 && (
          <div className="flex items-center gap-3 mb-4 px-4 py-2.5 bg-gm-blue-light rounded-gm-lg">
            <span className="text-label-lg text-gm-blue font-medium">
              {selectedIds.size} note{selectedIds.size !== 1 ? 's' : ''} selected
            </span>
            <div className="flex-1" />
            <button onClick={toggleAll} className="btn-text text-label-md py-1">
              {allSelected ? 'Deselect All' : 'Select All on Page'}
            </button>
            <button onClick={clearSelection} className="text-gm-blue hover:text-gm-red transition-colors">
              <X size={18} />
            </button>
          </div>
        )}

        {loadingNotes ? (
          <Loading message="Loading notes..." />
        ) : notes.length === 0 ? (
          <div className="text-center py-12">
            <Search size={40} className="mx-auto text-on-surface-variant/40 mb-3" />
            <p className="text-body-md text-on-surface-variant">
              Click "Search" to load notes from your database.
            </p>
          </div>
        ) : (
          <div className="flex gap-4">
            {/* Table */}
            <div className={`${showPreview && previewNote ? 'flex-1 min-w-0' : 'w-full'} transition-all`}>
              <div className="border border-outline/40 rounded-gm-md overflow-hidden">
                <table className="w-full text-body-md">
                  <thead>
                    <tr className="bg-surface-container text-left">
                      <th className="px-4 py-3 w-12">
                        <button onClick={toggleAll} className="text-on-surface-variant hover:text-gm-blue transition-colors">
                          {allSelected ? <CheckSquare size={18} /> : someSelected ? <CheckSquare size={18} className="opacity-50" /> : <Square size={18} />}
                        </button>
                      </th>
                      <th className="px-4 py-3 text-label-lg text-on-surface-variant font-medium">ID</th>
                      <th className="px-4 py-3 text-label-lg text-on-surface-variant font-medium">Date</th>
                      <th className="px-4 py-3 text-label-lg text-on-surface-variant font-medium">Author</th>
                      <th className="px-4 py-3 text-label-lg text-on-surface-variant font-medium">Preview</th>
                    </tr>
                  </thead>
                  <tbody>
                    {notes.map((note) => {
                      const isSelected = selectedIds.has(note.id);
                      const isPreviewed = previewNote?.id === note.id;
                      return (
                        <tr
                          key={note.id}
                          className={`border-t border-outline/20 cursor-pointer transition-colors duration-150 ${
                            isPreviewed
                              ? 'bg-gm-blue-light/60'
                              : isSelected
                                ? 'bg-gm-blue-light/30'
                                : 'hover:bg-surface-container'
                          }`}
                          onClick={() => setPreviewNote(note)}
                        >
                          <td className="px-4 py-3" onClick={(e) => { e.stopPropagation(); toggle(note.id); }}>
                            <button className={`transition-colors ${isSelected ? 'text-gm-blue' : 'text-on-surface-variant'}`}>
                              {isSelected ? <CheckSquare size={18} /> : <Square size={18} />}
                            </button>
                          </td>
                          <td className="px-4 py-3 font-mono text-label-md text-on-surface">{note.id}</td>
                          <td className="px-4 py-3 text-body-md text-on-surface">{note.date || '—'}</td>
                          <td className="px-4 py-3 text-body-md text-on-surface">{note.author || '—'}</td>
                          <td className="px-4 py-3 text-body-md text-on-surface-variant truncate max-w-xs">
                            {note.text_preview || '—'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="flex items-center justify-between mt-3">
                <span className="text-label-lg text-on-surface-variant">
                  Page {page} · {totalNotes} total notes
                </span>
                <div className="flex gap-1">
                  <button
                    onClick={() => loadNotes(page - 1)}
                    disabled={page <= 1}
                    className="btn-outlined py-1.5 px-3 text-label-md flex items-center gap-1 disabled:opacity-40"
                  >
                    <ChevronLeft size={16} /> Previous
                  </button>
                  <button
                    onClick={() => loadNotes(page + 1)}
                    disabled={notes.length < 20}
                    className="btn-outlined py-1.5 px-3 text-label-md flex items-center gap-1 disabled:opacity-40"
                  >
                    Next <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            </div>

            {/* Data Preview Panel */}
            {showPreview && previewNote && (
              <div className="w-96 flex-shrink-0 border border-outline/40 rounded-gm-md overflow-hidden bg-surface">
                <div className="flex items-center justify-between px-4 py-3 bg-surface-container border-b border-outline/40">
                  <h4 className="text-title-sm font-semibold text-on-surface">Note Preview</h4>
                  <button
                    onClick={() => setPreviewNote(null)}
                    className="text-on-surface-variant hover:text-on-surface transition-colors"
                  >
                    <X size={16} />
                  </button>
                </div>
                <div className="p-4 space-y-3">
                  <div className="grid grid-cols-2 gap-3 text-label-md">
                    <div>
                      <span className="text-on-surface-variant">ID</span>
                      <p className="font-mono text-on-surface">{previewNote.id}</p>
                    </div>
                    <div>
                      <span className="text-on-surface-variant">Date</span>
                      <p className="text-on-surface">{previewNote.date || '—'}</p>
                    </div>
                    <div>
                      <span className="text-on-surface-variant">Author</span>
                      <p className="text-on-surface">{previewNote.author || '—'}</p>
                    </div>
                    <div>
                      <span className="text-on-surface-variant">Characters</span>
                      <p className="text-on-surface">{previewNote.char_count.toLocaleString()}</p>
                    </div>
                  </div>
                  <div className="divider" />
                  <div>
                    <span className="text-label-md text-on-surface-variant mb-1.5 block">Content</span>
                    <pre className="text-body-md whitespace-pre-wrap bg-surface-container p-3 rounded-gm-sm
                                    max-h-80 overflow-auto text-on-surface leading-relaxed">
                      {previewNote.text_preview}
                    </pre>
                  </div>
                  <button
                    onClick={() => {
                      if (!selectedIds.has(previewNote.id)) toggle(previewNote.id);
                    }}
                    className={`w-full ${selectedIds.has(previewNote.id) ? 'btn-tonal' : 'btn-filled'} text-label-md`}
                  >
                    {selectedIds.has(previewNote.id) ? 'Selected ✓' : 'Add to Selection'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Step 3: Extract */}
      <div className="flex justify-end">
        <button
          onClick={runExtraction}
          disabled={extracting || selectedIds.size === 0 || columns.length === 0}
          className="btn-filled flex items-center gap-2"
        >
          {extracting ? (
            <>Extracting...</>
          ) : (
            <>
              <Play size={16} />
              Extract Data ({selectedIds.size} note{selectedIds.size !== 1 ? 's' : ''})
            </>
          )}
        </button>
      </div>

      {/* Step 4: Results */}
      {result && (
        <DataTable
          columns={result.columns}
          data={result.rows}
          readOnlyColumns={result.provenance_columns}
        />
      )}
    </div>
  );
}
