# Implementation Plan

- [ ] 1. Scaffolding y configuración
- [ ] 1.1 Crear app Django `apps/reportes/` con estructura de archivos
  - Crear `__init__.py`, `apps.py`, `models.py`, `services.py`, `tasks.py`, `builders.py`, `serializers.py`, `views.py`, `urls.py`, `storage.py`, `tests/`
  - Registrar `'apps.reportes'` en `TENANT_APPS` en `config/settings/base.py`
  - Registrar URL prefix `/api/reportes/` y `/api/dashboard/` en el router principal
  - Verificable: `python manage.py check` sin errores; app aparece en `INSTALLED_APPS`
  - _Requirements: 2.1, 3.1_
  - _Boundary: apps/reportes/_

- [ ] 1.2 Configurar Celery task name y dependencias (P)
  - Verificar que `reportlab`, `openpyxl`, `django-storages`, `boto3` están en `requirements/base.txt`
  - Registrar task name `sgca.reportes.generar_reporte` en `config/celery.py`
  - Verificable: `celery inspect registered` incluye `sgca.reportes.generar_reporte`
  - _Requirements: 2.1, 3.1_
  - _Boundary: config/celery.py, requirements/_
  - _Depends: 1.1_

---

- [ ] 2. Modelo ReporteGenerado
- [ ] 2.1 Implementar modelo ReporteGenerado y migraciones
  - Campos: tipo, estado, filtros (JSONField), created_by FK, s3_path, celery_task_id, expira_at, created_at, updated_at
  - Hereda de TenantModel; índices en created_by, estado, expira_at
  - Ejecutar `makemigrations reportes` y `migrate`
  - Verificable: tabla existe en schema de tenant de prueba; `ReporteGenerado.objects.create(...)` funciona
  - _Requirements: 2.1, 2.2, 5.1, 5.2_
  - _Boundary: apps/reportes/models.py_
  - _Depends: 1.1_

---

- [ ] 3. MetricasService (aggregation queries)
- [ ] 3.1 Implementar MetricasService con todas las aggregation queries (P)
  - `get_metricas_dashboard(filtros)`: queries para acciones por estado, por tipo, por área, compliance deadlines, tendencia mensual de issues (12 meses)
  - `_base_accion_qs(filtros)` y `_base_issue_qs(filtros)` para filtros reutilizables
  - Verificable: unit tests de `test_services.py` pasan con datos de factory_boy
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 6.1, 6.3, 6.4_
  - _Boundary: apps/reportes/services.py_
  - _Depends: 2.1_

---

- [ ] 4. DashboardMetricasView
- [ ] 4.1 Implementar DashboardMetricasView y serializer de respuesta (P)
  - `GET /api/dashboard/metricas/` con query params opcionales (fecha_inicio, fecha_fin, area)
  - Serializer `FiltrosSerializer` valida fecha_inicio <= fecha_fin y choices válidos
  - `RequireRole(admin, supervisor)` como permission class
  - Verificable: test de integración `test_api.py` — admin obtiene métricas; responsable → 403; fecha_inicio > fecha_fin → 400
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 6.1, 6.2, 6.3, 6.4_
  - _Boundary: apps/reportes/views.py, apps/reportes/serializers.py_
  - _Depends: 3.1_

---

- [ ] 5. ReportesService y ReporteViewSet
- [ ] 5.1 Implementar ReportesService (lifecycle de ReporteGenerado)
  - `queue_report(tipo, filtros, user)`: crea ReporteGenerado + encola tarea Celery
  - `get_download_url(reporte, user)`: verifica permisos + expiración + genera URL firmada
  - `delete_report(reporte, user)`: borra S3 + DB
  - `queryset_for_user(user)`: admin=todos, supervisor=propios
  - `_check_expiry(reporte)`: marca expirado si expira_at < now
  - Verificable: unit tests de `test_services.py` cubren todos los métodos
  - _Requirements: 2.1, 2.2, 4.1, 4.2, 4.3, 4.4, 5.1, 5.3, 5.4_
  - _Boundary: apps/reportes/services.py_
  - _Depends: 2.1_

- [ ] 5.2 Implementar ReporteViewSet con endpoints CRUD + download (P)
  - `POST /api/reportes/generar/` → 202 con reporte pendiente
  - `GET /api/reportes/` → lista paginada
  - `GET /api/reportes/{id}/download/` → URL firmada o error descriptivo
  - `DELETE /api/reportes/{id}/` → borra S3 + registro
  - Verificable: integration tests en `test_api.py` cubren estados pendiente/listo/expirado y permisos
  - _Requirements: 2.1, 2.2, 3.1, 4.1, 4.2, 4.3, 4.4, 5.1, 5.3, 5.4_
  - _Boundary: apps/reportes/views.py, apps/reportes/serializers.py_
  - _Depends: 5.1_

