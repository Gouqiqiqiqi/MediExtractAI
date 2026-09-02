/**
 * Filters for the note browser.
 *
 * Ordered the way a clinician actually narrows down to a note: kind of note
 * first, then who wrote it, then when. Free-text search is last because it is
 * the fallback, not the opening move — in a system where nursing, outpatient
 * and inpatient notes all sit together, "show me this month's respiratory
 * clinic letters" is the query, and a keyword only helps once you are already
 * close.
 */

import { Filter, Search, X } from 'lucide-react';
import type { NoteFilterOptions, NoteFilters } from '../../types';

interface Props {
  options: NoteFilterOptions | null;
  filters: NoteFilters;
  onChange: (filters: NoteFilters) => void;
  onApply: () => void;
  onReset: () => void;
  disabled?: boolean;
}

export const EMPTY_FILTERS: NoteFilters = {
  search: '',
  noteType: '',
  author: '',
  dateFrom: '',
  dateTo: '',
};

export function activeFilterCount(filters: NoteFilters): number {
  return Object.values(filters).filter((v) => v !== '').length;
}

export default function NoteFilterBar({
  options,
  filters,
  onChange,
  onApply,
  onReset,
  disabled = false,
}: Props) {
  const set = (patch: Partial<NoteFilters>) => onChange({ ...filters, ...patch });
  const active = activeFilterCount(filters);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    onApply();
  };

  return (
    <form
      onSubmit={submit}
      className="flex flex-wrap items-end gap-2 px-4 py-3 border-b border-outline bg-surface-dim"
    >
      <span className="flex items-center gap-1.5 text-label-md text-on-surface-variant pb-2 mr-1">
        <Filter size={14} />
        Filter
      </span>

      {options?.has_note_type && (
        <label className="block">
          <span className="label">Note type</span>
          <select
            value={filters.noteType}
            onChange={(e) => set({ noteType: e.target.value })}
            disabled={disabled}
            className="select-field py-1.5 w-44"
          >
            <option value="">All types</option>
            {options.note_types.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
      )}

      <label className="block">
        <span className="label">Clinician</span>
        <select
          value={filters.author}
          onChange={(e) => set({ author: e.target.value })}
          disabled={disabled}
          className="select-field py-1.5 w-52"
        >
          <option value="">Anyone</option>
          {(options?.authors ?? []).map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
      </label>

      <label className="block">
        <span className="label">From</span>
        <input
          type="date"
          value={filters.dateFrom}
          onChange={(e) => set({ dateFrom: e.target.value })}
          disabled={disabled}
          className="input-field py-1.5 w-36"
        />
      </label>

      <label className="block">
        <span className="label">To</span>
        <input
          type="date"
          value={filters.dateTo}
          onChange={(e) => set({ dateTo: e.target.value })}
          disabled={disabled}
          className="input-field py-1.5 w-36"
        />
      </label>

      <label className="block flex-1 min-w-[12rem]">
        <span className="label">Contains</span>
        <div className="relative">
          <Search
            size={14}
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-on-surface-variant pointer-events-none"
          />
          <input
            type="search"
            value={filters.search}
            onChange={(e) => set({ search: e.target.value })}
            disabled={disabled}
            placeholder="Keyword in the note text"
            className="input-field py-1.5 pl-8"
          />
        </div>
      </label>

      <button type="submit" disabled={disabled} className="btn-filled">
        Apply
      </button>
      {active > 0 && (
        <button type="button" onClick={onReset} disabled={disabled} className="btn-text">
          <X size={14} />
          Clear {active}
        </button>
      )}
    </form>
  );
}
