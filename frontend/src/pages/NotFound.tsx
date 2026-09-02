import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="flex h-screen items-center justify-center bg-surface-dim px-6">
      <div className="text-center">
        <p className="text-label-sm text-on-surface-variant/80">Error 404</p>
        <h1 className="text-display-md text-on-surface mt-1">Page not found</h1>
        <p className="text-body-lg text-on-surface-variant mt-2">
          That route does not exist in MediExtractAI.
        </p>
        <Link to="/" className="btn-filled mt-5">
          <ArrowLeft size={14} />
          Back to dashboard
        </Link>
      </div>
    </div>
  );
}
