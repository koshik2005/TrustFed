import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from services import inference

m = inference.load_model('backend/artifacts/pretrained_cleveland.npz')
presets = {
    'High Risk': dict(age=63, sex=1, chestPainType=4, restingBP=154, cholesterol=286, fastingBloodSugar=0, restingECG=2,
                      maxHeartRate=124, exerciseAngina=1, oldPeak=2.6, slope=2, ca=2, thal=7),
    'Moderate Risk': dict(age=55, sex=1, chestPainType=2, restingBP=135, cholesterol=240, fastingBloodSugar=0, restingECG=1,
                         maxHeartRate=140, exerciseAngina=1, oldPeak=1.2, slope=2, ca=0, thal=6),
    'Low Risk': dict(age=42, sex=0, chestPainType=1, restingBP=116, cholesterol=178, fastingBloodSugar=0, restingECG=0,
                     maxHeartRate=168, exerciseAngina=0, oldPeak=0.2, slope=1, ca=0, thal=3)
}

def test_clinical_presets():
    res_high = inference.predict(m, presets['High Risk'])
    assert res_high['riskLabel'] == 'High'
    assert res_high['riskScore'] > 0.90

    res_mod = inference.predict(m, presets['Moderate Risk'])
    assert res_mod['riskLabel'] == 'Medium'
    assert 0.35 <= res_mod['riskScore'] <= 0.65

    res_low = inference.predict(m, presets['Low Risk'])
    assert res_low['riskLabel'] == 'Low'
    assert res_low['riskScore'] < 0.10
    print("All clinical risk presets verified successfully!")

if __name__ == "__main__":
    test_clinical_presets()
