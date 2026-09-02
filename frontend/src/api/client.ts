/**
 * Axios API client. Demo mode: no auth header required.
 */

import axios from 'axios';
import { getDemoRole } from '../lib/demoRole';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120_000, // extraction over several notes can take a while
});

// ── Request interceptor: carry the demo role ──
// The backend reads this header only when DEMO_MODE is on. With real auth the
// role comes from the token and this is ignored, so it cannot be used to
// escalate anything in a deployed environment.
apiClient.interceptors.request.use((config) => {
  config.headers.set('X-Demo-Role', getDemoRole());
  return config;
});

// ── Response interceptor: handle errors ──
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    return Promise.reject(error);
  },
);

export default apiClient;
