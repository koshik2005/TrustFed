import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ShieldCheck, TerminalSquare } from 'lucide-react';
import { api } from '@/services/api';
import type { PrivacyReport } from '@/types';

export default function PrivacyPage() {
  const [showTerminal, setShowTerminal] = useState(false);
  const [report, setReport] = useState<PrivacyReport | null>(null);

  useEffect(() => {
    // Fetch dynamic report
    const fetchReport = async () => {
      try {
        const data = await api.teflApi.getPrivacyReport('latest');
        setReport(data);
      } catch (e) {
        console.error("Failed to load privacy report", e);
      }
    };
    fetchReport();

    // Small delay before starting terminal animation
    const t = setTimeout(() => setShowTerminal(true), 500);
    return () => clearTimeout(t);
  }, []);

  const withoutDPPct  = report ? Math.round(report.attackSuccessWithoutDP * 100) : null;
  const withDPPct     = report ? Math.round(report.attackSuccessWithDP * 100) : null;
  const heKeySize     = report?.heKeySize ?? 1024;
  const leakageReduction = (withoutDPPct !== null && withDPPct !== null)
    ? ((withoutDPPct - withDPPct) / withoutDPPct * 100).toFixed(1)
    : null;

  interface TerminalLine {
    text: string;
    color: string;
    highlight?: string;
  }

  const terminalLines: TerminalLine[] = [
    { text: "$ Membership-inference attack (loss-threshold, Yeom et al.)", color: "text-emerald-400" },
    { text: "> Members: pooled training records | Non-members: held-out test records", color: "text-emerald-400" },
    { text: `> Reference model (identical run, no DP): attack AUC = ${withoutDPPct !== null ? (withoutDPPct / 100).toFixed(3) : '…'}`, color: "text-amber-400" },
    { text: `> Protected model (ε = ${report?.epsilon != null ? report.epsilon.toFixed(2) : '∞'}): attack AUC = ${withDPPct !== null ? (withDPPct / 100).toFixed(3) : '…'}${leakageReduction ? ` (Risk reduction: -${leakageReduction}%)` : ''}`, color: "text-emerald-400" },
    { text: "> AUC 0.5 = attacker no better than guessing. Small cohorts give noisy AUCs; see the paper for CIs.", color: "text-slate-400" },
  ];

  const arcLength = 282.7; // pi * 90

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col max-w-[1440px] mx-auto w-full pb-8 gap-8 relative"
    >
      {/* Background Ambient Glows */}
      <div className="fixed top-[10%] left-[10%] w-[50vw] h-[50vh] rounded-full bg-blue-500/5 blur-[120px] pointer-events-none -z-10" />
      <div className="fixed bottom-[10%] right-[10%] w-[40vw] h-[40vh] rounded-full bg-emerald-500/5 blur-[120px] pointer-events-none -z-10" />

      {/* PAGE HEADER */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 relative z-10">
        <div>
          <h1 className="text-slate-900 font-bold text-[24px] mb-1 tracking-tight">Privacy Validation Report</h1>
          <p className="text-slate-600 text-[13px] font-mono">Membership-Inference Attack Simulation · Differential Privacy Proof</p>
        </div>
        <Badge className="bg-emerald-50 border border-emerald-500/40 text-emerald-700 hover:bg-emerald-100 px-3 py-1 rounded-full text-[13px] font-semibold flex items-center gap-2">
          <ShieldCheck className="w-4 h-4" /> DP Enabled — Protected
        </Badge>
      </div>

      {/* TOP STAT ROW */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative z-10">
        {/* Stat Card 1 */}
        <Card className="glass-card bg-white border-slate-200 relative overflow-hidden flex flex-col justify-center">
          <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-emerald-500" />
          <CardContent className="p-6">
            <div className="text-[12px] uppercase tracking-wider font-semibold text-slate-600 mb-2">MIA Resistance</div>
            <div className="font-mono text-[36px] font-bold text-emerald-500 leading-none mb-2">
              {withDPPct !== null ? (report!.privacyResistance * 100).toFixed(1) + '%' : '--'}
            </div>
            <div className="text-slate-500 text-[12px]">1 − attack advantage (higher is better)</div>
          </CardContent>
        </Card>

        {/* Stat Card 2 */}
        <Card className="glass-card bg-white border-slate-200 relative overflow-hidden flex flex-col justify-center">
          <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-blue-500" />
          <CardContent className="p-6">
            <div className="text-[12px] uppercase tracking-wider font-semibold text-slate-600 mb-2">Encryption Strength</div>
            <div className="font-mono text-[36px] font-bold text-blue-500 leading-none mb-2">{report?.paillierEnabled ? `${heKeySize}-bit` : 'Off'}</div>
            <div className="text-slate-500 text-[12px]">Paillier HE (Research Simulation in backend/tefl/secagg.py)</div>
          </CardContent>
        </Card>

        {/* Stat Card 3 */}
        <Card className="glass-card bg-white border-slate-200 relative overflow-hidden flex flex-col justify-center">
          <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-cyan-500" />
          <CardContent className="p-6">
            <div className="text-[12px] uppercase tracking-wider font-semibold text-slate-600 mb-2">Privacy Budget</div>
            <div className="font-mono text-[36px] font-bold text-cyan-500 leading-none mb-2">
              ε = {report?.epsilon != null ? report.epsilon.toFixed(2) : '∞'}
            </div>
            <div className="text-slate-500 text-[12px]">RDP accountant, δ = 1e-5</div>
          </CardContent>
        </Card>
      </div>

      {/* Target Epsilon / Accountant Transparency Notice */}
      {(report as any)?.targetEpsilon != null && !(report as any)?.targetMet && (
        <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-900 text-xs relative z-10">
          <span className="text-lg flex-shrink-0">⚠️</span>
          <div className="flex flex-col gap-1">
            <span className="font-semibold text-amber-950">
              Accountant Stability Cap Active (Target ε = {(report as any).targetEpsilon.toFixed(2)} Not Met)
            </span>
            <p className="text-amber-800 leading-relaxed">
              To prevent gradient explosion and neural weight collapse on small hospital sample cohorts, Gaussian noise is clamped to σ ≤ 3.5. Under this stability ceiling, the RDP accountant certifies an actual spent privacy loss of <strong>ε = {report?.epsilon != null ? report.epsilon.toFixed(2) : 'N/A'}</strong> at δ = 1e-5. This real spent budget is reported transparently rather than claiming an unachieved target.
            </p>
          </div>
        </div>
      )}

      {/* COMPARISON SECTION */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 relative z-10">
        
        {/* Left Card (Without DP) */}
        <Card className="glass-card bg-white border-red-500/30 flex flex-col items-center text-center relative overflow-hidden">
          <div className="absolute top-6 left-6">
            <Badge className="bg-red-50 text-red-700 border border-red-200 font-semibold">
              No Protection
            </Badge>
          </div>
          <CardContent className="p-8 flex flex-col items-center w-full">
            <h3 className="text-slate-900 font-semibold mb-8 mt-2 opacity-80 text-lg">Without DP</h3>
            
            {/* Gauge */}
            <div className="relative w-[200px] h-[100px] mb-6 drop-shadow-[0_0_12px_rgba(239,68,68,0.5)]">
              <svg className="w-full h-full" viewBox="0 0 200 100">
                {/* Background Arc */}
                <path d="M 10 100 A 90 90 0 0 1 190 100" fill="none" stroke="#E2E8F0" strokeLinecap="round" strokeWidth="12" />
                {/* Foreground Arc */}
                <motion.path 
                  initial={{ strokeDashoffset: arcLength }}
                  animate={{ strokeDashoffset: report ? arcLength * (1 - report.attackSuccessWithoutDP) : arcLength }}
                  transition={{ duration: 1.5, ease: "easeOut" }}
                  d="M 10 100 A 90 90 0 0 1 190 100" 
                  fill="none" 
                  stroke="#EF4444" 
                  strokeDasharray={arcLength} 
                  strokeLinecap="round" 
                  strokeWidth="12" 
                />
              </svg>
              <div className="absolute bottom-0 left-0 w-full text-center">
                <span className="text-[32px] font-bold text-red-500">
                  {report ? Math.round(report.attackSuccessWithoutDP * 100) : '--'}%
                </span>
              </div>
            </div>
            
            <div className="text-red-500 font-bold text-[14px] mb-3">HIGH RISK — Model leaks training data</div>
            <div className="text-slate-600 text-[13px] max-w-sm leading-relaxed">
              Attack AUC on the non-private reference model: {report ? Math.round(report.attackSuccessWithoutDP * 100) : '--'}% (50% = random guessing).</div>
          </CardContent>
        </Card>

        {/* Right Card (With DP) */}
        <Card className="glass-card bg-white border-emerald-500/30 flex flex-col items-center text-center relative overflow-hidden">
          <div className="absolute top-6 left-6">
            <Badge className="bg-emerald-50 text-emerald-700 border border-emerald-200 font-semibold">
              DP Active
            </Badge>
          </div>
          <CardContent className="p-8 flex flex-col items-center w-full">
            <h3 className="text-slate-900 font-semibold mb-8 mt-2 opacity-80 text-lg">With DP Enabled</h3>
            
            {/* Gauge */}
            <div className="relative w-[200px] h-[100px] mb-6 drop-shadow-[0_0_12px_rgba(16,185,129,0.4)]">
              <svg className="w-full h-full" viewBox="0 0 200 100">
                {/* Background Arc */}
                <path d="M 10 100 A 90 90 0 0 1 190 100" fill="none" stroke="#E2E8F0" strokeLinecap="round" strokeWidth="12" />
                {/* Foreground Arc */}
                <motion.path 
                  initial={{ strokeDashoffset: arcLength }}
                  animate={{ strokeDashoffset: report ? arcLength * (1 - report.attackSuccessWithDP) : arcLength }}
                  transition={{ duration: 1.5, ease: "easeOut", delay: 0.2 }}
                  d="M 10 100 A 90 90 0 0 1 190 100" 
                  fill="none" 
                  stroke="#10B981" 
                  strokeDasharray={arcLength} 
                  strokeLinecap="round" 
                  strokeWidth="12" 
                />
              </svg>
              <div className="absolute bottom-0 left-0 w-full text-center">
                <span className="text-[32px] font-bold text-emerald-500">
                  {report ? Math.round(report.attackSuccessWithDP * 100) : '--'}%
                </span>
              </div>
            </div>
            
            <div className="text-emerald-500 font-bold text-[14px] mb-3">PROTECTED — Near random guessing</div>
            <div className="text-slate-600 text-[13px] max-w-sm leading-relaxed">
              Attack AUC on the DP-protected model: {report ? Math.round(report.attackSuccessWithDP * 100) : '--'}%.</div>
          </CardContent>
        </Card>

      </div>

      {/* TERMINAL CARD */}
      <Card className="glass-card bg-[#040810]/95 border-emerald-500/30 shadow-2xl relative z-10 backdrop-blur-xl">
        <CardContent className="p-6">
          <div className="flex justify-between items-center border-b border-slate-800 pb-4 mb-4">
            <div className="flex items-center gap-2 text-slate-100 font-bold text-[14px]">
              <TerminalSquare className="w-5 h-5 text-emerald-400" />
              <span>Attack Simulation Log</span>
            </div>
            <Badge className="bg-transparent border border-emerald-500/40 text-emerald-400 font-mono text-[10px] tracking-widest uppercase rounded">
              Completed
            </Badge>
          </div>
          
          <div className="font-mono text-[13px] text-emerald-400 leading-[1.8] whitespace-pre-wrap min-h-[220px]">
            {showTerminal && terminalLines.map((line, i) => (
              <motion.div 
                key={i}
                initial={{ opacity: 0, x: -5 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.1, delay: i * 0.4 }}
              >
                {line.highlight ? (
                  <span>
                    {line.text.split(line.highlight)[0]}
                    <span className="text-red-500 font-bold">{line.highlight}</span>
                    {line.text.split(line.highlight)[1]}
                  </span>
                ) : (
                  line.text
                )}
              </motion.div>
            ))}
            
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: [0, 1, 0] }}
              transition={{ repeat: Infinity, duration: 1 }}
              className="inline-block mt-1"
            >
              $ _
            </motion.div>
          </div>
        </CardContent>
      </Card>

    </motion.div>
  );
}
