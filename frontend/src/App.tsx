import { lazy } from 'react';
import { Routes, Route } from 'react-router-dom';

import Layout from './components/Layout/Layout';
import ProtectedRoute from './auth/ProtectedRoute';
import { RoleProvider } from './auth/RoleContext';
import Dashboard from './pages/Dashboard';
import NotFound from './pages/NotFound';

// The landing page is imported eagerly — it is what most visits render, and
// lazy-loading it would only add a round trip. The rest are split out: the file
// extractor drags in a dropzone library, the data source page is administrator
// -only, and neither belongs in the bundle a first-time visitor waits for.
//
// The Suspense boundary these need lives inside Layout, so the shell stays on
// screen while a page loads.
const DatabaseExtractor = lazy(() => import('./pages/DatabaseExtractor'));
const FileExtractor = lazy(() => import('./pages/FileExtractor'));
const Results = lazy(() => import('./pages/Results'));
const DataSources = lazy(() => import('./pages/DataSources'));

export default function App() {
  return (
    <RoleProvider>
      <Routes>
        <Route
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="database" element={<DatabaseExtractor />} />
          <Route path="upload" element={<FileExtractor />} />
          <Route path="results" element={<Results />} />
          <Route path="data-sources" element={<DataSources />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </RoleProvider>
  );
}
