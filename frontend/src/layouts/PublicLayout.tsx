import React from 'react';
import { Outlet, Link } from 'react-router-dom';
import { HeartPulse, ArrowLeft, ShieldAlert } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import PublicFooter from '@/components/common/PublicFooter';

export default function PublicLayout() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 font-sans">
      {/* Top Header */}
      <header className="w-full bg-white border-b border-slate-200 py-3.5 px-4 sm:px-8 sticky top-0 z-30 shadow-2xs">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-8 h-8 rounded-xl flex items-center justify-center text-white font-bold text-sm shadow-md bg-gradient-to-br from-blue-600 via-blue-500 to-cyan-500 group-hover:scale-105 transition-transform">
              <HeartPulse className="w-4 h-4" />
            </div>
            <div>
              <p className="font-bold text-slate-900 text-sm leading-tight tracking-tight">TrustFed-Health</p>
              <p className="text-[10px] text-slate-500 font-medium">Public Transparency & Legal Center</p>
            </div>
          </Link>

          <div className="flex items-center gap-3">
            <Badge variant="outline" className="bg-amber-50 text-amber-800 border-amber-300 text-[10px] font-semibold hidden sm:inline-flex items-center gap-1">
              <ShieldAlert className="w-3 h-3 text-amber-600" />
              DRAFT, pending legal review
            </Badge>

            <Link to="/login">
              <Button size="sm" variant="outline" className="text-xs font-semibold h-8 border-slate-300">
                <ArrowLeft className="w-3.5 h-3.5 mr-1" />
                Back to Platform
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 py-8 px-4 sm:px-8">
        <div className="max-w-4xl mx-auto bg-white border border-slate-200 rounded-2xl p-6 sm:p-10 shadow-sm">
          <Outlet />
        </div>
      </main>

      {/* Universal Footer */}
      <PublicFooter />
    </div>
  );
}

