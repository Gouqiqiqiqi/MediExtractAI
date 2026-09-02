/**
 * Results — review and export the latest extraction (persisted in sessionStorage).
 */

import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { Download, FileSpreadsheet, FileJson } from 'lucide-react';
import { exportCsv, exportExcel } from '../api/export';
import DataTable from '../components/DataTable/DataTable';
import { loadResult, saveEditedRows, type SavedResult } from '../lib/resultStore';

export default function Results() {
  const [result, setResult] = useState<SavedResult | null>(null);

  useEffect(() => {
    setResult(loadResult());
  }, []);

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
        <h1 className="text-display-sm font-bold text-on-surface mb-6">Results</h1>
        <div className="card-elevated text-center py-16">
          <p className="text-body-md text-on-surface-variant">
            No results yet. Run an extraction from the Database or File Extractor pages.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-display-sm font-bold text-on-surface">Results</h1>
        <div className="flex gap-2">
          <button onClick={handleExportCsv} className="btn-outlined flex items-center gap-2 text-label-md">
            <Download size={16} />
            CSV
          </button>
          <button onClick={handleExportExcel} className="btn-outlined flex items-center gap-2 text-label-md">
            <FileSpreadsheet size={16} />
            Excel
          </button>
          <button
            onClick={() => {
              navigator.clipboard.writeText(JSON.stringify(result, null, 2));
              toast.success('JSON copied to clipboard');
            }}
            className="btn-outlined flex items-center gap-2 text-label-md"
          >
            <FileJson size={16} />
            Copy JSON
          </button>
        </div>
      </div>

      <DataTable
        columns={result.columns}
        data={result.rows}
        readOnlyColumns={result.provenance_columns}
        onDataChange={(rows) => {
          const updated = { ...result, rows };
          setResult(updated);
          saveEditedRows(updated);
        }}
      />
    </div>
  );
}
