/** Inline spinner for in-flight work. */

interface Props {
  message?: string;
  fullPage?: boolean;
  className?: string;
}

export default function Loading({
  message = 'Loading…',
  fullPage = false,
  className = '',
}: Props) {
  const content = (
    <div className={`flex items-center justify-center gap-2.5 py-10 ${className}`}>
      <span
        className="w-4 h-4 rounded-full border-2 border-outline border-t-gm-blue animate-spin"
        aria-hidden
      />
      <span className="text-body-md text-on-surface-variant">{message}</span>
    </div>
  );

  if (fullPage) {
    return <div className="h-full flex items-center justify-center">{content}</div>;
  }
  return content;
}
