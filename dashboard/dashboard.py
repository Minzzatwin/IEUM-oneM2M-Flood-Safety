
"""IEUM MEC + oneM2M Monitoring Dashboard (Read-only)."""
from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

from cse_client import CSEClient
from mec_client import MECClient


# =========================================================
# 1. Page configuration
# =========================================================

st.set_page_config(
    page_title="IEUM Edge Monitor",
    page_icon="🌧️",
    layout="wide",
    initial_sidebar_state="expanded",
)

RISK_LABELS = {
    "NORMAL": "Normal",
    "CAUTION": "Caution",
    "WARNING": "Caution",
    "DANGER": "Danger",
    "EMERGENCY": "Emergency",
    "INCOMPLETE": "Incomplete Sensor Data",
}


# =========================================================
# 2. Utility functions
# =========================================================

def decode_con(cin: dict[str, Any] | None) -> Any:
    """Decode the oneM2M CIN content (con) into JSON when possible."""
    if not cin:
        return None

    if "_decoded_con" in cin:
        return cin["_decoded_con"]

    value = cin.get("con")

    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    return value


def as_dict(value: Any) -> dict[str, Any]:
    """Return a dictionary or an empty dictionary."""
    if isinstance(value, dict):
        return value
    return {}


def first(
    data: dict[str, Any],
    *keys: str,
    default: Any = "—",
) -> Any:
    """Return the first available, non-null field."""
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return default


def pretty(value: Any) -> str:
    """Convert values into readable display strings."""
    if value is None:
        return "—"

    if isinstance(value, bool):
        return "ON" if value else "OFF"

    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)

    return str(value)


def normalize_risk(value: Any) -> str:
    """Convert internal risk codes into readable English labels."""
    raw = str(value or "—").upper()
    return RISK_LABELS.get(raw, str(value or "—"))


def render_json_expander(title: str, value: Any) -> None:
    """Display raw API/CIN data in an expandable section."""
    with st.expander(title):
        st.json(
            value if value is not None
            else {"message": "No data available"}
        )


# =========================================================
# 3. Dashboard header and settings
# =========================================================

st.title("IEUM Edge Monitor")

st.caption(
    "Integrated monitoring of MEC Application status, "
    "oneM2M sensor data, Edge risk analysis, and control commands. "
    "This dashboard is read-only."
)

with st.sidebar:
    st.subheader("Dashboard Settings")

    refresh_seconds = st.number_input(
        "Auto-refresh interval (seconds)",
        min_value=0,
        max_value=300,
        value=5,
        step=1,
    )

    show_raw = st.checkbox(
        "Show raw CIN / API responses",
        value=False,
    )

    st.caption(
        "Set the interval to 0 to disable automatic refresh."
    )

    st.divider()

    st.caption(
        "This dashboard does not generate control commands "
        "or directly operate physical devices."
    )


# =========================================================
# 4. Initialize MEC and oneM2M clients
# =========================================================

mec = MECClient()
cse = CSEClient()


# =========================================================
# 5. Retrieve MEC Application information
# =========================================================

mec_summary: dict[str, Any] = {
    "application_name": "Unavailable",
    "platform": "Unavailable",
    "application_instance_id": "Unavailable",
    "ready_notification": "Unknown",
}

mec_summary_error: str | None = None

try:
    mec_summary = mec.status_summary()
except Exception as exc:
    mec_summary_error = str(exc)


mec_result: dict[str, Any] | None = None
mec_error: str | None = None

try:
    mec_result = mec.check_registered_iot_platforms()
except Exception as exc:
    mec_error = str(exc)


# =========================================================
# 6. Retrieve Hosted MN-CSE data
# =========================================================

cse_ok = False
cse_message = "Connection status unavailable"

data: dict[str, Any] = {}
data_error: str | None = None
data_ok = False

try:
    cse_ok, cse_message = cse.health_check()
except Exception as exc:
    cse_message = str(exc)

if cse_ok:
    try:
        data = cse.fetch_dashboard_data()
        data_ok = True
    except Exception as exc:
        data_error = str(exc)


# =========================================================
# 7. Connection status
# =========================================================

st.subheader("Connection Status")

m1, m2, m3 = st.columns(3)

with m1:
    st.metric(
        "MEC Application",
        mec_summary.get("application_name", "Unavailable"),
    )

    st.caption(
        f'{mec_summary.get("platform", "Unavailable")} '
        f'· {mec_summary.get("application_instance_id", "Unavailable")}'
    )

    if mec_summary_error:
        st.caption(f"Application information error: {mec_summary_error}")


with m2:
    if mec_result and mec_result.get("ok"):
        st.metric("MEC Service API", "Connected")
        st.caption("registered_iot_platforms query successful")

    elif mec_result:
        status = mec_result.get("http_status", "Error")
        st.metric("MEC Service API", f"HTTP {status}")
        st.caption("Check the API response, authentication, or endpoint.")

    else:
        st.metric("MEC Service API", "Connection Failed")
        st.caption(mec_error or "No response received")


with m3:
    st.metric(
        "Hosted MN-CSE",
        "Connected" if cse_ok else "Connection Failed",
    )
    st.caption(cse_message)


ready_status = mec_summary.get(
    "ready_notification",
    "Unknown",
)

st.info(
    f"Application READY notification: {ready_status}. "
    "This represents the previously confirmed notification record; "
    "the READY API is not called again on every refresh."
)


# =========================================================
# 8. Sensor, risk analysis, and Edge control data
# =========================================================

st.divider()
st.subheader("Sensor Data & Edge Analysis")

if not cse_ok:
    st.error(
        "Unable to connect to Hosted MN-CSE. "
        "Sensor, risk, and control data cannot be retrieved."
    )
    st.code(cse_message)

