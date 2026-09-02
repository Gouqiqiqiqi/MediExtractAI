/**
 * DatabaseExtractor — choose notes from a connected clinical database and
 * extract them into a table the user defines.
 *
 * Laid out as the sequence it actually is. Previously the schema builder, the
 * note browser and the run button were three items of equal weight with no
 * indication of order or of what was blocking the next step; the numbered
 * panels and the docked action bar make the state of the workflow readable
 * without scrolling.
 */

import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  CheckSquare,
  ChevronLeft,
  ChevronRight,
  Database,
  Play,
  Search,
  Square,
  Table2,
  X,
} from 'lucide-react';
import type { ColumnDefinition, DataSource, ExtractionResponse, NotePreview } from '../types';
import { fetchNotes } from '../api/notes';
import { fetchDataSources } from '../api/dataSources';
import { extractFromDatabase } from '../api/extraction';
import SchemaBuilder from '../components/SchemaBuilder/SchemaBuilder';
import DataTable from '../components/DataTable/DataTable';
import StepPanel from '../components/common/StepPanel';
import EmptyState from '../components/common/EmptyState';
import { SkeletonRows } from '../components/common/Skeleton';
import { saveResult } from '../lib/resultStore';

const PAGE_SIZE = 20;

export default function DatabaseExtractor() {
  const [searchParams, setSearchParams] = useSearchParams();

  const [columns, setColumns] = useState<ColumnDefinition[]>([]);

  const [sources, setSources] = useState<DataSource[]>([]);
  const [sourceId, setSourceId] = useState<string>('');

  const [notes, setNotes] = useState<NotePreview[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [searchTerm, setSearchTerm] = useState(searchParams.get('q') ?? '');
  // The term the currently displayed page was fetched with. Paging must reuse
  // it: typing a new term without pressing Search and then hitting Next would
  // otherwise fetch page 2 of a different query.
  const [activeQuery, setActiveQuery] = useState('');
  const [loadingNotes, setLoadingNotes] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [totalNotes, setTotalNotes] = useState(0);
  const [page, setPage] = useState(1);

  const [previewNote, setPreviewNote] = useState<NotePreview | null>(null);

  const [result, setResult] = useState<ExtractionResponse | null>(null);
  const [extracting, setExtracting] = useState(false);

  const selectedSource = sources.find((s) => s.id === sourceId);

  // ── Load the data sources this deployment can read ──
  useEffect(() => {
    fetchDataSources()
      .then((list) => {
        setSources(list);
        const preferred = list.find((s) => s.is_default) ?? list[0];
        if (preferred) setSourceId(preferred.id);
      })
      .catch(() => toast.error('Could not load data sources'));
  }, []);

  const loadNotes = async (p = 1, term = searchTerm) => {
    setLoadingNotes(true);
    setHasSearched(true);
    try {
      const data = await fetchNotes(p, PAGE_SIZE, term || undefined, sourceId || undefined);
      setActiveQuery(term);
      setNotes(data.items);
      setTotalNotes(data.total);
      setPage(p);
    } catch {
      toast.error('Failed to load notes from the data source');
    } finally {
      setLoadingNotes(false);
    }
  };

  // ── Search handed over from the header ──
  // The header search navigates here with ?q=…; consume it once a source is
  // known, then clear it so a later back-navigation does not re-run the query.
  useEffect(() => {
    const q = searchParams.get('q');
    if (q === null || !sourceId) return;
    setSearchTerm(q);
    void loadNotes(1, q);
    setSearchParams({}, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, sourceId]);

  // A note ID from one system means nothing in another, so changing source
  // must not carry a stale selection across.
  const changeSource = (id: string) => {
    setSourceId(id);
    setSelectedIds(new Set());
    setNotes([]);
    setPreviewNote(null);
    setHasSearched(false);
    setTotalNotes(0);
    setActiveQuery('');
  };

  const toggle = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const allSelected = notes.length > 0 && notes.every((n) => selectedIds.has(n.id));

  const toggleAll = () => {
    if (allSelected) {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        notes.forEach((n) => next.delete(n.id));
        return next;
      });
    } else {
      setSelectedIds((prev) => new Set([...prev, ...notes.map((n) => n.id)]));
    }
  };

  const namedColumns = columns.filter((c) => c.name.trim());
  const schemaReady = namedColumns.length > 0 && namedColumns.length === columns.length;
  const canRun = schemaReady && selectedIds.size > 0 && !extracting;

  const runExtraction = async () => {
    if (selectedIds.size === 0) return toast.error('Select at least one note');
    if (!schemaReady) return toast.error('Every column needs a name');

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
      toast.error('Extraction failed — check the API logs');
    } finally {
      setExtracting(false);
    }
  };

  const lastPage = Math.max(1, Math.ceil(totalNotes / PAGE_SIZE));

  return (
    <div className="max-w-6xl mx-auto pb-20">
      {/* Page heading */}
      <div className="mb-4">
        <h1 className="page-title">Database Extractor</h1>
        <p className="page-subtitle">
          Choose notes from a connected clinical database and extract them into a table you
          define.
        </p>
      </div>

      {/* Which system are we reading? */}
      <div className="card px-4 py-3 mb-4">
        {sources.length === 0 ? (
          <p className="text-body-md text-on-surface-variant">
            No data source configured yet — an administrator adds one under{' '}
            <span className="text-on-surface">Data Sources</span>.
          </p>
        ) : (
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
            <label className="flex items-center gap-2">
              <Database size={15} className="text-on-surface-variant shrink-0" />
              <span className="text-label-md text-on-surface-variant">Data source</span>
              <select
                value={sourceId}
                onChange={(e) => changeSource(e.target.value)}
                className="select-field py-1.5 w-auto min-w-[18rem] max-w-[26rem]"
                aria-label="Data source"
              >
                {sources.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                    {s.is_default ? ' (default)' : ''}
                  </option>
                ))}
              </select>
            </label>

            {selectedSource && (
              <p className="text-label-md text-on-surface-variant">
                Reading <span className="mono">{selectedSource.table_name}</span>
                <span className="mx-1.5 text-outline">·</span>
                note text from{' '}
                <span className="mono">{selectedSource.columns.note_text}</span>
              </p>
            )}
          </div>
        )}
      </div>

      <div className="space-y-4">
        {/* ── Step 1: schema ── */}
        <StepPanel
          index={1}
          title="Output schema"
          status={schemaReady ? 'done' : 'active'}
          summary={
            columns.length === 0
              ? 'What columns do you want?'
              : `${columns.length} column${columns.length === 1 ? '' : 's'}${
                  schemaReady ? '' : ' · some unnamed'
                }`
          }
          flush
        >
          <SchemaBuilder columns={columns} onChange={setColumns} />
        </StepPanel>

        {/* ── Step 2: notes ── */}
        <StepPanel
          index={2}
          title="Select notes"
          status={
            selectedIds.size > 0 ? 'done' : hasSearched || schemaReady ? 'active' : 'todo'
          }
          summary={
            selectedIds.size > 0
              ? `${selectedIds.size} selected`
              : totalNotes > 0
                ? `${totalNotes} available`
                : undefined
          }
          actions={
            <>
              {selectedIds.size > 0 && (
                <button onClick={() => setSelectedIds(new Set())} className="btn-text">
                  <X size={14} />
                  Clear
                </button>
              )}
              <div className="relative">
                <Search
                  size={14}
                  className="absolute left-2.5 top-1/2 -translate-y-1/2 text-on-surface-variant pointer-events-none"
                />
                <input
                  type="search"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && loadNotes(1)}
                  placeholder="Keyword, patient ID, author…"
                  className="input-field py-1.5 pl-8 w-64"
                  aria-label="Search notes"
                />
              </div>
              <button
                onClick={() => loadNotes(1)}
                disabled={sources.length === 0}
                className="btn-filled"
              >
                Search
              </button>
            </>
          }
          flush
        >
          {loadingNotes ? (
            <SkeletonRows rows={6} className="py-2" />
          ) : !hasSearched ? (
            <EmptyState
              icon={Search}
              title="Nothing loaded yet"
              description="Search to browse this data source, or leave the box empty and press Search to list everything."
            />
          ) : notes.length === 0 ? (
            <EmptyState
              icon={Search}
              title="No notes matched"
              description={
                searchTerm ? (
                  <>
                    Nothing in this source contains{' '}
                    <span className="mono">{searchTerm}</span>.
                  </>
                ) : (
                  'This data source returned no rows.'
                )
              }
            />
          ) : (
            <div className="flex">
              <div className="flex-1 min-w-0">
                <table className="w-full">
                  <thead>
                    <tr className="text-left border-b border-outline bg-surface-dim">
                      <th className="w-10 px-3 py-2">
                        <button
                          onClick={toggleAll}
                          className="text-on-surface-variant hover:text-gm-blue transition-colors"
                          aria-label={allSelected ? 'Deselect page' : 'Select page'}
                        >
                          {allSelected ? <CheckSquare size={15} /> : <Square size={15} />}
                        </button>
                      </th>
                      <th className="px-3 py-2 text-label-sm text-on-surface-variant/80">ID</th>
                      <th className="px-3 py-2 text-label-sm text-on-surface-variant/80">Patient</th>
                      <th className="px-3 py-2 text-label-sm text-on-surface-variant/80">Date</th>
                      <th className="px-3 py-2 text-label-sm text-on-surface-variant/80">Author</th>
                      <th className="px-3 py-2 text-label-sm text-on-surface-variant/80">Preview</th>
                    </tr>
                  </thead>
                  <tbody>
                    {notes.map((note) => {
                      const isSelected = selectedIds.has(note.id);
                      const isPreviewed = previewNote?.id === note.id;
                      return (
                        <tr
                          key={note.id}
                          onClick={() => setPreviewNote(note)}
                          className={`border-b border-outline-variant cursor-pointer transition-colors duration-150 ${
                            isPreviewed
                              ? 'bg-gm-blue-light'
                              : isSelected
                                ? 'bg-gm-blue-light/50'
                                : 'hover:bg-surface-dim'
                          }`}
                        >
                          <td
                            className="px-3 py-2"
                            onClick={(e) => {
                              e.stopPropagation();
                              toggle(note.id);
                            }}
                          >
                            <button
                              className={isSelected ? 'text-gm-blue' : 'text-on-surface-variant'}
                              aria-label={isSelected ? 'Deselect note' : 'Select note'}
                            >
                              {isSelected ? <CheckSquare size={15} /> : <Square size={15} />}
                            </button>
                          </td>
                          <td className="px-3 py-2 mono whitespace-nowrap">{note.id}</td>
                          <td className="px-3 py-2 mono whitespace-nowrap text-on-surface-variant">
                            {note.patient_id || '—'}
                          </td>
                          <td className="px-3 py-2 text-body-md tabular whitespace-nowrap">
                            {note.date || '—'}
                          </td>
                          <td className="px-3 py-2 text-body-md whitespace-nowrap max-w-[14rem] truncate">
                            {note.author || '—'}
                          </td>
                          <td className="px-3 py-2 text-body-md text-on-surface-variant">
                            <span className="block max-w-md truncate">
                              {note.text_preview?.replace(/\s+/g, ' ') || '—'}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>

                <div className="flex items-center justify-between px-3 py-2.5">
                  <span className="text-label-md text-on-surface-variant tabular">
                    Page {page} of {lastPage} · {totalNotes} note
                    {totalNotes === 1 ? '' : 's'}
                  </span>
                  <div className="flex gap-1.5">
                    <button
                      onClick={() => loadNotes(page - 1, activeQuery)}
                      disabled={page <= 1}
                      className="btn-outlined py-1.5 px-2.5"
                    >
                      <ChevronLeft size={14} /> Previous
                    </button>
                    <button
                      onClick={() => loadNotes(page + 1, activeQuery)}
                      disabled={page >= lastPage}
                      className="btn-outlined py-1.5 px-2.5"
                    >
                      Next <ChevronRight size={14} />
                    </button>
                  </div>
                </div>
              </div>

              {/* Note preview */}
              {previewNote && (
                <aside className="w-96 shrink-0 border-l border-outline flex flex-col">
                  <div className="flex items-center justify-between px-3 py-2 border-b border-outline bg-surface-dim">
                    <h3 className="text-title-sm text-on-surface">Note preview</h3>
                    <button
                      onClick={() => setPreviewNote(null)}
                      className="btn-icon w-7 h-7"
                      aria-label="Close preview"
                    >
                      <X size={14} />
                    </button>
                  </div>
                  <div className="p-3 space-y-3 overflow-auto">
                    <dl className="grid grid-cols-2 gap-x-3 gap-y-2">
                      {[
                        ['ID', previewNote.id, true],
                        ['Patient', previewNote.patient_id || '—', true],
                        ['Date', previewNote.date || '—', false],
                        ['Characters', previewNote.char_count.toLocaleString(), false],
                      ].map(([label, value, isMono]) => (
                        <div key={String(label)}>
                          <dt className="text-label-sm text-on-surface-variant/80">{label}</dt>
                          <dd className={isMono ? 'mono' : 'text-body-md text-on-surface tabular'}>
                            {value}
                          </dd>
                        </div>
                      ))}
                      <div className="col-span-2">
                        <dt className="text-label-sm text-on-surface-variant/80">Author</dt>
                        <dd className="text-body-md text-on-surface">
                          {previewNote.author || '—'}
                        </dd>
                      </div>
                    </dl>

                    <pre
                      className="text-body-md whitespace-pre-wrap bg-surface-dim border border-outline
                                 rounded-gm-md p-3 max-h-72 overflow-auto text-on-surface leading-relaxed"
                    >
                      {previewNote.text_preview}
                    </pre>

                    <button
                      onClick={() => toggle(previewNote.id)}
                      className={`w-full ${
                        selectedIds.has(previewNote.id) ? 'btn-outlined' : 'btn-filled'
                      }`}
                    >
                      {selectedIds.has(previewNote.id) ? 'Remove from selection' : 'Add to selection'}
                    </button>
                  </div>
                </aside>
              )}
            </div>
          )}
        </StepPanel>

        {/* ── Results ── */}
        {result && (
          <StepPanel
            index={3}
            title="Results"
            status="done"
            summary={`${result.rows.length} rows · ${result.note_count} notes`}
            actions={
              <Link to="/results" className="btn-outlined">
                <Table2 size={14} />
                Review &amp; export
              </Link>
            }
            flush
          >
            <DataTable
              columns={result.columns}
              data={result.rows}
              readOnlyColumns={result.provenance_columns}
              onDataChange={(rows) => {
                // Corrections made here have to reach the stored result too,
                // or the Results page and any export would hand back the
                // pre-edit values.
                const updated = { ...result, rows };
                setResult(updated);
                saveResult(updated);
              }}
            />
          </StepPanel>
        )}
      </div>

      {/* Docked action bar — the run button should never be somewhere you have
          to hunt for after scrolling a long note list. */}
      <div className="fixed bottom-0 left-60 right-0 border-t border-outline bg-surface/95 backdrop-blur-sm z-20">
        <div className="max-w-6xl mx-auto px-6 py-2.5 flex items-center gap-4">
          <p className="text-label-md text-on-surface-variant tabular">
            {selectedIds.size} note{selectedIds.size === 1 ? '' : 's'}
            <span className="mx-1.5 text-outline">×</span>
            {namedColumns.length} column{namedColumns.length === 1 ? '' : 's'}
            {!schemaReady && columns.length > 0 && (
              <span className="ml-2 text-gm-yellow">every column needs a name</span>
            )}
          </p>
          <div className="flex-1" />
          <button onClick={runExtraction} disabled={!canRun} className="btn-filled">
            {extracting ? (
              <>
                <span className="w-3.5 h-3.5 rounded-full border-2 border-white/40 border-t-white animate-spin" />
                Extracting…
              </>
            ) : (
              <>
                <Play size={14} />
                Run extraction
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
