/**
 * EditableCell — inline editing for extraction result cells.
 */

import { useState, useRef, useEffect } from 'react';
import type { ColumnDataType } from '../../types';

interface Props {
  value: unknown;
  onChange: (value: unknown) => void;
  dataType: ColumnDataType;
}

export default function EditableCell({ value, onChange, dataType }: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(formatValue(value, dataType));
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const commit = () => {
    setEditing(false);
    onChange(parseValue(draft, dataType));
  };

  if (editing) {
    return (
      <input
        ref={inputRef}
        type={inputType(dataType)}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => e.key === 'Enter' && commit()}
        className="input-field py-1 px-1.5 text-body-md"
      />
    );
  }

  return (
    <span
      onClick={() => {
        setDraft(formatValue(value, dataType));
        setEditing(true);
      }}
      className="cursor-text hover:bg-gm-blue-light hover:ring-1 hover:ring-gm-blue-surface
                 px-1.5 py-1 -mx-1.5 rounded-gm-sm inline-block min-w-[2rem] min-h-[1.5em]
                 text-body-md text-on-surface transition-colors duration-100"
      title="Click to edit"
    >
      {displayValue(value, dataType)}
    </span>
  );
}

// ── Helpers ──

function formatValue(value: unknown, dataType: ColumnDataType): string {
  if (value === null || value === undefined) return '';
  if (dataType === 'text[]' && Array.isArray(value)) return value.join(', ');
  return String(value);
}

function displayValue(value: unknown, dataType: ColumnDataType): string {
  if (value === null || value === undefined) return '—';
  if (dataType === 'boolean') return value ? '✓' : '✗';
  if (dataType === 'text[]' && Array.isArray(value)) return value.join(', ');
  return String(value);
}

function parseValue(raw: string, dataType: ColumnDataType): unknown {
  if (raw === '') return null;
  switch (dataType) {
    case 'integer':
      return parseInt(raw, 10) || null;
    case 'float':
      return parseFloat(raw) || null;
    case 'boolean':
      return ['true', '1', 'yes'].includes(raw.toLowerCase());
    case 'text[]':
      return raw.split(',').map((s) => s.trim()).filter(Boolean);
    default:
      return raw;
  }
}

function inputType(dataType: ColumnDataType): string {
  switch (dataType) {
    case 'integer':
    case 'float':
      return 'number';
    case 'date':
      return 'date';
    case 'datetime':
      return 'datetime-local';
    default:
      return 'text';
  }
}
