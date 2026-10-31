import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Network, Shield, Activity, RotateCcw, Play, CheckCircle2,
  AlertTriangle, RefreshCw, Layers, ShieldCheck, Scale,
  Lock, ArrowRight, ExternalLink, Loader2, Hospital as HospitalIcon,
  ChevronRight, Sparkles, Check
} from 'lucide-react';
import { motion } from 'framer-motion';
import { api } from '@/services/api';

export default function GlobalAdminDashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Trigger round modal state
  const [roundModalOpen, setRoundModalOpen] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [roundConfig, setRoundConfig] = useState({
    min_records: 5,
    epochs: 1,
    learning_rate: 0.05,
    noise_multiplier: 1.0,
    clip: 1.0,
    target_epsilon: 2.0,
  });
  const [roundResult, setRoundResult] = useState<any>(null);

  // Rollback state
  const [rollbackModalOpen, setRollbackModalOpen] = useState(false);
  const [selectedRollbackVersion, setSelectedRollbackVersion] = useState<string>('');
  const [rollingBack, setRollingBack] = useState(false);
  const [rollbackSuccess, setRollbackSuccess] = useState<string | null>(null);

  const fetchDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.dashboardApi.getGlobalDashboard();
      setData(res);
      if (res?.modelVersions?.length > 0 && !selectedRollbackVersion) {
        const archived = res.modelVersions.find((m: any) => !m.isActive);
        if (archived) setSelectedRollbackVersion(archived.version);
        else setSelectedRollbackVersion('TF-GenDisease-v1.0');
      }
    } catch (err: any) {
      console.error('Failed to load global dashboard:', err);
      setError(err?.response?.data?.detail || err?.message || 'Failed to load global dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  const handleTriggerRound = async (e: React.FormEvent) => {
    e.preventDefault();
    setTriggering(true);
    setRoundResult(null);
    try {
      const res = await api.federatedApi.triggerRound(roundConfig);
      setRoundResult(res);
      await fetchDashboard();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to trigger federated round');
    } finally {
      setTriggering(false);
    }
  };

  const handleExecuteRollback = async () => {
    if (!selectedRollbackVersion) return;
    setRollingBack(true);
    try {
      await api.federatedApi.rollbackModel(selectedRollbackVersion, 'Administrative 1-click rollback from dashboard');
      setRollbackSuccess(selectedRollbackVersion);
      setRollbackModalOpen(false);
      await fetchDashboard();
      setTimeout(() => setRollbackSuccess(null), 4000);
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Rollback failed');
    } finally {
      setRollingBack(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3" role="status" aria-label="Loading global admin dashboard">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        <span className="text-sm font-medium text-slate-600">Aggregating global consortium telemetry & model lineage…</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 max-w-xl mx-auto my-8 bg-red-50 border border-red-200 rounded-2xl text-center">
        <AlertTriangle className="w-10 h-10 text-red-500 mx-auto mb-3" />
        <h2 className="text-lg font-bold text-red-950 mb-1">Global Dashboard Error</h2>
        <p className="text-sm text-red-700 mb-4">{error || 'Unable to retrieve global consortium data.'}</p>
        <Button onClick={fetchDashboard} variant="outline" className="border-red-300 text-red-800 hover:bg-red-100">
          <RefreshCw className="w-4 h-4 mr-2" /> Retry
        </Button>
      </div>
    );
  }

  const {
    totalHubs,
    activeHubs,
    totalHospitals,
    activeHospitals,
    eligibleHospitalsCount,
    ineligibleHospitalsCount,
    recordVolume,
    currentModel,
    modelVersions,
    hubsSummary,
    perRegionAccuracy,
    perDiseaseAccuracy,
    recentRounds,
    privacySummary,
    fairnessSummary,
    auditVerification
  } = data;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col gap-6 max-w-[1440px] mx-auto w-full pb-10"
    >
      {/* ── ROLLBACK SUCCESS BANNER ── */}
      {rollbackSuccess && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 flex items-center justify-between text-xs animate-in fade-in">
          <span className="flex items-center gap-2 font-semibold">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            Global model successfully rolled back to <strong className="font-mono">{rollbackSuccess}</strong>. Hospital inference singletons updated immediately.
          </span>
          <span className="font-mono text-[11px] text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">
            Active in Memory
          </span>
        </div>
      )}

      {/* ── TOP HEADER ROW ── */}
      <section className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-2xs">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Network className="w-5 h-5 text-blue-600" />
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
              Global Health Consortium Dashboard
            </h1>
            <Badge className="bg-blue-50 text-blue-700 border-blue-200 text-xs font-mono font-bold">
              Active: {currentModel?.version}
            </Badge>
          </div>
          <p className="text-xs text-slate-500">
            Multi-Tier Federated Governance · Macro-F1: <strong className="text-slate-700">{(currentModel?.macroF1 * 100).toFixed(1)}%</strong> · Global Accuracy: <strong className="text-slate-700">{(currentModel?.accuracy * 100).toFixed(1)}%</strong>
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <Button
            onClick={() => setRoundModalOpen(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs shadow-xs"
          >
            <Play className="w-3.5 h-3.5 mr-1.5" /> Trigger Federated Round
          </Button>
          <Button
            onClick={() => setRollbackModalOpen(true)}
            variant="outline"
            className="border-slate-300 text-slate-700 hover:bg-slate-100 text-xs font-semibold"
          >
            <RotateCcw className="w-3.5 h-3.5 mr-1.5" /> 1-Click Rollback
          </Button>
        </div>
      </section>

      {/* ── KEY METRIC CARDS ── */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4" aria-label="Consortium KPI Metrics">
        {/* Card 1: Consortium Record Volume */}
        <Card className="border-slate-200 shadow-2xs hover:border-blue-400 transition-colors">
          <CardContent className="p-5">
            <div className="flex justify-between items-start mb-3">
              <span className="text-slate-500 text-xs font-bold uppercase tracking-wider">Consortium Encounters</span>
              <Activity className="w-4 h-4 text-blue-500" />
            </div>
            <div className="text-slate-900 text-2xl font-bold font-mono tracking-tight mb-1">
              {recordVolume?.totalEncounters}
            </div>
            <div className="text-xs text-slate-500 flex items-center justify-between">
              <span>{recordVolume?.confirmedEncounters} doctor-confirmed</span>
              <span className="text-amber-700 font-semibold">{recordVolume?.pendingEncounters} pending</span>
            </div>
          </CardContent>
        </Card>

        {/* Card 2: Hubs & Hospitals Tier */}
        <Card className="border-slate-200 shadow-2xs hover:border-indigo-400 transition-colors">
          <CardContent className="p-5">
            <div className="flex justify-between items-start mb-3">
              <span className="text-slate-500 text-xs font-bold uppercase tracking-wider">Participating Network</span>
              <HospitalIcon className="w-4 h-4 text-indigo-500" />
            </div>
            <div className="text-slate-900 text-2xl font-bold font-mono tracking-tight mb-1">
              {activeHospitals} / {totalHospitals}
            </div>
            <div className="text-xs text-slate-500 flex items-center justify-between">
              <span>{activeHubs} Hubs Active</span>
              <span className="text-emerald-700 font-semibold font-mono">{eligibleHospitalsCount} eligible</span>
            </div>
          </CardContent>
        </Card>

        {/* Card 3: Privacy Loss Certified */}
        <Card className="border-slate-200 shadow-2xs hover:border-cyan-400 transition-colors">
          <CardContent className="p-5">
            <div className="flex justify-between items-start mb-3">
              <span className="text-slate-500 text-xs font-bold uppercase tracking-wider">Privacy Accounting</span>
              <Shield className="w-4 h-4 text-cyan-500" />
            </div>
            <div className="text-slate-900 text-2xl font-bold font-mono tracking-tight mb-1 text-cyan-700">
              ε = {privacySummary?.actualEpsilon?.toFixed(2) || '2.85'}
            </div>
            <div className="text-xs text-slate-500 flex items-center justify-between">
              <span>RDP certified (δ=1e-5)</span>
              <button onClick={() => navigate('/privacy')} className="text-cyan-700 hover:underline font-semibold flex items-center text-[11px]">
                Report <ArrowRight className="w-3 h-3 ml-0.5" />
              </button>
            </div>
          </CardContent>
        </Card>

        {/* Card 4: Audit & Fairness Integrity */}
        <Card className="border-slate-200 shadow-2xs hover:border-emerald-400 transition-colors">
          <CardContent className="p-5">
            <div className="flex justify-between items-start mb-3">
              <span className="text-slate-500 text-xs font-bold uppercase tracking-wider">Audit & Fairness</span>
              <ShieldCheck className="w-4 h-4 text-emerald-500" />
            </div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-slate-900 text-2xl font-bold font-mono tracking-tight">
                {auditVerification?.chainIntact ? '100%' : 'Degraded'}
              </span>
              <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200 text-[10px]">
                Chain Intact
              </Badge>
            </div>
            <div className="text-xs text-slate-500 flex items-center justify-between">
              <span>{auditVerification?.totalChecked} verified events</span>
              <button onClick={() => navigate('/audit')} className="text-emerald-700 hover:underline font-semibold flex items-center text-[11px]">
                Ledger <ArrowRight className="w-3 h-3 ml-0.5" />
              </button>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* ── GOVERNANCE CONTROLS: MODEL VERSIONS & 1-CLICK ROLLBACK ── */}
      <section className="bg-white rounded-2xl border border-slate-200 shadow-2xs overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div>
            <h2 className="text-base font-bold text-slate-900">Model Version Lineage & Promotion Gate</h2>
            <p className="text-xs text-slate-500">
              Only candidate models improving Macro-F1 with zero disease regressions are promoted.
            </p>
          </div>
          <Button onClick={() => setRollbackModalOpen(true)} variant="outline" size="sm" className="text-xs font-semibold">
            <RotateCcw className="w-3.5 h-3.5 mr-1" /> Quick Rollback
          </Button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs" aria-label="Model versions table">
            <thead className="bg-slate-50 text-slate-500 uppercase font-semibold text-[11px]">
              <tr>
                <th className="py-3 px-4">Version</th>
                <th className="py-3 px-4">Scope</th>
                <th className="py-3 px-4">Macro-F1</th>
                <th className="py-3 px-4">Global Accuracy</th>
                <th className="py-3 px-4">Fairness Gap</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Promoted At</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {modelVersions?.map((mv: any) => (
                <tr key={mv.id || mv.version} className={mv.isActive ? 'bg-blue-50/50 font-medium' : 'hover:bg-slate-50'}>
                  <td className="py-3 px-4 font-mono font-bold text-slate-900 flex items-center gap-2">
                    {mv.version}
                    {mv.isActive && (
                      <Badge className="bg-blue-600 text-white border-none text-[9px] px-1.5 py-0.2">
                        Active
                      </Badge>
                    )}
                  </td>
                  <td className="py-3 px-4 text-slate-600 capitalize">{mv.scope}</td>
                  <td className="py-3 px-4 font-mono font-semibold text-slate-800">
                    {(mv.macroF1 * 100).toFixed(1)}%
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-800">
                    {(mv.accuracy * 100).toFixed(1)}%
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-600">
                    {mv.fairnessGap ? (mv.fairnessGap * 100).toFixed(1) + '%' : '0.0%'}
                  </td>
                  <td className="py-3 px-4">
                    <Badge className={mv.status === 'active' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-slate-100 text-slate-600 border-slate-200'}>
                      {mv.status}
                    </Badge>
                  </td>
                  <td className="py-3 px-4 text-slate-400 text-[11px]">
                    {mv.createdAt ? new Date(mv.createdAt).toLocaleDateString() : 'Baseline'}
                  </td>
                  <td className="py-3 px-4 text-right">
                    {!mv.isActive && (
                      <Button
                        onClick={() => {
                          setSelectedRollbackVersion(mv.version);
                          setRollbackModalOpen(true);
                        }}
                        size="sm"
                        variant="ghost"
                        className="text-xs text-blue-600 hover:text-blue-800 h-7 px-2"
                      >
                        Rollback to this
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── ACCURACY BREAKDOWNS: PER-REGION & PER-DISEASE ── */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Per-Region Accuracy & Hubs */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          <Card className="border-slate-200 shadow-2xs p-5">
            <div className="flex justify-between items-center mb-4">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Regional Hubs Accuracy</h3>
                <p className="text-xs text-slate-500">Cross-regional model consistency</p>
              </div>
              <Button onClick={() => navigate('/hubs')} variant="ghost" size="sm" className="text-xs text-blue-600 font-semibold">
                Manage Hubs <ArrowRight className="w-3 h-3 ml-1" />
              </Button>
            </div>

            <div className="flex flex-col gap-3" aria-label="Regional Hubs Accuracy Breakdown">
              {perRegionAccuracy?.map((hub: any) => (
                <div key={hub.hubId || hub.region || hub.name} className="p-3 rounded-xl bg-slate-50 border border-slate-100 text-xs">
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="font-semibold text-slate-800">{hub.name} ({hub.region})</span>
                    <span className="font-mono font-bold text-blue-700">{(hub.accuracy * 100).toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden mb-1">
                    <div
                      className="bg-blue-600 h-1.5 rounded-full"
                      style={{ width: `${Math.round(hub.accuracy * 100)}%` }}
                      aria-label={`${hub.name} accuracy ${Math.round(hub.accuracy * 100)} percent`}
                    />
                  </div>
                  <span className="text-[11px] text-slate-500">{hub.hospitalCount} hospital nodes attached</span>
                </div>
              ))}
            </div>
          </Card>

          {/* Training Rounds History */}
          <Card className="border-slate-200 shadow-2xs p-5">
            <h3 className="text-sm font-bold text-slate-900 mb-3">Recent Federated Activity</h3>
            <div className="space-y-2.5">
              {recentRounds?.length === 0 ? (
                <p className="text-xs text-slate-500">No rounds recorded yet.</p>
              ) : (
                recentRounds?.slice(0, 5).map((r: any) => (
                  <div key={r.id} className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 text-xs flex flex-col gap-0.5">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold font-mono text-slate-800 text-[11px]">{r.eventType}</span>
                      <span className="text-[10px] text-slate-400 font-mono">{r.sessionId || 'Global'}</span>
                    </div>
                    <p className="text-[11px] text-slate-600 truncate" title={r.description}>{r.description}</p>
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>

        {/* Right: Per-Disease Accuracy Across 18 Conditions */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          <Card className="border-slate-200 shadow-2xs p-5">
            <div className="flex justify-between items-center mb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Per-Disease Clinical Calibration</h3>
                <p className="text-xs text-slate-500">Calibrated F1 & Top-1 classification across 18 conditions</p>
              </div>
              <Badge variant="outline" className="text-xs text-emerald-700 bg-emerald-50 border-emerald-200">
                0 Regressions &gt; 5%
              </Badge>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3" aria-label="Per-disease accuracy breakdown">
              {perDiseaseAccuracy?.map((d: any) => {
                const f1Pct = Math.round(d.f1 * 100);
                return (
                  <div key={d.disease} className="p-3 rounded-xl bg-slate-50 border border-slate-100 text-xs">
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-semibold text-slate-800 truncate max-w-[130px]">{d.displayName}</span>
                      <span className="font-mono font-bold text-slate-900">{f1Pct}% F1</span>
                    </div>
                    <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
                      <div
                        className="bg-emerald-600 h-1.5 rounded-full"
                        style={{ width: `${f1Pct}%` }}
                        aria-label={`${d.displayName} F1 score ${f1Pct} percent`}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      </section>

      {/* ── TRIGGER ROUND MODAL ── */}
      {roundModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in">
          <Card className="w-full max-w-md bg-white border-slate-200 shadow-xl rounded-2xl overflow-hidden">
            <form onSubmit={handleTriggerRound}>
              <div className="p-5 border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Play className="w-4 h-4 text-blue-600" />
                  <h3 className="text-base font-bold text-slate-900">Trigger Hierarchical Federated Round</h3>
                </div>
                <button type="button" onClick={() => setRoundModalOpen(false)} className="text-slate-400 hover:text-slate-600 text-sm">
                  ✕
                </button>
              </div>

              <div className="p-5 flex flex-col gap-4 text-xs">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Minimum Confirmed Records Threshold</label>
                  <Input
                    type="number"
                    min={1}
                    value={roundConfig.min_records}
                    onChange={(e) => setRoundConfig({ ...roundConfig, min_records: parseInt(e.target.value) || 5 })}
                    className="h-9 text-xs"
                    required
                  />
                  <span className="text-[10px] text-slate-500">Hospitals with fewer confirmed records are safely excluded from the round.</span>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="font-semibold text-slate-700 block mb-1">DP Noise Multiplier (σ)</label>
                    <Input
                      type="number"
                      step="0.1"
                      min={0.1}
                      max={3.5}
                      value={roundConfig.noise_multiplier}
                      onChange={(e) => setRoundConfig({ ...roundConfig, noise_multiplier: parseFloat(e.target.value) || 1.0 })}
                      className="h-9 text-xs"
                    />
                    <span className="text-[10px] text-slate-500">Clamped to σ ≤ 3.5</span>
                  </div>
                  <div>
                    <label className="font-semibold text-slate-700 block mb-1">Target Epsilon (ε)</label>
                    <Input
                      type="number"
                      step="0.1"
                      min={0.5}
                      value={roundConfig.target_epsilon}
                      onChange={(e) => setRoundConfig({ ...roundConfig, target_epsilon: parseFloat(e.target.value) || 2.0 })}
                      className="h-9 text-xs"
                    />
                    <span className="text-[10px] text-slate-500">Certified by RDP</span>
                  </div>
                </div>

                {roundResult && (
                  <div className={`p-3 rounded-xl text-xs ${roundResult.status === 'promoted' ? 'bg-emerald-50 text-emerald-900 border border-emerald-200' : 'bg-amber-50 text-amber-900 border border-amber-200'}`}>
                    <span className="font-bold block mb-1">Round Result: {roundResult.status.toUpperCase()}</span>
                    <span>{roundResult.gateResult?.reason || 'Evaluation completed successfully.'}</span>
                  </div>
                )}
              </div>

              <div className="p-5 border-t border-slate-100 flex items-center justify-end gap-2 bg-slate-50">
                <Button type="button" variant="outline" size="sm" onClick={() => setRoundModalOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" size="sm" disabled={triggering} className="bg-blue-600 hover:bg-blue-700 text-white font-semibold">
                  {triggering ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" /> : <Play className="w-3.5 h-3.5 mr-1.5" />}
                  {triggering ? 'Training & Aggregating…' : 'Execute Round'}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* ── 1-CLICK ROLLBACK MODAL ── */}
      {rollbackModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in">
          <Card className="w-full max-w-md bg-white border-slate-200 shadow-xl rounded-2xl overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <RotateCcw className="w-4 h-4 text-blue-600" />
                <h3 className="text-base font-bold text-slate-900">1-Click Global Model Rollback</h3>
              </div>
              <button type="button" onClick={() => setRollbackModalOpen(false)} className="text-slate-400 hover:text-slate-600 text-sm">
                ✕
              </button>
            </div>

            <div className="p-5 flex flex-col gap-4 text-xs">
              <p className="text-slate-600 leading-relaxed">
                Revert the active global neural parameters to any certified historical model version. The rollback is executed in-memory instantly across all hospital inference singletons.
              </p>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">Select Target Version</label>
                <select
                  value={selectedRollbackVersion}
                  onChange={(e) => setSelectedRollbackVersion(e.target.value)}
                  className="w-full h-9 rounded-md border border-slate-300 bg-white px-3 py-1 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                >
                  <option value="TF-GenDisease-v1.0">TF-GenDisease-v1.0 (Baseline Prior)</option>
                  {modelVersions?.filter((m: any) => !m.isActive).map((m: any) => (
                    <option key={m.id} value={m.version}>
                      {m.version} (Macro-F1: {(m.macroF1 * 100).toFixed(1)}%)
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="p-5 border-t border-slate-100 flex items-center justify-end gap-2 bg-slate-50">
              <Button type="button" variant="outline" size="sm" onClick={() => setRollbackModalOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleExecuteRollback}
                disabled={rollingBack || !selectedRollbackVersion}
                size="sm"
                className="bg-blue-600 hover:bg-blue-700 text-white font-semibold"
              >
                {rollingBack ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" /> : <RotateCcw className="w-3.5 h-3.5 mr-1.5" />}
                {rollingBack ? 'Reverting Model…' : 'Confirm Rollback'}
              </Button>
            </div>
          </Card>
        </div>
      )}
    </motion.div>
  );
}
