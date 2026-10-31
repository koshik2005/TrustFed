import React, { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Hospital as HospitalIcon, Users, Activity, Plus, Edit2, Ban,
  Trash2, KeyRound, Copy, Check, AlertTriangle, ShieldCheck,
  RefreshCw, CheckCircle2, Shield, Loader2, ArrowRight
} from 'lucide-react';
import { motion } from 'framer-motion';
import { api } from '@/services/api';
import { useAuthStore } from '@/store/authStore';

export default function RegionalDashboard() {
  const { user } = useAuthStore();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Add Hospital modal state
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [newHosp, setNewHosp] = useState({ id: '', name: '', share_deidentified: false });
  const [creating, setCreating] = useState(false);

  // Edit Hospital modal state
  const [editHosp, setEditHosp] = useState<any>(null);
  const [updating, setUpdating] = useState(false);

  // Destructive confirm state
  const [confirmAction, setConfirmAction] = useState<{
    type: 'suspend' | 'reactivate' | 'delete';
    hospital: any;
  } | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Issue credentials state
  const [issueModalHosp, setIssueModalHosp] = useState<any>(null);
  const [issueForm, setIssueForm] = useState<{ name: string; email: string; role: 'hospital_staff' | 'doctor' }>({
    name: '',
    email: '',
    role: 'doctor',
  });
  const [issuing, setIssuing] = useState(false);
  const [issuedResult, setIssuedResult] = useState<{ email: string; temp_password: string; role: string } | null>(null);
  const [copied, setCopied] = useState(false);

  // View Hospital Users state
  const [viewUsersHosp, setViewUsersHosp] = useState<any>(null);
  const [hospitalUsers, setHospitalUsers] = useState<any[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);

  const fetchRegionalData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.dashboardApi.getRegionalDashboard(user?.hubId || undefined);
      setData(res);
    } catch (err: any) {
      console.error('Failed to load regional dashboard:', err);
      setError(err?.response?.data?.detail || err?.message || 'Failed to load regional dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRegionalData();
  }, [user?.hubId]);

  const handleCreateHospital = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newHosp.id || !newHosp.name) return;
    setCreating(true);
    try {
      await api.regionalHospitalsApi.create(newHosp);
      setAddModalOpen(false);
      setNewHosp({ id: '', name: '', share_deidentified: false });
      await fetchRegionalData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to create hospital.');
    } finally {
      setCreating(false);
    }
  };

  const handleUpdateHospital = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editHosp) return;
    setUpdating(true);
    try {
      await api.regionalHospitalsApi.update(editHosp.id, {
        name: editHosp.name,
        share_deidentified: editHosp.shareDeidentified,
      });
      setEditHosp(null);
      await fetchRegionalData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to update hospital.');
    } finally {
      setUpdating(false);
    }
  };

  const handleExecuteAction = async () => {
    if (!confirmAction) return;
    setActionLoading(true);
    try {
      if (confirmAction.type === 'suspend') {
        await api.regionalHospitalsApi.suspend(confirmAction.hospital.id);
      } else if (confirmAction.type === 'reactivate') {
        await api.regionalHospitalsApi.reactivate(confirmAction.hospital.id);
      } else if (confirmAction.type === 'delete') {
        await api.regionalHospitalsApi.delete(confirmAction.hospital.id);
      }
      setConfirmAction(null);
      await fetchRegionalData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Operation failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleIssueUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!issueModalHosp || !issueForm.name || !issueForm.email) return;
    setIssuing(true);
    try {
      const res = await api.regionalHospitalsApi.issueUser(issueModalHosp.id, issueForm);
      setIssuedResult({
        email: issueForm.email,
        temp_password: res.temp_password,
        role: issueForm.role,
      });
      setIssueForm({ name: '', email: '', role: 'doctor' });
      await fetchRegionalData();
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to issue hospital user credentials.');
    } finally {
      setIssuing(false);
    }
  };

  const handleViewUsers = async (hosp: any) => {
    setViewUsersHosp(hosp);
    setLoadingUsers(true);
    try {
      const users = await api.regionalHospitalsApi.listUsers(hosp.id);
      setHospitalUsers(users);
    } catch (err: any) {
      console.error('Failed to load hospital users', err);
    } finally {
      setLoadingUsers(false);
    }
  };

  const handleSuspendUser = async (userId: string | number) => {
    if (!confirm('Are you sure you want to suspend this user? Their active session tokens will be revoked immediately.')) return;
    try {
      await api.regionalHospitalsApi.suspendUser(userId);
      if (viewUsersHosp) handleViewUsers(viewUsersHosp);
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to suspend user.');
    }
  };

  const handleDeleteUser = async (userId: string | number) => {
    if (!confirm('Are you sure you want to permanently delete this user?')) return;
    try {
      await api.regionalHospitalsApi.deleteUser(userId);
      if (viewUsersHosp) handleViewUsers(viewUsersHosp);
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to delete user.');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3" role="status" aria-label="Loading regional hub dashboard">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        <span className="text-sm font-medium text-slate-600">Loading regional hub metrics and hospitals…</span>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 max-w-xl mx-auto my-8 bg-red-50 border border-red-200 rounded-2xl text-center">
        <AlertTriangle className="w-10 h-10 text-red-500 mx-auto mb-3" />
        <h2 className="text-lg font-bold text-red-950 mb-1">Regional Dashboard Unavailable</h2>
        <p className="text-sm text-red-700 mb-4">{error || 'Unable to retrieve regional hub data.'}</p>
        <Button onClick={fetchRegionalData} variant="outline" className="border-red-300 text-red-800 hover:bg-red-100">
          <RefreshCw className="w-4 h-4 mr-2" /> Retry
        </Button>
      </div>
    );
  }

  const {
    hub,
    activeModelVersion,
    hospitals,
    totalHospitals,
    eligibleHospitalsCount,
    ineligibleHospitalsCount,
    regionalRecordVolume,
    regionalModelPerformance,
    perDiseaseAccuracy
  } = data;

  const activeHospitalsCount = hospitals?.filter((h: any) => h.status === 'active').length ?? 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col gap-6 max-w-[1440px] mx-auto w-full pb-10"
    >
      {/* ── TOP HEADER ROW ── */}
      <section className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-2xs">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <HospitalIcon className="w-5 h-5 text-blue-600" />
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
              {hub?.name || 'Regional Hub Coordinator'}
            </h1>
            <Badge className="bg-blue-50 text-blue-700 border-blue-200 text-xs font-semibold">
              Region: {hub?.region || 'Jurisdiction'}
            </Badge>
          </div>
          <p className="text-xs text-slate-500">
            Hub ID: <span className="font-mono font-semibold text-slate-700">{hub?.id}</span> · Active Global Model: <span className="font-mono font-semibold text-slate-700">{activeModelVersion}</span>
          </p>
        </div>

        <Button
          onClick={() => setAddModalOpen(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs shadow-xs"
        >
          <Plus className="w-3.5 h-3.5 mr-1.5" /> Add Hospital Node
        </Button>
      </section>

      {/* ── STAT CARDS ROW ── */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4" aria-label="Regional Hub KPI Metrics">
        {/* Card 1: Regional Record Volume */}
        <Card className="border-slate-200 shadow-2xs hover:border-blue-400 transition-colors">
          <CardContent className="p-5">
            <div className="flex justify-between items-start mb-3">
              <span className="text-slate-500 text-xs font-bold uppercase tracking-wider">Regional Volume</span>
              <Activity className="w-4 h-4 text-blue-500" />
            </div>
            <div className="text-slate-900 text-2xl font-bold font-mono tracking-tight mb-1">
              {regionalRecordVolume?.totalEncounters}
            </div>
            <div className="text-xs text-slate-500 flex items-center justify-between">
              <span>{regionalRecordVolume?.confirmedEncounters} confirmed</span>
              <span className="text-amber-700 font-semibold">{regionalRecordVolume?.pendingEncounters} pending</span>
            </div>
          </CardContent>
        </Card>

        {/* Card 2: Regional Model Performance */}
        <Card className="border-slate-200 shadow-2xs hover:border-indigo-400 transition-colors">
          <CardContent className="p-5">
            <div className="flex justify-between items-start mb-3">
              <span className="text-slate-500 text-xs font-bold uppercase tracking-wider">Regional Model F1</span>
              <ShieldCheck className="w-4 h-4 text-indigo-500" />
            </div>
            <div className="text-slate-900 text-2xl font-bold font-mono tracking-tight mb-1">
              {(regionalModelPerformance?.macroF1 * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-slate-500">
              Accuracy: <strong className="text-slate-700 font-mono">{(regionalModelPerformance?.accuracy * 100).toFixed(1)}%</strong>
            </div>
          </CardContent>
        </Card>

        {/* Card 3: Next Round Eligibility */}
        <Card className="border-slate-200 shadow-2xs hover:border-emerald-400 transition-colors">
          <CardContent className="p-5">
            <div className="flex justify-between items-start mb-3">
              <span className="text-slate-500 text-xs font-bold uppercase tracking-wider">Round Eligibility</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            </div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-slate-900 text-2xl font-bold font-mono tracking-tight">
                {eligibleHospitalsCount} / {totalHospitals}
              </span>
              <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200 text-[10px]">
                {eligibleHospitalsCount} Ready
              </Badge>
            </div>
            <div className="text-xs text-slate-500">
              {ineligibleHospitalsCount} need more confirmed records
            </div>
          </CardContent>
        </Card>

        {/* Card 4: Active Hospitals */}
        <Card className="border-slate-200 shadow-2xs hover:border-purple-400 transition-colors">
          <CardContent className="p-5">
            <div className="flex justify-between items-start mb-3">
              <span className="text-slate-500 text-xs font-bold uppercase tracking-wider">Active Hospitals</span>
              <HospitalIcon className="w-4 h-4 text-purple-500" />
            </div>
            <div className="text-slate-900 text-2xl font-bold font-mono tracking-tight mb-1">
              {activeHospitalsCount} of {totalHospitals}
            </div>
            <div className="text-xs text-slate-500">
              {totalHospitals - activeHospitalsCount} suspended nodes
            </div>
          </CardContent>
        </Card>
      </section>

      {/* ── PER-DISEASE ACCURACY BREAKDOWN ── */}
      <section className="bg-white rounded-2xl border border-slate-200 shadow-2xs p-5">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h2 className="text-base font-bold text-slate-900">Per-Disease Accuracy & Regional Representation</h2>
            <p className="text-xs text-slate-500">Clinical performance across common presenting conditions</p>
          </div>
          <Badge variant="outline" className="text-xs text-blue-700 bg-blue-50 border-blue-200">
            Regional Calibration
          </Badge>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3" aria-label="Per-disease accuracy breakdown">
          {perDiseaseAccuracy?.map((d: any) => {
            const accPct = Math.round(d.accuracy * 100);
            return (
              <div key={d.disease} className="p-3 rounded-xl bg-slate-50 border border-slate-100 text-xs">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-semibold text-slate-800">{d.displayName}</span>
                  <span className="font-mono font-bold text-slate-900">{accPct}% Accuracy</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden mb-1">
                  <div
                    className="bg-blue-600 h-1.5 rounded-full"
                    style={{ width: `${accPct}%` }}
                    aria-label={`${d.displayName} accuracy ${accPct} percent`}
                  />
                </div>
                <span className="text-[10px] text-slate-400 font-mono">{d.count} confirmed clinical records</span>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── HOSPITAL LIST WITH STATUS & MANAGEMENT CONTROLS ── */}
      <section className="bg-white rounded-2xl border border-slate-200 shadow-2xs overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex justify-between items-center">
          <div>
            <h2 className="text-base font-bold text-slate-900">Hospital Nodes in Jurisdiction</h2>
            <p className="text-xs text-slate-500">Manage hospital status, FL eligibility, credentials, and research consent</p>
          </div>
          <span className="text-xs font-semibold text-slate-500">{hospitals?.length} hospitals registered</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs" aria-label="Regional hospitals table">
            <thead className="bg-slate-50 text-slate-500 uppercase font-semibold text-[11px]">
              <tr>
                <th className="py-3 px-4">Hospital Name & ID</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Encounters</th>
                <th className="py-3 px-4">Confirmed</th>
                <th className="py-3 px-4">FL Eligibility</th>
                <th className="py-3 px-4">Research Consent</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {hospitals?.map((hosp: any) => (
                <tr key={hosp.id} className="hover:bg-slate-50 transition-colors">
                  <td className="py-3 px-4">
                    <span className="font-bold text-slate-900 block">{hosp.name}</span>
                    <span className="font-mono text-slate-400 text-[11px]">{hosp.id}</span>
                  </td>
                  <td className="py-3 px-4">
                    <Badge className={hosp.status === 'active' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-700 border-red-200'}>
                      {hosp.status}
                    </Badge>
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-700">{hosp.datasetSize}</td>
                  <td className="py-3 px-4 font-mono font-semibold text-slate-900">{hosp.confirmedCount}</td>
                  <td className="py-3 px-4">
                    <Badge
                      className={hosp.eligibleForRound ? 'bg-emerald-50 text-emerald-700 border-emerald-200 text-[10px]' : 'bg-amber-50 text-amber-700 border-amber-200 text-[10px]'}
                      title={hosp.eligibilityReason}
                    >
                      {hosp.eligibleForRound ? '✓ Eligible' : 'Ineligible'}
                    </Badge>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`text-[11px] font-semibold ${hosp.shareDeidentified ? 'text-emerald-700' : 'text-slate-400'}`}>
                      {hosp.shareDeidentified ? '● Granted' : '○ Default OFF'}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        onClick={() => {
                          setIssueModalHosp(hosp);
                          setIssuedResult(null);
                        }}
                        size="sm"
                        variant="ghost"
                        className="text-xs text-blue-600 hover:text-blue-800 h-7 px-2"
                        title="Issue Credentials"
                      >
                        <KeyRound className="w-3.5 h-3.5 mr-1" /> Creds
                      </Button>
                      <Button
                        onClick={() => handleViewUsers(hosp)}
                        size="sm"
                        variant="ghost"
                        className="text-xs text-slate-600 hover:text-slate-900 h-7 px-2"
                        title="View Users"
                      >
                        <Users className="w-3.5 h-3.5 mr-1" /> Users
                      </Button>
                      <Button
                        onClick={() => setEditHosp(hosp)}
                        size="sm"
                        variant="ghost"
                        className="text-xs text-slate-500 hover:text-slate-800 h-7 px-2"
                        title="Edit Hospital"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </Button>
                      {hosp.status === 'active' ? (
                        <Button
                          onClick={() => setConfirmAction({ type: 'suspend', hospital: hosp })}
                          size="sm"
                          variant="ghost"
                          className="text-xs text-amber-600 hover:text-amber-800 h-7 px-2"
                          title="Suspend Hospital"
                        >
                          <Ban className="w-3.5 h-3.5" />
                        </Button>
                      ) : (
                        <Button
                          onClick={() => setConfirmAction({ type: 'reactivate', hospital: hosp })}
                          size="sm"
                          variant="ghost"
                          className="text-xs text-emerald-600 hover:text-emerald-800 h-7 px-2"
                          title="Reactivate Hospital"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                        </Button>
                      )}
                      <Button
                        onClick={() => setConfirmAction({ type: 'delete', hospital: hosp })}
                        size="sm"
                        variant="ghost"
                        className="text-xs text-red-500 hover:text-red-700 h-7 px-2"
                        title="Delete Hospital"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── MODALS: ADD HOSPITAL ── */}
      {addModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in">
          <Card className="w-full max-w-md bg-white border-slate-200 shadow-xl rounded-2xl overflow-hidden">
            <form onSubmit={handleCreateHospital}>
              <div className="p-5 border-b border-slate-100 flex items-center justify-between">
                <h3 className="text-base font-bold text-slate-900">Add New Hospital Node</h3>
                <button type="button" onClick={() => setAddModalOpen(false)} className="text-slate-400 hover:text-slate-600 text-sm">✕</button>
              </div>
              <div className="p-5 flex flex-col gap-3 text-xs">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Hospital ID (unique slug)</label>
                  <Input
                    value={newHosp.id}
                    onChange={(e) => setNewHosp({ ...newHosp, id: e.target.value })}
                    placeholder="e.g. hosp-valley-memorial"
                    className="h-9 text-xs"
                    required
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Hospital Display Name</label>
                  <Input
                    value={newHosp.name}
                    onChange={(e) => setNewHosp({ ...newHosp, name: e.target.value })}
                    placeholder="e.g. Valley Memorial Hospital"
                    className="h-9 text-xs"
                    required
                  />
                </div>
              </div>
              <div className="p-5 border-t border-slate-100 flex items-center justify-end gap-2 bg-slate-50">
                <Button type="button" variant="outline" size="sm" onClick={() => setAddModalOpen(false)}>Cancel</Button>
                <Button type="submit" size="sm" disabled={creating} className="bg-blue-600 hover:bg-blue-700 text-white font-semibold">
                  {creating ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" /> : null} Create Hospital
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* ── MODALS: EDIT HOSPITAL ── */}
      {editHosp && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in">
          <Card className="w-full max-w-md bg-white border-slate-200 shadow-xl rounded-2xl overflow-hidden">
            <form onSubmit={handleUpdateHospital}>
              <div className="p-5 border-b border-slate-100 flex items-center justify-between">
                <h3 className="text-base font-bold text-slate-900">Edit Hospital Node</h3>
                <button type="button" onClick={() => setEditHosp(null)} className="text-slate-400 hover:text-slate-600 text-sm">✕</button>
              </div>
              <div className="p-5 flex flex-col gap-3 text-xs">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Hospital ID</label>
                  <Input value={editHosp.id} disabled className="h-9 text-xs bg-slate-100 font-mono text-slate-600" />
                </div>
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Hospital Name</label>
                  <Input
                    value={editHosp.name}
                    onChange={(e) => setEditHosp({ ...editHosp, name: e.target.value })}
                    className="h-9 text-xs"
                    required
                  />
                </div>
              </div>
              <div className="p-5 border-t border-slate-100 flex items-center justify-end gap-2 bg-slate-50">
                <Button type="button" variant="outline" size="sm" onClick={() => setEditHosp(null)}>Cancel</Button>
                <Button type="submit" size="sm" disabled={updating} className="bg-blue-600 hover:bg-blue-700 text-white font-semibold">
                  {updating ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" /> : null} Save Changes
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* ── MODALS: ISSUE CREDENTIALS ── */}
      {issueModalHosp && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in">
          <Card className="w-full max-w-md bg-white border-slate-200 shadow-xl rounded-2xl overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-900">Issue Hospital Credentials</h3>
              <button type="button" onClick={() => setIssueModalHosp(null)} className="text-slate-400 hover:text-slate-600 text-sm">✕</button>
            </div>

            {issuedResult ? (
              <div className="p-5 flex flex-col gap-4 text-xs">
                <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-950">
                  <span className="font-bold block mb-1">Credentials Issued Successfully</span>
                  <p className="text-[11px] text-emerald-800 mb-3">Copy this temporary password now. It will not be shown again.</p>
                  <div className="bg-white p-2.5 rounded-lg border border-emerald-200 font-mono flex items-center justify-between text-xs">
                    <span>{issuedResult.temp_password}</span>
                    <button onClick={() => copyToClipboard(issuedResult.temp_password)} className="text-emerald-700 hover:text-emerald-900">
                      {copied ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                <Button onClick={() => setIssueModalHosp(null)} className="w-full bg-blue-600 hover:bg-blue-700 text-white text-xs">
                  Done
                </Button>
              </div>
            ) : (
              <form onSubmit={handleIssueUser}>
                <div className="p-5 flex flex-col gap-3 text-xs">
                  <p className="text-slate-500">Creating credentials for <strong className="text-slate-800">{issueModalHosp.name}</strong></p>
                  <div>
                    <label className="font-semibold text-slate-700 block mb-1">User Full Name</label>
                    <Input
                      value={issueForm.name}
                      onChange={(e) => setIssueForm({ ...issueForm, name: e.target.value })}
                      placeholder="e.g. Dr. Jane Smith"
                      className="h-9 text-xs"
                      required
                    />
                  </div>
                  <div>
                    <label className="font-semibold text-slate-700 block mb-1">Email Address</label>
                    <Input
                      type="email"
                      value={issueForm.email}
                      onChange={(e) => setIssueForm({ ...issueForm, email: e.target.value })}
                      placeholder="e.g. jsmith@hospital.org"
                      className="h-9 text-xs"
                      required
                    />
                  </div>
                  <div>
                    <label className="font-semibold text-slate-700 block mb-1">Assigned Role</label>
                    <select
                      value={issueForm.role}
                      onChange={(e) => setIssueForm({ ...issueForm, role: e.target.value as any })}
                      className="w-full h-9 rounded-md border border-slate-300 bg-white px-3 py-1 text-xs"
                    >
                      <option value="doctor">Attending Doctor (can confirm diagnoses)</option>
                      <option value="hospital_staff">Hospital Staff (patient intake only)</option>
                    </select>
                  </div>
                </div>
                <div className="p-5 border-t border-slate-100 flex items-center justify-end gap-2 bg-slate-50">
                  <Button type="button" variant="outline" size="sm" onClick={() => setIssueModalHosp(null)}>Cancel</Button>
                  <Button type="submit" size="sm" disabled={issuing} className="bg-blue-600 hover:bg-blue-700 text-white font-semibold">
                    {issuing ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" /> : null} Issue Temporary Password
                  </Button>
                </div>
              </form>
            )}
          </Card>
        </div>
      )}

      {/* ── MODALS: CONFIRM DESTRUCTIVE ACTION ── */}
      {confirmAction && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in">
          <Card className="w-full max-w-md bg-white border-slate-200 shadow-xl rounded-2xl overflow-hidden p-6 text-center">
            <AlertTriangle className="w-10 h-10 text-amber-500 mx-auto mb-3" />
            <h3 className="text-base font-bold text-slate-900 mb-1 capitalize">
              {confirmAction.type} Hospital Node?
            </h3>
            <p className="text-xs text-slate-600 mb-5 leading-relaxed">
              Are you sure you want to {confirmAction.type} <strong className="text-slate-900">{confirmAction.hospital.name}</strong>?
              {confirmAction.type === 'suspend' && ' All user tokens will be immediately revoked and node excluded from future training rounds.'}
              {confirmAction.type === 'delete' && ' This permanently removes the hospital and cascades token revocation.'}
            </p>
            <div className="flex items-center justify-center gap-2">
              <Button variant="outline" size="sm" onClick={() => setConfirmAction(null)}>Cancel</Button>
              <Button
                onClick={handleExecuteAction}
                disabled={actionLoading}
                size="sm"
                className={confirmAction.type === 'delete' ? 'bg-red-600 hover:bg-red-700 text-white' : 'bg-amber-600 hover:bg-amber-700 text-white'}
              >
                {actionLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" /> : null} Confirm {confirmAction.type}
              </Button>
            </div>
          </Card>
        </div>
      )}
    </motion.div>
  );
}
