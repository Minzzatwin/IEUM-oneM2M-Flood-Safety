# Limitations and Future Work

## Current Limitations

### No physical hardware

The repository contains simulated sensor input and terminal output. Physical water-level sensors, rainfall sensors, river-level sensors, barriers, LEDs, and buzzers are not connected.

### Rule-based analysis

The risk engine uses deterministic thresholds and state rules. It does not contain a trained machine-learning model, model training pipeline, or inference service.

### IN-CSE synchronization

The supplied records do not verify remoteCSE registration or data synchronization with an IN-CSE.

### MEC execution location

The Python applications are documented as local-PC processes communicating with a Hosted MN-CSE. Execution inside the MEC Host is not verified.

### Thresholds

The configured values are demonstration parameters. They are not certified hydrological, traffic-control, or public-safety thresholds.

### Session state

The integrated engine persists state, but the current risk engine maintains one sequential predecessor in memory. Multiple sensor sessions and multiple sites require additional isolation and validation before operational use.

### Security configuration

The companion scripts contain fixed connection values and sandbox-oriented TLS settings. Public deployment requires environment-based configuration, certificate verification, and secret handling.

### Local dashboard deployment

The Streamlit dashboard runs locally on the user's PC. Deployment of the dashboard or Python risk engine inside a MEC Host has not been verified.

### Read-only dashboard

The dashboard is read-only. It does not perform risk calculation or send barrier, warning, or detour commands.

### Multi-site operation

Multiple independent edge sites and IN-CSE synchronization remain unverified.

## Future Work

- Verify the current Hosted Sandbox Resource Tree and run the complete pipeline again.
- Verify IN-CSE remoteCSE registration and synchronization.
- Separate previous measurements by site, sensor, and simulation session.
- Add focused automated tests for missing data, duplicate CINs, restart recovery, and manual unlock.
- Connect physical or hardware-in-the-loop sensors and actuators.
- Add authenticated operator-controlled manual unlock.
- Validate thresholds with field data and safety requirements.
- Evaluate a machine-learning model only after sufficient validated data is available.
