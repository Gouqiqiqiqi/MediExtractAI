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

import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  CheckSquare,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  Database,
  Play,
  Search,
  Square,
  X,
} from 'lucide-react';
import type {
  ColumnDefinition,
  DataSource,
  NoteFilterOptions,
  NoteFilters,
  NotePreview,
} from '../types';
import { fetchNoteFilterOptions, fetchNotes } from '../api/notes';
import { errorMessage } from '../api/errors';
import { fetchDataSources } from '../api/dataSources';
import { extractFromDatabase } from '../api/extraction';
import SchemaBuilder from '../components/SchemaBuilder/SchemaBuilder';
import RunDialog from '../components/Review/RunDialog';
import StepPanel from '../components/common/StepPanel';
import EmptyState from '../components/common/EmptyState';
import { SkeletonRows } from '../components/common/Skeleton';
import NoteFilterBar, {
  activeFilterCount,
  EMPTY_FILTERS,
} from '../components/NoteBrowser/NoteFilterBar';
import { fetchRun } from '../api/runs';
import { useRole } from '../auth/RoleContext';
import { RunStatusChip } from '../components/Review/StatusChip';
import { runProgress } from '../lib/runProgress';
import { runsChanged } from '../lib/runEvents';
import { relativeTime } from '../lib/time';
import type { RunDetail } from '../types';

const PAGE_SIZE = 20;

