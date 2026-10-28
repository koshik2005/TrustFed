import { describe, it, expect, vi, beforeEach } from 'vitest';
import '@testing-library/jest-dom';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import LoginPage from './LoginPage';
import { api } from '@/services/api';
import { useAuthStore } from '@/store/authStore';

vi.mock('@/services/api', () => ({
  api: {
    authApi: {
      login: vi.fn(),
    },
  },
}));

describe('LoginPage Security Invariants & Error Handling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: null,
      token: null,
      csrfToken: null,
      isAuthenticated: false,
      isBackendWakingUp: false,
    });
  });

  it('renders DEMO ENVIRONMENT warning banner on screen', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );
    expect(screen.getByText(/DEMO ENVIRONMENT/i)).not.toBeNull();
    expect(screen.getByText(/No real patient data/i)).not.toBeNull();
  });

  it('proves login fails and displays error when the backend returns 401 Unauthorized', async () => {
    const error401 = new Error('Invalid email or password.');
    (error401 as unknown as { status: number }).status = 401;
    vi.mocked(api.authApi.login).mockRejectedValueOnce(error401);

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    const emailInput = screen.getByLabelText(/email address/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const submitBtn = screen.getByRole('button', { name: /secure clinical sign in/i });

    fireEvent.change(emailInput, { target: { value: 'hospital@trustfed.ai' } });
    fireEvent.change(passwordInput, { target: { value: 'wrongpassword' } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText('Invalid email or password.')).not.toBeNull();
    });

    // CRITICAL: Ensure no client-side mock authentication was granted
    const authState = useAuthStore.getState();
    expect(authState.isAuthenticated).toBe(false);
    expect(authState.token).toBeNull();
    expect(authState.user).toBeNull();
  });

  it('proves login fails and displays rate-limit message when backend returns 429 Too Many Requests', async () => {
    const error429 = new Error('Too many login attempts. Please try again in 45 seconds.');
    (error429 as unknown as { status: number }).status = 429;
    vi.mocked(api.authApi.login).mockRejectedValueOnce(error429);

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    const submitBtn = screen.getByRole('button', { name: /secure clinical sign in/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Too many login attempts. Please try again in 45 seconds./i)).not.toBeNull();
    });

    // CRITICAL: Ensure no authentication was granted
    const authState = useAuthStore.getState();
    expect(authState.isAuthenticated).toBe(false);
    expect(authState.token).toBeNull();
    expect(authState.user).toBeNull();
  });

  it('1-click demo buttons perform real backend authentication and fail if backend returns 401', async () => {
    vi.mocked(api.authApi.login).mockRejectedValueOnce(new Error('Invalid email or password.'));

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    // Click 1-Click Clinical Demo Access Hospital button
    const demoButtons = screen.getAllByRole('button');
    const hospitalDemoBtn = demoButtons.find(b => b.textContent?.includes('Hospital'));
    expect(hospitalDemoBtn).toBeDefined();

    fireEvent.click(hospitalDemoBtn!);

    await waitFor(() => {
      expect(api.authApi.login).toHaveBeenCalledWith('hospital@trustfed.ai', 'password123');
      expect(screen.getByText('Invalid email or password.')).not.toBeNull();
    });

    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().token).toBeNull();
  });
});