elif not data_ok:
    st.error(
        "Connected to Hosted MN-CSE, but failed to retrieve dashboard data."
    )
    st.code(data_error or "Unknown data retrieval error")

else:
    # -----------------------------------------------------
    # Decode latest CIN contents
    # -----------------------------------------------------

    sensor = as_dict(decode_con(data.get("sensor")))
    risk = as_dict(decode_con(data.get("risk")))
    barrier = as_dict(decode_con(data.get("barrier")))
    warning = as_dict(decode_con(data.get("warning")))
    detour = as_dict(decode_con(data.get("detour")))


    # -----------------------------------------------------
    # Sensor measurements
    # -----------------------------------------------------

    st.markdown("### Sensor Measurements")

    sensor_cols = st.columns(4)

    sensor_values = [
        (
            "Water Level",
            first(
                sensor,
                "water_level_cm",
                "waterLevel",
                "water_level",
            ),
            "cm",
        ),
        (
            "Rainfall",
            first(
                sensor,
                "rainfall_mm_per_hour",
                "rainfall",
                "rainfall_mm_h",
            ),
            "mm/h",
        ),
        (
            "River Level",
            first(
                sensor,
                "river_level_m",
                "riverLevel",
                "river_level",
            ),
            "m",
        ),
        (
            "Water Level Rise Rate",
            first(
                sensor,
                "rise_rate_cm_per_min",
                "rise_rate",
                "water_level_rate",
            ),
            "cm/min",
        ),
    ]

    for col, (label, value, unit) in zip(
        sensor_cols,
        sensor_values,
    ):
        with col:
            st.metric(
                label,
                f"{value} {unit}" if value != "—" else "—",
            )


    # -----------------------------------------------------
    # Risk assessment
    # -----------------------------------------------------

    st.markdown("### Risk Assessment")

    risk_level = first(
        risk,
        "risk_level",
        "risk",
        "level",
        "status",
    )

    risk_reason = first(
        risk,
        "reason",
        "message",
        "description",
        default="No assessment explanation available.",
    )

    rc1, rc2, rc3 = st.columns(3)

    with rc1:
        st.metric(
            "Risk Level",
            normalize_risk(risk_level),
        )

    with rc2:
        st.metric(
            "Raw Risk Code",
            pretty(risk_level),
        )

    with rc3:
        st.metric(
            "Sensor Data",
            "Received" if sensor else "Unavailable",
        )

    st.caption(
        f"Assessment Details: {pretty(risk_reason)}"
    )


    # -----------------------------------------------------
    # Edge control commands
    # -----------------------------------------------------

    st.markdown("### Edge Control Commands")

    b1, b2, b3 = st.columns(3)

    barrier_state = first(
        barrier,
        "barrier",
        "barrier_command",
        "command",
        "state",
        "action",
    )

    warning_state = first(
        warning,
        "warning",
        "warning_command",
        "led",
        "buzzer",
        "command",
        "state",
    )

    detour_state = first(
        detour,
        "detour",
        "detour_info",
        "route",
        "message",
        "command",
    )

    with b1:
        st.metric(
            "Barrier Command",
            pretty(barrier_state),
        )

    with b2:
        st.metric(
            "Warning Command",
            pretty(warning_state),
        )

    with b3:
        st.metric(
            "Detour Guidance",
            pretty(detour_state),
        )

    st.warning(
        "These values represent control commands stored in MN-CSE CINs. "
        "They do not confirm the physical operation of barriers, "
        "warning lights, or buzzers."
    )


    # -----------------------------------------------------
    # Data timestamps
    # -----------------------------------------------------

    st.markdown("### Data Timestamps")

    timestamps = {
        "Sensor": first(
            data.get("sensor") or {},
            "ct",
            "lt",
        ),
        "Risk Assessment": first(
            data.get("risk") or {},
            "ct",
            "lt",
        ),
        "Barrier Control": first(
            data.get("barrier") or {},
            "ct",
            "lt",
        ),
        "Warning Control": first(
            data.get("warning") or {},
            "ct",
            "lt",
        ),
        "Detour Guidance": first(
            data.get("detour") or {},
            "ct",
            "lt",
        ),
    }

    timestamp_rows = [
        {
            "Data Type": key,
            "oneM2M Creation / Update Time": value,
        }
        for key, value in timestamps.items()
    ]

    st.dataframe(
        pd.DataFrame(timestamp_rows),
        use_container_width=True,
        hide_index=True,
    )


    # -----------------------------------------------------
    # Risk history
    # -----------------------------------------------------

    history = data.get("risk_history_items", [])

    if history:
        st.markdown("### Risk History")

        rows = []

        for item in history[-20:]:
            con = decode_con(item)

            rows.append({
                "Creation Time": item.get("ct", "—"),
                "Risk Data": pretty(con),
            })

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.caption(
            "No child CINs were retrieved from the risk history container. "
            "Check the resource contents, access permissions, or response format."
        )


# =========================================================
# 9. Raw API / CIN response viewer
# =========================================================

if show_raw:
    st.divider()
    st.subheader("Raw API Responses")

    render_json_expander(
        "MEC registered_iot_platforms Response",
        mec_result or {"error": mec_error},
    )

    render_json_expander(
        "Hosted MN-CSE Response",
        data if data else {"error": data_error or cse_message},
    )


# =========================================================
# 10. Footer and automatic refresh
# =========================================================

st.divider()

st.caption(
    "IEUM Edge Monitor | Read-only monitoring interface"
)

st.caption(
    "Last dashboard refresh: "
    f'{datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")}'
)

if refresh_seconds > 0:
    time.sleep(refresh_seconds)
    st.rerun()
