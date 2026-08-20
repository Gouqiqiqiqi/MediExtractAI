/**
 * Modal — accessible overlay dialog.
 */

import { type ReactNode, useEffect, useRef } from 'react';
import { X } from 'lucide-react';

interface Props {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}

export default function Modal({ open, onClose, title, children }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (open) {
      dialog.showModal();
    } else {
      dialog.close();
    }
  }, [open]);

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      className="rounded-lg shadow-xl border-0 p-0 backdrop:bg-black/40 max-w-2xl w-full"
    >
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-nhs-dark-grey">{title}</h3>
        <button onClick={onClose} className="text-nhs-grey hover:text-nhs-dark-grey transition-colors">
          <X size={20} />
        </button>
      </div>
      <div className="p-6">{children}</div>
    </dialog>
  );
}
