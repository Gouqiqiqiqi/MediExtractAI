import { Routes, Route } from 'react-router-dom';

import Layout from './components/Layout/Layout';
import ProtectedRoute from './auth/ProtectedRoute';
import { RoleProvider } from './auth/RoleContext';
import Dashboard from './pages/Dashboard';
import DatabaseExtractor from './pages/DatabaseExtractor';
import DataSources from './pages/DataSources';
import FileExtractor from './pages/FileExtractor';
import Results from './pages/Results';
import NotFound from './pages/NotFound';

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
