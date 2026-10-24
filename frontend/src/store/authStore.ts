import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AuthState, User } from '../types';

interface AuthStore extends AuthState {
  login: (user: User, token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      login: (user, token) => {
        localStorage.setItem('tf_token', token);
        set({ user, token, isAuthenticated: true });
      },

      logout: () => {
        localStorage.removeItem('tf_token');
        set({ user: null, token: null, isAuthenticated: false });
      },
    }),
    { name: 'tf-auth' }
  )
);
