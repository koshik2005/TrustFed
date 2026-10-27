import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore } from './authStore';
import type { User } from '../types';

class LocalStorageMock {
  private store: Record<string, string> = {};
  getItem(key: string) { return this.store[key] ?? null; }
  setItem(key: string, value: string) { this.store[key] = String(value); }
  removeItem(key: string) { delete this.store[key]; }
  clear() { this.store = {}; }
}

const mockStorage = new LocalStorageMock();
Object.defineProperty(globalThis, 'localStorage', {
  value: mockStorage,
  writable: true,
});
if (typeof (globalThis as unknown as { window: unknown }).window === 'undefined') {
  (globalThis as unknown as { window: unknown }).window = globalThis;
}
(globalThis as unknown as { window: { localStorage: unknown } }).window.localStorage = mockStorage;

describe('AuthStore Security & Tenancy Invariants', () => {
  const mockHospitalUser: User = {
    id: 'usr-hosp-01',
    name: 'Dr. Sarah Chen',
    email: 'hospital@trustfed.ai',
    role: 'hospital_staff',
    hospitalId: 'boston_general',
  };

  beforeEach(() => {
    mockStorage.clear();
    useAuthStore.setState({
      user: null,
      token: null,
      csrfToken: null,
      isAuthenticated: false,
      isLoading: false,
      isBackendWakingUp: false,
    });
  });

  it('keeps short-lived access tokens strictly in memory without writing to localStorage', () => {
    const rawAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy_access_token';
    const csrfToken = 'csrf_secure_token_123';

    useAuthStore.getState().login(mockHospitalUser, rawAccessToken, csrfToken);

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.token).toBe(rawAccessToken);
    expect(state.csrfToken).toBe(csrfToken);
    expect(state.user?.role).toBe('hospital_staff');
    expect(state.user?.hospitalId).toBe('boston_general');

    // CRITICAL SECURITY ASSERTION: Access token MUST NOT be stored in plaintext in localStorage
    expect(localStorage.getItem('tf_token')).toBeNull();

    // Verify persisted Zustand payload only retains safe fields
    const persisted = localStorage.getItem('tf-auth');
    if (persisted) {
      const parsed = JSON.parse(persisted);
      expect(parsed.state.token).toBeUndefined();
      expect(parsed.state.csrfToken).toBeUndefined();
      expect(parsed.state.user.id).toBe('usr-hosp-01');
      expect(parsed.state.isAuthenticated).toBe(true);
    }
  });

  it('clears all tokens and resets authentication on logout', async () => {
    useAuthStore.getState().login(
      mockHospitalUser,
      'token_to_revoke',
      'csrf_to_revoke'
    );
    expect(useAuthStore.getState().isAuthenticated).toBe(true);

    await useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.token).toBeNull();
    expect(state.csrfToken).toBeNull();
    expect(state.user).toBeNull();
    expect(localStorage.getItem('tf_token')).toBeNull();
  });
});
