/**
 * One numbered step of a workflow.
 *
 * The extractor pages are a sequence — define a schema, choose notes, run it —
 * but they used to render as three cards of equal weight with no indication of
 * order, of what was already done, or of what was blocking the next step. The
 * status here is derived from real state, so the tick marks are not decoration:
 * they say the step is genuinely satisfied.
 */

import type { ReactNode } from 'react';
import { Check } from 'lucide-react';

export type StepStatus = 'todo' | 'active' | 'done';

interface Props {
  index: number;
  title: string;
  /** Short summary of what this step currently holds, e.g. "4 columns". */
  summary?: ReactNode;
  status: StepStatus;
  /** Rendered on the right of the header — usually an action button. */
  actions?: ReactNode;
  children: ReactNode;
  /** Removes the body padding, for panels that render their own table. */
  flush?: boolean;
}

const MARKER: Record<StepStatus, string> = {
  done: 'bg-gm-green text-white border-gm-green',
  active: 'bg-gm-blue text-white border-gm-blue',
  todo: 'bg-surface text-on-surface-variant border-outline',
};

export default function StepPanel({
  index,
  title,
  summary,
  status,
  actions,
  children,
  flush = false,
}: Props) {
  return (
    <section className="panel">
      <header className="panel-header">
        <div className="flex items-center gap-2.5 min-w-0">
          <span
            className={`w-5 h-5 shrink-0 rounded-full border flex items-center justify-center
                        text-label-sm tabular ${MARKER[status]}`}
          >
            {status === 'done' ? <Check size={12} strokeWidth={3} /> : index}
          </span>
          <h2
            className={`text-title-lg truncate ${
              status === 'todo' ? 'text-on-surface-variant' : 'text-on-surface'
            }`}
          >
            {title}
          </h2>
          {summary && (
            <span className="text-label-md text-on-surface-variant truncate">
              {summary}
            </span>
          )}
        </div>
        {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
      </header>
      <div className={flush ? '' : 'panel-body'}>{children}</div>
    </section>
  );
}
