import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { AlertTriangle, Sliders, Shield, Building2, Bell, Lock, KeyRound, ShieldCheck, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import apiClient from '@/services/apiClient';
import { useAuthStore } from '@/store/authStore';

const NAV_ITEMS = [
  { id: 'fl-params', label: 'FL Parameters', icon: Sliders },
  { id: 'privacy', label: 'Privacy Config', icon: Shield },
  { id: 'hospital', label: 'Hospital Config', icon: Building2 },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'security', label: 'Security', icon: Lock },
];

export default function SettingsPage() {
  const [activeSection, setActiveSection] = useState('fl-params');
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

  // MFA State
  const currentUser = useAuthStore((s) => s.user);
  const [mfaStep, setMfaStep] = useState<'initial' | 'setup' | 'enabled'>(
    currentUser?.mfaEnabled ? 'enabled' : 'initial'
  );
  const [mfaSecret, setMfaSecret] = useState('');
  const [mfaCode, setMfaCode] = useState('');
  const [mfaRecoveryCodes, setMfaRecoveryCodes] = useState<string[]>([]);
  const [mfaLoading, setMfaLoading] = useState(false);
  const [mfaError, setMfaError] = useState('');

  const handleStartMfaSetup = async () => {
    setMfaLoading(true);
    setMfaError('');
    try {
      const res = await apiClient.post<{ secret: string; otpauth_uri: string }>('/auth/mfa/setup');
      setMfaSecret(res.data.secret);
      setMfaStep('setup');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to initiate MFA setup';
      setMfaError(msg);
    } finally {
      setMfaLoading(false);
    }
  };

  const handleVerifyMfa = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!mfaCode || mfaCode.length < 6) {
      setMfaError('Please enter a valid 6-digit TOTP code.');
      return;
    }
    setMfaLoading(true);
    setMfaError('');
    try {
      const res = await apiClient.post<{ mfa_enabled: boolean; recovery_codes: string[] }>('/auth/mfa/enable', {
        code: mfaCode.trim()
      });
      setMfaRecoveryCodes(res.data.recovery_codes || []);
      setMfaStep('enabled');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Invalid MFA code. Verification failed.';
      setMfaError(msg);
    } finally {
      setMfaLoading(false);
    }
  };

  const saveSettings = () => {
    localStorage.setItem('tf_settings', JSON.stringify({
      rounds: rounds[0], local_epochs: epochs[0], lr: parseFloat(lr), batch: parseInt(batchSize, 10),
      target_epsilon: epsilon[0], clip: parseFloat(maxNorm), secure_agg: agpm, he,
    }));
    alert('Saved. These settings apply to the next training session.');
  };

  // In a real app, this would check against initial state
  const hasUnsavedChanges = true;

  const scrollToSection = (id: string) => {
    setActiveSection(id);
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

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
                {NAV_ITEMS.map((item) => {
                  const Icon = item.icon;
                  const isActive = activeSection === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => scrollToSection(item.id)}
                      className={cn(
                        "px-3 py-2 rounded-lg flex items-center gap-3 transition-colors text-left w-full",
                        isActive
                          ? "bg-blue-50 border-l-4 border-blue-500 text-slate-900 font-medium"
                          : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 border-l-4 border-transparent"
                      )}
                    >
                      <Icon className={cn("w-4 h-4", isActive ? "text-blue-500" : "text-slate-400")} />
                      {item.label}
                    </button>
                  );
                })}
              </nav>
            </CardContent>
          </Card>
        </aside>

        {/* Right Content */}
        <div className="flex-1 max-w-3xl">
          
          {/* FL Parameters Section */}
          <div id="fl-params" className="mb-10 scroll-mt-20">
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
                    <span className="bg-blue-50 text-blue-700 px-3 py-1 rounded text-sm font-mono border border-blue-200 min-w-[3rem] text-center">
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
                    <span className="bg-blue-50 text-blue-700 px-3 py-1 rounded text-sm font-mono border border-blue-200 min-w-[3rem] text-center">
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
          <div id="privacy" className="mb-10 scroll-mt-20">
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
                    <span className="bg-emerald-50 text-emerald-700 px-3 py-1 rounded text-sm font-mono border border-emerald-200 min-w-[3.5rem] text-center">
                      {epsilon[0].toFixed(1)}
                    </span>
                  </div>
                </div>

                {/* Row 7 */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-slate-200 gap-4">
                  <Label className="sm:max-w-[60%] text-slate-900 font-medium text-base">Noise Multiplier (σ) — auto-calibrated</Label>
                  <div className="flex items-center gap-4 sm:w-[40%]">
                    <Slider disabled value={noise} onValueChange={(v) => setNoise(v as number[])} max={8.0} min={0.5} step={0.1} className="w-full" />
                    <span className="bg-blue-50 text-blue-700 px-3 py-1 rounded text-sm font-mono border border-blue-200 min-w-[3.5rem] text-center">
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
                  <Switch id="agpm" checked={agpm} onCheckedChange={setAgpm} className="data-[state=checked]:bg-cyan-500" />
                </div>

                {/* Row 10 */}
                <div className="flex items-center justify-between">
                  <Label className="text-slate-900 font-medium text-base cursor-pointer" htmlFor="he">Enable Paillier HE</Label>
                  <Switch id="he" checked={he} onCheckedChange={setHe} className="data-[state=checked]:bg-blue-500" />
                </div>

              </CardContent>
            </Card>
          </div>

          {/* Hospital Config — placeholder section */}
          <div id="hospital" className="mb-10 scroll-mt-20">
            <div className="mb-6">
              <h2 className="text-[20px] font-bold text-slate-900">Hospital Configuration</h2>
              <p className="text-sm text-slate-600 mt-1">Manage connected hospital nodes</p>
            </div>
            <Card className="glass-card bg-white border-slate-200">
              <CardContent className="p-8 text-center text-slate-500 text-sm">
                Hospital node configuration is managed automatically by the federated orchestrator. Visit the <span className="text-blue-600 font-medium">Regional Hub</span> page to view connected nodes.
              </CardContent>
            </Card>
          </div>

          {/* Notifications — placeholder section */}
          <div id="notifications" className="mb-10 scroll-mt-20">
            <div className="mb-6">
              <h2 className="text-[20px] font-bold text-slate-900">Notifications</h2>
              <p className="text-sm text-slate-600 mt-1">Configure alerts and notifications</p>
            </div>
            <Card className="glass-card bg-white border-slate-200">
              <CardContent className="p-8 text-center text-slate-500 text-sm">
                Notification preferences will be available in a future release.
              </CardContent>
            </Card>
          </div>

          {/* Security & Multi-Factor Authentication Section */}
          <div id="security" className="scroll-mt-20">
            <div className="mb-6">
              <h2 className="text-[20px] font-bold text-slate-900">Security & Authentication</h2>
              <p className="text-sm text-slate-600 mt-1">Multi-Factor Authentication (TOTP) and access control</p>
            </div>
            
            <Card className="glass-card bg-white border-slate-200">
              <CardContent className="p-6 flex flex-col gap-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                      <KeyRound className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-base font-semibold text-slate-900">Two-Factor Authentication (TOTP)</h3>
                      <p className="text-xs text-slate-500">RFC 6238 time-based one-time password security</p>
                    </div>
                  </div>
                  {mfaStep === 'enabled' ? (
                    <span data-testid="mfa-active-badge" className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      Active & Enforced
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                      Optional / Not Enforced
                    </span>
                  )}
                </div>

                {mfaError && (
                  <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-xs text-red-700">
                    {mfaError}
                  </div>
                )}

                {/* Step 1: Initial Prompt */}
                {mfaStep === 'initial' && (
                  <div className="flex flex-col gap-4 border-t border-slate-100 pt-4">
                    <p className="text-xs text-slate-600 leading-relaxed">
                      Protect your privileged clinical account by linking an authenticator app (such as Google Authenticator, Authy, or 1Password). Once enrolled, logins will require a 6-digit TOTP code.
                    </p>
                    <div>
                      <Button
                        type="button"
                        data-testid="mfa-setup-btn"
                        onClick={handleStartMfaSetup}
                        disabled={mfaLoading}
                        className="bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs h-9 px-4 rounded-lg shadow-xs"
                      >
                        {mfaLoading ? 'Generating TOTP Secret...' : 'Begin MFA Enrollment'}
                      </Button>
                    </div>
                  </div>
                )}

                {/* Step 2: Secret & Verification Code Input */}
                {mfaStep === 'setup' && (
                  <form onSubmit={handleVerifyMfa} className="flex flex-col gap-4 border-t border-slate-100 pt-4">
                    <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col gap-2">
                      <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                        1. Add Secret Key to Authenticator App
                      </span>
                      <div className="flex items-center gap-2">
                        <code data-testid="mfa-secret-code" className="font-mono text-sm font-bold text-slate-800 bg-white px-3 py-1.5 rounded-lg border border-slate-200 select-all">
                          {mfaSecret}
                        </code>
                      </div>
                      <p className="text-[11px] text-slate-500">
                        Enter this 32-character key manually into your TOTP app or password vault.
                      </p>
                    </div>

                    <div className="flex flex-col gap-2">
                      <Label htmlFor="mfa-code-input" className="text-xs font-semibold text-slate-700">
                        2. Enter 6-digit Verification Code
                      </Label>
                      <div className="flex items-center gap-3">
                        <Input
                          id="mfa-code-input"
                          data-testid="mfa-code-input"
                          type="text"
                          placeholder="e.g. 123456"
                          maxLength={6}
                          value={mfaCode}
                          onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, ''))}
                          className="w-48 font-mono text-center tracking-widest text-base h-10 border-slate-300"
                        />
                        <Button
                          type="submit"
                          data-testid="mfa-verify-btn"
                          disabled={mfaLoading || mfaCode.length < 6}
                          className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs h-10 px-5 rounded-lg shadow-xs"
                        >
                          {mfaLoading ? 'Verifying...' : 'Confirm & Activate MFA'}
                        </Button>
                      </div>
                    </div>
                  </form>
                )}

                {/* Step 3: Enrolled & Recovery Codes Display */}
                {mfaStep === 'enabled' && (
                  <div className="flex flex-col gap-4 border-t border-slate-100 pt-4">
                    <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 flex flex-col gap-3">
                      <div className="flex items-center gap-2 text-emerald-900 font-semibold text-xs">
                        <ShieldCheck className="w-4 h-4 text-emerald-600" />
                        MFA Enrollment Confirmed — Single-Use Recovery Codes
                      </div>
                      <p className="text-[11px] text-emerald-800 leading-relaxed">
                        Save these 8 recovery codes in a secure location. If you lose access to your authenticator device, each code can be used exactly once to restore access.
                      </p>
                      {mfaRecoveryCodes.length > 0 && (
                        <div data-testid="mfa-recovery-codes-grid" className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 font-mono text-xs">
                          {mfaRecoveryCodes.map((rc, idx) => (
                            <span key={idx} className="bg-white border border-emerald-300 text-slate-800 px-2.5 py-1 rounded text-center font-bold">
                              {rc}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}
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

