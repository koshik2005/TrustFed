// ─────────────────────────────────────────────────────────────────────────────
// Global TypeScript Definitions — TrustFed-Health
// Single source of truth for all data shapes across the entire frontend.
// ─────────────────────────────────────────────────────────────────────────────

// ── Auth ─────────────────────────────────────────────────────────────────────
export type UserRole = 'hospital_staff' | 'regional_admin' | 'global_admin';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  hospitalId?: string;
  avatarUrl?: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
}

// ── Federated Learning ────────────────────────────────────────────────────────
export type TrainingStatus = 'idle' | 'running' | 'converged' | 'failed' | 'Completed' | 'In Progress';

export interface RoundMetric {
  round: number;
  accuracy: number;
  loss: number;
  epsilon: number;
  timestamp: string;
}

export interface Hospital {
  id: string;
  name: string;
  status: string; // 'connected' | 'disconnected' | 'training' | 'idle' | 'offline'
  localDatasetSize: number;
  region: string;
  currentEpoch: number;
  totalEpochs: number;
}

export interface TrainingSession {
  sessionId: string;
  status: TrainingStatus;
  currentRound: number;
  totalRounds: number;
  startedAt: string;
  metrics: RoundMetric[];
  hospitals: Hospital[];
  globalAccuracy?: number | null;
  privacyBudget?: number | null;
  dataset?: string | null;
  error?: string | null;
}

// ── Patient & Prediction ──────────────────────────────────────────────────────
export interface Patient {
  id: string;
  anonymizedId: string;
  age: number;
  sex: 'M' | 'F';
  vitals: PatientVitals;
}

export interface PatientVitals {
  age: number;
  sex: number;
  chestPainType: number;
  restingBP: number;
  cholesterol: number;
  fastingBloodSugar: number;
  restingECG: number;
  maxHeartRate: number;
  exerciseAngina: number;
  oldPeak: number;
  slope: number;
  ca: number;
  thal: number;
}

export interface PredictionResult {
  patientId: string;
  riskScore: number;          // 0.0 – 1.0
  riskLabel: 'Low' | 'Medium' | 'High';
  confidence: number;
  shapValues: ShapValue[];
  nlpExplanation?: string;    // NVIDIA NIM output
  predictedAt: string;
}

// ── TEFL ─────────────────────────────────────────────────────────────────────
export interface ShapValue {
  feature: string;
  value: number;              // +positive = increases risk, -negative = decreases
  featureValue: string | number;
}

export interface FairnessReport {
  sessionId: string;
  overallScore: number;       // 0.0 – 1.0
  subgroupResults: SubgroupResult[];
  flaggedIssues: FairnessFlag[];
  generatedAt: string;
}

export interface SubgroupResult {
  subgroup: string;           // e.g. "Age > 65", "Female"
  accuracy: number;
  sampleSize: number;
  divergenceScore: number;    // Distance from global average
}

export interface FairnessFlag {
  severity: 'low' | 'medium' | 'high';
  subgroup: string;
  message: string;
  divergence: number;
}

export interface PrivacyReport {
  sessionId: string;
  attackSuccessWithDP: number;    // ~0.5 = random guessing = good
  attackSuccessWithoutDP: number; // ~0.7 = leaking info = bad
  privacyResistance: number;      // 1 - membership-inference advantage (with DP)
  epsilon?: number | null;
  delta?: number | null;
  heKeySize: number;
  paillierEnabled: boolean;
  generatedAt: string;
}

// ── Audit Log ────────────────────────────────────────────────────────────────
export type AuditEventType = 'training' | 'prediction' | 'tefl' | 'auth' | 'config';

export interface AuditEntry {
  id: string;
  timestamp: string;
  nodeId: string;
  eventType: AuditEventType;
  description: string;
  hash: string;               // Cryptographic hash of the log entry
  metadata?: Record<string, unknown>;
}

// ── API Responses ─────────────────────────────────────────────────────────────
export interface ApiResponse<T> {
  data: T;
  message: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// ── UI Utilities ──────────────────────────────────────────────────────────────
export type Theme = 'dark' | 'light';

export interface NavItem {
  id: string;
  label: string;
  path: string;
  icon: string;
  roles: UserRole[];
  badge?: number;
}
