/**
 * Route guard — no-op in demo mode (the app is open, synthetic data only).
 */

import { type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

export default function ProtectedRoute({ children }: Props) {
  return <>{children}</>;
}
