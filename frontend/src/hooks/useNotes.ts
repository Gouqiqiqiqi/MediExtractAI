/**
 * useNotes — hook wrapping the notes API with pagination.
 */

import { useState, useCallback } from 'react';
import type { NotePreview } from '../types';
import { fetchNotes } from '../api/notes';

export function useNotes(pageSize = 20) {
  const [notes, setNotes] = useState<NotePreview[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (p = 1, search?: string) => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchNotes(p, pageSize, search);
        setNotes(data.items);
        setTotal(data.total);
        setPage(p);
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Failed to load notes';
        setError(msg);
      } finally {
        setLoading(false);
      }
    },
    [pageSize],
  );

  return { notes, total, page, loading, error, load };
}
