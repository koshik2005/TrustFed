#!/usr/bin/env python3
"""Run model evaluation with bootstrap 95% confidence intervals and update docs/MODEL_CARD.md.

Usage:
    python scripts/evaluate_model_bootstrap.py
"""
import os
import sys

# Add backend directory to path
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, backend_dir)

from services.evaluation import run_evaluation, generate_model_card

def main():
    print("Running bootstrap model evaluation (B=1,000 resamples on held-out test cohort N=216)...")
    report = run_evaluation(seed=42, n_bootstrap=1000)
    
    doc_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "docs",
        "MODEL_CARD.md"
    )
    generate_model_card(report, doc_path)
    
    print("=" * 60)
    print("TrustFed AI - Model Evaluation & Bootstrap 95% CIs")
    print("=" * 60)
    print(f"Model Version:         {report['modelVersion']}")
    print(f"Held-Out Test Samples: N = {report['testSetSize']}")
    print(f"Top-1 Accuracy:        {report['top1Accuracy']*100:.1f}% (95% CI: [{report['top1Accuracy_ci_95'][0]*100:.1f}%, {report['top1Accuracy_ci_95'][1]*100:.1f}%])")
    print(f"Top-3 Coverage:        {report['top3Accuracy']*100:.1f}% (95% CI: [{report['top3Accuracy_ci_95'][0]*100:.1f}%, {report['top3Accuracy_ci_95'][1]*100:.1f}%])")
    print(f"Macro-F1 Score:        {report['macroF1']:.3f} (95% CI: [{report['macroF1_ci_95'][0]:.3f}, {report['macroF1_ci_95'][1]:.3f}])")
    print(f"Macro-Precision:       {report['macroPrecision']:.3f} (95% CI: [{report['macroPrecision_ci_95'][0]:.3f}, {report['macroPrecision_ci_95'][1]:.3f}])")
    print(f"Macro-Recall:          {report['macroRecall']:.3f} (95% CI: [{report['macroRecall_ci_95'][0]:.3f}, {report['macroRecall_ci_95'][1]:.3f}])")
    print(f"Expected Cal. Error:   {report['expectedCalibrationError']:.4f} (95% CI: [{report['expectedCalibrationError_ci_95'][0]:.4f}, {report['expectedCalibrationError_ci_95'][1]:.4f}])")
    print("=" * 60)
    print("Per-Condition Performance Breakdown:")
    for code, d in report['perDisease'].items():
        flag = " [LOW CONFIDENCE: N < 20]" if d['low_confidence'] else ""
        print(f" - {d['name']} (N={d['support']}{flag}): F1 = {d['f1']:.3f} CI {d['f1_ci_95']}")
    print(f"\nModel Card updated at: {doc_path}")

if __name__ == "__main__":
    main()

