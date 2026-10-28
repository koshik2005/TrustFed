import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Loader2, ShieldCheck, HeartPulse, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';
import { useAuthStore } from '@/store/authStore';
import type { UserRole } from '@/types';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { api } from '@/services/api';

const DEMO_EMAIL: Record<UserRole, string> = {
  hospital_staff: 'hospital@trustfed.ai',
  regional_admin: 'regional@trustfed.ai',
  global_admin: 'admin@trustfed.ai',
};

const ROLES: { id: UserRole; title: string; desc: string; icon: string }[] = [
  { id: 'hospital_staff', title: 'Hospital Staff', desc: 'Boston General node', icon: '🏥' },
  { id: 'regional_admin', title: 'Regional Admin', desc: 'East Zone aggregator', icon: '🌐' },
  { id: 'global_admin', title: 'Global Admin', desc: 'System governance', icon: '⚡' },
];

export default function LoginPage() {
  const [selectedRole, setSelectedRole] = useState<UserRole>('hospital_staff');
  const [email, setEmail] = useState('hospital@trustfed.ai');
  const [password, setPassword] = useState('password123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login, isBackendWakingUp } = useAuthStore();
  const navigate = useNavigate();

  const submitLogin = async (loginEmail: string, loginPassword: string) => {
    setLoading(true);
    setError('');
    try {
      const { token, user, csrf_token } = await api.authApi.login(loginEmail, loginPassword);
      login(user, token, csrf_token);
      navigate('/dashboard');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Invalid email or password.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleLoginSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    await submitLogin(email, password);
  };

  const handleQuickDemoAccess = async (role: UserRole) => {
    setSelectedRole(role);
    const targetEmail = DEMO_EMAIL[role];
    setEmail(targetEmail);
    setPassword('password123');
    await submitLogin(targetEmail, 'password123');
  };

  return (
    <div className="relative min-h-screen w-full flex items-center justify-center bg-slate-50 overflow-hidden p-6 font-sans text-slate-900">
      {/* Background radial gradient glow */}
      <div 
        className="absolute inset-0 z-0 pointer-events-none"
        style={{ background: 'radial-gradient(circle at top center, rgba(59, 130, 246, 0.15) 0%, rgba(6, 182, 212, 0.05) 40%, transparent 70%)' }}
      />

      {/* Main Glass Card container */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="relative z-10 w-full max-w-[480px]"
      >
        <Card className="w-full border-slate-200/80 bg-white/95 p-8 backdrop-blur-xl shadow-2xl flex flex-col gap-6 rounded-2xl">
          
          {/* Header Row */}
          <div className="flex items-center justify-between border-b border-slate-100 pb-5">
            <div className="flex items-center gap-3.5">
              <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 via-blue-500 to-cyan-500 text-lg font-bold text-white shadow-md shadow-blue-500/20">
                <HeartPulse className="w-6 h-6" />
              </div>
              <div className="flex flex-col">
                <h1 className="text-xl font-bold text-slate-900 leading-tight">TrustFed-Health</h1>
                <span className="text-xs text-slate-500 font-medium">Federated Learning & Clinical AI Platform</span>
              </div>
            </div>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Live v2.0
            </span>
          </div>

          {/* Visible Demo Environment Notice */}
          <div className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-900 text-xs font-medium">
            <span className="text-base flex-shrink-0">⚠️</span>
            <div className="flex flex-col">
              <span className="font-semibold text-amber-950">DEMO ENVIRONMENT</span>
              <span className="text-[11px] text-amber-800">No real patient data. Evaluation test credentials only.</span>
            </div>
          </div>

          {/* Quick 1-Click Demo Access */}
          <div className="p-3.5 rounded-xl bg-gradient-to-r from-blue-50 to-cyan-50 border border-blue-200/70 flex flex-col gap-2">
            <div className="flex items-center justify-between text-xs font-semibold text-blue-900">
              <span className="flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-blue-600" />
                1-Click Clinical Demo Access
              </span>
              <span className="text-[10px] text-blue-600 font-normal">No password required</span>
            </div>
            <div className="grid grid-cols-3 gap-2 pt-1">
              {ROLES.map((role) => (
                <button
                  key={role.id}
                  type="button"
                  onClick={() => handleQuickDemoAccess(role.id)}
                  className="px-2.5 py-1.5 rounded-lg bg-white border border-blue-200 text-slate-700 hover:text-blue-600 hover:border-blue-400 hover:shadow-xs transition-all text-xs font-medium text-center truncate"
                >
                  {role.icon} {role.title.split(' ')[0]}
                </button>
              ))}
            </div>
          </div>

          {/* Role Selector */}
          <div>
            <div className="flex items-center justify-between mb-2.5">
              <span className="block text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">
                Or Select Role to Sign In
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2.5">
              {ROLES.map((role) => {
                const isActive = selectedRole === role.id;
                return (
                  <div
                    key={role.id}
                    onClick={() => {
                      setSelectedRole(role.id);
                      setEmail(DEMO_EMAIL[role.id]);
                      setPassword('password123');
                    }}
                    className={cn(
                      "cursor-pointer rounded-xl border p-3 text-center transition-all duration-200 relative overflow-hidden",
                      isActive
                        ? "border-blue-500 bg-blue-50/70 text-blue-700 shadow-sm ring-1 ring-blue-500/30"
                        : "border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700"
                    )}
                  >
                    <div className="text-base mb-1">{role.icon}</div>
                    <div className="text-xs font-semibold text-slate-900 mb-0.5">{role.title}</div>
                    <div className="text-[10px] text-slate-500 leading-tight">{role.desc}</div>
                    
                    {isActive && (
                      <motion.div
                        layoutId="activeRoleIndicator"
                        className="absolute bottom-0 left-0 right-0 h-[2.5px] bg-blue-600"
                        transition={{ type: "spring", stiffness: 350, damping: 30 }}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Login Form */}
          <form onSubmit={handleLoginSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email" className="text-xs font-medium text-slate-700">Email Address</Label>
              <Input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@trustfed.ai"
                className="rounded-xl border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus-visible:border-blue-500 focus-visible:ring-2 focus-visible:ring-blue-500/20"
              />
            </div>
            
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="password" className="text-xs font-medium text-slate-700">Password</Label>
              <Input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="rounded-xl border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus-visible:border-blue-500 focus-visible:ring-2 focus-visible:ring-blue-500/20"
              />
            </div>

            {isBackendWakingUp && (
              <div className="p-3 rounded-xl bg-blue-50 border border-blue-200 text-blue-850 text-xs font-medium flex items-center gap-2 animate-pulse">
                <Loader2 className="h-4 w-4 animate-spin text-blue-600 flex-shrink-0" />
                <span>Backend server is waking up on Render free tier. Retrying automatically...</span>
              </div>
            )}

            {error && (
              <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs font-medium flex items-start gap-2">
                <span className="text-red-500 font-bold">•</span>
                <span>{error}</span>
              </div>
            )}
            
            <Button
              type="submit"
              disabled={loading}
              className="mt-1 h-11 w-full rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 text-sm font-semibold text-white shadow-md shadow-blue-500/25 transition-all duration-200 hover:from-blue-700 hover:to-cyan-700 active:scale-[0.99] disabled:opacity-70"
            >
              {loading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <>
                  Secure Clinical Sign In
                  <ArrowRight className="ml-2 h-4 w-4" />
                </>
              )}
            </Button>
          </form>

          {/* Footer Badges */}
          <div className="border-t border-slate-100 pt-3 flex items-center justify-center gap-4 text-[11px] text-slate-500">
            <span className="flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              HIPAA Compliant
            </span>
            <span>•</span>
            <span>Local DP (ε = 1.84)</span>
            <span>•</span>
            <span>Paillier Cryptography</span>
          </div>
          
        </Card>
      </motion.div>
    </div>
  );
}
