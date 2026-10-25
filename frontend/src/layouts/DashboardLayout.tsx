import { useState } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Activity, BrainCircuit, FlaskConical,
  Shield, ShieldAlert, Network, BarChart3, ScrollText,
  Settings, LogOut, ChevronRight, Menu, X,
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { cn } from '@/utils';
import type { NavItem } from '@/types';

const NAV_ITEMS: NavItem[] = [
  { id: 'dashboard',  label: 'Hospital Dashboard', path: '/dashboard',  icon: 'LayoutDashboard', roles: ['hospital_staff', 'regional_admin', 'global_admin'] },
  { id: 'training',   label: 'Global Training',    path: '/training',   icon: 'Activity',         roles: ['regional_admin', 'global_admin'] },
  { id: 'prediction', label: 'Patient Prediction', path: '/prediction', icon: 'BrainCircuit',     roles: ['hospital_staff', 'regional_admin', 'global_admin'] },
  { id: 'explain',    label: 'Explainability',      path: '/explain',    icon: 'FlaskConical',     roles: ['hospital_staff', 'regional_admin', 'global_admin'] },
  { id: 'fairness',   label: 'Fairness Audit',      path: '/fairness',   icon: 'ShieldAlert',      roles: ['regional_admin', 'global_admin'] },
  { id: 'privacy',    label: 'Privacy Report',      path: '/privacy',    icon: 'Shield',           roles: ['regional_admin', 'global_admin'] },
  { id: 'regional',   label: 'Regional Hub',        path: '/regional',   icon: 'Network',          roles: ['regional_admin', 'global_admin'] },
  { id: 'comparison', label: 'Model Comparison',    path: '/comparison', icon: 'BarChart3',        roles: ['regional_admin', 'global_admin'] },
  { id: 'audit',      label: 'Audit Log',           path: '/audit',      icon: 'ScrollText',       roles: ['regional_admin', 'global_admin'] },
  { id: 'settings',   label: 'Settings',            path: '/settings',   icon: 'Settings',         roles: ['hospital_staff', 'regional_admin', 'global_admin'] },
];

const ICON_MAP: Record<string, React.ComponentType<{ size?: number; className?: string }>> = {
  LayoutDashboard, Activity, BrainCircuit, FlaskConical,
  Shield, ShieldAlert, Network, BarChart3, ScrollText, Settings,
};

export default function DashboardLayout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const visibleItems = NAV_ITEMS.filter(
    (item) => !user?.role || item.roles.includes(user.role)
  );

  const handleLogout = () => { logout(); navigate('/login'); };

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--color-bg-base)' }}>

      {/* ── Mobile Sidebar Overlay ───────────────────────────────────────── */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-40 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 flex flex-col py-6 px-3 border-r transition-transform duration-200 ease-in-out md:static md:translate-x-0",
          mobileOpen ? "translate-x-0 shadow-2xl" : "-translate-x-full"
        )}
        style={{
          background: 'var(--color-bg-surface)',
          borderColor: 'var(--color-border)',
        }}
      >
        {/* Logo */}
        <div className="px-3 mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-sm shadow-md"
              style={{ background: 'linear-gradient(135deg, #3B82F6, #06B6D4)' }}
            >
              TF
            </div>
            <div>
              <p className="font-semibold text-slate-900 text-sm leading-tight">TrustFed</p>
              <p className="text-xs text-slate-500">Health Platform</p>
            </div>
          </div>
          <button
            onClick={() => setMobileOpen(false)}
            className="md:hidden p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
          >
            <X size={18} />
          </button>
        </div>

        {/* Nav Items */}
        <nav className="flex-1 space-y-1 overflow-y-auto">
          {visibleItems.map((item) => {
            const Icon = ICON_MAP[item.icon];
            return (
              <NavLink
                key={item.id}
                to={item.path}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  cn(
                    'group flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200',
                    isActive
                      ? 'text-blue-600 bg-blue-50 border border-blue-200/60 font-semibold shadow-xs'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    {Icon && (
                      <Icon
                        size={16}
                        className={cn(
                          'flex-shrink-0 transition-colors',
                          isActive ? 'text-blue-600' : 'text-slate-400 group-hover:text-slate-600'
                        )}
                      />
                    )}
                    <span className="flex-1">{item.label}</span>
                    {isActive && <ChevronRight size={14} className="text-blue-600 opacity-70" />}
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>

        {/* User Footer */}
        <div className="pt-4 border-t" style={{ borderColor: 'var(--color-border)' }}>
          <div className="flex items-center gap-3 px-3 py-2 rounded-xl bg-slate-50 border border-slate-200/60">
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0 shadow-sm"
              style={{ background: 'linear-gradient(135deg, #8B5CF6, #3B82F6)' }}
            >
              {user?.name?.charAt(0)?.toUpperCase() ?? 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-slate-900 truncate">{user?.name ?? 'User'}</p>
              <p className="text-[11px] text-slate-500 truncate capitalize">{user?.role?.replace('_', ' ')}</p>
            </div>
            <button
              onClick={handleLogout}
              className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors"
              title="Logout"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main Content ─────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Top Header */}
        <header
          className="h-14 flex items-center justify-between px-4 sm:px-6 border-b flex-shrink-0"
          style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg-surface)' }}
        >
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileOpen(true)}
              className="md:hidden p-1.5 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100"
              title="Open Navigation"
            >
              <Menu size={20} />
            </button>
            <span className="status-dot live" />
            <span className="text-sm font-medium text-slate-700">
              TrustFed-Health Platform
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Shield size={14} className="text-blue-500" />
            <span className="hidden sm:inline">End-to-End Encrypted & Audited</span>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
