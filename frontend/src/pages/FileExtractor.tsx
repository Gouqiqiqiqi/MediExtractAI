/**
 * FileExtractor — upload documents, define a schema, extract.
 *
 * Same three-step shape as the Database Extractor so the two pages teach each
 * other; only the source of the text differs.
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { ClipboardCheck, FileText, Play } from 'lucide-react';
import type { ColumnDefinition, RunDetail } from '../types';
import { extractFromText } from '../api/extraction';
import { errorMessage } from '../api/errors';
import FileUpload from '../components/FileUpload/FileUpload';
import SchemaBuilder from '../components/SchemaBuilder/SchemaBuilder';
import RunDialog from '../components/Review/RunDialog';
import StepPanel from '../components/common/StepPanel';
import { RunStatusChip } from '../components/Review/StatusChip';
import { fetchRun } from '../api/runs';
import { useRole } from '../auth/RoleContext';
import { runProgress } from '../lib/runProgress';
import { runsChanged } from '../lib/runEvents';
import { relativeTime } from '../lib/time';

export default function FileExtractor() {
  const { canExtract } = useRole();
  const [columns, setColumns] = useState<ColumnDefinition[]>([]);
  const [text, setText] = useState('');
  const [filenames, setFilenames] = useState<string[]>([]);
  // The finished run, and whether its table is open over the page. Closing the
  // pop-up keeps the run, so the panel below can offer to reopen it.
  const [run, setRun] = useState<RunDetail | null>(null);
  const [showResult, setShowResult] = useState(false);
  const [extracting, setExtracting] = useState(false);

  const documentLabel = filenames.join(', ') || 'Uploaded text';

  const handleTextExtracted = (extractedText: string, names: string[]) => {
    setText(extractedText);
    setFilenames(names);
    setRun(null);
  };

  const namedColumns = columns.filter((c) => c.name.trim());
  const schemaReady = namedColumns.length > 0 && namedColumns.length === columns.length;
  const hasText = text.trim().length > 0;
  const canRun = hasText && schemaReady && !extracting;

  const runExtraction = async () => {
    if (!hasText) return toast.error('Upload at least one file first');
    if (!schemaReady) return toast.error('Every column needs a name');

    setExtracting(true);
    try {
      const res = await extractFromText({
        text,
        columns,
        source_name: filenames.join(', ') || undefined,
      });
      // The backend has already saved this as a draft run; reading it back is
      // what gives every row its identity, so a correction made in the pop-up
      // is the same edit the review page would make.
      setRun(await fetchRun(res.run_id));
      setShowResult(true);
      runsChanged();
    } catch (err) {
      toast.error(errorMessage(err, 'Extraction failed — check the API logs'), {
        duration: 8000,
      });
    } finally {
      setExtracting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto pb-20">
      <div className="mb-4">
        <h1 className="page-title">File Extractor</h1>
        <p className="page-subtitle">
          Upload <span className="mono">.txt</span>, <span className="mono">.docx</span> or{' '}
          <span className="mono">.pdf</span> documents and tabulate their contents.
        </p>
      </div>

      <div className="space-y-4">
        <StepPanel
          index={1}
          title="Documents"
          status={hasText ? 'done' : 'active'}
          summary={
            hasText
              ? `${documentLabel} · ${text.length.toLocaleString()} characters`
              : 'Nothing uploaded yet'
          }
        >
          <FileUpload onTextExtracted={handleTextExtracted} multiple />

          {hasText && (
            <details className="mt-3 group">
              <summary
                className="flex items-center gap-1.5 cursor-pointer text-label-lg text-on-surface-variant
                           hover:text-on-surface transition-colors select-none"
              >
                <FileText size={14} />
                Show extracted text
              </summary>
              <pre
                className="mt-2 text-body-md whitespace-pre-wrap bg-surface-dim border border-outline
                           rounded-gm-md p-3 max-h-80 overflow-auto text-on-surface leading-relaxed"
              >
                {text}
              </pre>
            </details>
          )}
        </StepPanel>

        <StepPanel
          index={2}
          title="Output schema"
          status={schemaReady ? 'done' : hasText ? 'active' : 'todo'}
          summary={
            columns.length === 0
              ? 'What columns do you want?'
              : `${columns.length} column${columns.length === 1 ? '' : 's'}${
                  schemaReady ? '' : ' · some unnamed'
                }`
          }
          flush
        >
          <SchemaBuilder columns={columns} onChange={setColumns} />
        </StepPanel>

        {run && (
          <StepPanel
            index={3}
            title="Review"
            status="done"
            summary={
              <span className="flex items-center gap-1.5">
                <RunStatusChip status={runProgress(run).status} />
                {run.rows.length} row{run.rows.length === 1 ? '' : 's'}
                <span className="text-outline">·</span>
                {runProgress(run).pending} pending
                <span className="text-outline">·</span>
                {relativeTime(run.created_at)}
              </span>
            }
            actions={
              <>
                <button onClick={() => setShowResult(true)} className="btn-outlined">
                  <ClipboardCheck size={14} />
                  Open review
                </button>
                <Link to={`/review?run=${run.id}`} className="btn-text">
                  All runs
                </Link>
              </>
            }
          >
            <p className="text-body-md text-on-surface-variant">
              Saved on the server as a draft — nothing here has been approved yet.
              These rows came from an uploaded file, so their provenance is a filename:
              there is no source system to read the original back from.
            </p>
          </StepPanel>
        )}
      </div>

      <div className="fixed bottom-0 left-60 right-0 border-t border-outline bg-surface/95 backdrop-blur-sm z-20">
        <div className="max-w-6xl mx-auto px-6 py-2.5 flex items-center gap-4">
          <p className="text-label-md text-on-surface-variant tabular">
            {hasText ? `${text.length.toLocaleString()} characters` : 'No document'}
            <span className="mx-1.5 text-outline">×</span>
            {namedColumns.length} column{namedColumns.length === 1 ? '' : 's'}
            {!schemaReady && columns.length > 0 && (
              <span className="ml-2 text-gm-yellow">every column needs a name</span>
            )}
          </p>
          <div className="flex-1" />
          <button onClick={runExtraction} disabled={!canRun} className="btn-filled">
            {extracting ? (
              <>
                <span className="w-3.5 h-3.5 rounded-full border-2 border-white/40 border-t-white animate-spin" />
                Extracting…
              </>
            ) : (
              <>
                <Play size={14} />
                Run extraction
              </>
            )}
          </button>
        </div>
      </div>

      {run && showResult && (
        <RunDialog
          run={run}
          onRunChange={setRun}
          onClose={() => setShowResult(false)}
          canReview={canExtract}
        />
      )}
    </div>
  );
}
