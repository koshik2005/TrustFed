import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Activity, BrainCircuit, FlaskConical,
  Shield, ShieldAlert, Network, BarChart3, ScrollText,
  Settings, LogOut, ChevronRight,
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
  { id: 'comparison', label: 'Model Comparison',    path: '/comparison', icon: 'BarChart3',        roles: ['global_admin'] },
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

  const visibleItems = NAV_ITEMS.filter(
    (item) => !user?.role || item.roles.includes(user.role)
  );

  const handleLogout = () => { logout(); navigate('/login'); };

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--color-bg-base)' }}>

      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <aside
        className="w-64 flex-shrink-0 flex flex-col py-6 px-3 border-r"
        style={{
          background: 'var(--color-bg-surface)',
          borderColor: 'var(--color-border)',
        }}
      >
        {/* Logo */}
        <div className="px-3 mb-8">
          <div className="flex items-center gap-2">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-900 font-bold text-sm"
              style={{ background: 'linear-gradient(135deg, #3B82F6, #06B6D4)' }}
            >
              TF
            </div>
            <div>
              <p className="font-semibold text-slate-900 text-sm leading-tight">TrustFed</p>
              <p className="text-xs" style={{ color: '#64748B' }}>Health Platform</p>
            </div>
          </div>
        </div>

        {/* Nav Items */}
        <nav className="flex-1 space-y-1">
          {visibleItems.map((item) => {
            const Icon = ICON_MAP[item.icon];
            return (
              <NavLink
                key={item.id}
                to={item.path}
                className={({ isActive }) =>
                  cn(
                    'group flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200',
                    isActive
                      ? 'text-slate-900'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  )
                }
                style={({ isActive }) => isActive ? {
                  background: 'linear-gradient(135deg, rgba(59,130,246,0.15), rgba(6,182,212,0.08))',
                  border: '1px solid rgba(59,130,246,0.2)',
                } : {}}
              >
                {({ isActive }) => (
                  <>
                    {Icon && (
                      <Icon
                        size={16}
                        className={cn(
                          'flex-shrink-0 transition-colors',
                          isActive ? 'text-blue-400' : 'text-slate-500 group-hover:text-slate-700'
                        )}
                      />
                    )}
                    <span className="flex-1">{item.label}</span>
                    {isActive && <ChevronRight size={12} className="text-blue-400 opacity-60" />}
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>

        {/* User Footer */}
        <div className="pt-4 border-t" style={{ borderColor: 'var(--color-border)' }}>
          <div className="flex items-center gap-3 px-3 py-2 rounded-xl mb-1">
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-slate-900 text-xs font-bold flex-shrink-0"
              style={{ background: 'linear-gradient(135deg, #8B5CF6, #3B82F6)' }}
            >
              {user?.name?.charAt(0)?.toUpperCase() ?? 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-slate-900 truncate">{user?.name ?? 'User'}</p>
              <p className="text-xs truncate" style={{ color: '#64748B' }}>{user?.role}</p>
            </div>
            <button
              onClick={handleLogout}
              className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
              title="Logout"
            >
              <LogOut size={14} />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main Content ─────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header */}
        <header
          className="h-14 flex items-center justify-between px-6 border-b flex-shrink-0"
          style={{ borderColor: 'var(--color-border)', background: 'var(--color-bg-surface)' }}
        >
          <div className="flex items-center gap-3">
            <span className="status-dot live" />
            <span className="text-sm text-slate-600">
              FL Hub Active
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Shield size={12} className="text-blue-400" />
            <span>End-to-End Encrypted</span>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
