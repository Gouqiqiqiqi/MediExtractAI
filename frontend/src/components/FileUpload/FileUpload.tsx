/**
 * FileUpload — drag-and-drop multi-file uploader.
 */

import { useCallback, useState } from 'react';
import { useDropzone, type FileRejection } from 'react-dropzone';
import { Upload, FileText, ScanLine, X, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { uploadFile } from '../../api/upload';
import { errorMessage } from '../../api/errors';
import type { UploadResponse } from '../../types';

interface Props {
  /**
   * Called with every document currently uploaded, in the order they were
   * added. Documents rather than one combined string because a document is
   * not always text: a scan arrives as page images, and the caller has to be
   * able to tell the two apart — to count them, to show them, and because a
   * request carrying images may only go to a model that can read them.
   */
  onDocumentsChange: (documents: UploadResponse[]) => void;
  /** When true, several files may be uploaded and are extracted together. */
  multiple?: boolean;
}

const ACCEPT = {
  'text/plain': ['.txt'],
  'application/pdf': ['.pdf'],
  'application/msword': ['.doc'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
};

const MAX_SIZE = 10 * 1024 * 1024; // 10 MB

export default function FileUpload({ onDocumentsChange, multiple = true }: Props) {
  const [uploading, setUploading] = useState(false);
  const [results, setResults] = useState<UploadResponse[]>([]);

  const onDrop = useCallback(
    async (accepted: File[], rejected: FileRejection[]) => {
      if (rejected.length > 0) {
        toast.error(`${rejected.length} file(s) rejected — check format and size (max 10 MB).`);
      }

      if (accepted.length === 0) return;

      setUploading(true);
      const newResults: UploadResponse[] = [];

      for (const file of accepted) {
        try {
          const response = await uploadFile(file);
          newResults.push(response);
        } catch (err: unknown) {
          // The server says why — an unreadable scan and an unsupported
          // format need different things from the user, and "Upload failed"
          // tells them neither.
          toast.error(`${file.name}: ${errorMessage(err, 'Upload failed')}`, {
            duration: 8000,
          });
        }
      }

      if (newResults.length > 0) {
        const all = [...results, ...newResults];
        setResults(all);
        onDocumentsChange(all);
        const scans = newResults.filter((r) => r.page_images.length > 0).length;
        toast.success(
          scans > 0
            ? `Extracted from ${newResults.length} file(s) — ${scans} read as scanned pages`
            : `Extracted from ${newResults.length} file(s)`,
        );
      }

      setUploading(false);
    },
    [onDocumentsChange, results],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPT,
    maxSize: MAX_SIZE,
    maxFiles: multiple ? 20 : 1,
    disabled: uploading,
  });

  const removeFile = (index: number) => {
    const updated = results.filter((_, i) => i !== index);
    setResults(updated);
    onDocumentsChange(updated);
  };

  const clearAll = () => {
    setResults([]);
    onDocumentsChange([]);
  };

  const totalChars = results.reduce((sum, r) => sum + r.char_count, 0);
  const totalPages = results.reduce((sum, r) => sum + r.page_images.length, 0);

  return (
    <div className="space-y-3">
      {/* Uploaded files */}
      {results.length > 0 && (
        <div className="card divide-y divide-outline-variant">
          {results.map((r, i) => {
            const scanned = r.page_images.length > 0;
            return (
              <div
                key={`${r.filename}-${i}`}
                className="flex items-center gap-2.5 px-3 py-2 group"
              >
                {scanned ? (
                  <ScanLine size={15} className="text-gm-blue shrink-0" />
                ) : (
                  <FileText size={15} className="text-on-surface-variant shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-body-md text-on-surface truncate">{r.filename}</p>
                  <p className="text-label-md text-on-surface-variant tabular">
                    {(r.size_bytes / 1024).toFixed(1)} KB ·{' '}
                    {scanned
                      ? `${r.page_images.length} page${
                          r.page_images.length === 1 ? '' : 's'
                        } read as images`
                      : `${r.char_count.toLocaleString()} characters`}
                  </p>
                </div>
                <button
                  onClick={() => removeFile(i)}
                  className="btn-icon w-7 h-7 hover:text-gm-red opacity-0 group-hover:opacity-100
                             focus-visible:opacity-100 transition-opacity"
                  aria-label={`Remove ${r.filename}`}
                >
                  <X size={14} />
                </button>
              </div>
            );
          })}
          <div className="flex items-center justify-between px-3 py-2 bg-surface-dim">
            <span className="text-label-md text-on-surface-variant tabular">
              {results.length} file{results.length !== 1 ? 's' : ''} ·{' '}
              {totalChars.toLocaleString()} characters
              {totalPages > 0 && ` · ${totalPages} scanned page${totalPages === 1 ? '' : 's'}`}
            </span>
            <button onClick={clearAll} className="btn-text text-gm-red hover:text-gm-red">
              Clear all
            </button>
          </div>
        </div>
      )}

      {/* A scan is read by a different kind of model and transcribed rather
          than parsed, which is worth saying before anyone reads the rows. */}
      {totalPages > 0 && (
        <p className="flex items-start gap-1.5 text-label-md text-on-surface-variant">
          <ScanLine size={13} className="mt-0.5 shrink-0 text-gm-blue" />
          <span>
            {totalPages === 1 ? 'One page has' : `${totalPages} pages have`} no text layer
            and will be read from the image itself. Transcription can be imperfect —
            check these rows in review before approving them.
          </span>
        </p>
      )}

      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`border border-dashed rounded-gm-lg cursor-pointer transition-colors duration-150
                    text-center py-8 px-4 ${
                      isDragActive
                        ? 'border-gm-blue bg-gm-blue-light'
                        : 'border-outline hover:border-gm-blue hover:bg-surface-dim'
                    } ${uploading ? 'opacity-60 cursor-wait' : ''}`}
      >
        <input {...getInputProps()} />
        {uploading ? (
          <Loader2 size={20} className="mx-auto text-gm-blue animate-spin mb-2" />
        ) : (
          <Upload size={20} className="mx-auto text-on-surface-variant mb-2" />
        )}
        <p className="text-title-md text-on-surface">
          {uploading
            ? 'Uploading and extracting text…'
            : isDragActive
              ? 'Drop the files here'
              : results.length > 0
                ? 'Drop more files, or click to browse'
                : 'Drag files here, or click to browse'}
        </p>
        <p className="text-label-md text-on-surface-variant mt-1">
          <span className="mono">.txt</span> <span className="mono">.doc</span>{' '}
          <span className="mono">.docx</span> <span className="mono">.pdf</span> · up to 10 MB each
          {multiple ? ' · multiple files allowed' : ''}
        </p>
      </div>
    </div>
  );
}
