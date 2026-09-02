import { Suspense } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';
import Loading from '../common/Loading';

export default function Layout() {
  return (
    <div className="flex h-screen overflow-hidden bg-surface-dim">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <Header />
        <main className="flex-1 overflow-auto">
          <div className="px-6 py-5">
            {/* Inside the shell, not around it. A boundary placed outside the
                layout would swap the sidebar and header for a spinner every
                time a lazily-loaded page was opened. */}
            <Suspense fallback={<Loading message="Loading page…" />}>
              <Outlet />
            </Suspense>
          </div>
        </main>
      </div>
    </div>
  );
}
