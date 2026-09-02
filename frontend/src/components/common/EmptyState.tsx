/**
 * The state a panel is in most often before anyone has done anything.
 *
 * Says what to do next rather than only that nothing is here — an empty screen
 * with no instruction is where a first-time user stalls.
 */

import type { LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';

interface Props {
  icon?: LucideIcon;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  compact?: boolean;
}

export default function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  compact = false,
}: Props) {
  return (
    <div className={`text-center ${compact ? 'py-8' : 'py-14'} px-6`}>
      {Icon && (
        <div
          className="w-9 h-9 mx-auto mb-3 rounded-gm-lg bg-surface-container
                     flex items-center justify-center"
        >
          <Icon size={18} className="text-on-surface-variant" />
        </div>
      )}
      <p className="text-title-md text-on-surface">{title}</p>
      {description && (
        <p className="text-body-md text-on-surface-variant mt-1.5 max-w-md mx-auto">
          {description}
        </p>
      )}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}
