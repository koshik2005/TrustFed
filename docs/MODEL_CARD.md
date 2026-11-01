# Model Card: TrustFed AI General Disease Differential Inference Engine

**Model Identifier**: `TF-GenDisease-v1.0`  
**Architecture**: Calibrated Multinomial Diagnostic Linear Model ($W \in \mathbb{R}^{55 \times 18}, b \in \mathbb{R}^{18}$)  
**Task**: Multi-class differential diagnosis across 18 common outpatient and emergency conditions.  
**Federated Learning Compatibility**: Weight-averaging compatible (FedAvg & TEFL DP-SGD).  
**Dataset Origin**: Public (UCI ML Repository) + Synthetic Supplement Cohort (N=1,080)  
**Status**: **Prototype Decision Support Benchmark - Not Clinically Validated**

---

## 1. Multi-Dimensional Performance Summary (with Bootstrap 95% Confidence Intervals)

> [!IMPORTANT]
> **No Headline Accuracy Claim & Rigorous Statistical Reporting**: In accordance with clinical machine learning evaluation standards, TrustFed AI reports all primary metrics alongside non-parametric bootstrap 95% confidence intervals ($B = 1000$ iterations on held-out test cohort $N = 216$).

| Metric | Point Estimate | Bootstrap 95% CI | Clinical Interpretation |
| :--- | :---: | :---: | :--- |
| **Top-3 Differential Coverage** | **86.1%** | [81.9%, 90.7%] | In 86.1% of cases, the true diagnosis is included in the top-3 differential presented to the physician. |
| **Top-1 Strict Accuracy** | **61.1%** | [54.6%, 67.1%] | Strict top-1 exact match on presenting clinical features. |
| **Macro-F1 Score** | **0.572** | [0.504, 0.624] | Unweighted average harmonic mean across all 18 condition classes. |
| **Macro Precision** | **0.601** | [0.543, 0.651] | Average positive predictive value across conditions. |
| **Macro Recall** | **0.599** | [0.541, 0.657] | Average clinical sensitivity across conditions. |
| **Expected Calibration Error (ECE)** | **0.0919** | [0.0690, 0.1660] | Quantifies probability calibration. Low ECE indicates predicted probabilities closely match empirical probabilities. |

---

## 2. Per-Condition Performance Breakdown & Sample Count Audit

Evaluated on $N = 216$ held-out test cohort across all 18 clinical phenotypes.  
> [!WARNING]
> **Low-Confidence Flag ($N < 20$)**: In accordance with Phase E clinical safety standards, any disease category with fewer than 20 held-out test samples is explicitly flagged as **"low confidence"**. Such metrics should be interpreted with clinical caution pending larger consortium cohorts.

| Disease Code | Clinical Condition Name | Test Support ($N$) | Confidence Tier | Precision (95% CI) | Recall (95% CI) | F1-Score (95% CI) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `common_cold` | Common Cold (Viral Rhinitis) | 11 | ⚠️ low confidence | 0.000 [0.00, 0.00] | 0.000 [0.00, 0.00] | **0.000** [0.00, 0.00] |
| `influenza` | Influenza (Seasonal Flu) | 15 | ⚠️ low confidence | 1.000 [1.00, 1.00] | 0.533 [0.26, 0.79] | **0.696** [0.41, 0.88] |
| `viral_fever` | Acute Viral Pyrexia | 8 | ⚠️ low confidence | 0.000 [0.00, 0.00] | 0.000 [0.00, 0.00] | **0.000** [0.00, 0.00] |
| `dengue` | Dengue Fever (Breakbone Fever) | 12 | ⚠️ low confidence | 0.440 [0.25, 0.64] | 0.917 [0.73, 1.00] | **0.595** [0.39, 0.76] |
| `typhoid` | Typhoid Enteric Fever | 10 | ⚠️ low confidence | 0.556 [0.25, 0.88] | 0.500 [0.20, 0.83] | **0.526** [0.22, 0.78] |
| `malaria` | Malaria | 16 | ⚠️ low confidence | 0.381 [0.16, 0.60] | 0.500 [0.23, 0.75] | **0.432** [0.19, 0.61] |
| `covid19` | COVID-19 / Acute Respiratory Illness | 17 | ⚠️ low confidence | 1.000 [1.00, 1.00] | 0.765 [0.54, 0.94] | **0.867** [0.70, 0.97] |
| `gastroenteritis` | Acute Gastroenteritis | 10 | ⚠️ low confidence | 0.571 [0.17, 1.00] | 0.400 [0.11, 0.75] | **0.471** [0.13, 0.74] |
| `uti` | Urinary Tract Infection | 19 | ⚠️ low confidence | 0.933 [0.75, 1.00] | 0.737 [0.53, 0.93] | **0.824** [0.65, 0.94] |
| `pneumonia` | Community-Acquired Pneumonia | 12 | ⚠️ low confidence | 0.412 [0.18, 0.67] | 0.583 [0.30, 0.88] | **0.483** [0.23, 0.71] |
| `bronchitis` | Acute Bronchitis | 14 | ⚠️ low confidence | 0.643 [0.38, 0.89] | 0.643 [0.38, 0.91] | **0.643** [0.40, 0.83] |
| `asthma` | Bronchial Asthma Exacerbation | 12 | ⚠️ low confidence | 1.000 [1.00, 1.00] | 0.333 [0.09, 0.64] | **0.500** [0.17, 0.78] |
| `hypertension` | Essential Hypertension | 9 | ⚠️ low confidence | 0.500 [0.25, 0.75] | 1.000 [1.00, 1.00] | **0.667** [0.40, 0.86] |
| `type2_diabetes` | Type 2 Diabetes Mellitus | 9 | ⚠️ low confidence | 0.556 [0.20, 0.90] | 0.556 [0.21, 0.90] | **0.556** [0.22, 0.82] |
| `anemia` | Iron Deficiency / Nutritional Anemia | 10 | ⚠️ low confidence | 0.636 [0.29, 0.90] | 0.700 [0.40, 1.00] | **0.667** [0.38, 0.86] |
| `migraine` | Migraine / Vascular Cephalea | 10 | ⚠️ low confidence | 0.750 [0.50, 1.00] | 0.900 [0.67, 1.00] | **0.818** [0.61, 0.97] |
| `allergic_rhinitis` | Allergic Rhinitis (Hay Fever) | 12 | ⚠️ low confidence | 0.647 [0.41, 0.88] | 0.917 [0.73, 1.00] | **0.759** [0.55, 0.91] |
| `heart_disease` | Coronary Artery Disease (CAD) | 10 | ⚠️ low confidence | 0.800 [0.50, 1.00] | 0.800 [0.50, 1.00] | **0.800** [0.50, 0.96] |

