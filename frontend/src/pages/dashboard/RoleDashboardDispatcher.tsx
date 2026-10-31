import React, { useState } from 'react';
import { useAuthStore } from '@/store/authStore';
import HospitalDashboard from './HospitalDashboard';
import RegionalDashboard from './RegionalDashboard';
import GlobalAdminDashboard from './GlobalAdminDashboard';
import { Badge } from '@/components/ui/badge';
import { ShieldCheck, Network, Hospital as HospitalIcon } from 'lucide-react';

export default function RoleDashboardDispatcher() {
  const { user } = useAuthStore();
  const [adminViewTier, setAdminViewTier] = useState<'global' | 'regional' | 'hospital'>('global');

  if (!user) {
    return <HospitalDashboard />;
  }

  // Hospital staff and doctors only see Hospital Dashboard
  if (user.role === 'hospital_staff' || user.role === 'doctor') {
    return <HospitalDashboard />;
  }

  // Regional Admin sees Regional Hub Dashboard
  if (user.role === 'regional_admin') {
    return <RegionalDashboard />;
  }

  // Global Admin has access to all tiers with quick switcher
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between bg-white p-3 px-4 rounded-xl border border-slate-200 shadow-2xs text-xs">
        <div className="flex items-center gap-2 text-slate-700 font-semibold">
          <ShieldCheck className="w-4 h-4 text-blue-600" />
          <span>Global Administrator Tier Inspection:</span>
        </div>
        <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-lg">
          <button
            onClick={() => setAdminViewTier('global')}
            className={`px-3 py-1 rounded-md font-semibold transition-all ${
              adminViewTier === 'global' ? 'bg-white text-blue-700 shadow-2xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Global Consortium
          </button>
          <button
            onClick={() => setAdminViewTier('regional')}
            className={`px-3 py-1 rounded-md font-semibold transition-all ${
              adminViewTier === 'regional' ? 'bg-white text-blue-700 shadow-2xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Regional Hub View
          </button>
          <button
            onClick={() => setAdminViewTier('hospital')}
            className={`px-3 py-1 rounded-md font-semibold transition-all ${
              adminViewTier === 'hospital' ? 'bg-white text-blue-700 shadow-2xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Hospital Node View
          </button>
        </div>
      </div>

      {adminViewTier === 'global' && <GlobalAdminDashboard />}
      {adminViewTier === 'regional' && <RegionalDashboard />}
      {adminViewTier === 'hospital' && <HospitalDashboard />}
    </div>
  );
}
