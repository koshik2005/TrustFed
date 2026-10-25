import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Download, FileText, Shield, Scale, BadgeCheck, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/services/api';

const getBadgeStyle = (status: string) => {
  switch (status) {
    case 'HIGH': return 'bg-red-50 text-red-700 border-red-300';
    case 'MEDIUM': return 'bg-orange-50 text-orange-700 border-orange-300';
    case 'LOW': return 'bg-yellow-50 text-yellow-700 border-yellow-300';
    case 'BEST': return 'bg-green-50 text-green-700 border-green-300';
    default: return 'bg-slate-100 text-slate-600 border-slate-300';
  }
};

export default function ComparisonPage() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await api.trainingApi.getComparison();
        setData(response);
      } catch (error) {
        console.error("Failed to fetch comparison data", error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const base = data.find((d) => d.name === 'FedAvg (non-IID)');
  const tefl = data.find((d) => d.special);
  const insightPrivacy = base && tefl
    ? `Membership-inference AUC ${base.mia} (FedAvg) vs ${tefl.mia} (TEFL, ε = ${tefl.epsilon}); accuracy ${base.acc} → ${tefl.acc}.`
    : 'Run `python -m tefl.run_experiments` to populate this benchmark.';
  const insightFair = base && tefl
    ? `Fairness score (1 − worst subgroup accuracy gap): ${base.fairness} (FedAvg) vs ${tefl.fairness} (TEFL).`
    : 'Run `python -m tefl.run_experiments` to populate this benchmark.';

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[50vh]">
        <Loader2 className="h-8 w-8 animate-spin text-cyan-500" />
      </div>
    );
  }

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col max-w-[1440px] mx-auto w-full pb-8 gap-8 relative"
    >
      {/* Ambient Gradients */}
      <div className="fixed top-1/2 left-[15%] w-[50vw] h-[50vh] rounded-full bg-blue-500/5 blur-[120px] pointer-events-none -translate-y-1/2 -z-10" />
      <div className="fixed top-[30%] right-[15%] w-[40vw] h-[40vh] rounded-full bg-cyan-500/5 blur-[120px] pointer-events-none -z-10" />

      {/* Page Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 relative z-10">
        <div>
          <h1 className="text-[24px] font-bold text-slate-900 mb-2 leading-tight tracking-tight">Model Performance Comparison</h1>
          <p className="text-slate-600 text-[13px]">Replicating Table 3 — Singh et al. 2025 + TrustFed-Health TEFL Extension</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" className="border-slate-600 text-slate-700 hover:text-slate-900 hover:bg-slate-100 transition-all h-9 text-xs">
            <Download className="w-4 h-4 mr-2" /> Export CSV
          </Button>
          <Button variant="outline" className="border-slate-600 text-slate-700 hover:text-slate-900 hover:bg-slate-100 transition-all h-9 text-xs">
            <FileText className="w-4 h-4 mr-2" /> Export PDF
          </Button>
        </div>
      </div>

      {/* Comparison Table Card */}
      <Card className="glass-card bg-white border-slate-200 overflow-hidden relative z-10 shadow-lg">
        <div className="w-full overflow-x-auto">
          <Table>
            <TableHeader className="bg-slate-50 border-b border-slate-200">
              <TableRow className="hover:bg-transparent border-none">
                <TableHead className="text-[11px] font-semibold uppercase tracking-widest text-slate-600 py-4 px-6 h-auto">Model Name</TableHead>
                <TableHead className="text-[11px] font-semibold uppercase tracking-widest text-slate-600 py-4 px-6 h-auto">Accuracy</TableHead>
                <TableHead className="text-[11px] font-semibold uppercase tracking-widest text-slate-600 py-4 px-6 h-auto">Privacy Leakage (MIA ↓)</TableHead>
                <TableHead className="text-[11px] font-semibold uppercase tracking-widest text-slate-600 py-4 px-6 h-auto">Fairness Score (↑)</TableHead>
                <TableHead className="text-[11px] font-semibold uppercase tracking-widest text-slate-600 py-4 px-6 h-auto">Training Time</TableHead>
                <TableHead className="text-[11px] font-semibold uppercase tracking-widest text-slate-600 py-4 px-6 h-auto">HE Used</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className="text-[13px] text-slate-800">
              {data.map((row, index) => (
                <TableRow 
                  key={index} 
                  className={cn(
                    "transition-colors",
                    row.special 
                      ? "bg-blue-50/70 hover:bg-blue-50 border-l-4 border-l-blue-500 border-b border-slate-200" 
                      : "border-b border-slate-200 hover:bg-slate-50/80"
                  )}
                >
                  <TableCell className={cn("py-4 px-6 font-medium", row.special ? "text-slate-900" : "text-slate-800")}>
                    {row.special ? (
                      <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-cyan-400 font-bold">
                        {row.name}
                      </span>
                    ) : row.name}
                  </TableCell>
                  
                  <TableCell className={cn("py-4 px-6 font-mono", row.special ? "text-slate-900 font-medium" : "text-slate-600")}>
                    {row.acc}
                  </TableCell>
                  
                  <TableCell className="py-4 px-6 font-mono">
                    <div className="flex items-center gap-2">
                      <span className={cn(row.special ? "text-slate-900 font-medium" : "text-slate-600")}>{row.mia}</span>
                      <Badge variant="outline" className={cn("px-2 py-0 text-[10px] font-bold rounded-full border tracking-wider", getBadgeStyle(row.miaStatus))}>
                        {row.miaStatus} {row.miaStatus === 'BEST' && '✓'}
                      </Badge>
                    </div>
                  </TableCell>
                  
                  <TableCell className="py-4 px-6 font-mono">
                    <div className="flex items-center gap-2">
                      <span className={cn(row.special ? "text-slate-900 font-medium" : "text-slate-600")}>{row.fairness}</span>
                      {row.fairnessStatus && (
                        <Badge variant="outline" className={cn("px-2 py-0 text-[10px] font-bold rounded-full border tracking-wider", getBadgeStyle(row.fairnessStatus))}>
                          {row.fairnessStatus} ✓
                        </Badge>
                      )}
                    </div>
                  </TableCell>
                  
                  <TableCell className={cn("py-4 px-6 font-mono", row.special ? "text-slate-900 font-medium" : "text-slate-600")}>
                    {row.time}
                  </TableCell>
                  
                  <TableCell className={cn("py-4 px-6 font-mono", row.special ? "text-slate-900 font-medium" : "text-slate-600")}>
                    {row.special ? (
                      <span className="flex items-center gap-1.5 text-slate-800">
                        <BadgeCheck className="w-4 h-4 text-cyan-400" /> {row.he}
                      </span>
                    ) : (
                      row.he
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Card>

      {/* Insight Callout Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative z-10">
        
        {/* Privacy Insight */}
        <Card className="glass-card bg-white border-slate-200 border-l-4 border-l-blue-500 overflow-hidden relative">
          <div className="absolute -right-10 -top-10 w-32 h-32 bg-blue-500 opacity-10 blur-[40px] rounded-full z-0"></div>
          <CardContent className="p-5 relative z-10">
            <div className="flex items-center gap-3 mb-3">
              <Shield className="text-blue-500 w-5 h-5 fill-blue-500/20" />
              <h3 className="text-slate-900 text-sm font-bold">Privacy Insight</h3>
            </div>
            <p className="text-slate-600 text-[13px] leading-relaxed">
              {insightPrivacy}
            </p>
          </CardContent>
        </Card>

        {/* Fairness Insight */}
        <Card className="glass-card bg-white border-slate-200 border-l-4 border-l-cyan-400 overflow-hidden relative">
          <div className="absolute -right-10 -top-10 w-32 h-32 bg-cyan-400 opacity-10 blur-[40px] rounded-full z-0"></div>
          <CardContent className="p-5 relative z-10">
            <div className="flex items-center gap-3 mb-3">
              <Scale className="text-cyan-400 w-5 h-5 fill-cyan-400/20" />
              <h3 className="text-slate-900 text-sm font-bold">Fairness Insight</h3>
            </div>
            <p className="text-slate-600 text-[13px] leading-relaxed">
              {insightFair}
            </p>
          </CardContent>
        </Card>

      </div>
    </motion.div>
  );
}
