#!/bin/sh
set -e

# Aplica las migraciones del schema público (tenants, planes, suscripciones).
# migrate_schemas --shared sólo toca el schema 'public' de PostgreSQL;
# los schemas privados de cada tenant se crean al registrar el primer tenant.
# La migración 0002 ya crea el tenant público, el dominio localhost y los planes.
echo "Aplicando migraciones del schema público..."
python manage.py migrate_schemas --shared

# Configura el dominio público si se define la variable PUBLIC_DOMAIN.
# Dev:  PUBLIC_DOMAIN no definida → solo localhost (creado por la migración).
# Prod: PUBLIC_DOMAIN=sgca.com    → agrega sgca.com como primario y quita localhost.
if [ -n "$PUBLIC_DOMAIN" ]; then
  echo "Configurando dominio público: $PUBLIC_DOMAIN"
  python manage.py add_public_domain "$PUBLIC_DOMAIN" --primary
  python manage.py remove_public_domain localhost || true
fi

exec "$@"
