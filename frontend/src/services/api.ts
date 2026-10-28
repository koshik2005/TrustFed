import apiClient from './apiClient';
import type {
  TrainingSession, RoundMetric, PredictionResult,
  PatientVitals, FairnessReport, PrivacyReport,
  AuditEntry, PaginatedResponse, Hospital, User
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
};

export const api = {
  authApi,
  trainingApi,
  predictionApi,
  teflApi,
  auditApi,
};
