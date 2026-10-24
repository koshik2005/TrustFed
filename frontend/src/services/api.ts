import apiClient from './apiClient';
import type {
  TrainingSession, RoundMetric, PredictionResult,
  PatientVitals, FairnessReport, PrivacyReport,
  AuditEntry, PaginatedResponse, Hospital,
} from '../types';

// ── Training ──────────────────────────────────────────────────────────────────
export const trainingApi = {
  getSession: (id: string) =>
    apiClient.get<TrainingSession>(`/training/sessions/${id}`).then(res => res.data),

  getLatestSession: () =>
    apiClient.get<TrainingSession>('/training/sessions/latest').then(res => res.data),

  startSession: (config: Record<string, unknown>) =>
    apiClient.post<TrainingSession>('/training/sessions', config).then(res => res.data),

  getRoundMetrics: (sessionId: string) =>
    apiClient.get<RoundMetric[]>(`/training/sessions/${sessionId}/metrics`).then(res => res.data),

  getHospitals: () =>
    apiClient.get<Hospital[]>('/training/hospitals').then(res => res.data),

  getComparison: () =>
    apiClient.get<any[]>('/training/comparison').then(res => res.data),
};

// ── Prediction ────────────────────────────────────────────────────────────────
export const predictionApi = {
  predict: (vitals: PatientVitals) =>
    apiClient.post<PredictionResult>('/prediction/predict', vitals).then(res => res.data),

  getHistory: (page = 1, pageSize = 20) =>
    apiClient.get<PaginatedResponse<PredictionResult>>(
      `/prediction/history?page=${page}&page_size=${pageSize}`
    ).then(res => res.data),

  getById: (id: string) =>
    apiClient.get<PredictionResult>(`/prediction/${id}`).then(res => res.data),
};

// ── TEFL ──────────────────────────────────────────────────────────────────────
export const teflApi = {
  getFairnessReport: (sessionId: string) =>
    apiClient.get<FairnessReport>(`/tefl/fairness/${sessionId}`).then(res => res.data),

  getPrivacyReport: (sessionId: string) =>
    apiClient.get<PrivacyReport>(`/tefl/privacy/${sessionId}`).then(res => res.data),

};

// ── Audit ─────────────────────────────────────────────────────────────────────
export const auditApi = {
  getLogs: (params: { page?: number; eventType?: string; from?: string; to?: string }) =>
    apiClient.get<PaginatedResponse<AuditEntry>>('/audit/logs', { params }).then(res => res.data),
};

export const authApi = {
  login: (email: string, password: string) =>
    apiClient.post<{ token: string; user: import('../types').User }>('/auth/login', { email, password }).then(res => res.data),
};

export const api = {
  authApi,
  trainingApi,
  predictionApi,
  teflApi,
  auditApi
};
