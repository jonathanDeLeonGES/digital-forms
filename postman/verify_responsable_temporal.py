"""Replay the DF-11/DF-57 Postman steps against a disposable local Compose stack.

Creates an isolated tenant and random test credentials; never use on production.
Outputs JSON request/response evidence with credentials and JWTs redacted.
Run: python postman/verify_responsable_temporal.py
"""
import argparse
from datetime import datetime, timedelta
import json
import secrets
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import uuid4
from zoneinfo import ZoneInfo


def redact(value):
    if isinstance(value, dict):
        return {
            key: '[REDACTED]' if any(part in key.lower() for part in
                                    ('password', 'token', 'access', 'refresh', 'secret'))
            else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def request(base, host, path, payload=None, token=None, log=True):
    headers = {'Host': host, 'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    body = json.dumps(payload).encode() if payload is not None else None
    req = Request(base + path, data=body, headers=headers)
    try:
        response = urlopen(req, timeout=20)
    except HTTPError as error:
        response = error
    with response:
        status = response.code
        raw = response.read()
        try:
            data = json.loads(raw)
        except ValueError:
            data = {'detail': 'Non-JSON response (body omitted to avoid debug secrets)'}
    if log:
        print(json.dumps({'method': req.get_method(), 'host': host, 'path': path,
                          'request': redact(payload), 'status': status,
                          'response': redact(data)}, ensure_ascii=False), flush=True)
    return status, data


def expect(result, status):
    actual, data = result
    if actual != status:
        raise RuntimeError(f'Expected HTTP {status}, received {actual}; see redacted evidence')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    args = parser.parse_args()
    base = args.base_url.rstrip('/')
    parsed = urlparse(base)
    if parsed.hostname not in ('127.0.0.1', 'localhost') or parsed.scheme != 'http':
        parser.error('This seed-and-replay tool only supports a disposable localhost stack')

    registration = '/api/public/tenants/register/'
    for attempt in range(120):
        try:
            status, _ = request(base, 'localhost', registration, log=False)
            if status == 405:
                break
        except (URLError, TimeoutError, ConnectionError):
            pass
        if attempt % 20 == 0:
            print(json.dumps({'waiting_for_backend_seconds': attempt}), flush=True)
        time.sleep(1)
    else:
        raise RuntimeError('Compose backend did not become ready')

    schema = 'df57' + uuid4().hex[:10]
    host = f'{schema}.localhost'
    password = secrets.token_urlsafe(24)
    admin_email = f'admin@{schema}.example.com'
    temp_email = f'temporary@{schema}.example.com'
    expect(request(base, 'localhost', registration, {
        'nombre_empresa': 'DF-57 disposable regression tenant', 'subdominio': schema,
        'email_admin': admin_email, 'password': password,
    }), 201)
    admin_token = expect(request(base, host, '/api/auth/login/', {
        'email': admin_email, 'password': password,
    }), 200)['access']

    users = {}
    for name in ('permanent', 'temporary'):
        users[name] = expect(request(base, host, '/api/users/', {
            'nombre_completo': f'DF-57 {name}', 'email': f'{name}@{schema}.example.com',
            'password': password, 'role': 'responsable',
        }, admin_token), 201)['id']
    temp_token = expect(request(base, host, '/api/auth/login/', {
        'email': temp_email, 'password': password,
    }), 200)['access']
    today = datetime.now(ZoneInfo('America/Guatemala')).date()
    issue = expect(request(base, host, '/api/issues/', {
        'tipo': 'incidente', 'titulo': 'DF-57 reproducible boundary test',
        'descripcion': 'Disposable regression data', 'fecha_evento': today.isoformat(),
        'area': 'QA', 'gravedad': 'baja',
    }, admin_token), 201)
    expect(request(base, host, f'/api/issues/{issue["id"]}/transition/',
                   {'estado': 'en_analisis'}, admin_token), 200)

    failures = []
    for offset, expected in [(-1, 403), (0, 200), (1, 200)]:
        until = (today + timedelta(days=offset)).isoformat()
        accion = expect(request(base, host, '/api/acciones/', {
            'issue_id': issue['id'], 'tipo': 'correctiva',
            'resultado_esperado': f'DF-57 expiry {until}',
            'responsable_id': users['permanent'],
            'fecha_limite': (today + timedelta(days=30)).isoformat(),
        }, admin_token), 201)
        path = f'/api/acciones/{accion["id"]}'
        expect(request(base, host, path + '/responsable-temporal/', {
            'responsable_temporal_id': users['temporary'],
            'responsable_temporal_hasta': until,
        }, admin_token), 200)
        actual, result = request(base, host, path + '/transition/', {
            'estado': 'en_proceso', 'comentario': 'DF-57 boundary verification',
        }, temp_token)
        persisted = expect(request(base, host, path + '/', token=admin_token), 200)
        state = 'en_proceso' if expected == 200 else 'abierto'
        passed = actual == expected and persisted['estado'] == state
        history = persisted['historial_estados']
        if expected == 200:
            passed = passed and result.get('estado') == state and len(history) == 1
            passed = passed and history[0]['usuario']['id'] == users['temporary']
        else:
            passed = passed and not history
        print(json.dumps({'case': offset, 'today': today.isoformat(), 'until': until,
                          'expected_status': expected, 'actual_status': actual,
                          'persisted_state': persisted['estado'], 'passed': passed}), flush=True)
        if not passed:
            failures.append(offset)
    if failures:
        raise SystemExit(f'DF-57 regression failed for expiry offsets: {failures}')
    print(json.dumps({'result': 'PASS', 'cases': 3, 'tenant': schema}), flush=True)


if __name__ == '__main__':
    main()
