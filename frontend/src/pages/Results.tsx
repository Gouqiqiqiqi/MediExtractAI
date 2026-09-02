/**
 * Results — review, correct and export the latest extraction.
 */

import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { Database, Download, FileJson, FileSpreadsheet, Table2 } from 'lucide-react';
import { exportCsv, exportExcel } from '../api/export';
import DataTable from '../components/DataTable/DataTable';
import EmptyState from '../components/common/EmptyState';
import { loadResult, saveEditedRows, type SavedResult } from '../lib/resultStore';

export default function Results() {
  const [result, setResult] = useState<SavedResult | null>(null);

  useEffect(() => {
    setResult(loadResult());
  }, []);

  // Memoised: a fresh [] each render would change identity every time and
  // defeat DataTable's column memo.
  const provenance = useMemo(
    () => result?.provenance_columns ?? [],
    [result?.provenance_columns],
  );

  const handleExportCsv = async () => {
    if (!result) return;
    try {
      await exportCsv(result);
      toast.success('CSV downloaded');
    } catch {
      toast.error('Export failed');
    }
  };

  const handleExportExcel = async () => {
    if (!result) return;
    try {
      await exportExcel(result);
      toast.success('Excel downloaded');
    } catch {
      toast.error('Export failed');
    }
  };

  if (!result) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="mb-4">
          <h1 className="page-title">Results</h1>
          <p className="page-subtitle">
            Review, correct and export the most recent extraction.
          </p>
        </div>
        <div className="card">
          <EmptyState
            icon={Table2}
            title="Nothing extracted yet"
            description="Run an extraction and the rows will appear here, ready to correct and export."
            action={
              <Link to="/database" className="btn-filled">
                <Database size={14} />
                Go to Database Extractor
              </Link>
            }
          />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-title">Results</h1>
          <p className="page-subtitle tabular">
            {result.rows.length} row{result.rows.length === 1 ? '' : 's'}
            <span className="mx-1.5 text-outline">·</span>
            {result.columns.length} column{result.columns.length === 1 ? '' : 's'}
            {provenance.length > 0 && (
              <>
                <span className="mx-1.5 text-outline">·</span>
                {provenance.length} provenance column
                {provenance.length === 1 ? '' : 's'} (read-only)
              </>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleExportCsv} className="btn-outlined">
            <Download size={14} />
            CSV
          </button>
          <button onClick={handleExportExcel} className="btn-outlined">
            <FileSpreadsheet size={14} />
            Excel
          </button>
          <button
            onClick={() => {
              void navigator.clipboard.writeText(JSON.stringify(result, null, 2));
              toast.success('JSON copied to clipboard');
            }}
            className="btn-outlined"
          >
            <FileJson size={14} />
            Copy JSON
          </button>
        </div>
      </div>

      {provenance.length > 0 && (
        <p className="text-label-md text-on-surface-variant">
          Every row carries the note it came from. Those columns cannot be edited — one
          note can produce several rows, so the link back to the source is a record of
          fact rather than a value to correct.
        </p>
      )}

      <DataTable
        columns={result.columns}
        data={result.rows}
        readOnlyColumns={provenance}
        onDataChange={(rows) => {
          const updated = { ...result, rows };
          setResult(updated);
          saveEditedRows(updated);
        }}
      />
    </div>
  );
}
