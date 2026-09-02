/**
 * Getting a run out of the system.
 *
 * The scope selector is the honest part: a run that has not been signed off can
 * still be exported — refusing outright only drives people to screenshots and
 * retyping, which is the same data leaving with none of the caveats. What it
 * cannot do is come out looking reviewed. The server names the file (DRAFT or
 * approved), stamps a review-status column on every draft row, and records the
 * export in the audit trail; this component only says which scope was asked for.
 */

import { useState } from 'react';
import toast from 'react-hot-toast';
import { Download, FileSpreadsheet } from 'lucide-react';
import { exportRunCsv, exportRunExcel, type ExportScope } from '../../api/export';
import { errorMessageAsync } from '../../api/errors';
import type { RunDetail } from '../../types';
import { runProgress } from '../../lib/runProgress';

export default function ExportButtons({ run }: { run: RunDetail }) {
  const progress = runProgress(run);
  const signedOff = progress.status === 'approved';
  // Default to the safest thing that will actually produce a file.
  const [scope, setScope] = useState<ExportScope>(
    progress.approved > 0 ? 'approved' : 'all',
  );
  const [busy, setBusy] = useState(false);

  // Signing off is usually done with this panel already on screen — in the
  // pop-up that follows an extraction, it is the button right above these. The
  // selector disappears at that moment, so a scope chosen before the signature
  // must not survive it: it would download the rejected rows too, in a file the
  // server would rightly name DRAFT.
  const effectiveScope: ExportScope = signedOff ? 'approved' : scope;

  const run_export = async (fn: (id: string, scope: ExportScope) => Promise<string>) => {
    setBusy(true);
    try {
      const name = await fn(run.id, effectiveScope);
      toast.success(`Downloaded ${name}`);
    } catch (err) {
      toast.error(await errorMessageAsync(err, 'Export failed'), { duration: 6000 });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      {!signedOff && (
        <select
          value={scope}
          onChange={(e) => setScope(e.target.value as ExportScope)}
          className="select-field py-1.5 w-auto"
          aria-label="What to export"
        >
          <option value="approved" disabled={progress.approved === 0}>
            Approved rows only{progress.approved === 0 ? ' (none yet)' : ''}
          </option>
          <option value="all">Everything — marked as draft</option>
        </select>
      )}
      <button
        onClick={() => void run_export(exportRunCsv)}
        disabled={busy}
        className="btn-outlined"
      >
        <Download size={14} />
        CSV
      </button>
      <button
        onClick={() => void run_export(exportRunExcel)}
        disabled={busy}
        className="btn-outlined"
      >
        <FileSpreadsheet size={14} />
        Excel
      </button>
    </div>
  );
}
