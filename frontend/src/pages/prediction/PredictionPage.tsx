import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Sparkles, AlertTriangle, Activity, ArrowRight, Shield,
  CheckCircle2, HelpCircle, FileText, Loader2, Stethoscope, Plus
} from 'lucide-react';
import { api } from '@/services/api';

const CLINICAL_PRESETS = [
  {
    name: 'Dengue / Acute Viral Presentation',
    icon: '🦟',
    values: {
      age: 28,
      sex: 1,
      symptoms: ['fever', 'headache', 'body ache', 'joint pain', 'rash'],
      symptom_duration_days: 4,
      vitals: { temperature: 102.4, heartRate: 98, bpSystolic: 110, bpDiastolic: 70, spo2: 98 }
    }
  },
  {
    name: 'Common Cold / Seasonal Viral',
    icon: '🤧',
    values: {
      age: 34,
      sex: 0,
      symptoms: ['runny nose', 'sore throat', 'cough', 'fatigue'],
      symptom_duration_days: 2,
      vitals: { temperature: 99.2, heartRate: 78, bpSystolic: 118, bpDiastolic: 76, spo2: 99 }
    }
  },
  {
    name: 'Acute Gastroenteritis',
    icon: '🤢',
    values: {
      age: 24,
      sex: 1,
      symptoms: ['vomiting', 'diarrhea', 'abdominal pain', 'nausea'],
      symptom_duration_days: 1,
      vitals: { temperature: 99.8, heartRate: 94, bpSystolic: 108, bpDiastolic: 68, spo2: 99 }
    }
  },
  {
    name: 'Asthma / Acute Bronchial Flare',
    icon: '🫁',
    values: {
      age: 45,
      sex: 0,
      symptoms: ['breathlessness', 'cough', 'chest tightness', 'wheezing'],
      symptom_duration_days: 3,
      vitals: { temperature: 98.6, heartRate: 102, bpSystolic: 130, bpDiastolic: 84, spo2: 93 }
    }
  }
];

const COMMON_SYMPTOMS = [
  'fever', 'cough', 'sore throat', 'runny nose', 'headache',
  'vomiting', 'diarrhea', 'abdominal pain', 'chest pain',
  'breathlessness', 'rash', 'joint pain', 'fatigue', 'body ache',
  'burning urination', 'loss of taste/smell', 'nausea', 'wheezing'
];

const formatDiseaseName = (name?: string) => {
  if (!name) return '';
  return name
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
};

