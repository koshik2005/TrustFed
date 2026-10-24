import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Loader2 } from 'lucide-react';
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

const ROLES: { id: UserRole; title: string; desc: string }[] = [
  { id: 'hospital_staff', title: 'Hospital Staff', desc: 'Local node access' },
  { id: 'regional_admin', title: 'Regional Admin', desc: 'Cluster oversight' },
  { id: 'global_admin', title: 'Global Admin', desc: 'System master' },
];

export default function LoginPage() {
  const [selectedRole, setSelectedRole] = useState<UserRole>('hospital_staff');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const { token, user } = await api.authApi.login(email, password);
      login(user, token);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Could not reach the server');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen w-full flex items-center justify-center bg-slate-50 overflow-hidden p-6 font-sans text-slate-900">
      {/* Background radial gradient glow */}
      <div 
        className="absolute inset-0 z-0 pointer-events-none"
        style={{ background: 'radial-gradient(circle at top center, rgba(59, 130, 246, 0.12) 0%, transparent 60%)' }}
      />

      {/* Main Glass Card container */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="relative z-10 w-full max-w-[440px]"
      >
        <Card className="w-full border-slate-200 bg-white p-8 backdrop-blur-xl shadow-2xl flex flex-col gap-6 rounded-2xl">
          
          {/* Header Row */}
          <div className="flex items-center gap-4">
            <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-[10px] bg-gradient-to-br from-blue-500 to-cyan-500 text-base font-bold text-slate-900 shadow-lg">
              TF
            </div>
            <div className="flex flex-col">
              <h1 className="text-lg font-bold text-slate-900 leading-tight">TrustFed-Health</h1>
              <span className="text-xs text-slate-600">Secure Federated Learning Hub</span>
            </div>
          </div>

          {/* Role Selector */}
          <div>
            <span className="mb-3 block text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-500">
              Select Your Role
            </span>
            <div className="grid grid-cols-3 gap-2">
              {ROLES.map((role) => {
                const isActive = selectedRole === role.id;
                return (
                  <div
                    key={role.id}
                    onClick={() => { setSelectedRole(role.id); setEmail(DEMO_EMAIL[role.id]); }}
                    className={cn(
                      "cursor-pointer rounded-lg border p-3 text-center transition-all duration-200 relative overflow-hidden",
                      isActive
                        ? "border-blue-500/40 bg-blue-500/10 shadow-[0_0_12px_rgba(59,130,246,0.2)]"
                        : "border-slate-200 bg-slate-100 hover:bg-slate-200"
                    )}
                  >
                    <div className="text-[11px] font-semibold text-slate-900 mb-1">{role.title}</div>
                    <div className="text-[9px] text-slate-600 leading-tight">{role.desc}</div>
                    
                    {/* Active state indicator line */}
                    {isActive && (
                      <motion.div
                        layoutId="activeRoleIndicator"
                        className="absolute bottom-0 left-0 right-0 h-[2px] bg-blue-500"
                        transition={{ type: "spring", stiffness: 300, damping: 30 }}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="email" className="text-xs font-medium text-slate-600">Email Address</Label>
              <Input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@trustfed.ai"
                className="rounded-xl border-slate-200 bg-slate-100 px-4 py-5 text-sm text-slate-900 placeholder:text-slate-500 focus-visible:border-blue-500 focus-visible:ring-2 focus-visible:ring-blue-500/20"
              />
            </div>
            
            <div className="flex flex-col gap-2">
              <Label htmlFor="password" className="text-xs font-medium text-slate-600">Password</Label>
              <Input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="rounded-xl border-slate-200 bg-slate-100 px-4 py-5 text-sm text-slate-900 placeholder:text-slate-500 focus-visible:border-blue-500 focus-visible:ring-2 focus-visible:ring-blue-500/20"
              />
            </div>

            {error && <p className="text-sm text-red-600">{error}</p>}
            <Button
              type="submit"
              disabled={loading}
              className="mt-2 h-[48px] w-full rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 text-sm font-semibold text-slate-900 shadow-[0_0_24px_rgba(59,130,246,0.35)] transition-all duration-200 hover:opacity-90 hover:shadow-[0_0_32px_rgba(59,130,246,0.5)] active:scale-[0.98] disabled:opacity-70"
            >
              {loading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <>
                  Secure Login
                  <ArrowRight className="ml-2 h-4 w-4" />
                </>
              )}
            </Button>
          </form>

          {/* Footer Text */}
          <div className="mt-2 text-center text-xs text-slate-500">
            Protected by end-to-end encryption · HIPAA compliant
          </div>
          
        </Card>
      </motion.div>
    </div>
  );
}
