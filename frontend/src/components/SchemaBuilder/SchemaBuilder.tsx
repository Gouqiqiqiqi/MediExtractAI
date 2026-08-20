/**
 * SchemaBuilder — lets users define output columns (name, type, description).
 */

import { Plus } from 'lucide-react';
import type { ColumnDefinition } from '../../types';
import ColumnEditor from './ColumnEditor';

interface Props {
  columns: ColumnDefinition[];
  onChange: (columns: ColumnDefinition[]) => void;
}

const EMPTY_COLUMN: ColumnDefinition = {
  name: '',
  data_type: 'text',
  description: '',
  required: false,
};

export default function SchemaBuilder({ columns, onChange }: Props) {
  const addColumn = () => {
    onChange([...columns, { ...EMPTY_COLUMN }]);
  };

  const updateColumn = (index: number, updated: ColumnDefinition) => {
    const next = [...columns];
    next[index] = updated;
    onChange(next);
  };

  const removeColumn = (index: number) => {
    onChange(columns.filter((_, i) => i !== index));
  };

  return (
    <div className="card-elevated">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-title-md font-semibold text-on-surface">
          Output Schema
        </h3>
        <button onClick={addColumn} className="btn-tonal text-label-md flex items-center gap-1.5">
          <Plus size={16} />
          Add Column
        </button>
      </div>

      {columns.length === 0 ? (
        <div className="text-center py-10">
          <div className="w-12 h-12 mx-auto rounded-gm-xl bg-surface-container flex items-center justify-center mb-3">
            <Plus size={24} className="text-on-surface-variant" />
          </div>
          <p className="text-body-md text-on-surface-variant">
            No columns defined. Click "Add Column" to start building your schema.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {/* Header */}
          <div className="grid grid-cols-12 gap-2 text-label-md font-medium text-on-surface-variant px-2">
            <div className="col-span-1"></div>
            <div className="col-span-3">Column Name</div>
            <div className="col-span-2">Data Type</div>
            <div className="col-span-4">Description</div>
            <div className="col-span-1">Required</div>
            <div className="col-span-1"></div>
          </div>

          {/* Rows */}
          {columns.map((col, i) => (
            <ColumnEditor
              key={i}
              column={col}
              onChange={(updated) => updateColumn(i, updated)}
              onRemove={() => removeColumn(i)}
            />
          ))}
        </div>
      )}

      {/* Presets */}
      <div className="mt-4 pt-4 border-t border-outline/30">
        <p className="text-label-md text-on-surface-variant mb-2">Quick presets:</p>
        <div className="flex gap-2 flex-wrap">
          {PRESETS.map((preset) => (
            <button
              key={preset.label}
              onClick={() => onChange(preset.columns)}
              className="chip"
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Common extraction presets ──

const PRESETS: { label: string; columns: ColumnDefinition[] }[] = [
  {
    label: 'General Clinical',
    columns: [
      { name: 'Diagnosis', data_type: 'text', description: 'Primary diagnosis', required: true },
      { name: 'Symptoms', data_type: 'text[]', description: 'Reported symptoms', required: false },
      { name: 'Medications', data_type: 'text[]', description: 'Prescribed medications', required: false },
      { name: 'Follow_Up_Date', data_type: 'date', description: 'Next appointment date', required: false },
    ],
  },
  {
    label: 'Vital Signs',
    columns: [
      { name: 'BP_Systolic', data_type: 'integer', description: 'Systolic blood pressure (mmHg)', required: true },
      { name: 'BP_Diastolic', data_type: 'integer', description: 'Diastolic blood pressure (mmHg)', required: true },
      { name: 'Heart_Rate', data_type: 'integer', description: 'Heart rate (bpm)', required: false },
      { name: 'Temperature', data_type: 'float', description: 'Temperature (°C)', required: false },
      { name: 'SpO2', data_type: 'integer', description: 'Oxygen saturation (%)', required: false },
    ],
  },
  {
    label: 'Medication Review',
    columns: [
      { name: 'Drug_Name', data_type: 'text', description: 'Medication name', required: true },
      { name: 'Dose', data_type: 'text', description: 'Dosage', required: true },
      { name: 'Frequency', data_type: 'text', description: 'How often taken', required: false },
      { name: 'Route', data_type: 'text', description: 'Route of administration', required: false },
      { name: 'Indication', data_type: 'text', description: 'Reason for medication', required: false },
    ],
  },
];
