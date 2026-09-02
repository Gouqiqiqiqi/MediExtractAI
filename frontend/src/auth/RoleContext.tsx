/**
 * Current role, shared across the app.
 *
 * In demo mode the role is chosen by the viewer; with real auth it would come
 * from the token. Either way the UI only uses it to decide what to *offer* —
 * the API enforces it independently, so hiding a menu item is a courtesy, not
 * a security boundary.
 */

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { getDemoRole, setDemoRole, type Role } from '../lib/demoRole';

interface RoleContextValue {
  role: Role;
  setRole: (role: Role) => void;
  isAdmin: boolean;
  /** May browse notes and run extractions. */
  canExtract: boolean;
}

const RoleContext = createContext<RoleContextValue | null>(null);

export function RoleProvider({ children }: { children: ReactNode }) {
  const [role, setRoleState] = useState<Role>(getDemoRole);

  const setRole = useCallback((next: Role) => {
    setDemoRole(next);
    setRoleState(next);
  }, []);

  const value = useMemo<RoleContextValue>(
    () => ({
      role,
      setRole,
      isAdmin: role === 'Admin',
      canExtract: role === 'Admin' || role === 'Clinician',
    }),
    [role, setRole],
  );

  return <RoleContext.Provider value={value}>{children}</RoleContext.Provider>;
}

export function useRole(): RoleContextValue {
  const ctx = useContext(RoleContext);
  if (ctx === null) {
    throw new Error('useRole must be used inside a RoleProvider');
  }
  return ctx;
}
