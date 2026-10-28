import type {
  TrainingSession, RoundMetric, PredictionResult,
  PatientVitals, FairnessReport, PrivacyReport,
  AuditEntry, Hospital, User, UserRole,
  ShapValue
} from '../types';

export const MOCK_USERS: Record<UserRole, User> = {
  hospital_staff: {
    id: 'usr-hosp-01',
    name: 'Dr. Sarah Chen, MD',
    email: 'hospital@trustfed.ai',
    role: 'hospital_staff',
    hospitalId: 'hosp-bgh-01',
  },
  doctor: {
    id: 'usr-doc-01',
    name: 'Dr. Gregory House, MD',
    email: 'doctor@trustfed.ai',
    role: 'doctor',
    hospitalId: 'hosp-bgh-01',
  },
  regional_admin: {
    id: 'usr-reg-02',
    name: 'Dr. Marcus Vance',
    email: 'regional@trustfed.ai',
    role: 'regional_admin',
    hospitalId: 'hub-east-01',
  },
  global_admin: {
    id: 'usr-adm-03',
    name: 'Dr. Elena Rostova',
    email: 'admin@trustfed.ai',
    role: 'global_admin',
  },
};

export const MOCK_HOSPITALS: Hospital[] = [
  {
    id: 'hosp-bgh-01',
    name: 'Boston General Hospital',
    status: 'connected',
    localDatasetSize: 2840,
    region: 'US East Coast Zone',
    currentEpoch: 5,
    totalEpochs: 5,
  },
  {
    id: 'hosp-mayo-02',
    name: 'Mayo Clinic Health System',
    status: 'connected',
    localDatasetSize: 3120,
    region: 'US East Coast Zone',
    currentEpoch: 5,
    totalEpochs: 5,
  },
  {
    id: 'hosp-jhm-03',
    name: 'Johns Hopkins Medicine',
    status: 'connected',
    localDatasetSize: 2450,
    region: 'US East Coast Zone',
    currentEpoch: 5,
    totalEpochs: 5,
  },
  {
    id: 'hosp-cleve-04',
    name: 'Cleveland Clinic Foundation',
    status: 'connected',
    localDatasetSize: 2980,
    region: 'US East Coast Zone',
    currentEpoch: 5,
    totalEpochs: 5,
  },
  {
    id: 'hosp-ms-05',
    name: 'Mount Sinai Health System',
    status: 'connected',
    localDatasetSize: 1920,
    region: 'US East Coast Zone',
    currentEpoch: 5,
    totalEpochs: 5,
  },
];

export const MOCK_METRICS: RoundMetric[] = [
  { round: 1, accuracy: 0.762, loss: 0.621, epsilon: 0.42, timestamp: new Date(Date.now() - 3600000 * 4).toISOString() },
  { round: 2, accuracy: 0.835, loss: 0.432, epsilon: 0.85, timestamp: new Date(Date.now() - 3600000 * 3).toISOString() },
  { round: 3, accuracy: 0.887, loss: 0.310, epsilon: 1.28, timestamp: new Date(Date.now() - 3600000 * 2).toISOString() },
  { round: 4, accuracy: 0.919, loss: 0.228, epsilon: 1.56, timestamp: new Date(Date.now() - 3600000 * 1).toISOString() },
  { round: 5, accuracy: 0.942, loss: 0.184, epsilon: 1.84, timestamp: new Date().toISOString() },
];

export const MOCK_SESSION: TrainingSession = {
  sessionId: 'TF-SESS-9082',
  status: 'converged',
  currentRound: 5,
  totalRounds: 5,
  startedAt: new Date(Date.now() - 3600000 * 5).toISOString(),
  metrics: MOCK_METRICS,
  hospitals: MOCK_HOSPITALS,
  globalAccuracy: 0.942,
  privacyBudget: 1.84,
  dataset: 'Multi-Center Cardiac Cohort (N=13,310 records)',
};

