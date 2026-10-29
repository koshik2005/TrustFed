import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  User, ArrowLeft, Plus, Calendar, Clock,
  CheckCircle2, ArrowRight, Loader2, AlertCircle, FileText
} from 'lucide-react';
import { clinicalApi } from '@/services/api';
import type { ClinicalPatient, ClinicalEncounter } from '@/types';
import { useAuthStore } from '@/store/authStore';

export default function PatientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [patient, setPatient] = useState<ClinicalPatient | null>(null);
  const [encounters, setEncounters] = useState<ClinicalEncounter[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDetail = async () => {
    if (!id) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await clinicalApi.getPatientDetail(Number(id));
      setPatient(res.patient);
      setEncounters(res.encounters);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load patient history.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [id]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-3">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        <p className="text-xs text-slate-500 font-medium">Loading patient record...</p>
      </div>
    );
  }

  if (error || !patient) {
    return (
      <div className="max-w-3xl mx-auto p-6 bg-white rounded-2xl border border-slate-200 space-y-4">
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5 text-rose-600" />
          <div>
            <p className="font-semibold text-sm">Cannot View Patient</p>
            <p className="text-xs mt-0.5">{error || 'Patient record not found.'}</p>
          </div>
        </div>
        <button
          onClick={() => navigate('/patients')}
          className="inline-flex items-center gap-2 text-xs font-semibold text-blue-600 hover:underline"
        >
          <ArrowLeft size={14} /> Back to Patient Directory
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-12">
      {/* Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/patients')}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white px-3 py-1.5 rounded-xl border border-slate-200/80 shadow-2xs transition-all"
        >
          <ArrowLeft size={14} />
          Back to Directory
        </button>

        <button
          onClick={() => navigate('/patients/new')}
          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 shadow-xs transition-all"
        >
          <Plus size={14} />
          Log New Encounter
        </button>
      </div>

      {/* Patient Profile Card */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-xl shrink-0">
            <User size={28} />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-bold text-slate-900">
                {patient.name || 'Anonymous Patient'}
              </h1>
              <span className="font-mono text-xs px-2.5 py-0.5 rounded-md bg-blue-50 text-blue-700 font-bold border border-blue-200/60">
                {patient.patientIdentifier}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Age: <strong className="text-slate-700">{patient.age} yrs</strong> · Sex: <strong className="text-slate-700">{patient.sexLabel}</strong>
              {patient.weight && ` · Weight: ${patient.weight} kg`}
              {patient.height && ` · Height: ${patient.height} cm`}
            </p>
            {patient.contact && (
              <p className="text-xs text-slate-400 mt-0.5">
                Contact: <span className="font-medium text-slate-600">{patient.contact}</span>
              </p>
            )}
          </div>
        </div>

        <div className="text-right text-xs text-slate-500">
          <p>Total Encounters: <strong className="text-slate-900 font-bold">{encounters.length}</strong></p>
          <p className="mt-0.5">Registered: {patient.createdAt ? new Date(patient.createdAt).toLocaleDateString() : 'Recent'}</p>
        </div>
      </div>

      {/* Encounter History Section */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden space-y-0">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <FileText size={16} className="text-blue-600" />
            Clinical Encounter History
          </h2>
          <span className="text-xs text-slate-400 font-medium">Chronological</span>
        </div>

        {encounters.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-400">
            No clinical encounters recorded yet for this patient.
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {encounters.map((enc) => {
              const isConfirmed = enc.status === 'confirmed' || enc.doctorConfirmedDiagnosis !== null;
              return (
                <div
                  key={enc.id}
                  className="p-5 hover:bg-slate-50/60 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4"
                >
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center gap-2.5">
                      <span className="font-mono text-xs font-semibold text-blue-600">
                        {enc.encounterIdentifier}
                      </span>
                      <span className="text-xs text-slate-400 flex items-center gap-1">
                        <Calendar size={12} />
                        {enc.createdAt ? new Date(enc.createdAt).toLocaleString() : 'Recent'}
                      </span>
                      {isConfirmed ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <CheckCircle2 size={11} /> {enc.doctorConfirmedDiagnosis}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                          <Clock size={11} /> Awaiting Confirmation
                        </span>
                      )}
                    </div>

                    <div className="flex flex-wrap gap-1.5 pt-1">
                      <span className="text-xs text-slate-400 font-medium self-center mr-1">Symptoms:</span>
                      {enc.symptoms.map((s) => (
                        <span
                          key={s}
                          className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-100 text-slate-700 capitalize"
                        >
                          {s.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>

                    {isConfirmed && enc.treatment && (
                      <p className="text-xs text-slate-600 pt-0.5 line-clamp-1">
                        <strong>Rx:</strong> {enc.treatment}
                      </p>
                    )}
                  </div>

                  <button
                    onClick={() => navigate(`/encounters/${enc.id}`)}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold text-blue-600 hover:bg-blue-50 transition-all self-start md:self-auto shrink-0"
                  >
                    <span>View Assessment</span>
                    <ArrowRight size={13} />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
