import apiClient from './apiClient';
import type {
  TrainingSession, RoundMetric, PredictionResult,
  PatientVitals, FairnessReport, PrivacyReport,
  AuditEntry, PaginatedResponse, Hospital, User,
  RegionalHub, RegionalHospital, ClinicalSymptom,
  ClinicalVitals, ClinicalPatient, ClinicalEncounter
} from '../types';
import {
  MOCK_HOSPITALS, MOCK_SESSION, MOCK_METRICS,
  computeMockPrediction, MOCK_INITIAL_PREDICTION,
  MOCK_FAIRNESS_REPORT, MOCK_PRIVACY_REPORT,
  MOCK_COMPARISON_DATA, MOCK_AUDIT_LOGS
} from './mockData';

// In-memory cache for demo predictions & sessions
let currentSession: TrainingSession = { ...MOCK_SESSION };
const predictionHistory: PredictionResult[] = [MOCK_INITIAL_PREDICTION];

// ── Training ──────────────────────────────────────────────────────────────────
export const trainingApi = {
  getSession: async (id: string): Promise<TrainingSession> => {
    try {
      const res = await apiClient.get<TrainingSession>(`/training/sessions/${id}`);
      return res.data;
    } catch {
      return currentSession;
    }
  },

  getLatestSession: async (): Promise<TrainingSession> => {
    try {
      const res = await apiClient.get<TrainingSession>('/training/sessions/latest');
      return res.data;
    } catch {
      return currentSession;
    }
  },

  startSession: async (config: Record<string, unknown>): Promise<TrainingSession> => {
    try {
      const res = await apiClient.post<TrainingSession>('/training/sessions', config);
      return res.data;
    } catch {
      // Simulate live training session starting
      const totalRounds = Number(config.rounds) || 5;
      currentSession = {
        ...MOCK_SESSION,
        sessionId: `TF-SESS-${Math.floor(1000 + Math.random() * 9000)}`,
        status: 'running',
        currentRound: 1,
        totalRounds,
        startedAt: new Date().toISOString(),
        metrics: [MOCK_METRICS[0]],
      };

      // Progressively advance rounds in the background for live feedback
      let round = 1;
      const timer = setInterval(() => {
        round++;
        if (round <= Math.min(totalRounds, MOCK_METRICS.length)) {
          currentSession = {
            ...currentSession,
            currentRound: round,
            metrics: MOCK_METRICS.slice(0, round),
            globalAccuracy: MOCK_METRICS[round - 1].accuracy,
            privacyBudget: MOCK_METRICS[round - 1].epsilon,
          };
        } else {
          currentSession.status = 'converged';
          clearInterval(timer);
        }
      }, 3500);

      return currentSession;
    }
  },

  getRoundMetrics: async (sessionId: string): Promise<RoundMetric[]> => {
    try {
      const res = await apiClient.get<RoundMetric[]>(`/training/sessions/${sessionId}/metrics`);
      return res.data;
    } catch {
      return currentSession.metrics;
    }
  },

  getHospitals: async (): Promise<Hospital[]> => {
    try {
      const res = await apiClient.get<Hospital[]>('/training/hospitals');
      return res.data;
    } catch {
      return MOCK_HOSPITALS;
    }
  },

  getComparison: async (): Promise<any[]> => {
    try {
      const res = await apiClient.get<any[]>('/training/comparison');
      return res.data;
    } catch {
      return MOCK_COMPARISON_DATA;
    }
  },
};

// ── Prediction ────────────────────────────────────────────────────────────────
export const predictionApi = {
  predict: async (vitals: PatientVitals): Promise<PredictionResult> => {
    try {
      const res = await apiClient.post<PredictionResult>('/prediction/predict', vitals);
      predictionHistory.unshift(res.data);
      return res.data;
    } catch {
      const mockResult = computeMockPrediction(vitals);
      predictionHistory.unshift(mockResult);
      return mockResult;
    }
  },

  getHistory: async (page = 1, pageSize = 20): Promise<PaginatedResponse<PredictionResult>> => {
    try {
      const res = await apiClient.get<PaginatedResponse<PredictionResult>>(
        `/prediction/history?page=${page}&page_size=${pageSize}`
      );
      return res.data;
    } catch {
      return {
        items: predictionHistory.slice((page - 1) * pageSize, page * pageSize),
        total: predictionHistory.length,
        page,
        pageSize,
        totalPages: Math.ceil(predictionHistory.length / pageSize),
      };
    }
  },

  getById: async (id: string): Promise<PredictionResult> => {
    try {
      const res = await apiClient.get<PredictionResult>(`/prediction/${id}`);
      return res.data;
    } catch {
      const found = predictionHistory.find(p => p.patientId === id);
      return found || predictionHistory[0] || MOCK_INITIAL_PREDICTION;
    }
  },
};

