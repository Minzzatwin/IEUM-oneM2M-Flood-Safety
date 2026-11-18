#!/usr/bin/env python3
"""IEUM Edge risk assessment and oneM2M ACME integration.

Install: py -m pip install requests
Setup: py ieum_edge_integrated.py --setup
Run: py ieum_edge_integrated.py --watch
Check: py ieum_edge_integrated.py --check

The original sensor_generator.py and actuator_controller.py files are preserved.
The --run-sensor and --run-actuator modes apply the sandbox URL and required
cnf value through an in-process compatibility adapter. Running the original
files directly may fail due to their local URLs or missing cnf values.
"""
import argparse
import hashlib
import importlib.util
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import sys
import time
from uuid import uuid4

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CSE_BASE_URL = os.environ.get(
    'IEUM_CSE_BASE_URL',
    'https://example.invalid/mn-cse',
).rstrip('/')
RELEASE_VERSION = '3'
VERIFY_TLS = os.environ.get('IEUM_VERIFY_TLS', 'false').lower() == 'true'
POLL_INTERVAL = 2
REQUEST_TIMEOUT = 20
RETRY_SECONDS = 3

# Keep the resource names used by the companion scripts.
SENSOR_AE, SENSOR_ID = 'SensorAE', 'CSensorAE'
EDGE_AE, EDGE_ID = 'EdgeAE', 'CEdgeAE'
RISK_AE, RISK_ID = 'RiskAnalysisAE', 'CRiskAnalysisAE'
SENSOR_CONTAINER = 'cnt_water_level'
OUTPUT_CONTAINERS = {
    EDGE_AE: ['cnt_barrier_control', 'cnt_warning_control', 'cnt_detour_info'],
    RISK_AE: ['cnt_risk_level', 'cnt_risk_history'],
    SENSOR_AE: [SENSOR_CONTAINER, 'cnt_water_level_rate'],
}
# Demo thresholds only.
LIMITS = {
    'water_level_cm': (15, 40, 70),
    'rainfall_mm_per_hour': (10, 30, 60),
    'river_level_m': (2.0, 3.0, 4.0),
}
LEVELS = ['NORMAL', 'CAUTION', 'DANGER', 'EMERGENCY']
# Older CSE records may contain localized display text.
LEGACY_TEXT = {
    "정상": "NORMAL", "주의": "CAUTION", "위험": "DANGER", "긴급": "EMERGENCY",
    "데이터 부족": "INSUFFICIENT DATA",
    "진입 금지: 침수 위험": "Do not enter - flood risk",
    "침수 주의": "Caution - flood risk",
    "정상 통행 가능": "Normal traffic flow",
}


def english_record(record):
    result = record.copy()
    for key in ("assessment", "observed_risk_level", "message"):
        value = result.get(key)
        if isinstance(value, str) and value in LEGACY_TEXT:
            result[key] = LEGACY_TEXT[value]
    return result


def valid_number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and value >= 0)


class RiskEngine:
    """Evaluate samples from one sensor in timestamp order."""
    def __init__(self, closed=False):
        self.previous = None
        self.closed = closed

    def evaluate(self, sample):
        now = datetime.fromisoformat(sample['timestamp'].replace('Z', '+00:00'))
        if now.tzinfo is None:
            raise ValueError('The timestamp must include timezone information.')
        if self.previous and now <= self.previous[0]:
            raise ValueError('The timestamp must be later than the previous measurement.')
        water = sample.get('water_level_cm')
        rise_rate = None
        if self.previous and valid_number(water) and valid_number(self.previous[1]):
            minutes = (now - self.previous[0]).total_seconds() / 60
            rise_rate = round((water - self.previous[1]) / minutes, 3)
        self.previous = (now, water)
        missing = [key for key in LIMITS if not valid_number(sample.get(key))]
        level_by_sensor = {
            key: sum(value >= limit for limit in LIMITS[key])
            for key in LIMITS
            if valid_number(value := sample.get(key))
        }
        level = max(level_by_sensor.values(), default=0)
        # Keep the barrier locked when any required reading is missing.
        self.closed = self.closed or level >= 2 or bool(missing)
        return {
            'measurement_id': sample['measurement_id'],
            'timestamp': sample['timestamp'],
            'water_level_rise_cm_per_min': rise_rate,
            'riskLevel': LEVELS[level],
            'observed_risk_level': LEVELS[level],
            'assessment': 'INSUFFICIENT DATA' if missing else LEVELS[level],
            'data_quality': 'incomplete' if missing else 'complete',
            'missing_fields': missing,
            'reasons': [k for k, v in level_by_sensor.items() if v == level and v > 0],
            'control_command': {
                'barrier': 'CLOSE' if self.closed else 'NO_CHANGE',
                'led': 'RED' if self.closed else ('YELLOW' if level == 1 else 'GREEN'),
                'buzzer': 'ON' if self.closed else 'OFF',
            },
            'reopen_requires_manual_check': self.closed,
            'actuator_actual_state': 'UNKNOWN',
            'rule_version': 'ieum-demo-v3',
        }


