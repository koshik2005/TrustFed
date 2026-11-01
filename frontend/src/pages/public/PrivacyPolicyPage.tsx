import React from 'react';
import { Badge } from '@/components/ui/badge';
import { ShieldAlert, ShieldCheck, Cookie, Lock, Database, AlertCircle } from 'lucide-react';

export default function PrivacyPolicyPage() {
  return (
    <article className="prose prose-slate max-w-none text-slate-800 text-xs sm:text-sm leading-relaxed">
      {/* Notice Banner */}
      <div className="p-4 mb-6 rounded-xl bg-amber-50 border border-amber-300 text-amber-900 flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
        <div>
          <span className="font-bold block text-sm mb-0.5">DRAFT, pending legal review</span>
          <p className="text-xs text-amber-800 m-0 leading-normal">
            This Privacy Policy outlines current operational practices for our prototype service. It does NOT claim certified statutory compliance (such as DPDP or HIPAA).
          </p>
        </div>
      </div>

      <div className="border-b border-slate-200 pb-4 mb-6">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-900 mb-1">Privacy Policy</h1>
        <p className="text-xs text-slate-500 m-0">
          Last Updated: November 2026 • Dual-Mode Architecture Specification
        </p>
      </div>

      {/* ── SECTION 1: INFORMATIONAL MODE (ACTIVE) ── */}
      <section className="mb-8 p-5 rounded-2xl bg-blue-50/50 border border-blue-200">
        <div className="flex items-center justify-between gap-2 mb-3">
          <h2 className="text-base font-bold text-blue-950 flex items-center gap-2 m-0">
            <ShieldCheck className="w-5 h-5 text-blue-600" />
            1. Informational Mode: Data Practices [CURRENTLY ACTIVE]
          </h2>
          <Badge className="bg-blue-600 text-white text-[10px] uppercase font-bold">
            Active Mode
          </Badge>
        </div>
        <p className="text-blue-900 text-xs mb-4">
          TrustFed operates by default in <strong>Informational Mode</strong> for educational and research exploration. In this mode, no patient identifiable information (PII) or protected health records (PHI) are accepted or stored.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-3.5 rounded-xl bg-white border border-blue-100 shadow-2xs">
            <span className="font-bold text-slate-900 block mb-1.5 flex items-center gap-1.5">
              <span className="text-emerald-600">✓</span> What Is Collected (Anonymous Metrics Only)
            </span>
            <ul className="list-disc pl-4 space-y-1 text-slate-600">
              <li><strong>Broad Age Integer:</strong> Age number for differential triage rules.</li>
              <li><strong>Biological Sex Indicator:</strong> Binary/category token (Male/Female/Other).</li>
              <li><strong>Selected Symptoms:</strong> Standardized tokens (e.g. <code>fever</code>, <code>cough</code>).</li>
              <li><strong>Optional Vitals:</strong> Numerical values (e.g. Temp, BP, HR, SpO2).</li>
              <li><strong>System Telemetry:</strong> Anonymized request IDs and latency percentiles.</li>
            </ul>
          </div>

          <div className="p-3.5 rounded-xl bg-white border border-blue-100 shadow-2xs">
            <span className="font-bold text-slate-900 block mb-1.5 flex items-center gap-1.5">
              <span className="text-red-600">✗</span> What Is NOT Collected (Strictly Blocked)
            </span>
            <ul className="list-disc pl-4 space-y-1 text-slate-600">
              <li><strong>NO Patient Names:</strong> Names and initials are completely blocked.</li>
              <li><strong>NO Contact Numbers:</strong> No phones, email IDs, or addresses.</li>
              <li><strong>NO Government IDs:</strong> No Aadhaar, SSN, or national health IDs.</li>
              <li><strong>NO Real Hospital MRNs:</strong> No real clinical record identifiers.</li>
              <li><strong>NO Re-Identifiable Data:</strong> No linkable patient profiles.</li>
            </ul>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-blue-100 text-xs text-blue-900 space-y-1.5">
          <p className="m-0">
            <strong>Retention & Purging:</strong> Symptom inputs and vital calculations are processed ephemerally in-memory during inference and discarded upon response delivery. Server logs use automated redaction filters to scrub any accidental identifiers.
          </p>
          <p className="m-0">
            <strong>User Rights (Informational Mode):</strong> Because no individual patient records are stored, there are no personal health records linkable to you. Administrative account holders may request inspection, rotation, or deletion of their credentials.
          </p>
        </div>
      </section>

      {/* ── SECTION 2: STAFF & ADMINISTRATIVE ACCOUNT DATA ── */}
      <section className="mb-8 p-5 rounded-2xl bg-white border border-slate-200">
        <h2 className="text-base font-bold text-slate-900 mb-2">
          2. Platform Accounts & Staff Data Processing
        </h2>
        <p className="text-xs text-slate-600 mb-3">
          While anonymous public decision support collects zero patient data, authorized healthcare personnel and system administrators have provisioned operational accounts. The following operational account data is processed:
        </p>
        <ul className="list-disc pl-5 space-y-1.5 text-xs text-slate-700">
          <li><strong>Staff Identity & Roles:</strong> Work email addresses and assigned role tiers (<code>global_admin</code>, <code>regional_admin</code>, <code>doctor</code>, <code>hospital_staff</code>) for role-based access control.</li>
          <li><strong>Authentication Credentials:</strong> Passwords hashed with <code>bcrypt</code> (work factor 12). Plaintext passwords are never stored or logged.</li>
          <li><strong>MFA Credentials:</strong> TOTP Base32 secrets stored encrypted; single-use emergency recovery codes hashed using SHA-256.</li>
          <li><strong>Immutable Audit Trail:</strong> High-risk administrative actions (user provisioning, soft deletions, password changes, model checkpoint promotions) record the acting user ID and timestamp in an append-only audit ledger.</li>
          <li><strong>Ephemeral Network Identifiers:</strong> IP addresses are inspected in-memory by rate limiters (SlowAPI) to prevent denial of service and brute-force attacks, and are never attached to public decision-support queries.</li>
          <li><strong>Retention Policy:</strong> Account records remain active while the personnel is affiliated with their hospital node. Soft-deleted accounts enter a 30-day retention grace period before permanent purging.</li>
        </ul>
      </section>

      {/* ── SECTION 3: ESSENTIAL COOKIES ONLY ── */}
      <section className="mb-8 p-4 rounded-xl bg-slate-50 border border-slate-200">
        <h2 className="text-sm sm:text-base font-bold text-slate-900 flex items-center gap-2 mb-2">
          <Cookie className="w-4 h-4 text-slate-600" />
          3. Essential Cookies Notice & Technical Attributes
        </h2>
        <p className="text-xs text-slate-600 mb-2">
          TrustFed uses <strong>strictly essential cookies</strong> required for application security and session integrity. The deployed environment sets:
        </p>
        <div className="overflow-x-auto text-xs my-3">
          <table className="w-full border-collapse border border-slate-200 text-left">
            <thead className="bg-slate-100 text-slate-700">
              <tr>
                <th className="p-2 border border-slate-200">Cookie Name</th>
                <th className="p-2 border border-slate-200">Scope / Path</th>
                <th className="p-2 border border-slate-200">Security Attributes</th>
                <th className="p-2 border border-slate-200">Lifespan</th>
                <th className="p-2 border border-slate-200">Purpose</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-slate-600">
              <tr>
                <td className="p-2 font-mono font-medium text-slate-800">tf_refresh_token</td>
                <td className="p-2 font-mono">/api/v1/auth</td>
                <td className="p-2 font-mono text-[11px]">HttpOnly; Secure; SameSite=Lax</td>
                <td className="p-2">7 days (604800s)</td>
                <td className="p-2">Secure token rotation for authenticated staff sessions</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="text-xs text-slate-500 mt-2 font-medium">
          <strong>Zero Tracking or Advertising Cookies:</strong> TrustFed does NOT use third-party analytics, marketing, behavioral tracking, or advertising cookies.
        </p>
      </section>

      {/* ── SECTION 4: CLINICAL MODE (NOT ACTIVE) ── */}
      <section className="mb-8 p-5 rounded-2xl bg-purple-50/40 border border-purple-200">
        <div className="flex items-center justify-between gap-2 mb-3">
          <h2 className="text-base font-bold text-purple-950 flex items-center gap-2 m-0">
            <Lock className="w-5 h-5 text-purple-600" />
            4. Clinical Mode Architecture [NOT ACTIVE]
          </h2>
          <Badge variant="outline" className="bg-purple-100 text-purple-800 border-purple-300 text-[10px] uppercase font-bold">
            NOT ACTIVE
          </Badge>
        </div>
        <div className="p-3 mb-3 rounded-lg bg-amber-50 border border-amber-200 text-[11px] text-amber-900 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0" />
          <span>
            Clinical Mode is completely disabled in the current prototype deployment. It will only be activated after legal consortium agreements, ethics board clearance, and regulatory review.
          </span>
        </div>
        <p className="text-xs text-purple-900 mb-2">
          When activated in future consortium deployments, Clinical Mode will operate under strict architectural safeguards:
        </p>
        <ul className="list-disc pl-5 space-y-1 text-xs text-slate-700">
          <li><strong>Local Tenancy Boundary:</strong> Data remains inside the originating hospital node. No raw patient records leave the hospital.</li>
          <li><strong>Differential Privacy (DP-SGD):</strong> Federated model aggregation applies mathematical privacy bounds (ε ≤ 1.84) to prevent patient record reconstruction.</li>
          <li><strong>Patient Consent Registry:</strong> Explicit digital consent records required before any encounter can be marked eligible for local model training.</li>
          <li><strong>Immutable Audit Trail:</strong> Append-only cryptographically hashed audit ledgers for all data access events.</li>
        </ul>
      </section>

      {/* ── SECTION 5: NO STATUTORY COMPLIANCE CLAIMS ── */}
      <section className="mb-6 p-4 rounded-xl bg-slate-100 border border-slate-300 text-xs text-slate-700">
        <h3 className="text-xs font-bold uppercase text-slate-900 mb-1">
          5. Regulatory Notice: No Statutory Compliance Claims
        </h3>
        <p className="m-0 leading-relaxed">
          TrustFed is an engineering research platform and does NOT claim formal certification, regulatory clearance, or statutory compliance with the Digital Personal Data Protection Act (DPDP), HIPAA, GDPR, or Software as a Medical Device (SaMD) directives. Achieving statutory compliance requires institutional legal review, Data Protection Officer appointments, institutional data sharing contracts, and independent third-party audits.
        </p>
      </section>
    </article>
  );
}

