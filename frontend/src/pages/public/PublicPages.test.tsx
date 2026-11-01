import { describe, it, expect } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import TermsPage from './TermsPage';
import PrivacyPolicyPage from './PrivacyPolicyPage';
import MedicalDisclaimerPage from './MedicalDisclaimerPage';
import GrievancePage from './GrievancePage';
import IntendedUsePage from './IntendedUsePage';
import PublicFooter from '@/components/common/PublicFooter';

describe('Phase F Public Legal & Transparency Pages', () => {
  it('renders TermsPage with DRAFT notice and plain-language terms', () => {
    render(
      <MemoryRouter>
        <TermsPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/DRAFT, pending legal review/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Terms of Use/i })).toBeInTheDocument();
    expect(screen.getByText(/Non-Diagnostic Prototype/i)).toBeInTheDocument();
    expect(screen.getAllByText(/112/i).length).toBeGreaterThan(0);
  });

  it('renders PrivacyPolicyPage with Informational Mode active and Clinical Mode NOT ACTIVE', () => {
    render(
      <MemoryRouter>
        <PrivacyPolicyPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/DRAFT, pending legal review/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Privacy Policy/i })).toBeInTheDocument();
    expect(screen.getByText(/What Is NOT Collected/i)).toBeInTheDocument();
    expect(screen.getAllByText(/NOT ACTIVE/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Essential Cookies Notice & Technical Attributes/i)).toBeInTheDocument();
  });

  it('renders MedicalDisclaimerPage with emergency numbers and pending physician review labels', () => {
    render(
      <MemoryRouter>
        <MedicalDisclaimerPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/DRAFT, pending legal review/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Medical & Safety Disclaimer/i })).toBeInTheDocument();
    expect(screen.getByText(/Immediate Emergency Medical Guidance/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Pending Physician Review/i).length).toBeGreaterThan(0);
    // Emergency numbers
    expect(screen.getAllByText('112').length).toBeGreaterThan(0);
    expect(screen.getByText('911')).toBeInTheDocument();
    expect(screen.getByText('999')).toBeInTheDocument();
  });

  it('renders GrievancePage with Indian Nodal Grievance Officer details and timeline', () => {
    render(
      <MemoryRouter>
        <GrievancePage />
      </MemoryRouter>
    );

    expect(screen.getByText(/DRAFT, pending legal review/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Contact & Grievance Redressal/i })).toBeInTheDocument();
    expect(screen.getByText(/Grievance Officer Name - Pending Formal Statutory Appointment/i)).toBeInTheDocument();
    expect(screen.getAllByText(/grievance-officer@trustfed.ai/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Bengaluru, Karnataka/i)).toBeInTheDocument();
    expect(screen.getByText(/15 days/i)).toBeInTheDocument();
  });

  it('renders IntendedUsePage with target audience and contraindications', () => {
    render(
      <MemoryRouter>
        <IntendedUsePage />
      </MemoryRouter>
    );

    expect(screen.getByText(/DRAFT, pending legal review/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Intended Use Specification/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Who It Is For/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /What It Is NOT For/i })).toBeInTheDocument();
    expect(screen.getByText(/NOT for Primary Medical Diagnosis/i)).toBeInTheDocument();
    expect(screen.getByText(/NOT a Certified Medical Device/i)).toBeInTheDocument();
  });

  it('renders PublicFooter with all 5 mandatory links and emergency notice', () => {
    render(
      <MemoryRouter>
        <PublicFooter />
      </MemoryRouter>
    );

    expect(screen.getByRole('link', { name: /Intended Use/i })).toHaveAttribute('href', '/intended-use');
    expect(screen.getByRole('link', { name: /Terms of Use/i })).toHaveAttribute('href', '/terms');
    expect(screen.getByRole('link', { name: /Privacy Policy/i })).toHaveAttribute('href', '/privacy-policy');
    expect(screen.getByRole('link', { name: /Medical Disclaimer/i })).toHaveAttribute('href', '/disclaimer');
    expect(screen.getByRole('link', { name: /Contact & Grievance/i })).toHaveAttribute('href', '/grievance');
    expect(screen.getByText(/Essential cookies only/i)).toBeInTheDocument();
    expect(screen.getByText(/Educational decision support\. Not medical advice/i)).toBeInTheDocument();
  });
});
