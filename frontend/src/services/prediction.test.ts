import { describe, it, expect } from 'vitest';
import { computeMockPrediction } from './mockData';
import type { PatientVitals } from '../types';

describe('Clinical Risk Prediction Logic', () => {
  it('identifies high risk for symptomatic high-cholesterol cardiac patient', () => {
    const highRiskVitals: PatientVitals = {
      age: 67,
      sex: 1, // Male
      chestPainType: 4, // Asymptomatic / ischemic
      restingBP: 165,
      cholesterol: 310,
      fastingBloodSugar: 1,
      restingECG: 2,
      maxHeartRate: 110,
      exerciseAngina: 1,
      oldPeak: 3.2,
      slope: 2,
      ca: 2,
      thal: 7,
    };

    const result = computeMockPrediction(highRiskVitals);

    expect(result.riskScore).toBeGreaterThanOrEqual(0.65);
    expect(result.riskLabel).toBe('High');
    expect(result.shapValues.length).toBeGreaterThan(0);
    expect(result.nlpExplanation).toBeDefined();

    // Verify SHAP values contain clinically meaningful impact features
    const features = result.shapValues.map((s) => s.feature);
    expect(features).toContain('Chest Pain Classification');
    expect(features).toContain('ST Depression (Oldpeak)');
  });

  it('identifies low risk for young asymptomatic patient with normal vitals', () => {
    const lowRiskVitals: PatientVitals = {
      age: 28,
      sex: 0, // Female
      chestPainType: 1, // Typical
      restingBP: 110,
      cholesterol: 175,
      fastingBloodSugar: 0,
      restingECG: 0,
      maxHeartRate: 175,
      exerciseAngina: 0,
      oldPeak: 0.1,
      slope: 1,
      ca: 0,
      thal: 3,
    };

    const result = computeMockPrediction(lowRiskVitals);

    expect(result.riskScore).toBeLessThan(0.40);
    expect(result.riskLabel).toBe('Low');
    expect(result.confidence).toBeGreaterThan(0.70);
  });
});