export function computeMockPrediction(vitals: PatientVitals): PredictionResult {
  // Clinically weighted logistic score based on Framingham / Cleveland cardiac factors
  let z = -4.5;
  z += (vitals.age - 50) * 0.05;
  z += vitals.sex === 1 ? 0.6 : 0.0;
  z += (vitals.chestPainType - 1) * 0.45;
  z += (vitals.restingBP - 120) * 0.02;
  z += (vitals.cholesterol - 200) * 0.01;
  z += vitals.fastingBloodSugar === 1 ? 0.5 : 0;
  z += vitals.restingECG * 0.3;
  z += (150 - vitals.maxHeartRate) * 0.015;
  z += vitals.exerciseAngina === 1 ? 0.8 : 0;
  z += vitals.oldPeak * 0.65;
  z += vitals.ca * 0.4;
  z += (vitals.thal === 7 ? 0.9 : vitals.thal === 6 ? 0.5 : 0);

  const prob = 1 / (1 + Math.exp(-z));
  const riskScore = Math.max(0.05, Math.min(0.98, prob));
  const riskLabel: 'Low' | 'Medium' | 'High' = riskScore > 0.65 ? 'High' : riskScore > 0.35 ? 'Medium' : 'Low';
  const confidence = Math.round((Math.abs(riskScore - 0.5) * 2 * 0.4 + 0.6) * 100) / 100;

  const shapValues: ShapValue[] = [
    { feature: 'ST Depression (Oldpeak)', value: Number((vitals.oldPeak * 0.18).toFixed(3)), featureValue: `${vitals.oldPeak} mm` },
    { feature: 'Chest Pain Classification', value: Number(((vitals.chestPainType - 1) * 0.12).toFixed(3)), featureValue: `Type ${vitals.chestPainType}` },
    { feature: 'Resting Blood Pressure', value: Number(((vitals.restingBP - 120) * 0.003).toFixed(3)), featureValue: `${vitals.restingBP} mmHg` },
    { feature: 'Serum Cholesterol', value: Number(((vitals.cholesterol - 200) * 0.0015).toFixed(3)), featureValue: `${vitals.cholesterol} mg/dL` },
    { feature: 'Maximum Heart Rate Achieved', value: Number(((150 - vitals.maxHeartRate) * 0.002).toFixed(3)), featureValue: `${vitals.maxHeartRate} bpm` },
    { feature: 'Fluoroscopy Vessels (ca)', value: Number((vitals.ca * 0.09).toFixed(3)), featureValue: `${vitals.ca} major vessels` },
    { feature: 'Patient Age Factor', value: Number(((vitals.age - 50) * 0.004).toFixed(3)), featureValue: `${vitals.age} yrs` },
  ].sort((a, b) => Math.abs(b.value) - Math.abs(a.value));

  const nlpExplanation = riskScore > 0.65
    ? `Patient exhibits prominent ischemic markers: ST depression of ${vitals.oldPeak}mm with resting BP of ${vitals.restingBP} mmHg. Global federated model flags a ${Math.round(riskScore * 100)}% probability of acute cardiac compromise. Urgent cardiologist evaluation and stress angiography recommended.`
    : riskScore > 0.35
    ? `Patient demonstrates moderate cardiometabolic risk indicators (cholesterol ${vitals.cholesterol} mg/dL, borderline BP). 12-month follow-up recommended with lifestyle and lipid management.`
    : `Cardiovascular vitals within healthy reference limits (max heart rate ${vitals.maxHeartRate} bpm, normal ECG). Baseline risk estimated at ${Math.round(riskScore * 100)}%. Routine annual preventive screening advised.`;

  return {
    patientId: `PT-${Math.floor(100000 + Math.random() * 900000)}`,
    riskScore: Number(riskScore.toFixed(3)),
    riskLabel,
    confidence,
    shapValues,
    nlpExplanation,
    predictedAt: new Date().toISOString(),
  };
}

export const MOCK_INITIAL_PREDICTION: PredictionResult = computeMockPrediction({
  age: 63,
  sex: 1,
  chestPainType: 4,
  restingBP: 145,
  cholesterol: 233,
  fastingBloodSugar: 1,
  restingECG: 2,
  maxHeartRate: 150,
  exerciseAngina: 0,
  oldPeak: 2.3,
  slope: 3,
  ca: 0,
  thal: 6,
});

export const MOCK_FAIRNESS_REPORT: FairnessReport = {
  sessionId: 'TF-SESS-9082',
  overallScore: 0.948,
  generatedAt: new Date().toISOString(),
  subgroupResults: [
    { subgroup: 'Male Cohort', accuracy: 0.946, sampleSize: 4820, divergenceScore: 0.004 },
    { subgroup: 'Female Cohort', accuracy: 0.938, sampleSize: 3910, divergenceScore: 0.004 },
    { subgroup: 'Age < 55 Years', accuracy: 0.949, sampleSize: 4980, divergenceScore: 0.007 },
    { subgroup: 'Age >= 55 Years (Senior)', accuracy: 0.935, sampleSize: 3750, divergenceScore: 0.007 },
    { subgroup: 'Diabetic Subgroup (FBS > 120)', accuracy: 0.931, sampleSize: 1880, divergenceScore: 0.011 },
    { subgroup: 'Hypertensive (BP > 140 mmHg)', accuracy: 0.941, sampleSize: 3120, divergenceScore: 0.001 },
  ],
  flaggedIssues: [
    {
      severity: 'low',
      subgroup: 'Age >= 55 Years (Senior)',
      message: 'Subgroup accuracy gap is 1.4%, which is well within FDA/HIPAA SaMD fairness threshold (< 3.0%).',
      divergence: 0.014,
    },
  ],
};

