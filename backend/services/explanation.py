"""Clinical narrative: NVIDIA NIM (Llama 3.1) when a key is configured, deterministic template otherwise."""
import os
from dotenv import load_dotenv
from .inference import template_explanation

load_dotenv()


def generate_clinical_explanation(patient_data: dict, risk_score: float, shap_values: list) -> str:
    key = os.getenv("NVIDIA_API_KEY")
    fallback = template_explanation(patient_data, risk_score, shap_values)
    if not key:
        return fallback
    try:
        from openai import OpenAI
        client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=key, timeout=15)
        top = [{"feature": s["feature"], "value": s["featureValue"], "shap": round(s["value"], 3)} for s in shap_values[:6]]
        prompt = ("You are a clinical decision-support assistant. In at most 3 sentences, explain why a model predicted "
                  f"a {risk_score:.0%} heart-disease risk. Use ONLY these SHAP attributions (positive raises risk): {top}. "
                  "Do not invent findings and do not give a diagnosis.")
        out = client.chat.completions.create(model=os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct"),
                                             messages=[{"role": "user", "content": prompt}],
                                             temperature=0.2, max_tokens=150)
        return out.choices[0].message.content.strip()
    except Exception as e:                       # network / quota / key errors -> safe fallback
        print(f"[explanation] LLM unavailable ({e}); using template")
        return fallback
