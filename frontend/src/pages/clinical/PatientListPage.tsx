import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users, Search, UserPlus, ArrowRight, Calendar,
  ShieldCheck, Loader2, AlertCircle, FileText
} from 'lucide-react';
import { clinicalApi } from '@/services/api';
import type { ClinicalPatient } from '@/types';
import { useAuthStore } from '@/store/authStore';

export default function PatientListPage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [patients, setPatients] = useState<ClinicalPatient[]>([]);
  const [search, setSearch] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPatients = async (query?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await clinicalApi.listPatients({ search: query });
      setPatients(res.items);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load patients.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPatients();
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchPatients(search.trim());
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      {/* Top Header */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-blue-600 font-semibold text-xs uppercase tracking-wider mb-1">
            <Users size={16} />
            Hospital Patient Directory
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Patients & Encounters
          </h1>
          <p className="text-slate-500 text-sm mt-0.5">
            Patients registered at Hospital Node <strong>{user?.hospitalId || 'Local Node'}</strong>. Names and contacts decrypted in-hospital.
          </p>
        </div>

        <button
          onClick={() => navigate('/patients/new')}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 shadow-md shadow-blue-500/20 transition-all self-start sm:self-auto"
        >
          <UserPlus size={15} />
          Register New Patient
        </button>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <form onSubmit={handleSearchSubmit} className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search patient by name or MRN (e.g. PT-3A8B, John...)"
            className="w-full pl-9 pr-24 py-2 rounded-xl text-sm border border-slate-200 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
          />
          <button
            type="submit"
            className="absolute right-1.5 top-1.5 px-3 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-all"
          >
            Search
          </button>
        </form>

        <div className="flex items-center gap-2 text-xs text-slate-500 bg-slate-50 px-3 py-2 rounded-xl border border-slate-200 shrink-0">
          <ShieldCheck size={14} className="text-emerald-600" />
          <span>Local Node Encrypted Scope</span>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5 text-rose-600" />
          <div>
            <p className="font-semibold text-sm">Error Loading Directory</p>
            <p className="text-xs mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Directory Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-16 text-slate-400 space-y-3">
            <Loader2 className="w-7 h-7 animate-spin text-blue-600" />
            <p className="text-xs font-medium">Decrypting and loading patient records...</p>
          </div>
        ) : patients.length === 0 ? (
          <div className="text-center py-16 px-4">
            <div className="w-12 h-12 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center mx-auto mb-3">
              <Users size={24} />
            </div>
            <h3 className="text-sm font-semibold text-slate-900">No patients found</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              {search ? `No patient matching "${search}". Try searching by another name or MRN.` : 'Register your first patient and run an AI differential diagnosis.'}
            </p>
            {!search && (
              <button
                onClick={() => navigate('/patients/new')}
                className="mt-4 inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold text-blue-600 bg-blue-50 hover:bg-blue-100 transition-all"
              >
                <UserPlus size={14} /> Register Patient
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/75 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="py-3.5 px-4">Patient MRN</th>
                  <th className="py-3.5 px-4">Patient Name</th>
                  <th className="py-3.5 px-4">Age / Sex</th>
                  <th className="py-3.5 px-4">Contact</th>
                  <th className="py-3.5 px-4 text-center">Encounters</th>
                  <th className="py-3.5 px-4">Last Visit</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {patients.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-3 px-4 font-mono font-semibold text-blue-600">
                      {p.patientIdentifier}
                    </td>
                    <td className="py-3 px-4 font-semibold text-slate-900">
                      {p.name || <span className="text-slate-400 italic">Unspecified</span>}
                    </td>
                    <td className="py-3 px-4">
                      {p.age} yrs · <span className="font-medium text-slate-600">{p.sexLabel}</span>
                    </td>
                    <td className="py-3 px-4 text-slate-500">
                      {p.contact || <span className="text-slate-400 italic">None</span>}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-700">
                        {p.encounterCount || 0}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-500">
                      {p.lastEncounterDate ? (
                        <div className="flex items-center gap-1.5">
                          <Calendar size={13} className="text-slate-400 shrink-0" />
                          <span>{new Date(p.lastEncounterDate).toLocaleDateString()}</span>
                        </div>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right space-x-1.5">
                      {p.lastEncounterId && (
                        <button
                          onClick={() => navigate(`/encounters/${p.lastEncounterId}`)}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-slate-600 hover:text-blue-600 hover:bg-blue-50 font-medium transition-all"
                          title="View Latest Encounter"
                        >
                          <FileText size={13} />
                          <span>Encounter</span>
                        </button>
                      )}
                      <button
                        onClick={() => navigate(`/patients/${p.id}`)}
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-blue-600 hover:bg-blue-50 font-semibold transition-all"
                      >
                        <span>History</span>
                        <ArrowRight size={13} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
