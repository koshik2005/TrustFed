import { useState } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Activity, BrainCircuit, FlaskConical,
  Shield, ShieldAlert, Network, BarChart3, ScrollText,
  Settings, LogOut, ChevronRight, Menu, X, ShieldCheck,
  UserCheck, HeartPulse, Loader2, Hospital, Users,
  UserPlus, Stethoscope
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { cn } from '@/utils';
import type { NavItem } from '@/types';

const NAV_ITEMS: NavItem[] = [
  { id: 'dashboard',             label: 'Role Dashboard',        path: '/dashboard',     icon: 'LayoutDashboard', roles: ['hospital_staff', 'doctor', 'regional_admin', 'global_admin'] },
  { id: 'patients',              label: 'Patient Directory',     path: '/patients',      icon: 'Users',           roles: ['hospital_staff', 'doctor', 'global_admin'] },
  { id: 'new-patient',           label: 'New Patient Intake',    path: '/patients/new',  icon: 'UserPlus',        roles: ['hospital_staff', 'doctor', 'global_admin'] },
  { id: 'pending-confirmations', label: 'Doctor Confirmations', path: '/doctor/pending', icon: 'Stethoscope',    roles: ['doctor', 'global_admin'] },
  { id: 'prediction',            label: 'Clinical Prediction',   path: '/prediction',    icon: 'BrainCircuit',    roles: ['hospital_staff', 'doctor', 'global_admin'] },
  { id: 'hubs',                  label: 'Regional Hubs',         path: '/hubs',          icon: 'Network',         roles: ['global_admin'] },
  { id: 'regional',              label: 'Regional Hospitals',    path: '/regional',      icon: 'Hospital',        roles: ['regional_admin', 'global_admin'] },
  { id: 'training',              label: 'Global Training',       path: '/training',      icon: 'Activity',        roles: ['global_admin'] },
  { id: 'fairness',              label: 'Fairness Audit',        path: '/fairness',      icon: 'ShieldAlert',     roles: ['global_admin'] },
  { id: 'privacy',               label: 'Privacy Report',        path: '/privacy',       icon: 'Shield',          roles: ['global_admin'] },
  { id: 'audit',                 label: 'Audit Log',             path: '/audit',         icon: 'ScrollText',      roles: ['global_admin'] },
  { id: 'settings',              label: 'Settings',              path: '/settings',      icon: 'Settings',        roles: ['hospital_staff', 'doctor', 'regional_admin', 'global_admin'] },
];


const ICON_MAP: Record<string, React.ComponentType<{ size?: number; className?: string }>> = {
  LayoutDashboard, Activity, BrainCircuit, FlaskConical,
  Shield, ShieldAlert, Network, BarChart3, ScrollText, Settings, Hospital,
  Users, UserPlus, Stethoscope,
};

