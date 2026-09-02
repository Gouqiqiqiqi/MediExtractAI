/**
 * Demo-only control for viewing the app as a different role.
 *
 * Exists because "the flows differ by role" is a claim, and a claim is weaker
 * than letting someone switch and watch the navigation and the permissions
 * change in front of them.
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
    const onEsc = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onEsc);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onEsc);
    };
  }, [open]);

  const choose = (next: Role) => {
    if (next === role) {
      setOpen(false);
      return;
    }
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
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex items-center gap-1.5 h-8 px-2.5 rounded-gm-md border border-outline
                   bg-surface text-label-lg text-on-surface-variant
                   hover:bg-surface-container hover:text-on-surface transition-colors duration-150"
        title="Demo only — switch role to see how the app differs"
      >
        <Eye size={14} />
        <span className="hidden md:inline">View as</span>
        <span className="text-on-surface">{role}</span>
        <ChevronDown size={13} className={open ? 'rotate-180 transition-transform' : 'transition-transform'} />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 mt-1.5 w-80 bg-surface rounded-gm-lg shadow-gm-4
                     border border-outline py-1 z-50"
        >
          <p className="px-3 py-2 text-label-md text-on-surface-variant border-b border-outline">
            Demo only. The API enforces these roles — the 403s are real.
          </p>
          {ROLES.map((r) => (
            <button
              key={r}
              role="menuitem"
              onClick={() => choose(r)}
              className="w-full text-left px-3 py-2 hover:bg-surface-container
                         transition-colors duration-150 flex items-start gap-2.5"
            >
              <span className="w-3.5 pt-0.5 shrink-0">
                {r === role && <Check size={14} className="text-gm-blue" />}
              </span>
              <span className="min-w-0">
                <span className="block text-label-lg text-on-surface">{r}</span>
                <span className="block text-label-md text-on-surface-variant mt-0.5">
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
