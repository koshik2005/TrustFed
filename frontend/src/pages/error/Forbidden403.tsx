import { ShieldAlert, ArrowLeft, Home, Lock } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { Button } from '@/components/ui/button';

export default function Forbidden403() {
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const formattedRole = user?.role
    ? user.role.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())
    : 'Guest';

  return (
    <div className="min-h-[75vh] flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-white rounded-2xl border border-slate-200/90 p-8 shadow-xl text-center flex flex-col items-center">
        <div className="w-16 h-16 rounded-2xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 mb-5 shadow-xs">
          <ShieldAlert className="w-8 h-8" />
        </div>

        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100/70 text-amber-800 border border-amber-300/60 mb-3">
          <Lock className="w-3.5 h-3.5" />
          HTTP 403 • Access Restricted
        </span>

        <h1 className="text-xl font-bold text-slate-900 mb-2">
          Tenancy Role Boundary Enforced
        </h1>

        <p className="text-sm text-slate-600 mb-6 leading-relaxed">
          Your current session is authenticated as{' '}
          <strong className="text-slate-900 font-semibold">{formattedRole}</strong>.
          You do not have administrative clearance to access this federation module.
        </p>

        <div className="w-full bg-slate-50 border border-slate-200/80 rounded-xl p-3 mb-6 text-left text-xs text-slate-600 space-y-1.5">
          <div className="flex justify-between">
            <span className="text-slate-500">Active Node:</span>
            <span className="font-mono text-slate-800">
              {user?.hospitalId || 'boston_general'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Isolation Policy:</span>
            <span className="font-semibold text-emerald-700">Strict Multi-Tenant</span>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full">
          <Button
            variant="outline"
            onClick={() => navigate(-1)}
            className="flex-1 rounded-xl text-xs font-medium border-slate-200 hover:bg-slate-100"
          >
            <ArrowLeft className="w-3.5 h-3.5 mr-1.5" />
            Go Back
          </Button>
          <Button
            onClick={() => navigate('/dashboard')}
            className="flex-1 rounded-xl text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white shadow-xs"
          >
            <Home className="w-3.5 h-3.5 mr-1.5" />
            Return to Dashboard
          </Button>
        </div>
      </div>
    </div>
  );
}
