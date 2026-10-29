import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Clock, Stethoscope, ArrowRight, CheckCircle2,
  AlertCircle, Loader2, Sparkles, User, RefreshCw
} from 'lucide-react';
import { clinicalApi } from '@/services/api';
import type { ClinicalEncounter } from '@/types';
import { useAuthStore } from '@/store/authStore';

export default function PendingConfirmationsPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [encounters, setEncounters] = useState<ClinicalEncounter[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPending = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await clinicalApi.listEncounters({ status: 'pending' });
      setEncounters(res.items);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load pending encounters.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPending();
  }, []);

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      {/* Top Banner */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-blue-600 font-semibold text-xs uppercase tracking-wider mb-1">
            <Stethoscope size={16} />
            Physician Review Queue
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Pending Doctor Confirmations
          </h1>
          <p className="text-slate-500 text-sm mt-0.5">
            Encounters awaiting attending physician diagnosis confirmation before being marked trainable.
          </p>
        </div>

        <button
          onClick={fetchPending}
          disabled={isLoading}
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 transition-all self-start sm:self-auto disabled:opacity-60"
        >
          <RefreshCw size={14} className={isLoading ? "animate-spin" : ""} />
          Refresh Queue
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5 text-rose-600" />
          <div>
            <p className="font-semibold text-sm">Error Loading Queue</p>
            <p className="text-xs mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Queue List */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-16 text-slate-400 space-y-3">
            <Loader2 className="w-7 h-7 animate-spin text-blue-600" />
            <p className="text-xs font-medium">Fetching encounters pending confirmation...</p>
          </div>
        ) : encounters.length === 0 ? (
          <div className="text-center py-16 px-4">
            <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto mb-3">
              <CheckCircle2 size={24} />
            </div>
            <h3 className="text-sm font-bold text-slate-900">All caught up!</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              There are no pending patient encounters requiring doctor confirmation at this time. All records have been verified.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {encounters.map((enc) => {
              const p = enc.patient;
              const topPred = enc.predictedTop3 && enc.predictedTop3.length > 0 ? enc.predictedTop3[0] : null;

              return (
                <div
                  key={enc.id}
                  className="p-5 hover:bg-slate-50/70 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4"
                >
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center gap-2.5">
                      <span className="font-mono text-xs font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-md">
                        {enc.encounterIdentifier}
                      </span>
                      <span className="text-sm font-bold text-slate-900">
                        {p?.name || 'Anonymous Patient'}
                      </span>
                      <span className="text-xs text-slate-400">
                        ({p?.age} yrs · {p?.sexLabel})
                      </span>
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-md border border-amber-200/60">
                        <Clock size={11} /> Pending
                      </span>
                    </div>

                    <div className="flex flex-wrap gap-1.5 pt-1">
                      <span className="text-xs text-slate-400 font-medium self-center mr-1">Symptoms:</span>
                      {enc.symptoms.slice(0, 4).map((s) => (
                        <span
                          key={s}
                          className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-100 text-slate-700 capitalize"
                        >
                          {s.replace(/_/g, ' ')}
                        </span>
                      ))}
                      {enc.symptoms.length > 4 && (
                        <span className="text-[11px] text-slate-400 self-center">
                          +{enc.symptoms.length - 4} more
                        </span>
                      )}
                    </div>
                  </div>

                  {/* AI Prediction & Action */}
                  <div className="flex items-center gap-4 shrink-0">
                    {topPred && (
                      <div className="text-right">
                        <div className="flex items-center gap-1 text-[11px] text-slate-400 font-medium justify-end">
                          <Sparkles size={12} className="text-blue-500" /> Top AI Prediction:
                        </div>
                        <div className="text-xs font-bold text-slate-900">
                          {topPred.disease} ({Math.round(topPred.probability * 100)}%)
                        </div>
                      </div>
                    )}

                    <button
                      onClick={() => navigate(`/encounters/${enc.id}`)}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 shadow-xs transition-all"
                    >
                      <span>Review & Confirm</span>
                      <ArrowRight size={13} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