---

- [ ] 6. Builders (PDF y Excel)
- [ ] 6.1 Implementar PDFBuilder con ReportLab (P)
  - `build(data, filtros)`: portada con título y filtros + tabla de acciones + tabla de issues + métricas resumen
  - Retorna `bytes` del PDF generado en memoria (no archivo en disco)
  - Verificable: `test_builders.py` — `build(data)` retorna bytes > 0; PDF contiene al menos una página
  - _Requirements: 2.4_
  - _Boundary: apps/reportes/builders.py_
  - _Depends: 1.2_

- [ ] 6.2 Implementar ExcelBuilder con openpyxl (P)
  - `build(data, filtros)`: workbook con hojas 'Acciones' (columnas tipo/estado/área/responsable/fecha_limite), 'Issues' (tipo/área/gravedad/fecha), 'Resumen' (conteos por estado/tipo)
  - Retorna `bytes` en memoria
  - Verificable: `test_builders.py` — `build(data)` retorna bytes > 0; workbook tiene 3 hojas
  - _Requirements: 3.3_
  - _Boundary: apps/reportes/builders.py_
  - _Depends: 1.2_

---

- [ ] 7. Celery task generar_reporte
- [ ] 7.1 Implementar tarea Celery `sgca.reportes.generar_reporte`
  - Pasos: cargar reporte + queries con filtros → build PDF o Excel → upload S3 → actualizar ReporteGenerado (listo, s3_path, expira_at) → enviar email SendGrid con URL firmada
  - Idempotencia: skip si reporte ya en estado 'listo'
  - En except: marcar estado='error', log ERROR; max_retries=3 con backoff exponencial
  - Celery task name: `sgca.reportes.generar_reporte`
  - Verificable: `test_tasks.py` con mock S3 y mock SendGrid — reporte pasa a 'listo'; email enviado con URL firmada
  - _Requirements: 2.1, 2.3, 2.4, 2.5, 3.1, 3.2, 3.4_
  - _Boundary: apps/reportes/tasks.py_
  - _Depends: 5.1, 6.1, 6.2_

---

- [ ] 8. Frontend: Dashboard con Recharts
- [ ] 8.1 Implementar DashboardPage con charts de Recharts (P)
  - `DashboardPage.tsx`: layout con panel de filtros (fecha, area) + 5 secciones de charts
  - `AccionesPorEstadoChart.tsx`: PieChart (donut) con estados
  - `AccionesPorTipoChart.tsx`: BarChart vertical por tipo
  - `AccionesPorAreaChart.tsx`: BarChart horizontal por área
  - `CumplimientoDeadlinesChart.tsx`: BarChart stacked (a_tiempo vs vencidas)
  - `TendenciaIncidentesChart.tsx`: LineChart de 12 meses
  - `DashboardFilters.tsx`: inputs fecha_inicio, fecha_fin, area con submit
  - `dashboardService.ts`: `getMetricas(filtros)` → GET /api/dashboard/metricas/
  - Verificable: página carga sin errores en browser; filtros actualizan todos los charts
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_
  - _Boundary: frontend/src/pages/dashboard/, frontend/src/components/dashboard/_
  - _Depends: 4.1_

- [ ] 8.2 Implementar ReportesPage para gestión de solicitudes (P)
  - `ReportesPage.tsx`: formulario para solicitar PDF/Excel con filtros + tabla de reportes con estado y botón de descarga
  - `reportesService.ts`: `solicitarReporte(tipo, filtros)`, `listarReportes()`, `getDownloadUrl(id)`, `eliminarReporte(id)`
  - Mostrar estados con badge (pendiente/listo/expirado/error); refrescar lista periódicamente si hay reportes pendientes
  - Verificable: usuario puede solicitar reporte, ver estado pendiente, descargar cuando listo
  - _Requirements: 2.1, 2.2, 3.1, 4.1, 4.2, 4.3, 5.1, 5.3_
  - _Boundary: frontend/src/pages/reportes/, frontend/src/services/reportes.ts_
  - _Depends: 5.2_

---

- [ ] 9. Tests de aislamiento y permisos
- [ ] 9.1 Tests de aislamiento de tenant y permisos completos
  - Verificar que ReporteGenerado de tenant A no es accesible desde tenant B (404)
  - Verificar que responsable y verificador reciben 403 en todos los endpoints de reportes y dashboard
  - Verificar que supervisor solo ve sus propios reportes; admin ve todos los del tenant
  - Verificar que supervisor no puede eliminar reporte de otro usuario (403)
  - Verificable: todos los tests en `test_permissions.py` pasan
  - _Requirements: 1.7, 4.4, 5.4_
  - _Boundary: apps/reportes/tests/test_api.py_
  - _Depends: 5.2, 4.1_
