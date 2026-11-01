import React from 'react';
import { Badge } from '@/components/ui/badge';
import { ShieldAlert, AlertTriangle, PhoneCall, Stethoscope, HeartPulse } from 'lucide-react';

export default function MedicalDisclaimerPage() {
  return (
    <article className="prose prose-slate max-w-none text-slate-800 text-xs sm:text-sm leading-relaxed">
      {/* Notice Banner */}
      <div className="p-4 mb-6 rounded-xl bg-amber-50 border border-amber-300 text-amber-900 flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
        <div>
          <span className="font-bold block text-sm mb-0.5">DRAFT, pending legal review</span>
          <p className="text-xs text-amber-800 m-0 leading-normal">
            This disclaimer applies universally across all algorithmic differentials, explanations, red-flag alerts, and recommendations produced by TrustFed.
          </p>
        </div>
      </div>

      <div className="border-b border-slate-200 pb-4 mb-6">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-900 mb-1">Medical & Safety Disclaimer</h1>
        <p className="text-xs text-slate-500 m-0">
          Educational Decision Support Prototype • Not a Certified Medical Device • Not Medical Advice
        </p>
      </div>

      {/* Emergency Guidance Callout */}
      <div className="p-5 mb-8 rounded-2xl bg-red-50 border-2 border-red-300 text-red-950 shadow-xs">
        <div className="flex items-center gap-2 mb-2 font-bold text-base text-red-900">
          <PhoneCall className="w-5 h-5 text-red-600" />
          Immediate Emergency Medical Guidance
        </div>
        <p className="text-xs sm:text-sm text-red-900 leading-relaxed mb-3">
          <strong>IF YOU OR SOMEONE AROUND YOU IS EXPERIENCING A MEDICAL EMERGENCY, DO NOT RELY ON THIS SERVICE.</strong>
          <br />
          Immediately call emergency medical dispatch or go to the nearest emergency room:
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs font-bold text-red-950">
          <div className="p-2.5 rounded-xl bg-white border border-red-200 shadow-2xs">
            <span className="text-slate-500 block text-[10px] uppercase font-normal">India</span>
            <span className="text-base text-red-700">112</span>
          </div>
          <div className="p-2.5 rounded-xl bg-white border border-red-200 shadow-2xs">
            <span className="text-slate-500 block text-[10px] uppercase font-normal">US & Canada</span>
            <span className="text-base text-red-700">911</span>
          </div>
          <div className="p-2.5 rounded-xl bg-white border border-red-200 shadow-2xs">
            <span className="text-slate-500 block text-[10px] uppercase font-normal">United Kingdom</span>
            <span className="text-base text-red-700">999</span>
          </div>
          <div className="p-2.5 rounded-xl bg-white border border-red-200 shadow-2xs">
            <span className="text-slate-500 block text-[10px] uppercase font-normal">European Union</span>
            <span className="text-base text-red-700">112</span>
          </div>
        </div>
      </div>

      <section className="space-y-6">
        <div>
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 mb-2">
            <Stethoscope className="w-4 h-4 text-blue-600" />
            1. Educational Prototype Benchmark — Not a Diagnostic Medical Device
          </h2>
          <p>
            TrustFed is an algorithmic machine learning decision-support prototype. It has <strong>NOT been cleared, certified, or registered by any medical device authority</strong> (such as the Central Drugs Standard Control Organisation - CDSCO in India, the US Food and Drug Administration - FDA, or the European Medicines Agency - EMA) as a Software as a Medical Device (SaMD).
          </p>
          <p>
            It is provided strictly as an educational and research exploration platform for evaluating federated learning algorithms, differential probability distributions, and clinical feature attributions.
          </p>
        </div>

        <div>
          <h2 className="text-base font-bold text-slate-900 mb-2">
            2. No Healthcare Advice or Doctor-Patient Relationship
          </h2>
          <ul className="list-disc pl-5 space-y-1.5 text-xs sm:text-sm">
            <li>TrustFed does <strong>NOT</strong> provide medical advice, diagnosis, treatment, prognosis, or prescription.</li>
            <li>Use of this platform does <strong>NOT</strong> establish a physician-patient, nurse-patient, or confidential healthcare relationship.</li>
            <li>Algorithmic differential predictions are computational heuristics based on synthetic and public benchmark data ($N=1,080$) and must never substitute for clinical acumen, physical examinations, laboratory cultures, or imaging.</li>
          </ul>
        </div>

        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
          <h3 className="text-sm font-bold text-slate-900 mb-1.5 flex items-center gap-2">
            <HeartPulse className="w-4 h-4 text-amber-600" />
            3. All Thresholds & Guidance Labeled "Pending Physician Review"
          </h3>
          <p className="text-xs text-slate-600 mb-2">
            All numerical vital thresholds evaluated by our safety engine are conservative heuristics labeled <strong>"Pending Physician Review"</strong>:
          </p>
          <ul className="grid grid-cols-1 sm:grid-cols-2 gap-1 text-xs text-slate-600 list-disc pl-5">
            <li>Hypoxia: SpO2 &lt; 92.0%</li>
            <li>Tachycardia: HR ≥ 120 bpm (with dual signs)</li>
            <li>Bradycardia: HR &lt; 40 bpm</li>
            <li>Hypotension: Systolic BP &lt; 90 mmHg</li>
            <li>Hypertensive Crisis: BP ≥ 180/120 mmHg</li>
            <li>Infant Pyrexia: Temp ≥ 38.5°C in age ≤ 1 yr</li>
          </ul>
          <p className="text-[11px] text-slate-500 mt-2 m-0">
            These thresholds have not undergone randomized controlled clinical trials and must be reviewed, calibrated, and confirmed by an attending physician.
          </p>
        </div>
      </section>
    </article>
  );
}

