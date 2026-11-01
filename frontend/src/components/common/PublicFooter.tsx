import React from 'react';
import { Link } from 'react-router-dom';
import { Shield, AlertTriangle, Cookie, HeartPulse, Scale, FileText } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { cn } from '@/lib/utils';

interface PublicFooterProps {
  className?: string;
}

export default function PublicFooter({ className }: PublicFooterProps) {
  const { appMode } = useAuthStore();

  return (
    <footer className={cn("w-full bg-white border-t border-slate-200 py-4 px-4 sm:px-8 text-xs text-slate-500 z-10 shadow-xs", className)}>
      <div className="max-w-7xl mx-auto flex flex-col gap-3">
        {/* Top Row: Mode Badge + Legal Links */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded-md flex items-center justify-center bg-blue-600 text-white font-bold text-[10px]">
              TF
            </div>
            <span
              className={cn(
                "px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider",
                appMode === 'clinical'
                  ? "bg-purple-100 text-purple-800 border border-purple-200"
                  : "bg-blue-100 text-blue-800 border border-blue-200"
              )}
            >
              Mode: {appMode === 'clinical' ? 'Clinical (Consented Live Data)' : 'Informational (Educational Prototype)'}
            </span>
            <span className="text-slate-300">|</span>
            <span className="inline-flex items-center gap-1 text-[11px] text-slate-500">
              <Cookie className="w-3 h-3 text-slate-400" />
              Essential cookies only (zero tracking)
            </span>
          </div>

          {/* Public Legal Navigation Links */}
          <nav className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1.5 text-xs font-medium text-slate-600">
            <Link to="/intended-use" className="hover:text-blue-600 hover:underline transition-colors">
              Intended Use
            </Link>
            <span className="text-slate-300">•</span>
            <Link to="/terms" className="hover:text-blue-600 hover:underline transition-colors">
              Terms of Use
            </Link>
            <span className="text-slate-300">•</span>
            <Link to="/privacy-policy" className="hover:text-blue-600 hover:underline transition-colors">
              Privacy Policy
            </Link>
            <span className="text-slate-300">•</span>
            <Link to="/disclaimer" className="hover:text-blue-600 hover:underline transition-colors">
              Medical Disclaimer
            </Link>
            <span className="text-slate-300">•</span>
            <Link to="/grievance" className="hover:text-blue-600 hover:underline transition-colors">
              Contact & Grievance
            </Link>
          </nav>
        </div>

        {/* Bottom Row: Mandatory Persistent Medical & Emergency Disclaimer */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-2 text-center md:text-left">
          <p className="text-[11px] text-slate-600 font-medium leading-relaxed max-w-4xl">
            <strong>Emergency & Regulatory Notice:</strong> Educational decision support. Not medical advice. Not clinically validated.
            In an emergency, call your local emergency number immediately (<strong>112</strong> in India, <strong>911</strong> in US/Canada, <strong>999</strong> in UK).
          </p>
          <span className="text-[10px] text-slate-400 whitespace-nowrap">
            All policies marked [DRAFT, pending legal review]
          </span>
        </div>
      </div>
    </footer>
  );
}

