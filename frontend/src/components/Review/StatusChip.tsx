/**
 * Where a run, or a single row, stands in review.
 *
 * One vocabulary in one place: "draft" has to look the same in the navigation
 * rail, in the pop-up that follows an extraction, and on the row itself, or a
 * reviewer has to learn the colours twice.
 */

import { Check, CircleDashed, FileEdit, ShieldCheck, X } from 'lucide-react';
import type { RowStatus, RunStatus } from '../../types';

const RUN_STYLE: Record<RunStatus, { label: string; className: string; icon: typeof Check }> = {
  draft: {
    label: 'Draft',
    className: 'badge-warning',
    icon: FileEdit,
  },
  in_review: {
    label: 'In review',
    className: 'badge-info',
    icon: CircleDashed,
  },
  approved: {
    label: 'Signed off',
    className: 'badge-success',
    icon: ShieldCheck,
  },
  rejected: {
    label: 'Rejected',
    className: 'badge-danger',
    icon: X,
  },
};

export function RunStatusChip({ status }: { status: RunStatus }) {
  const { label, className, icon: Icon } = RUN_STYLE[status];
  return (
    <span className={className}>
      <Icon size={10} strokeWidth={2.5} />
      {label}
    </span>
  );
}

const ROW_STYLE: Record<RowStatus, { label: string; className: string }> = {
  pending: { label: 'Pending', className: 'badge-neutral' },
  approved: { label: 'Approved', className: 'badge-success' },
  rejected: { label: 'Rejected', className: 'badge-danger' },
};

export function RowStatusChip({ status }: { status: RowStatus }) {
  const { label, className } = ROW_STYLE[status];
  return <span className={className}>{label}</span>;
}