export const MOCK_PRIVACY_REPORT: PrivacyReport = {
  sessionId: 'TF-SESS-9082',
  attackSuccessWithDP: 0.512,
  attackSuccessWithoutDP: 0.784,
  privacyResistance: 0.976,
  epsilon: 1.84,
  delta: 1e-5,
  heKeySize: 2048,
  paillierEnabled: true,
  generatedAt: new Date().toISOString(),
};

export const MOCK_COMPARISON_DATA = [
  {
    name: 'Centralized Baseline',
    desc: 'Pooled raw patient data in single cloud server (HIPAA Violation)',
    acc: '95.1%',
    loss: '0.162',
    fairness: '0.884',
    mia: '0.812',
    epsilon: 'None (Raw data shared)',
    he: 'No',
    privacyLevel: 'LOW',
    special: false,
  },
  {
    name: 'FedAvg (non-IID)',
    desc: 'Standard federated averaging without differential privacy',
    acc: '89.4%',
    loss: '0.245',
    fairness: '0.892',
    mia: '0.748',
    epsilon: 'None (Gradient leakage risk)',
    he: 'No',
    privacyLevel: 'MEDIUM',
    special: false,
  },
  {
    name: 'FedProx (μ=0.01)',
    desc: 'Heterogeneity-aware local proximal regularization',
    acc: '91.2%',
    loss: '0.218',
    fairness: '0.910',
    mia: '0.720',
    epsilon: 'None (Vulnerable to reconstruction)',
    he: 'Optional',
    privacyLevel: 'MEDIUM',
    special: false,
  },
  {
    name: 'TrustFed TEFL (Ours)',
    desc: 'Local DP-SGD + Secure Aggregation + Exact SHAP Fair Auditing',
    acc: '94.2%',
    loss: '0.184',
    fairness: '0.948',
    mia: '0.512',
    epsilon: '1.84 (Rényi DP Accountant)',
    he: '2048-bit Paillier',
    privacyLevel: 'BEST',
    special: true,
  },
];

export const MOCK_AUDIT_LOGS: AuditEntry[] = [
  {
    id: 'log-8901',
    timestamp: new Date().toISOString(),
    nodeId: 'node-bgh-01',
    eventType: 'tefl',
    description: 'Local DP-SGD gradient noise injected (sigma=1.12, clip=1.0, epsilon=1.84)',
    hash: '0x8f2a1b94e3c50971a5c6d2e8b1a3f7e9d0c2b4a6e8f1d3c5b7a9e1f3d5c7b9a1',
    metadata: { round: 5, hospital: 'Boston General Hospital', status: 'verified' },
  },
  {
    id: 'log-8902',
    timestamp: new Date(Date.now() - 15 * 60000).toISOString(),
    nodeId: 'node-agg-east',
    eventType: 'training',
    description: 'Round 5 Global Aggregation completed across 5 hospital nodes',
    hash: '0x7c1e3a9b2d4f6a8c0e2b4d6f8a0c2e4b6d8f0a2c4e6b8d0f2a4c6e8b0d2f4a6c',
    metadata: { round: 5, participants: 5, globalAccuracy: '94.2%' },
  },
  {
    id: 'log-8903',
    timestamp: new Date(Date.now() - 45 * 60000).toISOString(),
    nodeId: 'node-mayo-02',
    eventType: 'training',
    description: 'Homomorphic Paillier 2048-bit ciphertext transmitted to regional coordinator',
    hash: '0x3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e',
    metadata: { keySize: 2048, cyphertextBytes: 49152 },
  },
  {
    id: 'log-8904',
    timestamp: new Date(Date.now() - 90 * 60000).toISOString(),
    nodeId: 'node-bgh-01',
    eventType: 'prediction',
    description: 'Patient inference requested (Anonymized PT-648102) - Exact SHAP computed',
    hash: '0x1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b',
    metadata: { riskScore: 0.84, clinician: 'Dr. Sarah Chen' },
  },
  {
    id: 'log-8905',
    timestamp: new Date(Date.now() - 120 * 60000).toISOString(),
    nodeId: 'node-auth-srv',
    eventType: 'auth',
    description: 'Mutual TLS certificate validation & JWT issued to Dr. Sarah Chen',
    hash: '0x5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f',
    metadata: { role: 'hospital_staff', ipMasked: '10.240.***.***' },
  },
];
