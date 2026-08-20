/**
 * FileUpload — drag-and-drop multi-file uploader with Google Material styling.
 */

import { useCallback, useState } from 'react';
import { useDropzone, type FileRejection } from 'react-dropzone';
import { Upload, FileText, X, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { uploadFile } from '../../api/upload';
import type { UploadResponse } from '../../types';

interface Props {
  onTextExtracted: (text: string, filename: string) => void;
  /** When true, aggregates all uploaded file texts and calls onTextExtracted with combined text */
  multiple?: boolean;
}

const ACCEPT = {
  'text/plain': ['.txt'],
  'application/pdf': ['.pdf'],
  'application/msword': ['.doc'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
};

const MAX_SIZE = 10 * 1024 * 1024; // 10 MB

export default function FileUpload({ onTextExtracted, multiple = true }: Props) {
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
          const message = err instanceof Error ? err.message : 'Upload failed';
          toast.error(`${file.name}: ${message}`);
        }
      }

      if (newResults.length > 0) {
        const all = [...results, ...newResults];
        setResults(all);
        const combinedText = all.map((r) => r.extracted_text).join('\n\n---\n\n');
        const filenames = all.map((r) => r.filename).join(', ');
        onTextExtracted(combinedText, filenames);
        toast.success(`Extracted from ${newResults.length} file(s)`);
      }

      setUploading(false);
    },
    [onTextExtracted, results],
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
    if (updated.length === 0) {
      onTextExtracted('', '');
    } else {
      const combinedText = updated.map((r) => r.extracted_text).join('\n\n---\n\n');
      const filenames = updated.map((r) => r.filename).join(', ');
      onTextExtracted(combinedText, filenames);
    }
  };

  const clearAll = () => {
    setResults([]);
    onTextExtracted('', '');
  };

  return (
    <div className="card-elevated space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-title-md font-semibold text-on-surface">Upload Files</h3>
        {results.length > 0 && (
          <button onClick={clearAll} className="btn-text text-label-md text-gm-red">
            Clear All
          </button>
        )}
      </div>

      {/* Uploaded files list */}
      {results.length > 0 && (
        <div className="space-y-2">
          {results.map((r, i) => (
            <div
              key={`${r.filename}-${i}`}
              className="flex items-center gap-3 px-4 py-3 bg-surface-container rounded-gm-md group"
            >
              <div className="w-9 h-9 rounded-gm-sm bg-gm-blue-light flex items-center justify-center flex-shrink-0">
                <FileText size={18} className="text-gm-blue" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-body-md text-on-surface font-medium truncate">{r.filename}</p>
                <p className="text-label-md text-on-surface-variant">
                  {(r.size_bytes / 1024).toFixed(1)} KB · {r.char_count.toLocaleString()} chars
                </p>
              </div>
              <button
                onClick={() => removeFile(i)}
                className="text-on-surface-variant hover:text-gm-red transition-colors opacity-0 group-hover:opacity-100"
              >
                <X size={16} />
              </button>
            </div>
          ))}
          <p className="text-label-md text-on-surface-variant">
            {results.length} file{results.length !== 1 ? 's' : ''} ·{' '}
            {results.reduce((sum, r) => sum + r.char_count, 0).toLocaleString()} total characters
          </p>
        </div>
      )}

      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-gm-lg cursor-pointer transition-all duration-200 text-center py-10 ${
          isDragActive
            ? 'border-gm-blue bg-gm-blue-light/50'
            : 'border-outline/60 hover:border-gm-blue hover:bg-surface-container'
        } ${uploading ? 'opacity-50 cursor-wait' : ''}`}
      >
        <input {...getInputProps()} />
        {uploading ? (
          <Loader2 size={36} className="mx-auto text-gm-blue animate-spin mb-3" />
        ) : (
          <div className="w-14 h-14 mx-auto rounded-gm-xl bg-gm-blue-light flex items-center justify-center mb-3">
            <Upload size={24} className="text-gm-blue" />
          </div>
        )}
        <p className="text-title-sm font-medium text-on-surface">
          {uploading
            ? 'Uploading & extracting...'
            : isDragActive
              ? 'Drop files here'
              : results.length > 0
                ? 'Drop more files, or click to browse'
                : 'Drag & drop files, or click to browse'}
        </p>
        <p className="text-label-md text-on-surface-variant mt-1.5">
          Supported: .txt, .doc, .docx, .pdf · Max 10 MB each{multiple ? ' · Multiple files allowed' : ''}
        </p>
      </div>
    </div>
  );
}
