# Test Results

## Evidence Classification

This document distinguishes:

- **Verified in supplied records**: supported by recorded HTTP responses or terminal output.
- **Historical implementation**: present in prior code or notes but not independently rerun here.
- **Unverified**: no sufficient evidence in the supplied materials.
- **Future work**: outside the current prototype.

## Local ACME MN-CSE

Historical local ACME records show:

| Test | Result |
|---|---|
| Sensor CIN POST | HTTP 201 Created |
| Sensor latest CIN (`/la`) | HTTP 200 OK |
| Risk-level CIN storage | HTTP 201 Created |
| Risk-history retrieval | HTTP 200 OK |
| Edge warning/barrier/detour CIN storage | HTTP 201 Created |
| Edge latest CIN retrieval | HTTP 200 OK |
| RiskAnalysisAE retrieve without ACP | HTTP 403 Forbidden |
| ACP creation and permission update | HTTP 201/200 records |

These are historical local ACME tests. They are not a claim that the current Hosted Sandbox was just re-tested.

## Hosted MEC Sandbox

Historical platform notes record:

- MEC timing API: HTTP 200.
- MEC service-management API: HTTP 200.
- Hosted MN-CSE base resource: HTTP 200.
- MN-CSE response identifying an MN-CSE.

The public repository intentionally omits the Sandbox identifier, IP address, and private endpoint.

## Scenario Evidence

The supplied development records include five-stage flood simulation output and terminal actuator output. The current code supports `flood`, `rain`, `river`, and `missing` scenarios.

No local video file was supplied. Video-based claims are therefore not independently verifiable from this repository.

## Not Verified

- IN-CSE remoteCSE registration.
- IN-CSE data synchronization.
- Python risk-engine execution inside the MEC Host.
- Physical sensor input.
- Physical barrier, LED, or buzzer operation.
- Machine-learning model inference.
- Current live rerun against a Hosted Sandbox.

## Dashboard Integration Tests

The following dashboard checks are supported by available integration evidence:

| Check | Result |
|---|---|
| Streamlit dashboard language | Display confirmed in English |
| MEC Service API connectivity check | Confirmed to work from the dashboard |
| Hosted MN-CSE connectivity check | Confirmed to work from the dashboard |
| `flood` sensor scenario | Five stages published: Normal, Caution, Danger, Emergency, and Recovery |
| `flood` sensor ContentInstance POST | Five stage requests returned HTTP 201 |
| `flood` latest ContentInstance retrieval | Retrieval checks returned HTTP 200 |
| `rain` sensor scenario | Five stages published and latest retrieval verified successfully |
| `river` sensor scenario | Partial success; some requests encountered read timeouts |
| `missing` sensor scenario | Unverified; no successful execution log is available |
| Continuous `--watch` mode | Encountered read timeouts; further validation is required |

These checks distinguish the dashboard and Hosted Sandbox evidence from historical local ACME tests:

- Historical local ACME tests demonstrated CIN creation/retrieval and control-record storage on a local MN-CSE.
- The dashboard integration checks verify browser display and connection behavior against the relevant services.
- Risk-history rows, every dashboard field, and physical control-record operation should not be considered fully validated unless additional test output is supplied.