export default function DashboardLayout() {
  const { user, logout, isBackendWakingUp } = useAuthStore();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const allowedNavItems = NAV_ITEMS.filter((item) =>
    user?.role ? item.roles.includes(user.role) : false
  );

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 text-slate-900">

      {/* ── Mobile Sidebar Overlay ───────────────────────────────────────── */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-40 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 flex flex-col py-5 px-3.5 bg-white border-r border-slate-200 transition-transform duration-200 ease-in-out md:static md:translate-x-0 shadow-xs",
          mobileOpen ? "translate-x-0 shadow-2xl" : "-translate-x-full"
        )}
      >
        {/* Logo */}
        <div className="px-2 mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center text-white font-bold text-sm shadow-md bg-gradient-to-br from-blue-600 via-blue-500 to-cyan-500">
              <HeartPulse className="w-5 h-5" />
            </div>
            <div>
              <p className="font-bold text-slate-900 text-sm leading-tight tracking-tight">TrustFed-Health</p>
              <p className="text-[11px] text-slate-500 font-medium">Federated Clinical AI</p>
            </div>
          </div>
          <button
            onClick={() => setMobileOpen(false)}
            className="md:hidden p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
          >
            <X size={18} />
          </button>
        </div>

        {/* Navigation Category Label */}
        <div className="px-3 pb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
          Clinical & FL Navigation
        </div>

        {/* Nav Items */}
        <nav className="flex-1 space-y-1 overflow-y-auto pr-1">
          {allowedNavItems.map((item) => {
            const Icon = ICON_MAP[item.icon];
            return (
              <NavLink
                key={item.id}
                to={item.path}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  cn(
                    'group flex items-center gap-3 px-3 py-2 rounded-xl text-[13px] font-medium transition-all duration-150',
                    isActive
                      ? 'text-blue-700 bg-blue-50/80 font-semibold border border-blue-200/60 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    {Icon && (
                      <Icon
                        size={17}
                        className={cn(
                          'flex-shrink-0 transition-colors',
                          isActive ? 'text-blue-600' : 'text-slate-400 group-hover:text-slate-600'
                        )}
                      />
                    )}
                    <span className="flex-1 truncate">{item.label}</span>
                    {isActive && <ChevronRight size={14} className="text-blue-600 opacity-80" />}
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>

        {/* Hospital Node Status Badge */}
        <div className="my-3 px-3 py-2.5 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col gap-1 text-[11px]">
          <div className="flex items-center justify-between font-semibold text-slate-700">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              Node Sync Live
            </span>
            <span className="text-[10px] text-blue-600 font-mono">ε = 1.84</span>
          </div>
          <p className="text-slate-500 truncate text-[10px]">
            {user?.role === 'hospital_staff' ? 'Boston General Hospital Node' : user?.role === 'regional_admin' ? 'East Coast Coordinator' : 'Global Health Consortium'}
          </p>
        </div>

        {/* User Footer */}
        <div className="pt-3 border-t border-slate-200">
          <div className="flex items-center gap-2.5 px-2.5 py-2 rounded-xl bg-white border border-slate-200 shadow-xs">
            <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0 shadow-xs bg-gradient-to-br from-indigo-500 to-blue-600">
              {user?.name?.charAt(0)?.toUpperCase() ?? 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-slate-900 truncate">{user?.name ?? 'Dr. Sarah Chen'}</p>
              <p className="text-[10px] text-slate-500 truncate capitalize">{user?.role?.replace('_', ' ') ?? 'Hospital Staff'}</p>
            </div>
            <button
              onClick={handleLogout}
              className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors"
              title="Logout"
            >
              <LogOut size={15} />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main Content ─────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0 bg-slate-50">
        {/* Visible Demo Environment Banner */}
        <div className="bg-amber-400 text-amber-950 px-4 py-1.5 text-xs font-semibold flex items-center justify-between border-b border-amber-500/30 flex-shrink-0">
          <div className="flex items-center gap-2 mx-auto">
            <span className="text-sm">⚠️</span>
            <span>DEMO ENVIRONMENT — Synthetic clinical and federated data only. Real PHI is prohibited.</span>
          </div>
        </div>

        {/* Top Header */}
        <header className="h-14 flex items-center justify-between px-4 sm:px-6 border-b border-slate-200 bg-white flex-shrink-0 shadow-xs">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileOpen(true)}
              className="md:hidden p-1.5 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100"
              title="Open Navigation"
            >
              <Menu size={20} />
            </button>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-xs sm:text-sm font-semibold text-slate-800">
                TrustFed Clinical Workspace
              </span>
            </div>
          </div>

          {/* Current Authenticated Role Badge */}
          <div className="flex items-center gap-2.5">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-100 border border-slate-200/80 text-xs">
              <UserCheck className="w-3.5 h-3.5 text-blue-600" />
              <span className="font-semibold text-slate-800 capitalize">
                {user?.role ? user.role.replace('_', ' ') : 'Guest'}
              </span>
              {user?.hospitalId && (
                <span className="text-slate-500 font-mono text-[11px] bg-white px-1.5 py-0.5 rounded border border-slate-200">
                  {user.hospitalId}
                </span>
              )}
              {user?.hubId && !user?.hospitalId && (
                <span className="text-slate-500 font-mono text-[11px] bg-white px-1.5 py-0.5 rounded border border-slate-200">
                  {user.hubId}
                </span>
              )}
            </div>

            <div className="flex items-center gap-1.5 text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-full font-medium">
              <ShieldCheck size={14} className="text-emerald-600" />
              <span className="hidden sm:inline">HIPAA Certified</span>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          {isBackendWakingUp && (
            <div className="mb-4 flex items-center justify-between rounded-xl border border-amber-300 bg-amber-50 px-4 py-2.5 text-xs text-amber-800 shadow-xs animate-in fade-in">
              <span className="flex items-center gap-2 font-medium">
                <Loader2 className="w-4 h-4 animate-spin text-amber-600" />
                Connecting to clinical cloud backend: server waking up from standby (Render cold-start)...
              </span>
              <span className="text-[11px] font-semibold text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full">
                Auto-retrying
              </span>
            </div>
          )}
          <Outlet />
        </main>
      </div>
    </div>
  );
}