export default function PredictionPage() {
  const navigate = useNavigate();
  const [age, setAge] = useState<number>(28);
  const [sex, setSex] = useState<number>(1);
  const [selectedSymptoms, setSelectedSymptoms] = useState<string[]>(CLINICAL_PRESETS[0].values.symptoms);
  const [durationDays, setDurationDays] = useState<number>(4);
  const [vitals, setVitals] = useState<any>(CLINICAL_PRESETS[0].values.vitals);

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const toggleSymptom = (symptom: string) => {
    if (selectedSymptoms.includes(symptom)) {
      setSelectedSymptoms(selectedSymptoms.filter((s) => s !== symptom));
    } else {
      setSelectedSymptoms([...selectedSymptoms, symptom]);
    }
  };

  const handlePredict = async () => {
    if (selectedSymptoms.length === 0) {
      setError('Please select at least one presenting symptom.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const payload = {
        age,
        sex,
        symptoms: selectedSymptoms,
        symptom_duration_days: durationDays,
        vitals
      };
      const data = await api.clinicalApi.predictDifferential(payload);
      setResult(data);
    } catch (err: any) {
      console.error('Prediction failed:', err);
      setError(err?.response?.data?.detail || err?.message || 'Differential prediction failed');
    } finally {
      setLoading(false);
    }
  };

  const applyPreset = (preset: typeof CLINICAL_PRESETS[0]) => {
    setAge(preset.values.age);
    setSex(preset.values.sex);
    setSelectedSymptoms(preset.values.symptoms);
    setDurationDays(preset.values.symptom_duration_days);
    setVitals(preset.values.vitals);
    setResult(null);
    setError(null);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col lg:flex-row gap-6 max-w-[1440px] mx-auto w-full pb-10"
    >
      {/* ── LEFT: INPUT FORM ── */}
      <div className="w-full lg:w-[50%] flex flex-col gap-5">
        <Card className="border-slate-200 shadow-2xs p-6 bg-white rounded-2xl">
          <div className="flex justify-between items-center mb-4 pb-3 border-b border-slate-100">
            <div>
              <h1 className="text-lg font-bold text-slate-900 tracking-tight">Clinical Differential Prediction</h1>
              <p className="text-xs text-slate-500">General multi-condition neural diagnostic inference (18 conditions)</p>
            </div>
            <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 text-xs font-mono font-semibold">
              TF-GenDisease
            </Badge>
          </div>

          {/* Clinical Presets */}
          <div className="mb-5 p-3 rounded-xl bg-slate-50 border border-slate-200">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-blue-600" />
              Quick Clinical Presentation Presets
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
              {CLINICAL_PRESETS.map((p) => (
                <button
                  key={p.name}
                  type="button"
                  onClick={() => applyPreset(p)}
                  className="px-2.5 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 hover:border-blue-400 hover:bg-blue-50/50 hover:text-blue-700 transition-all text-xs font-medium text-left truncate shadow-2xs flex items-center gap-1.5"
                >
                  <span>{p.icon}</span>
                  <span className="truncate">{p.name}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Demographics */}
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div>
              <label className="font-semibold text-slate-700 text-xs block mb-1">Patient Age</label>
              <Input
                type="number"
                min={0}
                max={120}
                value={age}
                onChange={(e) => setAge(parseInt(e.target.value) || 0)}
                className="h-9 text-xs"
              />
            </div>
            <div>
              <label className="font-semibold text-slate-700 text-xs block mb-1">Biological Sex</label>
              <select
                value={sex}
                onChange={(e) => setSex(parseInt(e.target.value))}
                className="w-full h-9 rounded-md border border-slate-300 bg-white px-3 py-1 text-xs text-slate-800"
              >
                <option value={1}>Male</option>
                <option value={0}>Female</option>
              </select>
            </div>
          </div>

          {/* Symptoms Multi-Select */}
          <div className="mb-4">
            <label className="font-semibold text-slate-700 text-xs block mb-1.5">
              Presenting Symptoms ({selectedSymptoms.length} selected)
            </label>
            <div className="flex flex-wrap gap-1.5 max-h-[160px] overflow-y-auto p-2 bg-slate-50 rounded-xl border border-slate-200">
              {COMMON_SYMPTOMS.map((symptom) => {
                const isSelected = selectedSymptoms.includes(symptom);
                return (
                  <button
                    key={symptom}
                    type="button"
                    onClick={() => toggleSymptom(symptom)}
                    className={`px-2.5 py-1 rounded-full text-xs font-medium transition-all capitalize ${
                      isSelected
                        ? 'bg-blue-600 text-white shadow-2xs'
                        : 'bg-white text-slate-700 border border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    {isSelected ? '✓ ' : '+ '}{symptom}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Optional Vitals */}
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl mb-4 text-xs">
            <span className="font-bold text-slate-700 block mb-2">Optional Clinical Vitals</span>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              <div>
                <label className="text-[11px] text-slate-500 block mb-0.5">Temp (°F)</label>
                <Input
                  type="number"
                  step="0.1"
                  value={vitals.temperature || ''}
                  onChange={(e) => setVitals({ ...vitals, temperature: parseFloat(e.target.value) || undefined })}
                  placeholder="98.6"
                  className="h-8 text-xs bg-white"
                />
              </div>
              <div>
                <label className="text-[11px] text-slate-500 block mb-0.5">Heart Rate (bpm)</label>
                <Input
                  type="number"
                  value={vitals.heartRate || ''}
                  onChange={(e) => setVitals({ ...vitals, heartRate: parseInt(e.target.value) || undefined })}
                  placeholder="75"
                  className="h-8 text-xs bg-white"
                />
              </div>
              <div>
                <label className="text-[11px] text-slate-500 block mb-0.5">SpO2 (%)</label>
                <Input
                  type="number"
                  value={vitals.spo2 || ''}
                  onChange={(e) => setVitals({ ...vitals, spo2: parseInt(e.target.value) || undefined })}
                  placeholder="98"
                  className="h-8 text-xs bg-white"
                />
              </div>
            </div>
          </div>

          {error && (
            <div className="p-3 mb-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <Button
            onClick={handlePredict}
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs h-10 shadow-xs"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Stethoscope className="w-4 h-4 mr-2" />}
            {loading ? 'Evaluating Model…' : 'Compute Top-3 Differential Diagnosis'}
          </Button>
        </Card>
      </div>

      {/* ── RIGHT: TOP-3 DIFFERENTIAL & EXPLANATIONS ── */}
      <div className="w-full lg:w-[50%] flex flex-col gap-5">
        {!result ? (
          <Card className="border-slate-200 shadow-2xs p-8 bg-white rounded-2xl flex flex-col items-center justify-center text-center min-h-[380px]">
            <Stethoscope className="w-12 h-12 text-slate-300 mb-3" />
            <h3 className="text-base font-bold text-slate-800 mb-1">Awaiting Clinical Presentation</h3>
            <p className="text-xs text-slate-500 max-w-sm">
              Select symptoms and vitals on the left, then click "Compute Top-3 Differential Diagnosis" to generate calibrated probabilities.
            </p>
          </Card>
        ) : (
          <div className="flex flex-col gap-4">
            {/* Red Flag Safety Banner */}
            {result.redFlags?.length > 0 && (
              <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-900 text-xs">
                <div className="flex items-center gap-2 font-bold mb-1 text-red-950">
                  <AlertTriangle className="w-4 h-4 text-red-600" />
                  Clinical Red Flag Alert Triggered
                </div>
                <ul className="list-disc pl-5 space-y-0.5 text-[11px] text-red-800">
                  {result.redFlags.map((rf: any, i: number) => (
                    <li key={i}><strong>{rf.condition}:</strong> {rf.recommendation}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Top 3 Calibrated Differential Diagnoses */}
            <Card className="border-slate-200 shadow-2xs p-5 bg-white rounded-2xl">
              <div className="flex justify-between items-center mb-3">
                <h2 className="text-sm font-bold text-slate-900">Calibrated Differential Diagnoses (Top 3)</h2>
                <Badge variant="outline" className="text-[10px] font-mono text-slate-500">
                  {result.modelVersion}
                </Badge>
              </div>

              <div className="flex flex-col gap-2.5">
                {result.predictedTop3?.map((pred: any, i: number) => {
                  const probPct = Math.round(pred.probability * 100);
                  return (
                    <div key={pred.disease} className="p-3 rounded-xl bg-slate-50 border border-slate-100 text-xs">
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-bold text-slate-800">
                          {i + 1}. {pred.displayName || formatDiseaseName(pred.disease)}
                        </span>
                        <span className="font-mono font-bold text-blue-700">{probPct}% probability</span>
                      </div>
                      <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
                        <div
                          className="bg-blue-600 h-1.5 rounded-full"
                          style={{ width: `${probPct}%` }}
                          aria-label={`${pred.disease} probability ${probPct} percent`}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>

            {/* Adaptive Questioning Guidance */}
            {result.adaptiveQuestion && (
              <Card className="border-slate-200 shadow-2xs p-4 bg-blue-50/50 border-blue-200 rounded-xl text-xs">
                <div className="flex items-center gap-2 font-bold text-blue-900 mb-1">
                  <HelpCircle className="w-4 h-4 text-blue-600" />
                  Adaptive Questioning (High Information Gain)
                </div>
                <p className="text-blue-800 text-[11px] leading-relaxed">
                  {result.adaptiveQuestion.question}
                </p>
              </Card>
            )}

            {/* Suggested Etiology & Remedies */}
            {result.suggestedClinicalGuidance && (
              <Card className="border-slate-200 shadow-2xs p-4 bg-white rounded-xl text-xs">
                <span className="text-[10px] font-bold text-amber-800 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 uppercase mb-2 inline-block">
                  {result.suggestedClinicalGuidance.verificationNotice}
                </span>
                <p className="font-semibold text-slate-800 mb-1">Suggested Etiology: <span className="font-normal text-slate-600">{result.suggestedClinicalGuidance.suggestedCause}</span></p>
                <div className="text-slate-600 text-[11px]">
                  <strong>Recommended Interventions:</strong>
                  <ul className="list-disc pl-5 mt-1 space-y-0.5">
                    {result.suggestedClinicalGuidance.commonRemedies?.map((rem: string, i: number) => (
                      <li key={i}>{rem}</li>
                    ))}
                  </ul>
                </div>
              </Card>
            )}

            {/* Disclaimer */}
            <div className="text-[11px] text-slate-500 text-center bg-slate-50 border border-slate-200 rounded-lg p-2.5">
              <span className="font-semibold text-slate-700">Prototype Decision Support: </span>
              {result.disclaimer || "Clinical decision support only, not a diagnostic verdict."}
              <span className="block text-[10px] text-slate-400 mt-0.5">Trained on public and synthetic benchmark data (N=1,080). Prototype benchmark results are not a clinical validation.</span>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}
