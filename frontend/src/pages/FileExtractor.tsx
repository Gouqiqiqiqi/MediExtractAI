/**
 * FileExtractor — upload multiple files, define schema, extract structured data.
 */

import { useState } from 'react';
import toast from 'react-hot-toast';
import { Play } from 'lucide-react';
import type { ColumnDefinition, ExtractionResponse } from '../types';
import { extractFromText } from '../api/extraction';
import FileUpload from '../components/FileUpload/FileUpload';
import SchemaBuilder from '../components/SchemaBuilder/SchemaBuilder';
import NoteViewer from '../components/NoteViewer/NoteViewer';
import DataTable from '../components/DataTable/DataTable';
import { saveResult } from '../lib/resultStore';

export default function FileExtractor() {
  const [columns, setColumns] = useState<ColumnDefinition[]>([]);
  const [text, setText] = useState('');
  const [filename, setFilename] = useState('');
  const [result, setResult] = useState<ExtractionResponse | null>(null);
  const [extracting, setExtracting] = useState(false);

  const handleTextExtracted = (extractedText: string, name: string) => {
    setText(extractedText);
    setFilename(name);
    setResult(null);
  };

  const runExtraction = async () => {
    if (!text.trim()) {
      toast.error('Upload at least one file first');
      return;
    }
    if (columns.length === 0 || columns.some((c) => !c.name.trim())) {
      toast.error('Define at least one named column');
      return;
    }

    setExtracting(true);
    try {
      const res = await extractFromText({
        text,
        columns,
        source_name: filename || undefined,
      });
      setResult(res);
      saveResult(res);
      toast.success(`Extracted ${res.rows.length} rows`);
    } catch {
      toast.error('Extraction failed — check API logs');
    } finally {
      setExtracting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <h1 className="text-display-sm font-bold text-on-surface">File Extractor</h1>

      {/* Step 1: Upload (multi-file) */}
      <FileUpload onTextExtracted={handleTextExtracted} multiple />

      {/* Preview */}
      {text && (
        <NoteViewer text={text} title={`Combined text from: ${filename}`} />
      )}

      {/* Step 2: Schema */}
      <SchemaBuilder columns={columns} onChange={setColumns} />

      {/* Step 3: Extract */}
      <div className="flex justify-end">
        <button
          onClick={runExtraction}
          disabled={extracting || !text.trim() || columns.length === 0}
          className="btn-filled flex items-center gap-2"
        >
          {extracting ? (
            <>Extracting...</>
          ) : (
            <>
              <Play size={16} />
              Extract Data
            </>
          )}
        </button>
      </div>

      {/* Step 4: Results */}
      {result && (
        <DataTable
          columns={result.columns}
          data={result.rows}
          readOnlyColumns={result.provenance_columns}
        />
      )}
    </div>
  );
}
