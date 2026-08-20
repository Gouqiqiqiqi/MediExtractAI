import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <div className="flex h-screen items-center justify-center bg-nhs-pale-grey">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-nhs-blue mb-4">404</h1>
        <p className="text-nhs-dark-grey mb-6">Page not found</p>
        <Link to="/" className="btn-primary">
          Back to Dashboard
        </Link>
      </div>
    </div>
  );
}
