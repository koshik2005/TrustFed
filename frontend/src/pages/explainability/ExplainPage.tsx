import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { BrainCircuit, Timer, ArrowRight, Activity, Loader2 } from 'lucide-react';
import { api } from '@/services/api';
import type { PredictionResult } from '@/types';

export default function ExplainPage() {
  const navigate = useNavigate();
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLatestPrediction = async () => {
      try {
        const history = await api.predictionApi.getHistory(1, 1);
        if (history.items && history.items.length > 0) {
          setPrediction(history.items[0]);
        }
      } catch (error) {
        console.error("Failed to fetch prediction history", error);
      } finally {
        setLoading(false);
      }
    };
    fetchLatestPrediction();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[50vh]">
        <Loader2 className="h-8 w-8 animate-spin text-cyan-500" />
      </div>
    );
  }

  const shapData = prediction?.shapValues || [];
  const riskScorePercentage = prediction ? Math.round(prediction.riskScore * 100) : 0;
  const isHighRisk = prediction?.riskLabel === 'High';
  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col max-w-[1440px] mx-auto w-full pb-8 gap-6"
    >
      <style>{`
        .animated-border { position: relative; z-index: 1; }
        .animated-border::before {
          content: '';
          position: absolute;
          top: -2px; left: -2px; right: -2px; bottom: -2px;
          background: linear-gradient(45deg, #3B82F6, #06b6d4, #8b5cf6, #3B82F6);
          background-size: 400%;
          z-index: -1;
          filter: blur(6px);
          animation: glowing 8s linear infinite;
          border-radius: 14px;
        }
        @keyframes glowing {
          0% { background-position: 0 0; }
          50% { background-position: 400% 0; }
          100% { background-position: 0 0; }
        }
      `}</style>

      {/* PAGE HEADER */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 border-b border-slate-200 pb-6 relative z-10">
        <div>
          <h1 className="text-[24px] font-bold text-slate-900 mb-1 tracking-tight">AI Explainability</h1>
          <p className="text-slate-600 text-[13px] font-medium">Patient #{prediction?.patientId || 'Unknown'} · Global Model · Latest Prediction</p>
        </div>
        <div className={`border px-4 py-2 rounded-full text-xs font-semibold flex items-center gap-2 ${isHighRisk ? 'bg-red-50 border-red-200 text-red-700' : 'bg-emerald-50 border-emerald-200 text-emerald-700'}`}>
          <span className={`w-2 h-2 rounded-full animate-pulse ${isHighRisk ? 'bg-red-500' : 'bg-emerald-500'}`}></span>
          Predicted Risk: {riskScorePercentage}% {prediction?.riskLabel?.toUpperCase()}
        </div>
      </div>

      {/* TOP GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 relative z-10">
        
        {/* Left Card: SHAP Feature Attribution */}
        <div className="lg:col-span-7">
          <Card className="glass-card bg-white border-slate-200 h-full">
            <CardContent className="p-6 flex flex-col gap-6">
              <div className="flex justify-between items-center border-b border-slate-200 pb-4">
                <h2 className="text-lg font-semibold text-slate-900">SHAP Feature Attribution</h2>
                <div className="flex gap-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-blue-500 rounded-sm"></div>
                    <span>Decreases Risk</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-red-400 rounded-sm"></div>
                    <span>Increases Risk</span>
                  </div>
                </div>
              </div>

              <div className="relative w-full py-4 flex flex-col gap-2">
                {/* Central Axis */}
                <div className="absolute left-1/2 top-0 bottom-0 border-l border-dashed border-slate-300 z-0"></div>

                {/* Data Bars */}
                {shapData.length === 0 && (
                  <div className="text-center py-8 text-slate-600">No SHAP data available. Run a prediction first.</div>
                )}
                {shapData.map((item: any, i: number) => {
                  const type = item.value > 0 ? 'increase' : 'decrease';
                  const width = Math.min(Math.abs(item.value) * 200, 100); // Scale for visual width
                  return (
                  <div key={item.feature} className="relative z-10 flex items-center justify-center w-full py-2 hover:bg-slate-100 rounded transition-colors duration-150">
                    
                    {/* Left Side (Negative/Decrease) */}
                    <div className="w-1/2 flex justify-end pr-4 text-right relative h-8">
                      {type === 'decrease' ? (
                        <>
                          <motion.div 
                            initial={{ width: 0 }}
                            animate={{ width: `${width}%` }}
                            transition={{ duration: 0.8, delay: i * 0.15, ease: 'easeOut' }}
                            className="absolute right-4 top-1 bg-blue-500 h-6 rounded-l-md flex items-center justify-end pr-2"
                          >
                            <span className="font-mono text-[11px] text-white font-bold mr-1 drop-shadow-md">{item.value.toFixed(2)}</span>
                          </motion.div>
                          <span className="text-slate-800 text-sm mt-1.5 mr-[90px] z-20 whitespace-nowrap">{item.feature}</span>
                        </>
                      ) : (
                        <span className="text-slate-800 text-sm mt-1.5">{item.feature}</span>
                      )}
                    </div>

                    {/* Right Side (Positive/Increase) */}
                    <div className="w-1/2 flex justify-start relative h-8">
                      {type === 'increase' && (
                        <motion.div 
                          initial={{ width: 0 }}
                          animate={{ width: `${width}%` }}
                          transition={{ duration: 0.8, delay: i * 0.15, ease: 'easeOut' }}
                          className="bg-red-400 h-6 mt-1 rounded-r-md flex items-center pl-2"
                        >
                          <span className="font-mono text-[11px] text-white font-bold ml-2 drop-shadow-md">+{item.value.toFixed(2)}</span>
                        </motion.div>
                      )}
                    </div>
                    
                  </div>
                )})}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Card: AI Clinical Explanation */}
        <div className="lg:col-span-5 relative">
          <div className="animated-border h-full">
            <Card className="glass-card bg-white border-slate-200 h-full relative z-10 shadow-lg">
              <CardContent className="p-6 flex flex-col justify-between h-full">
                <div className="flex flex-col gap-4">
                  <div className="flex justify-between items-start">
                    <h2 className="text-lg font-semibold text-slate-900">AI Clinical Explanation</h2>
                    <BrainCircuit className="text-cyan-500 animate-pulse h-6 w-6" />
                  </div>
                  
                  <Badge className="bg-cyan-500/10 text-cyan-700 hover:bg-cyan-500/20 border-cyan-500/20 font-mono text-[11px] w-fit">
                    Narrative: LLM (if configured) or template
                  </Badge>

                  <div className="mt-4 p-5 bg-slate-50 rounded-lg border border-slate-200 relative overflow-hidden">
                    {/* Subtle gradient background inside the quote box */}
                    <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-cyan-500/5 pointer-events-none"></div>
                    <motion.p 
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 1, delay: 0.5 }}
                      className="text-[15px] italic text-slate-700 leading-relaxed font-light relative z-10"
                    >
                      {prediction?.nlpExplanation ? `"${prediction.nlpExplanation}"` : 'No explanation available. Run a prediction to generate one with LLaMA 3.'}
                    </motion.p>
                  </div>
                </div>

                <div className="mt-6 flex justify-between items-center text-[12px] font-mono text-slate-600 border-t border-slate-200 pt-4">
                  <span className="flex items-center gap-1">
                    <Timer className="h-4 w-4" /> Exact SHAP (all 2^13 coalitions)
                  </span>
                  <span onClick={() => navigate('/audit')} className="flex items-center gap-1 text-blue-500 hover:text-blue-700 cursor-pointer hover:underline font-sans font-medium">
                    View Full Log <ArrowRight className="h-3 w-3" />
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
        
      </div>
    </motion.div>
  );
}
