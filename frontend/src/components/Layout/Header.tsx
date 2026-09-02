import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, User } from 'lucide-react';
import { useRole } from '../../auth/RoleContext';
import RoleSwitcher from './RoleSwitcher';

const DISPLAY_NAME: Record<string, string> = {
  Admin: 'Dr Demo Admin',
  Clinician: 'Dr Demo Clinician',
  ReadOnly: 'Demo Auditor',
};

export default function Header() {
  const { role, canExtract } = useRole();
  const navigate = useNavigate();
  const [term, setTerm] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // ⌘K / Ctrl-K, or "/" when not already typing. Only bound when the input is
  // actually rendered — otherwise the shortcut would swallow the keystroke and
  // then have nothing to focus.
  useEffect(() => {
    if (!canExtract) return;
    const onKey = (e: KeyboardEvent) => {
      if (!inputRef.current) return;
      const typing =
        e.target instanceof HTMLElement &&
        ['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName);
      const shortcut =
        (e.key === 'k' && (e.metaKey || e.ctrlKey) && !typing) || (e.key === '/' && !typing);
      if (!shortcut) return;
      e.preventDefault();
      inputRef.current.focus();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [canExtract]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const q = term.trim();
    if (!q) return;
    // Search means "find notes", and notes are browsed in the Database
    // Extractor — so this hands off to that page rather than inventing a
    // second results view that would then have to be kept in step with it.
    navigate(`/database?q=${encodeURIComponent(q)}`);
    setTerm('');
    inputRef.current?.blur();
  };

  return (
    <header className="h-14 shrink-0 bg-surface border-b border-outline flex items-center gap-4 px-4">
      {canExtract ? (
        <form onSubmit={submit} className="relative w-full max-w-md">
          <Search
            size={15}
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-on-surface-variant pointer-events-none"
          />
          <input
            ref={inputRef}
            type="search"
            value={term}
            onChange={(e) => setTerm(e.target.value)}
            placeholder="Search clinical notes…"
            aria-label="Search clinical notes"
            className="w-full h-8 pl-8 pr-12 bg-surface-container border border-transparent
                       rounded-gm-md text-body-md text-on-surface
                       placeholder:text-on-surface-variant/80
                       focus:outline-none focus:bg-surface focus:border-gm-blue
                       focus:ring-2 focus:ring-gm-blue/25 transition-colors duration-150"
          />
          <kbd
            className="kbd absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none
                       hidden sm:inline-flex"
          >
            ⌘K
          </kbd>
        </form>
      ) : (
        <div className="flex-1" />
      )}

      <div className="flex items-center gap-2 ml-auto shrink-0">
        <RoleSwitcher />

        <div className="flex items-center gap-2 pl-2.5 ml-1 border-l border-outline">
          <span
            className="w-7 h-7 rounded-gm-md bg-surface-container border border-outline
                       flex items-center justify-center shrink-0"
          >
            <User size={14} className="text-on-surface-variant" />
          </span>
          <span className="flex flex-col leading-tight">
            <span className="text-label-lg text-on-surface">
              {DISPLAY_NAME[role] ?? 'Demo User'}
            </span>
            <span className="text-label-md text-on-surface-variant">{role}</span>
          </span>
        </div>
      </div>
    </header>
  );
}
