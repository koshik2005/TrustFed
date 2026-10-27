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

  login: (user: User, token: string, csrfToken?: string) => void;
  setTokens: (token: string, csrfToken?: string) => void;
  setBackendWakingUp: (waking: boolean) => void;
  logout: () => Promise<void>;
  initializeAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      token: null, // NEVER stored in localStorage
      csrfToken: null,
      isAuthenticated: false,
      isLoading: false,
      isBackendWakingUp: false,

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
      // Only persist safe metadata, NEVER in-memory access token or CSRF token
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

