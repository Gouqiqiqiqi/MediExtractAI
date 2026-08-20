/**
 * Loading spinner / skeleton indicator.
 */

import { Loader2 } from 'lucide-react';

interface Props {
  message?: string;
  fullPage?: boolean;
}

export default function Loading({ message = 'Loading...', fullPage = false }: Props) {
  const content = (
    <div className="flex flex-col items-center justify-center gap-3 py-12">
      <Loader2 size={32} className="text-gm-blue animate-spin" />
      <p className="text-body-md text-on-surface-variant">{message}</p>
    </div>
  );

  if (fullPage) {
    return <div className="h-full flex items-center justify-center">{content}</div>;
  }
  return content;
}
