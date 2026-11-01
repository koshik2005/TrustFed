import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UserPlus, Search, X, AlertCircle, Heart, Thermometer,
  Activity, ArrowRight, ShieldCheck, CheckCircle2, Loader2, Sparkles
} from 'lucide-react';
import { clinicalApi } from '@/services/api';
import { useAuthStore } from '@/store/authStore';
import type { ClinicalSymptom, ClinicalVitals } from '@/types';
import { cn } from '@/utils';

export default function NewPatientEncounterPage() {
  const navigate = useNavigate();
  const { appMode } = useAuthStore();

  // Symptoms taxonomy from server
  const [availableSymptoms, setAvailableSymptoms] = useState<ClinicalSymptom[]>([]);
  const [symptomSearch, setSymptomSearch] = useState('');
  const [isLoadingSymptoms, setIsLoadingSymptoms] = useState(true);

  // Form State
  const [name, setName] = useState('');
  const [contact, setContact] = useState('');
  const [age, setAge] = useState<number | ''>('');
  const [sex, setSex] = useState<number>(0); // 0=Female, 1=Male, 2=Other
  const [weight, setWeight] = useState<number | ''>('');
  const [height, setHeight] = useState<number | ''>('');

  const [selectedSymptoms, setSelectedSymptoms] = useState<string[]>([]);
  const [durationDays, setDurationDays] = useState<number>(2);

  // Vitals State
  const [tempC, setTempC] = useState<number | ''>('');
  const [bpSys, setBpSys] = useState<number | ''>('');
  const [bpDia, setBpDia] = useState<number | ''>('');
  const [hr, setHr] = useState<number | ''>('');
  const [spo2, setSpo2] = useState<number | ''>('');
  const [respRate, setRespRate] = useState<number | ''>('');
  const [bloodSugar, setBloodSugar] = useState<number | ''>('');
  const [ecgFinding, setEcgFinding] = useState<string>('normal');

  // Labs State
  const [platelets, setPlatelets] = useState<number | ''>('');
  const [wbc, setWbc] = useState<number | ''>('');

  // Submission & Validation State
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [globalError, setGlobalError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchSymptoms() {
      try {
        const data = await clinicalApi.getSymptoms();
        setAvailableSymptoms(data.symptoms);
      } catch {
        // Fallback standard symptoms
        setAvailableSymptoms([
          { code: 'fever', label: 'Fever / Pyrexia' },
          { code: 'cough', label: 'Cough' },
          { code: 'sore_throat', label: 'Sore Throat / Pharyngitis' },
          { code: 'runny_nose', label: 'Rhinorrhea / Runny Nose' },
          { code: 'headache', label: 'Headache' },
          { code: 'vomiting', label: 'Nausea & Vomiting' },
          { code: 'diarrhea', label: 'Diarrhea' },
          { code: 'chest_pain', label: 'Chest Pain' },
          { code: 'breathlessness', label: 'Dyspnea / Breathlessness' },
          { code: 'rash', label: 'Rash' },
          { code: 'joint_pain', label: 'Joint Pain / Arthralgia' },
          { code: 'fatigue', label: 'Fatigue & Malaise' },
          { code: 'body_ache', label: 'Body Ache / Myalgia' },
          { code: 'abdominal_pain', label: 'Abdominal Pain' },
          { code: 'burning_urination', label: 'Burning Urination / Dysuria' },
        ]);
      } finally {
        setIsLoadingSymptoms(false);
      }
    }
    fetchSymptoms();
  }, []);

  const toggleSymptom = (code: string) => {
    setSelectedSymptoms((prev) =>
      prev.includes(code) ? prev.filter((s) => s !== code) : [...prev, code]
    );
    if (errors.symptoms) {
      setErrors((prev) => {
        const copy = { ...prev };
        delete copy.symptoms;
        return copy;
      });
    }
  };

  const filteredSymptoms = availableSymptoms.filter((s) =>
    s.label.toLowerCase().includes(symptomSearch.toLowerCase()) ||
    s.code.toLowerCase().includes(symptomSearch.toLowerCase())
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});
    setGlobalError(null);

    // Client-side quick check
    const localErrors: Record<string, string> = {};
    if (age === '' || Number(age) < 0 || Number(age) > 125) {
      localErrors.age = 'Age is required and must be between 0 and 125.';
    }
    if (selectedSymptoms.length === 0) {
      localErrors.symptoms = 'At least one presenting symptom is required.';
    }
    if (bpSys !== '' && bpDia !== '' && Number(bpSys) <= Number(bpDia)) {
      localErrors['vitals.bp'] = 'Systolic BP must be greater than diastolic BP.';
    }

    if (Object.keys(localErrors).length > 0) {
      setErrors(localErrors);
      return;
    }

    setIsSubmitting(true);

    const vitalsPayload: ClinicalVitals = {};
    if (tempC !== '') vitalsPayload.temp_c = Number(tempC);
    if (bpSys !== '') vitalsPayload.bp_sys = Number(bpSys);
    if (bpDia !== '') vitalsPayload.bp_dia = Number(bpDia);
    if (hr !== '') vitalsPayload.hr = Number(hr);
    if (spo2 !== '') vitalsPayload.spo2 = Number(spo2);
    if (respRate !== '') vitalsPayload.resp_rate = Number(respRate);
    if (bloodSugar !== '') vitalsPayload.blood_sugar = Number(bloodSugar);

    const labsPayload: Record<string, any> = {};
    if (platelets !== '') labsPayload.platelets = Number(platelets);
    if (wbc !== '') labsPayload.wbc = Number(wbc);

    try {
      const res = await clinicalApi.registerPatient({
        name: appMode === 'clinical' && name.trim() ? name.trim() : undefined,
        contact: appMode === 'clinical' && contact.trim() ? contact.trim() : undefined,
        age: Number(age),
        sex,
        weight: weight !== '' ? Number(weight) : undefined,
        height: height !== '' ? Number(height) : undefined,
        symptoms: selectedSymptoms,
        symptom_duration_days: durationDays,
        vitals: Object.keys(vitalsPayload).length > 0 ? vitalsPayload : undefined,
        structured_ecg_finding: ecgFinding || undefined,
        optional_labs: Object.keys(labsPayload).length > 0 ? labsPayload : undefined,
      });

      if (res.encounter) {
        navigate(`/encounters/${res.encounter.id}`);
      } else {
        navigate(`/patients/${res.patient.id}`);
      }
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (detail && typeof detail === 'object' && detail.errors) {
        setErrors(detail.errors);
        setGlobalError(detail.message || 'Please correct the highlighted clinical fields.');
      } else {
        setGlobalError(err.response?.data?.message || err.message || 'Failed to submit patient encounter.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-12">
      {/* Header Banner */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-blue-600 font-semibold text-xs uppercase tracking-wider mb-1">
            <UserPlus size={16} />
            Clinical Intake & Assessment
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">New Patient Registration</h1>
          <p className="text-slate-500 text-sm mt-0.5">
            Capture demographics, presenting symptoms, and vitals. Generates differential AI diagnosis for doctor confirmation.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs bg-slate-50 text-slate-600 px-3.5 py-2 rounded-xl border border-slate-200 self-start md:self-auto">
          <ShieldCheck size={16} className="text-emerald-600 shrink-0" />
          <span>Patient Name & Contact are <strong>encrypted at rest (AES-128 Fernet)</strong></span>
        </div>
      </div>

      {globalError && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5 text-rose-600" />
          <div>
            <p className="font-semibold text-sm">Validation Notice</p>
            <p className="text-xs mt-0.5">{globalError}</p>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate className="space-y-6">
        {/* Section 1: Demographics */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-5">
          <div className="border-b border-slate-100 pb-3 flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <span className="w-6 h-6 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center text-xs font-bold">1</span>
              Patient Demographics
            </h2>
            <span className="text-xs text-slate-400 font-medium">* Age and Sex required</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {appMode === 'informational' ? (
              <div className="col-span-1 md:col-span-2 p-3.5 rounded-xl bg-blue-50/70 border border-blue-200 text-blue-900 text-xs flex items-center gap-2.5">
                <ShieldCheck className="w-5 h-5 text-blue-600 flex-shrink-0" />
                <span className="leading-relaxed">
                  <strong>Informational Mode Active:</strong> Direct patient identifiers (full name, phone, email) are not collected. All records are processed anonymously.
                </span>
              </div>
            ) : (
              <>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Full Name <span className="text-slate-400 font-normal">(Optional)</span>
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. John Doe"
                    className={cn(
                      "w-full px-3.5 py-2 rounded-xl text-sm border bg-slate-50/50 transition-all focus:bg-white focus:outline-none focus:ring-2",
                      errors.name ? "border-rose-300 focus:ring-rose-200" : "border-slate-200 focus:ring-blue-100 focus:border-blue-500"
                    )}
                  />
                  {errors.name && <p className="text-xs text-rose-600 mt-1">{errors.name}</p>}
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Contact Phone / Email <span className="text-slate-400 font-normal">(Optional)</span>
                  </label>
                  <input
                    type="text"
                    value={contact}
                    onChange={(e) => setContact(e.target.value)}
                    placeholder="e.g. +1-555-0199"
                    className={cn(
                      "w-full px-3.5 py-2 rounded-xl text-sm border bg-slate-50/50 transition-all focus:bg-white focus:outline-none focus:ring-2",
                      errors.contact ? "border-rose-300 focus:ring-rose-200" : "border-slate-200 focus:ring-blue-100 focus:border-blue-500"
                    )}
                  />
                  {errors.contact && <p className="text-xs text-rose-600 mt-1">{errors.contact}</p>}
                </div>
              </>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Age (Years) <span className="text-rose-500">*</span>
              </label>
              <input
                type="number"
                min="0"
                max="125"
                value={age}
                onChange={(e) => setAge(e.target.value === '' ? '' : Number(e.target.value))}
                placeholder="e.g. 35"
                required
                className={cn(
                  "w-full px-3.5 py-2 rounded-xl text-sm border bg-slate-50/50 transition-all focus:bg-white focus:outline-none focus:ring-2",
                  errors.age ? "border-rose-300 focus:ring-rose-200 bg-rose-50/30" : "border-slate-200 focus:ring-blue-100 focus:border-blue-500"
                )}
              />
              {errors.age && <p className="text-xs text-rose-600 mt-1">{errors.age}</p>}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Biological Sex <span className="text-rose-500">*</span>
              </label>
              <select
                value={sex}
                onChange={(e) => setSex(Number(e.target.value))}
                className="w-full px-3.5 py-2 rounded-xl text-sm border border-slate-200 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
              >
                <option value={0}>Female</option>
                <option value={1}>Male</option>
                <option value={2}>Other</option>
              </select>
              {errors.sex && <p className="text-xs text-rose-600 mt-1">{errors.sex}</p>}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Weight <span className="text-slate-400 font-normal">(kg, Optional)</span>
              </label>
              <input
                type="number"
                step="0.1"
                min="0.5"
                max="450"
                value={weight}
                onChange={(e) => setWeight(e.target.value === '' ? '' : Number(e.target.value))}
                placeholder="e.g. 68.5"
                className={cn(
                  "w-full px-3.5 py-2 rounded-xl text-sm border bg-slate-50/50 transition-all focus:bg-white focus:outline-none focus:ring-2",
                  errors.weight ? "border-rose-300 focus:ring-rose-200" : "border-slate-200 focus:ring-blue-100 focus:border-blue-500"
                )}
              />
              {errors.weight && <p className="text-xs text-rose-600 mt-1">{errors.weight}</p>}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Height <span className="text-slate-400 font-normal">(cm, Optional)</span>
              </label>
              <input
                type="number"
                step="0.5"
                min="30"
                max="260"
                value={height}
                onChange={(e) => setHeight(e.target.value === '' ? '' : Number(e.target.value))}
                placeholder="e.g. 172.0"
                className={cn(
                  "w-full px-3.5 py-2 rounded-xl text-sm border bg-slate-50/50 transition-all focus:bg-white focus:outline-none focus:ring-2",
                  errors.height ? "border-rose-300 focus:ring-rose-200" : "border-slate-200 focus:ring-blue-100 focus:border-blue-500"
                )}
              />
              {errors.height && <p className="text-xs text-rose-600 mt-1">{errors.height}</p>}
            </div>
          </div>
        </div>

        {/* Section 2: Symptoms & Presentation */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-5">
          <div className="border-b border-slate-100 pb-3 flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <span className="w-6 h-6 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center text-xs font-bold">2</span>
              Presenting Symptoms & Duration
            </h2>
            <span className="text-xs text-rose-500 font-medium">* Select at least one symptom</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Searchable Symptoms Multi-Select
              </label>
              <div className="relative mb-2">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="text"
                  value={symptomSearch}
                  onChange={(e) => setSymptomSearch(e.target.value)}
                  placeholder="Type to filter symptoms (fever, cough, rash, chest pain...)"
                  className="w-full pl-9 pr-3.5 py-2 rounded-xl text-sm border border-slate-200 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
                />
              </div>

              {/* Selected Pills */}
              {selectedSymptoms.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-3 p-2.5 rounded-xl bg-blue-50/50 border border-blue-100">
                  <span className="text-xs font-medium text-blue-800 self-center mr-1">Selected:</span>
                  {selectedSymptoms.map((code) => {
                    const item = availableSymptoms.find((s) => s.code === code);
                    return (
                      <span
                        key={code}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold bg-blue-600 text-white shadow-xs"
                      >
                        {item ? item.label : code}
                        <button
                          type="button"
                          onClick={() => toggleSymptom(code)}
                          className="hover:text-blue-200 p-0.5"
                        >
                          <X size={12} />
                        </button>
                      </span>
                    );
                  })}
                </div>
              )}

              {/* Available Symptom Grid */}
              <div className="max-h-52 overflow-y-auto border border-slate-200 rounded-xl p-2.5 grid grid-cols-1 sm:grid-cols-2 gap-1.5 bg-slate-50/30">
                {isLoadingSymptoms ? (
                  <div className="col-span-2 flex items-center justify-center py-6 text-slate-400 text-xs">
                    <Loader2 className="w-4 h-4 animate-spin mr-2" /> Loading symptoms taxonomy...
                  </div>
                ) : filteredSymptoms.length === 0 ? (
                  <div className="col-span-2 text-center py-4 text-xs text-slate-400">
                    No matching symptoms found.
                  </div>
                ) : (
                  filteredSymptoms.map((s) => {
                    const isSelected = selectedSymptoms.includes(s.code);
                    return (
                      <button
                        type="button"
                        key={s.code}
                        onClick={() => toggleSymptom(s.code)}
                        className={cn(
                          "flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium text-left transition-all border",
                          isSelected
                            ? "bg-blue-50 border-blue-300 text-blue-800 font-semibold"
                            : "bg-white border-slate-200/80 text-slate-700 hover:border-slate-300 hover:bg-slate-50"
                        )}
                      >
                        <span>{s.label}</span>
                        {isSelected && <CheckCircle2 size={14} className="text-blue-600 shrink-0" />}
                      </button>
                    );
                  })
                )}
              </div>
              {errors.symptoms && <p className="text-xs text-rose-600 mt-1">{errors.symptoms}</p>}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Symptom Duration (Days)
              </label>
              <input
                type="number"
                min="1"
                max="365"
                value={durationDays}
                onChange={(e) => setDurationDays(Number(e.target.value))}
                className={cn(
                  "w-full px-3.5 py-2 rounded-xl text-sm border bg-slate-50/50 transition-all focus:bg-white focus:outline-none focus:ring-2",
                  errors.symptom_duration_days ? "border-rose-300 focus:ring-rose-200" : "border-slate-200 focus:ring-blue-100 focus:border-blue-500"
                )}
              />
              <p className="text-[11px] text-slate-400 mt-1">Number of days symptoms have been actively present.</p>
              {errors.symptom_duration_days && <p className="text-xs text-rose-600 mt-1">{errors.symptom_duration_days}</p>}
            </div>
          </div>
        </div>

        {/* Section 3: Vitals & Lab Indicators (Optional) */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-5">
          <div className="border-b border-slate-100 pb-3 flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <span className="w-6 h-6 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center text-xs font-bold">3</span>
              Clinical Vitals & Laboratory Findings
            </h2>
            <span className="text-xs text-slate-400 font-medium">All vitals are optional</span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center gap-1.5">
                <Thermometer size={14} className="text-amber-500" /> Temperature (°C)
              </label>
              <input
                type="number"
                step="0.1"
                min="30"
                max="45"
                value={tempC}
                onChange={(e) => setTempC(e.target.value === '' ? '' : Number(e.target.value))}
                placeholder="e.g. 38.5"
                className={cn(
                  "w-full px-3.5 py-2 rounded-xl text-sm border bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2",
                  errors['vitals.temp'] ? "border-rose-300 focus:ring-rose-200" : "border-slate-200 focus:ring-blue-100 focus:border-blue-500"
                )}
              />
              {errors['vitals.temp'] && <p className="text-xs text-rose-600 mt-1">{errors['vitals.temp']}</p>}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center gap-1.5">
                <Activity size={14} className="text-rose-500" /> Systolic BP (mmHg)
              </label>
              <input
                type="number"
                min="50"
                max="260"
                value={bpSys}
                onChange={(e) => setBpSys(e.target.value === '' ? '' : Number(e.target.value))}
                placeholder="e.g. 120"
                className={cn(
                  "w-full px-3.5 py-2 rounded-xl text-sm border bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2",
                  errors['vitals.bp_sys'] || errors['vitals.bp'] ? "border-rose-300 focus:ring-rose-200" : "border-slate-200 focus:ring-blue-100 focus:border-blue-500"
                )}
              />
              {errors['vitals.bp_sys'] && <p className="text-xs text-rose-600 mt-1">{errors['vitals.bp_sys']}</p>}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center gap-1.5">
                <Activity size={14} className="text-rose-500" /> Diastolic BP (mmHg)
              </label>
              <input
                type="number"
                min="30"
                max="160"
                value={bpDia}
                onChange={(e) => setBpDia(e.target.value === '' ? '' : Number(e.target.value))}
                placeholder="e.g. 80"
                className={cn(
                  "w-full px-3.5 py-2 rounded-xl text-sm border bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2",
                  errors['vitals.bp_dia'] || errors['vitals.bp'] ? "border-rose-300 focus:ring-rose-200" : "border-slate-200 focus:ring-blue-100 focus:border-blue-500"
                )}
              />
              {errors['vitals.bp_dia'] && <p className="text-xs text-rose-600 mt-1">{errors['vitals.bp_dia']}</p>}
              {errors['vitals.bp'] && <p className="text-xs text-rose-600 mt-1">{errors['vitals.bp']}</p>}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center gap-1.5">
                <Heart size={14} className="text-red-500" /> Heart Rate (bpm)
              </label>
              <input
                type="number"
                min="30"
                max="260"
                value={hr}
                onChange={(e) => setHr(e.target.value === '' ? '' : Number(e.target.value))}
                placeholder="e.g. 76"
                className={cn(
                  "w-full px-3.5 py-2 rounded-xl text-sm border bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2",
                  errors['vitals.hr'] ? "border-rose-300 focus:ring-rose-200" : "border-slate-200 focus:ring-blue-100 focus:border-blue-500"
                )}
              />
              {errors['vitals.hr'] && <p className="text-xs text-rose-600 mt-1">{errors['vitals.hr']}</p>}
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-1">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Oxygen Saturation (SpO2 %)
              </label>
              <input
                type="number"
                min="50"
                max="100"
                value={spo2}
                onChange={(e) => setSpo2(e.target.value === '' ? '' : Number(e.target.value))}
                placeholder="e.g. 98"
                className={cn(
                  "w-full px-3.5 py-2 rounded-xl text-sm border bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2",
                  errors['vitals.spo2'] ? "border-rose-300 focus:ring-rose-200" : "border-slate-200 focus:ring-blue-100 focus:border-blue-500"
                )}
              />
              {errors['vitals.spo2'] && <p className="text-xs text-rose-600 mt-1">{errors['vitals.spo2']}</p>}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Respiratory Rate (bpm)
              </label>
              <input
                type="number"
                min="5"
                max="70"
                value={respRate}
                onChange={(e) => setRespRate(e.target.value === '' ? '' : Number(e.target.value))}
                placeholder="e.g. 16"
                className="w-full px-3.5 py-2 rounded-xl text-sm border border-slate-200 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Blood Glucose (mg/dL)
              </label>
              <input
                type="number"
                min="20"
                max="700"
                value={bloodSugar}
                onChange={(e) => setBloodSugar(e.target.value === '' ? '' : Number(e.target.value))}
                placeholder="e.g. 105"
                className="w-full px-3.5 py-2 rounded-xl text-sm border border-slate-200 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Structured ECG Finding
              </label>
              <select
                value={ecgFinding}
                onChange={(e) => setEcgFinding(e.target.value)}
                className="w-full px-3.5 py-2 rounded-xl text-sm border border-slate-200 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
              >
                <option value="normal">Normal Sinus Rhythm</option>
                <option value="st_change">ST Segment Elevation / Depression</option>
                <option value="arrhythmia">Arrhythmia / Ectopic beats</option>
                <option value="tachycardia">Sinus Tachycardia</option>
                <option value="other">Other Abnormality</option>
              </select>
            </div>
          </div>

          <div className="border-t border-slate-100 pt-3 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Platelet Count (x10³/µL) <span className="text-slate-400 font-normal">(Crucial for Dengue)</span>
              </label>
              <input
                type="number"
                step="1"
                min="5"
                max="2000"
                value={platelets}
                onChange={(e) => setPlatelets(e.target.value === '' ? '' : Number(e.target.value))}
                placeholder="e.g. 140 (Normal: 150-450)"
                className="w-full px-3.5 py-2 rounded-xl text-sm border border-slate-200 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                WBC Total Count (x10³/µL) <span className="text-slate-400 font-normal">(Leukocytosis / Leukopenia)</span>
              </label>
              <input
                type="number"
                step="0.1"
                min="0.2"
                max="150"
                value={wbc}
                onChange={(e) => setWbc(e.target.value === '' ? '' : Number(e.target.value))}
                placeholder="e.g. 8.4 (Normal: 4.0-11.0)"
                className="w-full px-3.5 py-2 rounded-xl text-sm border border-slate-200 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Submit Bar */}
        <div className="flex items-center justify-between bg-white rounded-2xl p-5 border border-slate-200/80 shadow-xs">
          <div className="text-xs text-slate-500">
            Clicking assess will securely register the patient and compute top-3 AI differential probabilities.
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => navigate('/patients')}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200/80 rounded-xl transition-all"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 shadow-md shadow-blue-500/20 transition-all disabled:opacity-60"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Evaluating Clinical Evidence...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Run AI Differential Assessment
                  <ArrowRight size={14} />
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
