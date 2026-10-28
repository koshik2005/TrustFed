import React, { useState } from 'react';
import { ShieldCheck, KeyRound, AlertCircle, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { api } from '@/services/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export default function ForcePasswordResetModal() {
  const { user, login, token, csrfToken } = useAuthStore();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!user?.mustResetPassword) {
    return null;
  }

  // Password policy live criteria
  const hasLength = newPassword.length >= 8;
  const hasUpper = /[A-Z]/.test(newPassword);
  const hasLower = /[a-z]/.test(newPassword);
  const hasNumber = /[0-9]/.test(newPassword);
  const hasSpecial = /[!@#$%^&*()-_=+[\]{}|;:,.<>?]/.test(newPassword);
  const matchesConfirm = newPassword.length > 0 && newPassword === confirmPassword;
  const isAllValid = hasLength && hasUpper && hasLower && hasNumber && hasSpecial && matchesConfirm;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAllValid) return;
    setError(null);
    setLoading(true);

    try {
      const res = await api.authApi.resetPassword(currentPassword, newPassword);
      if (res.user && token) {
        login(res.user, token, csrfToken || undefined);
      }
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(axiosErr.response?.data?.detail || axiosErr.message || 'Failed to reset password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/75 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-md w-full p-6 text-slate-900 animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-600 flex items-center justify-center flex-shrink-0">
            <KeyRound className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold tracking-tight text-slate-900">Mandatory Password Reset</h2>
            <p className="text-xs text-slate-500 font-medium">First-login security compliance requirement</p>
          </div>
        </div>

        <p className="text-xs text-slate-600 leading-relaxed mb-5 bg-slate-50 p-3 rounded-xl border border-slate-200/80">
          Your account was provisioned with a temporary one-time credential. Please set a strong, private password to activate your clinical access.
        </p>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-50 border border-rose-200 flex items-start gap-2.5 text-xs text-rose-700">
            <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Current Temporary Password</label>
            <Input
              type="password"
              placeholder="Enter the password provided by your admin"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
              className="text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">New Password</label>
            <Input
              type="password"
              placeholder="Create a strong password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              className="text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Confirm New Password</label>
            <Input
              type="password"
              placeholder="Re-enter your new password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              className="text-sm"
            />
          </div>

          {/* Password Policy Checklist */}
          <div className="bg-slate-50 rounded-xl p-3 border border-slate-200/80 space-y-1.5 text-[11px]">
            <p className="font-semibold text-slate-700 mb-1">Password Requirements:</p>
            <div className="grid grid-cols-2 gap-1.5">
              <span className={`flex items-center gap-1.5 ${hasLength ? 'text-emerald-700 font-medium' : 'text-slate-500'}`}>
                {hasLength ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> : <XCircle className="w-3.5 h-3.5 text-slate-400" />}
                8+ characters
              </span>
              <span className={`flex items-center gap-1.5 ${hasUpper ? 'text-emerald-700 font-medium' : 'text-slate-500'}`}>
                {hasUpper ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> : <XCircle className="w-3.5 h-3.5 text-slate-400" />}
                1 uppercase letter
              </span>
              <span className={`flex items-center gap-1.5 ${hasLower ? 'text-emerald-700 font-medium' : 'text-slate-500'}`}>
                {hasLower ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> : <XCircle className="w-3.5 h-3.5 text-slate-400" />}
                1 lowercase letter
              </span>
              <span className={`flex items-center gap-1.5 ${hasNumber ? 'text-emerald-700 font-medium' : 'text-slate-500'}`}>
                {hasNumber ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> : <XCircle className="w-3.5 h-3.5 text-slate-400" />}
                1 number
              </span>
              <span className={`flex items-center gap-1.5 ${hasSpecial ? 'text-emerald-700 font-medium' : 'text-slate-500'}`}>
                {hasSpecial ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> : <XCircle className="w-3.5 h-3.5 text-slate-400" />}
                1 special character
              </span>
              <span className={`flex items-center gap-1.5 ${matchesConfirm ? 'text-emerald-700 font-medium' : 'text-slate-500'}`}>
                {matchesConfirm ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> : <XCircle className="w-3.5 h-3.5 text-slate-400" />}
                Passwords match
              </span>
            </div>
          </div>

          <Button
            type="submit"
            disabled={!isAllValid || loading || !currentPassword}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 rounded-xl flex items-center justify-center gap-2 shadow-xs transition-colors"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
            <span>Update Password & Continue</span>
          </Button>
        </form>
      </div>
    </div>
  );
}
