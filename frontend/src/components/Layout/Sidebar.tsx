import { Link, useLocation } from 'react-router-dom';
import { Database, FileUp, LayoutDashboard, Plug, Table2 } from 'lucide-react';
import { useRole } from '../../auth/RoleContext';
import type { Role } from '../../lib/demoRole';

interface NavItem {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
  /** Roles that may use this page. Omitted means everyone. */
  roles?: Role[];
  section: 'work' | 'configure';
}

const navItems: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, section: 'work' },
  {
    to: '/database',
    label: 'Database Extractor',
    icon: Database,
    roles: ['Admin', 'Clinician'],
    section: 'work',
  },
  {
    to: '/upload',
    label: 'File Extractor',
    icon: FileUp,
    roles: ['Admin', 'Clinician'],
    section: 'work',
  },
  { to: '/results', label: 'Results', icon: Table2, section: 'work' },
  {
    to: '/data-sources',
    label: 'Data Sources',
    icon: Plug,
    roles: ['Admin'],
    section: 'configure',
  },
];

const SECTION_LABEL: Record<NavItem['section'], string> = {
  work: 'Extract',
  configure: 'Configure',
};

export default function Sidebar() {
  const location = useLocation();
  const { role } = useRole();

  const visible = navItems.filter((item) => !item.roles || item.roles.includes(role));
  const sections: NavItem['section'][] = ['work', 'configure'];

  return (
    <aside className="w-60 shrink-0 bg-surface flex flex-col h-screen border-r border-outline">
      {/* Wordmark */}
      <Link to="/" className="flex items-center gap-2.5 px-4 h-14 border-b border-outline">
        <span
          className="w-7 h-7 rounded-gm-md bg-gm-blue flex items-center justify-center
                     text-white font-semibold text-label-lg shrink-0"
        >
          M
        </span>
        <span className="flex flex-col leading-tight min-w-0">
          <span className="text-title-md text-on-surface truncate">MediExtractAI</span>
          <span className="text-label-md text-on-surface-variant truncate">
            Clinical data extraction
          </span>
        </span>
      </Link>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3">
        {sections.map((section) => {
          const items = visible.filter((i) => i.section === section);
          if (items.length === 0) return null;
          return (
            <div key={section} className="px-2 mb-4">
              <p className="px-2 mb-1 text-label-sm text-on-surface-variant/80">
                {SECTION_LABEL[section]}
              </p>
              <div className="space-y-0.5">
                {items.map(({ to, label, icon: Icon }) => {
                  const isActive = location.pathname === to;
                  return (
                    <Link
                      key={to}
                      to={to}
                      className={`flex items-center gap-2.5 px-2 py-1.5 rounded-gm-md
                                  text-label-lg transition-colors duration-150 ${
                                    isActive
                                      ? 'bg-gm-blue-light text-gm-blue'
                                      : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
                                  }`}
                    >
                      <Icon size={16} strokeWidth={isActive ? 2.2 : 1.8} className="shrink-0" />
                      <span className="truncate">{label}</span>
                    </Link>
                  );
                })}
              </div>
            </div>
          );
        })}
      </nav>

      {/* Environment footer */}
      <div className="px-3 py-3 border-t border-outline">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-gm-green shrink-0" />
          <span className="text-label-md text-on-surface-variant">
            Demo mode · synthetic data only
          </span>
        </div>
      </div>
    </aside>
  );
}
