# IEUM Edge Monitor Dashboard

Read-only Streamlit dashboard for:
- MEC Sandbox app metadata and a known MEC IoT API connectivity check.
- oneM2M Hosted MN-CSE latest CINs for SensorAE, RiskAnalysisAE, and EdgeAE.

## Important limitations

1. The MEC Application Instance ID is registered in the Sandbox. The Sandbox emulates MEC app lifecycle; this does not prove that this Python dashboard is deployed on a MEC host.
2. `confirm_ready` already returned HTTP 204 for the configured ID. The dashboard does not repeat that POST.
3. `/iots/v1/registered_iot_platforms` is a known GET endpoint previously observed returning HTTP 200. It is an IoT API reachability check, not an app-instance status endpoint.
4. Dashboard values are read from CINs. Barrier/warning values are commanded states, not physical actuator feedback.
5. Configure the MEC Sandbox and Hosted MN-CSE endpoints separately. Do not publish organizer-specific IDs or private URLs.
6. TLS verification defaults to false to match the existing sandbox test setup. Use true if the sandbox certificates validate on your machine.

## Windows PowerShell setup

Run from the `dashboard` directory:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m streamlit run dashboard.py
```

If PowerShell blocks activation, use:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Open `http://localhost:8501`.

## Mobile access on the same Wi-Fi

```powershell
python -m streamlit run dashboard.py --server.address 0.0.0.0
```

Find the PC's Wi-Fi IPv4 address with:

```powershell
ipconfig
```

On the phone, open `http://<PC의 IPv4 주소>:8501`. Allow Python/Streamlit through Windows Firewall only on a trusted Private network.

## Environment variables

The defaults are already set for the current project. To override them for the current PowerShell session:

```powershell
$env:IEUM_CSE_BASE_URL = "https://example.invalid/mn-cse"
$env:IEUM_CSE_ORIGIN = "CAdmin"
$env:IEUM_CSE_RVI = "3"
$env:IEUM_VERIFY_TLS = "false"
$env:IEUM_MEC_SANDBOX_PREFIX = "https://example.invalid"
$env:IEUM_MEC_PLATFORM = "mep1"
$env:IEUM_MEC_APP_NAME = "IEUM-Edge-Monitor"
$env:IEUM_MEC_APP_INSTANCE_ID = "<your-application-instance-id>"
$env:IEUM_MEC_VERIFY_TLS = "false"
```

## What the dashboard reads

- `SensorAE/cnt_water_level/la`
- `RiskAnalysisAE/cnt_risk_level/la`
- `RiskAnalysisAE/cnt_risk_history?rcn=4`
- `EdgeAE/cnt_barrier_control/la`
- `EdgeAE/cnt_warning_control/la`
- `EdgeAE/cnt_detour_info/la`

If one or more containers have different names in the actual Resource Tree, update the mapping in `cse_client.py`.

## Troubleshooting

- **MN-CSE 401/403:** confirm `IEUM_CSE_ORIGIN` and the CSE access-control policy. Do not assume CAdmin is authorized just because another endpoint was accessible.
- **MN-CSE 404:** verify the base URL and AE/container names in the Hosted MN-CSE Resource Tree.
- **MEC 401:** the Swagger browser session may have authentication cookies not available to this separate Python process. Use only an organizer-provided supported token/auth method; do not copy session cookies into source code.
- **MEC 404:** verify the IoT API path in the current Sandbox Swagger and compare the API Console endpoint.
- **Empty values or —:** inspect the raw response expander and confirm the latest CIN's `con` schema. Field names can differ between versions of the user's pipeline.
- **TLS errors:** first test with the sandbox's documented certificate setup. `verify=false` is retained as a compatibility default from the existing project code; it is not ideal for production.
