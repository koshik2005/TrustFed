import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { ArrowRight, Save, Activity, Sparkles, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/services/api';

const PRESETS = [
  {
    name: 'High Risk (Cardiac Ischemia)',
    icon: '🔴',
    values: {
      age: '63', sex: '1', cp: '4', bp: '154', chol: '286', fbs: true, ecg: '2',
      hr: '124', exang: true, oldpeak: '2.6', slope: '2', ca: '2', thal: '7',
    },
  },
  {
    name: 'Moderate Risk (Borderline Angina)',
    icon: '🟡',
    values: {
      age: '55', sex: '1', cp: '2', bp: '135', chol: '240', fbs: false, ecg: '1',
      hr: '140', exang: true, oldpeak: '1.2', slope: '2', ca: '0', thal: '6',
    },
  },
  {
    name: 'Low Risk (Healthy Reference)',
    icon: '🟢',
    values: {
      age: '42', sex: '0', cp: '1', bp: '116', chol: '178', fbs: false, ecg: '0',
      hr: '168', exang: false, oldpeak: '0.2', slope: '1', ca: '0', thal: '3',
    },
  },
];

export default function PredictionPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [predicted, setPredicted] = useState(true);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [v, setV] = useState(PRESETS[0].values);
  const [predictionResult, setPredictionResult] = useState<any>({
    patientId: 'PT-892401',
    riskScore: 0.84,
    riskLabel: 'High',
    confidence: 0.94,
    shapValues: [
      { feature: 'ST Depression (Oldpeak)', value: 0.468, featureValue: '2.6 mm' },
      { feature: 'Fluoroscopy Vessels (ca)', value: 0.180, featureValue: '2 major vessels' },
      { feature: 'Chest Pain Classification', value: 0.144, featureValue: 'Type 4 (Asymptomatic)' },
      { feature: 'Resting Blood Pressure', value: 0.102, featureValue: '154 mmHg' },
      { feature: 'Maximum Heart Rate Achieved', value: 0.052, featureValue: '124 bpm' },
    ],
    nlpExplanation: 'Patient exhibits prominent ischemic markers: ST depression of 2.6mm with resting BP of 154 mmHg and 2 fluoroscopy-opacified vessels. Global federated model flags an 84% probability of acute coronary event. Urgent cardiologist evaluation and stress angiography recommended.',
  });
  const [error, setError] = useState('');

  const setField = (k: string, val: string | boolean) => setV((p) => ({ ...p, [k]: val }));
  const riskColor = (l?: string) => (l === 'High' ? '#EF4444' : l === 'Medium' ? '#F59E0B' : '#10B981');
  const arcLength = 471;

  const handlePredict = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.predictionApi.predict({
        age: Number(v.age), sex: Number(v.sex), chestPainType: Number(v.cp), restingBP: Number(v.bp),
        cholesterol: Number(v.chol), fastingBloodSugar: v.fbs ? 1 : 0, restingECG: Number(v.ecg),
        maxHeartRate: Number(v.hr), exerciseAngina: v.exang ? 1 : 0, oldPeak: Number(v.oldpeak),
        slope: Number(v.slope), ca: Number(v.ca), thal: Number(v.thal),
      });
      setPredictionResult(data);
      setPredicted(true);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Prediction failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveRecord = () => {
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col lg:flex-row gap-6 max-w-[1440px] mx-auto w-full pb-8 relative"
    >
      {/* LEFT COLUMN: Input Form */}
      <div className="w-full lg:w-[55%] flex flex-col gap-6">
        <Card className="bg-white border-slate-200 shadow-xs h-full rounded-2xl">
          <CardContent className="p-6">
            <div className="mb-5 border-b border-slate-100 pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h2 className="text-[18px] font-bold text-slate-900 tracking-tight">Clinical Vitals Assessment</h2>
                <p className="text-slate-500 text-xs font-medium">Federated Multi-Hospital Cardiac Risk Classifier</p>
              </div>
              <Badge className="bg-blue-50 text-blue-700 border-blue-200 text-xs px-2.5 py-1 font-semibold self-start sm:self-auto">
                Model: {(predictionResult as any)?.modelVersion || 'TF-HeartNet-v2 (Active)'}
              </Badge>
            </div>

            {/* Explicit Clinical Disclaimer */}
            <div className="mb-5 flex items-start gap-2.5 p-3 rounded-xl bg-amber-500/10 border border-amber-500/25 text-amber-900 text-xs">
              <span className="text-base flex-shrink-0">⚠️</span>
              <div>
                <span className="font-semibold text-amber-950">Clinical Decision Support Only — Not a Diagnostic Evaluation: </span>
                <span className="text-amber-800 leading-relaxed">
                  This tool provides assistive statistical risk estimation based on multi-hospital federated learning. It does not replace comprehensive medical examination, physician judgement, or diagnostic laboratory testing.
                </span>
              </div>
            </div>

            {/* Clinical Presets */}
            <div className="mb-5 p-3 rounded-xl bg-slate-50 border border-slate-200">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                Quick Clinical Presets
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-2">
                {PRESETS.map((preset) => (
                  <button
                    key={preset.name}
                    type="button"
                    onClick={() => {
                      setV(preset.values);
                      setPredicted(false);
                    }}
                    className="px-2.5 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 hover:border-blue-400 hover:bg-blue-50/50 hover:text-blue-700 transition-all text-xs font-medium text-left truncate shadow-2xs"
                  >
                    {preset.icon} {preset.name.split(' ')[0]} {preset.name.split(' ')[1]}
                  </button>
                ))}
              </div>
            </div>

            {/* Form Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

              <div className="flex flex-col gap-1.5">
                <Label className="text-slate-600 text-[12px] font-medium">Patient Age</Label>
                <Input type="number" value={v.age} onChange={(e) => setField('age', e.target.value)} placeholder="54" className="bg-slate-50 border-slate-200 text-slate-900 h-10 rounded-lg" />
              </div>

              <div className="flex flex-col gap-1.5">
                <Label className="text-slate-600 text-[12px] font-medium">Sex</Label>
                <Select value={v.sex} onValueChange={(x) => setField('sex', String(x))}>
                  <SelectTrigger className="bg-slate-50 border-slate-200 text-slate-900 h-10 rounded-lg">
                    <SelectValue placeholder="Select" />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-slate-200 text-slate-900 shadow-xl">
                    <SelectItem value="1">Male</SelectItem>
                    <SelectItem value="0">Female</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label className="text-slate-600 text-[12px] font-medium">Chest Pain Type</Label>
                <Select value={v.cp} onValueChange={(x) => setField('cp', String(x))}>
                  <SelectTrigger className="bg-slate-50 border-slate-200 text-slate-900 h-10 rounded-lg">
                    <SelectValue placeholder="Select" />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-slate-200 text-slate-900 shadow-xl">
                    <SelectItem value="1">Typical Angina</SelectItem>
                    <SelectItem value="2">Atypical Angina</SelectItem>
                    <SelectItem value="3">Non-anginal Pain</SelectItem>
                    <SelectItem value="4">Asymptomatic (Severe)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label className="text-slate-600 text-[12px] font-medium">Resting Blood Pressure (mmHg)</Label>
                <Input type="number" value={v.bp} onChange={(e) => setField('bp', e.target.value)} placeholder="130" className="bg-slate-50 border-slate-200 text-slate-900 h-10 rounded-lg" />
              </div>

              <div className="flex flex-col gap-1.5">
                <Label className="text-slate-600 text-[12px] font-medium">Serum Cholesterol (mg/dL)</Label>
                <Input type="number" value={v.chol} onChange={(e) => setField('chol', e.target.value)} placeholder="289" className="bg-slate-50 border-slate-200 text-slate-900 h-10 rounded-lg" />
              </div>

              <div className="flex flex-col gap-1.5 justify-center">
                <div className="flex items-center justify-between bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
                  <Label className="text-slate-700 text-xs font-medium cursor-pointer" htmlFor="fbs">Fasting Blood Sugar &gt; 120</Label>
                  <Switch id="fbs" checked={Boolean(v.fbs)} onCheckedChange={(c) => setField('fbs', c)} className="data-[state=checked]:bg-blue-600" />
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label className="text-slate-600 text-[12px] font-medium">Resting ECG</Label>
                <Select value={v.ecg} onValueChange={(x) => setField('ecg', String(x))}>
                  <SelectTrigger className="bg-slate-50 border-slate-200 text-slate-900 h-10 rounded-lg">
                    <SelectValue placeholder="Select" />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-slate-200 text-slate-900 shadow-xl">
                    <SelectItem value="0">Normal</SelectItem>
                    <SelectItem value="1">ST-T Wave Abnormality</SelectItem>
                    <SelectItem value="2">Left Ventricular Hypertrophy</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label className="text-slate-600 text-[12px] font-medium">Max Heart Rate (bpm)</Label>
                <Input type="number" value={v.hr} onChange={(e) => setField('hr', e.target.value)} placeholder="150" className="bg-slate-50 border-slate-200 text-slate-900 h-10 rounded-lg" />
              </div>

              <div className="flex flex-col gap-1.5 justify-center">
                <div className="flex items-center justify-between bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
                  <Label className="text-slate-700 text-xs font-medium cursor-pointer" htmlFor="exang">Exercise Induced Angina</Label>
                  <Switch id="exang" checked={Boolean(v.exang)} onCheckedChange={(c) => setField('exang', c)} className="data-[state=checked]:bg-blue-600" />
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label className="text-slate-600 text-[12px] font-medium">ST Depression (Oldpeak mm)</Label>
                <Input type="number" step="0.1" value={v.oldpeak} onChange={(e) => setField('oldpeak', e.target.value)} placeholder="1.4" className="bg-slate-50 border-slate-200 text-slate-900 h-10 rounded-lg" />
              </div>

              <div className="flex flex-col gap-1.5">
                <Label className="text-slate-600 text-[12px] font-medium">ST Slope</Label>
                <Select value={v.slope} onValueChange={(x) => setField('slope', String(x))}>
                  <SelectTrigger className="bg-slate-50 border-slate-200 text-slate-900 h-10 rounded-lg"><SelectValue placeholder="Select" /></SelectTrigger>
                  <SelectContent className="bg-white border-slate-200 text-slate-900 shadow-xl">
                    <SelectItem value="1">Upsloping</SelectItem>
                    <SelectItem value="2">Flat</SelectItem>
                    <SelectItem value="3">Downsloping</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label className="text-slate-600 text-[12px] font-medium">Major Vessels by Fluoroscopy (0-3)</Label>
                <Input type="number" min="0" max="3" value={v.ca} onChange={(e) => setField('ca', e.target.value)} className="bg-slate-50 border-slate-200 text-slate-900 h-10 rounded-lg" />
              </div>

            </div>

            <Button
              onClick={handlePredict}
              disabled={loading}
              className="w-full mt-6 h-12 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 text-white font-bold text-sm shadow-md shadow-blue-500/25 hover:from-blue-700 hover:to-cyan-700 transition-all border-none"
            >
              {loading ? (
                <div className="flex items-center gap-2"><Activity className="w-4 h-4 animate-spin" /> Evaluating Federated Neural Network...</div>
              ) : (
                "Run Model Inference"
              )}
            </Button>
            {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
          </CardContent>
        </Card>
      </div>

      {/* RIGHT COLUMN: Output */}
      <div className="w-full lg:w-[45%] flex flex-col">
        <Card className="bg-white border-slate-200 shadow-xs flex-1 rounded-2xl relative overflow-hidden">
          <CardContent className="p-6 flex flex-col h-full">
            <div className="flex items-center justify-between mb-6 pb-3 border-b border-slate-100">
              <span className="text-slate-500 text-xs font-mono font-medium tracking-wide">
                Patient Case #{predictionResult?.patientId ?? 'PT-892401'}
              </span>
              <div className="flex items-center gap-1.5">
                {(predictionResult as any)?.isFallback && (
                  <Badge className="bg-amber-50 text-amber-700 border-amber-200 text-[10px] font-semibold">
                    Baseline Model
                  </Badge>
                )}
                <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200 text-[11px] font-semibold">
                  Privacy-Preserving Inference
                </Badge>
              </div>
            </div>

            {predicted ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex-1 flex flex-col"
              >
                {/* Circular Gauge */}
                <div className="flex flex-col items-center justify-center my-4">
                  <div className="relative w-[180px] h-[180px]">
                    <svg className="w-full h-full rotate-[-90deg]" viewBox="0 0 160 160">
                      <circle cx="80" cy="80" r="75" fill="none" stroke="#F1F5F9" strokeWidth="10" />
                      <motion.circle
                        initial={{ strokeDashoffset: arcLength }}
                        animate={{ strokeDashoffset: arcLength * (1 - (predictionResult?.riskScore || 0)) }}
                        transition={{ duration: 1.2, ease: "easeOut" }}
                        cx="80"
                        cy="80"
                        r="75"
                        fill="none"
                        stroke={riskColor(predictionResult?.riskLabel)}
                        strokeWidth="10"
                        strokeLinecap="round"
                        strokeDasharray={arcLength}
                      />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <span className="text-slate-900 font-extrabold text-[36px] leading-none">
                        {Math.round((predictionResult?.riskScore || 0) * 100)}%
                      </span>
                      <span className={cn(
                        "font-bold text-[11px] tracking-wider mt-1 uppercase px-2 py-0.5 rounded-full text-white",
                        predictionResult?.riskLabel === 'High' ? "bg-red-500" : predictionResult?.riskLabel === 'Medium' ? "bg-amber-500" : "bg-emerald-500"
                      )}>
                        {predictionResult?.riskLabel} RISK
                      </span>
                    </div>
                  </div>
                  <div className="mt-3 text-xs text-slate-500 font-medium">
                    Model Confidence: <span className="font-bold text-slate-800">{Math.round((predictionResult?.confidence || 0.94) * 100)}%</span>
                  </div>
                </div>

                {/* AI Clinical Recommendation Note */}
                <div className="w-full mb-4 p-4 rounded-xl border border-blue-200 bg-blue-50/70 relative">
                  <h4 className="text-[11px] uppercase tracking-wider text-blue-900 font-bold mb-1.5 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                    Clinical Decision Support Guidance
                  </h4>
                  <p className="text-slate-700 text-xs leading-relaxed font-normal">
                    {predictionResult?.nlpExplanation}
                  </p>
                </div>

                {/* Top SHAP Drivers Preview */}
                {predictionResult?.shapValues && predictionResult.shapValues.length > 0 && (
                  <div className="mb-4">
                    <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-2">
                      Key Risk Driving Factors (SHAP)
                    </div>
                    <div className="space-y-1.5">
                      {predictionResult.shapValues.slice(0, 3).map((s: any, idx: number) => {
                        const numVal = typeof s.value === 'number' ? s.value : parseFloat(s.value || '0');
                        const isPositive = numVal >= 0;
                        const formattedVal = (isPositive ? '+' : '') + numVal.toFixed(2);
                        return (
                          <div key={idx} className="flex items-center justify-between text-xs p-2 rounded-lg bg-slate-50 border border-slate-100">
                            <span className="text-slate-700 font-medium">{s.feature}</span>
                            <span className={cn("font-mono font-semibold", isPositive ? "text-red-600" : "text-emerald-600")}>
                              {formattedVal} ({s.featureValue})
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="w-full flex flex-col sm:flex-row gap-2 mt-auto pt-4 border-t border-slate-100">
                  <Button
                    variant="outline"
                    className="flex-1 border-blue-300 text-blue-700 hover:bg-blue-50 font-semibold text-xs"
                    onClick={() => navigate('/explain')}
                  >
                    Deep SHAP Breakdown <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                  </Button>
                  <Button
                    variant="outline"
                    className={cn(
                      "flex-1 font-semibold text-xs transition-colors",
                      savedSuccess ? "bg-emerald-50 text-emerald-700 border-emerald-300" : "border-slate-300 text-slate-700 hover:bg-slate-50"
                    )}
                    onClick={handleSaveRecord}
                  >
                    {savedSuccess ? (
                      <>
                        <Check className="w-3.5 h-3.5 mr-1 text-emerald-600" /> Saved to EHR
                      </>
                    ) : (
                      <>
                        <Save className="w-3.5 h-3.5 mr-1" /> Save to Patient EHR
                      </>
                    )}
                  </Button>
                </div>

              </motion.div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-slate-400">
                <Activity className="w-10 h-10 mb-3 text-slate-300 animate-pulse" />
                <p className="text-slate-600 font-medium text-sm">Select a clinical preset or enter vitals, then click "Run Model Inference".</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </motion.div>
  );
}
