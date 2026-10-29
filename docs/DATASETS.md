# TrustFed AI — Clinical Datasets & Evidence Documentation

This document describes the primary symptom-disease data sources, public clinical benchmarks, and synthetic supplements utilized for developing and benchmarking the General Disease Prediction platform in TrustFed AI.

---

## 1. Datasets Overview & Licenses

| Dataset Name | Source / Provider | License | Scope & Conditions | Primary Features |
| :--- | :--- | :--- | :--- | :--- |
| **Columbia University Symptom-Disease Knowledge Base** | PubMed Central / New York-Presbyterian Hospital (Wang et al.) | Open Access / Academic Fair Use | Multi-condition clinical associations across inpatient and ambulatory presentations | 130+ clinical symptoms mapped to ICD-9 / ICD-10 diagnostic categories |
| **Kaggle Symptom-Disease Tabular Benchmark** | Public Clinical Machine Learning Benchmark (curated from CDC & NHS symptom tables) | CC0: Public Domain / Open Data | 41 common acute & chronic conditions (Respiratory, Infectious, GI, Metabolic) | Binary presenting symptom vectors, severity weights |
| **UCI Cleveland Heart Disease Dataset** | UCI Machine Learning Repository (Detrano et al., V.A. Medical Center, Long Beach) | Creative Commons Attribution 4.0 International (CC BY 4.0) | Adult cardiovascular ischemic heart disease risk | 13 continuous & categorical hemodynamic parameters (BP, HR, ST depression, fluoroscopy, thal) |
| **TrustFed Synthetic Clinical Benchmark Supplement** | TrustFed Clinical Engineering Team (`backend/data/synthetic_clinical_supplement.json`) | Apache 2.0 (Internal Platform Component) | 18 general disease conditions with multi-system vitals, labs, and missingness masks | 35 symptoms, 7 physiological vitals (Temp, BP, HR, SpO2, RR, Glucose), and 3 labs (WBC, Platelets, Hb) |

---

## 2. Critical Clinical Limitations & Real-World Generalization Warning

> [!WARNING]
> ### CLINICAL HONESTY & GENERALIZATION CAUTION
> Many publicly available symptom-disease prediction datasets are **synthetic, crowd-sourced, or derived from idealized medical encyclopedia tables**. 
> 
> As a consequence:
> 1. **Overly Clean Presentations**: In textbook and toy datasets, patients present with 100% textbook signs (e.g., Dengue always exhibiting high fever, joint pain, and petechiae without conflicting confounders).
> 2. **Absence of Comorbidities**: Public datasets rarely account for co-occurring chronic conditions (e.g., an elderly diabetic with influenza and underlying renal failure).
> 3. **Real-World Clinical Accuracy is Lower**: In authentic emergency department and ambulatory triage workflows, patient-reported symptoms are noisy, subjective, and overlapping. A model scoring 95%+ top-3 accuracy on synthetic tables will exhibit lower fidelity in high-variance clinical settings.
> 4. **No Substitute for Clinical Judgment**: All model outputs are strictly intended for **Clinical Decision Support (CDS)**. Institutional validation against local, de-identified electronic health records (EHR) is mandatory before clinical deployment.

---

## 3. Configurable Disease Registry (18 Common Conditions)

TrustFed AI v2.0 evaluates multi-condition differential diagnosis across 18 high-incidence outpatient and acute care conditions:

1. **Common Cold** (`common_cold`): Upper airway viral rhinitis (rhinovirus, coronavirus).
2. **Influenza** (`influenza`): Seasonal orthomyxovirus infection with acute pyrexia, severe myalgia, and respiratory symptoms.
3. **Acute Viral Pyrexia** (`viral_fever`): Non-specific viral syndrome with constitutional malaise and fever.
4. **Dengue Fever** (`dengue`): Flavivirus transmitted by *Aedes aegypti* with retro-orbital headache, arthralgia, and risk of thrombocytopenia.
5. **Typhoid Enteric Fever** (`typhoid`): *Salmonella enterica* bacteremia with stepwise fever, abdominal tenderness, and bradycardia.
6. **Malaria** (`malaria`): *Plasmodium* infection characterized by paroxysmal chills, rigors, and sweats.
7. **COVID-19 / Acute Respiratory Illness** (`covid19`): SARS-CoV-2 presentation with cough, dyspnea, and anosmia/ageusia.
8. **Acute Gastroenteritis** (`gastroenteritis`): Infectious diarrhea, vomiting, abdominal cramping, and risk of dehydration.
9. **Urinary Tract Infection** (`uti`): Ascending bacterial cystitis with dysuria, urgency, and suprapubic pain.
10. **Community-Acquired Pneumonia** (`pneumonia`): Lower respiratory consolidation with fever, productive cough, and hypoxemia (SpO2 drop).
11. **Acute Bronchitis** (`bronchitis`): Self-limiting bronchial inflammation with persistent cough and retrosternal discomfort.
12. **Bronchial Asthma Exacerbation** (`asthma`): Reversible bronchospasm with expiratory wheezing and breathlessness.
13. **Essential Hypertension** (`hypertension`): Chronic systemic arterial hypertension (Systolic BP >= 140 or Diastolic BP >= 90).
14. **Type 2 Diabetes Mellitus** (`type2_diabetes`): Hyperglycemia with polyuria, polydipsia, and metabolic fatigue.
15. **Iron Deficiency / Nutritional Anemia** (`anemia`): Pallor, exertional dyspnea, chronic fatigue, and reduced hemoglobin.
16. **Migraine** (`migraine`): Unilateral pulsating headache with photophobia, phonophobia, and nausea.
17. **Allergic Rhinitis** (`allergic_rhinitis`): IgE-mediated nasal mucosal hypersensitivity with sneezing, clear rhinorrhea, and ocular itching.
18. **Coronary Artery Disease Risk** (`heart_disease`): Ischemic cardiac presentation with exertional chest pain, pressure, and dyspnea.

---

## 4. Synthetic Benchmark Supplement (`synthetic_clinical_supplement.json`)

To train, calibrate, and deterministically evaluate the general disease model across this 18-condition taxonomy:
- A dedicated synthetic supplement was engineered adhering to validated clinical phenotype distributions.
- **Missingness Handling**: Includes realistic rates of unmeasured vitals (e.g. 30% missing SpO2, 45% missing blood sugar, 60% missing platelet labs) paired with explicit binary missingness indicators (`is_missing_<feature>`).
- Kept strictly isolated in `backend/data/synthetic_clinical_supplement.json` to prevent contamination with local hospital datasets.
- Utilized for baseline model pre-training and deterministic calibration before federated on-node fine-tuning.
