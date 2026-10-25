import apiClient from './apiClient';
import type {
  TrainingSession, RoundMetric, PredictionResult,
  PatientVitals, FairnessReport, PrivacyReport,
  AuditEntry, PaginatedResponse, Hospital, User
} from '../types';
import {
  MOCK_USERS, MOCK_HOSPITALS, MOCK_SESSION, MOCK_METRICS,
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

export const authApi = {
  login: async (email: string, password: string): Promise<{ token: string; user: User }> => {
    try {
      const res = await apiClient.post<{ token: string; user: User }>('/auth/login', { email, password });
      return res.data;
    } catch {
      // Offline fallback: match user by role or email
      let user: User = MOCK_USERS.hospital_staff;
      if (email.includes('admin') || email.startsWith('admin@')) {
        user = MOCK_USERS.global_admin;
      } else if (email.includes('regional') || email.startsWith('regional@')) {
        user = MOCK_USERS.regional_admin;
      }
      const token = `tf-mock-jwt-${user.role}-${Date.now()}`;
      return { token, user };
    }
  },
};

export const api = {
  authApi,
  trainingApi,
  predictionApi,
  teflApi,
  auditApi,
};