def headers(origin, kind=None):
    h = {
        'X-M2M-Origin': origin,
        'X-M2M-RI': 'ieum_' + uuid4().hex[:12],
        'X-M2M-RVI': RELEASE_VERSION,
        'Accept': 'application/json',
    }
    if kind is not None:
        h['Content-Type'] = f'application/json;ty={kind}'
    return h


def request(method, path, origin, kind=None, body=None):
    url = f'{CSE_BASE_URL}/{path.lstrip("/")}' if path else CSE_BASE_URL
    response = requests.request(
        method, url, headers=headers(origin, kind),
        data=json.dumps(body, ensure_ascii=False) if body is not None else None,
        timeout=REQUEST_TIMEOUT, verify=VERIFY_TLS,
    )
    if not response.ok:
        raise RuntimeError(f'{method} {url} -> HTTP {response.status_code}: {response.text[:300]}')
    return response.json()


def try_get(path, origin):
    url = f'{CSE_BASE_URL}/{path.lstrip("/")}'
    response = requests.get(url, headers=headers(origin), timeout=REQUEST_TIMEOUT, verify=VERIFY_TLS)
    if response.status_code == 404:
        return None
    if not response.ok:
        raise RuntimeError(f'GET {url} -> HTTP {response.status_code}: {response.text[:300]}')
    return response.json()


def ensure_resource(path, origin, kind, payload, check_path=None):
    """Check the existing resource after a conflict."""
    url = f'{CSE_BASE_URL}/{path.lstrip("/")}' if path else CSE_BASE_URL
    response = requests.post(
        url, headers=headers(origin, kind), data=json.dumps(payload, ensure_ascii=False),
        timeout=REQUEST_TIMEOUT, verify=VERIFY_TLS,
    )
    if response.status_code in (200, 201):
        print('  Created:', check_path or payload)
        return
    if response.status_code == 409:
        if check_path:
            try_get(check_path, origin)
        print('  Using existing resource:', check_path or path)
        return
    raise RuntimeError(f'Resource creation failed: HTTP {response.status_code}: {response.text[:300]}')


def setup():
    for ae, origin, api in (
        (SENSOR_AE, SENSOR_ID, 'N.ieum.sensor'),
        (EDGE_AE, EDGE_ID, 'N.ieum.edge'),
        (RISK_AE, RISK_ID, 'N.ieum.risk'),
    ):
        ensure_resource('', origin, 2, {'m2m:ae': {
            'rn': ae, 'api': api, 'rr': False, 'srv': [RELEASE_VERSION],
        }}, ae)
        for name in OUTPUT_CONTAINERS[ae]:
            ensure_resource(ae, origin, 3, {'m2m:cnt': {'rn': name, 'mni': 100}}, f'{ae}/{name}')
    print('Server resources are ready.')


