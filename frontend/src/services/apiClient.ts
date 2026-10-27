import axios, { type InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '../store/authStore';
import { getBaseUrl } from './config';

// Central Axios instance — all API calls go through here
const apiClient = axios.create({
  baseURL: getBaseUrl(),
  timeout: 15000,
  withCredentials: true, // Required for httpOnly tf_refresh_token cookie
  headers: { 'Content-Type': 'application/json' },
});

// ── Request interceptor: attach in-memory JWT and CSRF header ─────────────────
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const { token, csrfToken } = useAuthStore.getState();
  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if (csrfToken && !config.headers['X-CSRF-Token']) {
    config.headers['X-CSRF-Token'] = csrfToken;
  }
  return config;
});

// Queue for holding requests while a token refresh is in flight
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Helper for cold-start retry
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// ── Response interceptor: cold-start retries & token refresh rotation ──────────
apiClient.interceptors.response.use(
  (response) => {
    useAuthStore.getState().setBackendWakingUp(false);
    return response;
  },
  async (error) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retryCount?: number;
      _isRetry?: boolean;
    };

    if (!originalRequest) {
      return Promise.reject(error);
    }

    const status = error.response?.status;
    const isNetworkOrColdStart =
      !status ||
      status === 502 ||
      status === 503 ||
      status === 504 ||
      error.code === 'ECONNABORTED';

    // 1. Cold start retry logic for free tier Render backends
    if (isNetworkOrColdStart && (originalRequest._retryCount || 0) < 3) {
      originalRequest._retryCount = (originalRequest._retryCount || 0) + 1;
      useAuthStore.getState().setBackendWakingUp(true);
      const delay = Math.min(1000 * Math.pow(2, originalRequest._retryCount - 1), 4000);
      await sleep(delay);
      return apiClient(originalRequest);
    }
    useAuthStore.getState().setBackendWakingUp(false);

    // 2. Token refresh rotation on 401 Unauthorized
    if (status === 401 && !originalRequest._isRetry) {
      const url = originalRequest.url || '';
      const isAuthEndpoint =
        url.includes('/auth/login') ||
        url.includes('/auth/refresh') ||
        url.includes('/auth/logout');

      if (isAuthEndpoint) {
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((newToken) => {
            if (newToken && typeof newToken === 'string') {
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
            }
            return apiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._isRetry = true;
      isRefreshing = true;

      try {
        const { csrfToken } = useAuthStore.getState();
        const refreshResponse = await axios.post<{
          token: string;
          csrf_token?: string;
        }>(
          `${getBaseUrl()}/auth/refresh`,
          {},
          {
            withCredentials: true,
            headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : {},
          }
        );

        const newToken = refreshResponse.data.token;
        const newCsrf = refreshResponse.data.csrf_token;
        useAuthStore.getState().setTokens(newToken, newCsrf);

        processQueue(null, newToken);
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        if (newCsrf) originalRequest.headers['X-CSRF-Token'] = newCsrf;
        return apiClient(originalRequest);
      } catch (refreshErr) {
        processQueue(refreshErr, null);
        await useAuthStore.getState().logout();
        if (
          typeof window !== 'undefined' &&
          window.location.pathname !== '/login'
        ) {
          window.location.href = '/login';
        }
        return Promise.reject(refreshErr);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;

