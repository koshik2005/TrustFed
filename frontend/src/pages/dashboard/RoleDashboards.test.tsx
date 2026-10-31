import { describe, it, expect, vi, beforeEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import HospitalDashboard from './HospitalDashboard';
import RegionalDashboard from './RegionalDashboard';
import GlobalAdminDashboard from './GlobalAdminDashboard';
import RoleDashboardDispatcher from './RoleDashboardDispatcher';
import DashboardLayout from '@/layouts/DashboardLayout';
import { api } from '@/services/api';
import { useAuthStore } from '@/store/authStore';

vi.mock('@/services/api', () => ({
  api: {
    dashboardApi: {
      getHospitalDashboard: vi.fn(),
      getRegionalDashboard: vi.fn(),
      getGlobalDashboard: vi.fn(),
    },
    regionalHospitalsApi: {
      list: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      suspend: vi.fn(),
      reactivate: vi.fn(),
      delete: vi.fn(),
      issueCredentials: vi.fn(),
      listUsers: vi.fn(),
    },
    federatedApi: {
      getModelsLineage: vi.fn(),
      triggerFederatedRound: vi.fn(),
      rollbackModel: vi.fn(),
      updateConsent: vi.fn(),
    },
  },
}));

describe('Phase 6: Multi-Tier Role Dashboards', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Hospital Dashboard Tests ───────────────────────────────────────────────
  it('renders HospitalDashboard with patients today, pending confirmations, accuracy, and contribution status', async () => {
    useAuthStore.setState({
      user: {
        id: '1',
        email: 'doc@bgh.org',
        name: 'Dr. Sarah Chen',
        role: 'doctor',
        hospitalId: 'hosp-boston',
      },
      isAuthenticated: true,
    });

    vi.mocked(api.dashboardApi.getHospitalDashboard).mockResolvedValue({
      hospital: {
        id: 'hosp-boston',
        name: 'Boston General Hospital',
        region: 'North-East',
        status: 'active',
        shareDeidentified: true,
      },
      currentModelVersion: 'v2.1.0-fl-promoted',
      patientsToday: 14,
      totalPatients: 120,
      pendingConfirmationsCount: 3,
      confirmedEncountersCount: 15,
      totalEncounters: 18,
      localAccuracy: {
        top1Accuracy: 0.885,
        top3Accuracy: 0.965,
        evaluatedEncounters: 15,
      },
      contributionStatus: {
        eligible: true,
        confirmedCount: 15,
        minRequired: 5,
        status: 'active',
        reason: 'Hospital meets minimum confirmed record threshold (15 >= 5).',
        shareDeidentified: true,
      },
      recentPredictions: [
        {
          id: 101,
          encounterIdentifier: 'ENC-2026-001',
          patientIdentifier: 'PT-BGH-001',
          age: 45,
          sexLabel: 'Female',
          symptoms: ['fever', 'cough'],
          topCondition: 'Influenza',
          topConfidence: 0.88,
          doctorConfirmedDiagnosis: 'Influenza',
          isConfirmed: true,
          trainable: true,
          createdAt: '2026-10-31T06:00:00Z',
        },
      ],
      diseaseDistribution: [
        { disease: 'Influenza', count: 8, percentage: 53.3 },
        { disease: 'Common Cold', count: 7, percentage: 46.7 },
      ],
    });

    render(
      <MemoryRouter>
        <HospitalDashboard />
      </MemoryRouter>
    );

    // Verify loading resolution
    await waitFor(() => {
      expect(screen.getByText('Boston General Hospital')).toBeInTheDocument();
    });

    // KPI cards
    expect(screen.getByText('Patients Today')).toBeInTheDocument();
    expect(screen.getByText('14')).toBeInTheDocument();
    expect(screen.getByText('Pending Confirmations')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('Local Model Accuracy')).toBeInTheDocument();
    expect(screen.getByText('89%')).toBeInTheDocument();
    expect(screen.getByText('FL Contribution')).toBeInTheDocument();
    expect(screen.getByText('Eligible')).toBeInTheDocument();

    // Predictions list
    expect(screen.getByText('PT-BGH-001')).toBeInTheDocument();
    expect(screen.getAllByText('Influenza').length).toBeGreaterThan(0);
  });

  // ── Regional Hub Dashboard Tests ───────────────────────────────────────────
  it('renders RegionalDashboard with record volume, performance, per-disease accuracy, and hospital list', async () => {
    useAuthStore.setState({
      user: {
        id: '2',
        email: 'reg@trustfed.ai',
        name: 'Regional Admin North',
        role: 'regional_admin',
        hubId: 'hub-north',
      },
      isAuthenticated: true,
    });

    vi.mocked(api.dashboardApi.getRegionalDashboard).mockResolvedValue({
      hub: {
        id: 'hub-north',
        name: 'North-East Regional Medical Hub',
        region: 'North-East',
        status: 'active',
      },
      activeModelVersion: 'v2.1.0-fl-promoted',
      totalHospitals: 3,
      eligibleHospitalsCount: 2,
      ineligibleHospitalsCount: 1,
      regionalRecordVolume: {
        totalEncounters: 150,
        confirmedEncounters: 130,
        pendingEncounters: 20,
      },
      regionalModelPerformance: {
        macroF1: 0.892,
        accuracy: 0.905,
        activeVersion: 'v2.1.0-fl-promoted',
      },
      perDiseaseAccuracy: [
        { disease: 'common_cold', displayName: 'Common Cold', count: 40, accuracy: 0.94 },
        { disease: 'dengue', displayName: 'Dengue Fever', count: 25, accuracy: 0.91 },
      ],
      hospitals: [
        {
          id: 'hosp-1',
          name: 'Metro Hospital',
          hubId: 'hub-north',
          status: 'active',
          datasetSize: 80,
          confirmedCount: 75,
          pendingCount: 5,
          eligibleForRound: true,
          eligibilityReason: 'Eligible',
          shareDeidentified: true,
          consentStatus: 'active',
        },
      ],
    });

    render(
      <MemoryRouter>
        <RegionalDashboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('North-East Regional Medical Hub')).toBeInTheDocument();
    });

    // Regional metrics
    expect(screen.getByText('150')).toBeInTheDocument(); // Regional encounters
    expect(screen.getByText('89.2%')).toBeInTheDocument(); // Macro F1
    expect(screen.getByText('Common Cold')).toBeInTheDocument();
    expect(screen.getByText('Dengue Fever')).toBeInTheDocument();
    expect(screen.getByText('Metro Hospital')).toBeInTheDocument();

    // Accessible labels check
    const diseaseBar = screen.getByLabelText(/Common Cold accuracy 94 percent/i);
    expect(diseaseBar).toBeInTheDocument();
  });

  // ── Global Admin Dashboard Tests ───────────────────────────────────────────
  it('renders GlobalAdminDashboard with consortium overview, model lineage, and governance controls', async () => {
    useAuthStore.setState({
      user: {
        id: '3',
        email: 'admin@trustfed.ai',
        name: 'Consortium Superadmin',
        role: 'global_admin',
      },
      isAuthenticated: true,
    });

    vi.mocked(api.dashboardApi.getGlobalDashboard).mockResolvedValue({
      totalHubs: 3,
      activeHubs: 3,
      totalHospitals: 8,
      activeHospitals: 7,
      eligibleHospitalsCount: 6,
      ineligibleHospitalsCount: 1,
      recordVolume: {
        totalEncounters: 450,
        confirmedEncounters: 410,
        pendingEncounters: 40,
        totalPatients: 380,
      },
      currentModel: {
        version: 'v2.1.0-fl-promoted',
        macroF1: 0.892,
        accuracy: 0.914,
        promotedAt: '2026-10-31T05:00:00Z',
      },
      modelVersions: [
        {
          version: 'v2.1.0-fl-promoted',
          description: 'Hierarchical aggregation round 3',
          macroF1: 0.892,
          accuracy: 0.914,
          status: 'active',
          createdAt: '2026-10-31T05:00:00Z',
        },
      ],
      hubsSummary: [],
      perRegionAccuracy: [
        { region: 'North-East', accuracy: 0.912, hospitalsCount: 3, recordVolume: 180 },
      ],
      perDiseaseAccuracy: [
        { disease: 'common_cold', displayName: 'Common Cold', accuracy: 0.94 },
      ],
      recentRounds: [],
      privacySummary: {
        actualEpsilon: 1.84,
        delta: 1e-5,
        targetEpsilon: 2.0,
        targetMet: true,
      },
      fairnessSummary: {
        overallScore: 0.966,
        maxDisparity: 0.034,
        demographicParityStatus: 'Passed',
        subgroupsEvaluated: ['Male', 'Female'],
        flaggedBiases: [],
      },
      auditVerification: {
        chainIntact: true,
        totalChecked: 142,
        latestHash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      },
    });

    render(
      <MemoryRouter>
        <GlobalAdminDashboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Global Health Consortium Dashboard')).toBeInTheDocument();
    });

    expect(screen.getByText('450')).toBeInTheDocument(); // Record volume
    expect(screen.getByText('Trigger Federated Round')).toBeInTheDocument();
    expect(screen.getByText('Quick Rollback')).toBeInTheDocument();
    expect(screen.getByText('Chain Intact')).toBeInTheDocument();
  });

  // ── Role Dashboard Dispatcher Tests ────────────────────────────────────────
  it('dispatches HospitalDashboard for hospital staff and doctor roles', async () => {
    useAuthStore.setState({
      user: {
        id: '1',
        email: 'staff@bgh.org',
        name: 'Nurse Jackie',
        role: 'hospital_staff',
        hospitalId: 'hosp-boston',
      },
      isAuthenticated: true,
    });

    vi.mocked(api.dashboardApi.getHospitalDashboard).mockResolvedValue({
      hospital: { id: 'hosp-boston', name: 'Boston General Hospital', region: 'North', status: 'active' },
      currentModelVersion: 'v2.0.0',
      patientsToday: 5,
      pendingConfirmationsCount: 1,
      totalEncounters: 10,
      localAccuracy: { top1Accuracy: 0.9, top3Accuracy: 0.98, evaluatedEncounters: 9 },
      contributionStatus: { eligible: true, confirmedCount: 9, minRequired: 5, status: 'active', reason: 'Eligible' },
      recentPredictions: [],
      diseaseDistribution: [],
    });

    render(
      <MemoryRouter>
        <RoleDashboardDispatcher />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Boston General Hospital')).toBeInTheDocument();
    });
    expect(screen.getByText('Patients Today')).toBeInTheDocument();
  });

  it('dispatches RegionalDashboard for regional admin', async () => {
    useAuthStore.setState({
      user: {
        id: '2',
        email: 'reg@trustfed.ai',
        name: 'Reg Coordinator',
        role: 'regional_admin',
        hubId: 'hub-1',
      },
      isAuthenticated: true,
    });

    vi.mocked(api.dashboardApi.getRegionalDashboard).mockResolvedValue({
      hub: { id: 'hub-1', name: 'Western Regional Hub', region: 'West', status: 'active' },
      activeModelVersion: 'v2.0.0',
      totalHospitals: 2,
      eligibleHospitalsCount: 2,
      ineligibleHospitalsCount: 0,
      regionalRecordVolume: { totalEncounters: 50, confirmedEncounters: 45, pendingEncounters: 5 },
      regionalModelPerformance: { macroF1: 0.88, accuracy: 0.89, activeVersion: 'v2.0.0' },
      perDiseaseAccuracy: [],
      hospitals: [],
    });

    render(
      <MemoryRouter>
        <RoleDashboardDispatcher />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Western Regional Hub')).toBeInTheDocument();
    });
    expect(screen.getByText('Regional Volume')).toBeInTheDocument();
  });

  it('renders visible demo banner in DashboardLayout', () => {
    useAuthStore.setState({
      user: {
        id: '1',
        email: 'doc@bgh.org',
        name: 'Dr. Sarah',
        role: 'doctor',
      },
      isAuthenticated: true,
    });

    render(
      <MemoryRouter>
        <DashboardLayout />
      </MemoryRouter>
    );

    expect(screen.getByText(/DEMO ENVIRONMENT/i)).toBeInTheDocument();
    expect(screen.getByText(/Synthetic clinical and federated data only/i)).toBeInTheDocument();
  });
});
