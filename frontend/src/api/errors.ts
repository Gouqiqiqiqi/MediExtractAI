/**
 * Turning an API failure into something worth reading.
 *
 * The backend already explains itself — "All AI models are rate limited —
 * gemini:gemini-3.5-flash (daily quota exhausted, 14320s)" — and throwing that
 * away in favour of "Extraction failed" costs the one piece of information that
 * says whether to wait, retry, or change something. A demo that degrades
 * visibly is worth more than one that fails opaquely.
 */

import { AxiosError } from 'axios';

/** FastAPI puts the message in `detail`, as a string or as validation objects. */
function detailOf(data: unknown): string | null {
  if (typeof data === 'string') return data.trim() || null;
  if (!data || typeof data !== 'object') return null;
  const detail = (data as { detail?: unknown }).detail;
  if (typeof detail === 'string') return detail.trim() || null;
  if (Array.isArray(detail)) {
    // 422 from request validation: [{loc, msg, type}, ...]
    const messages = detail
      .map((d) => (d && typeof d === 'object' ? (d as { msg?: string }).msg : null))
      .filter((m): m is string => Boolean(m));
    if (messages.length) return messages.join('; ');
  }
  return null;
}

export function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof AxiosError) {
    const detail = detailOf(error.response?.data);
    if (detail) return detail;
    // No response at all: the request never landed, or something in front of
    // the app cut it off. Say which, because they need different fixes.
    if (error.code === 'ECONNABORTED') {
      return 'The request timed out before the server answered. Try fewer notes.';
    }
    if (!error.response) return 'Could not reach the API — is the backend up?';
  }
  return fallback;
}
