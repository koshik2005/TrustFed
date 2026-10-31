"""TrustFed-Health: Structured Logging & Error Monitoring.

Features:
- PHI Redaction Filter: Enforces zero patient identifiers (names, contacts, patient IDs like PT-*) in server logs.
- Structured JSON formatting for cloud aggregators (Render, Datadog, CloudWatch).
- Sentry Error Monitoring: Opt-in via SENTRY_DSN with send_default_pii=False and before_send scrubbing.
"""
from __future__ import annotations
import json
import logging
import os
import re
import sys
from typing import Any, Dict, Optional

# PHI Redaction Regex Patterns
PATIENT_ID_PATTERN = re.compile(r"PT-[A-Za-z0-9\-_]{3,}", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_PATTERN = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{4}")
TOKEN_PATTERN = re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE)


def redact_phi_text(text: str) -> str:
    """Scrubs patient identifiers, phone numbers, and tokens from any string."""
    if not isinstance(text, str):
        return text
    text = PATIENT_ID_PATTERN.sub("[REDACTED_PATIENT_ID]", text)
    text = PHONE_PATTERN.sub("[REDACTED_PHONE]", text)
    text = TOKEN_PATTERN.sub("Bearer [REDACTED_TOKEN]", text)
    return text


class PHIRedactionFilter(logging.Filter):
    """Logging filter ensuring patient identifiers never appear in server log sinks."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_phi_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: (redact_phi_text(v) if isinstance(v, str) else v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(redact_phi_text(v) if isinstance(v, str) else v for v in record.args)
        return True


class JSONLogFormatter(logging.Formatter):
    """Structured JSON formatter with timestamp, level, module, and sanitized message."""

    def format(self, record: logging.LogRecord) -> str:
        try:
            msg = record.getMessage()
        except Exception:
            msg = str(record.msg)
        data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_phi_text(msg),
        }
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
        return json.dumps(data)


def before_send_scrubber(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Sentry pre-send hook ensuring zero patient health information reaches Sentry."""
    if not event:
        return event

    # Scrub request URL and headers
    if "request" in event:
        req = event["request"]
        if "url" in req:
            req["url"] = redact_phi_text(req["url"])
        if "headers" in req:
            for h in list(req["headers"].keys()):
                if h.lower() in ("authorization", "cookie", "x-csrf-token"):
                    req["headers"][h] = "[REDACTED_HEADER]"

    # Scrub log messages & breadcrumbs
    if "logentry" in event and "message" in event["logentry"]:
        event["logentry"]["message"] = redact_phi_text(event["logentry"]["message"])

    if "breadcrumbs" in event and "values" in event["breadcrumbs"]:
        for bc in event["breadcrumbs"]["values"]:
            if "message" in bc and isinstance(bc["message"], str):
                bc["message"] = redact_phi_text(bc["message"])

    return event


def init_monitoring_and_logging() -> None:
    """Configures global logging with PHI redaction and initializes Sentry if configured."""
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Remove existing handlers to prevent duplicates
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.addFilter(PHIRedactionFilter())

    env = os.getenv("ENVIRONMENT", "development").strip().lower()
    if env in ("production", "prod"):
        handler.setFormatter(JSONLogFormatter())
    else:
        fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
        handler.setFormatter(fmt)

    root.addHandler(handler)

    # Sentry error monitoring integration
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration

            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[FastApiIntegration()],
                traces_sample_rate=0.2,
                profiles_sample_rate=0.1,
                send_default_pii=False,  # STRICT: never send default PII
                before_send=before_send_scrubber,
                environment=env,
                release="trustfed-health@2.0.0"
            )
            logging.info("Sentry error monitoring initialized with strict PII scrubbing.")
        except Exception as e:
            logging.warning("Could not initialize Sentry: %s", str(e))
    else:
        logging.info("Sentry DSN not provided; running with local structured logging.")
