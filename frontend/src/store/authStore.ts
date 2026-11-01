import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '../types';

interface AuthStore {
  user: User | null;
  token: string | null; // In-memory access token (short-lived)
  csrfToken: string | null; // In-memory double-submit CSRF token
  isAuthenticated: boolean;
  isLoading: boolean;
  isBackendWakingUp: boolean;
  appMode: 'informational' | 'clinical';

  login: (user: User, token: string, csrfToken?: string) => void;
  setTokens: (token: string, csrfToken?: string) => void;
  setBackendWakingUp: (waking: boolean) => void;
  setAppMode: (mode: 'informational' | 'clinical') => void;
  fetchSystemMode: () => Promise<void>;
  logout: () => Promise<void>;
  initializeAuth: () => Promise<void>;
}

const defaultAppMode: 'informational' | 'clinical' =
  (import.meta.env.VITE_APP_MODE === 'clinical') ? 'clinical' : 'informational';

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      token: null, // NEVER stored in localStorage
      csrfToken: null,
      isAuthenticated: false,
      isLoading: false,
      isBackendWakingUp: false,
      appMode: defaultAppMode,

      setAppMode: (appMode: 'informational' | 'clinical') => {
        set({ appMode });
      },

      fetchSystemMode: async () => {
        try {
          const { getBaseUrl } = await import('../services/config');
          const axios = (await import('axios')).default;
          const base = getBaseUrl().replace(/\/api$/, '');
          const res = await axios.get<{ mode?: string }>(`${base}/health`);
          if (res.data?.mode === 'clinical') {
            set({ appMode: 'clinical' });
          } else if (res.data?.mode === 'informational') {
            set({ appMode: 'informational' });
          }
        } catch {
          // Keep current fallback mode on network error
        }
      },

      login: (user: User, token: string, csrfToken?: string) => {
        set({
          user,
          token,
          csrfToken: csrfToken || null,
          isAuthenticated: true,
        });
      },

      setTokens: (token: string, csrfToken?: string) => {
        set((state) => ({
          token,
          csrfToken: csrfToken !== undefined ? csrfToken : state.csrfToken,
          isAuthenticated: true,
        }));
      },

      setBackendWakingUp: (isBackendWakingUp: boolean) => {
        set({ isBackendWakingUp });
      },

      logout: async () => {
        try {
          const { getBaseUrl } = await import('../services/config');
          const axios = (await import('axios')).default;
          await axios.post(`${getBaseUrl()}/auth/logout`, {}, { withCredentials: true });
        } catch {
          // Ignore network or logout failure on client
        } finally {
          localStorage.removeItem('tf_token');
          set({
            user: null,
            token: null,
            csrfToken: null,
            isAuthenticated: false,
          });
        }
      },

      initializeAuth: async () => {
        // Query backend mode asynchronously
        get().fetchSystemMode().catch(() => {});

        const { isAuthenticated, user, csrfToken } = get();
        // If not authenticated, nothing to restore
        if (!isAuthenticated && !user) return;

        set({ isLoading: true });
        try {
          const { getBaseUrl } = await import('../services/config');
          const axios = (await import('axios')).default;
          const res = await axios.post<{ token: string; user: User; csrf_token?: string }>(
            `${getBaseUrl()}/auth/refresh`,
            {},
            {
              withCredentials: true,
              headers: csrfToken ? { 'X-CSRF-Token': csrfToken } : {},
            }
          );
          if (res.data?.token) {
            set({
              token: res.data.token,
              csrfToken: res.data.csrf_token || null,
              user: res.data.user || user,
              isAuthenticated: true,
            });
          }
        } catch {
          // If refresh cookie expired or invalid, keep user logged out or handle fallback
        } finally {
          set({ isLoading: false });
        }
      },
    }),
    {
      name: 'tf-auth',
      // Persist user, isAuthenticated, and CSRF token for refresh rotation; NEVER persist raw access token
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        csrfToken: state.csrfToken,
      }),
    }
  )
);

