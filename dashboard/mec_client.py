"""Read-only MEC Sandbox API checks for the IEUM dashboard.

The READY notification was already sent manually and returned HTTP 204.
This module intentionally does NOT send confirm_ready again.
"""
from __future__ import annotations

import os
from typing import Any

import requests


class MECClient:
    def __init__(self) -> None:
        self.sandbox_prefix = os.getenv(
            "IEUM_MEC_SANDBOX_PREFIX",
            "",
        ).rstrip("/")
        self.platform = os.getenv("IEUM_MEC_PLATFORM", "mep1")
        self.app_name = os.getenv("IEUM_MEC_APP_NAME", "IEUM-Edge-Monitor")
        self.app_instance_id = os.getenv(
            "IEUM_MEC_APP_INSTANCE_ID",
            "Not configured",
        )
        self.app_support_base = (
            f"{self.sandbox_prefix}/{self.platform}/mec_app_support/v2"
        )
        # The API Console previously showed this exact endpoint returning 200.
        self.iot_api_url = (
            f"{self.sandbox_prefix}/{self.platform}/iots/v1/registered_iot_platforms"
        )
        self.verify_tls = os.getenv("IEUM_MEC_VERIFY_TLS", "false").lower() in ("1", "true", "yes")
        self.timeout = float(os.getenv("IEUM_MEC_TIMEOUT", "8"))
        self.session = requests.Session()
        token = os.getenv("IEUM_MEC_BEARER_TOKEN", "").strip()
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def check_registered_iot_platforms(self) -> dict[str, Any]:
        response = self.session.get(
            self.iot_api_url,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
            verify=self.verify_tls,
        )
        result: dict[str, Any] = {
            "url": self.iot_api_url,
            "http_status": response.status_code,
            "ok": response.status_code == 200,
        }
        if response.content:
            try:
                result["body"] = response.json()
            except ValueError:
                result["body"] = response.text[:2000]
        else:
            result["body"] = None
        if response.status_code >= 400:
            result["error"] = response.text[:1000]
        return result

    def status_summary(self) -> dict[str, Any]:
        return {
            "application_name": self.app_name,
            "application_instance_id": self.app_instance_id,
            "platform": self.platform,
            "ready_notification": "HTTP 204 확인됨 (2026-11-20)",
            "app_support_base": self.app_support_base,
        }
