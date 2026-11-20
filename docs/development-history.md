# Development History

## 1. Planning

The project began as a design for underground-infrastructure flood risk management using oneM2M, ACME CSE, and MEC/Edge concepts. The planned data sources were water level, rainfall, river level, and water-level rise rate.

## 2. Local ACME Development

Historical Notion exports show a local ACME MN-CSE environment using a local CSE base. The team created the SensorAE, RiskAnalysisAE, and EdgeAE resource structure and tested oneM2M operations.

The local development process included:

- Sensor CIN creation and retrieval.
- Rule-based risk calculation.
- Risk-level and risk-history storage.
- Edge warning, barrier, and detour records.
- ACP permission configuration.

## 3. Permission Errors

The development logs record HTTP 403 responses when an AE attempted to retrieve a resource without permission. ACP resources were then created and attached with the appropriate originator and operation permissions. CREATE-only permissions were also expanded when RETRIEVE access was required.

## 4. Integrated Engine

The current integrated source combines:

- Resource setup and connectivity checks.
- Full CIN discovery with `rcn=4`.
- Rule-based risk assessment.
- Idempotent output CIN naming.
- Processed-ID and pending-state persistence.
- Barrier-state recovery.
- Runtime adapters for the companion sensor and actuator scripts.

The original companion scripts remain separate files and are loaded without editing their source.

## 5. MEC Sandbox

The project later used a Hosted MEC Sandbox MN-CSE endpoint for platform connectivity checks. Historical notes record successful MEC timing, service-management, and MN-CSE base-resource requests.

The supplied records do not independently verify IN-CSE synchronization or Python execution inside the MEC host.

## 6. Current Submission Boundary

The source files in `src/` are copied from the current `project_context` files. Historical versions in the Notion export are development evidence, not additional production entry points. They are not copied into the executable source tree.

## 7. Streamlit Monitoring Dashboard

After the initial CLI-based prototype and terminal actuator monitor, the project added a separate Streamlit monitoring dashboard under `dashboard/`. It provides read-only browser views of MEC status and Hosted oneM2M data.

`cse_client.py` communicates with the Hosted MN-CSE using the oneM2M HTTP API and retrieves latest CINs and risk-history children. `mec_client.py` performs separate MEC Service API checks for application metadata and registered IoT platforms. `dashboard.py` renders these results and does not invoke the risk engine or send actuator commands.
