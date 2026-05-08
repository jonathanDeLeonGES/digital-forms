# Product: SGCA — Sistema de Gestión y Control de Acciones

## Qué es
SaaS multi-tenant para gestión del ciclo de vida completo de acciones correctivas, 
preventivas y de mejora derivadas de eventos de seguridad industrial.

## Clientes objetivo
Empresas industriales en Guatemala y Centroamérica que necesitan trazabilidad 
de incidentes de seguridad para auditorías y cumplimiento normativo.

## Problema que resuelve
Las empresas gestionan sus acciones de seguridad en Excel o papel, sin trazabilidad, 
sin notificaciones automáticas y sin verificación de que las acciones realmente 
funcionaron a largo plazo.

## Flujo principal
1. Ocurre un evento (incidente, casi incidente, reunión de seguridad)
2. Se registra como Issue con análisis de causa raíz (Diagrama de Ishikawa)
3. Se generan Acciones (correctiva/preventiva/mejora) con responsables asignados
4. Cada acción tiene un Plan de Trabajo con actividades, deadlines y evidencias
5. Las acciones transitan por estados: Abierto → En proceso → Cerrado → Verificado
6. Meses después se verifica si la acción fue realmente eficaz

## Modelo de negocio SaaS

### Planes
- **Trial**: 14 días de acceso completo al registrarse. 
  El admin del sistema puede extender manualmente la fecha de vencimiento.
- **Enterprise**: acceso completo sin límite de tiempo. 
  El admin del sistema activa este plan y asigna la cantidad de licencias (usuarios).

### Gestión de licencias
- Cada tenant en modo Enterprise tiene un número máximo de usuarios definido por el admin del sistema.
- El admin del sistema puede cambiar un tenant de Trial a Enterprise desde un panel de administración interno.
- No hay autoservicio de pagos por ahora.

### Lo que queda fuera del MVP
- Pagos, facturación y Stripe
- Plan Free y Plan Pro
- Upgrades automáticos

## Roles del sistema
- Admin: configura catálogos, gestiona usuarios, ve todos los reportes
- Responsable: ejecuta actividades del plan de trabajo, sube evidencias
- Supervisor: valida ejecución, aprueba cierre de acciones
- Verificador: verifica eficacia a largo plazo