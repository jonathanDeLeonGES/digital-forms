#!/usr/bin/env python3
"""DF-58 — Verificación HTTP del límite inclusivo de la asignación temporal.

Reproduce el escenario del ticket contra un backend en ejecución (por defecto
el stack de Docker Compose del proyecto en http://localhost:8000):

  1. Registra un tenant desechable vía la API pública.
  2. El admin crea usuarios, un issue en análisis y una acción (abierto).
  3. El admin asigna un responsable temporal con hasta = HOY (fecha local de
     negocio, TIME_ZONE del proyecto: America/Guatemala).
  4. El responsable temporal hace POST /api/acciones/{id}/transition/ con
     estado=en_proceso.

Resultado esperado: 200 OK (la fecha 'hasta' es inclusiva).
Comportamiento del bug DF-58: 403 Forbidden.

Códigos de salida: 0 = comportamiento esperado (200), 1 = bug reproducido
(403), 2 = error de infraestructura. La evidencia JSON de cada paso se
escribe en el archivo indicado por EVIDENCE_FILE (por defecto
./df58_evidence.json).

Uso:
  python postman/verify_df58_responsable_temporal.py
  BASE_URL=http://localhost:8000 EVIDENCE_FILE=evidence/http.json \
    python postman/verify_df58_responsable_temporal.py
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone as dt_timezone

BASE = os.environ.get("BASE_URL", "http://localhost:8000")
EVIDENCE_FILE = os.environ.get("EVIDENCE_FILE", "df58_evidence.json")
STAMP = str(int(time.time()))[-6:]
SUB = f"df58v{STAMP}"
HOST_PUBLIC = "localhost"
HOST_TENANT = f"{SUB}.localhost"
ADMIN_EMAIL = f"admin@{SUB}.com"
ADMIN_PASS = "Admin123!"
TEMP_EMAIL = f"temp@{SUB}.com"
TEMP_PASS = "Temp1234!"

# "Hoy" en la zona horaria de negocio del producto (America/Guatemala, UTC-6)
GT_TODAY = (datetime.now(dt_timezone.utc) - timedelta(hours=6)).date()
UTC_TODAY = datetime.now(dt_timezone.utc).date()

EVIDENCE = []


def call(method, path, host, body=None, token=None, expect=None, label=""):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Host", host)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            code, payload = resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        code, payload = e.code, e.read().decode()
    EVIDENCE.append({"step": label, "method": method, "path": path, "host": host,
                     "request": body, "status": code, "response": payload[:500]})
    print(f"[{label}] {method} {path} (Host: {host}) -> {code}")
    if expect and code not in expect:
        print(f"  !! esperado {expect}, recibido {code}: {payload[:300]}")
        if label != "REPRO-TRANSITION":
            _dump()
            sys.exit(2)
    return code, (json.loads(payload) if payload[:1] in "{[" else payload)


def _dump():
    with open(EVIDENCE_FILE, "w") as f:
        json.dump({"tenant": SUB, "hasta": str(GT_TODAY), "gt_today": str(GT_TODAY),
                   "utc_today": str(UTC_TODAY), "steps": EVIDENCE},
                  f, indent=2, ensure_ascii=False)


def main():
    print(f"tenant={SUB}  hasta=hoy(GT)={GT_TODAY}  hoy(UTC)={UTC_TODAY}")

    call("POST", "/api/public/tenants/register/", HOST_PUBLIC, {
        "nombre_empresa": f"DF58 Verify {STAMP}", "subdominio": SUB,
        "email_admin": ADMIN_EMAIL, "password": ADMIN_PASS,
    }, expect=(200, 201), label="register-tenant")

    _, tok = call("POST", "/api/auth/login/", HOST_TENANT,
                  {"email": ADMIN_EMAIL, "password": ADMIN_PASS},
                  expect=(200,), label="login-admin")
    admin_token = tok["access"]

    _, u = call("POST", "/api/users/", HOST_TENANT, {
        "nombre_completo": "Responsable Temporal DF58",
        "email": TEMP_EMAIL, "password": TEMP_PASS, "role": "responsable",
    }, token=admin_token, expect=(201,), label="create-temp-user")
    temp_id = u["id"]

    _, u2 = call("POST", "/api/users/", HOST_TENANT, {
        "nombre_completo": "Responsable Titular DF58",
        "email": f"titular@{SUB}.com", "password": TEMP_PASS, "role": "responsable",
    }, token=admin_token, expect=(201,), label="create-titular-user")
    titular_id = u2["id"]

    _, iss = call("POST", "/api/issues/", HOST_TENANT, {
        "tipo": "incidente", "titulo": "DF58 verify issue",
        "descripcion": "Issue para verificar DF-58",
        "fecha_evento": str(GT_TODAY), "area": "Calidad", "gravedad": "baja",
    }, token=admin_token, expect=(201,), label="create-issue")
    issue_id = iss["id"]
    call("POST", f"/api/issues/{issue_id}/transition/", HOST_TENANT,
         {"estado": "en_analisis"}, token=admin_token, expect=(200,),
         label="issue-en-analisis")

    _, acc = call("POST", "/api/acciones/", HOST_TENANT, {
        "issue_id": issue_id, "tipo": "correctiva",
        "resultado_esperado": "Verificar DF-58: inicio el ultimo dia de asignacion temporal",
        "responsable_id": titular_id, "fecha_limite": str(GT_TODAY + timedelta(days=30)),
    }, token=admin_token, expect=(201,), label="create-accion")
    accion_id = acc["id"]

    call("POST", f"/api/acciones/{accion_id}/responsable-temporal/", HOST_TENANT, {
        "responsable_temporal_id": temp_id,
        "responsable_temporal_hasta": str(GT_TODAY),
    }, token=admin_token, expect=(200,), label="assign-temp-hasta-today")

    _, tok2 = call("POST", "/api/auth/login/", HOST_TENANT,
                   {"email": TEMP_EMAIL, "password": TEMP_PASS},
                   expect=(200,), label="login-temp")
    temp_token = tok2["access"]

    code, body = call("POST", f"/api/acciones/{accion_id}/transition/", HOST_TENANT, {
        "estado": "en_proceso",
        "comentario": "Verificacion DF-58: inicio el ultimo dia de la asignacion temporal",
    }, token=temp_token, expect=(200,), label="REPRO-TRANSITION")

    _dump()
    if code == 200:
        print("\nRESULTADO: 200 OK — comportamiento ESPERADO (DF-58 corregido).")
        sys.exit(0)
    if code == 403:
        print(f"\nRESULTADO: 403 Forbidden — BUG DF-58 REPRODUCIDO. Body: {body}")
        sys.exit(1)
    print(f"\nRESULTADO: estado inesperado {code}")
    sys.exit(2)


if __name__ == "__main__":
    main()
