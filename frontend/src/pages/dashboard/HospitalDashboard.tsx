import React, { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Database, CheckCircle2, Shield, Lock, RefreshCw } from 'lucide-react';
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { motion } from 'framer-motion';
import { api } from '@/services/api';
import type { Hospital, TrainingSession } from '@/types';

export default function HospitalDashboard() {
  const [hospital, setHospital] = useState<Hospital | null>(null);
  const [session, setSession] = useState<TrainingSession | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [hospitals, latestSession] = await Promise.all([
          api.trainingApi.getHospitals(),
          api.trainingApi.getLatestSession(),
        ]);
        // Show the first (primary) hospital for this dashboard view
        if (hospitals && hospitals.length > 0) setHospital(hospitals[0]);
        setSession(latestSession);
      } catch (e) {
        console.error('Dashboard load failed', e);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Build dynamic loss chart data from session round progress
  const totalRounds = session?.totalRounds || 5;
  const currentRound = session?.currentRound || 0;
  const lossData = (session?.metrics ?? []).map((m) => ({ epoch: `R${m.round}`, dpLoss: m.loss }));

  const privacyBudget = session?.privacyBudget ?? null;
  const totalEpochs   = hospital?.totalEpochs ?? 5;
  const currentEpoch  = hospital?.currentEpoch ?? 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col gap-8 max-w-[1440px] mx-auto w-full pb-8"
    >
      {/* PAGE HEADER ROW */}
      <section className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-slate-900 font-bold text-2xl tracking-tight">
            {loading ? 'Loading…' : hospital?.name ?? 'Hospital Dashboard'}
          </h1>
          <div className="flex items-center gap-2 mt-1">
            <span className="status-dot live" />
            <span className="text-slate-600 text-sm">
              Connected to Regional Hub — {hospital?.region ?? '…'}
            </span>
          </div>
        </div>

        <div className="bg-blue-50 border border-blue-200 text-blue-600 text-[13px] px-4 py-1.5 rounded-full font-medium flex items-center gap-2">
          <RefreshCw className={`h-3.5 w-3.5 ${session?.status === 'running' ? 'animate-spin' : ''}`} />
          Round {session?.currentRound ?? 0} / {session?.totalRounds ?? 20} · {session?.status ?? 'Idle'}
        </div>
      </section>

      {/* STAT CARDS ROW */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="glass-card hover:border-blue-500/30 transition-colors border-slate-200">
          <CardContent className="p-6">
            <div className="flex justify-between items-start mb-4">
              <span className="text-slate-600 text-xs uppercase tracking-wider font-semibold">Local Dataset</span>
              <Database className="text-blue-400 h-5 w-5" />
            </div>
            <div>
              <div className="text-slate-900 text-[28px] font-bold font-mono tracking-tight mb-1">
                {loading ? '…' : (hospital?.localDatasetSize?.toLocaleString() ?? 'N/A')}
              </div>
              <div className="text-slate-600 text-xs">records</div>
            </div>
          </CardContent>
        </Card>

        <Card className="glass-card hover:border-blue-500/30 transition-colors border-slate-200">
          <CardContent className="p-6">
            <div className="flex justify-between items-start mb-4">
              <span className="text-slate-600 text-xs uppercase tracking-wider font-semibold">Local Epochs</span>
              <CheckCircle2 className="text-emerald-400 h-5 w-5" />
            </div>
            <div>
              <div className="text-slate-900 text-[28px] font-bold font-mono tracking-tight mb-1">
                {currentEpoch} / {totalEpochs}
              </div>
              <div className="text-slate-600 text-xs">
                {currentEpoch >= totalEpochs ? 'All complete' : 'In progress'}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="glass-card hover:border-blue-500/30 transition-colors border-slate-200">
          <CardContent className="p-6">
            <div className="flex justify-between items-start mb-4">
              <span className="text-slate-600 text-xs uppercase tracking-wider font-semibold">Privacy Budget</span>
              <Shield className="text-cyan-400 h-5 w-5" />
            </div>
            <div>
              <div className="text-slate-900 text-[28px] font-bold font-mono tracking-tight mb-1">
                {typeof privacyBudget === 'number' ? `ε = ${privacyBudget.toFixed(2)}` : 'No DP'}
              </div>
              <div className="text-slate-600 text-xs">worst-case hospital, δ = 1e-5</div>
            </div>
          </CardContent>
        </Card>

        <Card className="glass-card hover:border-blue-500/30 transition-colors border-slate-200">
          <CardContent className="p-6">
            <div className="flex justify-between items-start mb-4">
              <span className="text-slate-600 text-xs uppercase tracking-wider font-semibold">Global Accuracy</span>
              <Lock className="text-violet-400 h-5 w-5" />
            </div>
            <div>
              <div className="text-slate-900 text-[28px] font-bold font-mono tracking-tight mb-1">
                {session?.globalAccuracy != null
                  ? (session.globalAccuracy * 100).toFixed(1) + '%'
                  : 'N/A'}
              </div>
              <div className="text-slate-600 text-xs">Global FL model</div>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* MAIN GRID */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT CHART */}
        <Card className="glass-card lg:col-span-8 p-6 flex flex-col border-slate-200">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-slate-900 font-semibold text-lg">Global Model Test Loss per Round</h2>
            <div className="flex gap-4 text-xs">
              <div className="flex items-center gap-2">
                <div className="w-3 h-0.5 bg-blue-500" />
                <span className="text-slate-600">Test loss</span>
              </div>
            </div>
          </div>

          <div className="flex-grow w-full h-[260px] relative">
            {lossData.length === 0 ? (
              <div className="flex items-center justify-center h-full text-slate-500 text-sm">
                No training data yet. Start a session on the Global Monitor page.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={lossData} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="dpGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#1D6BF3" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#1D6BF3" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="epoch" stroke="#475569" fontSize={10} tickLine={false} axisLine={false} />
                  <YAxis stroke="#475569" fontSize={10} tickLine={false} axisLine={false} tickFormatter={(v) => v.toFixed(1)} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                    itemStyle={{ color: '#334155' }}
                  />
                  <Area type="monotone" dataKey="dpLoss"   name="With DP"    stroke="#1D6BF3" strokeWidth={2} fillOpacity={1} fill="url(#dpGradient)" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>

        {/* RIGHT TIMELINE */}
        <Card className="glass-card lg:col-span-4 p-6 flex flex-col border-slate-200">
          <h2 className="text-slate-900 font-semibold text-lg mb-6">Training Activity</h2>

          <div className="relative pl-6 space-y-8 flex-grow">
            <div className="absolute left-[11px] top-2 bottom-2 w-px border-l border-dashed border-slate-300" />

            {[
              { label: 'Dataset Loaded',        done: currentRound >= 1, icon: <CheckCircle2 className="text-emerald-500 h-4 w-4" /> },
              { label: 'Model Initialized',     done: currentRound >= 1, icon: <CheckCircle2 className="text-emerald-500 h-4 w-4" /> },
              { label: `LDP Applied — ε=${typeof privacyBudget === 'number' ? privacyBudget.toFixed(3) : '…'}`, done: currentRound >= 1, icon: <CheckCircle2 className="text-emerald-500 h-4 w-4" /> },
              { label: session?.status === 'running' ? 'Encrypting Update…' : (session?.status === 'Completed' ? 'Updates Sent ✓' : 'Awaiting Session'), done: false, icon: session?.status === 'running' ? <RefreshCw className="text-blue-500 h-4 w-4 animate-spin" /> : <CheckCircle2 className="text-slate-400 h-4 w-4" /> },
            ].map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className="relative flex flex-col gap-1"
              >
                <div className="absolute -left-[30px] bg-white rounded-full p-0.5">
                  {item.icon}
                </div>
                <div className={`text-sm ${item.done ? 'text-slate-800' : 'text-blue-600 font-medium'}`}>
                  {item.label}
                </div>
              </motion.div>
            ))}
          </div>
        </Card>
      </section>
    </motion.div>
  );
}
