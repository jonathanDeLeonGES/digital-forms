#!/bin/sh
set -e

# Aplica las migraciones del schema público (tenants, planes, suscripciones).
# migrate_schemas --shared sólo toca el schema 'public' de PostgreSQL;
# los schemas privados de cada tenant se crean al registrar el primer tenant.
echo "Aplicando migraciones del schema público..."
python manage.py migrate_schemas --shared

# Carga el fixture de planes (trial / enterprise).
# El || true evita que el entrypoint falle si los registros ya existen
# (la constraint UNIQUE en Plan.nombre lanzaría un IntegrityError).
echo "Cargando fixture inicial de planes..."
python manage.py loaddata apps/tenants/fixtures/initial_plans.json \
  || echo "  Los planes ya existen, omitiendo."

exec "$@"
