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
import { Search, ArrowRight, Save, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/services/api';

export default function PredictionPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [predicted, setPredicted] = useState(false);
  const [predictionResult, setPredictionResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [v, setV] = useState({
    age: '63', sex: '1', cp: '4', bp: '145', chol: '233', fbs: false, ecg: '2',
    hr: '150', exang: false, oldpeak: '2.3', slope: '3', ca: '0', thal: '6',
  });
  const setField = (k: string, val: string | boolean) => setV((p) => ({ ...p, [k]: val }));
  const riskColor = (l?: string) => (l === 'High' ? '#EF4444' : l === 'Medium' ? '#F59E0B' : '#10B981');

  const arcLength = 471; // roughly 2 * pi * 75 for gauge radius

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
      setPredicted(false);
      setError(e?.response?.data?.detail ?? 'Prediction failed');
    } finally {
      setLoading(false);
    }
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
        <Card className="glass-card bg-white border-slate-200 h-full">
          <CardContent className="p-6">
            <div className="mb-6 border-b border-slate-200 pb-4">
              <h2 className="text-[18px] font-bold text-slate-900 tracking-tight">Patient Vitals Input</h2>
              <p className="text-slate-600 text-[12px] font-medium">Global model · latest completed session</p>
            </div>

            {/* Search Bar */}
            <div className="relative w-full mb-6">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600 w-4 h-4" />
              <Input
                className="w-full bg-slate-50 border-slate-200 pl-10 text-slate-900 focus:border-blue-500 transition-colors h-10 rounded-lg placeholder:text-slate-500"
                placeholder="Search patient by ID or name..."
              />
            </div>

            {/* Form Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

              <div className="flex flex-col gap-1.5">
                <Label className="text-slate-600 text-[12px] font-medium">Age</Label>
                <Input type="number" value={v.age} onChange={(e) => setField('age', e.target.value)} placeholder="54" className="bg-slate-50 border-slate-200 text-slate-900 h-10" />
              </div>

              <div className="flex flex-col gap-1.5">
                <Label className="text-slate-600 text-[12px] font-medium">Sex</Label>
                <Select value={v.sex} onValueChange={(x) => setField('sex', String(x))}>
                  <SelectTrigger className="bg-slate-50 border-slate-200 text-slate-900 h-10">
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
                  <SelectTrigger className="bg-slate-50 border-slate-200 text-slate-900 h-10">
                    <SelectValue placeholder="Select" />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-slate-200 text-slate-900 shadow-xl">
                    <SelectItem value="1">Typical Angina</SelectItem>
                    <SelectItem value="2">Atypical Angina</SelectItem>
                    <SelectItem value="3">Non-anginal</SelectItem>
                    <SelectItem value="4">Asymptomatic</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label className="text-slate-600 text-[12px] font-medium">Resting BP (mmHg)</Label>
                <Input type="number" value={v.bp} onChange={(e) => setField('bp', e.target.value)} placeholder="130" className="bg-slate-50 border-slate-200 text-slate-900 h-10" />
              </div>

              <div className="flex flex-col gap-1.5">
                <Label className="text-slate-600 text-[12px] font-medium">Cholesterol (mg/dL)</Label>
                <Input type="number" value={v.chol} onChange={(e) => setField('chol', e.target.value)} placeholder="289" className="bg-slate-50 border-slate-200 text-slate-900 h-10" />
              </div>

              <div className="flex flex-col gap-1.5 justify-center mt-2">
                <div className="flex items-center justify-between bg-white/[0.02] border border-slate-200 rounded-lg px-3 py-2.5">
                  <Label className="text-slate-700 text-[13px] cursor-pointer" htmlFor="fbs">Fasting Blood Sugar &gt; 120</Label>
                  <Switch id="fbs" checked={v.fbs} onCheckedChange={(c) => setField('fbs', c)} className="data-[state=checked]:bg-blue-500" />
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label className="text-slate-600 text-[12px] font-medium">Resting ECG</Label>
                <Select value={v.ecg} onValueChange={(x) => setField('ecg', String(x))}>
                  <SelectTrigger className="bg-slate-50 border-slate-200 text-slate-900 h-10">
                    <SelectValue placeholder="Select" />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-slate-200 text-slate-900 shadow-xl">
                    <SelectItem value="0">Normal</SelectItem>
                    <SelectItem value="1">ST Abnormality</SelectItem>
                    <SelectItem value="2">LV Hypertrophy</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label className="text-slate-600 text-[12px] font-medium">Max Heart Rate</Label>
                <Input type="number" value={v.hr} onChange={(e) => setField('hr', e.target.value)} placeholder="150" className="bg-slate-50 border-slate-200 text-slate-900 h-10" />
              </div>

              <div className="flex flex-col gap-1.5 justify-center mt-2">
                <div className="flex items-center justify-between bg-white/[0.02] border border-slate-200 rounded-lg px-3 py-2.5">
                  <Label className="text-slate-700 text-[13px] cursor-pointer" htmlFor="exang">Exercise Induced Angina</Label>
                  <Switch id="exang" checked={v.exang} onCheckedChange={(c) => setField('exang', c)} className="data-[state=checked]:bg-blue-500" />
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label className="text-slate-600 text-[12px] font-medium">ST Depression</Label>
                <Input type="number" step="0.1" value={v.oldpeak} onChange={(e) => setField('oldpeak', e.target.value)} placeholder="1.4" className="bg-slate-50 border-slate-200 text-slate-900 h-10" />
              </div>

              <div className="flex flex-col gap-1.5">
                <Label className="text-slate-600 text-[12px] font-medium">ST Slope</Label>
                <Select value={v.slope} onValueChange={(x) => setField('slope', String(x))}>
                  <SelectTrigger className="bg-slate-50 border-slate-200 text-slate-900 h-10"><SelectValue placeholder="Select" /></SelectTrigger>
                  <SelectContent className="bg-white border-slate-200 text-slate-900 shadow-xl">
                    <SelectItem value="1">Upsloping</SelectItem>
                    <SelectItem value="2">Flat</SelectItem>
                    <SelectItem value="3">Downsloping</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label className="text-slate-600 text-[12px] font-medium">Major Vessels Coloured (0-3)</Label>
                <Input type="number" min="0" max="3" value={v.ca} onChange={(e) => setField('ca', e.target.value)} className="bg-slate-50 border-slate-200 text-slate-900 h-10" />
              </div>

              <div className="flex flex-col gap-1.5">
                <Label className="text-slate-600 text-[12px] font-medium">Thalassemia</Label>
                <Select value={v.thal} onValueChange={(x) => setField('thal', String(x))}>
                  <SelectTrigger className="bg-slate-50 border-slate-200 text-slate-900 h-10"><SelectValue placeholder="Select" /></SelectTrigger>
                  <SelectContent className="bg-white border-slate-200 text-slate-900 shadow-xl">
                    <SelectItem value="3">Normal</SelectItem>
                    <SelectItem value="6">Fixed defect</SelectItem>
                    <SelectItem value="7">Reversible defect</SelectItem>
                  </SelectContent>
                </Select>
              </div>

            </div>

            <Button
              onClick={handlePredict}
              disabled={loading}
              className="w-full mt-6 h-12 rounded-xl bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-bold text-sm shadow-[0_0_20px_rgba(59,130,246,0.3)] hover:shadow-[0_0_30px_rgba(59,130,246,0.5)] transition-all border-none"
            >
              {loading ? (
                <div className="flex items-center gap-2"><Activity className="w-4 h-4 animate-spin" /> Analyzing Model...</div>
              ) : (
                "Run Prediction"
              )}
            </Button>
            {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
          </CardContent>
        </Card>
      </div>

      {/* RIGHT COLUMN: Output */}
      <div className="w-full lg:w-[45%] flex flex-col">
        <Card className="glass-card bg-white border-slate-200 flex-1 relative overflow-hidden">
          <CardContent className="p-6 flex flex-col h-full">
            <div className="text-slate-600 text-[13px] font-mono tracking-wider mb-8">Patient #{predictionResult?.patientId ?? '—'}</div>

            {predicted ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex-1 flex flex-col items-center justify-center relative"
              >
                {/* Gauge Background Glow */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-48 h-48 bg-red-500/20 blur-[50px] rounded-full pointer-events-none"></div>

                {/* Circular Gauge */}
                <div className="relative w-[180px] h-[180px] mb-8">
                  <svg className="w-full h-full rotate-[-90deg]" viewBox="0 0 160 160">
                    <circle cx="80" cy="80" r="75" fill="none" stroke="#E2E8F0" strokeWidth="8" />
                    <motion.circle
                      initial={{ strokeDashoffset: arcLength }}
                      animate={{ strokeDashoffset: arcLength * (1 - (predictionResult?.riskScore || 0)) }}
                      transition={{ duration: 1.5, ease: "easeOut", delay: 0.2 }}
                      cx="80"
                      cy="80"
                      r="75"
                      fill="none"
                      stroke={riskColor(predictionResult?.riskLabel)}
                      strokeWidth="8"
                      strokeLinecap="round"
                      strokeDasharray={arcLength}
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-slate-900 font-bold text-[36px] leading-none drop-shadow-md">
                      {Math.round((predictionResult?.riskScore || 0) * 100)}%
                    </span>
                    <span className={cn(
                      "font-bold text-[11px] tracking-widest mt-1 uppercase",
                      predictionResult?.riskLabel === 'High' ? "text-red-500" : predictionResult?.riskLabel === 'Medium' ? "text-amber-500" : "text-emerald-500"
                    )}>
                      {predictionResult?.riskLabel} RISK
                    </span>
                  </div>
                </div>

                {/* Confidence Bar */}
                <div className="w-full max-w-[280px] mb-8">
                  <div className="flex justify-between items-end mb-2">
                    <span className="text-slate-600 text-[12px] font-medium">Confidence</span>
                    <span className="text-slate-900 font-bold text-[14px]">
                      {Math.round((predictionResult?.confidence || 0) * 100)}%
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-200 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.round((predictionResult?.confidence || 0) * 100)}%` }}
                      transition={{ duration: 1, delay: 0.5 }}
                      className="h-full bg-gradient-to-r from-blue-500 to-cyan-400"
                    />
                  </div>
                </div>

                {/* AI Explanation Box */}
                <div className="w-full mb-6 p-4 rounded-xl border border-blue-500/20 bg-blue-500/5 relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-1 h-full bg-blue-500"></div>
                  <h4 className="text-[11px] uppercase tracking-wider text-blue-400 font-bold mb-2 flex items-center gap-2">
                    AI Clinical Explanation <span className="text-slate-500 font-medium normal-case tracking-normal text-[10px]">(LLM if configured, else template)</span>
                  </h4>
                  <p className="text-slate-700 text-[12px] leading-relaxed">
                    {predictionResult?.nlpExplanation || 'Generating explanation...'}
                  </p>
                </div>

                {/* Patient Vitals Pills */}
                <div className="flex flex-wrap justify-center gap-2 mb-4">
                  <Badge className="bg-slate-100 border-slate-200 text-slate-700 font-normal px-3 py-1">Age: {v.age}</Badge>
                  <Badge className="bg-slate-100 border-slate-200 text-slate-700 font-normal px-3 py-1">Chol: {v.chol}</Badge>
                  <Badge className="bg-slate-100 border-slate-200 text-slate-700 font-normal px-3 py-1">HR: {v.hr}</Badge>
                </div>

                <div className="w-full border-t border-slate-200 my-4"></div>

                {/* Actions */}
                <div className="w-full flex flex-col gap-3 mt-2">
                  <Button
                    variant="outline"
                    className="border-cyan-600/60 text-cyan-700 hover:bg-cyan-50 hover:text-cyan-800 transition-colors w-full flex items-center justify-between"
                    onClick={() => navigate('/explain')}
                  >
                    View SHAP Explanation <ArrowRight className="w-4 h-4 ml-2" />
                  </Button>
                  <Button variant="ghost" className="text-slate-600 hover:text-slate-900 w-full border border-slate-200 hover:bg-slate-50">
                    <Save className="w-4 h-4 mr-2" /> Save to Record
                  </Button>
                </div>

              </motion.div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center opacity-30">
                <div className="w-32 h-32 rounded-full border-4 border-dashed border-slate-600 flex items-center justify-center mb-4">
                  <Activity className="w-8 h-8 text-slate-500" />
                </div>
                <p className="text-slate-600 text-sm font-medium">Awaiting input data</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </motion.div>
  );
}
