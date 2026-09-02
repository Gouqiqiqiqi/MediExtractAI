/**
 * Which role the demo is being viewed as.
 *
 * Demo mode has no authentication, so there is no token to carry a role. This
 * lets a visitor switch between what an administrator, a clinician and an
 * auditor actually see — the difference is enforced by the API, not faked in
 * the UI, so the 403s are real.
 *
 * Kept outside React state as well as in it: the axios interceptor has to read
 * the current role on every request, and it runs outside the component tree.
 */

export type Role = 'Admin' | 'Clinician' | 'ReadOnly';

export const ROLES: Role[] = ['Admin', 'Clinician', 'ReadOnly'];

export const ROLE_BLURB: Record<Role, string> = {
  Admin: 'Configures data sources and mappings. The deployment engineer.',
  Clinician: 'Browses notes and runs extractions. Never sees a connection string.',
  ReadOnly: 'Can see what exists, but cannot read notes or extract.',
};

const STORAGE_KEY = 'mediextract:demo_role';
const DEFAULT_ROLE: Role = 'Admin';

let current: Role = DEFAULT_ROLE;

try {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored && (ROLES as string[]).includes(stored)) {
    current = stored as Role;
  }
} catch {
  // Private browsing or blocked storage — the in-memory default is fine.
}

export function getDemoRole(): Role {
  return current;
}

export function setDemoRole(role: Role): void {
  current = role;
  try {
    localStorage.setItem(STORAGE_KEY, role);
  } catch {
    // as above
  }
}
