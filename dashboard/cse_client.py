"""Read-only oneM2M client for the IEUM monitoring dashboard."""
from __future__ import annotations

import uuid
import json
import os
from typing import Any, Optional
from urllib.parse import quote

import requests


class CSEClient:
    def __init__(self) -> None:
        self.base_url = os.getenv(
            "IEUM_CSE_BASE_URL",
            "https://example.invalid/mn-cse",
        ).rstrip("/")
        self.origin = os.getenv("IEUM_CSE_ORIGIN", "CAdmin")
        self.rvi = os.getenv("IEUM_CSE_RVI", "3")
        self.verify_tls = os.getenv("IEUM_VERIFY_TLS", "false").lower() in ("1", "true", "yes")
        self.timeout = float(os.getenv("IEUM_CSE_TIMEOUT", "8"))
        self.session = requests.Session()

    def _headers(self) -> dict[str, str]:
        return {
            "X-M2M-Origin": self.origin,
            "X-M2M-RI": f"ieum-dashboard-{uuid.uuid4().hex[:16]}",
            "X-M2M-RVI": self.rvi,
            "Accept": "application/json",
        }

    def get_resource(self, resource_path: str, params: Optional[dict] = None) -> dict[str, Any]:
        path = resource_path.strip("/")
        url = f"{self.base_url}/{path}"
        response = self.session.get(
            url,
            headers=self._headers(),
            params=params,
            timeout=self.timeout,
            verify=self.verify_tls,
        )
        response.raise_for_status()
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise RuntimeError(f"응답이 JSON 형식이 아닙니다: {url}") from exc

    @staticmethod
    def _unwrap_cin(payload: dict[str, Any]) -> dict[str, Any]:
        if "m2m:cin" in payload:
            return payload["m2m:cin"]
        if "cin" in payload:
            return payload["cin"]
        # 일부 CSE 응답은 wrapper 없이 CIN 속성을 직접 반환할 수 있음
        return payload

    @staticmethod
    def _decode_content(cin: dict[str, Any]) -> Any:
        content = cin.get("con")
        if isinstance(content, str):
            try:
                return json.loads(content)
            except (json.JSONDecodeError, TypeError):
                return content
        return content

    def latest_cin(self, ae: str, container: str) -> dict[str, Any]:
        payload = self.get_resource(f"{quote(ae)}/{quote(container)}/la")
        cin = self._unwrap_cin(payload)
        cin["_decoded_con"] = self._decode_content(cin)
        return cin

    def container_children(self, ae: str, container: str) -> list[dict[str, Any]]:
        """Fetch container children using oneM2M resultContent=attributesAndChildResources (rcn=4)."""
        payload = self.get_resource(
            f"{quote(ae)}/{quote(container)}",
            params={"rcn": "4"},
        )
        root = payload.get("m2m:cnt", payload.get("cnt", payload))
        children = root.get("ch", []) if isinstance(root, dict) else []
        result: list[dict[str, Any]] = []
        for child in children if isinstance(children, list) else []:
            cin = child.get("m2m:cin", child.get("cin", child))
            if isinstance(cin, dict):
                cin["_decoded_con"] = self._decode_content(cin)
                result.append(cin)
        result.sort(key=lambda item: str(item.get("ct", item.get("lt", ""))))
        return result

    def health_check(self) -> tuple[bool, str]:
        try:
            self.latest_cin("SensorAE", "cnt_water_level")
            return True, "MN-CSE 연결 및 센서 CIN 조회 정상"

        except requests.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else "HTTP"
            return False, f"MN-CSE HTTP {code}: {exc}"

        except requests.RequestException as exc:
            return False, f"MN-CSE 통신 오류: {exc}"

        except Exception as exc:
            return False, f"MN-CSE 조회 오류: {exc}"

    def fetch_dashboard_data(self) -> dict[str, Any]:
        resources = {
            "sensor": ("SensorAE", "cnt_water_level"),
            "risk": ("RiskAnalysisAE", "cnt_risk_level"),
            "risk_history": ("RiskAnalysisAE", "cnt_risk_history"),
            "barrier": ("EdgeAE", "cnt_barrier_control"),
            "warning": ("EdgeAE", "cnt_warning_control"),
            "detour": ("EdgeAE", "cnt_detour_info"),
        }
        data: dict[str, Any] = {}
        errors: dict[str, str] = {}
        for key, (ae, container) in resources.items():
            try:
                data[key] = self.latest_cin(ae, container)
            except Exception as exc:
                data[key] = None
                errors[key] = str(exc)
        try:
            data["risk_history_items"] = self.container_children("RiskAnalysisAE", "cnt_risk_history")
        except Exception as exc:
            data["risk_history_items"] = []
            errors["risk_history"] = errors.get("risk_history", str(exc))
        data["errors"] = errors
        return data
