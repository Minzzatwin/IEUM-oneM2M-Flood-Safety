# Demonstration Scenario

## Preparation

1. Install the Python dependency.
2. Set `IEUM_CSE_BASE_URL` in the shell.
3. Confirm that the target MN-CSE is reachable.
4. Run `--check` or perform resource setup where authorized.
5. Mask private endpoints and identifiers in any public capture.

## Three-Terminal Flow

Run from the `src` directory.

### Terminal 1: Actuator monitor

```powershell
py .\ieum_edge_integrated.py --run-actuator
```

### Terminal 2: Risk engine

```powershell
py .\ieum_edge_integrated.py --watch
```

### Terminal 3: Flood simulator

```powershell
py .\ieum_edge_integrated.py --run-sensor --scenario flood
```

Other supported scenarios:

```powershell
py .\ieum_edge_integrated.py --run-sensor --scenario rain
py .\ieum_edge_integrated.py --run-sensor --scenario river
py .\ieum_edge_integrated.py --run-sensor --scenario missing
```

### Terminal 4: Monitoring dashboard

Run the dashboard from the repository root in a separate PowerShell window:

```powershell
py -m streamlit run dashboard\dashboard.py
```

Open `http://localhost:8501`. During the flood scenario, use the dashboard to observe whether the latest sensor CIN and available risk/control records appear. The dashboard can show:

- Latest water-level, rainfall, river-level, and rise-rate values.
- An available risk-level record and its explanation.
- Available barrier, warning, and detour records.
- oneM2M creation/update timestamps and retrieved risk-history CINs.

Do not expect the dashboard to confirm physical barrier, LED, or buzzer operation. The dashboard is read-only and only displays stored software records. If a field is empty or unavailable, inspect the raw oneM2M response and resource permissions rather than inferring a result.

## Expected Software-Level Observations

The intended software flow is:

```text
sensor measurement
→ SensorAE CIN
→ risk assessment
→ risk/history records
→ EdgeAE control records
→ terminal dashboard
```

The dashboard represents control information. It does not prove that a physical barrier, LED, or buzzer operated.

## Evidence to Capture

- Resource access or setup response.
- Sensor POST response.
- `/la` or container retrieval response.
- Risk-level and Edge control CINs.
- Terminal risk and barrier-lock output.
- Command lines and software versions.

Do not publish credentials, private Sandbox identifiers, or raw private endpoints.
