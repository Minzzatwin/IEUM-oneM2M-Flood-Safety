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
