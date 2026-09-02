/**
 * Timestamp formatting for the extraction history.
 *
 * Two forms, because a list of runs needs both: the clock time says which run
 * is which, the relative time says how long ago the newest one was.
 */

/** "14:32" for today, "2 Sep 14:32" otherwise. */
export function formatRunTime(iso: string, now: Date = new Date()): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '—';

  const time = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const sameDay =
    date.getDate() === now.getDate() &&
    date.getMonth() === now.getMonth() &&
    date.getFullYear() === now.getFullYear();

  if (sameDay) return time;
  const day = date.toLocaleDateString([], { day: 'numeric', month: 'short' });
  return `${day} ${time}`;
}

/** "just now", "3 min ago", "2 h ago", then falls back to the clock time. */
export function relativeTime(iso: string, now: Date = new Date()): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '—';

  const seconds = Math.max(0, Math.round((now.getTime() - date.getTime()) / 1000));
  if (seconds < 45) return 'just now';
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 12) return `${hours} h ago`;
  return formatRunTime(iso, now);
}
