# Dashboard Integration

## 1. Overview

The IEUM monitoring dashboard is a Streamlit-based, read-only interface for observing the prototype at runtime. It runs on the user's local PC and reads data through the MEC Service API and the oneM2M HTTP API.

The dashboard does not calculate flood risk, change resource state, or issue physical or software actuator commands. Risk calculation and control-record writing remain in `src/ieum_edge_integrated.py`.

## 2. Dashboard Architecture

The dashboard has three communication roles:

- **MEC Service API communication:** retrieves application/platform information and checks a registered-IoT-platform endpoint.
- **Hosted MN-CSE communication:** uses oneM2M HTTP requests to retrieve latest CINs and risk-history records.
- **Local Streamlit execution:** renders values in a browser on the user's PC and periodically refreshes the page.

MEC and MN-CSE communication are separate paths. A successful MEC API check does not prove MN-CSE resource access, and an MN-CSE connection does not prove that an application is deployed inside the MEC Host.

## 3. MEC Client

`dashboard/mec_client.py` defines `MECClient`. It reads organizer-specific values from environment variables, including the MEC sandbox prefix, platform name, application name, application instance ID, TLS verification, timeout, and optional bearer token.

It checks `registered_iot_platforms` through the MEC Service API. This is an API reachability check, not a claim that the dashboard application is deployed or registered as a physical MEC application instance.

## 4. oneM2M CSE Client

`dashboard/cse_client.py` defines `CSEClient`. It reads `IEUM_CSE_BASE_URL`, origin, RVI, TLS verification, and timeout from the process environment.

The CSE client uses read-only oneM2M operations:

- Latest CIN retrieval through `/la`.
- Container child retrieval through `rcn=4`.
- Sensor, risk, and EdgeAE container mapping.

It can use the same `IEUM_CSE_BASE_URL` and `IEUM_VERIFY_TLS` configuration as `src/ieum_edge_integrated.py`. The code does not load `.env` files automatically.

## 5. Dashboard Components

`dashboard/dashboard.py` provides:

- MEC application and platform status.
- MEC Service API connectivity.
- Hosted MN-CSE connectivity.
- Sensor measurements.
- Available risk assessment information.
- Barrier, warning, and detour control records.
- Data timestamps.
- Available risk-history rows.
- Optional raw-response expansion.
- Configurable periodic refresh.

## 6. Data Retrieval Flow

The core data flow is:

```text
Sensor Simulator
      |
      v
Hosted MN-CSE
      |
      v
IEUM Edge Processing
      |
      +--> RiskAnalysisAE
      |
      +--> EdgeAE
      |
      v
Hosted MN-CSE
      |
      v
Streamlit Monitoring Dashboard
```

The Sensor Simulator publishes CINs to the Hosted MN-CSE. `ieum_edge_integrated.py` retrieves those measurements, performs rule-based assessment, and writes risk/control CINs back to the Hosted MN-CSE. The dashboard retrieves the latest values and available history from the CSE.

The MEC application/platform check is a separate path through the MEC Service API.

## 7. Displayed Information

The dashboard can display:

- Latest water level, rainfall, river level, and water-level rise rate.
- Risk level and raw risk code.
- Risk explanation when included in the stored record.
- Stored barrier, warning, and detour control values.
- oneM2M creation/update timestamps.
- Risk-history child CIN values.

The control values represent stored commands or state records. They do not confirm operation of a physical barrier, light, or buzzer.

## 8. Installation and Execution

Install the root Python dependencies:

```powershell
py -m pip install -r requirements.txt
```

Run the dashboard from the repository root:

```powershell
py -m streamlit run dashboard\dashboard.py
```

Open `http://localhost:8501`.

## 9. Configuration

Set required variables in the shell process before starting the dashboard:

```powershell
$env:IEUM_CSE_BASE_URL = "https://example.invalid/mn-cse"
$env:IEUM_VERIFY_TLS = "true"
$env:IEUM_CSE_ORIGIN = "CAdmin"
$env:IEUM_CSE_RVI = "3"
$env:IEUM_MEC_SANDBOX_PREFIX = "https://example.invalid"
$env:IEUM_MEC_PLATFORM = "mep1"
$env:IEUM_MEC_APP_INSTANCE_ID = "<your-application-instance-id>"
```

Use `.env.example` only as a reference. Copying or editing it does not make environment variables available unless the process loader in the user's shell or an application library loads it.

Do not commit endpoints, Sandbox IDs, instance IDs, bearer tokens, passwords, or local absolute paths.

## 10. Current Implementation Scope

The dashboard is an implemented read-only browser interface over the current prototype. The sensor simulator and rule-based engine run from the local PC, communicate with the Hosted MN-CSE, and write stored records for dashboard retrieval.

The public repository contains no claim that the dashboard or Python engine is deployed inside the MEC Host.

## 11. Limitations

- The dashboard runs locally on the user's PC.
- MEC Host deployment of the dashboard or Python risk engine is unverified.
- The dashboard is read-only.
- Physical sensors and actuators are not connected.
- Stored control records do not prove physical actuator operation.
- Historical local ACME tests and current Hosted Sandbox tests are different evidence sets.
- Continuous watch operation, `river`, and `missing` scenarios require additional successful logs.
