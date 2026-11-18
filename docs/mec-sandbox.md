# MEC Sandbox

## Recorded Environment

The project notes describe a Hosted ACME MN-CSE deployed through an ETSI MEC Sandbox Option C workflow. Public repository documentation intentionally does not include the recorded Sandbox ID, IP address, or private URL.

## Confirmed Platform Checks

Historical notes record successful HTTP 200 responses for:

- MEC timing API.
- MEC service-management API.
- Hosted MN-CSE base-resource retrieval.

These checks establish reachability at the time of the recorded tests.

## Execution Boundary

The sensor simulator, integrated risk engine, and actuator monitor are Python programs executed from the local PC in the supplied execution records. The records do not demonstrate that these programs execute inside the MEC Host.

Therefore this repository describes the Hosted MEC component as the MN-CSE/platform endpoint used by the local applications, not as proof of in-host application deployment.

## IN-CSE Status

IN-CSE registration and synchronization remain unverified in the supplied evidence. Option C preconfiguration may provide an intended registration path, but an intended or automatic procedure is not equivalent to a captured remoteCSE/resource-tree verification.

## TLS and Configuration

The companion scripts contain fixed connection settings and use sandbox-oriented certificate behavior. The integrated script reads `IEUM_CSE_BASE_URL` and `IEUM_VERIFY_TLS`. Production deployment must use certificate verification and secret management appropriate to the target environment.
