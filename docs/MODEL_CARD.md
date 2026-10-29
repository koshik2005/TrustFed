# Model Card: TrustFed AI General Disease Differential Inference Engine

**Model Identifier**: `TF-GenDisease-v1.0`  
**Architecture**: Calibrated Multinomial Diagnostic Linear Model ($W \in \mathbb{R}^{55 \times 18}, b \in \mathbb{R}^{18}$)  
**Task**: Multi-class differential diagnosis across 18 common outpatient and emergency conditions.  
**Federated Learning Compatibility**: Weight-averaging compatible (FedAvg & TEFL DP-SGD).

---

## 1. Multi-Dimensional Performance Summary

> [!IMPORTANT]
> **No Headline Accuracy Claim**: In accordance with rigorous clinical evaluation standards, TrustFed AI does not cite a single oversimplified headline accuracy metric. Clinical diagnostic performance is reported through multi-class Top-3 coverage, Macro-F1, and Expected Calibration Error (ECE).

| Metric | Held-Out Test Evaluation | Clinical Interpretation |
| :--- | :--- | :--- |
| **Top-3 Differential Coverage** | **86.1%** | In 86.1% of cases, the true diagnosis is included in the top-3 differential presented to the physician. |
| **Top-1 Strict Accuracy** | **61.1%** | Strict top-1 exact match on presenting clinical features. |
| **Macro-F1 Score** | **0.572** | Unweighted average harmonic mean across all 18 condition classes. |
| **Macro Precision** | **0.601** | Average positive predictive value across conditions. |
| **Macro Recall** | **0.599** | Average clinical sensitivity across conditions. |
| **Expected Calibration Error (ECE)** | **0.0919** | Quantifies probability calibration. Low ECE indicates predicted probabilities closely match empirical probabilities. |

---

## 2. Per-Condition Performance Breakdown

Evaluated on $N = 216$ held-out test cohort across all 18 clinical phenotypes:

| Disease Code | Clinical Condition Name | Test Support | Precision | Recall | F1-Score |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `common_cold` | Common Cold (Viral Rhinitis) | 11 | 0.000 | 0.000 | **0.000** |
| `influenza` | Influenza (Seasonal Flu) | 15 | 1.000 | 0.533 | **0.696** |
| `viral_fever` | Acute Viral Pyrexia | 8 | 0.000 | 0.000 | **0.000** |
| `dengue` | Dengue Fever (Breakbone Fever) | 12 | 0.440 | 0.917 | **0.595** |
| `typhoid` | Typhoid Enteric Fever | 10 | 0.556 | 0.500 | **0.526** |
| `malaria` | Malaria | 16 | 0.381 | 0.500 | **0.432** |
| `covid19` | COVID-19 / Acute Respiratory Illness | 17 | 1.000 | 0.765 | **0.867** |
| `gastroenteritis` | Acute Gastroenteritis | 10 | 0.571 | 0.400 | **0.471** |
| `uti` | Urinary Tract Infection | 19 | 0.933 | 0.737 | **0.824** |
| `pneumonia` | Community-Acquired Pneumonia | 12 | 0.412 | 0.583 | **0.483** |
| `bronchitis` | Acute Bronchitis | 14 | 0.643 | 0.643 | **0.643** |
| `asthma` | Bronchial Asthma Exacerbation | 12 | 1.000 | 0.333 | **0.500** |
| `hypertension` | Essential Hypertension | 9 | 0.500 | 1.000 | **0.667** |
| `type2_diabetes` | Type 2 Diabetes Mellitus | 9 | 0.556 | 0.556 | **0.556** |
| `anemia` | Iron Deficiency / Nutritional Anemia | 10 | 0.636 | 0.700 | **0.667** |
| `migraine` | Migraine / Vascular Cephalea | 10 | 0.750 | 0.900 | **0.818** |
| `allergic_rhinitis` | Allergic Rhinitis (Hay Fever) | 12 | 0.647 | 0.917 | **0.759** |
| `heart_disease` | Coronary Artery Disease (CAD) | 10 | 0.800 | 0.800 | **0.800** |

---

## 3. Probability Calibration (ECE & Reliability Bins)

Predicted probabilities are scaled using temperature calibration ($T = 1.0$). Bins evaluate confidence versus empirical accuracy:

| Confidence Bin | Sample Count | Mean Confidence | Empirical Accuracy | Calibration Gap |
| :---: | :---: | :---: | :---: | :---: |
| 0.1-0.2 | 3 | 0.173 | 0.333 | 0.160 |
| 0.2-0.3 | 11 | 0.257 | 0.273 | 0.016 |
| 0.3-0.4 | 24 | 0.354 | 0.292 | 0.062 |
| 0.4-0.5 | 24 | 0.449 | 0.542 | 0.093 |
| 0.5-0.6 | 26 | 0.543 | 0.500 | 0.043 |
| 0.6-0.7 | 21 | 0.643 | 0.524 | 0.119 |
| 0.7-0.8 | 22 | 0.747 | 0.636 | 0.111 |
| 0.8-0.9 | 24 | 0.852 | 0.833 | 0.019 |
| 0.9-1.0 | 61 | 0.967 | 0.820 | 0.147 |

---

## 4. Native Missingness Handling & Adaptive Questioning

1. **Native Missingness Indicators**: Continuous vitals (Temp, BP, HR, SpO2, Resp Rate, Glucose) and labs (Platelets, WBC) are accompanied by binary indicators (`is_missing_<feature>`). Rather than imputing with artifacts, the model learns the clinical context of missing diagnostic investigations.
2. **Adaptive Questioning**: When top-1 probability is below 0.65, the inference engine computes the Expected Information Gain (EIG) over currently unmeasured parameters and surfaces the single most decisive observation to the clinician (e.g., *"Add SpO2 to improve this result"*).

---

## 5. Red-Flag Safety Overrides

The model is bound by deterministic clinical safety guardrails ([red_flags.py](file:///d:/projects/TrustFed/backend/services/red_flags.py)) that trigger immediate urgent warnings overriding routine ambulatory outputs:
- **Acute Coronary Syndrome (ACS)**: Chest pain with diaphoresis, dyspnea, tachycardia, or ST deviation.
- **Severe Hypoxemia**: Measured $\text{SpO}_2 < 92\%$.
- **Acute Stroke**: Positive FAST neurological indicators (facial droop, arm weakness, speech difficulty).
- **Suspected Meningitis**: Pyrexia combined with nuchal rigidity / neck stiffness.
- **High Fever in Infant**: Age $< 1$ year with core temperature $\ge 38.5^\circ\text{C}$.
- **Hypovolemic Shock**: Severe dehydration from vomiting/diarrhea with systolic $\text{BP} < 90\text{ mmHg}$.

---

## 6. Known Limitations & Clinical Caution

1. **Synthetic & Clean Baseline Cohort**: The baseline pre-training supplement was generated from validated medical phenotype distributions. Real-world emergency room presentations involve complex polypharmacy, multi-morbidity, and inconsistent patient histories.
2. **Ambulatory vs Emergency Triage**: Model weights represent initial clinical triage likelihoods and must never replace diagnostic investigations (cultures, imaging, ECG).
3. **Mandatory Clinician Verification**: All suggested causes and remedies are labeled: *"Suggested, clinician must verify."*
