# Tech Stack: SGCA

## Frontend
- React 18 + Vite
- Recharts para gráficas interactivas tipo Power BI
- TailwindCSS para estilos

## Backend
- Python 3.12 + Django 5 + Django REST Framework
- JWT auth con djangorestframework-simplejwt
- RBAC con 4 roles: admin, responsable, supervisor, verificador

## Base de datos
- PostgreSQL 16
- django-tenants con schema-per-tenant
- Schema público: Tenant, Plan, Subscription
- Schema privado por cliente: todos los datos de negocio

## Tareas asíncronas
- Celery + Redis para:
  - Envío de emails de notificación al cambiar estado de acciones
  - Generación de reportes PDF/Excel en background
  - Detección diaria de deadlines próximos a vencer (3 días, 1 día, vencido)
  - Resumen semanal automático al admin
  - Programación de verificaciones de eficacia a futuro (6 meses, 1 año, 2 años)

## Email transaccional
- SendGrid con plantillas HTML personalizadas

## Almacenamiento
- Amazon S3 en producción, MinIO en desarrollo local
- Carpetas separadas por tenant: s3://bucket/{tenant-slug}/evidencias/

## Reportes
- ReportLab para PDF con gráficas embebidas
- openpyxl para Excel

## Infraestructura
- Docker + docker-compose
- Nginx + Gunicorn en producción

## Seguridad
- HTTPS obligatorio en producción
- Argon2 para cifrado de contraseñas
- Protección CSRF
- Auditoría completa en tabla historial_estados

## Calidad de código
- ruff + black para linting
- pytest + factory_boy para tests
- Conventional commits: feat:, fix:, docs: