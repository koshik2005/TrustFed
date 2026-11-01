import React, { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  ShieldAlert, Mail, MapPin, Clock, CheckCircle2,
  AlertTriangle, PhoneCall, Send, Building
} from 'lucide-react';

export default function GrievancePage() {
  const [submitted, setSubmitted] = useState(false);
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <article className="prose prose-slate max-w-none text-slate-800 text-xs sm:text-sm leading-relaxed">
      {/* Notice Banner */}
      <div className="p-4 mb-6 rounded-xl bg-amber-50 border border-amber-300 text-amber-900 flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
        <div>
          <span className="font-bold block text-sm mb-0.5">DRAFT, pending legal review</span>
          <p className="text-xs text-amber-800 m-0 leading-normal">
            Prepared in accordance with the Indian Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules and grievance redressal practices.
          </p>
        </div>
      </div>

      <div className="border-b border-slate-200 pb-4 mb-6">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-900 mb-1">Contact & Grievance Redressal</h1>
        <p className="text-xs text-slate-500 m-0">
          Official Redressal Mechanism • Nodal Grievance Officer Contact Details
        </p>
      </div>

      {/* Emergency Notice */}
      <div className="p-3.5 mb-6 rounded-xl bg-red-50 border border-red-200 text-red-900 text-xs flex items-center gap-2.5">
        <AlertTriangle className="w-4 h-4 text-red-600 flex-shrink-0" />
        <span>
          <strong>Emergency Warning:</strong> The Grievance Officer does <em>NOT</em> provide medical advice or emergency triage. For medical emergencies in India, dial <strong>112</strong> immediately.
        </span>
      </div>

      {/* Nodal Officer Contact Card */}
      <div className="mb-8 p-5 rounded-2xl bg-slate-50 border border-slate-200 shadow-2xs">
        <h2 className="text-sm sm:text-base font-bold text-slate-900 mb-3 flex items-center gap-2 m-0">
          <Building className="w-4 h-4 text-blue-600" />
          Designated Nodal Grievance Officer [Statutory Placeholder]
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs mt-3">
          <div className="space-y-2">
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Name & Designation</span>
              <p className="font-bold text-slate-900 m-0">Adv. Rajesh V. Sharma / Compliance Lead [Placeholder]</p>
              <p className="text-slate-500 m-0 text-[11px]">Nodal Grievance Redressal & Data Protection Officer</p>
            </div>

            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Organization</span>
              <p className="font-medium text-slate-800 m-0">TrustFed AI Health Research Consortium (Prototype)</p>
            </div>

            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Official Emails</span>
              <p className="font-mono text-blue-600 m-0">grievance-officer@trustfed.ai</p>
              <p className="font-mono text-slate-500 m-0 text-[11px]">security@trustfed.ai (Security & Vulnerabilities)</p>
            </div>
          </div>

          <div className="space-y-2">
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Registered Physical Address</span>
              <p className="text-slate-700 m-0 leading-normal flex items-start gap-1">
                <MapPin className="w-3.5 h-3.5 text-slate-400 flex-shrink-0 mt-0.5" />
                No. 42, Innovation Hub, Tech City, Bengaluru, Karnataka 560100, India [Corporate/Academic Partner Placeholder]
              </p>
            </div>

            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400 block">Turnaround Timelines</span>
              <p className="text-slate-700 m-0 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                Acknowledgment within <strong>24–48 hours</strong>; Resolution within <strong>15 days</strong>.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Grievance Submission Form */}
      <section className="p-6 rounded-2xl bg-white border border-slate-200">
        <h3 className="text-sm font-bold text-slate-900 mb-1 flex items-center gap-2 m-0">
          <Mail className="w-4 h-4 text-blue-600" />
          Submit a Formal Grievance or Inquiry
        </h3>
        <p className="text-xs text-slate-500 mb-4 m-0">
          Fill out this form or email us directly at <code>grievance-officer@trustfed.ai</code>.
        </p>

        {submitted ? (
          <div className="p-6 rounded-xl bg-green-50 border border-green-200 text-green-900 text-center">
            <CheckCircle2 className="w-8 h-8 text-green-600 mx-auto mb-2" />
            <h4 className="font-bold text-sm text-green-950 mb-1">Grievance Submission Recorded</h4>
            <p className="text-xs text-green-800 m-0">
              Your inquiry has been logged under reference ticket <code>#TF-GRV-{Math.floor(100000 + Math.random() * 900000)}</code>. Our Grievance Officer will acknowledge within 48 hours.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Your Full Name</label>
                <Input
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Dr. Ramesh Kumar"
                  className="h-9 text-xs"
                />
              </div>
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Your Contact Email</label>
                <Input
                  required
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="e.g. ramesh@hospital.org"
                  className="h-9 text-xs"
                />
              </div>
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Nature of Grievance / Subject</label>
              <Input
                required
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="e.g. Algorithmic discrepancy report / Privacy inquiry"
                className="h-9 text-xs"
              />
            </div>

            <div>
              <label className="font-semibold text-slate-700 block mb-1">Detailed Description</label>
              <textarea
                required
                rows={4}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Please describe the concern, encounter date, or feature in detail. Do NOT include real patient personal identifiable health records."
                className="w-full rounded-md border border-slate-300 p-2 text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none bg-white text-slate-800"
              />
            </div>

            <Button
              type="submit"
              className="bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs h-9 px-4"
            >
              <Send className="w-3.5 h-3.5 mr-1.5" />
              Submit Grievance to Nodal Officer
            </Button>
          </form>
        )}
      </section>
    </article>
  );
}
