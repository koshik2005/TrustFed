# Intended Use Specification

> [!CAUTION]
> **DRAFT, pending legal review.**  
> This specification documents the intended user population, clinical scope, and boundary limitations of the TrustFed software.

**Platform Identifier**: TrustFed General Disease Differential Decision Support  
**Version**: `v2.0.0` (`TF-GenDisease-v1.0`)  
**Deployment Mode**: Informational Mode (Educational / Research Prototype)

---

## 1. Who It Is For (Intended Audience)

TrustFed is designed and provided strictly for the following authorized user groups:
1. **Medical Students & Clinical Trainees**: As an interactive educational aid for learning differential diagnosis reasoning, symptom associations, and clinical lab correlation.
2. **Clinical Informaticians & ML Researchers**: For studying federated learning weight averaging (FedAvg), differential privacy guarantees (DP-SGD $\varepsilon \le 1.84$), and missing value handling in healthcare ML.
3. **Healthcare Educators**: As a pedagogical demonstration platform for multi-class triage, red-flag alert architectures, and explainable AI (SHAP-based clinical feature attributions).
4. **Clinical Decision Support Evaluators**: For participating institutions evaluating prospective shadow-mode triage software prior to clinical validation.

---

## 2. What It Is NOT For (Contraindications & Prohibited Uses)

TrustFed is strictly **NOT** intended or validated for the following uses:
1. **NOT for Primary Diagnosis**: It cannot replace formal medical evaluation, history taking, or physical examination.
2. **NOT a Medical Device**: It has not received regulatory clearance or certification (e.g. CDSCO, FDA, or CE mark) as a Software as a Medical Device (SaMD).
3. **NOT for Consumer Self-Treatment**: Non-clinicians must not use this system to self-diagnose, adjust dosages, or initiate self-medication.
4. **NOT for Acute Triage in Emergency Departments**: It must not be used to gate, delay, or prioritize emergency patient admissions.
5. **NOT for High-Risk Autonomous Decisions**: All algorithmic suggestions are labeled *"Pending Physician Review"* and require active, independent confirmation by an attending physician.

---

## 3. Emergency Medical Guidance

> [!WARNING]
> **TrustFed is not an emergency triage tool.**  
> In any situation involving life-threatening symptoms, acute trauma, severe respiratory distress, or stroke indicators, bypass the software and immediately contact emergency services:
> - **India**: `112`
> - **United States / Canada**: `911`
> - **United Kingdom**: `999`
> - **European Union**: `112`

