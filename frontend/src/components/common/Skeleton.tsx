/**
 * Placeholder rows shown while data loads.
 *
 * A spinner tells you something is happening; a skeleton also tells you what
 * shape it will be, and stops the page jumping when the content lands.
 */

interface Props {
  rows?: number;
  className?: string;
}

export function SkeletonRows({ rows = 4, className = '' }: Props) {
  return (
    <div className={`space-y-2 ${className}`} aria-hidden>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 px-3 py-2.5">
          <div className="skeleton h-4 w-4 shrink-0" />
          <div className="skeleton h-3 w-24 shrink-0" />
          <div className="skeleton h-3 w-20 shrink-0" />
          <div className="skeleton h-3 flex-1" style={{ maxWidth: `${70 - i * 6}%` }} />
        </div>
      ))}
    </div>
  );
}

export function SkeletonBlock({ className = '' }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-hidden />;
}
