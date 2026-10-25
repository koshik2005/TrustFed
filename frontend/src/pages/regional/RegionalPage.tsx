import React from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Zap, Lock, Network, Info, Box, RefreshCw, CheckCircle2, Hourglass } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { api } from '@/services/api';
import type { Hospital } from '@/types';

export default function RegionalPage() {
  const [hospitals, setHospitals] = React.useState<Hospital[]>([]);

  const fetchHospitals = async () => {
    try {
      const data = await api.trainingApi.getHospitals();
      setHospitals(data);
    } catch (e) {
      console.error("Failed to load hospitals", e);
    }
  };

  React.useEffect(() => {
    fetchHospitals();
  }, []);
  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col max-w-[1440px] mx-auto w-full pb-8 gap-8 relative"
    >
      <style>{`
        .flow-line {
          stroke-dasharray: 4;
          animation: flow 1s linear infinite;
        }
        @keyframes flow {
          from { stroke-dashoffset: 8; }
          to { stroke-dashoffset: 0; }
        }
      `}</style>

      {/* Background Ambient Glows */}
      <div className="fixed top-[-10%] left-[-10%] w-[50vw] h-[50vh] rounded-full bg-blue-500/10 blur-[120px] pointer-events-none -z-10" />
      <div className="fixed bottom-[-10%] right-[-10%] w-[40vw] h-[40vh] rounded-full bg-cyan-500/5 blur-[120px] pointer-events-none -z-10" />

      {/* PAGE HEADER */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 w-full relative z-10">
        <div>
          <h1 className="text-[24px] font-bold text-slate-900 mb-1 tracking-tight">Regional Hub — East Zone</h1>
          <p className="text-slate-600 font-mono text-[13px]">Secure Multi-Party Computation Aggregation Layer</p>
        </div>
        <div className="glass-card bg-white border-slate-200 px-4 py-2 rounded-full flex items-center gap-3">
          <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 shadow-[0_0_8px_#22d3ee] animate-pulse"></span>
          <span className="text-[12px] uppercase font-semibold tracking-wider text-slate-800">{hospitals.length} / {hospitals.length} Hospitals Connected</span>
        </div>
      </header>

      {/* TOP STAT ROW */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative z-10">
        <Card className="glass-card bg-white border-slate-200 hover:border-blue-500/30 hover:shadow-[0_0_15px_rgba(59,130,246,0.15)] transition-all duration-300">
          <CardContent className="p-6 flex flex-col justify-between h-full">
            <div className="flex items-start justify-between mb-4">
              <span className="text-sm font-medium text-slate-600">Aggregation Latency</span>
              <Zap className="text-cyan-400 w-5 h-5 fill-cyan-400/20" />
            </div>
            <div>
              <div className="text-3xl font-bold text-slate-900 tracking-tight">124ms</div>
              <div className="font-mono text-xs text-slate-500 mt-2">Last aggregation</div>
            </div>
          </CardContent>
        </Card>

        <Card className="glass-card bg-white border-slate-200 hover:border-blue-500/30 hover:shadow-[0_0_15px_rgba(59,130,246,0.15)] transition-all duration-300">
          <CardContent className="p-6 flex flex-col justify-between h-full">
            <div className="flex items-start justify-between mb-4">
              <span className="text-sm font-medium text-slate-600">Payload Size</span>
              <Lock className="text-blue-500 w-5 h-5 fill-blue-500/20" />
            </div>
            <div>
              <div className="text-3xl font-bold text-slate-900 tracking-tight">2.4 MB</div>
              <div className="font-mono text-xs text-slate-500 mt-2">Encrypted payload sent</div>
            </div>
          </CardContent>
        </Card>

        <Card className="glass-card bg-white border-slate-200 hover:border-blue-500/30 hover:shadow-[0_0_15px_rgba(59,130,246,0.15)] transition-all duration-300">
          <CardContent className="p-6 flex flex-col justify-between h-full">
            <div className="flex items-start justify-between mb-4">
              <span className="text-sm font-medium text-slate-600">Hospitals Online</span>
              <Network className="text-cyan-400 w-5 h-5 fill-cyan-400/20" />
            </div>
            <div>
              <div className="text-3xl font-bold text-cyan-700 tracking-tight">{hospitals.length} / {hospitals.length}</div>
              <div className="font-mono text-xs text-slate-500 mt-2">All nodes ready</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* SMPC VISUALIZATION CARD */}
      <Card className="glass-card bg-white border-slate-200 relative overflow-hidden z-10 shadow-lg">
        <CardContent className="p-6 relative z-10">
          
          <div className="flex items-center gap-2 mb-8">
            <h2 className="text-lg font-semibold text-slate-900">Secret Sharing — SMPC Aggregation</h2>
            <Tooltip>
              <TooltipTrigger>
                <Info className="w-4 h-4 text-slate-600 hover:text-slate-800 transition-colors cursor-help" />
              </TooltipTrigger>
              <TooltipContent className="bg-white border-slate-200 text-slate-800 text-xs">
                No single node sees a complete model update
              </TooltipContent>
            </Tooltip>
          </div>

          <div className="flex flex-col md:flex-row items-center justify-between w-full h-auto md:h-[220px] gap-8 py-4 relative">
            
            {/* Left Nodes */}
            <div className="flex flex-col gap-4 w-full md:w-[160px] z-10">
              {[1, 2, 3].map((i) => (
                <div key={i} className="glass-card bg-white border-slate-200 rounded-lg p-3 flex items-center justify-between border-l-2 border-l-cyan-400 shadow-md">
                  <span className="font-mono text-xs text-slate-800 font-medium">Hospital {i}</span>
                  <div className="flex gap-1">
                    <div className="w-1.5 h-1.5 bg-blue-500/60 rounded-sm"></div>
                    <div className="w-1.5 h-1.5 bg-cyan-400/60 rounded-sm"></div>
                    <div className="w-1.5 h-1.5 bg-orange-400/60 rounded-sm"></div>
                  </div>
                </div>
              ))}
            </div>

            {/* Animation Layer */}
            <div className="hidden md:block absolute left-[180px] right-[240px] top-1/2 -translate-y-1/2 h-[180px] z-0 pointer-events-none">
              <svg height="100%" preserveAspectRatio="none" viewBox="0 0 100 100" width="100%">
                <path className="flow-line" d="M 0 20 Q 50 20 50 50" fill="none" stroke="rgba(59, 130, 246, 0.4)" strokeWidth="1"></path>
                <path className="flow-line" d="M 0 50 L 50 50" fill="none" stroke="rgba(59, 130, 246, 0.4)" strokeWidth="1"></path>
                <path className="flow-line" d="M 0 80 Q 50 80 50 50" fill="none" stroke="rgba(59, 130, 246, 0.4)" strokeWidth="1"></path>
                <path className="flow-line" d="M 50 50 L 100 50" fill="none" stroke="rgba(59, 130, 246, 0.6)" strokeWidth="2"></path>
              </svg>
            </div>

            {/* Center Hub */}
            <div className="flex flex-col items-center justify-center z-10 glass-card bg-white border-blue-500/30 p-4 rounded-full w-24 h-24 shadow-[0_0_24px_rgba(59,130,246,0.2)]">
              <Lock className="text-blue-500 w-7 h-7 mb-1 drop-shadow-[0_0_8px_rgba(59,130,246,0.8)] fill-blue-500/20" />
              <span className="text-[9px] uppercase font-bold text-blue-500 tracking-widest text-center leading-tight">Secret<br/>Shares</span>
            </div>

            {/* Right Aggregate */}
            <div className="glass-card bg-white border-blue-500/50 rounded-xl p-6 shadow-[0_0_30px_rgba(59,130,246,0.15)] z-10 w-full md:w-auto flex flex-col items-center">
              <Box className="text-slate-800 mb-3 w-6 h-6 fill-slate-200/20" />
              <div className="flex gap-1.5 mb-4">
                <div className="w-4 h-4 bg-blue-500 rounded-sm shadow-sm"></div>
                <div className="w-4 h-4 bg-cyan-400 rounded-sm shadow-sm"></div>
                <div className="w-4 h-4 bg-orange-400 rounded-sm shadow-sm"></div>
              </div>
              <span className="font-mono text-sm text-slate-900 font-semibold">Regional Aggregate</span>
              <span className="text-[11px] text-slate-600 mt-1.5 text-center">1 aggregated update (encrypted)</span>
            </div>
            
          </div>

          <div className="mt-6 pt-4 border-t border-slate-200">
            <p className="text-xs text-slate-500 italic">Each hospital splits its update into shares. No hub ever sees a full individual update.</p>
          </div>
        </CardContent>
      </Card>

      {/* HOSPITAL STATUS TABLE */}
      <Card className="glass-card bg-white border-slate-200 overflow-hidden relative z-10 shadow-lg">
        <div className="p-6 border-b border-slate-200 flex justify-between items-center bg-slate-50/70">
          <h3 className="font-semibold text-lg text-slate-900">Connected Hospital Nodes</h3>
          <Button onClick={fetchHospitals} variant="ghost" className="text-blue-600 hover:text-blue-700 hover:bg-blue-50 text-xs font-semibold uppercase tracking-wider h-8">
            <RefreshCw className="w-3 h-3 mr-2" /> REFRESH
          </Button>
        </div>
        
        <div className="w-full overflow-x-auto">
          <Table>
            <TableHeader className="bg-slate-50 border-b border-slate-200">
              <TableRow className="hover:bg-transparent border-none">
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-slate-600 py-4 h-auto">Hospital</TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-slate-600 py-4 h-auto">Status</TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-slate-600 py-4 h-auto">Dataset Size</TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-slate-600 py-4 h-auto">Last Update</TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-slate-600 py-4 h-auto">Share Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className="text-[13px] text-slate-800">
              {hospitals.map((node) => {
                const isTraining = node.status.toLowerCase() === 'training';
                return (
                  <TableRow key={node.id} className="border-b border-slate-200 hover:bg-slate-100 transition-colors">
                    <TableCell className="py-4 font-mono font-medium">{node.name}</TableCell>
                    <TableCell className="py-4">
                      <Badge className={cn(
                        "bg-transparent border px-2 py-0.5 text-[11px] font-medium tracking-wide flex items-center gap-1.5 w-fit uppercase",
                        isTraining ? "border-blue-300 text-blue-700 bg-blue-50" : "border-cyan-300 text-cyan-700 bg-cyan-50"
                      )}>
                        <span className={cn("w-1.5 h-1.5 rounded-full", isTraining ? "bg-blue-400 animate-pulse" : "bg-cyan-400")}></span>
                        {node.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="py-4 text-slate-600">{node.localDatasetSize.toLocaleString()} records</TableCell>
                    <TableCell className="py-4 font-mono text-slate-600">Epoch {node.currentEpoch}/{node.totalEpochs}</TableCell>
                    <TableCell className="py-4">
                      <div className={cn(
                        "inline-flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded uppercase",
                        isTraining ? "text-amber-700 bg-amber-50" : "text-emerald-700 bg-emerald-50"
                      )}>
                        {isTraining ? <Hourglass className="w-3 h-3" /> : <CheckCircle2 className="w-3 h-3" />}
                        {isTraining ? 'Pending' : 'Received'}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
              {hospitals.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8 text-slate-500">Loading nodes...</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </Card>

    </motion.div>
  );
}