def store(ae, origin, container, content):
    """Use stable CIN names so retries do not duplicate output."""
    payload_text = json.dumps(content, ensure_ascii=False, sort_keys=True, allow_nan=False)
    # Derive the resource name from its destination and measurement ID.
    measurement_id = str(content.get('measurement_id', 'unknown'))
    token = hashlib.sha256(f'{ae}/{container}/{measurement_id}'.encode()).hexdigest()[:20]
    rn = f'cin_ieum_{token}'
    payload = {'m2m:cin': {
        'rn': rn,
        'cnf': 'application/json:0',
        'con': payload_text,
    }}
    url_path = f'{ae}/{container}'
    url = f'{CSE_BASE_URL}/{url_path}'
    response = requests.post(url, headers=headers(origin, 4),
                             data=json.dumps(payload, ensure_ascii=False),
                             timeout=REQUEST_TIMEOUT, verify=VERIFY_TLS)
    if response.status_code in (200, 201):
        return
    if response.status_code == 409:
        # Verify that a conflicting record matches the intended output.
        existing = try_get(f'{url_path}/{rn}', origin)
        if existing:
            old_content = existing.get('m2m:cin', {}).get('con')
            if old_content == payload_text:
                return
            if isinstance(old_content, str):
                try:
                    old_content = json.loads(old_content)
                except ValueError:
                    old_content = None
            if isinstance(old_content, dict):
                canonical = json.dumps(english_record(old_content), ensure_ascii=False, sort_keys=True)
                if canonical == payload_text:
                    return
    raise RuntimeError(f'POST {url_path}/{rn} -> HTTP {response.status_code}: {response.text[:300]}')


def discover_sensor_samples():
    """Fetch child CINs to include intermediate readings."""
    path = f'{SENSOR_AE}/{SENSOR_CONTAINER}'
    url = f'{CSE_BASE_URL}/{path}'
    # rcn=4 requests attributes and child resources.
    response = requests.get(url, params={'rcn': 4}, headers=headers(SENSOR_ID),
                            timeout=REQUEST_TIMEOUT, verify=VERIFY_TLS)
    response.raise_for_status()
    result = response.json()
    cnt = result.get('m2m:cnt')
    if not isinstance(cnt, dict):
        raise RuntimeError('The rcn=4 response does not contain m2m:cnt: ' + str(result)[:300])
    cin_list = cnt.get('m2m:cin', [])
    if isinstance(cin_list, dict):
        cin_list = [cin_list]
    if not isinstance(cin_list, list):
        raise RuntimeError('Unexpected m2m:cin format in the rcn=4 response.')
    if cnt.get('cni', 0) and not cin_list:
        raise RuntimeError('The container contains CINs, but rcn=4 returned no list. Processing stopped to prevent missing data.')
    samples = []
    for cin in cin_list:
        if not isinstance(cin, dict):
            continue
        con = cin.get('con')
        try:
            sample = json.loads(con) if isinstance(con, str) else con
        except (ValueError, TypeError):
            continue
        if not isinstance(sample, dict) or not all(
            key in sample for key in ('measurement_id', 'timestamp')
        ):
            continue  # Skip manual test records.
        samples.append((str(cin.get('ri') or cin.get('rn')), sample))
    samples.sort(key=lambda item: (item[1]['timestamp'], item[0]))
    return samples


