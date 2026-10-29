// ─────────────────────────────────────────────────────────────────────────────
// Global TypeScript Definitions — TrustFed-Health
// Single source of truth for all data shapes across the entire frontend.
// ─────────────────────────────────────────────────────────────────────────────

// ── Auth ─────────────────────────────────────────────────────────────────────
export type UserRole = 'hospital_staff' | 'doctor' | 'regional_admin' | 'global_admin';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  hospitalId?: string;
  hubId?: string;
  mustResetPassword?: boolean;
  status?: string;
  avatarUrl?: string;
}

export interface RegionalHub {
  id: string;
  name: string;
  region: string;
  status: 'active' | 'suspended' | string;
  createdBy?: number;
  hospitalCount: number;
  adminCount: number;
  createdAt: string;
}

export interface RegionalHospital {
  id: string;
  name: string;
  hubId: string;
  status: 'active' | 'suspended' | 'removed' | string;
  shareDeidentified: boolean;
  userCount: number;
  datasetSize: number;
  nodeStatus: string;
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

// ── Clinical Encounters & General Disease Types ──────────────────────────────
export interface ClinicalSymptom {
  code: string;
  label: string;
}

export interface DiseaseProbability {
  code?: string;
  disease: string;
  probability: number;
}

export interface ClinicalVitals {
  temp_c?: number;
  bp_sys?: number;
  bp_dia?: number;
  hr?: number;
  spo2?: number;
  resp_rate?: number;
  blood_sugar?: number;
}

export interface ClinicalPatient {
  id: number;
  patientIdentifier: string;
  hospitalId: string;
  name?: string | null;
  contact?: string | null;
  age: number;
  sex: number;
  sexLabel: string;
  weight?: number | null;
  height?: number | null;
  encounterCount?: number;
  lastEncounterDate?: string | null;
  lastEncounterId?: number | null;
  createdAt?: string | null;
}

export interface ClinicalEncounter {
  id: number;
  encounterIdentifier: string;
  patientId: number;
  hospitalId: string;
  symptoms: string[];
  symptomDurationDays: number;
  vitals: ClinicalVitals;
  structuredEcgFinding?: string | null;
  optionalLabs?: Record<string, any>;
  modelVersion?: string;
  predictedTop3: DiseaseProbability[];
  doctorConfirmedDiagnosis?: string | null;
  cause?: string | null;
  treatment?: string | null;
  confirmedBy?: number | null;
  confirmedByName?: string | null;
  confirmedAt?: string | null;
  trainable: boolean;
  status: 'pending' | 'confirmed';
  createdAt?: string | null;
  patient?: ClinicalPatient;
}