// ── TEFL ──────────────────────────────────────────────────────────────────────
export const teflApi = {
  getFairnessReport: async (sessionId: string): Promise<FairnessReport> => {
    try {
      const res = await apiClient.get<FairnessReport>(`/tefl/fairness/${sessionId}`);
      return res.data;
    } catch {
      return MOCK_FAIRNESS_REPORT;
    }
  },

  getPrivacyReport: async (sessionId: string): Promise<PrivacyReport> => {
    try {
      const res = await apiClient.get<PrivacyReport>(`/tefl/privacy/${sessionId}`);
      return res.data;
    } catch {
      return MOCK_PRIVACY_REPORT;
    }
  },
};

// ── Audit ─────────────────────────────────────────────────────────────────────
export const auditApi = {
  getLogs: async (params: { page?: number; eventType?: string; from?: string; to?: string }): Promise<PaginatedResponse<AuditEntry>> => {
    try {
      const res = await apiClient.get<PaginatedResponse<AuditEntry>>('/audit/logs', { params });
      return res.data;
    } catch {
      let filtered = [...MOCK_AUDIT_LOGS];
      if (params.eventType && params.eventType !== 'all') {
        filtered = filtered.filter(l => l.eventType.toLowerCase() === params.eventType?.toLowerCase());
      }
      return {
        items: filtered,
        total: filtered.length,
        page: params.page || 1,
        pageSize: 10,
        totalPages: 1,
      };
    }
  },
};

export interface LoginResponse {
  token: string;
  user: User;
  csrf_token?: string;
  expires_in?: number;
}

