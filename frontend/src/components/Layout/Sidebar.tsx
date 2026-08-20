import { Link, useLocation } from 'react-router-dom';
import { Database, FileUp, LayoutDashboard, Table2 } from 'lucide-react';

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/database', label: 'Database Extractor', icon: Database },
  { to: '/upload', label: 'File Extractor', icon: FileUp },
  { to: '/results', label: 'Results', icon: Table2 },
];

export default function Sidebar() {
  const location = useLocation();
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
        {navItems.map(({ to, label, icon: Icon }) => {
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
        </div>
      </div>
    </aside>
  );
}
