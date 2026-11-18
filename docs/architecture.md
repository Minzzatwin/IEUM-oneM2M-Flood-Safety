# Architecture

## Scope

IEUM separates sensor input, risk assessment, and field-control information into oneM2M Application Entities.

The submitted Python processes are intended to run on a local PC and communicate with an ACME MN-CSE over HTTP(S). A Hosted MEC Sandbox provides an MN-CSE endpoint in the recorded platform checks. The supplied evidence does not establish that the Python processes execute inside the MEC host.

## Application Entities

| AE | Responsibility |
|---|---|
| SensorAE | Publishes simulated environmental measurements |
| RiskAnalysisAE | Evaluates measurements and stores risk results |
| EdgeAE | Stores barrier, warning, and detour control records |

## Resource Tree

```text
MN-CSE
├── SensorAE
│   ├── cnt_water_level
│   └── cnt_water_level_rate
├── RiskAnalysisAE
│   ├── cnt_risk_level
│   └── cnt_risk_history
└── EdgeAE
    ├── cnt_barrier_control
    ├── cnt_warning_control
    └── cnt_detour_info
```

## Processing Path

1. `sensor_generator.py` creates a JSON measurement.
2. The measurement is posted as a ContentInstance to `SensorAE/cnt_water_level`.
3. `ieum_edge_integrated.py` discovers stored CINs and evaluates them in timestamp order.
4. Risk and history records are stored under `RiskAnalysisAE`.
5. Rise-rate output is stored under `SensorAE/cnt_water_level_rate`.
6. Barrier, warning, and detour records are stored under `EdgeAE`.
7. `actuator_controller.py` reads the latest EdgeAE records and displays them in a terminal.

## Safety Behavior

The integrated engine keeps the barrier closed after a close condition or missing input. The actuator monitor also has a local in-memory lock when it observes `CLOSE`. The standalone monitor's lock is not a persistent shared state store; the integrated engine uses a state file.

Physical actuation is outside the verified scope.
