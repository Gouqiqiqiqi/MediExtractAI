/**
 * Demo-only control for viewing the app as a different role.
 *
 * Exists because "the flows differ by role" is a claim, and a claim is weaker
 * than letting someone switch and watch the navigation and permissions change
 * in front of them.
 */

import { useEffect, useRef, useState } from 'react';
import { Check, ChevronDown, Eye } from 'lucide-react';
import { useRole } from '../../auth/RoleContext';
import { ROLES, ROLE_BLURB, type Role } from '../../lib/demoRole';

export default function RoleSwitcher() {
  const { role, setRole } = useRole();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [open]);

  const choose = (next: Role) => {
    setRole(next);
    setOpen(false);
    // A role change alters what every page may load. Reloading is blunt but
    // honest — it guarantees nothing from the previous role lingers on screen.
    window.location.reload();
  };

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 px-3 py-2 rounded-gm-xl text-label-md
                   text-on-surface-variant hover:bg-surface-container transition-colors duration-200"
        title="Demo only — switch role to see how the app differs"
      >
        <Eye size={16} />
        <span>
          View as <span className="font-medium text-on-surface">{role}</span>
        </span>
        <ChevronDown size={14} />
      </button>

      {open && (
        <div className="absolute right-0 mt-1 w-80 bg-surface rounded-gm-xl shadow-lg
                        border border-outline/40 py-2 z-50">
          <div className="px-4 py-2 text-label-md text-on-surface-variant">
            Demo only. The API enforces these roles — the 403s are real.
          </div>
          <div className="divider my-1" />
          {ROLES.map((r) => (
            <button
              key={r}
              onClick={() => choose(r)}
              className="w-full text-left px-4 py-2.5 hover:bg-surface-container
                         transition-colors duration-150 flex items-start gap-3"
            >
              <span className="w-4 pt-0.5">
                {r === role && <Check size={16} className="text-gm-blue" />}
              </span>
              <span>
                <span className="block text-label-lg font-medium text-on-surface">{r}</span>
                <span className="block text-label-md text-on-surface-variant">
                  {ROLE_BLURB[r]}
                </span>
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
