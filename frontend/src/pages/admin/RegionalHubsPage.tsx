import React, { useState, useEffect } from 'react';
import {
  Network, Plus, Edit2, Ban, CheckCircle2, Trash2, KeyRound,
  Copy, Check, AlertTriangle, Loader2, Hospital, Users, RefreshCw
} from 'lucide-react';
import { api } from '@/services/api';
import type { RegionalHub } from '@/types';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

export default function RegionalHubsPage() {
  const [hubs, setHubs] = useState<RegionalHub[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals state
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [newHub, setNewHub] = useState({ id: '', name: '', region: '' });
  const [creating, setCreating] = useState(false);

  const [editHub, setEditHub] = useState<RegionalHub | null>(null);
  const [updating, setUpdating] = useState(false);

  const [confirmAction, setConfirmAction] = useState<{
    type: 'suspend' | 'reactivate' | 'delete';
    hub: RegionalHub;
  } | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Issue credentials state
  const [issueModalHub, setIssueModalHub] = useState<RegionalHub | null>(null);
  const [issueForm, setIssueForm] = useState({ name: '', email: '' });
  const [issuing, setIssuing] = useState(false);
  const [issuedResult, setIssuedResult] = useState<{ email: string; temp_password: string } | null>(null);
  const [copied, setCopied] = useState(false);

  const loadHubs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.hubsApi.list();
      setHubs(data);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(axiosErr.response?.data?.detail || axiosErr.message || 'Failed to load regional hubs.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    api.hubsApi.list()
      .then((data) => {
        if (!ignore) {
          setHubs(data);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!ignore) {
          const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
          setError(axiosErr.response?.data?.detail || axiosErr.message || 'Failed to load regional hubs.');
          setLoading(false);
        }
      });
    return () => {
      ignore = true;
    };
  }, []);

  const handleCreateHub = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newHub.id || !newHub.name || !newHub.region) return;
    setCreating(true);
    try {
      await api.hubsApi.create(newHub);
      setAddModalOpen(false);
      setNewHub({ id: '', name: '', region: '' });
      await loadHubs();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
      alert(axiosErr.response?.data?.detail || 'Failed to create regional hub.');
    } finally {
      setCreating(false);
    }
  };

  const handleUpdateHub = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editHub) return;
    setUpdating(true);
    try {
      await api.hubsApi.update(editHub.id, { name: editHub.name, region: editHub.region });
      setEditHub(null);
      await loadHubs();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
      alert(axiosErr.response?.data?.detail || 'Failed to update regional hub.');
    } finally {
      setUpdating(false);
    }
  };

  const handleExecuteAction = async () => {
    if (!confirmAction) return;
    setActionLoading(true);
    try {
      if (confirmAction.type === 'suspend') {
        await api.hubsApi.suspend(confirmAction.hub.id);
      } else if (confirmAction.type === 'reactivate') {
        await api.hubsApi.reactivate(confirmAction.hub.id);
      } else if (confirmAction.type === 'delete') {
        await api.hubsApi.delete(confirmAction.hub.id);
      }
      setConfirmAction(null);
      await loadHubs();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
      alert(axiosErr.response?.data?.detail || 'Operation failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleIssueAdmin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!issueModalHub || !issueForm.name || !issueForm.email) return;
    setIssuing(true);
    try {
      const res = await api.hubsApi.issueAdmin(issueModalHub.id, issueForm);
      setIssuedResult({ email: issueForm.email, temp_password: res.temp_password });
      setIssueForm({ name: '', email: '' });
      await loadHubs();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
      alert(axiosErr.response?.data?.detail || 'Failed to issue admin credentials.');
    } finally {
      setIssuing(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div className="max-w-[1400px] mx-auto w-full pb-10 space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-xs">
        <div className="flex items-center gap-3.5">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-blue-600 to-cyan-500 text-white flex items-center justify-center shadow-md">
            <Network className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900">Regional Hubs</h1>
            <p className="text-xs text-slate-500 font-medium">Global governance of jurisdictional multi-hospital federated hubs</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={loadHubs}
            disabled={loading}
            className="flex items-center gap-2 text-slate-600 hover:text-slate-900 rounded-xl"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </Button>
          <Button
            onClick={() => setAddModalOpen(true)}
            size="sm"
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl shadow-xs"
          >
            <Plus className="w-4 h-4" />
            <span>Add Regional Hub</span>
          </Button>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-between text-sm text-rose-700">
          <span>{error}</span>
          <Button variant="outline" size="sm" onClick={loadHubs} className="border-rose-300 text-rose-700">
            Retry
          </Button>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse bg-white border-slate-200 p-6 rounded-2xl h-52">
              <div className="h-6 bg-slate-100 rounded-md w-1/2 mb-4" />
              <div className="h-4 bg-slate-100 rounded-md w-3/4 mb-3" />
              <div className="h-4 bg-slate-100 rounded-md w-1/3" />
            </Card>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && hubs.length === 0 && (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center max-w-lg mx-auto">
          <div className="w-14 h-14 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-4">
            <Network className="w-7 h-7" />
          </div>
          <h3 className="text-base font-bold text-slate-900 mb-1">No Regional Hubs Provisioned</h3>
          <p className="text-xs text-slate-500 mb-6 leading-relaxed">
            Federated learning requires regional hubs to aggregate hospital weights via SMPC. Create your first hub to begin.
          </p>
          <Button onClick={() => setAddModalOpen(true)} className="bg-blue-600 text-white rounded-xl">
            <Plus className="w-4 h-4 mr-2" />
            <span>Create First Regional Hub</span>
          </Button>
        </div>
      )}

      {/* Hub Cards Grid */}
      {!loading && !error && hubs.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {hubs.map((hub) => (
            <Card
              key={hub.id}
              className="bg-white border-slate-200/90 rounded-2xl shadow-xs hover:shadow-md transition-shadow flex flex-col justify-between overflow-hidden"
            >
              <CardContent className="p-6">
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div>
                    <h3 className="text-base font-bold text-slate-900 tracking-tight">{hub.name}</h3>
                    <p className="font-mono text-[11px] text-slate-500 mt-0.5">ID: {hub.id}</p>
                  </div>
                  <Badge
                    variant="outline"
                    className={`font-semibold capitalize text-xs ${
                      hub.status === 'active'
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : 'bg-amber-50 text-amber-700 border-amber-200'
                    }`}
                  >
                    {hub.status}
                  </Badge>
                </div>

                <div className="text-xs text-slate-600 mb-5 flex items-center gap-1.5 font-medium">
                  <span className="text-slate-400">Jurisdiction / Region:</span>
                  <span className="font-semibold text-slate-800">{hub.region}</span>
                </div>

                <div className="grid grid-cols-2 gap-3 p-3 rounded-xl bg-slate-50 border border-slate-200/80 mb-5">
                  <div className="flex items-center gap-2.5">
                    <Hospital className="w-4 h-4 text-blue-600" />
                    <div>
                      <p className="text-[10px] text-slate-500 font-semibold uppercase">Hospitals</p>
                      <p className="text-sm font-bold text-slate-900">{hub.hospitalCount}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2.5">
                    <Users className="w-4 h-4 text-cyan-600" />
                    <div>
                      <p className="text-[10px] text-slate-500 font-semibold uppercase">Regional Admins</p>
                      <p className="text-sm font-bold text-slate-900">{hub.adminCount}</p>
                    </div>
                  </div>
                </div>

                {/* Card Actions */}
                <div className="flex flex-wrap items-center gap-2 pt-3 border-t border-slate-100">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={hub.status !== 'active'}
                    onClick={() => {
                      setIssueModalHub(hub);
                      setIssuedResult(null);
                    }}
                    className="text-xs flex items-center gap-1.5 rounded-lg text-blue-600 border-blue-200 hover:bg-blue-50"
                  >
                    <KeyRound className="w-3.5 h-3.5" />
                    <span>Issue Admin</span>
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setEditHub(hub)}
                    className="text-xs flex items-center gap-1.5 rounded-lg text-slate-700 hover:bg-slate-50"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                    <span>Edit</span>
                  </Button>

                  {hub.status === 'active' ? (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setConfirmAction({ type: 'suspend', hub })}
                      className="text-xs flex items-center gap-1.5 rounded-lg text-amber-700 border-amber-200 hover:bg-amber-50"
                    >
                      <Ban className="w-3.5 h-3.5" />
                      <span>Suspend</span>
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setConfirmAction({ type: 'reactivate', hub })}
                      className="text-xs flex items-center gap-1.5 rounded-lg text-emerald-700 border-emerald-200 hover:bg-emerald-50"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Reactivate</span>
                    </Button>
                  )}

                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setConfirmAction({ type: 'delete', hub })}
                    className="text-xs flex items-center gap-1.5 rounded-lg text-rose-600 border-rose-200 hover:bg-rose-50 ml-auto"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Delete</span>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Add Hub Modal */}
      {addModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-md w-full p-6 text-slate-900">
            <h3 className="text-base font-bold text-slate-900 mb-1">Create Regional Hub</h3>
            <p className="text-xs text-slate-500 mb-4">Add a new federated aggregation jurisdiction.</p>
            <form onSubmit={handleCreateHub} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Hub Identifier (e.g. hub-east)</label>
                <Input
                  placeholder="hub-east"
                  value={newHub.id}
                  onChange={(e) => setNewHub({ ...newHub, id: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Hub Name</label>
                <Input
                  placeholder="Northeast Regional Alliance"
                  value={newHub.name}
                  onChange={(e) => setNewHub({ ...newHub, name: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Jurisdiction / Region</label>
                <Input
                  placeholder="US-East"
                  value={newHub.region}
                  onChange={(e) => setNewHub({ ...newHub, region: e.target.value })}
                  required
                />
              </div>
              <div className="flex items-center justify-end gap-3 pt-3">
                <Button type="button" variant="outline" onClick={() => setAddModalOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={creating} className="bg-blue-600 text-white">
                  {creating ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                  <span>Create Hub</span>
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Hub Modal */}
      {editHub && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-md w-full p-6 text-slate-900">
            <h3 className="text-base font-bold text-slate-900 mb-1">Edit Regional Hub</h3>
            <p className="text-xs text-slate-500 mb-4">Update hub details for {editHub.id}.</p>
            <form onSubmit={handleUpdateHub} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Hub Name</label>
                <Input
                  value={editHub.name}
                  onChange={(e) => setEditHub({ ...editHub, name: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Jurisdiction / Region</label>
                <Input
                  value={editHub.region}
                  onChange={(e) => setEditHub({ ...editHub, region: e.target.value })}
                  required
                />
              </div>
              <div className="flex items-center justify-end gap-3 pt-3">
                <Button type="button" variant="outline" onClick={() => setEditHub(null)}>
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

      {/* Confirm Action Dialog (Suspend / Reactivate / Delete) */}
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
                  {confirmAction.type} Hub: {confirmAction.hub.name}
                </h3>
                <p className="text-xs text-slate-500 font-mono">ID: {confirmAction.hub.id}</p>
              </div>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed mb-6">
              {confirmAction.type === 'suspend' && (
                <>
                  Suspending this regional hub will <strong>immediately revoke all active access tokens</strong> for its regional
                  admins and dependent hospitals. Dependent hospitals will also be paused from participating in future FL rounds.
                </>
              )}
              {confirmAction.type === 'reactivate' && (
                <>
                  Reactivating will restore administrative access for regional hub personnel.
                </>
              )}
              {confirmAction.type === 'delete' && (
                <>
                  Deleting this regional hub is <strong>permanent</strong>. All dependent regional admin accounts will be deleted, and
                  associated hospitals will be severed from this hub.
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

      {/* Issue Admin Credentials Modal */}
      {issueModalHub && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-md w-full p-6 text-slate-900">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-600 flex items-center justify-center">
                <KeyRound className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">Issue Hub Admin Credentials</h3>
                <p className="text-xs text-slate-500">For {issueModalHub.name} ({issueModalHub.id})</p>
              </div>
            </div>

            {!issuedResult ? (
              <form onSubmit={handleIssueAdmin} className="space-y-4">
                <p className="text-xs text-slate-600 leading-relaxed bg-slate-50 p-3 rounded-xl border border-slate-200">
                  Generates high-entropy one-time credentials. The regional administrator will be forced to set a new password on their first login.
                </p>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Administrator Full Name</label>
                  <Input
                    placeholder="e.g. Dr. Jane Smith"
                    value={issueForm.name}
                    onChange={(e) => setIssueForm({ ...issueForm, name: e.target.value })}
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Administrator Email Address</label>
                  <Input
                    type="email"
                    placeholder="e.g. j.smith@hub-east.trustfed.ai"
                    value={issueForm.email}
                    onChange={(e) => setIssueForm({ ...issueForm, email: e.target.value })}
                    required
                  />
                </div>
                <div className="flex items-center justify-end gap-3 pt-3">
                  <Button type="button" variant="outline" onClick={() => setIssueModalHub(null)}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={issuing} className="bg-blue-600 text-white">
                    {issuing ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                    <span>Generate Credentials</span>
                  </Button>
                </div>
              </form>
            ) : (
              <div className="space-y-4">
                <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs">
                  <strong>Credentials Issued Successfully!</strong> The regional administrator has been provisioned.
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
                  ⚠️ This temporary password is never displayed again. Store it securely and instruct the admin to log in and set their personal password.
                </p>

                <div className="flex justify-end pt-2">
                  <Button
                    onClick={() => {
                      setIssueModalHub(null);
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
    </div>
  );
}