def save_state(path, state):
    """Atomically save the last completed action."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(state, ensure_ascii=False), encoding='utf-8')
    tmp.replace(path)


def latest(path, origin):
    data = try_get(f'{path}/la', origin)
    if not data:
        return None
    cin = data['m2m:cin']
    content = cin['con']
    return cin['ri'], json.loads(content) if isinstance(content, str) else content


def output_records(sample, decision):
    common = {k: sample.get(k) for k in
              ('measurement_id', 'site_id', 'sensor_id', 'timestamp', 'source')}
    command = decision['control_command']
    barrier = {**common, 'action': command['barrier'], 'command': command['barrier'],
               'riskLevel': decision['riskLevel'],
               'observed_risk_level': decision['observed_risk_level']}
    warning = {**common, 'riskLevel': decision['riskLevel'],
               'led': command['led'], 'buzzer': command['buzzer'],
               'action': 'ON' if command['buzzer'] == 'ON' else 'OFF',
               'message': ('Do not enter - flood risk' if decision['reopen_requires_manual_check']
                           else 'Caution - flood risk' if decision['riskLevel'] == 'CAUTION'
                           else 'Normal traffic flow')}
    detour = {**common, 'action': 'DETOUR' if decision['reopen_requires_manual_check'] else 'NONE'}
    rate = {**common, 'water_level_rise_cm_per_min': decision['water_level_rise_cm_per_min']}
    return [
        (RISK_AE, RISK_ID, 'cnt_risk_level', decision),
        (RISK_AE, RISK_ID, 'cnt_risk_history', decision),
        (SENSOR_AE, SENSOR_ID, 'cnt_water_level_rate', rate),
        (EDGE_AE, EDGE_ID, 'cnt_barrier_control', barrier),
        (EDGE_AE, EDGE_ID, 'cnt_warning_control', warning),
        (EDGE_AE, EDGE_ID, 'cnt_detour_info', detour),
    ]


def check():
    for path, origin in (
        (SENSOR_AE + '/' + SENSOR_CONTAINER, SENSOR_ID),
        (EDGE_AE + '/cnt_barrier_control', EDGE_ID),
        (EDGE_AE + '/cnt_warning_control', EDGE_ID),
        (EDGE_AE + '/cnt_detour_info', EDGE_ID),
    ):
        try:
            data = try_get(path, origin)
            print(('OK ' if data else 'MISSING '), path)
        except Exception as exc:
            print('ERROR ', path, str(exc))


def watch(interval, state_file, once=False):
    state_file = Path(state_file)
    if state_file.exists():
        state = json.loads(state_file.read_text(encoding='utf-8'))
    else:
        # Restore the latest barrier command if available.
        state = {'closed': False, 'processed_ids': [], 'pending': None}
        try:
            prior = latest(f'{EDGE_AE}/cnt_barrier_control', EDGE_ID)
            if prior:
                state['closed'] = (prior[1].get('action') or prior[1].get('command')) == 'CLOSE'
        except Exception as exc:
            print('Failed to retrieve the previous barrier state; starting with the barrier locked:', exc)
            state['closed'] = True
    state.setdefault('processed_ids', [])
    state.setdefault('pending', None)
    engine = RiskEngine(closed=bool(state.get('closed')))
    processed = set(state['processed_ids'])
    print('IEUM Edge started | Fetch all CINs (rcn=4) -> Risk assessment -> EdgeAE')
    print('Sensor container:', f'{CSE_BASE_URL}/{SENSOR_AE}/{SENSOR_CONTAINER}')
    print('Barrier locked:', engine.closed, '| Press Ctrl+C to exit')
    while True:
        try:
            samples = discover_sensor_samples()
            queue = [(ri, data) for ri, data in samples if ri not in processed]
            # Finish partially saved output first.
            if state['pending']:
                pending_ri = state['pending']['ri']
                queue = [(pending_ri, state['pending']['sample'])] + [
                    (ri, sample) for ri, sample in queue if ri != pending_ri
                ]
            if not queue and once:
                print('No new sensor data to process.')
                return
            for ri, sample in queue:
                if state['pending'] and state['pending']['ri'] == ri:
                    decision = english_record(state['pending']['decision'])
                    start_idx = state['pending']['next_output']
                else:
                    try:
                        decision = engine.evaluate(sample)
                    except (ValueError, KeyError, TypeError) as exc:
                        print('Sensor data assessment failed; check the data before retrying:', ri, exc)
                        raise
                    state['closed'] = engine.closed
                    state['pending'] = {
                        'ri': ri, 'sample': sample, 'decision': decision, 'next_output': 0,
                    }
                    save_state(state_file, state)
                    start_idx = 0
                records = output_records(sample, decision)
                for idx in range(start_idx, len(records)):
                    ae, origin, container, content = records[idx]
                    store(ae, origin, container, content)
                    state['pending']['next_output'] = idx + 1
                    save_state(state_file, state)
                state['pending'] = None
                processed.add(ri)
                state['processed_ids'] = list(processed)[-2000:]
                save_state(state_file, state)
                print(f"{sample['measurement_id']}: {decision['assessment']} / "
                      f"Barrier={decision['control_command']['barrier']} / "
                      f"Rise rate (cm/min)={decision['water_level_rise_cm_per_min']}", flush=True)
                if once:
                    return
        except (requests.RequestException, RuntimeError, ValueError, KeyError, TypeError) as exc:
            print('Integration error (retrying shortly):', exc, flush=True)
            if once:
                raise
            time.sleep(RETRY_SECONDS)
        time.sleep(interval)


def load_teammate_script(filename, module_name):
    """Load a companion script into the current process."""
    source = Path(__file__).resolve().parent / filename
    if not source.is_file():
        raise FileNotFoundError(f'Place the required file in the same folder: {source}')
    spec = importlib.util.spec_from_file_location(module_name, source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_original_sensor(scenario, delay):
    """Run the sensor generator with sandbox settings."""
    module = load_teammate_script('sensor_generator.py', 'ieum_teammate_sensor')
    module.CSE_BASE_URL = CSE_BASE_URL
    module.BASE_CNT_URL = f'{CSE_BASE_URL}/{module.AE_NAME}/{module.CNT_NAME}'
    module.LATEST_CIN_URL = module.BASE_CNT_URL + '/la'
    # This ACME instance requires cin.cnf=application/json:0.
    # Adapt outgoing POST requests at runtime.
    original_post = requests.post

    def compatible_post(url, **kwargs):
        payload = kwargs.get('data')
        if isinstance(payload, str):
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict) and isinstance(parsed.get('m2m:cin'), dict):
                parsed['m2m:cin'].setdefault('cnf', 'application/json:0')
                kwargs['data'] = json.dumps(parsed, ensure_ascii=False)
        return original_post(url, **kwargs)

    module.requests.post = compatible_post
    print('Running sensor_generator.py (original file preserved; cnf and URL adjusted at runtime)')
    module.run_simulation(scenario_name=scenario, interval_sec=delay)


def run_original_actuator():
    """Run the actuator controller with the sandbox URL."""
    module = load_teammate_script('actuator_controller.py', 'ieum_teammate_actuator')
    module.CSE_BASE_URL = CSE_BASE_URL
    module.make_headers = lambda: headers(EDGE_ID)
    module.BARRIER_URL = f'{CSE_BASE_URL}/EdgeAE/cnt_barrier_control/la'
    module.WARNING_URL = f'{CSE_BASE_URL}/EdgeAE/cnt_warning_control/la'
    module.DETOUR_URL = f'{CSE_BASE_URL}/EdgeAE/cnt_detour_info/la'
    print('Running actuator_controller.py (original file preserved; URLs adjusted at runtime)')
    module.main()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--setup', action='store_true', help='Create the required AEs and containers')
    modes.add_argument('--check', action='store_true', help='Check resource access')
    modes.add_argument('--watch', action='store_true', help='Continuously process sensor data and run Edge control')
    modes.add_argument('--once', action='store_true', help='Process one pending sensor sample and exit')
    modes.add_argument('--run-sensor', action='store_true', help='Run the original sensor script without modifying it')
    modes.add_argument('--run-actuator', action='store_true', help='Run the original actuator script without modifying it')
    parser.add_argument('--interval', type=float, default=POLL_INTERVAL)
    parser.add_argument('--state-file', default='ieum_edge_state.json')
    parser.add_argument('--scenario', choices=['flood', 'rain', 'river', 'missing'], default='flood')
    parser.add_argument('--delay', type=float, default=5, help='Sensor simulation transmission interval (seconds)')
    args = parser.parse_args()
    if not math.isfinite(args.interval) or args.interval <= 0:
        parser.error('--interval must be a positive number.')
    if args.delay < 0 or not math.isfinite(args.delay):
        parser.error('--delay must be a nonnegative number.')
    if args.setup:
        setup()
    elif args.check:
        check()
    elif args.run_sensor:
        run_original_sensor(args.scenario, args.delay)
    elif args.run_actuator:
        run_original_actuator()
    else:
        watch(args.interval, args.state_file, once=args.once)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nStopped.')
    except Exception as exc:
        print('Failed:', exc, file=sys.stderr)
        sys.exit(1)
