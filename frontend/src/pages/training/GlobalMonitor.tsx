import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Cloud, Network, CheckCircle2, RefreshCw, Loader2 } from 'lucide-react';
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, ReferenceLine } from 'recharts';
import { motion } from 'framer-motion';
import { api } from '@/services/api';
import type { TrainingSession } from '@/types';



export default function GlobalMonitor() {
  const [session, setSession] = useState<TrainingSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState('');

  // Fetch session status on mount
  const fetchStatus = async () => {
    try {
      const data = await api.trainingApi.getLatestSession();
      setSession(data);
    } catch (error) {
      console.error("Failed to load session status");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    // Poll every 3 seconds for responsive training telemetry
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleStartSession = async () => {
    setIsStarting(true);
    setStartError('');
    try {
      const saved = JSON.parse(localStorage.getItem('tf_settings') ?? '{}');
      await api.trainingApi.startSession({ rounds: 20, ...saved });
      await fetchStatus(); // Refresh immediately after starting
    } catch (e: any) {
      setStartError(e?.response?.data?.detail ?? 'Could not start a session');
    } finally {
      setIsStarting(false);
    }
  };

  const progressPercent = session ? Math.round((session.currentRound / session.totalRounds) * 100) : 0;

  // Real per-round metrics measured on the held-out test set (no synthetic curves)
  const dynamicConvergenceData = (session?.metrics ?? []).map((m) => ({
    round: `R${m.round}`,
    accuracy: m.accuracy,
    loss: m.loss,
  }));
  const sparklineData = (session?.metrics ?? []).map((m) => Math.round(m.accuracy * 100));

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col gap-8 max-w-[1440px] mx-auto w-full pb-8"
    >
      {/* PAGE HEADER */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-[24px] font-bold text-slate-900 mb-1 tracking-tight">Global Model Orchestration</h1>
          <p className="text-slate-600 text-[13px]">
            {session ? `Session #${session.sessionId} · Status: ${session.status}${session.dataset ? ` · Data: ${session.dataset}` : ''}` : 'Connecting to Server...'}{startError ? ` — ${startError}` : ''}
          </p>
        </div>
        <Button 
          onClick={handleStartSession} 
          disabled={isStarting || session?.status === "running"}
          variant="outline" 
          className="border-blue-500 text-blue-500 hover:bg-blue-500 hover:text-slate-900 transition-colors duration-200"
        >
          {isStarting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
          {session?.status === "running" ? "Training in Progress" : "Start New Session"}
        </Button>
      </header>

      {/* TOP STAT ROW */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Card 1: Current Round */}
        <Card className="glass-card border-slate-200 flex items-center p-6 gap-6 hover:border-blue-500/30 transition-colors">
          <div 
            className="w-20 h-20 rounded-full flex items-center justify-center relative shrink-0"
            style={{ background: `conic-gradient(#3B82F6 ${progressPercent}%, #1E293B 0)` }}
          >
            <div className="absolute inset-1 rounded-full bg-white backdrop-blur-xl flex items-center justify-center">
              <span className="text-slate-900 font-bold text-[20px]">{session?.currentRound || 0}/{session?.totalRounds || 20}</span>
            </div>
          </div>
          <div>
            <h3 className="text-slate-600 text-[12px] uppercase tracking-wider font-semibold mb-1">Current Round</h3>
            <p className="text-slate-500 text-[11px] font-medium">{progressPercent}% Complete</p>
          </div>
        </Card>

        {/* Card 2: Global Accuracy */}
        <Card className="glass-card border-slate-200 p-6 flex flex-col justify-center hover:border-blue-500/30 transition-colors">
          <div className="flex items-end gap-3 mb-2">
            <span className="text-slate-900 font-bold text-[32px] font-mono leading-none">
              {session?.globalAccuracy ? (session.globalAccuracy * 100).toFixed(1) + '%' : 'N/A'}
            </span>
            <div className="flex items-end h-[24px] pb-1 gap-[2px]">
              {sparklineData.map((h, i) => (
                <motion.div 
                  key={i}
                  initial={{ height: 0 }}
                  animate={{ height: `${h}%` }}
                  transition={{ delay: 0.1 * i, duration: 0.5 }}
                  className="w-1 bg-blue-500 rounded-sm"
                />
              ))}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-slate-600 text-[12px] font-medium">Global Accuracy</span>
          </div>
        </Card>

        {/* Card 3: AGPM Epsilon */}
        <Card className="glass-card border-slate-200 p-6 flex flex-col justify-center hover:border-blue-500/30 transition-colors">
          <div className="text-cyan-700 font-bold text-[28px] font-mono mb-1 leading-none">
            {session?.privacyBudget != null ? `ε = ${session.privacyBudget.toFixed(2)}` : 'ε = ∞ (no DP)'}
          </div>
          <div className="text-slate-600 text-[12px] font-medium mb-3">Privacy budget (RDP accountant, worst hospital)</div>
          <div>
            <Badge className="bg-emerald-50 text-emerald-700 border-none font-semibold text-[11px]">
              δ = 1e-5 · record-level DP-SGD
            </Badge>
          </div>
        </Card>
      </section>

      {/* MAIN DASHBOARD GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Network Diagram — intentionally dark card, NOT using glass-card which forces white bg */}
        <Card
          className="col-span-1 lg:col-span-2 overflow-hidden relative h-[360px] flex flex-col shadow-xl rounded-xl"
          style={{ background: '#0F172A', border: '1px solid #1E293B' }}
        >
          <div className="p-4 border-b border-slate-800 relative z-30">
            <h2 className="text-[12px] font-semibold uppercase tracking-[0.05em] text-slate-200">FL Hierarchy — Live Network</h2>
          </div>
          
          <div className="flex-1 relative flex flex-col items-center justify-between py-8 px-12 z-20">
            {/* Global Server */}
            <div className="relative flex flex-col items-center z-20">
              <div className="w-14 h-14 rounded-full border-2 border-blue-500 bg-slate-950 flex items-center justify-center shadow-[0_0_24px_rgba(59,130,246,0.5)] z-20">
                <Cloud className="text-blue-400 h-7 w-7" />
              </div>
              <span className="text-slate-100 text-[13px] mt-3 font-semibold">Global Server</span>
            </div>

            {/* Hubs */}
            <div className="flex justify-between w-full max-w-[480px] mt-6 relative z-20">
              <div className="flex flex-col items-center">
                <div className="w-11 h-11 rounded-full border-2 border-cyan-500 bg-slate-950 flex items-center justify-center z-20 shadow-[0_0_12px_rgba(6,182,212,0.3)]">
                  <Network className="text-cyan-400 h-5 w-5" />
                </div>
                <span className="text-slate-300 text-[12px] mt-2 font-medium">Hub East</span>
              </div>
              <div className="flex flex-col items-center">
                <div className="w-11 h-11 rounded-full border-2 border-cyan-500 bg-slate-950 flex items-center justify-center z-20 shadow-[0_0_12px_rgba(6,182,212,0.3)]">
                  <Network className="text-cyan-400 h-5 w-5" />
                </div>
                <span className="text-slate-300 text-[12px] mt-2 font-medium">Hub West</span>
              </div>
            </div>

            {/* Hospitals */}
            <div className="flex justify-between w-full mt-10 relative z-20">
              {['H1', 'H2', 'H3', 'H4', 'H5'].map((h, i) => {
                const isTraining = session?.status === "running";
                return (
                  <div key={h} className="flex flex-col items-center">
                    <div className={cn(
                      "w-9 h-9 rounded-full border-2 bg-slate-950 flex items-center justify-center text-xs font-bold z-20",
                      isTraining ? "border-blue-500 text-blue-400 shadow-[0_0_12px_rgba(59,130,246,0.6)]" : "border-emerald-500 text-emerald-400 shadow-[0_0_8px_rgba(34,197,94,0.3)]"
                    )}>
                      {h}
                    </div>
                    <Badge className={cn(
                      "mt-2 text-[10px] px-1.5 py-0 border-none font-medium flex items-center gap-1",
                      isTraining ? "bg-blue-500/20 text-blue-400 hover:bg-blue-500/30" : "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30"
                    )}>
                      {isTraining ? <RefreshCw className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
                      {isTraining ? 'Training' : 'Sent'}
                    </Badge>
                  </div>
                );
              })}
            </div>

            {/* SVG Connecting Lines — uses viewBox so numeric coords map to percentages */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none z-10 opacity-60" viewBox="0 0 100 100" preserveAspectRatio="none">
              {/* Hub to Global */}
              <line x1="50" y1="22" x2="35" y2="48" stroke="#1E3A5F" strokeWidth="0.4" />
              <line x1="50" y1="22" x2="65" y2="48" stroke="#1E3A5F" strokeWidth="0.4" />
              
              {/* Hospitals to Hub East (Left) */}
              <line x1="35" y1="48" x2="10" y2="78" stroke="#1E3A5F" strokeWidth="0.3" />
              <line x1="35" y1="48" x2="30" y2="78" stroke="#1E3A5F" strokeWidth="0.3" />
              <line x1="35" y1="48" x2="50" y2="78" stroke="#1E3A5F" strokeWidth="0.3" />

              {/* Hospitals to Hub West (Right) */}
              <line x1="65" y1="48" x2="70" y2="78" stroke="#1E3A5F" strokeWidth="0.3" />
              <line x1="65" y1="48" x2="90" y2="78" stroke="#1E3A5F" strokeWidth="0.3" />
            </svg>
            
          </div>
        </Card>

        {/* Convergence Chart */}
        <Card className="glass-card h-[360px] flex flex-col col-span-1 lg:col-span-2 border-slate-200">
          <div className="p-4 border-b border-slate-200 flex justify-between items-center z-10">
            <h2 className="text-[12px] font-semibold uppercase tracking-[0.05em] text-slate-900">Convergence History — All Rounds</h2>
            <div className="flex gap-4 text-[12px]">
              <div className="flex items-center gap-2"><div className="w-3 h-3 bg-blue-500 rounded-sm"></div> <span className="text-slate-700">Global Accuracy</span></div>
              <div className="flex items-center gap-2"><div className="w-3 h-3 bg-orange-500 rounded-sm"></div> <span className="text-slate-700">Global Loss</span></div>
            </div>
          </div>
          
          <div className="flex-1 p-6 relative">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={dynamicConvergenceData} margin={{ top: 20, right: 30, left: -10, bottom: 0 }}>
                <XAxis 
                  dataKey="round" 
                  stroke="#475569" 
                  fontSize={11} 
                  tickLine={false} 
                  axisLine={false}
                  dy={10}
                />
                <YAxis 
                  yAxisId="left"
                  stroke="#475569" 
                  fontSize={11} 
                  tickLine={false} 
                  axisLine={false}
                  domain={[0, 1]}
                  tickFormatter={(val) => val.toFixed(2)}
                />
                <YAxis 
                  yAxisId="right"
                  orientation="right"
                  stroke="#475569" 
                  fontSize={11} 
                  tickLine={false} 
                  axisLine={false}
                  domain={[0, 1]}
                  tickFormatter={(val) => val.toFixed(2)}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                  itemStyle={{ color: '#334155' }}
                  labelStyle={{ color: '#64748b', marginBottom: '4px' }}
                />
                
                {/* Current Round Reference Line */}
                <ReferenceLine yAxisId="left" x={`R${session?.currentRound || 1}`} stroke="#475569" strokeDasharray="4 4" label={{ position: 'top', value: `Current (${session?.currentRound || 0})`, fill: '#94a3b8', fontSize: 11, dy: -10 }} />
                
                {/* Global Accuracy Line */}
                <Line 
                  yAxisId="left"
                  type="monotone" 
                  dataKey="accuracy" 
                  name="Accuracy"
                  stroke="#3B82F6" 
                  strokeWidth={3}
                  dot={{ r: 4, fill: '#ffffff', stroke: '#3B82F6', strokeWidth: 2 }}
                  activeDot={{ r: 6, fill: '#3B82F6', stroke: '#fff', strokeWidth: 2 }}
                  connectNulls
                />

                {/* Global Loss Line */}
                <Line 
                  yAxisId="right"
                  type="monotone" 
                  dataKey="loss" 
                  name="Loss"
                  stroke="#F97316" 
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={{ r: 3, fill: '#ffffff', stroke: '#F97316', strokeWidth: 2 }}
                  connectNulls
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
        
      </div>
    </motion.div>
  );
}

// Helper for classnames
function cn(...classes: (string | undefined | null | false)[]) {
  return classes.filter(Boolean).join(' ');
}
