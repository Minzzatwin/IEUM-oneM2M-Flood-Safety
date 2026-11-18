import argparse
import os
import requests
import json
import time
import uuid
import urllib3
from datetime import datetime, timezone, timedelta

# Suppress HTTPS self-signed certificate warnings in the MEC Sandbox environment
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==============================================================================
# 1. MN-CSE Connection Configuration
# ==============================================================================
CSE_BASE_URL = os.environ.get(
    "IEUM_CSE_BASE_URL",
    "https://example.invalid/mn-cse",
).rstrip("/")
AE_NAME = "SensorAE"
AE_ID = "CSensorAE"               # AE-ID for X-M2M-Origin authentication
CNT_NAME = "cnt_water_level"

BASE_CNT_URL = f"{CSE_BASE_URL}/{AE_NAME}/{CNT_NAME}"
LATEST_CIN_URL = f"{BASE_CNT_URL}/la"

# ==============================================================================
# 2. Multi-Scenario Definitions Aligned with Team Schema & Risk Thresholds
#    Format: (Stage Label, Water Level [cm], Rainfall [mm/h], River Level [m])
#    * Default 'flood' scenario transitions: Normal -> Caution -> Danger -> Emergency -> Recovery
# ==============================================================================
SCENARIOS = {
    "flood": [
        ("Stage 1: Normal",              5.0,  2.0,  1.2),
        ("Stage 2: Caution",            10.0, 20.0,  2.1),
        ("Stage 3: Danger",             19.0, 42.0,  3.6),
        ("Stage 4: Emergency",          42.0, 68.0,  4.5),
        ("Stage 5: Recovery (Normal)",   6.0,  1.5,  1.4),
    ],
    "rain": [
        ("Rain-1: Normal",    8.5,  2.0, 1.2),
        ("Rain-2: Caution",   8.5, 18.5, 1.2),
        ("Rain-3: Danger",    8.5, 38.0, 1.2),
        ("Rain-4: Emergency", 8.5, 65.5, 1.2),
        ("Rain-5: Subsided",  8.5,  1.5, 1.2),
    ],
    "river": [
        ("River-1: Normal",    8.5, 2.0, 1.2),
        ("River-2: Caution",   8.5, 2.0, 2.1),
        ("River-3: Danger",    8.5, 2.0, 3.2),
        ("River-4: Emergency", 8.5, 2.0, 4.5),
        ("River-5: Receded",   8.5, 2.0, 1.5),
    ],
    "missing": [
        ("Missing-1: Complete Input",  8.5,  2.0,  1.2),
        ("Missing-2: Null Water",     None, 18.5,  2.1),
        ("Missing-3: Null Rainfall",  46.5, None,  3.2),
        ("Missing-4: Null River",     78.0, 65.5, None),
    ],
}

def get_kst_timestamp():
    """Generate an ISO 8601 timestamp with KST (+09:00) timezone info."""
    kst_tz = timezone(timedelta(hours=9))
    return datetime.now(kst_tz).isoformat()

def run_simulation(scenario_name="flood", interval_sec=5):
    steps = SCENARIOS[scenario_name]
    # Assign a unique session tag per run to prevent measurement_id collisions
    session_tag = datetime.now().strftime("%H%M%S")

    print("=================================================================")
    print(f"  [IEUM] Virtual Sensor Simulator Started (Scenario: {scenario_name.upper()})")
    print(f"  Target URL : {BASE_CNT_URL}")
    print(f"  Originator : {AE_ID} | Interval : {interval_sec}s")
    print("=================================================================\n")

    for idx, (label, water, rain, river) in enumerate(steps, start=1):
        measurement_id = f"sensor_01_{session_tag}_{scenario_name}_{idx:02d}"

        # Construct standardized 8-field JSON measurement payload
        sensor_payload = {
            "measurement_id": measurement_id,
            "site_id": "underpass_01",
            "sensor_id": "sensor_01",
            "timestamp": get_kst_timestamp(),
            "water_level_cm": water,
            "rainfall_mm_per_hour": rain,
            "river_level_m": river,
            "source": "simulated",
        }

        post_headers = {
            "X-M2M-Origin": AE_ID,
            "X-M2M-RI": f"req_post_{uuid.uuid4().hex[:8]}",
            "X-M2M-RVI": "4",
            "Content-Type": "application/json;ty=4",
            "Accept": "application/json",
        }

        one2m2m_body = {
            "m2m:cin": {
                "con": json.dumps(sensor_payload, ensure_ascii=False)
            }
        }

        print(f"▶ [{label}] Publishing measurement... (ID: {measurement_id})")
        try:
            # [STEP 1] Create a ContentInstance (CIN) on MN-CSE via HTTP POST
            post_res = requests.post(
                BASE_CNT_URL,
                headers=post_headers,
                data=json.dumps(one2m2m_body),
                timeout=8,
                verify=False,
            )
            print(f"  1) HTTP POST Status : {post_res.status_code}")

            if post_res.status_code in [200, 201]:
                print(f"     └ Payload JSON : {json.dumps(sensor_payload, ensure_ascii=False)}")

                # [STEP 2] Verify storage via oneM2M /la (latest) virtual resource
                get_headers = {
                    "X-M2M-Origin": AE_ID,
                    "X-M2M-RI": f"req_get_{uuid.uuid4().hex[:8]}",
                    "X-M2M-RVI": "4",
                    "Accept": "application/json",
                }
                get_res = requests.get(LATEST_CIN_URL, headers=get_headers, timeout=8, verify=False)
                print(f"  2) ACME Latest CIN Check (/la) : HTTP {get_res.status_code}")

                if get_res.status_code == 200:
                    saved_cin = get_res.json().get("m2m:cin", {})
                    print(f"     └ Verified (rn={saved_cin.get('rn')}) : {saved_cin.get('con')}\n")
                else:
                    print(f"     └ [Verification Failed] {get_res.text}\n")
            else:
                print(f"     └ [Publish Failed] Response: {post_res.text}\n")

        except Exception as e:
            print(f"  └ [Connection Error] Unable to reach MN-CSE -> {e}\n")

        if idx < len(steps):
            time.sleep(interval_sec)

    print("=================================================================")
    print(f"  [{scenario_name.upper()}] Scenario Transmission & Verification Complete")
    print("=================================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IEUM Virtual Sensor Data Simulator")
    parser.add_argument("--scenario", choices=list(SCENARIOS.keys()), default="flood", help="Select scenario (default: flood)")
    parser.add_argument("--delay", type=int, default=5, help="Transmission interval in seconds (default: 5)")
    args = parser.parse_args()

    run_simulation(scenario_name=args.scenario, interval_sec=args.delay)