import axios from 'axios';

// Central Axios instance — all API calls go through here
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Request interceptor: attach JWT ──────────────────────────────────────────
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('tf_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ── Response interceptor: handle 401 globally ────────────────────────────────
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('tf_token');
      localStorage.removeItem('tf-auth');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
