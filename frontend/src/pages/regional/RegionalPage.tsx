import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  Zap, Lock, Box, RefreshCw, CheckCircle2, Plus,
  Edit2, Ban, Trash2, KeyRound, Copy, Check, AlertTriangle, Users,
  Hospital as HospitalIcon, ShieldCheck, UserCheck, Loader2
} from 'lucide-react';
import { api } from '@/services/api';
import { useAuthStore } from '@/store/authStore';
import type { RegionalHospital, User } from '@/types';

export default function RegionalPage() {
  const { user } = useAuthStore();
  const [activeTab, setActiveTab] = useState<'hospitals' | 'telemetry'>('hospitals');
  const [hospitals, setHospitals] = useState<RegionalHospital[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Add / Edit Hospital modal state
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [newHosp, setNewHosp] = useState({ id: '', name: '', share_deidentified: false });
  const [creating, setCreating] = useState(false);

  const [editHosp, setEditHosp] = useState<RegionalHospital | null>(null);
  const [updating, setUpdating] = useState(false);

  // Destructive confirmation state
  const [confirmAction, setConfirmAction] = useState<{
    type: 'suspend' | 'reactivate' | 'delete';
    hospital: RegionalHospital;
  } | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Issue credentials state
  const [issueModalHosp, setIssueModalHosp] = useState<RegionalHospital | null>(null);
  const [issueForm, setIssueForm] = useState<{ name: string; email: string; role: 'hospital_staff' | 'doctor' }>({
    name: '',
    email: '',
    role: 'doctor',
  });
  const [issuing, setIssuing] = useState(false);
  const [issuedResult, setIssuedResult] = useState<{ email: string; temp_password: string; role: string } | null>(null);
  const [copied, setCopied] = useState(false);

  // View Hospital Users state
  const [viewUsersHosp, setViewUsersHosp] = useState<RegionalHospital | null>(null);
  const [hospitalUsers, setHospitalUsers] = useState<User[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);

  const loadHospitals = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.regionalHospitalsApi.list();
      setHospitals(data);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(axiosErr.response?.data?.detail || axiosErr.message || 'Failed to load hospitals.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    api.regionalHospitalsApi.list()
      .then((data) => {
        if (!ignore) {
          setHospitals(data);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!ignore) {
          const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
          setError(axiosErr.response?.data?.detail || axiosErr.message || 'Failed to load hospitals.');
          setLoading(false);
        }
      });
    return () => {
      ignore = true;
    };
  }, []);

  const handleCreateHospital = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newHosp.id || !newHosp.name) return;
    setCreating(true);
    try {
      await api.regionalHospitalsApi.create(newHosp);
      setAddModalOpen(false);
      setNewHosp({ id: '', name: '', share_deidentified: false });
      await loadHospitals();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
      alert(axiosErr.response?.data?.detail || 'Failed to create hospital.');
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
      await loadHospitals();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
      alert(axiosErr.response?.data?.detail || 'Failed to update hospital.');
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
      await loadHospitals();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
      alert(axiosErr.response?.data?.detail || 'Operation failed.');
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
      await loadHospitals();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
      alert(axiosErr.response?.data?.detail || 'Failed to issue hospital user credentials.');
    } finally {
      setIssuing(false);
    }
  };

  const handleViewUsers = async (hosp: RegionalHospital) => {
    setViewUsersHosp(hosp);
    setLoadingUsers(true);
    try {
      const users = await api.regionalHospitalsApi.listUsers(hosp.id);
      setHospitalUsers(users);
    } catch (err: unknown) {
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
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
      alert(axiosErr.response?.data?.detail || 'Failed to suspend user.');
    }
  };

  const handleDeleteUser = async (userId: string | number) => {
    if (!confirm('Are you sure you want to permanently delete this user?')) return;
    try {
      await api.regionalHospitalsApi.deleteUser(userId);
      if (viewUsersHosp) handleViewUsers(viewUsersHosp);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
      alert(axiosErr.response?.data?.detail || 'Failed to delete user.');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const activeCount = hospitals.filter((h) => h.status === 'active').length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col max-w-[1440px] mx-auto w-full pb-10 gap-6 relative"
    >
      {/* Background Ambient Glows */}
      <div className="fixed top-[-10%] left-[-10%] w-[50vw] h-[50vh] rounded-full bg-blue-500/10 blur-[120px] pointer-events-none -z-10" />
      <div className="fixed bottom-[-10%] right-[-10%] w-[40vw] h-[40vh] rounded-full bg-cyan-500/5 blur-[120px] pointer-events-none -z-10" />

      {/* PAGE HEADER */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs relative z-10">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Regional Hub Management</h1>
            <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 text-xs font-semibold">
              {user?.hubId ? `Assigned Hub: ${user.hubId}` : 'Regional Scope'}
            </Badge>
          </div>
          <p className="text-xs text-slate-500 font-medium">
            Manage jurisdictional hospital nodes, consent policies, and clinical credentials
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Tab Switcher */}
          <div className="flex items-center p-1 rounded-xl bg-slate-100 border border-slate-200/80 text-xs font-semibold">
            <button
              onClick={() => setActiveTab('hospitals')}
              className={`px-3 py-1.5 rounded-lg transition-colors ${
                activeTab === 'hospitals'
                  ? 'bg-white text-blue-700 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Hospitals ({hospitals.length})
            </button>
            <button
              onClick={() => setActiveTab('telemetry')}
              className={`px-3 py-1.5 rounded-lg transition-colors ${
                activeTab === 'telemetry'
                  ? 'bg-white text-blue-700 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              SMPC Telemetry
            </button>
          </div>

          <Button
            onClick={() => setAddModalOpen(true)}
            size="sm"
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl shadow-xs"
          >
            <Plus className="w-4 h-4" />
            <span>Add Hospital</span>
          </Button>
        </div>
      </header>

      {/* TOP STAT ROW */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 relative z-10">
        <Card className="bg-white border-slate-200 shadow-xs p-5 rounded-2xl flex flex-col justify-between">
          <div className="flex items-center justify-between mb-3 text-slate-500 text-xs font-medium">
            <span>Active Hospitals</span>
            <HospitalIcon className="w-4 h-4 text-blue-600" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900">{activeCount}</span>
            <span className="text-xs text-slate-500">of {hospitals.length} total</span>
          </div>
        </Card>

        <Card className="bg-white border-slate-200 shadow-xs p-5 rounded-2xl flex flex-col justify-between">
          <div className="flex items-center justify-between mb-3 text-slate-500 text-xs font-medium">
            <span>Aggregated Dataset Records</span>
            <Zap className="w-4 h-4 text-cyan-600" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900">
              {hospitals.reduce((acc, h) => acc + (h.datasetSize || 0), 0).toLocaleString()}
            </span>
            <span className="text-xs text-slate-500">records under FL</span>
          </div>
        </Card>

        <Card className="bg-white border-slate-200 shadow-xs p-5 rounded-2xl flex flex-col justify-between">
          <div className="flex items-center justify-between mb-3 text-slate-500 text-xs font-medium">
            <span>De-Identified Sharing Consent</span>
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-900">
              {hospitals.filter((h) => h.shareDeidentified).length}
            </span>
            <span className="text-xs text-slate-500">consenting nodes</span>
          </div>
        </Card>
      </div>

      {/* ERROR BANNER */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-between text-xs text-rose-700">
          <span>{error}</span>
          <Button variant="outline" size="sm" onClick={loadHospitals}>
            Retry
          </Button>
        </div>
      )}

      {/* HOSPITALS MANAGEMENT TAB */}
      {activeTab === 'hospitals' && (
        <Card className="bg-white border-slate-200 shadow-xs rounded-2xl overflow-hidden relative z-10">
          <div className="p-5 border-b border-slate-200 flex justify-between items-center bg-slate-50/60">
            <div>
              <h2 className="text-base font-bold text-slate-900">Regional Hospitals Directory</h2>
              <p className="text-xs text-slate-500">Manage hospitals, issue staff & doctor credentials, or toggle node status</p>
            </div>
            <Button
              onClick={loadHospitals}
              variant="outline"
              size="sm"
              className="text-xs flex items-center gap-1.5 text-slate-600 hover:text-slate-900"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </Button>
          </div>

          {loading ? (
            <div className="p-12 text-center text-slate-500 text-xs">
              <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-blue-600" />
              <span>Loading jurisdictional hospitals...</span>
            </div>
          ) : hospitals.length === 0 ? (
            <div className="p-12 text-center text-slate-500">
              <HospitalIcon className="w-8 h-8 text-slate-400 mx-auto mb-2" />
              <p className="text-sm font-semibold text-slate-800">No Hospitals Registered In This Hub</p>
              <p className="text-xs text-slate-500 mt-1 mb-4">Add your first regional hospital node to begin federated training.</p>
              <Button onClick={() => setAddModalOpen(true)} size="sm" className="bg-blue-600 text-white rounded-xl">
                <Plus className="w-4 h-4 mr-1.5" /> Add Hospital
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader className="bg-slate-50/80">
                  <TableRow>
                    <TableHead className="text-xs font-semibold text-slate-600 py-3.5">Hospital Name</TableHead>
                    <TableHead className="text-xs font-semibold text-slate-600 py-3.5">Status</TableHead>
                    <TableHead className="text-xs font-semibold text-slate-600 py-3.5">De-Identified Sharing</TableHead>
                    <TableHead className="text-xs font-semibold text-slate-600 py-3.5">FL Node</TableHead>
                    <TableHead className="text-xs font-semibold text-slate-600 py-3.5">Dataset Size</TableHead>
                    <TableHead className="text-xs font-semibold text-slate-600 py-3.5">Staff & Doctors</TableHead>
                    <TableHead className="text-xs font-semibold text-slate-600 py-3.5 text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody className="text-xs text-slate-800">
                  {hospitals.map((hosp) => (
                    <TableRow key={hosp.id} className="hover:bg-slate-50 transition-colors">
                      <TableCell className="py-3.5 font-medium">
                        <div>
                          <span className="font-semibold text-slate-900">{hosp.name}</span>
                          <span className="block font-mono text-[11px] text-slate-500">{hosp.id}</span>
                        </div>
                      </TableCell>
                      <TableCell className="py-3.5">
                        <Badge
                          variant="outline"
                          className={`capitalize text-[11px] font-semibold ${
                            hosp.status === 'active'
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                              : 'bg-amber-50 text-amber-700 border-amber-200'
                          }`}
                        >
                          {hosp.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="py-3.5">
                        <span
                          className={`inline-flex items-center gap-1.5 text-[11px] font-medium px-2 py-0.5 rounded-full ${
                            hosp.shareDeidentified
                              ? 'bg-emerald-50 text-emerald-700'
                              : 'bg-slate-100 text-slate-600'
                          }`}
                        >
                          {hosp.shareDeidentified ? (
                            <>
                              <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Consented
                            </>
                          ) : (
                            'Private Only'
                          )}
                        </span>
                      </TableCell>
                      <TableCell className="py-3.5">
                        <span className="capitalize font-mono text-slate-600 text-[11px]">
                          {hosp.nodeStatus}
                        </span>
                      </TableCell>
                      <TableCell className="py-3.5 text-slate-600">
                        {hosp.datasetSize ? hosp.datasetSize.toLocaleString() : 0} cases
                      </TableCell>
                      <TableCell className="py-3.5">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleViewUsers(hosp)}
                          className="text-xs flex items-center gap-1.5 text-blue-600 hover:text-blue-700 hover:bg-blue-50 px-2 py-1 h-auto"
                        >
                          <Users className="w-3.5 h-3.5" />
                          <span>{hosp.userCount} users</span>
                        </Button>
                      </TableCell>
                      <TableCell className="py-3.5 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={hosp.status !== 'active'}
                            onClick={() => {
                              setIssueModalHosp(hosp);
                              setIssuedResult(null);
                            }}
                            className="text-[11px] h-7 px-2 text-blue-600 border-blue-200 hover:bg-blue-50 rounded-lg"
                          >
                            <KeyRound className="w-3 h-3 mr-1" />
                            <span>Issue Credentials</span>
                          </Button>

                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setEditHosp(hosp)}
                            className="text-[11px] h-7 px-2 text-slate-700 hover:bg-slate-50 rounded-lg"
                          >
                            <Edit2 className="w-3 h-3 mr-1" />
                            <span>Edit</span>
                          </Button>

                          {hosp.status === 'active' ? (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => setConfirmAction({ type: 'suspend', hospital: hosp })}
                              className="text-[11px] h-7 px-2 text-amber-700 border-amber-200 hover:bg-amber-50 rounded-lg"
                            >
                              <Ban className="w-3 h-3 mr-1" />
                              <span>Suspend</span>
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => setConfirmAction({ type: 'reactivate', hospital: hosp })}
                              className="text-[11px] h-7 px-2 text-emerald-700 border-emerald-200 hover:bg-emerald-50 rounded-lg"
                            >
                              <CheckCircle2 className="w-3 h-3 mr-1" />
                              <span>Reactivate</span>
                            </Button>
                          )}

                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setConfirmAction({ type: 'delete', hospital: hosp })}
                            className="text-[11px] h-7 px-2 text-rose-600 border-rose-200 hover:bg-rose-50 rounded-lg"
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </Card>
      )}

      {/* SMPC TELEMETRY TAB */}
      {activeTab === 'telemetry' && (
        <div className="space-y-6">
          <Card className="glass-card bg-white border-slate-200 overflow-hidden relative z-10 shadow-sm rounded-2xl">
            <CardContent className="p-6">
              <div className="flex flex-col md:flex-row items-center justify-between gap-6 py-6 border border-slate-200/80 rounded-2xl bg-slate-50/50 p-6">
                {/* Left Hospitals */}
                <div className="flex flex-col gap-3 w-full md:w-auto">
                  {hospitals.slice(0, 3).map((h, i) => (
                    <div key={h.id} className="flex items-center gap-3 bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
                      <div className={`w-3 h-3 rounded-full ${i === 0 ? 'bg-blue-500' : i === 1 ? 'bg-cyan-400' : 'bg-emerald-500'}`} />
                      <div>
                        <span className="font-semibold text-xs text-slate-800">{h.name}</span>
                        <p className="text-[10px] text-slate-500 font-mono">Status: {h.nodeStatus}</p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Secret Shares Center */}
                <div className="flex flex-col items-center justify-center p-4 rounded-full w-24 h-24 bg-white border border-blue-500/30 shadow-md">
                  <Lock className="text-blue-600 w-6 h-6 mb-1" />
                  <span className="text-[9px] uppercase font-bold text-blue-600 tracking-wider text-center leading-tight">
                    Secret<br />Shares
                  </span>
                </div>

                {/* Right Regional Aggregate */}
                <div className="bg-white border border-blue-500/30 rounded-xl p-5 shadow-xs w-full md:w-auto flex flex-col items-center">
                  <Box className="text-slate-800 mb-2 w-6 h-6" />
                  <span className="font-mono text-xs text-slate-900 font-bold">Regional Aggregate</span>
                  <span className="text-[11px] text-slate-500 mt-1">Homomorphically aggregated encrypted weights</span>
                </div>
              </div>
              <p className="text-xs text-slate-500 italic mt-4">
                Each hospital splits its update into secret shares. No hub or global server ever observes unencrypted individual patient weights.
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Add Hospital Modal */}
      {addModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-md w-full p-6 text-slate-900">
            <h3 className="text-base font-bold text-slate-900 mb-1">Add Hospital to Hub</h3>
            <p className="text-xs text-slate-500 mb-4">Provision a new clinical node in your regional hub.</p>
            <form onSubmit={handleCreateHospital} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Hospital ID (e.g. hosp-general)</label>
                <Input
                  placeholder="hosp-general"
                  value={newHosp.id}
                  onChange={(e) => setNewHosp({ ...newHosp, id: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Hospital Name</label>
                <Input
                  placeholder="Metropolitan General Hospital"
                  value={newHosp.name}
                  onChange={(e) => setNewHosp({ ...newHosp, name: e.target.value })}
                  required
                />
              </div>
              <div className="flex items-center gap-2.5 pt-1">
                <input
                  type="checkbox"
                  id="consent-check"
                  checked={newHosp.share_deidentified}
                  onChange={(e) => setNewHosp({ ...newHosp, share_deidentified: e.target.checked })}
                  className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="consent-check" className="text-xs text-slate-700 font-medium cursor-pointer">
                  Consent to share de-identified clinical records for federated training
                </label>
              </div>
              <div className="flex items-center justify-end gap-3 pt-3">
                <Button type="button" variant="outline" onClick={() => setAddModalOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={creating} className="bg-blue-600 text-white">
                  {creating ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                  <span>Add Hospital</span>
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Hospital Modal */}
      {editHosp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-md w-full p-6 text-slate-900">
            <h3 className="text-base font-bold text-slate-900 mb-1">Edit Hospital Settings</h3>
            <p className="text-xs text-slate-500 mb-4">Update policy and name for {editHosp.id}.</p>
            <form onSubmit={handleUpdateHospital} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Hospital Name</label>
                <Input
                  value={editHosp.name}
                  onChange={(e) => setEditHosp({ ...editHosp, name: e.target.value })}
                  required
                />
              </div>
              <div className="flex items-center gap-2.5 pt-1">
                <input
                  type="checkbox"
                  id="edit-consent-check"
                  checked={editHosp.shareDeidentified}
                  onChange={(e) => setEditHosp({ ...editHosp, shareDeidentified: e.target.checked })}
                  className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="edit-consent-check" className="text-xs text-slate-700 font-medium cursor-pointer">
                  Share de-identified clinical records for federated training
                </label>
              </div>
              <div className="flex items-center justify-end gap-3 pt-3">
                <Button type="button" variant="outline" onClick={() => setEditHosp(null)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={updating} className="bg-blue-600 text-white">
                  {updating ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                  <span>Save Changes</span>
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirmation Dialog (Suspend / Reactivate / Delete Hospital) */}
      {confirmAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-md w-full p-6 text-slate-900">
            <div className="flex items-center gap-3 mb-3">
              <div
                className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                  confirmAction.type === 'delete'
                    ? 'bg-rose-100 text-rose-600'
                    : confirmAction.type === 'suspend'
                    ? 'bg-amber-100 text-amber-600'
                    : 'bg-emerald-100 text-emerald-600'
                }`}
              >
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 capitalize">
                  {confirmAction.type} Hospital: {confirmAction.hospital.name}
                </h3>
                <p className="text-xs text-slate-500 font-mono">ID: {confirmAction.hospital.id}</p>
              </div>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed mb-6">
              {confirmAction.type === 'suspend' && (
                <>
                  Suspending this hospital will <strong>immediately revoke all active access tokens</strong> for its staff and doctors.
                  The hospital node will be set offline and excluded from future federated training rounds.
                </>
              )}
              {confirmAction.type === 'reactivate' && (
                <>
                  Reactivating will restore access for hospital personnel and set the node back to active training status.
                </>
              )}
              {confirmAction.type === 'delete' && (
                <>
                  Permanently removes this hospital and revokes all dependent user accounts.
                </>
              )}
            </p>

            <div className="flex items-center justify-end gap-3">
              <Button type="button" variant="outline" onClick={() => setConfirmAction(null)}>
                Cancel
              </Button>
              <Button
                onClick={handleExecuteAction}
                disabled={actionLoading}
                className={
                  confirmAction.type === 'delete'
                    ? 'bg-rose-600 hover:bg-rose-700 text-white'
                    : confirmAction.type === 'suspend'
                    ? 'bg-amber-600 hover:bg-amber-700 text-white'
                    : 'bg-emerald-600 hover:bg-emerald-700 text-white'
                }
              >
                {actionLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                <span className="capitalize">Confirm {confirmAction.type}</span>
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Issue Hospital User Credentials Modal */}
      {issueModalHosp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-md w-full p-6 text-slate-900">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-600 flex items-center justify-center">
                <KeyRound className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">Issue Clinical Credentials</h3>
                <p className="text-xs text-slate-500">{issueModalHosp.name}</p>
              </div>
            </div>

            {!issuedResult ? (
              <form onSubmit={handleIssueUser} className="space-y-4">
                <p className="text-xs text-slate-600 leading-relaxed bg-slate-50 p-3 rounded-xl border border-slate-200">
                  Issues a one-time temporary credential. The user must complete a password reset before accessing patient data.
                </p>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">User Role</label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setIssueForm({ ...issueForm, role: 'doctor' })}
                      className={`py-2 px-3 rounded-xl border text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors ${
                        issueForm.role === 'doctor'
                          ? 'border-blue-600 bg-blue-50 text-blue-700'
                          : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      <UserCheck className="w-4 h-4" /> Doctor
                    </button>
                    <button
                      type="button"
                      onClick={() => setIssueForm({ ...issueForm, role: 'hospital_staff' })}
                      className={`py-2 px-3 rounded-xl border text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors ${
                        issueForm.role === 'hospital_staff'
                          ? 'border-blue-600 bg-blue-50 text-blue-700'
                          : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      <Users className="w-4 h-4" /> Hospital Staff
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name</label>
                  <Input
                    placeholder="e.g. Dr. Robert Vance"
                    value={issueForm.name}
                    onChange={(e) => setIssueForm({ ...issueForm, name: e.target.value })}
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Email Address</label>
                  <Input
                    type="email"
                    placeholder="e.g. r.vance@hospital.org"
                    value={issueForm.email}
                    onChange={(e) => setIssueForm({ ...issueForm, email: e.target.value })}
                    required
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-3">
                  <Button type="button" variant="outline" onClick={() => setIssueModalHosp(null)}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={issuing} className="bg-blue-600 text-white">
                    {issuing ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                    <span>Issue Credentials</span>
                  </Button>
                </div>
              </form>
            ) : (
              <div className="space-y-4">
                <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs">
                  <strong>Credentials Generated!</strong> Role:{' '}
                  <span className="font-semibold capitalize">{issuedResult.role}</span>
                </div>

                <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2.5">
                  <div>
                    <span className="text-[10px] font-bold uppercase text-slate-500">Email (Username)</span>
                    <p className="text-xs font-mono font-semibold text-slate-800">{issuedResult.email}</p>
                  </div>
                  <div>
                    <span className="text-[10px] font-bold uppercase text-slate-500">Temporary Password (Shown Once Only)</span>
                    <div className="flex items-center gap-2 mt-1">
                      <code className="text-xs font-mono font-bold bg-white px-3 py-1.5 rounded-lg border border-slate-300 text-blue-700 flex-1 truncate select-all">
                        {issuedResult.temp_password}
                      </code>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => copyToClipboard(issuedResult.temp_password)}
                        className="flex items-center gap-1.5 text-xs text-slate-700 hover:text-slate-900"
                      >
                        {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                        <span>{copied ? 'Copied' : 'Copy'}</span>
                      </Button>
                    </div>
                  </div>
                </div>

                <p className="text-[11px] text-amber-700 bg-amber-50 p-2.5 rounded-xl border border-amber-200 leading-relaxed">
                  ⚠️ This temporary password is not stored in plaintext and cannot be recovered. Ensure you copy it before closing.
                </p>

                <div className="flex justify-end pt-2">
                  <Button
                    onClick={() => {
                      setIssueModalHosp(null);
                      setIssuedResult(null);
                    }}
                    className="bg-blue-600 text-white"
                  >
                    Done
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* View Hospital Users Drawer / Modal */}
      {viewUsersHosp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-lg w-full p-6 text-slate-900">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2.5">
                <Users className="w-5 h-5 text-blue-600" />
                <div>
                  <h3 className="text-base font-bold text-slate-900">Hospital Users</h3>
                  <p className="text-xs text-slate-500">{viewUsersHosp.name}</p>
                </div>
              </div>
              <Button size="sm" variant="ghost" onClick={() => setViewUsersHosp(null)}>
                Close
              </Button>
            </div>

            {loadingUsers ? (
              <div className="py-8 text-center text-xs text-slate-500">
                <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2 text-blue-600" />
                <span>Loading users...</span>
              </div>
            ) : hospitalUsers.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-500">
                <Users className="w-6 h-6 mx-auto mb-2 text-slate-400" />
                <p>No users provisioned for this hospital yet.</p>
              </div>
            ) : (
              <div className="max-h-72 overflow-y-auto space-y-2 pr-1">
                {hospitalUsers.map((usr) => (
                  <div
                    key={usr.id}
                    className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200/80 text-xs"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-900">{usr.name}</span>
                        <Badge variant="outline" className="text-[10px] capitalize px-1.5 py-0">
                          {usr.role.replace('_', ' ')}
                        </Badge>
                      </div>
                      <span className="text-[11px] text-slate-500 font-mono">{usr.email}</span>
                      {usr.status && usr.status !== 'active' && (
                        <span className="ml-2 text-[10px] text-rose-600 font-semibold uppercase">({usr.status})</span>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5">
                      {usr.status === 'active' && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleSuspendUser(usr.id)}
                          className="h-7 px-2 text-amber-700 hover:bg-amber-50"
                        >
                          Suspend
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDeleteUser(usr.id)}
                        className="h-7 px-2 text-rose-600 hover:bg-rose-50"
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </motion.div>
  );
}
