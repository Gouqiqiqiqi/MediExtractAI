/**
 * One row of the output schema: what to call the column, its type, and — the
 * field that does the real work — a description telling the model what to look
 * for. The description is not documentation; it is the instruction.
 */

import { Trash2 } from 'lucide-react';
import type { ColumnDataType, ColumnDefinition } from '../../types';

interface Props {
  column: ColumnDefinition;
  onChange: (updated: ColumnDefinition) => void;
  onRemove: () => void;
}

const DATA_TYPES: { value: ColumnDataType; label: string }[] = [
  { value: 'text', label: 'Text' },
  { value: 'integer', label: 'Integer' },
  { value: 'float', label: 'Float' },
  { value: 'boolean', label: 'Boolean' },
  { value: 'date', label: 'Date' },
  { value: 'datetime', label: 'DateTime' },
  { value: 'text[]', label: 'Text list' },
];

export default function ColumnEditor({ column, onChange, onRemove }: Props) {
  const update = (patch: Partial<ColumnDefinition>) => onChange({ ...column, ...patch });

  return (
    <div className="grid grid-cols-12 gap-2 items-center px-3 py-2 border-t border-outline
                    hover:bg-surface-dim transition-colors duration-150 group">
      <div className="col-span-3">
        <input
          type="text"
          value={column.name}
          onChange={(e) => update({ name: e.target.value })}
          placeholder="Column name"
          className="input-field py-1.5"
          aria-label="Column name"
        />
      </div>

      <div className="col-span-2">
        <select
          value={column.data_type}
          onChange={(e) => update({ data_type: e.target.value as ColumnDataType })}
          className="select-field py-1.5"
          aria-label="Data type"
        >
          {DATA_TYPES.map((dt) => (
            <option key={dt.value} value={dt.value}>
              {dt.label}
            </option>
          ))}
        </select>
      </div>

      <div className="col-span-6">
        <input
          type="text"
          value={column.description}
          onChange={(e) => update({ description: e.target.value })}
          placeholder="What should the model look for? e.g. “true only if the patient smokes now”"
          className="input-field py-1.5"
          aria-label="Description"
        />
      </div>

      <div className="col-span-1 flex items-center justify-end gap-1">
        <label className="flex items-center" title="Required">
          <input
            type="checkbox"
            checked={column.required}
            onChange={(e) => update({ required: e.target.checked })}
            className="checkbox-gm"
            aria-label="Required"
          />
        </label>
        <button
          onClick={onRemove}
          className="btn-icon w-7 h-7 hover:text-gm-red opacity-0 group-hover:opacity-100
                     focus-visible:opacity-100 transition-opacity"
          title="Remove column"
          aria-label="Remove column"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  );
}