export const authApi = {
  login: async (email: string, password: string): Promise<LoginResponse> => {
    try {
      const res = await apiClient.post<LoginResponse>('/auth/login', { email, password });
      return res.data;
    } catch (err: unknown) {
      const axiosErr = err as {
        response?: {
          status?: number;
          headers?: Record<string, string>;
          data?: { detail?: string; message?: string };
        };
        code?: string;
        message?: string;
      };
      if (axiosErr.response) {
        const status = axiosErr.response.status;
        if (status === 429) {
          const retryAfter = axiosErr.response.headers?.['retry-after'];
          const detail = axiosErr.response.data?.detail || axiosErr.response.data?.message;
          const msg = detail || (retryAfter
            ? `Too many login attempts. Please try again in ${retryAfter} seconds.`
            : 'Too many login attempts. Please wait a moment and try again.');
          const customErr = new Error(msg) as Error & { status?: number };
          customErr.status = 429;
          throw customErr;
        }
        if (status === 401) {
          const customErr = new Error('Invalid email or password.') as Error & { status?: number };
          customErr.status = 401;
          throw customErr;
        }
        const errorMsg =
          axiosErr.response.data?.detail ||
          axiosErr.response.data?.message ||
          `Server returned error (${status}).`;
        const customErr = new Error(errorMsg) as Error & { status?: number };
        customErr.status = status;
        throw customErr;
      }
      // Server unreachable / network timeout / cold start
      const networkMsg =
        'Backend server is waking up or temporarily unreachable. Please wait a few seconds and try again.';
      const netErr = new Error(networkMsg) as Error & { status?: number };
      netErr.status = 503;
      throw netErr;
    }
  },

  logout: async (): Promise<void> => {
    try {
      await apiClient.post('/auth/logout');
    } catch {
      // Client-side cleanup occurs in authStore
    }
  },

  refresh: async (): Promise<LoginResponse> => {
    const res = await apiClient.post<LoginResponse>('/auth/refresh');
    return res.data;
  },

  resetPassword: async (currentPassword: string, newPassword: string): Promise<{ message: string; user: User }> => {
    const res = await apiClient.post<{ message: string; user: User }>('/auth/reset-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return res.data;
  },
};

// ── Regional Hubs Management (Global Admin) ───────────────────────────────────
export const hubsApi = {
  list: async (): Promise<RegionalHub[]> => {
    const res = await apiClient.get<RegionalHub[]>('/admin/hubs');
    return res.data;
  },

  create: async (hub: { id: string; name: string; region: string }): Promise<void> => {
    await apiClient.post('/admin/hubs', hub);
  },

  update: async (hubId: string, data: { name?: string; region?: string }): Promise<void> => {
    await apiClient.put(`/admin/hubs/${hubId}`, data);
  },

  suspend: async (hubId: string): Promise<void> => {
    await apiClient.post(`/admin/hubs/${hubId}/suspend`);
  },

  reactivate: async (hubId: string): Promise<void> => {
    await apiClient.post(`/admin/hubs/${hubId}/reactivate`);
  },

  delete: async (hubId: string): Promise<void> => {
    await apiClient.delete(`/admin/hubs/${hubId}`);
  },

  issueAdmin: async (hubId: string, payload: { name: string; email: string }): Promise<{ user: User; temp_password: string }> => {
    const res = await apiClient.post<{ user: User; temp_password: string }>(`/admin/hubs/${hubId}/admins`, payload);
    return res.data;
  },

  listAdmins: async (hubId: string): Promise<User[]> => {
    const res = await apiClient.get<User[]>(`/admin/hubs/${hubId}/admins`);
    return res.data;
  },
};

// ── Hospital Management (Regional Admin & Global Admin) ────────────────────────
export const regionalHospitalsApi = {
  list: async (): Promise<RegionalHospital[]> => {
    const res = await apiClient.get<RegionalHospital[]>('/regional/hospitals');
    return res.data;
  },

  create: async (hospital: { id: string; name: string; hub_id?: string; share_deidentified?: boolean }): Promise<void> => {
    await apiClient.post('/regional/hospitals', hospital);
  },

  update: async (hospitalId: string, data: { name?: string; share_deidentified?: boolean }): Promise<void> => {
    await apiClient.put(`/regional/hospitals/${hospitalId}`, data);
  },

  suspend: async (hospitalId: string): Promise<void> => {
    await apiClient.post(`/regional/hospitals/${hospitalId}/suspend`);
  },

  reactivate: async (hospitalId: string): Promise<void> => {
    await apiClient.post(`/regional/hospitals/${hospitalId}/reactivate`);
  },

  delete: async (hospitalId: string): Promise<void> => {
    await apiClient.delete(`/regional/hospitals/${hospitalId}`);
  },

  issueUser: async (hospitalId: string, payload: { name: string; email: string; role: 'hospital_staff' | 'doctor' }): Promise<{ user: User; temp_password: string }> => {
    const res = await apiClient.post<{ user: User; temp_password: string }>(`/regional/hospitals/${hospitalId}/users`, payload);
    return res.data;
  },

  listUsers: async (hospitalId: string): Promise<User[]> => {
    const res = await apiClient.get<User[]>(`/regional/hospitals/${hospitalId}/users`);
    return res.data;
  },

  suspendUser: async (userId: string | number): Promise<void> => {
    await apiClient.post(`/regional/users/${userId}/suspend`);
  },

  deleteUser: async (userId: string | number): Promise<void> => {
    await apiClient.delete(`/regional/users/${userId}`);
  },
};

// ── Phase 3: Clinical Patient & Doctor Confirmation API ───────────────────────
export const clinicalApi = {
  getSymptoms: async (): Promise<{ symptoms: ClinicalSymptom[]; ecgFindings: string[] }> => {
    const res = await apiClient.get('/clinical/symptoms');
    return res.data;
  },

  registerPatient: async (payload: {
    name?: string;
    contact?: string;
    age: number;
    sex: number | string;
    weight?: number;
    height?: number;
    symptoms?: string[];
    symptom_duration_days?: number;
    vitals?: ClinicalVitals;
    structured_ecg_finding?: string;
    optional_labs?: Record<string, any>;
  }): Promise<{ patient: ClinicalPatient; encounter: ClinicalEncounter | null }> => {
    const res = await apiClient.post('/hospital/patients', payload);
    return res.data;
  },

  listPatients: async (params?: { search?: string; page?: number; pageSize?: number }): Promise<PaginatedResponse<ClinicalPatient>> => {
    const res = await apiClient.get<PaginatedResponse<ClinicalPatient>>('/hospital/patients', { params });
    return res.data;
  },

  getPatientDetail: async (id: number): Promise<{ patient: ClinicalPatient; encounters: ClinicalEncounter[] }> => {
    const res = await apiClient.get(`/hospital/patients/${id}`);
    return res.data;
  },

  createEncounter: async (patientId: number, payload: {
    symptoms: string[];
    symptom_duration_days?: number;
    vitals?: ClinicalVitals;
    structured_ecg_finding?: string;
    optional_labs?: Record<string, any>;
  }): Promise<ClinicalEncounter> => {
    const res = await apiClient.post(`/hospital/patients/${patientId}/encounters`, payload);
    return res.data;
  },

  listEncounters: async (params?: { status?: string; search?: string; page?: number; pageSize?: number }): Promise<PaginatedResponse<ClinicalEncounter>> => {
    const res = await apiClient.get<PaginatedResponse<ClinicalEncounter>>('/hospital/encounters', { params });
    return res.data;
  },

  getEncounterDetail: async (encounterId: number): Promise<ClinicalEncounter> => {
    const res = await apiClient.get<ClinicalEncounter>(`/hospital/encounters/${encounterId}`);
    return res.data;
  },

  confirmEncounter: async (encounterId: number, payload: {
    confirmed_diagnosis: string;
    cause: string;
    treatment: string;
  }): Promise<ClinicalEncounter> => {
    const res = await apiClient.post<ClinicalEncounter>(`/hospital/encounters/${encounterId}/confirm`, payload);
    return res.data;
  },
};

export const api = {
  authApi,
  trainingApi,
  predictionApi,
  teflApi,
  auditApi,
  hubsApi,
  regionalHospitalsApi,
  clinicalApi,
};
