import React from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Calendar, Lock, Download, ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/services/api';
import type { AuditEntry, PaginatedResponse } from '@/types';

const getEventBadgeStyle = (event: string) => {
  switch (event) {
    case 'TRAINING': return 'bg-blue-500/15 text-blue-300 border-blue-500/30';
    case 'TEFL': return 'bg-purple-500/15 text-purple-300 border-purple-500/30';
    case 'AUTH': return 'bg-amber-500/15 text-amber-300 border-amber-500/30';
    default: return 'bg-slate-500/15 text-slate-700 border-slate-500/30';
  }
};

export default function AuditPage() {
  const [logs, setLogs] = React.useState<PaginatedResponse<AuditEntry> | null>(null);

  React.useEffect(() => {
    const fetchLogs = async () => {
      try {
        const data = await api.auditApi.getLogs({ page: 1 });
        setLogs(data);
      } catch (e) {
        console.error("Failed to fetch logs", e);
      }
    };
    fetchLogs();
  }, []);

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col max-w-[1440px] mx-auto w-full pb-8 gap-8 relative"
    >
      {/* Background Ambient Glows */}
      <div className="fixed top-[20%] right-[10%] w-[40vw] h-[40vh] rounded-full bg-blue-500/5 blur-[120px] pointer-events-none -z-10" />

      {/* Page Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 relative z-10">
        <div>
          <h1 className="text-[24px] font-bold text-slate-900 mb-1 tracking-tight">Immutable Audit Log</h1>
          <p className="text-slate-600 text-[13px]">Append-only cryptographic event ledger · HIPAA / GDPR Compliant</p>
        </div>
        <Button variant="outline" className="border-slate-600 text-slate-700 hover:text-slate-900 hover:bg-slate-800 transition-colors">
          <Download className="w-4 h-4 mr-2" /> Export Logs
        </Button>
      </div>

      {/* Filter Bar */}
      <Card className="glass-card bg-white border-slate-200 z-10">
        <CardContent className="p-4 flex flex-wrap gap-4 items-center">
          
          <div className="flex items-center gap-3">
            <span className="text-slate-600 text-sm">From</span>
            <div className="relative w-[140px]">
              <Calendar className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-600 w-4 h-4" />
              <Input className="bg-white border-slate-200 pl-9 text-slate-800 focus:border-blue-500 h-9" placeholder="YYYY-MM-DD" />
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <span className="text-slate-600 text-sm">To</span>
            <div className="relative w-[140px]">
              <Calendar className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-600 w-4 h-4" />
              <Input className="bg-white border-slate-200 pl-9 text-slate-800 focus:border-blue-500 h-9" placeholder="YYYY-MM-DD" />
            </div>
          </div>

          <Select defaultValue="all">
            <SelectTrigger className="w-[160px] bg-white border-slate-200 text-slate-800 h-9">
              <SelectValue placeholder="All Events" />
            </SelectTrigger>
            <SelectContent className="bg-[#0f172a] border-slate-200 text-slate-800">
              <SelectItem value="all">All Events</SelectItem>
              <SelectItem value="training">Training</SelectItem>
              <SelectItem value="tefl">TEFL</SelectItem>
              <SelectItem value="auth">Auth</SelectItem>
            </SelectContent>
          </Select>

          <Input className="w-[200px] bg-white border-slate-200 text-slate-800 focus:border-blue-500 h-9" placeholder="Filter by node ID..." />

          <div className="ml-auto flex gap-2">
            <Button className="bg-blue-500/20 text-blue-400 border border-blue-500/30 hover:bg-blue-500/30 h-9">
              Apply Filters
            </Button>
            <Button variant="ghost" className="text-slate-600 hover:text-slate-900 h-9">
              Clear
            </Button>
          </div>
          
        </CardContent>
      </Card>

      {/* Log Table Card */}
      <Card className="glass-card bg-white border-slate-200 overflow-hidden relative z-10 shadow-lg">
        <div className="w-full overflow-x-auto">
          <Table>
            <TableHeader className="bg-[#040810] border-b border-slate-200">
              <TableRow className="hover:bg-transparent border-none">
                <TableHead className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 py-3 px-4 h-auto w-12">#</TableHead>
                <TableHead className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 py-3 px-4 h-auto w-48">Timestamp</TableHead>
                <TableHead className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 py-3 px-4 h-auto w-32">Node</TableHead>
                <TableHead className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 py-3 px-4 h-auto w-32">Event</TableHead>
                <TableHead className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 py-3 px-4 h-auto">Description</TableHead>
                <TableHead className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 py-3 px-4 h-auto w-40">Hash</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className="text-[13px] text-slate-800">
              {logs?.items.map((row) => (
                <TableRow 
                  key={row.id} 
                  className="border-t border-slate-200 hover:bg-slate-50 even:bg-white/[0.015] transition-colors"
                >
                  <TableCell className="py-3 px-4 text-slate-500">{row.id}</TableCell>
                  <TableCell className="py-3 px-4 font-mono text-[12px] text-slate-700">
                    {new Date(row.timestamp).toLocaleString()}
                  </TableCell>
                  <TableCell className="py-3 px-4">{row.nodeId}</TableCell>
                  <TableCell className="py-3 px-4">
                    <Badge variant="outline" className={cn("px-2 py-0.5 text-xs font-semibold rounded uppercase", getEventBadgeStyle(row.eventType))}>
                      {row.eventType}
                    </Badge>
                  </TableCell>
                  <TableCell className="py-3 px-4 text-slate-700">{row.description}</TableCell>
                  <TableCell className="py-3 px-4 font-mono text-[12px] text-slate-500">
                    <span className="flex items-center gap-1.5">
                      <Lock className="w-3 h-3 text-emerald-400" />
                      {row.hash.substring(0, 10)}...
                    </span>
                  </TableCell>
                </TableRow>
              ))}
              {!logs && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-slate-500">Loading secure ledger...</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>

        {/* Pagination Bar */}
        <div className="px-4 py-3 border-t border-slate-200 flex justify-between items-center bg-[#050A14]/50">
          <span className="text-slate-600 text-[13px]">Showing 1–20 of 1,847 entries</span>
          
          <div className="flex items-center gap-1 text-sm text-slate-600">
            <Button variant="ghost" size="sm" className="h-8 hover:text-slate-900 transition-colors">
              <ChevronLeft className="w-4 h-4 mr-1" /> Previous
            </Button>
            <Button variant="ghost" size="sm" className="h-8 w-8 p-0 bg-slate-200 text-slate-900 hover:bg-white/20 transition-colors">1</Button>
            <Button variant="ghost" size="sm" className="h-8 w-8 p-0 hover:text-slate-900 transition-colors">2</Button>
            <Button variant="ghost" size="sm" className="h-8 w-8 p-0 hover:text-slate-900 transition-colors">3</Button>
            <span className="px-1 text-slate-500">...</span>
            <Button variant="ghost" size="sm" className="h-8 w-8 p-0 hover:text-slate-900 transition-colors">93</Button>
            <Button variant="ghost" size="sm" className="h-8 hover:text-slate-900 transition-colors">
              Next <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
        </div>
      </Card>
      
    </motion.div>
  );
}
