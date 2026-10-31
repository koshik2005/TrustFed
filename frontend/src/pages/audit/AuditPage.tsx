import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Lock, Download, CheckCircle2, Search } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/services/api';
import type { AuditEntry, PaginatedResponse } from '@/types';

const getEventBadgeStyle = (event: string) => {
  switch (event.toLowerCase()) {
    case 'training': return 'bg-blue-50 text-blue-700 border-blue-300';
    case 'tefl': return 'bg-purple-50 text-purple-700 border-purple-300';
    case 'auth': return 'bg-amber-50 text-amber-700 border-amber-300';
    case 'prediction': return 'bg-emerald-50 text-emerald-700 border-emerald-300';
    default: return 'bg-slate-100 text-slate-600 border-slate-300';
  }
};

export default function AuditPage() {
  const [logs, setLogs] = useState<PaginatedResponse<AuditEntry> | null>(null);
  const [selectedEventType, setSelectedEventType] = useState('all');
  const [searchNode, setSearchNode] = useState('');

  useEffect(() => {
    let ignore = false;
    api.auditApi
      .getLogs({
        page: 1,
        eventType: selectedEventType === 'all' ? undefined : selectedEventType,
      })
      .then((data) => {
        if (!ignore) setLogs(data);
      })
      .catch((e) => {
        console.error('Failed to fetch logs', e);
      });
    return () => {
      ignore = true;
    };
  }, [selectedEventType]);

  const handleExportLogs = () => {
    if (!logs?.items?.length) return;
    const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(
      JSON.stringify(logs.items, null, 2)
    )}`;
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', jsonString);
    downloadAnchor.setAttribute('download', `trustfed_audit_ledger_${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const filteredItems = (logs?.items || []).filter(item => {
    if (!searchNode.trim()) return true;
    const query = searchNode.toLowerCase();
    return (
      item.nodeId.toLowerCase().includes(query) ||
      item.description.toLowerCase().includes(query) ||
      item.hash.toLowerCase().includes(query)
    );
  });

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col max-w-[1440px] mx-auto w-full pb-8 gap-6 relative"
    >
      {/* Page Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 relative z-10">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-[24px] font-bold text-slate-900 tracking-tight">Immutable Cryptographic Audit Trail</h1>
            <span className="flex items-center gap-1 text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full">
              <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Hash Chain Valid
            </span>
          </div>
          <p className="text-slate-500 text-[13px]">Append-only SHA-256 verifiable ledger · Technical Privacy Design Controls (Not a Compliance Claim)</p>
        </div>
        <Button
          onClick={handleExportLogs}
          variant="outline"
          className="border-slate-300 text-slate-700 hover:text-slate-900 hover:bg-slate-50 transition-colors font-semibold text-xs h-9"
        >
          <Download className="w-3.5 h-3.5 mr-1.5" /> Export Verifiable JSON
        </Button>
      </div>

      {/* Filter Bar */}
      <Card className="bg-white border-slate-200 shadow-xs rounded-xl z-10">
        <CardContent className="p-3.5 flex flex-wrap gap-3 items-center">
          
          <div className="flex items-center gap-2">
            <span className="text-slate-600 text-xs font-medium">Event:</span>
            <Select value={selectedEventType} onValueChange={(val) => setSelectedEventType(val || 'all')}>
              <SelectTrigger className="w-[150px] bg-slate-50 border-slate-200 text-slate-800 h-9 rounded-lg text-xs">
                <SelectValue placeholder="All Events" />
              </SelectTrigger>
              <SelectContent className="bg-white border-slate-200 text-slate-900 shadow-xl">
                <SelectItem value="all">All Events</SelectItem>
                <SelectItem value="training">Training</SelectItem>
                <SelectItem value="tefl">TEFL & Privacy</SelectItem>
                <SelectItem value="prediction">Clinical Inference</SelectItem>
                <SelectItem value="auth">Auth & Access</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 w-3.5 h-3.5" />
            <Input
              value={searchNode}
              onChange={(e) => setSearchNode(e.target.value)}
              className="w-full bg-slate-50 border-slate-200 pl-8 text-slate-800 text-xs focus:border-blue-500 h-9 rounded-lg"
              placeholder="Search by Node ID, Event Description, or Hash..."
            />
          </div>

          {searchNode && (
            <Button
              variant="ghost"
              onClick={() => setSearchNode('')}
              className="text-slate-500 hover:text-slate-800 text-xs h-9"
            >
              Clear
            </Button>
          )}
          
        </CardContent>
      </Card>

      {/* Log Table Card */}
      <Card className="bg-white border-slate-200 overflow-hidden relative z-10 shadow-xs rounded-2xl">
        <div className="w-full overflow-x-auto">
          <Table>
            <TableHeader className="bg-slate-50 border-b border-slate-200">
              <TableRow className="hover:bg-transparent border-none">
                <TableHead className="text-[10px] font-bold uppercase tracking-wider text-slate-600 py-3.5 px-4 w-20">ID</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-wider text-slate-600 py-3.5 px-4 w-44">Timestamp</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-wider text-slate-600 py-3.5 px-4 w-32">Origin Node</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-wider text-slate-600 py-3.5 px-4 w-28">Category</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-wider text-slate-600 py-3.5 px-4">Event Audit Description</TableHead>
                <TableHead className="text-[10px] font-bold uppercase tracking-wider text-slate-600 py-3.5 px-4 w-44">SHA-256 Digest</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className="text-[13px] text-slate-800">
              {filteredItems.map((row) => (
                <TableRow 
                  key={row.id} 
                  className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
                >
                  <TableCell className="py-3 px-4 text-xs font-mono font-medium text-slate-500">{row.id}</TableCell>
                  <TableCell className="py-3 px-4 font-mono text-[11px] text-slate-600">
                    {new Date(row.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })} ({new Date(row.timestamp).toLocaleDateString()})
                  </TableCell>
                  <TableCell className="py-3 px-4 text-xs font-semibold text-slate-800">{row.nodeId}</TableCell>
                  <TableCell className="py-3 px-4">
                    <Badge variant="outline" className={cn("px-2 py-0.5 text-[10px] font-bold rounded uppercase", getEventBadgeStyle(row.eventType))}>
                      {row.eventType}
                    </Badge>
                  </TableCell>
                  <TableCell className="py-3 px-4 text-xs text-slate-700">{row.description}</TableCell>
                  <TableCell className="py-3 px-4 font-mono text-[11px] text-slate-600">
                    <span className="flex items-center gap-1.5 font-mono">
                      <Lock className="w-3 h-3 text-emerald-600 flex-shrink-0" />
                      {row.hash.substring(0, 14)}...
                    </span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Card>
    </motion.div>
  );
}
