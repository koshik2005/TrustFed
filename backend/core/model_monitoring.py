"""TrustFed-Health: Model Monitoring & Distribution Drift Detection.

Tracks:
1. Active model versions in production.
2. Top-3 confidence distribution (running mean, min, max, and quartile histogram bins).
3. Daily red-flag occurrences and clinician override share.
4. Statistical drift detection against safety and calibration thresholds.
"""
from __future__ import annotations
import datetime
import logging
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger("trustfed.model_monitoring")

# Safety & Drift Thresholds
DEFAULT_THRESHOLDS = {
    "min_top1_mean_confidence": 0.50,       # Alert if mean top prediction confidence falls below 50%
    "max_red_flag_override_share": 0.30,    # Alert if clinicians override >30% of emergency red-flag triggers
    "max_top1_confidence_drop": 0.20,       # Alert if mean confidence degrades by >20% day-over-day
    "min_inferences_for_alert": 5           # Minimum samples before evaluating statistical drift alerts
}


class ModelMonitoringService:
    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        self._lock = threading.Lock()
        self.thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
        self.reset()

    def reset(self) -> None:
        """Reset all in-memory monitoring statistics (useful for tests and daily baselines)."""
        with self._lock:
            self.total_inferences = 0
            self.model_versions: Dict[str, int] = {}
            self.confidence_bins = {
                "low (<0.50)": 0,
                "medium (0.50-0.70)": 0,
                "high (0.70-0.90)": 0,
                "very_high (>=0.90)": 0,
            }
            self.top1_sum = 0.0
            self.top2_sum = 0.0
            self.top3_sum = 0.0
            self.total_red_flags = 0
            self.total_red_flag_overrides = 0
            # Daily aggregation: key = "YYYY-MM-DD"
            self.daily_stats: Dict[str, Dict[str, Any]] = {}

    def record_inference(
        self,
        model_version: str,
        top3_confidences: List[float],
        has_red_flag: bool = False,
        is_red_flag_overridden: bool = False,
        timestamp: Optional[datetime.datetime] = None
    ) -> None:
        """Records inference event metadata including top-3 confidences and red flag actions."""
        ts = timestamp or datetime.datetime.now(datetime.timezone.utc)
        date_str = ts.strftime("%Y-%m-%d")

        # Sanitize confidences
        c1 = float(top3_confidences[0]) if len(top3_confidences) > 0 else 0.0
        c2 = float(top3_confidences[1]) if len(top3_confidences) > 1 else 0.0
        c3 = float(top3_confidences[2]) if len(top3_confidences) > 2 else 0.0

        with self._lock:
            self.total_inferences += 1
            self.model_versions[model_version] = self.model_versions.get(model_version, 0) + 1

            self.top1_sum += c1
            self.top2_sum += c2
            self.top3_sum += c3

            # Binning top-1 confidence
            if c1 < 0.50:
                self.confidence_bins["low (<0.50)"] += 1
            elif c1 < 0.70:
                self.confidence_bins["medium (0.50-0.70)"] += 1
            elif c1 < 0.90:
                self.confidence_bins["high (0.70-0.90)"] += 1
            else:
                self.confidence_bins["very_high (>=0.90)"] += 1

            if has_red_flag:
                self.total_red_flags += 1
            if is_red_flag_overridden:
                self.total_red_flag_overrides += 1

            # Daily stats
            if date_str not in self.daily_stats:
                self.daily_stats[date_str] = {
                    "date": date_str,
                    "inferences": 0,
                    "top1_sum": 0.0,
                    "red_flags": 0,
                    "red_flag_overrides": 0
                }
            day = self.daily_stats[date_str]
            day["inferences"] += 1
            day["top1_sum"] += c1
            if has_red_flag:
                day["red_flags"] += 1
            if is_red_flag_overridden:
                day["red_flag_overrides"] += 1

        logger.info(
            "[MODEL_MONITORING] model=%s top3=[%.3f, %.3f, %.3f] red_flag=%s override=%s date=%s",
            model_version, c1, c2, c3, has_red_flag, is_red_flag_overridden, date_str
        )

    def record_override(self, date_str: Optional[str] = None) -> None:
        """Record an explicit doctor override of a previous red-flag warning."""
        dt_key = date_str or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        with self._lock:
            self.total_red_flag_overrides += 1
            if dt_key in self.daily_stats:
                self.daily_stats[dt_key]["red_flag_overrides"] += 1
        logger.info("[MODEL_MONITORING] Doctor override recorded for date=%s", dt_key)

    def get_monitoring_report(self) -> Dict[str, Any]:
        """Generates real-time report on model versions, confidence distribution, override rates, and drift alerts."""
        with self._lock:
            total = self.total_inferences
            mean_c1 = (self.top1_sum / total) if total > 0 else 0.0
            mean_c2 = (self.top2_sum / total) if total > 0 else 0.0
            mean_c3 = (self.top3_sum / total) if total > 0 else 0.0

            override_share = (self.total_red_flag_overrides / self.total_red_flags) if self.total_red_flags > 0 else 0.0

            daily_list = []
            for d in sorted(self.daily_stats.keys(), reverse=True):
                info = self.daily_stats[d]
                d_inf = info["inferences"]
                d_rf = info["red_flags"]
                d_ovr = info["red_flag_overrides"]
                daily_list.append({
                    "date": d,
                    "inferences": d_inf,
                    "mean_top1_confidence": round(info["top1_sum"] / d_inf, 4) if d_inf > 0 else 0.0,
                    "red_flags": d_rf,
                    "red_flag_overrides": d_ovr,
                    "red_flag_override_share": round(d_ovr / d_rf, 4) if d_rf > 0 else 0.0
                })

            # Check drift alerts
            alerts = []
            min_samples = int(self.thresholds["min_inferences_for_alert"])

            if total >= min_samples:
                # 1. Low confidence drift check
                if mean_c1 < self.thresholds["min_top1_mean_confidence"]:
                    alerts.append({
                        "metric": "top1_mean_confidence",
                        "severity": "CRITICAL",
                        "current": round(mean_c1, 4),
                        "threshold": self.thresholds["min_top1_mean_confidence"],
                        "message": f"Top-1 mean confidence ({mean_c1:.2%}) dropped below safety threshold ({self.thresholds['min_top1_mean_confidence']:.2%})."
                    })

                # 2. Excessive red-flag override rate check
                if self.total_red_flags >= min_samples and override_share > self.thresholds["max_red_flag_override_share"]:
                    alerts.append({
                        "metric": "red_flag_override_share",
                        "severity": "WARNING",
                        "current": round(override_share, 4),
                        "threshold": self.thresholds["max_red_flag_override_share"],
                        "message": f"Clinician red-flag override rate ({override_share:.2%}) exceeded safety threshold ({self.thresholds['max_red_flag_override_share']:.2%})."
                    })

                # 3. Day-over-day drift check
                if len(daily_list) >= 2 and daily_list[0]["inferences"] >= min_samples and daily_list[1]["inferences"] >= min_samples:
                    recent = daily_list[0]["mean_top1_confidence"]
                    prior = daily_list[1]["mean_top1_confidence"]
                    if prior - recent > self.thresholds["max_top1_confidence_drop"]:
                        alerts.append({
                            "metric": "day_over_day_confidence_drop",
                            "severity": "WARNING",
                            "current": round(prior - recent, 4),
                            "threshold": self.thresholds["max_top1_confidence_drop"],
                            "message": f"Significant day-over-day confidence degradation of {(prior - recent):.2%} detected."
                        })

            return {
                "status": "ok",
                "summary": {
                    "total_inferences": total,
                    "active_models": self.model_versions,
                    "mean_top1_confidence": round(mean_c1, 4),
                    "mean_top2_confidence": round(mean_c2, 4),
                    "mean_top3_confidence": round(mean_c3, 4),
                    "total_red_flags": self.total_red_flags,
                    "red_flag_overrides": self.total_red_flag_overrides,
                    "red_flag_override_share": round(override_share, 4)
                },
                "confidence_distribution": self.confidence_bins,
                "daily_metrics": daily_list,
                "drift_status": {
                    "has_alerts": len(alerts) > 0,
                    "alert_count": len(alerts),
                    "alerts": alerts,
                    "thresholds": self.thresholds
                }
            }


# Singleton service instance
model_monitor = ModelMonitoringService()
