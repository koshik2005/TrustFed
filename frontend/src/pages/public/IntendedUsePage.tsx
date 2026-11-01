import React from 'react';
import { Badge } from '@/components/ui/badge';
import { ShieldAlert, CheckCircle2, XCircle, AlertTriangle, BookOpen } from 'lucide-react';

export default function IntendedUsePage() {
  return (
    <article className="prose prose-slate max-w-none text-slate-800 text-xs sm:text-sm leading-relaxed">
      {/* Notice Banner */}
      <div className="p-4 mb-6 rounded-xl bg-amber-50 border border-amber-300 text-amber-900 flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
        <div>
          <span className="font-bold block text-sm mb-0.5">DRAFT, pending legal review</span>
          <p className="text-xs text-amber-800 m-0 leading-normal">
            This document outlines the clinical scope, target audience, and boundaries of TrustFed.
          </p>
        </div>
      </div>

      <div className="border-b border-slate-200 pb-4 mb-6">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-900 mb-1">Intended Use Specification</h1>
        <p className="text-xs text-slate-500 m-0">
          Target Audience • Clinical Boundaries • Emergency Guidance
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-8">
        {/* WHO IT IS FOR */}
        <div className="p-5 rounded-2xl bg-emerald-50/60 border border-emerald-200 shadow-2xs">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            <h2 className="text-base font-bold text-emerald-950 m-0">Who It Is For</h2>
          </div>
          <ul className="space-y-2 text-xs text-emerald-900 pl-0 list-none m-0">
            <li className="flex items-start gap-2">
              <span className="font-bold text-emerald-700">•</span>
              <span><strong>Medical Students & Trainees:</strong> An interactive study tool to examine differential diagnosis probabilities, symptom presentations, and lab correlations.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="font-bold text-emerald-700">•</span>
              <span><strong>Clinical Informatics Researchers:</strong> Evaluating federated learning architectures (FedAvg), local differential privacy (DP-SGD), and missing value indicators.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="font-bold text-emerald-700">•</span>
              <span><strong>Healthcare Educators:</strong> Demonstrating explainable AI (SHAP attributions) and clinical safety red-flag rule mechanics.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="font-bold text-emerald-700">•</span>
              <span><strong>Consortium Evaluators:</strong> Reviewing prospective decision-support algorithms in exploratory shadow mode.</span>
            </li>
          </ul>
        </div>

        {/* WHAT IT IS NOT FOR */}
        <div className="p-5 rounded-2xl bg-rose-50/60 border border-rose-200 shadow-2xs">
          <div className="flex items-center gap-2 mb-3">
            <XCircle className="w-5 h-5 text-rose-600" />
            <h2 className="text-base font-bold text-rose-950 m-0">What It Is NOT For</h2>
          </div>
          <ul className="space-y-2 text-xs text-rose-900 pl-0 list-none m-0">
            <li className="flex items-start gap-2">
              <span className="font-bold text-rose-700">•</span>
              <span><strong>NOT for Primary Medical Diagnosis:</strong> Cannot substitute for professional history-taking, examinations, or lab cultures.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="font-bold text-rose-700">•</span>
              <span><strong>NOT a Certified Medical Device:</strong> Has not received CDSCO, FDA, or CE mark regulatory clearance as a Software as a Medical Device (SaMD).</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="font-bold text-rose-700">•</span>
              <span><strong>NOT for Consumer Self-Treatment:</strong> Must not be used by patients to self-medicate, alter doses, or bypass doctors.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="font-bold text-rose-700">•</span>
              <span><strong>NOT for Emergency Department Triage:</strong> Must never delay, gate, or replace standard emergency triage workflows.</span>
            </li>
          </ul>
        </div>
      </div>

      {/* Emergency Guidance */}
      <div className="p-5 rounded-2xl bg-red-50 border border-red-200 text-red-950 shadow-xs">
        <h3 className="text-sm font-bold flex items-center gap-2 text-red-900 mb-2 m-0">
          <AlertTriangle className="w-4 h-4 text-red-600" />
          Mandatory Emergency Medical Guidance
        </h3>
        <p className="text-xs text-red-800 m-0 leading-relaxed">
          In any acute medical situation involving sudden chest pain, difficulty breathing, stroke symptoms (facial droop, arm weakness, speech slurring), or high fever in infants, bypass TrustFed immediately and call local emergency services:
          <br />
          <strong>India: 112</strong> • <strong>United States / Canada: 911</strong> • <strong>United Kingdom: 999</strong> • <strong>European Union: 112</strong>.
        </p>
      </div>
    </article>
  );
}

