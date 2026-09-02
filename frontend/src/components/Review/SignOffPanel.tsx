/**
 * Sign-off — the moment a draft becomes reviewed data.
 *
 * The batch button says what it does. "Approve the remaining 14" is a truthful
 * description of a real and necessary action; a single button that silently
 * approved everything under the label "Approve" would put a clinician's name
 * against rows nobody read, and at a few thousand rows that is the common case
 * rather than the exception. The server records which of the two happened.
 */

import { useState } from 'react';
import toast from 'react-hot-toast';
import { CheckCheck, RotateCcw, ShieldCheck, XCircle } from 'lucide-react';
import { approveRun, rejectRun, reopenRun } from '../../api/runs';
import { errorMessage } from '../../api/errors';
import type { RunDetail } from '../../types';
import { runProgress } from '../../lib/runProgress';
import { runsChanged } from '../../lib/runEvents';
import { formatRunTime } from '../../lib/time';

interface Props {
  run: RunDetail;
  onRunChange: (run: RunDetail) => void;
  /** False for a role that may read but not review. */
  canReview: boolean;
}

export default function SignOffPanel({ run, onRunChange, canReview }: Props) {
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState('');
  const progress = runProgress(run);

  const act = async (action: () => Promise<RunDetail>, success: string) => {
    setBusy(true);
    try {
      onRunChange(await action());
      setNote('');
      runsChanged();
      toast.success(success);
    } catch (err) {
      toast.error(errorMessage(err, 'That could not be recorded'), { duration: 6000 });
    } finally {
      setBusy(false);
    }
  };

  if (progress.status === 'approved') {
    return (
      <div className="card px-4 py-3 flex flex-wrap items-center justify-between gap-3 border-gm-green/30 bg-gm-green-light/40">
        <div className="flex items-start gap-2.5 min-w-0">
          <ShieldCheck size={16} className="text-gm-green shrink-0 mt-0.5" />
          <div className="min-w-0">
            <p className="text-title-sm text-on-surface">
              Signed off by {run.approved_by}
              {run.approved_at && ` · ${formatRunTime(run.approved_at)}`}
            </p>
            <p className="text-label-md text-on-surface-variant">
              {progress.approved} row{progress.approved === 1 ? '' : 's'} approved
              {progress.rejected > 0 && `, ${progress.rejected} rejected`}
              {run.sign_off_note && ` · “${run.sign_off_note}”`}
              <span className="mx-1.5 text-outline">·</span>
              read-only until reopened
            </p>
          </div>
        </div>
        {canReview && (
          <button
            onClick={() => void act(() => reopenRun(run.id, note), 'Run reopened for review')}
            disabled={busy}
            className="btn-outlined"
          >
            <RotateCcw size={14} />
            Reopen
          </button>
        )}
      </div>
    );
  }

  if (progress.status === 'rejected') {
    return (
      <div className="card px-4 py-3 border-gm-red/30 bg-gm-red-light/40">
        <p className="text-title-sm text-on-surface">This run was rejected</p>
        <p className="text-label-md text-on-surface-variant">
          {run.sign_off_note || 'Kept as a record — a bad run is a finding, not a mistake to erase.'}
        </p>
      </div>
    );
  }

  if (!canReview) {
    return (
      <div className="card px-4 py-3">
        <p className="text-label-md text-on-surface-variant">
          This run has not been signed off. Your role can read it, but only a clinician
          can approve rows or sign the run off.
        </p>
      </div>
    );
  }

  return (
    <div className="card px-4 py-3 space-y-2.5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-label-md text-on-surface-variant tabular">
          <span className="text-on-surface">{progress.approved}</span> approved
          <span className="mx-1.5 text-outline">·</span>
          <span className={progress.pending > 0 ? 'text-gm-yellow' : ''}>
            {progress.pending} pending
          </span>
          {progress.rejected > 0 && (
            <>
              <span className="mx-1.5 text-outline">·</span>
              {progress.rejected} rejected
            </>
          )}
          {progress.corrected > 0 && (
            <>
              <span className="mx-1.5 text-outline">·</span>
              {progress.corrected} corrected by hand
            </>
          )}
        </p>
        <div className="flex items-center gap-2">
          <button
            onClick={() =>
              void act(
                () => rejectRun(run.id, note || 'Unusable output'),
                'Run marked as rejected',
              )
            }
            disabled={busy}
            className="btn-text hover:text-gm-red"
          >
            <XCircle size={14} />
            Reject run
          </button>
          <button
            onClick={() =>
              void act(
                () => approveRun(run.id, progress.pending > 0, note),
                'Run signed off',
              )
            }
            disabled={busy || progress.total === 0}
            className="btn-filled"
          >
            {progress.pending > 0 ? (
              <>
                <CheckCheck size={14} />
                Approve remaining {progress.pending} &amp; sign off
              </>
            ) : (
              <>
                <ShieldCheck size={14} />
                Sign off {progress.approved} row{progress.approved === 1 ? '' : 's'}
              </>
            )}
          </button>
        </div>
      </div>

      <input
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Sign-off note — what was checked, and how (optional)"
        className="input-field py-1.5"
        maxLength={1000}
      />
    </div>
  );
}
