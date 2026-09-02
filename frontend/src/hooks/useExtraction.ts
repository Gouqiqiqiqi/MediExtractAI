/**
 * useExtraction — hook wrapping the extraction API with loading/error state.
 */

import { useState, useCallback } from 'react';
import type {
  ColumnDefinition,
  ExtractionResponse,
} from '../types';
import { extractFromDatabase, extractFromText } from '../api/extraction';
import { saveResult } from '../lib/resultStore';

export function useExtraction() {
  const [result, setResult] = useState<ExtractionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const extractDb = useCallback(
    async (noteIds: string[], columns: ColumnDefinition[]) => {
      setLoading(true);
      setError(null);
      try {
        const res = await extractFromDatabase({ note_ids: noteIds, columns });
        setResult(res);
        saveResult(res); // persist for the Results page
        return res;
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Extraction failed';
        setError(msg);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const extractText = useCallback(
    async (text: string, columns: ColumnDefinition[]) => {
      setLoading(true);
      setError(null);
      try {
        const res = await extractFromText({ text, columns });
        setResult(res);
        saveResult(res);
        return res;
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Extraction failed';
        setError(msg);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  return { result, loading, error, extractDb, extractText };
}
