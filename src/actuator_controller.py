import requests
import os
import json
import time
import uuid
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==============================================================================
# 1. MN-CSE Connection Configuration
# ==============================================================================
CSE_BASE_URL = os.environ.get(
    "IEUM_CSE_BASE_URL",
    "https://example.invalid/mn-cse",
).rstrip("/")
AE_ID = "CEdgeAE"
BARRIER_URL = f"{CSE_BASE_URL}/EdgeAE/cnt_barrier_control/la"
WARNING_URL = f"{CSE_BASE_URL}/EdgeAE/cnt_warning_control/la"
DETOUR_URL  = f"{CSE_BASE_URL}/EdgeAE/cnt_detour_info/la"

POLL_INTERVAL = 4

# Safety Lock Rule: Once barrier is set to CLOSE, prohibit automatic reopening until manual inspection
manual_lock_active = False

def make_headers():
    return {
        "X-M2M-Origin": AE_ID,
        "X-M2M-RI": f"act_get_{uuid.uuid4().hex[:8]}",
        "X-M2M-RVI": "4",
        "Accept": "application/json"
    }

def fetch_latest_cin(url):
    try:
        res = requests.get(url, headers=make_headers(), timeout=20, verify=False)
        if res.status_code == 200:
            return res.json().get("m2m:cin")
        return None
    except Exception:
        return None

def parse_content(cin):
    con = cin.get("con")
    if isinstance(con, str):
        return json.loads(con)
    return con

def render_device_dashboard(barrier_data, warning_data, detour_data):
    global manual_lock_active
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Compatible with both 'action' and 'command'/'led'/'buzzer' schemas
    raw_barrier = (barrier_data or {}).get("action") or (barrier_data or {}).get("command") or "OPEN"
    risk_lvl = (barrier_data or warning_data or {}).get("riskLevel") or (barrier_data or warning_data or {}).get("observed_risk_level") or "NORMAL"
    
    led_state = (warning_data or {}).get("led")
    buzzer_state = (warning_data or {}).get("buzzer")
    w_action = (warning_data or {}).get("action", "OFF")
    w_msg = (warning_data or {}).get("message", "Normal Traffic Flow")
    d_action = (detour_data or {}).get("action", "NONE")

    # Activate manual inspection lock once a CLOSE command is received
    if raw_barrier == "CLOSE":
        manual_lock_active = True

    # Ensure English-only VMS display message regardless of upstream locale strings
    if not w_msg.isascii():
        if raw_barrier == "CLOSE" or manual_lock_active or risk_lvl.upper() in ["DANGER", "EMERGENCY"]:
            w_msg = "ENTRY PROHIBITED: FLOOD RISK"
        elif risk_lvl.upper() == "CAUTION":
            w_msg = "FLOOD CAUTION"
        else:
            w_msg = "Normal Traffic Flow"

    print("\n" + "="*65)
    print(f"  🚧 [Field Edge Actuator Status Monitor] ({now_str})")
    print("="*65)
    print(f"  ▶ Evaluated Risk Level  : [ {risk_lvl} ]")
    print("-"*65)

    # Display barrier state (with Safety Lock rule applied)
    if raw_barrier == "CLOSE":
        print("  ▶ Entry Barrier         : 🔴 [ LOWERED / CLOSE ] - Vehicle Entry Prohibited")
    elif manual_lock_active:
        print("  ▶ Entry Barrier         : 🔒 [ LOCKED / CLOSE  ] - Awaiting Manual Inspection")
    else:
        print("  ▶ Entry Barrier         : 🟢 [ RAISED / OPEN   ] - Normal Entry Allowed")

    # Display warning light and siren status
    if led_state or buzzer_state:
        print(f"  ▶ Warning Light / Siren : LED=[{led_state or 'OFF'}] | BUZZER=[{buzzer_state or 'OFF'}]")
    elif risk_lvl in ["DANGER", "EMERGENCY", "Danger", "Emergency"]:
        print(f"  ▶ Warning Light / Siren : 🚨 [ RED FLASHING + SIREN ON ] ({w_action})")
    elif risk_lvl in ["CAUTION", "Caution"]:
        print(f"  ▶ Warning Light / Siren : ⚠️ [ YELLOW FLASHING + ALERT ] ({w_action})")
    else:
        print(f"  ▶ Warning Light / Siren : ⚪ [ OFF / STANDBY ] ({w_action})")

    print(f"  ▶ Variable Message Sign : 📢 {w_msg}")
    print(f"  ▶ Detour Guidance       : ↪️ {d_action}")
    print("="*65 + "\n")

def main():
    print("=================================================================")
    print("  [IEUM] Field Actuator Control Receiver Running (Safety Lock Active)")
    print(f"  Target MN-CSE : {CSE_BASE_URL}")
    print("=================================================================")

    last_ris = {"barrier": None, "warning": None, "detour": None}
    latest_data = {"barrier": None, "warning": None, "detour": None}

    while True:
        b_cin = fetch_latest_cin(BARRIER_URL)
        w_cin = fetch_latest_cin(WARNING_URL)
        d_cin = fetch_latest_cin(DETOUR_URL)

        updated = False

        if b_cin and b_cin.get("ri") != last_ris["barrier"]:
            last_ris["barrier"] = b_cin.get("ri")
            latest_data["barrier"] = parse_content(b_cin)
            updated = True

        if w_cin and w_cin.get("ri") != last_ris["warning"]:
            last_ris["warning"] = w_cin.get("ri")
            latest_data["warning"] = parse_content(w_cin)
            updated = True

        if d_cin and d_cin.get("ri") != last_ris["detour"]:
            last_ris["detour"] = d_cin.get("ri")
            latest_data["detour"] = parse_content(d_cin)
            updated = True

        if updated:
            render_device_dashboard(latest_data["barrier"], latest_data["warning"], latest_data["detour"])
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()