/**
 * Define the table you want out of the notes.
 *
 * Renders content only — the surrounding panel and its heading belong to the
 * step it sits in, so the same builder drops into both extractor pages without
 * either of them growing a second title.
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
  const addColumn = () => onChange([...columns, { ...EMPTY_COLUMN }]);

  const updateColumn = (index: number, updated: ColumnDefinition) => {
    const next = [...columns];
    next[index] = updated;
    onChange(next);
  };

  const removeColumn = (index: number) => {
    onChange(columns.filter((_, i) => i !== index));
  };

  return (
    <div>
      {/* Presets — the fast path, so they come first. */}
      <div className="flex items-center gap-2 flex-wrap px-4 py-3 border-b border-outline bg-surface-dim">
        <span className="text-label-md text-on-surface-variant">Start from a preset</span>
        {PRESETS.map((preset) => (
          <button key={preset.label} onClick={() => onChange(preset.columns)} className="chip">
            {preset.label}
            <span className="text-on-surface-variant/70">
              {preset.columns.length}
            </span>
          </button>
        ))}
      </div>

      {columns.length === 0 ? (
        <div className="px-4 py-10 text-center">
          <p className="text-body-md text-on-surface-variant">
            No columns yet. Pick a preset above, or add one column at a time.
          </p>
          <button onClick={addColumn} className="btn-outlined mt-3">
            <Plus size={14} />
            Add column
          </button>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-12 gap-2 px-3 py-2 text-label-sm text-on-surface-variant/80">
            <div className="col-span-3">Name</div>
            <div className="col-span-2">Type</div>
            <div className="col-span-6">Extraction instruction</div>
            <div className="col-span-1 text-right pr-8">Req.</div>
          </div>

          {columns.map((col, i) => (
            <ColumnEditor
              key={i}
              column={col}
              onChange={(updated) => updateColumn(i, updated)}
              onRemove={() => removeColumn(i)}
            />
          ))}

          <div className="px-3 py-2.5 border-t border-outline">
            <button onClick={addColumn} className="btn-text">
              <Plus size={14} />
              Add column
            </button>
          </div>
        </>
      )}
    </div>
  );
}

// ── Common extraction presets ──

const PRESETS: { label: string; columns: ColumnDefinition[] }[] = [
  {
    label: 'General clinical',
    columns: [
      { name: 'Diagnosis', data_type: 'text', description: 'Primary diagnosis or clinical impression', required: true },
      { name: 'Symptoms', data_type: 'text[]', description: 'Symptoms the patient reports', required: false },
      { name: 'Medications', data_type: 'text[]', description: 'Medications prescribed at this visit', required: false },
      { name: 'Follow_Up_Date', data_type: 'date', description: 'Next appointment date if stated', required: false },
    ],
  },
  {
    label: 'Vital signs',
    columns: [
      { name: 'BP_Systolic', data_type: 'integer', description: 'Systolic blood pressure (mmHg)', required: true },
      { name: 'BP_Diastolic', data_type: 'integer', description: 'Diastolic blood pressure (mmHg)', required: true },
      { name: 'Heart_Rate', data_type: 'integer', description: 'Heart rate (bpm)', required: false },
      { name: 'Temperature', data_type: 'float', description: 'Temperature (°C)', required: false },
      { name: 'SpO2', data_type: 'integer', description: 'Oxygen saturation (%) on air unless stated', required: false },
    ],
  },
  {
    label: 'Medication review',
    columns: [
      { name: 'Drug_Name', data_type: 'text', description: 'Medication name', required: true },
      { name: 'Dose', data_type: 'text', description: 'Dose including units', required: true },
      { name: 'Frequency', data_type: 'text', description: 'How often, e.g. BD, OD, TDS', required: false },
      { name: 'Route', data_type: 'text', description: 'Route of administration, e.g. PO, IV', required: false },
      { name: 'Indication', data_type: 'text', description: 'Reason the drug was given', required: false },
    ],
  },
  {
    label: 'Smoking & risk',
    columns: [
      { name: 'Current_Smoker', data_type: 'boolean', description: 'True ONLY if the patient smokes now. Ex-smokers are false.', required: true },
      { name: 'Pack_Years', data_type: 'float', description: 'Pack-year history if stated', required: false },
      { name: 'Alcohol_Units_Weekly', data_type: 'float', description: 'Units of alcohol per week if stated', required: false },
    ],
  },
];