---

## 3. Probability Calibration (ECE & Reliability Diagram)

Expected Calibration Error (ECE): **0.0919** (95% CI: [0.0690, 0.1660]).  
Predicted probabilities are calibrated via temperature scaling ($T = 1.0$). Bins evaluate confidence versus empirical accuracy:

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

### Reliability Diagram (Visual Calibration Chart)

```text
Confidence Bin | Samples | Conf   | Acc    | Reliability Chart (C = Mean Conf, A = Empirical Acc)
---------------+---------+--------+--------+-------------------------------------------------------
0.1-0.2        |       3 | 0.173  | 0.333  | [     C   A                    ]
0.2-0.3        |      11 | 0.257  | 0.273  | [       CA                     ]
0.3-0.4        |      24 | 0.354  | 0.292  | [        A C                   ]
0.4-0.5        |      24 | 0.449  | 0.542  | [             C  A             ]
0.5-0.6        |      26 | 0.543  | 0.500  | [               AC             ]
0.6-0.7        |      21 | 0.643  | 0.524  | [               A   C          ]
0.7-0.8        |      22 | 0.747  | 0.636  | [                   A  C       ]
0.8-0.9        |      24 | 0.852  | 0.833  | [                        AC    ]
0.9-1.0        |      61 | 0.967  | 0.820  | [                        A    C]
---------------+---------+--------+--------+-------------------------------------------------------
Legend: [C = Mean Predicted Confidence, A = Empirical Accuracy, * = Perfect Alignment]
```

---

## 4. Promotion Gate Specification

Model updates in federated rounds or retraining cycles must pass the statistical **Promotion Gate** ([promotion_gate.py](file:///d:/projects/TrustFed/backend/services/promotion_gate.py)) before deployment:
1. **Macro-F1 Improvement CI**: The LOWER bound of the bootstrap 95% CI of $\Delta \text{Macro-F1}$ must be strictly positive ($	ext{CI}_{	ext{lower}} > 0$). Tiny, statistically insignificant gains (where $\text{CI}_{\text{lower}} \le 0$) are rejected.
2. **Zero Severe Regression**: No single disease condition may experience a recall drop greater than $2.0\%$.
3. **No Fairness Degradation**: Disparity across demographic groups (e.g. biological sex) must not increase by more than $1.0\%$.

---

## 5. Red-Flag Safety Overrides

The model is bound by deterministic clinical safety guardrails ([red_flags.py](file:///d:/projects/TrustFed/backend/services/red_flags.py)) and canonical constants ([red_flag_constants.py](file:///d:/projects/TrustFed/backend/core/red_flag_constants.py)).  
All rules are labeled **"pending physician review"**:
- **Acute Coronary Syndrome (ACS)**: Chest pain with diaphoresis, dyspnea, tachycardia ($\text{HR} \ge 120\text{ bpm}$), or ST deviation.
- **Severe Hypoxemia**: Measured $\text{SpO}_2 < 92.0\%$.
- **Acute Stroke (FAST)**: Positive FAST neuro-deficit indicators (facial droop, arm weakness, speech difficulty).
- **Suspected Meningitis**: Pyrexia combined with nuchal rigidity / stiff neck.
- **High Fever in Infant**: Age $\le 1\text{ year}$ with temperature $\ge 38.5^\circ\text{C}$.
- **Hypovolemic Shock**: Fluid loss (vomiting/diarrhea) with systolic $\text{BP} < 90\text{ mmHg}$ or tachycardia.
- **Hypertensive Crisis**: Systolic $\text{BP} \ge 180\text{ mmHg}$ or diastolic $\text{BP} \ge 120\text{ mmHg}$.
- **Critical Bradycardia**: Resting heart rate $\text{HR} < 40\text{ bpm}$.

---

## 6. Known Limitations & Clinical Caution

1. **Synthetic & Public Benchmark Cohort**: Pre-training baseline incorporates public UCI repository data and synthetic clinical supplement ($N=1,080$).
2. **Prototype Benchmark Status**: This service is an informational/educational prototype benchmark, NOT a clinically validated diagnostic device.
3. **Mandatory Clinician Verification**: All suggested causes and remedies are labeled: *"Suggested, clinician must verify."*
