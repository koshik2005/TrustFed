import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { AlertTriangle, Sliders, Shield, Building2, Bell, Lock } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function SettingsPage() {
  const [rounds, setRounds] = useState([20]);
  const [epochs, setEpochs] = useState([1]);
  const [lr, setLr] = useState("0.1");
  const [batchSize, setBatchSize] = useState("8");
  const [minClients, setMinClients] = useState("3");

  const [epsilon, setEpsilon] = useState([1.0]);
  const [noise, setNoise] = useState([1.1]);
  const [maxNorm, setMaxNorm] = useState("1.0");
  const [agpm, setAgpm] = useState(true);
  const [he, setHe] = useState(false);
  const saveSettings = () => {
    localStorage.setItem('tf_settings', JSON.stringify({
      rounds: rounds[0], local_epochs: epochs[0], lr: parseFloat(lr), batch: parseInt(batchSize, 10),
      target_epsilon: epsilon[0], clip: parseFloat(maxNorm), secure_agg: agpm, he,
    }));
    alert('Saved. These settings apply to the next training session.');
  };

  // In a real app, this would check against initial state
  const hasUnsavedChanges = true;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col max-w-[1440px] mx-auto w-full pb-32 relative" // Extra bottom padding for sticky bar
    >
      {/* Background Ambient Glow */}
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[60vw] h-[60vh] rounded-full bg-blue-500/5 blur-[120px] pointer-events-none -z-10" />

      <div className="flex flex-col md:flex-row gap-8 w-full mt-4">
        
        {/* Left Nav (Sidebar) */}
        <aside className="w-full md:w-[240px] shrink-0">
          <Card className="glass-card bg-white border-slate-200 sticky top-28">
            <CardContent className="p-4">
              <h2 className="text-lg font-bold text-slate-900 mb-4 px-2">Settings</h2>
              <nav className="flex flex-col gap-1">
                <a href="#" className="px-3 py-2 rounded-lg bg-blue-500/10 border-l-4 border-blue-500 text-slate-900 font-medium flex items-center gap-3 transition-colors">
                  <Sliders className="w-4 h-4 text-blue-400" /> FL Parameters
                </a>
                <a href="#" className="px-3 py-2 rounded-lg text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors flex items-center gap-3">
                  <Shield className="w-4 h-4" /> Privacy Config
                </a>
                <a href="#" className="px-3 py-2 rounded-lg text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors flex items-center gap-3">
                  <Building2 className="w-4 h-4" /> Hospital Config
                </a>
                <a href="#" className="px-3 py-2 rounded-lg text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors flex items-center gap-3">
                  <Bell className="w-4 h-4" /> Notifications
                </a>
                <a href="#" className="px-3 py-2 rounded-lg text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors flex items-center gap-3">
                  <Lock className="w-4 h-4" /> Security
                </a>
              </nav>
            </CardContent>
          </Card>
        </aside>

        {/* Right Content */}
        <div className="flex-1 max-w-3xl">
          
          {/* FL Parameters Section */}
          <div className="mb-10">
            <div className="mb-6">
              <h2 className="text-[20px] font-bold text-slate-900">Federated Learning Parameters</h2>
              <p className="text-sm text-slate-600 mt-1">Configure the global FL training session</p>
            </div>
            
            <Card className="glass-card bg-white border-slate-200">
              <CardContent className="p-6 flex flex-col gap-6">
                
                {/* Row 1 */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-slate-200 gap-4">
                  <div className="sm:max-w-[60%]">
                    <Label className="block text-slate-900 font-medium text-base mb-1">Number of Rounds</Label>
                    <span className="text-[13px] text-slate-600">Total global communication rounds</span>
                  </div>
                  <div className="flex items-center gap-4 sm:w-[40%]">
                    <Slider value={rounds} onValueChange={(v) => setRounds(v as number[])} max={100} min={1} step={1} className="w-full" />
                    <span className="bg-blue-500/20 text-blue-400 px-3 py-1 rounded text-sm font-mono border border-blue-500/30 min-w-[3rem] text-center">
                      {rounds[0]}
                    </span>
                  </div>
                </div>

                {/* Row 2 */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-slate-200 gap-4">
                  <div className="sm:max-w-[60%]">
                    <Label className="block text-slate-900 font-medium text-base mb-1">Local Epochs</Label>
                    <span className="text-[13px] text-slate-600">Training iterations per hospital per round</span>
                  </div>
                  <div className="flex items-center gap-4 sm:w-[40%]">
                    <Slider value={epochs} onValueChange={(v) => setEpochs(v as number[])} max={20} min={1} step={1} className="w-full" />
                    <span className="bg-blue-500/20 text-blue-400 px-3 py-1 rounded text-sm font-mono border border-blue-500/30 min-w-[3rem] text-center">
                      {epochs[0]}
                    </span>
                  </div>
                </div>

                {/* Row 3 */}
                <div className="flex items-center justify-between pb-6 border-b border-slate-200">
                  <Label className="text-slate-900 font-medium text-base">Learning Rate</Label>
                  <Input type="number" step="0.001" value={lr} onChange={(e) => setLr(e.target.value)} className="w-24 bg-white border-slate-200 text-slate-900 font-mono text-right focus:border-blue-500" />
                </div>

                {/* Row 4 */}
                <div className="flex items-center justify-between pb-6 border-b border-slate-200">
                  <Label className="text-slate-900 font-medium text-base">Batch Size</Label>
                  <Input type="number" value={batchSize} onChange={(e) => setBatchSize(e.target.value)} className="w-24 bg-white border-slate-200 text-slate-900 font-mono text-right focus:border-blue-500" />
                </div>

                {/* Row 5 */}
                <div className="flex items-center justify-between">
                  <Label className="text-slate-900 font-medium text-base">Min Clients per Round</Label>
                  <Input type="number" value={minClients} onChange={(e) => setMinClients(e.target.value)} className="w-24 bg-white border-slate-200 text-slate-900 font-mono text-right focus:border-blue-500" />
                </div>

              </CardContent>
            </Card>
          </div>

          {/* Privacy Configuration Section */}
          <div>
            <div className="mb-6">
              <h2 className="text-[20px] font-bold text-slate-900">Privacy Configuration</h2>
            </div>
            
            <Card className="glass-card bg-white border-slate-200">
              <CardContent className="p-6 flex flex-col gap-6">
                
                {/* Row 6 */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-slate-200 gap-4">
                  <Label className="sm:max-w-[60%] text-slate-900 font-medium text-base">Target Epsilon (ε) — noise is calibrated to meet it</Label>
                  <div className="flex items-center gap-4 sm:w-[40%]">
                    <Slider value={epsilon} onValueChange={(v) => setEpsilon(v as number[])} max={5.0} min={0.5} step={0.1} className="w-full" />
                    <span className="bg-emerald-500/20 text-emerald-400 px-3 py-1 rounded text-sm font-mono border border-emerald-500/30 min-w-[3.5rem] text-center">
                      {epsilon[0].toFixed(1)}
                    </span>
                  </div>
                </div>

                {/* Row 7 */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-slate-200 gap-4">
                  <Label className="sm:max-w-[60%] text-slate-900 font-medium text-base">Noise Multiplier (σ) — auto-calibrated</Label>
                  <div className="flex items-center gap-4 sm:w-[40%]">
                    <Slider disabled value={noise} onValueChange={(v) => setNoise(v as number[])} max={8.0} min={0.5} step={0.1} className="w-full" />
                    <span className="bg-blue-500/20 text-blue-400 px-3 py-1 rounded text-sm font-mono border border-blue-500/30 min-w-[3.5rem] text-center">
                      auto
                    </span>
                  </div>
                </div>

                {/* Row 8 */}
                <div className="flex items-center justify-between pb-6 border-b border-slate-200">
                  <Label className="text-slate-900 font-medium text-base">Max Gradient Norm</Label>
                  <Input type="number" step="0.1" value={maxNorm} onChange={(e) => setMaxNorm(e.target.value)} className="w-24 bg-white border-slate-200 text-slate-900 font-mono text-right focus:border-blue-500" />
                </div>

                {/* Row 9 */}
                <div className="flex items-center justify-between pb-6 border-b border-slate-200">
                  <Label className="text-slate-900 font-medium text-base cursor-pointer" htmlFor="agpm">Secure aggregation (additive secret sharing)</Label>
                  <Switch id="agpm" checked={agpm} onCheckedChange={setAgpm} className="data-[state=checked]:bg-cyan-400" />
                </div>

                {/* Row 10 */}
                <div className="flex items-center justify-between">
                  <Label className="text-slate-900 font-medium text-base cursor-pointer" htmlFor="he">Enable Paillier HE</Label>
                  <Switch id="he" checked={he} onCheckedChange={setHe} className="data-[state=checked]:bg-blue-500" />
                </div>

              </CardContent>
            </Card>
          </div>
          
        </div>
      </div>

      {/* Sticky Bottom Bar */}
      {hasUnsavedChanges && (
        <motion.div 
          initial={{ y: 50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className="fixed bottom-0 left-0 w-full border-t border-slate-200 py-4 z-40 bg-white/95 backdrop-blur-xl shadow-2xl"
        >
          {/* Use the same max-w container but pad the left to align with the main content area (nav offset) */}
          <div className="max-w-[1440px] mx-auto w-full px-4 md:px-12 flex flex-col sm:flex-row justify-between items-center gap-4">
            <div className="flex items-center gap-2 text-amber-600 font-semibold text-sm md:ml-[260px]">
              <AlertTriangle className="w-4 h-4 text-amber-500" /> Unsaved Changes
            </div>
            <div className="flex gap-4">
              <Button variant="outline" className="border-slate-300 text-slate-700 hover:text-slate-900 hover:bg-slate-100 transition-all">
                Reset to Defaults
              </Button>
              <Button onClick={saveSettings} className="bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-semibold shadow-md hover:brightness-105 transition-all border-none">
                Deploy Configuration
              </Button>
            </div>
          </div>
        </motion.div>
      )}
      
    </motion.div>
  );
}
