import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Loader2, ShieldAlert } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { api } from '@/services/api';
import type { FairnessReport } from '@/types';

type Row = FairnessReport['subgroupResults'][number] & { shapP?: number; topFeatures?: string[]; tpr?: number; fpr?: number };

const pct = (x: number | undefined | null) => (x == null || Number.isNaN(x) ? '—' : `${(x * 100).toFixed(1)}%`);

export default function FairnessPage() {
  const navigate = useNavigate();
  const [report, setReport] = useState<FairnessReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.teflApi
      .getFairnessReport('latest')
      .then(setReport)
      .catch((e) => setError(e?.response?.data?.detail ?? 'Could not load the fairness report'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[50vh]">
        <Loader2 className="h-8 w-8 animate-spin text-cyan-500" />
      </div>
    );
  }
  if (!report) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] p-8 max-w-lg mx-auto text-center">
        <div className="w-16 h-16 rounded-full bg-blue-50 border border-blue-200 flex items-center justify-center mb-4 text-blue-500 shadow-sm">
          <ShieldAlert className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-bold text-slate-900 mb-2">No Fairness Audit Report Available</h2>
        <p className="text-sm text-slate-600 mb-6">
          {error || 'Fairness metrics are generated automatically on the held-out test cohort after a training session completes.'}
        </p>
        <Button onClick={() => navigate('/training')} className="bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-semibold shadow-md">
          Go to Global Training
        </Button>
      </div>
    );
  }

  const rows = report.subgroupResults as Row[];

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
      className="flex flex-col gap-6 max-w-[1440px] mx-auto w-full pb-8">
      <header>
        <h1 className="text-[24px] font-bold text-slate-900 tracking-tight">Fairness Audit</h1>
        <p className="text-slate-600 text-[13px]">
          Subgroup accuracy and SHAP-importance divergence (permutation test) · Session {report.sessionId}
        </p>
      </header>

      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="glass-card bg-white border-slate-200"><CardContent className="p-6">
          <div className="text-[12px] uppercase tracking-wider font-semibold text-slate-600 mb-2">Fairness score</div>
          <div className="font-mono text-[36px] font-bold text-slate-900 leading-none mb-2">{pct(report.overallScore)}</div>
          <div className="text-slate-500 text-[12px]">1 − largest subgroup accuracy gap (groups with n ≥ 15)</div>
        </CardContent></Card>
        <Card className="glass-card bg-white border-slate-200"><CardContent className="p-6">
          <div className="text-[12px] uppercase tracking-wider font-semibold text-slate-600 mb-2">Flags raised</div>
          <div className="font-mono text-[36px] font-bold text-slate-900 leading-none mb-2">{report.flaggedIssues.length}</div>
          <div className="text-slate-500 text-[12px]">accuracy gap &gt; 10 pts, or SHAP profile differs (p &lt; 0.05)</div>
        </CardContent></Card>
        <Card className="glass-card bg-white border-slate-200"><CardContent className="p-6">
          <div className="text-[12px] uppercase tracking-wider font-semibold text-slate-600 mb-2">Subgroups audited</div>
          <div className="font-mono text-[36px] font-bold text-slate-900 leading-none mb-2">{rows.length}</div>
          <div className="text-slate-500 text-[12px]">sex, age band, hospital site (held-out test set)</div>
        </CardContent></Card>
      </section>

      {report.flaggedIssues.length > 0 && (
        <Card className="glass-card bg-white border-slate-200"><CardContent className="p-6 flex flex-col gap-3">
          <h2 className="text-lg font-semibold text-slate-900">Flags</h2>
          {report.flaggedIssues.map((f, i) => (
            <div key={i} className="flex items-start gap-3 text-sm text-slate-700">
              <Badge className={f.severity === 'high' ? 'bg-red-500/20 text-red-600 border-none' : 'bg-amber-500/20 text-amber-600 border-none'}>
                {f.severity.toUpperCase()}
              </Badge>
              <span><strong>{f.subgroup}</strong> — {f.message}</span>
            </div>
          ))}
        </CardContent></Card>
      )}

      <Card className="glass-card bg-white border-slate-200"><CardContent className="p-6 overflow-x-auto">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Subgroup results</h2>
        <table className="w-full text-sm text-left">
          <thead className="text-slate-600 text-[12px] uppercase tracking-wider">
            <tr>
              <th className="py-2 pr-4">Subgroup</th><th className="pr-4">n</th><th className="pr-4">Accuracy</th>
              <th className="pr-4">TPR</th><th className="pr-4">FPR</th><th className="pr-4">SHAP JS-div.</th>
              <th className="pr-4">p-value</th><th>Top features</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.subgroup} className="border-t border-slate-200 text-slate-800">
                <td className="py-2 pr-4 font-medium">{r.subgroup}</td>
                <td className="pr-4 font-mono">{r.sampleSize}</td>
                <td className="pr-4 font-mono">{pct(r.accuracy)}</td>
                <td className="pr-4 font-mono">{pct(r.tpr)}</td>
                <td className="pr-4 font-mono">{pct(r.fpr)}</td>
                <td className="pr-4 font-mono">{r.divergenceScore.toFixed(3)}</td>
                <td className="pr-4 font-mono">{r.shapP != null ? r.shapP.toFixed(3) : '—'}</td>
                <td className="text-slate-600">{(r.topFeatures ?? []).join(', ')}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="text-[12px] text-slate-500 mt-4">
          Small subgroups give noisy estimates; treat flags as prompts for review, not verdicts.
        </p>
      </CardContent></Card>
    </motion.div>
  );
}
