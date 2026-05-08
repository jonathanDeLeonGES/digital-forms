# Project Structure: SGCA

## Repositorio
Monorepo con separación clara entre backend y frontend.

## Estructura de carpetas

sgca-saas/
├── backend/
│   ├── config/
│   ├── apps/
│   │   ├── tenants/
│   │   ├── users/
│   │   ├── issues/
│   │   ├── acciones/
│   │   ├── planes/
│   │   ├── evidencias/
│   │   ├── notificaciones/
│   │   ├── reportes/
│   │   └── dashboard/
│   ├── requirements/
│   │   ├── base.txt
│   │   ├── dev.txt
│   │   └── prod.txt
│   └── manage.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── store/
│   └── package.json
├── .kiro/
│   ├── steering/
│   └── specs/
├── .claude/
│   └── skills/
├── docker-compose.yml
└── README.md

## Convenciones importantes
- Cada app Django tiene: models.py, serializers.py, views.py, urls.py, tests/
- Los modelos de negocio heredan de TenantModel (django-tenants)
- NUNCA mezclar datos entre tenants
- Cada endpoint verifica automáticamente el tenant activo via middleware
- Los tests usan schemas de test aislados por tenant

## Multi-tenancy
- Schema público: Tenant, Plan, Subscription, datos de onboarding
- Schema privado por cliente: todos los datos de negocio del SGCA
- URL structure: app.sgca.com con tenant identificado por subdominio o JWT

## Convenciones de commits
- feat: nueva funcionalidad
- fix: corrección de bug
- docs: documentación
- test: tests
- chore: mantenimiento