import { Bell, Search, User } from 'lucide-react';

export default function Header() {
  return (
    <header className="h-16 bg-surface border-b border-outline/40 flex items-center justify-between px-6">
      {/* Search bar */}
      <div className="relative w-96">
        <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" />
        <input
          type="text"
          placeholder="Search notes, extractions..."
          className="w-full pl-10 pr-4 py-2 bg-surface-container rounded-gm-xl text-body-md text-on-surface
                     placeholder:text-on-surface-variant border-0 focus:outline-none focus:ring-2 focus:ring-gm-blue/40
                     transition-all duration-200"
        />
      </div>

      <div className="flex items-center gap-3">
        {/* Notification */}
        <button className="w-10 h-10 rounded-gm-xl flex items-center justify-center
                           text-on-surface-variant hover:bg-surface-container transition-colors duration-200">
          <Bell size={20} />
        </button>

        {/* User avatar */}
        <div className="flex items-center gap-3 pl-3 border-l border-outline/40">
          <div className="w-9 h-9 rounded-gm-xl bg-gm-blue-light flex items-center justify-center">
            <User size={18} className="text-gm-blue" />
          </div>
          <span className="text-label-lg text-on-surface font-medium">
            Demo User
          </span>
        </div>
      </div>
    </header>
  );
}
