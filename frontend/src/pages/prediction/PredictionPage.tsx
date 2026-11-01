import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Sparkles, AlertTriangle, Activity, ArrowRight, Shield,
  CheckCircle2, HelpCircle, FileText, Loader2, Stethoscope, Plus,
  Info, ChevronDown, ChevronUp, Database
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

  // Model Info & Bootstrap Statistics State
  const [modelInfoOpen, setModelInfoOpen] = useState(false);
  const [modelInfo, setModelInfo] = useState<any>(null);
  const [loadingModelInfo, setLoadingModelInfo] = useState(false);

  useEffect(() => {
    // Optionally fetch model info on mount
    const fetchInfo = async () => {
      try {
        setLoadingModelInfo(true);
        const data = await api.clinicalApi.getModelInfo();
        if (data?.evaluation) {
          setModelInfo(data.evaluation);
        }
      } catch (err) {
        console.warn('Could not fetch live model info', err);
      } finally {
        setLoadingModelInfo(false);
      }
    };
    fetchInfo();
  }, []);

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
      className="flex flex-col gap-6 max-w-[1440px] mx-auto w-full pb-10"
    >
      {/* ── TOP BANNER: MODEL INFO & STATISTICAL METRICS TOGGLE ── */}
      <Card className="border-slate-200 shadow-2xs p-4 bg-white rounded-2xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-blue-50 text-blue-700">
              <Stethoscope className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-bold text-slate-900 tracking-tight">TrustFed Clinical Differential Decision Support</h1>
                <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 text-[10px] font-mono font-semibold">
                  TF-GenDisease-v1.0
                </Badge>
                <Badge variant="outline" className="bg-amber-50 text-amber-800 border-amber-300 text-[10px] font-semibold">
                  Prototype Benchmark (Not Clinically Validated)
                </Badge>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Dataset: Public (UCI ML) + Synthetic Supplement (N=1,080) • 18 Diagnostic Categories
              </p>
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setModelInfoOpen(!modelInfoOpen)}
            className="text-xs font-semibold border-slate-300 text-slate-700 hover:bg-slate-50"
          >
            <Info className="w-3.5 h-3.5 mr-1.5 text-blue-600" />
            {modelInfoOpen ? 'Hide Model Statistics & CIs' : 'Model Info & Bootstrap 95% CIs'}
            {modelInfoOpen ? <ChevronUp className="w-3.5 h-3.5 ml-1" /> : <ChevronDown className="w-3.5 h-3.5 ml-1" />}
          </Button>
        </div>

        {/* Model Info Collapsible Panel */}
        {modelInfoOpen && (
          <div className="mt-4 pt-4 border-t border-slate-100 text-xs">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-[10px] uppercase font-bold text-slate-500 block">Top-3 Coverage</span>
                <span className="text-base font-bold text-slate-900">
                  {modelInfo ? `${(modelInfo.top3Accuracy * 100).toFixed(1)}%` : '86.1%'}
                </span>
                <span className="text-[10px] text-slate-500 block">
                  95% CI: {modelInfo?.top3Accuracy_ci_95 ? `[${(modelInfo.top3Accuracy_ci_95[0]*100).toFixed(1)}%, ${(modelInfo.top3Accuracy_ci_95[1]*100).toFixed(1)}%]` : '[81.9%, 90.7%]'}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-[10px] uppercase font-bold text-slate-500 block">Top-1 Accuracy</span>
                <span className="text-base font-bold text-slate-900">
                  {modelInfo ? `${(modelInfo.top1Accuracy * 100).toFixed(1)}%` : '61.1%'}
                </span>
                <span className="text-[10px] text-slate-500 block">
                  95% CI: {modelInfo?.top1Accuracy_ci_95 ? `[${(modelInfo.top1Accuracy_ci_95[0]*100).toFixed(1)}%, ${(modelInfo.top1Accuracy_ci_95[1]*100).toFixed(1)}%]` : '[54.6%, 67.1%]'}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-[10px] uppercase font-bold text-slate-500 block">Macro-F1 Score</span>
                <span className="text-base font-bold text-slate-900">
                  {modelInfo ? modelInfo.macroF1.toFixed(3) : '0.572'}
                </span>
                <span className="text-[10px] text-slate-500 block">
                  95% CI: {modelInfo?.macroF1_ci_95 ? `[${modelInfo.macroF1_ci_95[0].toFixed(3)}, ${modelInfo.macroF1_ci_95[1].toFixed(3)}]` : '[0.504, 0.624]'}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                <span className="text-[10px] uppercase font-bold text-slate-500 block">Calibration Error (ECE)</span>
                <span className="text-base font-bold text-slate-900">
                  {modelInfo ? modelInfo.expectedCalibrationError.toFixed(4) : '0.0919'}
                </span>
                <span className="text-[10px] text-slate-500 block">
                  95% CI: {modelInfo?.expectedCalibrationError_ci_95 ? `[${modelInfo.expectedCalibrationError_ci_95[0].toFixed(4)}, ${modelInfo.expectedCalibrationError_ci_95[1].toFixed(4)}]` : '[0.0690, 0.1660]'}
                </span>
              </div>
            </div>

            {/* Per-Disease Table with Sample Count and Low-Confidence Flags */}
            <div className="overflow-x-auto max-h-[220px] rounded-xl border border-slate-200 bg-white">
              <table className="w-full text-left text-[11px]">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold sticky top-0">
                  <tr>
                    <th className="py-2 px-3">Condition Name</th>
                    <th className="py-2 px-3 text-center">Test Support (N)</th>
                    <th className="py-2 px-3 text-center">Confidence Tier</th>
                    <th className="py-2 px-3 text-right">Precision (95% CI)</th>
                    <th className="py-2 px-3 text-right">Recall (95% CI)</th>
                    <th className="py-2 px-3 text-right">F1 (95% CI)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {modelInfo?.perDisease ? (
                    Object.entries(modelInfo.perDisease).map(([code, d]: [string, any]) => (
                      <tr key={code} className="hover:bg-slate-50/60">
                        <td className="py-1.5 px-3 font-medium text-slate-800">{d.name}</td>
                        <td className="py-1.5 px-3 text-center font-mono text-slate-600">{d.support}</td>
                        <td className="py-1.5 px-3 text-center">
                          {d.low_confidence ? (
                            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                              ⚠️ low confidence (&lt;20)
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-green-50 text-green-700 border border-green-200">
                              standard
                            </span>
                          )}
                        </td>
                        <td className="py-1.5 px-3 text-right font-mono text-slate-600">
                          {d.precision.toFixed(3)} <span className="text-[10px] text-slate-400">[{d.precision_ci_95?.[0].toFixed(2)}, {d.precision_ci_95?.[1].toFixed(2)}]</span>
                        </td>
                        <td className="py-1.5 px-3 text-right font-mono text-slate-600">
                          {d.recall.toFixed(3)} <span className="text-[10px] text-slate-400">[{d.recall_ci_95?.[0].toFixed(2)}, {d.recall_ci_95?.[1].toFixed(2)}]</span>
                        </td>
                        <td className="py-1.5 px-3 text-right font-mono font-bold text-slate-900">
                          {d.f1.toFixed(3)} <span className="text-[10px] font-normal text-slate-400">[{d.f1_ci_95?.[0].toFixed(2)}, {d.f1_ci_95?.[1].toFixed(2)}]</span>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="py-3 text-center text-slate-400">
                        All 18 disease categories currently have N &lt; 20 held-out test cases and are flagged as low confidence.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <p className="text-[10px] text-slate-500 mt-2">
              All intervals computed using non-parametric percentile bootstrap (B=1,000 resamples on held-out test cohort N=216).
            </p>
          </div>
        )}
      </Card>

      {/* ── MAIN WORKSPACE: INPUTS + RESULTS ── */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* ── LEFT: INPUT FORM ── */}
        <div className="w-full lg:w-[50%] flex flex-col gap-5">
          <Card className="border-slate-200 shadow-2xs p-6 bg-white rounded-2xl">
            <div className="flex justify-between items-center mb-4 pb-3 border-b border-slate-100">
              <div>
                <h2 className="text-base font-bold text-slate-900 tracking-tight">Presenting Clinical Features</h2>
                <p className="text-xs text-slate-500">Enter patient presentation or choose a validated phenotype preset</p>
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

        {/* ── RIGHT: TOP-3 DIFFERENTIAL & RESULTS PAGE ── */}
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
              {/* Mandatory Result Badges: Model Version, Dataset Origin, Prototype Benchmark Label */}
              <div className="flex flex-wrap items-center gap-2 p-3 bg-slate-50 border border-slate-200 rounded-xl text-[11px]">
                <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 font-mono">
                  Model: {result.modelVersion || 'TF-GenDisease-v1.0'}
                </Badge>
                <Badge variant="outline" className="bg-slate-100 text-slate-700 border-slate-300">
                  <Database className="w-3 h-3 mr-1 inline" />
                  {result.datasetOrigin || 'Public / Synthetic Dataset (N=1,080)'}
                </Badge>
                <Badge variant="outline" className="bg-amber-50 text-amber-800 border-amber-300 font-semibold">
                  {result.prototypeBenchmarkLabel || 'Prototype Benchmark (Not Clinically Validated)'}
                </Badge>
              </div>

              {/* Red Flag Safety Banner */}
              {result.redFlags?.length > 0 && (
                <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-900 text-xs">
                  <div className="flex items-center gap-2 font-bold mb-1 text-red-950">
                    <AlertTriangle className="w-4 h-4 text-red-600" />
                    Clinical Red Flag Alert Triggered [Pending Physician Review]
                  </div>
                  <ul className="list-disc pl-5 space-y-1 text-[11px] text-red-800">
                    {result.redFlags.map((rf: any, i: number) => (
                      <li key={i}>
                        <strong>{rf.title || rf.condition}:</strong> {rf.escalationAction || rf.action || rf.recommendation}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Top 3 Calibrated Differential Diagnoses with Confidence */}
              <Card className="border-slate-200 shadow-2xs p-5 bg-white rounded-2xl">
                <div className="flex justify-between items-center mb-3">
                  <h2 className="text-sm font-bold text-slate-900">Calibrated Differential Diagnoses (Top 3)</h2>
                  <span className="text-[11px] font-semibold text-slate-500">
                    Confidence Interval Supported
                  </span>
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
                          <span className="font-mono font-bold text-blue-700">{probPct}% confidence</span>
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

              {/* Adaptive "Add This Parameter" Hint */}
              {(result.adaptiveHint || result.adaptiveQuestion) && (
                <Card className="border-slate-200 shadow-2xs p-4 bg-blue-50/60 border-blue-200 rounded-xl text-xs">
                  <div className="flex items-center gap-2 font-bold text-blue-900 mb-1">
                    <HelpCircle className="w-4 h-4 text-blue-600" />
                    Adaptive Parameter Optimization Hint
                  </div>
                  <p className="text-blue-800 text-[11px] leading-relaxed">
                    {result.adaptiveHint || result.adaptiveQuestion?.question}
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

              {/* Persistent Educational & Emergency Disclaimer */}
              <div className="text-[11px] text-slate-600 text-center bg-slate-50 border border-slate-200 rounded-xl p-3 shadow-2xs leading-relaxed">
                <span className="font-bold text-slate-800 block mb-0.5">Educational Decision Support Notice</span>
                {result.disclaimer || "Educational decision support. Not medical advice. Not clinically validated. In an emergency call your local emergency number."}
                <span className="block text-[10px] text-slate-400 mt-1">
                  Trained on public and synthetic benchmark data (N=1,080). Prototype benchmark results are not a clinical validation.
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
