import React from 'react';
import { Badge } from '@/components/ui/badge';
import { ShieldAlert, Scale, AlertTriangle, FileText } from 'lucide-react';

export default function TermsPage() {
  return (
    <article className="prose prose-slate max-w-none text-slate-800 text-xs sm:text-sm leading-relaxed">
      {/* Notice Banner */}
      <div className="p-4 mb-6 rounded-xl bg-amber-50 border border-amber-300 text-amber-900 flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
        <div>
          <span className="font-bold block text-sm mb-0.5">DRAFT, pending legal review</span>
          <p className="text-xs text-amber-800 m-0 leading-normal">
            This document is an operational policy draft prepared for prototype service review. It does NOT constitute formal legal advice.
          </p>
        </div>
      </div>

      <div className="border-b border-slate-200 pb-4 mb-6">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-900 mb-1">Terms of Use</h1>
        <p className="text-xs text-slate-500 m-0">
          Last Updated: November 2026 • Platform Mode: Informational / Educational Prototype
        </p>
      </div>

      <section className="space-y-4">
        <div>
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 mb-2">
            <Scale className="w-4 h-4 text-blue-600" />
            1. Acceptance of Terms
          </h2>
          <p>
            By accessing, browsing, or utilizing the TrustFed platform ("TrustFed", "Service", "Platform"), you acknowledge and agree to be bound by these Terms of Use ("Terms"). If you do not agree to these Terms, you must immediately cease all access and use of the platform.
          </p>
        </div>

        <div>
          <h2 className="text-base font-bold text-slate-900 mb-2">
            2. Informational & Educational Decision Support Only
          </h2>
          <ul className="list-disc pl-5 space-y-1.5 text-xs sm:text-sm">
            <li>
              <strong>Non-Diagnostic Prototype:</strong> TrustFed is an experimental research and educational clinical decision-support benchmark developed to explore federated machine learning, differential triage heuristics, and privacy-preserving algorithms.
            </li>
            <li>
              <strong>Not a Medical Device or Licensed Service:</strong> TrustFed is NOT a licensed healthcare provider, diagnostic clinic, or certified medical device.
            </li>
            <li>
              <strong>No Doctor-Patient Relationship:</strong> Your use of this service does not establish a physician-patient, advisory, fiduciary, or confidential healthcare relationship.
            </li>
            <li>
              <strong>Mandatory Clinician Verification:</strong> All differential diagnoses, clinical probabilities, and suggested remedies are tentative prototype outputs labeled <em>"Pending Physician Review"</em>. They must be verified independently by a licensed medical practitioner.
            </li>
          </ul>
        </div>

        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-950">
          <h3 className="text-sm font-bold flex items-center gap-2 text-red-900 mb-1">
            <AlertTriangle className="w-4 h-4 text-red-600" />
            3. Medical Emergency Guidance
          </h3>
          <p className="text-xs text-red-800 m-0 leading-relaxed">
            <strong>Do not use TrustFed in a medical emergency.</strong> If you believe you or someone else is suffering from a life-threatening medical emergency (e.g. acute chest pain, sudden weakness, shortness of breath, high infant fever), immediately contact your local emergency services:
            <br />
            <strong>India: 112</strong> • <strong>United States / Canada: 911</strong> • <strong>United Kingdom: 999</strong> • <strong>European Union: 112</strong>.
          </p>
        </div>

        <div>
          <h2 className="text-base font-bold text-slate-900 mb-2">
            4. User Eligibility & Permitted Use
          </h2>
          <ul className="list-disc pl-5 space-y-1.5 text-xs sm:text-sm">
            <li>The platform is intended exclusively for educational, academic, and research exploration by medical educators, trainees, healthcare informaticians, and data science researchers.</li>
            <li>You must <strong>NOT</strong> use TrustFed as the sole or primary basis for prescribing medication, initiating surgical procedures, or altering patient therapy.</li>
            <li>You must <strong>NOT</strong> enter real patient personally identifiable information (PII) or protected health information (PHI) while the platform operates in Informational Mode.</li>
            <li>You must <strong>NOT</strong> attempt to reverse-engineer, de-anonymize, or reconstruct individual patient records from public or synthetic benchmark datasets.</li>
          </ul>
        </div>

        <div>
          <h2 className="text-base font-bold text-slate-900 mb-2">
            5. Disclaimer of Warranties & Limitation of Liability
          </h2>
          <p className="text-xs uppercase text-slate-500 font-semibold mb-1">
            Provided strictly "AS IS" and "AS AVAILABLE"
          </p>
          <p>
            THE SERVICE IS PROVIDED WITHOUT WARRANTIES OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, CLINICAL ACCURACY, OR NON-INFRINGEMENT. IN NO EVENT SHALL TRUSTFED OR ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, OR CONSEQUENTIAL DAMAGES ARISING FROM THE USE OF OR RELIANCE UPON PLATFORM OUTPUTS.
          </p>
        </div>

        <div>
          <h2 className="text-base font-bold text-slate-900 mb-2">
            6. Governing Law & Jurisdiction
          </h2>
          <p>
            These Terms shall be governed by and construed in accordance with the laws of India. Any dispute arising out of or related to these Terms shall be subject to the exclusive jurisdiction of the competent courts in Bengaluru, Karnataka, India [Corporate Placeholder].
          </p>
        </div>
      </section>
    </article>
  );
}

