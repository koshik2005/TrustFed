import { useQuery, useMutation } from '@tanstack/react-query';
import { trainingApi, predictionApi, teflApi, auditApi } from '../services/api';
import type { PatientVitals } from '../types';

// ── Training hooks ────────────────────────────────────────────────────────────
export const useLatestSession = () =>
  useQuery({
    queryKey: ['training', 'latest'],
    queryFn: () => trainingApi.getLatestSession(),
    refetchInterval: 5000, // Poll every 5s while training is live
  });

export const useHospitals = () =>
  useQuery({
    queryKey: ['training', 'hospitals'],
    queryFn: () => trainingApi.getHospitals(),
    refetchInterval: 10000,
  });

// ── Prediction hooks ──────────────────────────────────────────────────────────
export const usePredict = () =>
  useMutation({
    mutationFn: (vitals: PatientVitals) =>
      predictionApi.predict(vitals),
  });

export const usePredictionHistory = (page = 1) =>
  useQuery({
    queryKey: ['prediction', 'history', page],
    queryFn: () => predictionApi.getHistory(page),
  });

// ── TEFL hooks ────────────────────────────────────────────────────────────────
export const useFairnessReport = (sessionId: string) =>
  useQuery({
    queryKey: ['tefl', 'fairness', sessionId],
    queryFn: () => teflApi.getFairnessReport(sessionId),
    enabled: !!sessionId,
  });

export const usePrivacyReport = (sessionId: string) =>
  useQuery({
    queryKey: ['tefl', 'privacy', sessionId],
    queryFn: () => teflApi.getPrivacyReport(sessionId),
    enabled: !!sessionId,
  });

// ── Audit hooks ───────────────────────────────────────────────────────────────
export const useAuditLogs = (params: { page?: number; eventType?: string }) =>
  useQuery({
    queryKey: ['audit', 'logs', params],
    queryFn: () => auditApi.getLogs(params),
  });
