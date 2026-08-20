/**
 * NoteViewer — displays a medical note's text (read-only, scrollable).
 */

interface Props {
  text: string;
  title?: string;
}

export default function NoteViewer({ text, title }: Props) {
  if (!text) {
    return (
      <div className="card-elevated text-center py-8 text-body-md text-on-surface-variant">
        No note text to display.
      </div>
    );
  }

  return (
    <div className="card-elevated">
      {title && (
        <h4 className="text-label-lg font-medium text-on-surface-variant mb-2">{title}</h4>
      )}
      <pre className="text-body-md whitespace-pre-wrap bg-surface-container p-4 rounded-gm-sm max-h-96 overflow-auto text-on-surface leading-relaxed">
        {text}
      </pre>
    </div>
  );
}
