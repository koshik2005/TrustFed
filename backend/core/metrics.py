"""Performance & Latency Metrics Collector.

Provides thread-safe collection and calculation of endpoint latencies,
specifically p50, p95, and p99 percentiles for prediction endpoints (/predict).
"""
from __future__ import annotations
import math
import threading
import time
from collections import deque
from typing import Any, Dict, List, Optional


class LatencyTracker:
    """Thread-safe sliding-window latency tracker for response times."""

    def __init__(self, max_samples: int = 5000):
        self._max_samples = max_samples
        self._samples: deque[float] = deque(maxlen=max_samples)
        self._lock = threading.Lock()
        self._total_requests = 0
        self._error_requests = 0

    def record(self, duration_ms: float, is_error: bool = False) -> None:
        """Record a latency measurement in milliseconds."""
        with self._lock:
            self._samples.append(duration_ms)
            self._total_requests += 1
            if is_error:
                self._error_requests += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Compute summary statistics including p50, p95, and p99."""
        with self._lock:
            count = len(self._samples)
            total = self._total_requests
            errors = self._error_requests
            if count == 0:
                return {
                    "total_requests": total,
                    "error_requests": errors,
                    "error_rate": 0.0,
                    "sample_count": 0,
                    "p50_ms": 0.0,
                    "p95_ms": 0.0,
                    "p99_ms": 0.0,
                    "avg_ms": 0.0,
                    "min_ms": 0.0,
                    "max_ms": 0.0,
                }
            sorted_samples = sorted(self._samples)

        def percentile(p: float) -> float:
            if not sorted_samples:
                return 0.0
            k = (len(sorted_samples) - 1) * p
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return round(sorted_samples[int(k)], 2)
            d0 = sorted_samples[int(f)] * (c - k)
            d1 = sorted_samples[int(c)] * (k - f)
            return round(d0 + d1, 2)

        avg_val = sum(sorted_samples) / count
        error_rate = (errors / total) if total > 0 else 0.0

        return {
            "total_requests": total,
            "error_requests": errors,
            "error_rate": round(error_rate, 4),
            "sample_count": count,
            "p50_ms": percentile(0.50),
            "p95_ms": percentile(0.95),
            "p99_ms": percentile(0.99),
            "avg_ms": round(avg_val, 2),
            "min_ms": round(sorted_samples[0], 2),
            "max_ms": round(sorted_samples[-1], 2),
        }

    def reset(self) -> None:
        """Reset internal metrics."""
        with self._lock:
            self._samples.clear()
            self._total_requests = 0
            self._error_requests = 0


# Global tracker for /predict and /clinical/predict
predict_latency_tracker = LatencyTracker(max_samples=10000)

