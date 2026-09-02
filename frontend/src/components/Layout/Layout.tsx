import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';

export default function Layout() {
  return (
    <div className="flex h-screen overflow-hidden bg-surface-dim">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <Header />
        <main className="flex-1 overflow-auto">
          <div className="px-6 py-5">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
