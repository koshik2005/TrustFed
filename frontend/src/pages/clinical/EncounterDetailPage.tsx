import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Stethoscope, CheckCircle2, Clock, AlertCircle, ArrowLeft,
  Activity, Thermometer, Heart, User, ShieldCheck,
  Check, Loader2, Sparkles, Lock, AlertTriangle
} from 'lucide-react';
import { clinicalApi } from '@/services/api';
import type { ClinicalEncounter } from '@/types';
import { useAuthStore } from '@/store/authStore';
import { cn } from '@/utils';

const COMMON_DIAGNOSES = [
  { code: 'DENGUE', name: 'Dengue Fever' },
  { code: 'TYPHOID', name: 'Typhoid Enteric Fever' },
  { code: 'VIRAL_FEVER', name: 'Acute Viral Pyrexia' },
  { code: 'FLU', name: 'Influenza (Seasonal Flu)' },
  { code: 'COLD', name: 'Common Cold (Viral Rhinitis)' },
  { code: 'UTI', name: 'Urinary Tract Infection' },
  { code: 'CARDIAC_CAD', name: 'Coronary Artery Disease (CAD)' },
];

export default function EncounterDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [encounter, setEncounter] = useState<ClinicalEncounter | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Doctor Confirmation Form
  const [diagnosisChoice, setDiagnosisChoice] = useState('');
  const [customDiagnosis, setCustomDiagnosis] = useState('');
  const [cause, setCause] = useState('');
  const [treatment, setTreatment] = useState('');
  const [isConfirming, setIsConfirming] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [confirmSuccess, setConfirmSuccess] = useState(false);

  const isDoctor = user?.role === 'doctor' || user?.role === 'global_admin';
  const isStaffOnly = user?.role === 'hospital_staff';

  const fetchEncounter = async () => {
    if (!id) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await clinicalApi.getEncounterDetail(Number(id));
      setEncounter(data);

      // Pre-fill form if encounter already has top1 prediction or existing diagnosis
      if (data.doctorConfirmedDiagnosis) {
        setDiagnosisChoice(data.doctorConfirmedDiagnosis);
        setCause(data.cause || '');
        setTreatment(data.treatment || '');
      } else if (data.predictedTop3 && data.predictedTop3.length > 0) {
        setDiagnosisChoice(data.predictedTop3[0].disease);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load encounter.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchEncounter();
  }, [id]);

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!encounter) return;
    setConfirmError(null);

    const finalDiagnosis = diagnosisChoice === 'OTHER' ? customDiagnosis.trim() : diagnosisChoice.trim();
    if (!finalDiagnosis) {
      setConfirmError('Please select or specify a confirmed diagnosis.');
      return;
    }
    if (!cause.trim()) {
      setConfirmError('Clinical etiology / cause is required.');
      return;
    }
    if (!treatment.trim()) {
      setConfirmError('Prescribed treatment and remedies are required.');
      return;
    }

    setIsConfirming(true);
    try {
      const updated = await clinicalApi.confirmEncounter(encounter.id, {
        confirmed_diagnosis: finalDiagnosis,
        cause: cause.trim(),
        treatment: treatment.trim(),
      });
      setEncounter(updated);
      setConfirmSuccess(true);
      setTimeout(() => setConfirmSuccess(false), 4000);
    } catch (err: any) {
      setConfirmError(err.response?.data?.detail || err.message || 'Failed to confirm encounter.');
    } finally {
      setIsConfirming(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-3">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        <p className="text-xs text-slate-500 font-medium">Loading clinical assessment details...</p>
      </div>
    );
  }

  if (error || !encounter) {
    return (
      <div className="max-w-3xl mx-auto p-6 bg-white rounded-2xl border border-slate-200 space-y-4">
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5 text-rose-600" />
          <div>
            <p className="font-semibold text-sm">Cannot View Encounter</p>
            <p className="text-xs mt-0.5">{error || 'Encounter record not found.'}</p>
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

  const p = encounter.patient;
  const vitals = encounter.vitals || {};
  const isConfirmed = encounter.status === 'confirmed' || encounter.doctorConfirmedDiagnosis !== null;

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-12">
      {/* Navigation & Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/patients')}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white px-3 py-1.5 rounded-xl border border-slate-200/80 shadow-2xs transition-all"
        >
          <ArrowLeft size={14} />
          Back to Directory
        </button>

        <div className="flex items-center gap-2">
          {isConfirmed ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
              <CheckCircle2 size={13} className="text-emerald-600" />
              Doctor Confirmed · Trainable
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
              <Clock size={13} className="text-amber-600" />
              Awaiting Doctor Confirmation
            </span>
          )}
        </div>
      </div>

      {/* Patient Banner */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-lg shrink-0">
            <User size={24} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-slate-900">
                {p?.name || 'De-Identified Patient'}
              </h1>
              <span className="font-mono text-xs px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 font-semibold">
                {p?.patientIdentifier}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              {p?.age} yrs · {p?.sexLabel}
              {p?.weight && ` · ${p.weight} kg`}
              {p?.height && ` · ${p.height} cm`}
              {p?.contact && ` · ${p.contact}`}
            </p>
          </div>
        </div>

        <div className="text-right text-xs text-slate-400">
          <p>Encounter: <span className="font-mono font-semibold text-slate-600">{encounter.encounterIdentifier}</span></p>
          <p className="mt-0.5">Recorded: {encounter.createdAt ? new Date(encounter.createdAt).toLocaleString() : 'Recent'}</p>
        </div>
      </div>

      {/* Critical Red-Flag Safety Override Banner */}
      {(encounter.hasCriticalRedFlag || (encounter.redFlags && encounter.redFlags.length > 0)) && (
        <div className="bg-rose-50 border-2 border-rose-500 rounded-2xl p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-rose-900 font-extrabold text-sm tracking-wide">
              <AlertTriangle className="w-5 h-5 text-rose-600 animate-pulse" />
              <span>CRITICAL CLINICAL RED-FLAG SAFETY OVERRIDE</span>
              <span className="text-[10px] font-semibold text-amber-900 bg-amber-100 border border-amber-300 px-2 py-0.5 rounded-full">
                Pending Physician Review
              </span>
            </div>
            <span className="text-[10px] uppercase font-extrabold px-2.5 py-0.5 rounded-full bg-rose-600 text-white tracking-wider">
              Immediate Escalation Stat
            </span>
          </div>
          <p className="text-[11px] text-rose-700 italic">
            Deterministic safety heuristics; all physiological cutoffs are pending formal hospital physician review and clinical trial validation.
          </p>
          <div className="space-y-2">
            {encounter.redFlags?.map((rf) => (
              <div key={rf.ruleId} className="bg-white/95 border border-rose-200 rounded-xl p-3.5 space-y-1.5 shadow-2xs">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-rose-950">{rf.title}</span>
                  <span className="text-[10px] font-mono font-semibold text-rose-700 bg-rose-100 px-1.5 py-0.5 rounded">{rf.ruleId}</span>
                </div>
                <p className="text-xs text-rose-800 leading-relaxed">{rf.description}</p>
                <div className="text-xs font-semibold text-rose-900 pt-1 border-t border-rose-100 mt-1">
                  Immediate Action: <span className="font-medium text-rose-950">{rf.escalationAction || rf.action}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Adaptive Questioning Guidance */}
      {encounter.adaptiveQuestion && (
        <div className="bg-indigo-50/90 border border-indigo-200 rounded-2xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-2xs">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center shrink-0 mt-0.5">
              <Sparkles size={16} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-indigo-950">Diagnostic Refinement Recommendation</span>
                <span className="text-[10px] font-semibold text-indigo-700 bg-indigo-100 px-2 py-0.5 rounded-full">
                  Top-1 Confidence &lt; 65%
                </span>
              </div>
              <p className="text-xs text-indigo-800 mt-0.5">{encounter.adaptiveQuestion.reason}</p>
            </div>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-bold bg-white text-indigo-700 border border-indigo-200 shadow-2xs shrink-0">
            <span>{encounter.adaptiveQuestion.uiPrompt || encounter.adaptiveQuestion.prompt || `Add ${encounter.adaptiveQuestion.label} to improve this result`}</span>
          </div>
        </div>
      )}

      {/* Main Grid: Clinical Evidence + Differential Diagnosis */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Presenting Symptoms & Vitals */}
        <div className="lg:col-span-2 space-y-6">
          {/* Symptoms Card */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center justify-between">
              <span>Presenting Symptoms & Clinical History</span>
              <span className="text-xs font-semibold text-blue-600 normal-case bg-blue-50 px-2.5 py-0.5 rounded-md">
                Active for {encounter.symptomDurationDays} day{encounter.symptomDurationDays > 1 ? 's' : ''}
              </span>
            </h2>

            <div className="flex flex-wrap gap-2">
              {encounter.symptoms.map((s) => (
                <span
                  key={s}
                  className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-100 text-slate-800 border border-slate-200/60 capitalize"
                >
                  {s.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          </div>

          {/* Vitals & Labs Grid */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Objective Vitals & Laboratory Findings
            </h2>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70">
                <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
                  <Thermometer size={14} className="text-amber-500" /> Temperature
                </div>
                <div className="text-base font-bold text-slate-900 mt-1">
                  {vitals.temp_c ? `${vitals.temp_c} °C` : '—'}
                </div>
                {vitals.temp_c && vitals.temp_c >= 38.0 && (
                  <span className="text-[10px] font-bold text-rose-600">Pyrexia / Fever</span>
                )}
              </div>

              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70">
                <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
                  <Activity size={14} className="text-rose-500" /> Blood Pressure
                </div>
                <div className="text-base font-bold text-slate-900 mt-1">
                  {vitals.bp_sys ? `${vitals.bp_sys} / ${vitals.bp_dia}` : '—'}
                </div>
                {vitals.bp_sys && vitals.bp_sys >= 140 && (
                  <span className="text-[10px] font-bold text-amber-600">Elevated</span>
                )}
              </div>

              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70">
                <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
                  <Heart size={14} className="text-red-500" /> Heart Rate
                </div>
                <div className="text-base font-bold text-slate-900 mt-1">
                  {vitals.hr ? `${vitals.hr} bpm` : '—'}
                </div>
                {vitals.hr && vitals.hr > 100 && (
                  <span className="text-[10px] font-bold text-rose-600">Tachycardia</span>
                )}
              </div>

              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70">
                <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
                  <Activity size={14} className="text-blue-500" /> SpO2 Saturation
                </div>
                <div className="text-base font-bold text-slate-900 mt-1">
                  {vitals.spo2 ? `${vitals.spo2} %` : '—'}
                </div>
                {vitals.spo2 && vitals.spo2 < 95 && (
                  <span className="text-[10px] font-bold text-rose-600">Hypoxemia</span>
                )}
              </div>
            </div>

            {/* Additional details: ECG & Labs */}
            <div className="pt-2 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70">
                <span className="text-slate-400 font-medium block mb-1">Structured ECG Assessment:</span>
                <span className="font-semibold text-slate-800 capitalize">
                  {encounter.structuredEcgFinding || 'Normal Sinus Rhythm'}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/70">
                <span className="text-slate-400 font-medium block mb-1">Laboratory Markers:</span>
                <span className="font-semibold text-slate-800">
                  {encounter.optionalLabs && Object.keys(encounter.optionalLabs).length > 0
                    ? Object.entries(encounter.optionalLabs)
                        .map(([k, v]) => `${k.toUpperCase()}: ${v}`)
                        .join(' · ')
                    : 'Standard Baseline / Pending'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Col: Differential Diagnosis Top-3 probabilities */}
        <div className="space-y-6">
          <div className="bg-gradient-to-br from-white to-blue-50/40 rounded-2xl p-6 border border-blue-200/60 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Sparkles size={16} className="text-blue-600" />
                Differential AI Diagnosis
              </h2>
              <span className="text-[10px] font-semibold text-slate-500 bg-white px-2 py-0.5 rounded border border-slate-200">
                Top-3
              </span>
            </div>

            <p className="text-xs text-slate-500">
              Multi-disease Bayesian inference evaluated across presenting phenotypes.
            </p>

            <div className="space-y-3 pt-1">
              {encounter.predictedTop3 && encounter.predictedTop3.length > 0 ? (
                encounter.predictedTop3.map((pred, idx) => {
                  const pct = Math.round(pred.probability * 100);
                  return (
                    <div
                      key={pred.disease}
                      className={cn(
                        "p-3 rounded-xl border transition-all",
                        idx === 0
                          ? "bg-white border-blue-300 shadow-xs"
                          : "bg-white/80 border-slate-200"
                      )}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                          {idx === 0 && <span className="w-2 h-2 rounded-full bg-blue-600" />}
                          {pred.disease}
                        </span>
                        <span className="text-xs font-bold text-blue-700">{pct}%</span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                        <div
                          className={cn(
                            "h-full rounded-full transition-all duration-500",
                            idx === 0 ? "bg-blue-600" : idx === 1 ? "bg-cyan-500" : "bg-slate-400"
                          )}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="text-xs text-slate-400 italic">No differential predictions generated.</div>
              )}
            </div>

            {/* Feature Contributions (SHAP Attributions) */}
            {encounter.explanations?.positiveContributions && encounter.explanations.positiveContributions.length > 0 && (
              <div className="pt-3 border-t border-blue-100 space-y-2">
                <span className="text-xs font-bold text-slate-800 block">
                  Top Feature Contributions (for {encounter.explanations.topCondition}):
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {encounter.explanations.positiveContributions.slice(0, 4).map((c, i) => (
                    <span key={i} className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-800 border border-emerald-200">
                      +{c.impact} {c.feature}
                    </span>
                  ))}
                  {encounter.explanations.negativeContributions?.slice(0, 2).map((c, i) => (
                    <span key={i} className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 border border-slate-200">
                      {c.impact} {c.feature}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Suggested Etiology & First-Line Remedies */}
            {encounter.suggestedClinicalGuidance && (
              <div className="pt-3 border-t border-blue-100 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-800">
                    Suggested Cause & Common Remedies
                  </span>
                  <span className="text-[10px] italic font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                    Suggested, clinician must verify
                  </span>
                </div>
                {encounter.suggestedClinicalGuidance.suggestedCause && (
                  <div className="text-xs text-slate-700 bg-white/90 p-2.5 rounded-xl border border-slate-200/80">
                    <strong className="text-slate-900 block mb-0.5">Etiology:</strong>
                    {encounter.suggestedClinicalGuidance.suggestedCause}
                  </div>
                )}
                {encounter.suggestedClinicalGuidance.commonRemedies && encounter.suggestedClinicalGuidance.commonRemedies.length > 0 && (
                  <div className="text-xs text-slate-700 bg-white/90 p-2.5 rounded-xl border border-slate-200/80">
                    <strong className="text-slate-900 block mb-1">Common First-Line Protocol:</strong>
                    <ul className="list-disc list-inside space-y-0.5 text-slate-600">
                      {encounter.suggestedClinicalGuidance.commonRemedies.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {!isConfirmed && !isStaffOnly && (
                  <button
                    type="button"
                    onClick={() => {
                      if (encounter.suggestedClinicalGuidance?.suggestedCause) setCause(encounter.suggestedClinicalGuidance.suggestedCause);
                      if (encounter.suggestedClinicalGuidance?.commonRemedies) setTreatment(encounter.suggestedClinicalGuidance.commonRemedies.join('; '));
                    }}
                    className="text-[11px] font-semibold text-blue-600 hover:text-blue-800 hover:underline flex items-center gap-1"
                  >
                    Copy suggested etiology & remedies to confirmation form ↓
                  </button>
                )}
              </div>
            )}

            {/* Mandatory Disclaimer */}
            <div className="p-3 rounded-xl bg-amber-50/80 border border-amber-200 text-[11px] text-amber-900 font-medium flex items-center gap-2">
              <AlertCircle size={15} className="text-amber-600 shrink-0" />
              <span>{encounter.disclaimer || 'Clinical decision support only, not a diagnosis.'}</span>
            </div>

            {/* Model Version & Fallback Indicator */}
            <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 text-[10px] text-slate-500 flex items-center justify-between">
              <span>Model version: <strong>{encounter.modelVersion || 'TF-GenDisease-v1.0'}</strong></span>
              {encounter.isFallback && (
                <span className="font-bold text-amber-700 bg-amber-100 px-2 py-0.5 rounded">Fallback heuristic active</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Doctor Confirmation & Treatment Section */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-6">
        <div className="border-b border-slate-100 pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Stethoscope className="w-5 h-5 text-blue-600" />
              Doctor Confirmation & Clinical Treatment Plan
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Attending physician confirmation marks record as verified and eligible for federated model training.
            </p>
          </div>

          {encounter.trainable ? (
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-emerald-600 text-white shadow-xs">
              <CheckCircle2 size={14} />
              TRAINABLE (Federated Consent)
            </div>
          ) : (
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-100 text-slate-600">
              <Lock size={13} />
              Unconfirmed · Untrainable
            </div>
          )}
        </div>

        {confirmSuccess && (
          <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <div>
              <p className="font-bold text-sm">Diagnosis Confirmed & Trainable</p>
              <p className="text-xs mt-0.5">This clinical record has been verified and added to the hospital's trainable federated dataset.</p>
            </div>
          </div>
        )}

        {confirmError && (
          <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
            <div className="text-xs">{confirmError}</div>
          </div>
        )}

        {isConfirmed ? (
          /* View Mode for Confirmed Record */
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-xs font-semibold text-slate-500 block mb-1">Confirmed Diagnosis:</span>
                <span className="text-base font-bold text-slate-900 text-blue-700">
                  {encounter.doctorConfirmedDiagnosis}
                </span>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-xs font-semibold text-slate-500 block mb-1">Attending Physician:</span>
                <span className="text-sm font-bold text-slate-900">
                  {encounter.confirmedByName || 'Attending Doctor'}
                </span>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-xs font-semibold text-slate-500 block mb-1">Confirmation Timestamp:</span>
                <span className="text-sm font-medium text-slate-700">
                  {encounter.confirmedAt ? new Date(encounter.confirmedAt).toLocaleString() : 'Recorded'}
                </span>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block">Clinical Etiology / Cause</span>
              <p className="text-xs text-slate-700 leading-relaxed whitespace-pre-wrap">{encounter.cause}</p>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block">Prescribed Treatment & Remedies</span>
              <p className="text-xs text-slate-700 leading-relaxed whitespace-pre-wrap">{encounter.treatment}</p>
            </div>
          </div>
        ) : isStaffOnly ? (
          /* Staff View Notice: Staff cannot confirm */
          <div className="p-6 rounded-2xl bg-amber-50/70 border border-amber-200 text-amber-900 space-y-3">
            <div className="flex items-center gap-2 font-bold text-sm text-amber-900">
              <Lock size={18} className="text-amber-700" />
              Doctor Confirmation Required
            </div>
            <p className="text-xs text-amber-800 leading-relaxed">
              You are logged in as <strong>Hospital Staff</strong>. In accordance with clinical governance rules,
              only attending doctors may confirm diagnoses and mark records trainable. This encounter is queued in the doctor's pending confirmation list.
            </p>
          </div>
        ) : isDoctor ? (
          /* Doctor Confirmation Form */
          <form onSubmit={handleConfirm} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Confirmed Diagnosis <span className="text-rose-500">*</span>
                </label>
                <select
                  value={diagnosisChoice}
                  onChange={(e) => setDiagnosisChoice(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl text-sm border border-slate-200 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500 font-medium"
                >
                  <option value="">Select Confirmed / Corrected Diagnosis...</option>
                  {encounter.predictedTop3?.map((p) => (
                    <option key={p.disease} value={p.disease}>
                      [Top Prediction] {p.disease} ({Math.round(p.probability * 100)}%)
                    </option>
                  ))}
                  <option disabled>──────────</option>
                  {COMMON_DIAGNOSES.map((d) => (
                    <option key={d.code} value={d.name}>
                      {d.name}
                    </option>
                  ))}
                  <option value="OTHER">Other / Custom Diagnosis</option>
                </select>
              </div>

              {diagnosisChoice === 'OTHER' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Specify Custom Diagnosis <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={customDiagnosis}
                    onChange={(e) => setCustomDiagnosis(e.target.value)}
                    placeholder="Enter clinical condition"
                    className="w-full px-3.5 py-2 rounded-xl text-sm border border-slate-200 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
                  />
                </div>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Clinical Etiology / Root Cause <span className="text-rose-500">*</span>
              </label>
              <textarea
                rows={2}
                value={cause}
                onChange={(e) => setCause(e.target.value)}
                placeholder="e.g. Probable Aedes aegypti vector exposure with secondary viremia and thrombocytopenia"
                className="w-full px-3.5 py-2 rounded-xl text-sm border border-slate-200 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Prescribed Treatment & Remedy <span className="text-rose-500">*</span>
              </label>
              <textarea
                rows={2}
                value={treatment}
                onChange={(e) => setTreatment(e.target.value)}
                placeholder="e.g. Strict oral rehydration therapy, paracetamol 650mg SOS, monitor platelet count daily, avoid NSAIDs."
                className="w-full px-3.5 py-2 rounded-xl text-sm border border-slate-200 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
                required
              />
            </div>

            <div className="flex items-center justify-between pt-2">
              <span className="text-xs text-slate-500">
                Confirming updates the patient encounter and marks this record trainable.
              </span>
              <button
                type="submit"
                disabled={isConfirming}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 shadow-md shadow-emerald-600/20 transition-all disabled:opacity-60"
              >
                {isConfirming ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Recording Confirmation...
                  </>
                ) : (
                  <>
                    <Check size={14} />
                    Confirm Diagnosis & Mark Trainable
                  </>
                )}
              </button>
            </div>
          </form>
        ) : null}
      </div>
    </div>
  );
}
