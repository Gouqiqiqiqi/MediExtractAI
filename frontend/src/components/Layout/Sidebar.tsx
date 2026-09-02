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
}

const navItems: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/database', label: 'Database Extractor', icon: Database, roles: ['Admin', 'Clinician'] },
  { to: '/upload', label: 'File Extractor', icon: FileUp, roles: ['Admin', 'Clinician'] },
  { to: '/results', label: 'Results', icon: Table2 },
  { to: '/data-sources', label: 'Data Sources', icon: Plug, roles: ['Admin'] },
];

export default function Sidebar() {
  const location = useLocation();
  const { role } = useRole();

  const visible = navItems.filter((item) => !item.roles || item.roles.includes(role));

  return (
    <aside className="w-72 bg-surface flex flex-col min-h-screen border-r border-outline/40">
      {/* Logo */}
      <div className="px-6 py-5 flex items-center gap-3">
        <div className="w-10 h-10 rounded-gm-lg bg-gm-blue flex items-center justify-center">
          <span className="text-white font-bold text-title-md">M</span>
        </div>
        <Link to="/" className="flex flex-col">
          <span className="font-bold text-title-md text-on-surface">MediExtractAI</span>
          <span className="text-label-md text-on-surface-variant">Clinical Data Extraction</span>
        </Link>
      </div>

      <div className="divider mx-4" />

      {/* Navigation */}
      <nav className="flex-1 py-3 px-3 space-y-1">
        {visible.map(({ to, label, icon: Icon }) => {
          const isActive = location.pathname === to;
          return (
            <Link
              key={to}
              to={to}
              className={`flex items-center gap-3 px-4 py-2.5 rounded-gm-xl text-label-lg font-medium transition-all duration-200 ${
                isActive
                  ? 'bg-gm-blue-light text-gm-blue'
                  : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
              }`}
            >
              <Icon size={20} strokeWidth={isActive ? 2.2 : 1.8} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Demo badge */}
      <div className="p-3">
        <div className="divider mb-3" />
        <div className="px-4 py-2.5 text-label-md text-on-surface-variant">
          Demo mode &middot; synthetic data only
          <span className="block mt-0.5">
            Signed in as <span className="text-on-surface font-medium">{role}</span>
          </span>
        </div>
      </div>
    </aside>
  );
}
