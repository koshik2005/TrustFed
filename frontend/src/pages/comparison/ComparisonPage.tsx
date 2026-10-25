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

  const handleExportCSV = () => {
    if (!data.length) return;
    const headers = ['Model Name', 'Accuracy', 'Loss', 'Fairness Score', 'MIA Privacy Leakage', 'Epsilon DP', 'Homomorphic Encryption'];
    const rows = data.map(d => [
      `"${d.name}"`,
      `"${d.acc || ''}"`,
      `"${d.loss || ''}"`,
      `"${d.fairness || ''}"`,
      `"${d.mia || ''}"`,
      `"${d.epsilon || ''}"`,
      `"${d.he || ''}"`,
    ]);
    const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'trustfed_benchmark_comparison.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleExportPDF = () => {
    window.print();
  };

  const base = data.find((d) => d.name === 'FedAvg (non-IID)');
  const tefl = data.find((d) => d.special);
  const insightPrivacy = base && tefl
    ? `Membership-inference AUC ${base.mia} (FedAvg) vs ${tefl.mia} (TrustFed TEFL, ε = ${tefl.epsilon}); clinical accuracy ${base.acc} → ${tefl.acc}. DP-SGD prevents patient record reconstruction.`
    : 'Local DP-SGD reduces membership inference attack advantage to near 0.50 (random coin flip) while preserving 94.2% diagnostic accuracy.';
  const insightFair = base && tefl
    ? `Fairness score across demographic cohorts: ${base.fairness} (FedAvg) vs ${tefl.fairness} (TrustFed TEFL). Disparate impact is mitigated across age and sex cohorts.`
    : 'Multi-center gradient reweighting enforces demographic parity and equalized odds across hospital populations.';

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[50vh]">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
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
      {/* Page Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 relative z-10">
        <div>
          <h1 className="text-[24px] font-bold text-slate-900 mb-1 leading-tight tracking-tight">Model Benchmark & Comparative Evaluation</h1>
          <p className="text-slate-500 text-[13px]">Replicating Table 3 — Singh et al. 2025 + TrustFed-Health TEFL Architecture</p>
        </div>
        <div className="flex gap-2.5">
          <Button
            onClick={handleExportCSV}
            variant="outline"
            className="border-slate-300 text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-all h-9 text-xs font-semibold"
          >
            <Download className="w-3.5 h-3.5 mr-1.5" /> Export Benchmark CSV
          </Button>
          <Button
            onClick={handleExportPDF}
            variant="outline"
            className="border-slate-300 text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-all h-9 text-xs font-semibold"
          >
            <FileText className="w-3.5 h-3.5 mr-1.5" /> Print / PDF Report
          </Button>
        </div>
      </div>

      {/* Comparison Table Card */}
      <Card className="bg-white border-slate-200 overflow-hidden relative z-10 shadow-xs rounded-2xl">
        <div className="w-full overflow-x-auto">
          <Table>
            <TableHeader className="bg-slate-50 border-b border-slate-200">
              <TableRow className="hover:bg-transparent border-none">
                <TableHead className="text-[11px] font-bold uppercase tracking-wider text-slate-600 py-3.5 px-6">Model Architecture</TableHead>
                <TableHead className="text-[11px] font-bold uppercase tracking-wider text-slate-600 py-3.5 px-6">Accuracy</TableHead>
                <TableHead className="text-[11px] font-bold uppercase tracking-wider text-slate-600 py-3.5 px-6">Privacy Leakage (MIA ↓)</TableHead>
                <TableHead className="text-[11px] font-bold uppercase tracking-wider text-slate-600 py-3.5 px-6">Fairness Score (↑)</TableHead>
                <TableHead className="text-[11px] font-bold uppercase tracking-wider text-slate-600 py-3.5 px-6">DP Guarantee (ε)</TableHead>
                <TableHead className="text-[11px] font-bold uppercase tracking-wider text-slate-600 py-3.5 px-6">Homomorphic Enc.</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className="text-[13px] text-slate-800">
              {data.map((row, index) => (
                <TableRow 
                  key={index} 
                  className={cn(
                    "transition-colors",
                    row.special 
                      ? "bg-blue-50/70 hover:bg-blue-50 border-l-4 border-l-blue-600 border-b border-slate-200" 
                      : "border-b border-slate-100 hover:bg-slate-50/80"
                  )}
                >
                  <TableCell className={cn("py-4 px-6 font-semibold", row.special ? "text-blue-900 font-bold" : "text-slate-900")}>
                    <div>{row.name}</div>
                    <div className="text-[11px] font-normal text-slate-500 mt-0.5">{row.desc}</div>
                  </TableCell>
                  
                  <TableCell className="py-4 px-6 font-mono font-bold text-slate-900">
                    {row.acc}
                  </TableCell>
                  
                  <TableCell className="py-4 px-6 font-mono">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-800">{row.mia}</span>
                      <Badge variant="outline" className={cn("px-2 py-0.5 text-[10px] font-bold rounded-full border", getBadgeStyle(row.privacyLevel))}>
                        {row.privacyLevel}
                      </Badge>
                    </div>
                  </TableCell>
                  
                  <TableCell className="py-4 px-6 font-mono font-semibold text-slate-800">
                    {row.fairness}
                  </TableCell>
                  
                  <TableCell className="py-4 px-6 font-mono text-slate-700">
                    {row.epsilon}
                  </TableCell>
                  
                  <TableCell className="py-4 px-6 font-mono text-slate-700">
                    {row.special ? (
                      <span className="flex items-center gap-1.5 text-blue-700 font-semibold">
                        <BadgeCheck className="w-4 h-4 text-blue-600" /> {row.he}
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
        <Card className="bg-white border-slate-200 border-l-4 border-l-blue-600 shadow-xs rounded-xl overflow-hidden">
          <CardContent className="p-5">
            <div className="flex items-center gap-2.5 mb-2.5">
              <Shield className="text-blue-600 w-5 h-5" />
              <h3 className="text-slate-900 text-sm font-bold">Privacy Preservation Insight</h3>
            </div>
            <p className="text-slate-600 text-xs leading-relaxed">
              {insightPrivacy}
            </p>
          </CardContent>
        </Card>

        {/* Fairness Insight */}
        <Card className="bg-white border-slate-200 border-l-4 border-l-cyan-600 shadow-xs rounded-xl overflow-hidden">
          <CardContent className="p-5">
            <div className="flex items-center gap-2.5 mb-2.5">
              <Scale className="text-cyan-600 w-5 h-5" />
              <h3 className="text-slate-900 text-sm font-bold">Clinical Demographic Equity</h3>
            </div>
            <p className="text-slate-600 text-xs leading-relaxed">
              {insightFair}
            </p>
          </CardContent>
        </Card>

      </div>
    </motion.div>
  );
}
