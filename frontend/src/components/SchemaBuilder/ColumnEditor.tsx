/**
 * Single column definition row within the SchemaBuilder.
 */

import { GripVertical, Trash2 } from 'lucide-react';
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
  { value: 'text[]', label: 'Text Array' },
];

export default function ColumnEditor({ column, onChange, onRemove }: Props) {
  const update = (patch: Partial<ColumnDefinition>) =>
    onChange({ ...column, ...patch });

  return (
    <div className="grid grid-cols-12 gap-2 items-center bg-surface-container rounded-gm-sm p-2.5 hover:bg-surface-container-high transition-colors">
      {/* Drag handle */}
      <div className="col-span-1 flex justify-center text-on-surface-variant cursor-grab">
        <GripVertical size={16} />
      </div>

      {/* Name */}
      <div className="col-span-3">
        <input
          type="text"
          value={column.name}
          onChange={(e) => update({ name: e.target.value })}
          placeholder="Column name"
          className="input-field text-body-md"
        />
      </div>

      {/* Type */}
      <div className="col-span-2">
        <select
          value={column.data_type}
          onChange={(e) => update({ data_type: e.target.value as ColumnDataType })}
          className="input-field text-body-md"
        >
          {DATA_TYPES.map((dt) => (
            <option key={dt.value} value={dt.value}>
              {dt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Description */}
      <div className="col-span-4">
        <input
          type="text"
          value={column.description}
          onChange={(e) => update({ description: e.target.value })}
          placeholder="What to extract"
          className="input-field text-body-md"
        />
      </div>

      {/* Required */}
      <div className="col-span-1 flex justify-center">
        <input
          type="checkbox"
          checked={column.required}
          onChange={(e) => update({ required: e.target.checked })}
          className="checkbox-gm"
        />
      </div>

      {/* Remove */}
      <div className="col-span-1 flex justify-center">
        <button
          onClick={onRemove}
          className="text-on-surface-variant hover:text-gm-red transition-colors p-1 rounded-gm-sm hover:bg-surface"
          title="Remove column"
        >
          <Trash2 size={16} />
        </button>
      </div>
    </div>
  );
}
