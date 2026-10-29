import { describe, it, expect, vi, beforeEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import NewPatientEncounterPage from './NewPatientEncounterPage';
import EncounterDetailPage from './EncounterDetailPage';
import PatientListPage from './PatientListPage';
import { clinicalApi } from '@/services/api';
import { useAuthStore } from '@/store/authStore';

vi.mock('@/services/api', () => ({
  clinicalApi: {
    getSymptoms: vi.fn(),
    registerPatient: vi.fn(),
    listPatients: vi.fn(),
    getPatientDetail: vi.fn(),
    getEncounterDetail: vi.fn(),
    confirmEncounter: vi.fn(),
    listEncounters: vi.fn(),
  },
}));

describe('Phase 3: Clinical Patient & Doctor Confirmation UI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders NewPatientEncounterPage and enforces required age and symptoms', async () => {
    vi.mocked(clinicalApi.getSymptoms).mockResolvedValue({
      symptoms: [
        { code: 'fever', label: 'Fever / Pyrexia' },
        { code: 'cough', label: 'Cough' },
      ],
      ecgFindings: ['normal'],
    });

    render(
      <MemoryRouter>
        <NewPatientEncounterPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/New Patient Registration/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/e\.g\. 35/i)).toBeInTheDocument();
    expect(screen.getByText(/Searchable Symptoms Multi-Select/i)).toBeInTheDocument();

    // Submit without symptoms or age -> inline errors
    const submitBtn = screen.getByRole('button', { name: /Run AI Differential Assessment/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Age is required and must be between 0 and 125/i)).toBeInTheDocument();
      expect(screen.getByText(/At least one presenting symptom is required/i)).toBeInTheDocument();
    });
  });

  it('renders PatientListPage with directory search and patient records', async () => {
    vi.mocked(clinicalApi.listPatients).mockResolvedValue({
      items: [
        {
          id: 101,
          patientIdentifier: 'PT-9A8B7C',
          hospitalId: '1',
          name: 'Jane Smith',
          contact: '+1-555-0101',
          age: 34,
          sex: 0,
          sexLabel: 'Female',
          encounterCount: 2,
          lastEncounterDate: '2026-10-25T10:00:00Z',
          lastEncounterId: 201,
        },
      ],
      total: 1,
      page: 1,
      pageSize: 20,
      totalPages: 1,
    });

    render(
      <MemoryRouter>
        <PatientListPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Jane Smith')).toBeInTheDocument();
      expect(screen.getByText('PT-9A8B7C')).toBeInTheDocument();
      expect(screen.getByText(/34 yrs ·/i)).toBeInTheDocument();
    });
  });

  it('EncounterDetailPage renders differential top-3 and allows doctor confirmation', async () => {
    useAuthStore.getState().login({
      id: '2',
      name: 'Dr. Ross',
      email: 'doctor@trustfed.ai',
      role: 'doctor',
      hospitalId: '1',
    }, 'mock-doctor-token');

    vi.mocked(clinicalApi.getEncounterDetail).mockResolvedValue({
      id: 55,
      encounterIdentifier: 'ENC-TEST-55',
      patientId: 101,
      hospitalId: '1',
      symptoms: ['high_fever', 'severe_joint_pain', 'rash'],
      symptomDurationDays: 3,
      vitals: { temp_c: 39.2, bp_sys: 110, bp_dia: 72, hr: 96, spo2: 98 },
      structuredEcgFinding: 'normal',
      modelVersion: 'TF-GenDisease-v1.0',
      predictedTop3: [
        { disease: 'Dengue Fever', probability: 0.78 },
        { disease: 'Acute Viral Pyrexia', probability: 0.16 },
        { disease: 'Typhoid Enteric Fever', probability: 0.06 },
      ],
      doctorConfirmedDiagnosis: null,
      cause: null,
      treatment: null,
      trainable: false,
      status: 'pending',
      patient: {
        id: 101,
        patientIdentifier: 'PT-9A8B7C',
        hospitalId: '1',
        name: 'Alice Cooper',
        age: 29,
        sex: 0,
        sexLabel: 'Female',
      },
    });

    render(
      <MemoryRouter initialEntries={['/encounters/55']}>
        <Routes>
          <Route path="/encounters/:id" element={<EncounterDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Alice Cooper/i)).toBeInTheDocument();
      expect(screen.getAllByText(/Dengue Fever/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/78%/i).length).toBeGreaterThan(0);
      expect(screen.getByText(/Awaiting Doctor Confirmation/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Confirm Diagnosis & Mark Trainable/i })).toBeInTheDocument();
    });
  });

  it('EncounterDetailPage restricts hospital staff from confirming diagnoses', async () => {
    useAuthStore.getState().login({
      id: '3',
      name: 'Nurse Chen',
      email: 'hospital@trustfed.ai',
      role: 'hospital_staff',
      hospitalId: '1',
    }, 'mock-staff-token');

    vi.mocked(clinicalApi.getEncounterDetail).mockResolvedValue({
      id: 56,
      encounterIdentifier: 'ENC-TEST-56',
      patientId: 102,
      hospitalId: '1',
      symptoms: ['cough', 'fever'],
      symptomDurationDays: 2,
      vitals: { temp_c: 38.0 },
      modelVersion: 'TF-GenDisease-v1.0',
      predictedTop3: [
        { disease: 'Influenza (Seasonal Flu)', probability: 0.65 },
        { disease: 'Common Cold', probability: 0.35 },
      ],
      doctorConfirmedDiagnosis: null,
      trainable: false,
      status: 'pending',
      patient: {
        id: 102,
        patientIdentifier: 'PT-TEST-102',
        hospitalId: '1',
        name: 'Bob Marley',
        age: 45,
        sex: 1,
        sexLabel: 'Male',
      },
    });

    render(
      <MemoryRouter initialEntries={['/encounters/56']}>
        <Routes>
          <Route path="/encounters/:id" element={<EncounterDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Doctor Confirmation Required/i)).toBeInTheDocument();
      expect(screen.getByText(/only attending doctors may confirm diagnoses/i)).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Confirm Diagnosis & Mark Trainable/i })).not.toBeInTheDocument();
    });
  });

  it('EncounterDetailPage renders red flags, adaptive questioning, remedies label, and disclaimer', async () => {
    useAuthStore.getState().login({
      id: '2',
      name: 'Dr. Ross',
      email: 'doctor@trustfed.ai',
      role: 'doctor',
      hospitalId: '1',
    }, 'mock-doctor-token');

    vi.mocked(clinicalApi.getEncounterDetail).mockResolvedValue({
      id: 77,
      encounterIdentifier: 'ENC-RED-77',
      patientId: 105,
      hospitalId: '1',
      symptoms: ['chest_pain', 'breathlessness'],
      symptomDurationDays: 1,
      vitals: { temp_c: 37.0, bp_sys: 155, bp_dia: 95, hr: 110, spo2: 89 },
      structuredEcgFinding: 'st_change',
      modelVersion: 'TF-GenDisease-v1.0',
      predictedTop3: [
        { disease: 'Coronary Artery Disease (CAD)', probability: 0.58 },
        { disease: 'Community-Acquired Pneumonia', probability: 0.28 },
        { disease: 'Bronchial Asthma Exacerbation', probability: 0.14 },
      ],
      hasCriticalRedFlag: true,
      redFlags: [
        {
          ruleId: 'CARDIAC_ACUTE_CORONARY_SYNDROME',
          severity: 'CRITICAL',
          title: 'Suspected Acute Coronary Syndrome (ACS)',
          description: 'Chest pain with breathlessness detected.',
          escalationAction: 'Immediate 12-lead ECG stat and cardiac monitoring.'
        },
        {
          ruleId: 'CRITICAL_HYPOXIA',
          severity: 'CRITICAL',
          title: 'Severe Hypoxemic Respiratory Failure',
          description: 'SpO2 is 89%.',
          escalationAction: 'Initiate supplemental oxygen immediately.'
        }
      ],
      adaptiveQuestion: {
        suggestedParameter: 'spo2',
        label: 'Oxygen Saturation (SpO2)',
        action: 'Measure pulse oximetry',
        reason: 'Differentiates pulmonary vs cardiac causes.',
        prompt: 'Add SpO2 to improve this result',
        uiPrompt: 'Add SpO2 to improve this result',
        expectedInformationGain: 0.50
      },
      explanations: {
        topCondition: 'Coronary Artery Disease (CAD)',
        contributions: [
          { feature: 'Symptom: Chest Pain', rawFeature: 'sym_chest_pain', impact: 2.8, direction: 'supports' }
        ],
        positiveContributions: [
          { feature: 'Symptom: Chest Pain', rawFeature: 'sym_chest_pain', impact: 2.8, direction: 'supports' }
        ],
        negativeContributions: []
      },
      suggestedClinicalGuidance: {
        label: 'Suggested, clinician must verify',
        verificationNotice: 'Suggested, clinician must verify.',
        disease: 'Coronary Artery Disease (CAD)',
        suggestedCause: 'Atherosclerotic coronary artery plaque rupture.',
        commonRemedies: ['Aspirin 300mg stat', 'Nitroglycerin sublingual', 'Urgent cardiology consult']
      },
      disclaimer: 'Clinical decision support only, not a diagnosis.',
      doctorConfirmedDiagnosis: null,
      trainable: false,
      status: 'pending',
      patient: {
        id: 105,
        patientIdentifier: 'PT-999',
        hospitalId: '1',
        name: 'Eva Mendes',
        age: 58,
        sex: 0,
        sexLabel: 'Female',
      },
    });

    render(
      <MemoryRouter initialEntries={['/encounters/77']}>
        <Routes>
          <Route path="/encounters/:id" element={<EncounterDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      // 1. Red-flag override banner
      expect(screen.getByText(/CRITICAL CLINICAL RED-FLAG SAFETY OVERRIDE/i)).toBeInTheDocument();
      expect(screen.getByText(/Suspected Acute Coronary Syndrome/i)).toBeInTheDocument();
      expect(screen.getByText(/Severe Hypoxemic Respiratory Failure/i)).toBeInTheDocument();

      // 2. Adaptive question
      expect(screen.getByText(/Add SpO2 to improve this result/i)).toBeInTheDocument();

      // 3. Feature contribution
      expect(screen.getByText(/\+2.8 Symptom: Chest Pain/i)).toBeInTheDocument();

      // 4. Suggested guidance & label
      expect(screen.getByText(/Suggested, clinician must verify/i)).toBeInTheDocument();
      expect(screen.getByText(/Atherosclerotic coronary artery plaque rupture/i)).toBeInTheDocument();

      // 5. Mandatory disclaimer
      expect(screen.getByText(/Clinical decision support only, not a diagnosis/i)).toBeInTheDocument();
    });
  });
});