export default function DatabaseExtractor() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { canExtract } = useRole();

  const [columns, setColumns] = useState<ColumnDefinition[]>([]);

  const [sources, setSources] = useState<DataSource[]>([]);
  const [sourceId, setSourceId] = useState<string>('');

  const [notes, setNotes] = useState<NotePreview[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [filters, setFilters] = useState<NoteFilters>({
    ...EMPTY_FILTERS,
    search: searchParams.get('q') ?? '',
  });
  // The filters the currently displayed page was fetched with. Paging reuses
  // them rather than the live ones, so a filter edited while page 2 is on
  // screen cannot page into a query the list has not been refetched for; it
  // also tells the auto-apply effect below when it has nothing left to do.
  const [appliedFilters, setAppliedFilters] = useState<NoteFilters>(EMPTY_FILTERS);
  const [filterOptions, setFilterOptions] = useState<NoteFilterOptions | null>(null);
  const [loadingNotes, setLoadingNotes] = useState(false);
  const [totalNotes, setTotalNotes] = useState(0);
  const [page, setPage] = useState(1);

  const [previewNote, setPreviewNote] = useState<NotePreview | null>(null);

  // The run as the server stored it, and whether its table is currently open
  // over the page. Two pieces of state rather than one: closing the pop-up must
  // not lose the run, or the panel offering to reopen it would have nothing to
  // reopen.
  const [run, setRun] = useState<RunDetail | null>(null);
  const [showResult, setShowResult] = useState(false);
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

  const loadNotes = async (p = 1, applied: NoteFilters = filters) => {
    setLoadingNotes(true);
    try {
      const data = await fetchNotes(p, PAGE_SIZE, applied, sourceId || undefined);
      setAppliedFilters(applied);
      setNotes(data.items);
      setTotalNotes(data.total);
      setPage(p);
    } catch (err) {
      toast.error(errorMessage(err, 'Failed to load notes from the data source'));
    } finally {
      setLoadingNotes(false);
    }
  };

  const handedOverQuery = searchParams.get('q');

  // ── When a source is chosen: load its filter values and list everything ──
  // Listing on arrival rather than making the user press Search first: the
  // notes are the point of the page, and an empty table teaches nothing about
  // what is in there.
  useEffect(() => {
    if (!sourceId) return;
    fetchNoteFilterOptions(sourceId)
      .then(setFilterOptions)
      .catch(() => setFilterOptions(null));

    // A query handed over from the header is applied by the effect below.
    // Listing here as well would fetch twice and then show the unfiltered list.
    if (handedOverQuery !== null) return;
    void loadNotes(1, EMPTY_FILTERS);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sourceId]);

  // ── Search handed over from the header ──
  // Keyed on the query itself rather than the whole search-params object:
  // clearing the parameter below changes that object, and depending on it
  // would re-run this effect and immediately discard the query it just applied.
  useEffect(() => {
    if (handedOverQuery === null || !sourceId) return;
    const next: NoteFilters = { ...EMPTY_FILTERS, search: handedOverQuery };
    setFilters(next);
    void loadNotes(1, next);
    setSearchParams({}, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [handedOverQuery, sourceId]);

  // ── Filters apply themselves ──
  // There used to be an Apply button, and it was the whole of the "filtering
  // is broken" report: choosing a clinician lit up "Clear 1" while the list
  // below still showed all 24 notes, so the filter looked ignored. Refetching
  // on change removes the pending state that nothing on screen explained.
  //
  // Debounced because the keyword box changes on every keystroke. Keyed on the
  // serialised filters so the effect re-runs on content, not identity, and
  // stops as soon as what is displayed matches what is asked for — which is
  // also what keeps it from re-fetching the page it just loaded.
  const filtersKey = JSON.stringify(filters);
  const appliedKey = JSON.stringify(appliedFilters);
  const filtersRef = useRef(filters);
  filtersRef.current = filters;

  useEffect(() => {
    if (!sourceId || handedOverQuery !== null) return;
    if (filtersKey === appliedKey) return;
    const timer = setTimeout(() => void loadNotes(1, filtersRef.current), 300);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtersKey, appliedKey, sourceId, handedOverQuery]);

  // A note ID from one system means nothing in another, so changing source
  // must not carry a stale selection across.
  const changeSource = (id: string) => {
    setSourceId(id);
    setSelectedIds(new Set());
    setNotes([]);
    setPreviewNote(null);
    setTotalNotes(0);
    setFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
    setFilterOptions(null);
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
      // The backend has already saved this as a draft run; reading it back is
      // what gives every row its identity, so a correction made in the pop-up
      // is the same edit the review page would make.
      setRun(await fetchRun(res.run_id));
      setShowResult(true);
      runsChanged();
    } catch (err) {
      // The backend says which models are exhausted and when they return.
      // Long, but every word of it is what the reader needs next.
      toast.error(errorMessage(err, 'Extraction failed — check the API logs'), {
        duration: 8000,
      });
    } finally {
      setExtracting(false);
    }
  };

  const lastPage = Math.max(1, Math.ceil(totalNotes / PAGE_SIZE));
  const appliedActive = activeFilterCount(appliedFilters);

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
            selectedIds.size > 0 ? 'done' : notes.length > 0 || schemaReady ? 'active' : 'todo'
          }
          summary={
            selectedIds.size > 0
              ? `${selectedIds.size} selected`
              : totalNotes > 0
                ? `${totalNotes} note${totalNotes === 1 ? '' : 's'}${
                    appliedActive > 0 ? ' matching' : ''
                  }`
                : undefined
          }
          actions={
            selectedIds.size > 0 ? (
              <button onClick={() => setSelectedIds(new Set())} className="btn-text">
                <X size={14} />
                Clear selection
              </button>
            ) : undefined
          }
          flush
        >
          <NoteFilterBar
            options={filterOptions}
            filters={filters}
            onChange={setFilters}
            onApply={() => loadNotes(1, filters)}
            onReset={() => {
              setFilters(EMPTY_FILTERS);
              void loadNotes(1, EMPTY_FILTERS);
            }}
            disabled={sources.length === 0}
          />

          {loadingNotes ? (
            <SkeletonRows rows={6} className="py-2" />
          ) : notes.length === 0 ? (
            <EmptyState
              icon={Search}
              title={appliedActive > 0 ? 'No notes match these filters' : 'No notes here'}
              description={
                appliedActive > 0
                  ? 'Widen the date range, or clear a filter.'
                  : 'This data source returned no rows.'
              }
              action={
                appliedActive > 0 ? (
                  <button
                    onClick={() => {
                      setFilters(EMPTY_FILTERS);
                      void loadNotes(1, EMPTY_FILTERS);
                    }}
                    className="btn-outlined"
                  >
                    Clear filters
                  </button>
                ) : undefined
              }
            />
          ) : (
            <div className="flex">
              <div className="flex-1 min-w-0">
                {/* table-fixed with explicit widths: in auto layout the browser
                    sizes columns by content, so max-width on a cell is ignored
                    and a long author name pushes the preview past the panel. */}
                <table className="w-full table-fixed">
                  <thead>
                    <tr className="text-left border-b border-outline bg-surface-dim">
                      <th className="w-10 px-2 py-2">
                        <button
                          onClick={toggleAll}
                          className="text-on-surface-variant hover:text-gm-blue transition-colors"
                          aria-label={allSelected ? 'Deselect page' : 'Select page'}
                        >
                          {allSelected ? <CheckSquare size={15} /> : <Square size={15} />}
                        </button>
                      </th>
                      <th className="w-28 px-3 py-2 text-label-sm text-on-surface-variant/80">ID</th>
                      <th className="w-28 px-3 py-2 text-label-sm text-on-surface-variant/80">Patient</th>
                      {filterOptions?.has_note_type && (
                        <th className="w-40 px-3 py-2 text-label-sm text-on-surface-variant/80">Type</th>
                      )}
                      <th className="w-28 px-3 py-2 text-label-sm text-on-surface-variant/80">Date</th>
                      <th className="w-52 px-3 py-2 text-label-sm text-on-surface-variant/80">Author</th>
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
                          <td className="px-3 py-2 mono truncate">{note.id}</td>
                          <td className="px-3 py-2 mono truncate text-on-surface-variant">
                            {note.patient_id || '—'}
                          </td>
                          {filterOptions?.has_note_type && (
                            <td className="px-3 py-2 truncate">
                              {note.note_type ? (
                                <span className="badge-neutral">{note.note_type}</span>
                              ) : (
                                <span className="text-on-surface-variant">—</span>
                              )}
                            </td>
                          )}
                          <td className="px-3 py-2 text-body-md tabular truncate">
                            {note.date || '—'}
                          </td>
                          <td className="px-3 py-2 text-body-md truncate" title={note.author ?? ''}>
                            {note.author || '—'}
                          </td>
                          <td className="px-3 py-2 text-body-md text-on-surface-variant truncate">
                            {note.text_preview?.replace(/\s+/g, ' ') || '—'}
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
                      onClick={() => loadNotes(page - 1, appliedFilters)}
                      disabled={page <= 1}
                      className="btn-outlined py-1.5 px-2.5"
                    >
                      <ChevronLeft size={14} /> Previous
                    </button>
                    <button
                      onClick={() => loadNotes(page + 1, appliedFilters)}
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
                      {previewNote.note_type && (
                        <div className="col-span-2">
                          <dt className="text-label-sm text-on-surface-variant/80">Type</dt>
                          <dd>
                            <span className="badge-neutral">{previewNote.note_type}</span>
                          </dd>
                        </div>
                      )}
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

        {/* ── Step 3: the draft this produced ── */}
        {run && (
          <StepPanel
            index={3}
            title="Review"
            status="done"
            summary={
              <span className="flex items-center gap-1.5">
                <RunStatusChip status={runProgress(run).status} />
                {run.rows.length} row{run.rows.length === 1 ? '' : 's'}
                <span className="text-outline">·</span>
                {runProgress(run).pending} pending
                <span className="text-outline">·</span>
                {relativeTime(run.created_at)}
              </span>
            }
            actions={
              <>
                <button onClick={() => setShowResult(true)} className="btn-outlined">
                  <ClipboardCheck size={14} />
                  Open review
                </button>
                <Link to={`/review?run=${run.id}`} className="btn-text">
                  All runs
                </Link>
              </>
            }
          >
            <p className="text-body-md text-on-surface-variant">
              Saved on the server as a draft — nothing here has been approved yet.
              Correct what the model got wrong, then sign it off; only signed-off rows
              export as reviewed data.
            </p>
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

      {run && showResult && (
        <RunDialog
          run={run}
          onRunChange={setRun}
          onClose={() => setShowResult(false)}
          canReview={canExtract}
        />
      )}
    </div>
  );
}
