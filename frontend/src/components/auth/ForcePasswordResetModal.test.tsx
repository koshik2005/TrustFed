import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ForcePasswordResetModal from './ForcePasswordResetModal';
import { useAuthStore } from '@/store/authStore';
import { api } from '@/services/api';

vi.mock('@/services/api', () => ({
  api: {
    authApi: {
      resetPassword: vi.fn(),
    },
  },
}));

describe('ForcePasswordResetModal Security Enforcements', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: null,
      token: null,
      isAuthenticated: false,
    });
  });

  it('does not render if mustResetPassword is false or missing', () => {
    useAuthStore.setState({
      user: {
        id: '1',
        name: 'Dr. Test',
        email: 'doc@trustfed.ai',
        role: 'doctor',
        mustResetPassword: false,
      },
      token: 'jwt-token',
      isAuthenticated: true,
    });

    const { container } = render(<ForcePasswordResetModal />);
    expect(container.firstChild).toBeNull();
  });

  it('renders modal when user has mustResetPassword set to true', () => {
    useAuthStore.setState({
      user: {
        id: '2',
        name: 'New Admin',
        email: 'admin@trustfed.ai',
        role: 'regional_admin',
        mustResetPassword: true,
      },
      token: 'temp-jwt-token',
      isAuthenticated: true,
    });

    render(<ForcePasswordResetModal />);
    expect(screen.getByText(/Mandatory Password Reset/i)).not.toBeNull();
    expect(screen.getByText(/Current Temporary Password/i)).not.toBeNull();
    expect(screen.getAllByText(/New Password/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Password Requirements:/i)).not.toBeNull();
  });

  it('submits valid password and updates user state', async () => {
    useAuthStore.setState({
      user: {
        id: '2',
        name: 'New Admin',
        email: 'admin@trustfed.ai',
        role: 'regional_admin',
        mustResetPassword: true,
      },
      token: 'temp-jwt-token',
      isAuthenticated: true,
    });

    (api.authApi.resetPassword as any).mockResolvedValueOnce({
      message: 'Password reset successfully',
      user: {
        id: '2',
        name: 'New Admin',
        email: 'admin@trustfed.ai',
        role: 'regional_admin',
        mustResetPassword: false,
      },
    });

    render(<ForcePasswordResetModal />);

    const inputs = screen.getAllByPlaceholderText(/.+/);
    // 0: Current password, 1: New password, 2: Confirm new password
    fireEvent.change(inputs[0], { target: { value: 'OldTempPass123!' } });
    fireEvent.change(inputs[1], { target: { value: 'NewSecurePass123!Safe' } });
    fireEvent.change(inputs[2], { target: { value: 'NewSecurePass123!Safe' } });

    const submitBtn = screen.getByRole('button', { name: /Update Password & Continue/i });
    expect(submitBtn).not.toBeNull();
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.authApi.resetPassword).toHaveBeenCalledWith('OldTempPass123!', 'NewSecurePass123!Safe');
      expect(useAuthStore.getState().user?.mustResetPassword).toBe(false);
    });
  });
});
