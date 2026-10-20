# 🖥️ Comfutech Monitor

Sistema de monitoreo de red para **Comfutech** en Güigüe, Estado Carabobo, Venezuela.

Permite supervisar en tiempo real el estado de equipos de red (MikroTik, Cisco, Huawei,
Ubiquiti, Cambium y genéricos) vía **SNMP**, **ICMP** y **TCP**, con visualización en
**Grafana**, notificaciones por **Telegram**, recuperación de contraseña por email y
gestión completa desde una interfaz web **Django**.

**Versión actual:** 2.0 (post-refactor Django)  
**Estado:** Desarrollo activo  
**Última actualización:** Octubre 2026

---

## 📑 Tabla de contenido

1. [Descripción general](#-descripción-general)
2. [Historia del proyecto](#-historia-del-proyecto)
3. [Arquitectura del sistema](#-arquitectura-del-sistema)
4. [Stack tecnológico](#-stack-tecnológico)
5. [Características principales](#-características-principales)
6. [Estructura del proyecto](#-estructura-del-proyecto)
7. [Requisitos previos](#-requisitos-previos)
8. [Instalación paso a paso](#-instalación-paso-a-paso)
9. [Configuración](#-configuración)
10. [Base de datos](#-base-de-datos)
11. [Modelos y esquema](#-modelos-y-esquema)
12. [Motor de monitoreo](#-motor-de-monitoreo)
13. [Sistema de alertas multi-condicional](#-sistema-de-alertas-multi-condicional)
14. [Sistema de usuarios y verificación de email](#-sistema-de-usuarios-y-verificación-de-email)
15. [Configuración del sistema (UI)](#-configuración-del-sistema-ui)
16. [Interfaz web y navegación](#-interfaz-web-y-navegación)
17. [Integraciones externas](#-integraciones-externas)
18. [Exportación de datos](#-exportación-de-datos)
19. [Roles y permisos](#-roles-y-permisos)
20. [Despliegue en producción](#-despliegue-en-producción)
21. [Operación y mantenimiento](#-operación-y-mantenimiento)
22. [Solución de problemas](#-solución-de-problemas)
23. [Glosario](#-glosario)
24. [Changelog](#-changelog)
25. [Resumen del contenido](#-resumen-de-lo-que-cubre-este-readme)

---

## 🎯 Descripción general

**Comfutech Monitor** es un sistema completo de monitoreo de red que resuelve la
problemática de la empresa Comfutech en su sede de Güigüe: la ausencia de un sistema
centralizado de gestión (NMS) que consolidara las métricas de sus equipos de red
principales.

### Problema que resuelve

- **Antes**: el personal técnico verificaba manualmente cada equipo, desconociendo
  el estado real de la red, detectando fallas solo por reclamos de usuarios.
- **Después**: un panel web centralizado, con métricas en tiempo real, alertas
  automáticas multi-condicionales, notificaciones a Telegram y configuración 100%
  desde la UI, todo gestionado desde un navegador.

### Alcance actual

El sistema monitorea:

- **Equipos de red**: routers, switches, CPE, firewalls
- **Fabricantes soportados**: MikroTik, Cisco, Huawei, Ubiquiti, Cambium, genéricos
- **Modelos específicos**: cada fabricante puede tener N modelos con OIDs propios
- **Métricas de tráfico**: capacidad, Rx/Tx, utilización por interfaz
- **Métricas de chasis**: CPU, memoria, temperatura, uptime
- **Disponibilidad**: latencia ICMP, pérdida de paquetes, puertos TCP
- **Alertas**: reglas multi-condicionales (1-5 condicionales lógicos con AND/OR)

### Beneficios medibles

| Antes | Después |
|---|---|
| Verificación manual equipo por equipo | Monitoreo automático cada 60s |
| Detección de fallas por reclamos | Alertas proactivas con antelación |
| Sin visibilidad histórica | Dashboards con retención de 90 días |
| Sin notificaciones automáticas | Push a Telegram en <30s |
| Sin control de acceso | 3 niveles de roles + auditoría |
| Config por `.env` disperso | Config centralizada en BD + UI |

---

## 📜 Historia del proyecto

El sistema pasó por **dos fases** de desarrollo:

### Fase 1 — Prototipo en C++ (descontinuado)

Se construyó un CRUD de escritorio en **C++ con Visual Studio 2015** para gestionar
el inventario de equipos. Se descartó por:

- Dificultad de mantenimiento y despliegue
- Falta de integración natural con el stack Python/SNMP
- UI Win32 difícil de evolucionar

**Estado**: archivado en `_legacy/`. No forma parte del sistema actual.

### Fase 2 — Reingeniería en Django (actual)

Se reescribió todo el sistema como aplicación web Django, con las siguientes
iteraciones:

| Iteración | Cambios principales |
|---|---|
| **v0.1** — Setup inicial | Django, apps, modelos base, MySQL |
| **v0.2** — Inventario | CRUD de equipos e interfaces, discovery SNMP |
| **v0.3** — Motor de polling | Pollers SNMP/ICMP/Core Health, InfluxDB, APScheduler |
| **v0.4** — Sistema de alertas | Reglas por equipo, severidad, cooldown Telegram |
| **v0.5** — Configuración | Panel de configuración del sistema en BD |
| **v0.6** — Autenticación | Login custom, roles, protección de superadmin |
| **v0.7** — Recuperación | Password reset con código, verificación de email |
| **v0.8** — Alertas v2 | Multi-condicional (1-5), AND/OR, paginación |
| **v0.9** — Modelos | `DeviceModel`, `is_wireless_link`, vendor → model |
| **v1.0** — Refactor UI | Navbar lateral, theme switcher, monitor split |
| **v2.0** — Config UI v2 | Un solo formulario, secciones, tests desde POST |

**Estado actual**: v2.0 — estable para uso interno.

---

## 🏗️ Arquitectura del sistema

```
┌──────────────────────────────────────────────────────────────────┐
│                     NAVEGADOR WEB (Cliente)                      │
│  Login · Dashboard · Equipos · Interfaces · Alertas · Reglas     │
│  Monitor · Usuarios · Configuración · Grafana (link externo)     │
└──────────────────────────────┬───────────────────────────────────┘
                               │ HTTP (puerto 8000)
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│              DJANGO 4.2 + WAITRESS (Servicio Windows)            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │ Autenticación    │  │ CRUD (ORM)       │  │ Config UI      │ │
│  │ Login/Logout     │  │ Equipos/Reglas   │  │ (BD → runtime) │ │
│  │ Roles/Perfiles   │  │ Alertas/Usuarios │  │ Test endpoints │ │
│  └──────────────────┘  └──────────────────┘  └────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Context processors: grafana_available, is_admin, theme      │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────┬────────────────────────────────────┬───────────────────┘
          │ ORM (MySQL)                        │ servicios internos
          ▼                                    ▼
┌──────────────────────────┐    ┌─────────────────────────────────┐
│  MySQL 5.7 / 8.0         │    │   Monitor (APScheduler)         │
│  ─────────────────────   │    │  ┌───────────────────────────┐  │
│  - auth_user             │◄───┤  │ 4 jobs concurrentes:      │  │
│  - devices               │    │  │  · SNMP Traffic Poller    │  │
│  - device_models         │    │  │  · Core Health Poller     │  │
│  - interfaces            │    │  │  · ICMP/TCP Poller        │  │
│  - alert_rules           │    │  │  · Heartbeat + Reload     │  │
│  - alerts                │    │  └───────────────────────────┘  │
│  - thresholds            │    │  ┌───────────────────────────┐  │
│  - system_config         │    │  │ Motor de alertas:         │  │
│  - email_config          │    │  │  · 1-5 condicionales      │  │
│  - email_verifications   │    │  │  · AND/OR                 │  │
│  - password_reset_codes  │    │  │  · Anti-duplicados        │  │
│  - password_reset_attempts│   │  │  · Warm-up 120s           │  │
│  - monitor_status        │    │  └───────────────────────────┘  │
│  - discovery_jobs        │    └──────────┬──────────────────────┘
└──────────────────────────┘               │
                                           ├──→ InfluxDB (métricas)
                                           ├──→ Telegram (alertas)
                                           └──→ SMTP (emails)

          ┌──────────────────────────────────────┐
          │  InfluxDB 2.9.1                      │
          │  bucket: metricas_red (90d retención)│
          │  measurements:                       │
          │    · traffic (bps, utilización)      │
          │    · health (cpu, mem, temp)         │
          │    · icmp (latencia, pérdida)        │
          │    · tcp (puertos)                   │
          └─────────────┬────────────────────────┘
                        │
                        ▼
          ┌──────────────────────────────────────┐
          │  Grafana OSS 10.x                    │
          │  dashboards en tiempo real           │
          └──────────────────────────────────────┘
```

### Componentes detallados

| Componente | Rol | Servicio Windows | Puerto |
|---|---|---|---|
| **Django + Waitress** | Backend web, ORM, UI | `ComfutechDjango` | 8000 |
| **APScheduler** | Scheduler de polling en background | `ComfutechMonitor` | — |
| **MySQL** | Base de datos relacional | `MySQL80` | 3306 |
| **InfluxDB 2.9** | Base de datos de series temporales | `influxdb` | 8086 |
| **Grafana** | Visualización | `grafana` | 3000 |
| **Telegram Bot API** | Notificaciones push | (externo) | 443 |
| **SMTP** | Email transaccional | (externo) | 587/465 |
| **NSSM** | Envoltorio de servicios | (ejecutable) | — |

---

## 🛠️ Stack tecnológico

### Backend

| Tecnología | Versión | Rol |
|---|---|---|
| **Python** | 3.11+ (probado en 3.13) | Runtime |
| **Django** | 4.2 LTS / 5.x | Framework web |
| **Waitress** | 2.x | Servidor WSGI de producción |
| **APScheduler** | 3.10+ | Scheduler en background |
| **pysnmp** | 7.1+ | Cliente SNMP asíncrono |
| **influxdb-client** | 1.44+ | Escritura/lectura InfluxDB 2.x |
| **mysqlclient** / **pymysql** | 2.2+ / 1.1+ | Conexión MySQL |
| **requests** | 2.32+ | APIs externas (Telegram, Grafana health) |
| **python-dotenv** | 1.0+ | Variables de entorno |
| **openpyxl** | 3.1+ | Exportación Excel |
| **reportlab** | 4.2+ | Exportación PDF |

### Frontend

| Tecnología | Versión | Rol |
|---|---|---|
| **Bootstrap** | 5.3.x | Framework CSS (vía CDN) |
| **Bootstrap Icons** | 1.11.x | Iconografía (vía CDN) |
| **JavaScript** | ES2020+ | Interacciones dinámicas |
| **Django Templates** | — | Renderizado server-side |

### Bases de datos

| Base | Versión | Rol |
|---|---|---|
| **MySQL** | 5.7+ / 8.0 | Inventario, alertas, config, usuarios |
| **InfluxDB** | 2.9.1+ | Series temporales de métricas |

### Visualización y notificaciones

| Herramienta | Rol |
|---|---|
| **Grafana OSS** | Dashboards en tiempo real |
| **Telegram Bot API** | Notificaciones push a grupos |

### Despliegue

| Herramienta | Rol |
|---|---|
| **NSSM 2.24+** | Servicios Windows |
| **Windows** | 10/11 o Server 2016+ |

---

## ✨ Características principales

### 🧩 Gestión de inventario

#### Equipos (`devices`)

- **Nombre descriptivo** y dirección IP única
- **Tipo**: router, switch, CPE, firewall
- **Rol**: core, distribution, access, cpe
  - Los roles `core` y `distribution` reciben polling extendido de chasis
- **Fabricante** (`vendor`): cisco, mikrotik, huawei, ubiquiti, cambium, generic
- **Modelo** (`device_model`): FK obligatorio a `DeviceModel`
- **Ubicación física** y **estado activo**
- **Parámetros SNMP**: versión, community, usuario, auth, priv
- **Puertos TCP** a chequear (separados por coma)

#### Modelos de equipos (`device_models`)

- **Fabricante** + **Nombre de modelo**
- **OIDs específicos** del modelo en JSON (override de los OIDs por fabricante)
- **Flag `is_wireless_link`**: marca equipos de radio-enlace (AirMax, Cambium, etc.)
- Al **elegir fabricante** en el form de equipos, se cargan solo los modelos de ese fabricante vía AJAX
- Si un modelo tiene OIDs propios, el poller de chasis los usa en lugar de los genéricos

#### Interfaces (`interfaces`)

- Se descubren automáticamente vía **SNMP walk**
- Cada interfaz tiene: `ifIndex`, `ifName`, `ifAlias`, `ifSpeed`, `ifType`, `admin_status`, `oper_status`
- **Flag `monitored`** controlado por el usuario: solo las marcadas se pollean
- Filtros y ordenamiento en la UI

#### Discovery de interfaces

- **Ejecución manual** desde un botón en la UI
- **Ejecución masiva** desde `/monitoreo/live/` (botón "Discovery Interfaces")
- Cada ejecución queda registrada en `discovery_jobs` con métricas (duración, interfaces creadas/actualizadas/eliminadas, errores)
- **NO sobrescribe** el campo `monitored` del usuario

---

### 📊 Motor de monitoreo

El sistema ejecuta **4 jobs concurrentes** con APScheduler:

#### 1. Discovery Poller (manual o programado)

- Recorre el árbol IF-MIB vía SNMP walk
- Persiste las interfaces en MySQL con `ON DUPLICATE KEY UPDATE`
- Detecta interfaces nuevas, actualizadas y eliminadas
- Registra cada ejecución en `discovery_jobs`

#### 2. SNMP Traffic Poller (cada 60s configurable)

- Por cada interfaz con `monitored=True` y `oper_status=True`:
  - Lee `ifHCInOctets` / `ifHCOutOctets` (64 bits)
  - Fallback a `ifInOctets` / `ifOutOctets` (32 bits) si es necesario
  - Calcula `in_bps` / `out_bps` comparando con lectura previa (cache en memoria)
  - **Detecta counter wrap** para contadores de 32 bits
  - Calcula `utilization_pct` con sanity check (>500% se descarta)
- Escribe a InfluxDB en `traffic` con:
  - `in_bps`, `out_bps`, `utilization_pct`, `capacity_bps`, `rx_octets`, `tx_octets`
  - Tags: `device`, `ip`, `interface`, `role`

#### 3. Core Health Poller (cada 120s configurable)

- Solo para equipos con `device_role IN ('core', 'distribution')`
- Lee OIDs específicos según el **modelo** del equipo (fallback al **fabricante**)
- OIDs por fabricante en `chassis_oids.py`:

| Fabricante | CPU | Memoria | Temperatura |
|---|---|---|---|
| **MikroTik** (ROS 7) | `hrProcessorLoad` multi-core + propietario | `hrStorageUsed/Size.65536` | `mtxrHlTemperature` |
| **Cisco** | `cpmCPUTotal5min` | `ciscoMemoryPoolUsed` | `ciscoEnvMonTemperatureStatusValue` |
| **Huawei** | `hwEntityCpuUsage` | `hwEntityMemUsage` | `hwEntityTemperature` |
| **Ubiquiti** | `ubntSystemCPU` | `ubntSystemMem` | `ubntSystemTemp` |
| **Cambium** | `whispCpuUtilization` | — | — |

- Calcula `mem_pct` invirtiendo `free`/`total` cuando aplica
- Convierte TimeTicks a segundos
- Escribe a InfluxDB en `health`:
  - `cpu_pct`, `mem_pct`, `temp_c`, `uptime`
  - Tags: `device`, `ip`, `role`, `vendor`

#### 4. ICMP/TCP Poller (cada 120s configurable)

- **Paralelizado** con `ThreadPoolExecutor` (20 workers por defecto)
- Por cada equipo activo:
  - Ping ICMP con timeout configurable (1s por defecto)
  - Soporta **multi-encoding** para parsear el output del `ping.exe` (utf-8, cp1252, cp850, latin-1)
  - Calcula latencia media y porcentaje de pérdida
  - Chequeo TCP de los puertos configurados en `tcp_ports`
- Escribe a InfluxDB en `icmp` y `tcp`

#### 5. Heartbeat Poller (cada 60s)

- Actualiza `monitor_status.last_heartbeat`
- Detecta cambios en `SystemConfig` y los aplica **sin reiniciar** el proceso:
  - Cambio de intervalos → `modify_job`
  - Cambio de `enabled` → `pause`/`resume`
  - Cambio de InfluxDB → reset del cliente
- Reinicia el contador de warm-up de alertas

#### Configuración del scheduler

- `max_instances=1`: evita ciclos concurrentes del mismo job
- `coalesce=True`: si se pierden ciclos, se ejecuta solo uno al reanudar
- `misfire_grace_time=30`: tolerancia de retraso

---

### 🚨 Sistema de alertas multi-condicional (v2.0)

**Diseño**: cada regla tiene **1-5 condicionales lógicos** que se combinan con
**AND** / **OR**. La configuración completa se almacena como **JSON** en la
columna `conditionals` de la tabla `alert_rules`.

#### Estructura JSON de `conditionals`

```json
[
  {
    "device_id": 1,
    "metric": "cpu_pct",
    "operator": "gte",
    "threshold": 75.0,
    "duration_sec": 60,
    "logic": null
  },
  {
    "device_id": 2,
    "metric": "packet_loss_pct",
    "operator": "gte",
    "threshold": 5.0,
    "duration_sec": 120,
    "logic": "AND"
  }
]
```

- El primer condicional no necesita `logic` (es el punto de partida).
- Del segundo en adelante, `logic` es `AND` u `OR`.
- La combinación se evalúa de izquierda a derecha:
  `((cond1) AND/OR (cond2)) AND/OR (cond3) ...`

#### Métricas disponibles

| Métrica | Descripción | Unidad | Operadores válidos |
|---|---|---|---|
| `device_down` | Caída ICMP | binario | `eq` |
| `latency_ms` | Latencia ICMP | ms | `gte`, `gt` |
| `packet_loss_pct` | Pérdida de paquetes | % | `gte`, `gt` |
| `utilization_pct` | Utilización de enlace | % | `gte`, `gt` |
| `cpu_pct` | Uso de CPU | % | `gte`, `gt` |
| `mem_pct` | Uso de memoria | % | `gte`, `gt` |
| `temp_c` | Temperatura | °C | `gte`, `gt` |

#### Flags de comportamiento

| Flag | Descripción |
|---|---|
| `enabled` | Regla activa / inactiva |
| `fire_once` | Dispara solo una vez por periodo de violación (útil para "vuelta en línea") |
| `skip_on_startup` | No evalúa durante los primeros 120s tras arrancar el monitor |
| `telegram_enabled` | Notificar por Telegram |
| `telegram_cooldown_sec` | Cooldown mínimo entre notificaciones (mín. 60s) |

#### Máquina de estados

Por cada **(regla, condicional)** el motor mantiene:

```python
_cond_states[(rule_id, cond_index)] = {
    "first_seen": timestamp,
    "last_value": float,
}
```

- Cuando la condición empieza a cumplirse → `first_seen = ahora`
- Cuando sigue cumpliéndose → solo actualiza `last_value`
- Cuando deja de cumplirse → elimina el estado
- Si `ahora - first_seen >= duration_sec` → el condicional está "listo"

Además, por regla:

```python
_rule_fired[rule_id] = True/False
```

Controla el flag `fire_once`.

#### Placeholders del mensaje personalizado

Puedes personalizar el mensaje con placeholders. **Todos** son reemplazados al
disparar la alerta.

**Generales:**

| Placeholder | Valor |
|---|---|
| `{rule_name}` | Nombre de la regla |
| `{severity}` | Prioridad (Info / Advertencia / Crítica) |
| `{timestamp}` | Fecha y hora del disparo |
| `{conditionals_count}` | Número de condicionales |

**Del primer condicional (compatibilidad):**

| Placeholder | Valor |
|---|---|
| `{device}` | Nombre del equipo del primer condicional |
| `{ip}` | IP del equipo del primer condicional |
| `{metric}` | Métrica del primer condicional |
| `{operator}` | Operador del primer condicional |
| `{threshold}` | Umbral del primer condicional |
| `{value}` | Valor observado del primer condicional |

**Numerados (1-5):**

| Placeholder | Valor |
|---|---|
| `{device1}`...`{device5}` | Nombre del equipo del condicional N |
| `{ip1}`...`{ip5}` | IP del condicional N |
| `{metric1}`...`{metric5}` | Métrica del condicional N |
| `{operator1}`...`{operator5}` | Operador del condicional N |
| `{value1}`...`{value5}` | Valor observado del condicional N |
| `{threshold1}`...`{threshold5}` | Umbral del condicional N |

> **Fix aplicado en v2.0**: el bug anterior donde `{device}` mostraba
> `"RB Guigue (10.215.253)"` en lugar de solo `"RB Guigue"` fue resuelto.
> Ahora cada placeholder tiene su valor explícito y **no hay manera de que
> se mezclen**.

#### Anti-duplicados

- Por regla + equipo: si ya existe una alerta **activa** de esa regla para el
  mismo equipo, no se crea otra.
- Cooldown de Telegram: por regla + equipo, configurable.

#### Auto-resolución

- Cuando la combinación de condicionales deja de cumplirse, todas las alertas
  **activas** de esa regla se marcan como **resueltas** automáticamente.
- El flag `fire_once` se resetea para permitir un nuevo disparo futuro.

#### Ejemplo completo

**Regla**: "Alerta de saturación en Core"

- **Condicional 1**: Core 1, CPU ≥ 75%, 300s
- **Condicional 2**: (AND) Core 1, MEM ≥ 80%, 300s
- **Condicional 3**: (OR) Core 2, Packet Loss ≥ 5%, 120s

**Mensaje personalizado**:

```
🔥 {rule_name}

Saturación detectada:
- {device1}: CPU {value1}% (>{threshold1}%)
- {device2}: Mem {value2}% (>{threshold2}%)
- {device3}: Loss {value3}% (>{threshold3}%)
```

**Resultado en Telegram**:

```
🔥 Alerta de saturación en Core

Saturación detectada:
- Core-1: CPU 87.3% (>75.0%)
- Core-1: Mem 84.1% (>80.0%)
- Core-2: Loss 8.5% (>5.0%)
```

---

### 📱 Notificaciones Telegram

- **Configuración 100% desde la UI** (no más editar `.env`)
- Bot Token y Chat ID se guardan en `system_config`
- **Mensajes personalizados por regla** con placeholders
- **Cooldown configurable** por regla (mínimo 60s)
- **Botón "Enviar mensaje de prueba"** desde el panel de configuración
- Soporta **grupos** (chat_id con signo negativo)
- Formato HTML (negritas, emojis)
- Si el mensaje es personalizado → **no** se añade contexto automático
- Si es automático → se añade equipo + regla al final

---

### 👥 Sistema de usuarios con verificación de email

El sistema de usuarios es **completo y robusto**:

#### Creación de usuarios

- **Username**: 3-150 caracteres, sin espacios, solo `[a-zA-Z0-9._-]`
- **Nombre/Apellido**: solo letras (con acentos), espacios, guiones y apóstrofes
- **Email**: obligatorio, único en el sistema (un email = un usuario)
- **Contraseña**: 8-16 caracteres con validación de fuerza
- **Rol**: superadmin, administrador o usuario (nunca se puede crear otro superadmin)
- **Auto-envío**: al crear, se envía automáticamente el email de verificación

#### Verificación de email

- Cada usuario tiene un registro `EmailVerification` con:
  - `verified` (booleano)
  - `verified_email` (para invalidar si cambia el email)
  - `token` (UUID único)
  - `token_created_at` (para expiración)
- **Token válido por 48 horas**
- Al verificar, se marca `verified=True` y se guarda el email verificado
- **Solo el superadmin puede cambiar el email** de otro usuario
- Al cambiar el email:
  1. Se invalida la verificación anterior (`reset_verification()`)
  2. Se envía automáticamente un nuevo enlace de verificación
  3. El nuevo correo aparece como "Sin verificar" en la lista

#### Indicadores visuales

En `/usuarios/`:

- Badge **verde "Verificado"** si el email está verificado
- Badge **amarillo "Sin verificar"** si tiene email pero no verificado
- Badge **gris "Sin correo"** si no tiene email
- Botón **naranja de reenvío** si no está verificado
- Botón **verde deshabilitado** si ya está verificado

#### Recuperación de contraseña

- Formulario pide usuario o email
- Verifica que el email esté **verificado** (si no, rechaza con mensaje claro)
- Genera un **código de 8 dígitos** válido por **5 minutos**
- Envía el código por email
- Anti-fuerza-bruta: máx. 5 intentos fallidos en 15 min
- Al validar el código → permite establecer nueva contraseña
- Código se marca como `used=True` tras usarlo

#### Contraseñas

- **Longitud**: 8-16 caracteres (validado en cliente y servidor)
- **Indicador de fuerza**: 5 niveles (Muy corta, Débil, Aceptable, Buena, Excelente)
- **Toggle de visibilidad**: botón 👁️ en cada campo de contraseña
- **Validación de coincidencia** en tiempo real
- **Validación Django** (`validate_password`) adicional

#### Protecciones especiales

- **Nadie puede cambiar su propio rol** (ni superadmin)
- **No se puede eliminar al último superadmin activo**
- **No se puede desactivar al último superadmin activo**
- **No se puede eliminar al usuario `admin`** (nombre literal)
- **Los admins no ven** a otros admins ni superadmins

---

### ⚙️ Configuración del sistema (UI v2.0)

Diseño **compacto** en una sola card con secciones separadas por líneas:

#### Secciones

1. **InfluxDB**
   - URL, API Token (oculto), Organización, Bucket
   - Botón "Probar conexión" (verifica servidor + token + bucket)
   - Tip sobre crear API Token con permisos Read & Write

2. **Parámetros del Monitor**
   - Switch `monitor_enabled`
   - 3 intervalos (SNMP, Health, ICMP)
   - Tabla de recomendaciones (mínimo, recomendado) en `<details>`

3. **Telegram**
   - Switch `telegram_enabled`
   - Bot Token (oculto) y Chat ID
   - Botón "Probar" (envía mensaje de prueba)
   - Guía paso a paso con `@BotFather` en `<details>`

4. **Grafana**
   - URL del dashboard
   - Botón "Probar" (verifica que responda)
   - Ejemplos de URL en `<details>`
   - Aviso: si no responde, el botón del navbar desaparece

5. **Email (SMTP)**
   - Servidor, Puerto
   - TLS/SSL (mutuamente excluyentes, uno desactiva al otro)
   - Usuario SMTP
   - Contraseña SMTP (oculta)
   - Remitente por defecto
   - Botón "Probar" (modal con email destino)
   - Guía para obtener contraseña de aplicación de Gmail en `<details>`

#### Características del diseño

- **Un solo formulario** con **un solo botón "Guardar toda la configuración"**
- **Cada test lee del POST** (no necesita guardar antes)
- **Warning al salir** si hay cambios sin guardar
- **Botón "Descartar"** (type="reset")
- **Estado "Configurado"** en tokens/contraseñas que ya existen
- **Última actualización** en el footer (fecha + usuario)

---

### 🎨 Interfaz web

#### Navbar lateral sticky colapsable

- **Sidebar fijo a la izquierda** que se expande/colapsa
- **Estado colapsado**: solo iconos
- **Estado expandido**: iconos + textos
- **Persistencia**: el estado se guarda en `localStorage`
- **Expansión automática**: al pulsar cualquier botón del sidebar se expande
- **Excepción**: el botón del theme switcher NO expande el sidebar
- **Submenús desplegables** para Equipos, Reglas y Monitor
- **Responsive**: en móviles se oculta y se muestra con botón hamburguesa + overlay

#### Dropdowns del sidebar

| Menú | Opciones |
|---|---|
| **Equipos** | Ver todos · Nuevo equipo |
| **Reglas** | Ver todas · Nueva regla |
| **Monitor** | Estado del servicio · Monitoreo en vivo |

#### Theme switcher

- **Modo Claro**
- **Modo Oscuro**
- **Automático** (según preferencia del SO)
- Persistencia en `localStorage`
- Aplicado **antes** de renderizar (evita flash)
- Icono cambia según el tema activo

#### Botón Grafana (condicional)

- **Solo se muestra** si la URL de Grafana responde
- Validación con cache de 5 minutos
- Se oculta automáticamente si el servidor no responde

#### Patrones de UI

- **Buscadores colapsables**: cerrados por defecto, se abren al filtrar
- **Headers clicables**: ordenamiento ascendente/descendente
- **Botones "Volver"**: siempre en la esquina superior derecha
- **Stats cards clicables**: filtran con un click
- **Badges de color**: severidad, estado, rol
- **Paginación de 10 en 10** en alertas y reglas
- **Sticky footer** en formularios largos

---

### 📤 Exportación de datos

- **Excel** (`.xlsx`): con openpyxl, colores por severidad/estado, panel congelado
- **PDF** (A4 landscape): con reportlab, encabezados repetidos
- Ambos respetan **filtros** y **orden** aplicados en la lista
- Endpoints: `/alertas/export/excel/` y `/alertas/export/pdf/`

---

## 📁 Estructura del proyecto

```
sistema-trafico/
├── manage.py
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
├── README.md
│
├── sistema/                              # Configuración Django
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── core/                                 # App: dashboard, usuarios, config
│   ├── migrations/
│   ├── templatetags/
│   │   ├── __init__.py
│   │   ├── core_extras.py                # Filtro has_group
│   │   └── sorting_tags.py               # Tag sortable_th
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py                         # SystemConfig, EmailConfig,
│   │                                     # EmailVerification, PasswordResetCode,
│   │                                     # PasswordResetAttempt
│   ├── forms.py                          # UserCreateForm, UserEditForm,
│   │                                     # UserPasswordForm
│   ├── views.py                          # Dashboard
│   ├── views_users.py                    # CRUD de usuarios
│   ├── views_settings.py                 # Config + tests
│   ├── views_auth.py                     # Login custom + setup inicial
│   ├── views_email.py                    # Verificación de email
│   ├── views_password_reset.py           # Recuperación de contraseña
│   ├── decorators.py                     # @require_admin_or_super, etc.
│   ├── roles.py                          # Lógica de roles
│   ├── context_processors.py             # grafana_available, is_admin, theme
│   ├── sorting.py                        # Helper de ordenamiento
│   ├── signals.py                        # Cache invalidation
│   ├── runtime_config.py                 # Config lazy desde BD
│   ├── email_utils.py                    # Helpers de envío de email
│   ├── management/
│   │   └── commands/
│   │       └── setup_roles.py
│   ├── urls.py
│   └── admin.py
│
├── inventario/                           # App: equipos, modelos, interfaces
│   ├── migrations/
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py                         # Device, DeviceModel, Interface
│   ├── forms.py                          # DeviceForm
│   ├── views.py                          # CRUD + API models
│   ├── management/
│   │   └── commands/
│   │       └── load_device_models.py     # Poblar modelos con OIDs
│   ├── urls.py
│   └── admin.py
│
├── alertas/                              # App: alertas, reglas multi-condicionales
│   ├── migrations/
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py                         # AlertRule (JSON conditionals), Alert, Threshold
│   ├── forms.py                          # AlertRuleForm
│   ├── views.py                          # CRUD alertas + reglas (paginado)
│   ├── exports.py                        # Excel + PDF
│   ├── urls.py
│   └── admin.py
│
├── monitoreo/                            # App: motor de monitoreo
│   ├── management/
│   │   └── commands/
│   │       ├── __init__.py
│   │       ├── run_monitor.py            # Comando principal
│   │       ├── poll_once.py              # Todos los pollers 1 vez
│   │       ├── poll_snmp.py              # Solo SNMP
│   │       ├── poll_health.py            # Solo chasis
│   │       └── poll_icmp.py              # Solo ICMP/TCP
│   ├── migrations/
│   ├── services/
│   │   ├── __init__.py
│   │   ├── snmp_client.py                # Cliente SNMP async (pysnmp 7.x)
│   │   ├── chassis_oids.py               # OIDs por fabricante
│   │   ├── discovery.py                  # Discovery SNMP walk
│   │   ├── traffic.py                    # Poller de tráfico
│   │   ├── health.py                     # Poller de chasis
│   │   ├── icmp_tcp.py                   # Poller ICMP/TCP paralelo
│   │   ├── alerts.py                     # Motor multi-condicional
│   │   ├── telegram.py                   # Notificador Telegram
│   │   ├── influx_writer.py              # Escritura InfluxDB
│   │   └── influx_reader.py              # Lectura InfluxDB (live)
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py                         # DiscoveryJob, MonitorStatus
│   ├── views.py                          # Discovery + status + live
│   ├── scheduler.py                      # APScheduler
│   ├── urls.py
│   └── admin.py
│
├── templates/
│   ├── base.html                         # Layout con sidebar lateral
│   ├── registration/
│   │   └── login.html
│   ├── core/
│   │   ├── dashboard.html
│   │   ├── user_list.html
│   │   ├── user_form.html
│   │   ├── user_password.html
│   │   ├── user_confirm_delete.html
│   │   ├── profile.html
│   │   ├── system_settings.html
│   │   ├── email_verify_result.html
│   │   ├── password_reset_request.html
│   │   ├── password_reset_verify.html
│   │   ├── password_reset_new_password.html
│   │   ├── superadmin_setup.html
│   │   └── _sortable_th.html
│   ├── inventario/
│   │   ├── device_list.html
│   │   ├── device_detail.html
│   │   ├── device_form.html
│   │   ├── device_interfaces.html
│   │   └── device_confirm_delete.html
│   ├── alertas/
│   │   ├── alert_list.html
│   │   ├── alert_confirm_delete.html
│   │   ├── rule_list.html
│   │   ├── rule_form.html
│   │   └── rule_confirm_delete.html
│   └── monitoreo/
│       ├── monitor_status.html
│       ├── monitor_live.html
│       └── discovery_history.html
│
├── static/
│   ├── css/
│   │   └── style.css                     # CSS propio (light/dark)
│   ├── js/
│   └── img/
│
├── logs/                                 # Logs rotativos (runtime)
│   ├── django_out.log
│   ├── django_err.log
│   ├── monitor_out.log
│   └── monitor_err.log
│
├── scripts/                              # Scripts Windows
│   ├── _detect_venv.bat
│   ├── run_django.bat
│   ├── run_monitor.bat
│   ├── install_services.bat
│   ├── uninstall_services.bat
│   ├── restart_services.bat
│   ├── view_logs.bat
│   └── deploy.bat
│
├── docs/
│   └── grafana-dashboard.json            # Dashboard exportado
│
├── python_local/                         # Venv (no versionar)
└── backups/                              # Respaldos
```

---

## ✅ Requisitos previos

### Software mínimo

| Software | Versión | Notas |
|---|---|---|
| **Windows** | 10 / 11 / Server 2016+ | También funciona en Linux con ajustes |
| **Python** | 3.11+ (probado 3.13) | [python.org](https://python.org) |
| **MySQL** | 5.7+ / 8.0 | [dev.mysql.com](https://dev.mysql.com/downloads/) |
| **InfluxDB** | 2.9.1+ | [influxdata.com](https://portal.influxdata.com/downloads/) |
| **Grafana** | 9.x+ | [grafana.com](https://grafana.com/grafana/download) |
| **NSSM** | 2.24+ | [nssm.cc](https://nssm.cc/download) |
| **Git** (opcional) | Última | Para clonar el repo |

### Cuentas externas

- **Telegram Bot**: creado con [@BotFather](https://t.me/BotFather)
- **Grupo de Telegram** donde el bot enviará las alertas
- **Cuenta de email SMTP** (Gmail con contraseña de aplicación, Office365, etc.)

---

## 🚀 Instalación paso a paso

### 1. Copiar el proyecto

```cmd
cd C:\Users\TuUsuario\Desktop
git clone <url-del-repo> sistema-trafico
cd sistema-trafico
```

O copia la carpeta `sistema-trafico` a la ubicación deseada.

### 2. Crear el entorno virtual

```cmd
python -m venv python_local
python_local\Scripts\activate
```

Deberías ver `(python_local)` en el prompt.

### 3. Instalar dependencias

```cmd
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Si `mysqlclient` falla al compilar**, usa `pymysql`:

```cmd
pip install pymysql
```

Y añade en `sistema/__init__.py`:

```python
import pymysql
pymysql.install_as_MySQLdb()
```

### 4. Crear la base de datos MySQL

Desde phpMyAdmin o línea de comandos:

```sql
CREATE DATABASE monitoreo_red CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'monitor'@'localhost' IDENTIFIED BY 'TU_PASSWORD_SEGURA';
GRANT ALL PRIVILEGES ON monitoreo_red.* TO 'monitor'@'localhost';
FLUSH PRIVILEGES;
```

### 5. Configurar el `.env`

Copia `.env.example` a `.env` y edítalo:

```cmd
copy .env.example .env
notepad .env
```

Contenido **completo** del `.env` (solo variables bootstrap):

```env
# ============================================================
# Django
# ============================================================
DJANGO_SECRET_KEY=cambia-esto-por-una-clave-larga-aleatoria
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# ============================================================
# MySQL
# ============================================================
DB_NAME=monitoreo_red
DB_USER=monitor
DB_PASSWORD=TU_PASSWORD_SEGURA
DB_HOST=127.0.0.1
DB_PORT=3306

# ============================================================
# Email backend (el resto se configura desde la UI)
# ============================================================
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
```

**Genera la `DJANGO_SECRET_KEY`**:

```cmd
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 6. Aplicar migraciones

```cmd
python manage.py migrate
```

### 7. Crear grupos de roles

```cmd
python manage.py setup_roles
```

Crea los grupos `Administrador` y `Usuario`.

### 8. Crear superusuario

```cmd
python manage.py createsuperuser
```

Guarda usuario, email y contraseña. Este será el superadministrador inicial.

### 9. Cargar modelos de equipos (opcional)

```cmd
python manage.py load_device_models
```

Registra modelos conocidos (RB4011, LiteBeam M5, ePMP 1000, etc.) con sus OIDs.

### 10. Recolectar estáticos

```cmd
python manage.py collectstatic --no-input
```

### 11. Arrancar en desarrollo

```cmd
python manage.py runserver
```

Abre `http://localhost:8000/`.

---

## ⚙️ Configuración

### Filosofía de configuración

El sistema tiene **dos niveles** de configuración:

#### Nivel 1 — `.env` (bootstrap)

Solo las variables que **no cambian** y que son necesarias antes de que
Django tenga acceso a la BD:

| Variable | Descripción |
|---|---|
| `DJANGO_SECRET_KEY` | Clave secreta |
| `DJANGO_DEBUG` | `True`/`False` |
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | MySQL |
| `EMAIL_BACKEND` | Backend de Django para enviar emails |

#### Nivel 2 — BD MySQL + UI (`system_config`, `email_config`)

Todo lo demás se configura desde `/configuracion/`:

| Sección | Campos |
|---|---|
| **InfluxDB** | URL, token, org, bucket |
| **Monitor** | enabled, 3 intervalos |
| **Telegram** | bot_token, chat_id, enabled |
| **Grafana** | URL |
| **Email** | host, port, TLS, SSL, user, password, from_email |

### `runtime_config.py` — Config lazy

Para evitar leer la BD en cada request, se usa un **loader con caché**:

- `get_system_config()` → cachea el objeto `SystemConfig`
- `get_influx_config()` → dict con URL/token/org/bucket
- `get_telegram_config()` → dict con enabled/bot_token/chat_id
- `get_monitor_config()` → dict con intervalos
- `get_email_config()` → dict con SMTP
- `apply_email_config_to_settings()` → aplica al módulo `django.conf.settings`

**Invalidación de caché**: mediante `signals.py` que escucha `post_save` en
`SystemConfig` y `EmailConfig` y llama a `runtime_config.reset_cache()`.

### Validación de Grafana (context processor)

En cada request, el context processor verifica si la URL de Grafana responde
(con caché de 5 min) e inyecta `grafana_available` en todos los templates.
Si es `False`, el botón del navbar **no se muestra**.

---

## 💾 Base de datos

### Tablas principales

#### Django Auth

| Tabla | Descripción |
|---|---|
| `auth_user` | Usuarios del sistema |
| `auth_group` | Grupos (Administrador, Usuario) |
| `auth_permission` | Permisos |
| `django_session` | Sesiones |
| `django_admin_log` | Log del admin (DEBUG) |

#### Inventario

##### `device_models`

| Campo | Tipo | Descripción |
|---|---|---|
| id | INT UNSIGNED | PK |
| vendor | VARCHAR(50) | Fabricante |
| name | VARCHAR(100) | Nombre del modelo |
| oids | JSON | OIDs específicos del modelo |
| is_wireless_link | BOOLEAN | Es radio-enlace |
| active | BOOLEAN | Modelo activo |

##### `devices`

| Campo | Tipo | Descripción |
|---|---|---|
| id | INT UNSIGNED | PK |
| name | VARCHAR(100) | Nombre |
| ip | VARCHAR(45) | IP única |
| device_type | VARCHAR(50) | router, switch, cpe, firewall |
| device_role | ENUM | core, distribution, access, cpe |
| vendor | VARCHAR(50) | Fabricante |
| device_model_id | INT UNSIGNED | FK a device_models |
| location | VARCHAR(100) | Ubicación |
| snmp_version | VARCHAR(10) | 1, 2c, 3 |
| snmp_community | VARCHAR(100) | Community |
| snmp_user, snmp_auth, snmp_priv | VARCHAR(255) | SNMPv3 |
| tcp_ports | VARCHAR(255) | Puertos TCP |
| active | BOOLEAN | Activo |

##### `interfaces`

| Campo | Tipo | Descripción |
|---|---|---|
| id | INT UNSIGNED | PK |
| device_id | INT UNSIGNED | FK a devices |
| if_index | INT UNSIGNED | SNMP ifIndex |
| if_name | VARCHAR(100) | ifName |
| if_alias | VARCHAR(100) | ifAlias |
| if_speed_bps | BIGINT | Velocidad (bps) |
| if_type | VARCHAR(50) | Tipo |
| admin_status | BOOLEAN | Admin up/down |
| oper_status | BOOLEAN | Operativo up/down |
| monitored | BOOLEAN | Monitorear tráfico |

#### Alertas

##### `alert_rules`

| Campo | Tipo | Descripción |
|---|---|---|
| id | INT UNSIGNED | PK |
| name | VARCHAR(150) | Nombre |
| description | TEXT | Descripción |
| **conditionals** | **JSON** | **Lista de condicionales (1-5)** |
| severity | VARCHAR(20) | info, warning, critical |
| custom_message | TEXT | Mensaje con placeholders |
| telegram_enabled | BOOLEAN | Notificar Telegram |
| telegram_cooldown_sec | INT | Cooldown (mín. 60s) |
| fire_once | BOOLEAN | Disparar una sola vez |
| skip_on_startup | BOOLEAN | Omitir al arrancar |
| enabled | BOOLEAN | Regla activa |
| created_at, updated_at | TIMESTAMP | Auditoría |
| created_by_id | INT | Usuario |

##### `alerts`

| Campo | Tipo | Descripción |
|---|---|---|
| id | BIGINT UNSIGNED | PK |
| device_id | INT UNSIGNED | FK a devices |
| interface_id | INT UNSIGNED | FK a interfaces |
| rule_id | INT UNSIGNED | FK a alert_rules |
| alert_type | VARCHAR(50) | Métrica o "multi_conditional" |
| severity | VARCHAR(20) | Severidad |
| message | TEXT | Mensaje final |
| value_observed | DECIMAL(20,4) | Valor medido |
| threshold_value | DECIMAL(20,4) | Umbral |
| status | VARCHAR(20) | activa, reconocida, resuelta |
| created_at | TIMESTAMP | Fecha creación |
| resolved_at | TIMESTAMP | Fecha resolución |

##### `thresholds` (legacy)

Umbrales por equipo/métrica. Mantenido por compatibilidad.

#### Core

##### `system_config` (singleton)

| Campo | Descripción |
|---|---|
| influx_url, influx_token, influx_org, influx_bucket | InfluxDB |
| grafana_url | Grafana |
| telegram_bot_token, telegram_chat_id, telegram_enabled | Telegram |
| monitor_enabled | Monitor activo |
| snmp_poll_interval, health_poll_interval, icmp_poll_interval | Intervalos |
| updated_at, updated_by_id | Auditoría |

##### `email_config` (singleton)

| Campo | Descripción |
|---|---|
| email_host, email_port | SMTP |
| email_use_tls, email_use_ssl | Seguridad |
| email_host_user, email_host_password | Credenciales |
| default_from_email | Remitente |
| updated_at, updated_by_id | Auditoría |

##### `email_verifications`

| Campo | Descripción |
|---|---|
| user_id (OneToOne) | Usuario |
| verified | Booleano |
| verified_at | Fecha |
| verified_email | Email que fue verificado |
| token | UUID |
| token_created_at | Fecha de creación |

##### `password_reset_codes`

| Campo | Descripción |
|---|---|
| user_id | Usuario |
| code | Código de 8 dígitos |
| created_at | Fecha creación |
| expires_at | Caducidad (5 min) |
| used | Booleano |

##### `password_reset_attempts`

| Campo | Descripción |
|---|---|
| user_id | Usuario |
| ip | IP del solicitante |
| successful | Booleano |
| created_at | Fecha |

#### Monitoreo

##### `monitor_status` (singleton)

| Campo | Descripción |
|---|---|
| last_heartbeat | Último latido |
| status | running / stopped |
| hostname | Hostname |
| pid | PID del proceso |
| last_traffic_run | Último tráfico |
| last_health_run | Último health |
| last_icmp_run | Último ICMP |
| last_error | Último error |

##### `discovery_jobs`

| Campo | Descripción |
|---|---|
| device_id | FK a devices |
| status | running, success, failed |
| interfaces_found, interfaces_up | Contadores |
| interfaces_created, interfaces_updated, interfaces_deleted | Contadores |
| started_at, finished_at | Fechas |
| duration_ms | Duración |
| error_message | Error si falló |
| triggered_by_id | Usuario |

### InfluxDB

**Bucket**: `metricas_red` (retención 90 días).

**Measurements**:

| Measurement | Fields | Tags |
|---|---|---|
| `traffic` | in_bps, out_bps, utilization_pct, capacity_bps, rx_octets, tx_octets | device, ip, interface, role |
| `health` | cpu_pct, mem_pct, temp_c, uptime | device, ip, role, vendor |
| `icmp` | is_alive, latency_ms, packet_loss_pct | device, ip, role |
| `tcp` | is_open | device, ip, role, port |

---

## 📊 Motor de monitoreo

### Arquitectura de servicios

Todos los pollers viven en `monitoreo/services/`:

| Servicio | Archivo | Función |
|---|---|---|
| Cliente SNMP | `snmp_client.py` | Wrapper async de pysnmp 7.x |
| OIDs de chasis | `chassis_oids.py` | Diccionario por fabricante |
| Discovery | `discovery.py` | SNMP walk + persistencia |
| Tráfico | `traffic.py` | Poller SNMP de contadores |
| Chasis | `health.py` | Poller de CPU/MEM/TEMP |
| ICMP/TCP | `icmp_tcp.py` | Ping + TCP paralelo |
| Alertas | `alerts.py` | Motor multi-condicional |
| Telegram | `telegram.py` | Notificador |
| InfluxDB writer | `influx_writer.py` | Escritura a series |
| InfluxDB reader | `influx_reader.py` | Lectura para "live" |

### Comandos de management

| Comando | Uso |
|---|---|
| `run_monitor` | Arranca el monitor en bucle (usado por el servicio) |
| `run_monitor --silent` | Modo silencioso (solo WARNING+) |
| `run_monitor --skip-discovery` | No ejecutar discovery al arrancar |
| `poll_once` | Todos los pollers una vez |
| `poll_once --only traffic` | Solo tráfico |
| `poll_snmp` | Solo tráfico SNMP |
| `poll_health` | Solo chasis |
| `poll_icmp` | Solo ICMP/TCP |
| `setup_roles` | Crear grupos de roles |
| `load_device_models` | Cargar modelos con OIDs |

### Auto-Discovery al arrancar

Al arrancar el monitor se ejecuta **automáticamente** un discovery en todos los
equipos activos (configurable con `--skip-discovery`). Esto asegura que las
interfaces estén pobladas antes del primer ciclo de polling.

---

## 🚨 Sistema de alertas multi-condicional

Ver sección completa en [Características → Sistema de alertas](#-sistema-de-alertas-multi-condicional-v20).

### Flujo de evaluación (resumen)

```
1. Poller recolecta datos → evaluate_metrics(device, {metric: value})
2. Motor busca reglas con ese device y esa métrica en algún condicional
3. Por cada regla:
   a. Carga instancias de Device (una sola query)
   b. Para cada condicional i:
      - Evalúa si el valor cumple la condición
      - Actualiza _cond_states[(rule_id, i)]
      - Marca si está "listo" (cumplió duration_sec)
   c. Combina resultados con AND/OR
   d. Si `final_ready` → disparar alerta (respetando fire_once)
   e. Si `not final_ready` → auto-resolver si estaba activa
```

### Warm-up del monitor

Los primeros **120 segundos** tras arrancar el monitor, las reglas con
`skip_on_startup=True` **no se evalúan**. Esto evita que al reiniciar el
servicio se disparen alertas de "vuelta en línea" con datos iniciales.

### Ventana de duración

Cada condicional tiene su propio `duration_sec`. Para que cuente como "listo"
debe sostenerse **sin interrupciones** durante ese tiempo. Si la condición se
rompe aunque sea un instante, el contador se resetea.

---

## 👥 Sistema de usuarios y verificación de email

Ver sección completa en [Características → Sistema de usuarios](#-sistema-de-usuarios-con-verificación-de-email).

### Flujo de creación

```
Admin/Super → /usuarios/nuevo/
  ↓
Form valida (username, email único, password, nombre)
  ↓
Se crea User + se asigna rol + se crea EmailVerification
  ↓
Se envía AUTOMÁTICAMENTE el email de verificación
  ↓
Redirige a /usuarios/ con mensaje de éxito
```

### Flujo de verificación

```
Usuario recibe email con enlace /verificar-email/<uuid>/
  ↓
Accede (endpoint público, no requiere login)
  ↓
Se valida:
  · Token existe
  · No expirado (< 48h)
  · No verificado previamente
  ↓
Se marca verified=True y verified_email=<email actual>
  ↓
Muestra pantalla de éxito
```

### Flujo de recuperación de contraseña

```
1. /password-reset/ → ingresa usuario o email
2. Sistema verifica:
   · Usuario existe y activo
   · Tiene email
   · Email está VERIFICADO
   · Sin bloqueo por intentos
3. Genera código de 8 dígitos (5 min)
4. Envía email
5. /password-reset/verify/ → ingresa código
6. Si OK → /password-reset/new-password/
7. Establece nueva contraseña → redirige a login
```

---

## ⚙️ Configuración del sistema (UI)

Ver sección completa en [Características → Configuración](#-configuración-del-sistema-ui-v20).

### Endpoints de la UI

| URL | Acción |
|---|---|
| `/configuracion/` | Ver/guardar toda la config |
| `/configuracion/test-influx/` | Probar InfluxDB (POST) |
| `/configuracion/test-telegram/` | Probar Telegram (POST) |
| `/configuracion/test-grafana/` | Probar Grafana (POST) |
| `/configuracion/test-email/` | Probar email (POST, con modal) |

---

## 🖥️ Interfaz web y navegación

### URLs principales

| URL | Descripción | Permiso |
|---|---|---|
| `/` | Dashboard | Autenticado |
| `/accounts/login/` | Login | Público |
| `/accounts/logout/` | Logout | Autenticado |
| `/setup/` | Setup inicial (solo si no hay superadmin) | Público |
| `/perfil/` | Mi perfil | Autenticado |
| `/password-reset/` | Solicitar código | Público |
| `/password-reset/verify/` | Verificar código | Público |
| `/password-reset/new-password/` | Nueva contraseña | Público (sesión) |
| `/verificar-email/<uuid>/` | Verificar email | Público |
| `/equipos/` | Lista equipos | Autenticado |
| `/equipos/nuevo/` | Nuevo equipo | Admin |
| `/equipos/<id>/` | Detalle | Autenticado |
| `/equipos/<id>/editar/` | Editar | Admin |
| `/equipos/<id>/interfaces/` | Gestionar interfaces | Autenticado (edit: Admin) |
| `/equipos/api/models/?vendor=X` | API JSON de modelos | Autenticado |
| `/alertas/` | Lista alertas paginada | Autenticado |
| `/alertas/export/excel/` | Exportar Excel | Autenticado |
| `/alertas/export/pdf/` | Exportar PDF | Autenticado |
| `/alertas/reglas/` | Lista reglas paginada | Autenticado |
| `/alertas/reglas/nueva/` | Nueva regla multi-condicional | Admin |
| `/alertas/reglas/<id>/editar/` | Editar regla | Admin |
| `/alertas/reglas/<id>/toggle/` | Activar/desactivar | Admin |
| `/alertas/reglas/<id>/duplicar/` | Duplicar regla | Admin |
| `/alertas/reglas/bulk/` | Acciones en bloque | Admin |
| `/monitoreo/status/` | Estado del servicio | Autenticado |
| `/monitoreo/live/` | Monitoreo en vivo | Autenticado |
| `/monitoreo/api/devices-live/` | API JSON de métricas | Autenticado |
| `/monitoreo/device/<id>/discover/` | Discovery manual | Admin |
| `/monitoreo/device/<id>/history/` | Historial discovery | Autenticado |
| `/usuarios/` | Lista usuarios | Admin |
| `/usuarios/nuevo/` | Nuevo usuario | Admin |
| `/usuarios/<id>/editar/` | Editar usuario | Admin (o propio) |
| `/usuarios/<id>/password/` | Cambiar contraseña | Admin (o propio) |
| `/usuarios/<id>/eliminar/` | Eliminar usuario | Admin |
| `/usuarios/<id>/enviar-verificacion/` | Reenviar verificación | Admin |
| `/configuracion/` | Configuración del sistema | Superadmin |

### Navbar

Ver [Interfaz web → Navbar](#-interfaz-web).

---

## 🔌 Integraciones externas

### InfluxDB 2.9

- **Data source** de todas las métricas.
- **Cliente**: `influxdb-client` (oficial).
- **Timeout**: 5 segundos.
- **Modo**: escritura síncrona con `write_api`.
- **Reset automático**: si la config cambia, el cliente se recrea.

### Grafana OSS

- **Data Source**: InfluxDB con query language Flux.
- **Dashboards**: `docs/grafana-dashboard.json`.
- **URL**: configurable desde la UI.
- **Validación**: context processor verifica cada 5 min si responde.

### Telegram Bot

- **Bot creado con @BotFather**.
- **Config en BD**: token, chat_id, enabled.
- **Mensajes**: HTML con parse_mode.
- **Cooldown**: por regla (mín. 60s).
- **Formato**:
  ```
  🔴 CRITICAL

  <mensaje personalizado o automático>

  Equipo: <nombre> (<ip>)     ← solo si automático
  Regla: <nombre>             ← solo si automático
  ```

### SMTP (Email)

- **Gmail**: requiere contraseña de aplicación.
- **Office365**: requiere SMTP AUTH habilitado.
- **Fallback**: si `.env` no define backend, usa `console` (imprime a stdout).
- **Uso**:
  - Verificación de email (48h)
  - Recuperación de contraseña (código de 8 dígitos, 5 min)

---

## 📤 Exportación de datos

### Excel

- **Librería**: `openpyxl`
- **Formato**: `.xlsx` con estilos
- **Elementos**:
  - Título con fondo azul
  - Fila de filtros + total
  - Fila con ordenamiento actual
  - Colores por severidad y estado
  - Panel congelado
- **Endpoint**: `/alertas/export/excel/`

### PDF

- **Librería**: `reportlab`
- **Formato**: A4 landscape
- **Elementos**:
  - Título + filtros + orden
  - Encabezados repetidos
  - Colores por severidad
- **Endpoint**: `/alertas/export/pdf/`

---

## 👥 Roles y permisos

### Roles del sistema

| Rol | is_superuser | is_staff | Grupo |
|---|---|---|---|
| **Superadministrador** | ✅ | ✅ | (ninguno) |
| **Administrador** | ❌ | ✅ | `Administrador` |
| **Usuario** | ❌ | ❌ | `Usuario` |

### Matriz completa

| Acción | Superadmin | Admin | Usuario |
|---|---|---|---|
| Ver dashboard | ✅ | ✅ | ✅ |
| Ver equipos | ✅ | ✅ | ✅ |
| Crear/editar/eliminar equipo | ✅ | ✅ | ❌ |
| Ver/gestionar interfaces | ✅ | ✅ | Solo lectura |
| Ver alertas | ✅ | ✅ | ✅ |
| Reconocer/resolver/eliminar alerta | ✅ | ✅ | ❌ |
| Ver reglas | ✅ | ✅ | ✅ |
| Crear/editar/eliminar regla | ✅ | ✅ | ❌ |
| Ver usuarios | ✅ | ✅ (solo normales) | ❌ |
| Crear admin | ✅ | ❌ | ❌ |
| Crear usuario normal | ✅ | ✅ | ❌ |
| Editar propio perfil | ✅ | ✅ | ✅ |
| Cambiar propia contraseña | ✅ | ✅ | ✅ |
| Cambiar email de otros | ✅ | ❌ | ❌ |
| Configuración del sistema | ✅ | ❌ | ❌ |

### Protecciones especiales

1. Nadie puede cambiar su propio rol.
2. Los admins no ven a otros admins ni superadmins.
3. No se puede eliminar al último superadmin activo.
4. No se puede eliminar al propio usuario.
5. No se puede eliminar al usuario `admin`.

---

## 🚀 Despliegue en producción

### Como servicios de Windows (recomendado)

**Requisito previo**: `nssm.exe` en `C:\Windows\System32\`.

```cmd
cd scripts
install_services.bat
```

El script:

1. Verifica permisos de administrador
2. Detecta `PROJECT_ROOT` (padre de `scripts/`)
3. Detecta el venv (`python_local`, `venv_django`, `venv`, `.venv`, `env`)
4. Crea `logs/` si no existe
5. Instala `ComfutechDjango` (Waitress en `0.0.0.0:8000`)
6. Instala `ComfutechMonitor` (APScheduler en proceso separado)
7. Configura reinicio automático (delay 5-10s)
8. Arranca ambos servicios

### Verificar

```cmd
nssm status ComfutechDjango   # → SERVICE_RUNNING
nssm status ComfutechMonitor  # → SERVICE_RUNNING
```

### Desinstalar

```cmd
uninstall_services.bat
```

### Reiniciar tras cambios

```cmd
restart_services.bat
```

### Deploy completo (migraciones + estáticos + restart)

```cmd
deploy.bat
```

### Configuración de producción

En `.env`:

```env
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,10.253.215.X
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
```

### Recolectar estáticos

```cmd
python manage.py collectstatic --no-input
```

WhiteNoise los sirve automáticamente.

---

## 🔧 Operación y mantenimiento

### Comandos de Django

```cmd
python manage.py runserver            # Desarrollo
python manage.py migrate              # Aplicar migraciones
python manage.py makemigrations       # Generar migraciones
python manage.py collectstatic        # Recolectar estáticos
python manage.py createsuperuser      # Crear superusuario
python manage.py shell                # Shell con ORM
```

### Comandos del monitor

```cmd
python manage.py run_monitor                 # Bucle continuo
python manage.py run_monitor --silent        # Modo silencioso
python manage.py run_monitor --skip-discovery # Sin discovery al arrancar
python manage.py poll_once                   # Todos los pollers 1 vez
python manage.py poll_once --only traffic    # Solo tráfico
python manage.py poll_snmp                   # Solo SNMP
python manage.py poll_health                 # Solo chasis
python manage.py poll_icmp                   # Solo ICMP/TCP
python manage.py setup_roles                 # Crear grupos
python manage.py load_device_models          # Cargar modelos
```

### Backups

**MySQL:**

```cmd
mysqldump -u monitor -p monitoreo_red > backup_%date%.sql
```

**InfluxDB:**

```cmd
influx backup C:\backups\influx
```

**Recomendación**: programar backups diarios a las 3 AM con el Programador de Tareas.

### Rotación de logs

Los logs usan `RotatingFileHandler` con:

- 5 MB por archivo
- 3 archivos de respaldo
- Encoding UTF-8

Ubicación: `logs/`.

### Monitoreo del sistema

- **Estado del monitor**: `/monitoreo/status/`
- **Monitoreo en vivo**: `/monitoreo/live/`
- **Logs**: `logs/`
- **Servicios**: `services.msc`

---

## 🐛 Solución de problemas

### El monitor no arranca

1. Verificar el servicio: `nssm status ComfutechMonitor`
2. Revisar `logs/monitor_err.log`
3. Verificar config de InfluxDB en `/configuracion/`
4. Confirmar que InfluxDB esté corriendo

### No llegan notificaciones de Telegram

1. Verificar en `/configuracion/`:
   - `telegram_enabled` activo
   - Token y chat_id completos
2. Enviar mensaje de prueba desde el panel
3. Confirmar que el bot esté agregado al grupo
4. Chat_id debe empezar con `-` para grupos

### Las alertas no se disparan

1. Verificar que la regla esté `enabled=True`
2. Verificar que el **device del condicional** esté asignado
3. Verificar el `duration_sec` (eventos puntuales no disparan)
4. Verificar que el umbral sea alcanzable
5. Revisar `last_fired_at` de la regla
6. Verificar que no esté en warm-up (primeros 120s tras arrancar)

### El tráfico muestra 0 bps

1. Es normal en el primer ciclo (no hay contadores previos)
2. Verificar que la interfaz esté `monitored=True` y `oper_status=True`
3. Verificar la `community` SNMP
4. Confirmar con `snmpget` desde CMD

### InfluxDB timeout

1. Verificar: `curl http://localhost:8086/health`
2. Reducir la retención del bucket si el volumen es alto
3. Verificar que el token tenga permisos Read & Write

### `chat not found` en Telegram

1. Enviar un mensaje al grupo desde un usuario
2. Obtener el chat_id con `getUpdates`
3. Verificar que empiece con `-100` para supergrupos
4. Actualizar en `/configuracion/`

### El email de verificación no llega

1. Verificar config SMTP en `/configuracion/`
2. Probar con "Enviar email de prueba"
3. Si usas Gmail, verificar la contraseña de aplicación
4. Revisar logs de Django (`logs/django.log`)
5. Verificar que el email del destinatario exista

### `UnboundLocalError` en health.py

**Causa**: variable `vendor` no definida antes de usar.

**Fix aplicado en v1.0**: la función `_resolve_oids()` siempre devuelve
`(oids_map, vendor)`.

### `NameError: settings` en pollers

**Causa**: referencia residual a `django.conf.settings` en servicios.

**Fix aplicado en v1.0**: todos los servicios usan `core.runtime_config`.

### Error al cambiar el tema

**Causa**: conflicto entre `localStorage` y `data-bs-theme`.

**Fix aplicado en v1.0**: script inline en `<head>` que aplica el tema antes
de renderizar.

### `TypeError: require_admin_or_super() takes 0 positional arguments`

**Causa**: decorador sin paréntesis.

**Fix**: usar `@require_admin_or_super()` con paréntesis.

### `TypeError: 'NoneType' object is not callable` al cerrar

**Causa**: cliente de InfluxDB intenta hacer signout durante el `__del__`
cuando el intérprete está cerrando.

**Fix aplicado en v1.0**: `atexit.register(close)` en `influx_writer.py`.

---

## 📚 Glosario

| Término | Significado |
|---|---|
| **SNMP** | Simple Network Management Protocol |
| **OID** | Object Identifier (identificador de objeto SNMP) |
| **MIB** | Management Information Base |
| **ICMP** | Internet Control Message Protocol (ping) |
| **NMS** | Network Management System |
| **ISP** | Internet Service Provider |
| **WISP** | Wireless ISP |
| **QoS** | Quality of Service |
| **SLA** | Service Level Agreement |
| **MTTR** | Mean Time To Repair |
| **bps** | Bits por segundo |
| **SNMP walk** | Recorrer un subárbol SNMP |
| **SNMP get** | Consultar un OID específico |
| **ifIndex** | Índice SNMP de una interfaz |
| **Community** | Contraseña SNMPv1/v2c |
| **Counter wrap** | Desbordamiento de contador |
| **APScheduler** | Advanced Python Scheduler |
| **WSGI** | Web Server Gateway Interface |
| **ORM** | Object-Relational Mapping |
| **FK** | Foreign Key |
| **JSON** | JavaScript Object Notation |
| **UUID** | Universally Unique Identifier |
| **CSRF** | Cross-Site Request Forgery |
| **TLS/SSL** | Protocolos de cifrado para email |
| **SMTP** | Simple Mail Transfer Protocol |
| **NSSM** | Non-Sucking Service Manager |

---

## 📝 Changelog

### v2.0 — Octubre 2026

**Configuración del sistema:**
- Rediseño completo: un solo formulario, un solo botón "Guardar"
- Secciones separadas por líneas dentro de una card
- Botones de test en cada sección (leen del POST, no requieren guardar antes)
- Modal de email copia todos los campos actuales
- Warning al salir sin guardar
- Guías contextuales colapsables (Gmail, Telegram, Grafana)

**Sistema de alertas multi-condicional:**
- `AlertRule.conditionals` como lista JSON (1-5 condicionales)
- Combinación lógica AND/OR entre condicionales
- Placeholders numerados: `{device1}`, `{metric2}`, `{value3}`, etc.
- Fix del bug `{device}` que mostraba IP entre paréntesis
- Paginación de 10 reglas por página

**Modelos de equipos:**
- Nueva entidad `DeviceModel` con `vendor`, `name`, `oids`
- Flag `is_wireless_link` para radio-enlaces
- Selector dinámico vendor → modelo (AJAX)
- Modelo mostrado en tarjetas de equipo

**Interfaz:**
- Navbar lateral sticky colapsable con persistencia
- Dropdowns para Equipos, Reglas y Monitor
- Theme switcher (Claro/Oscuro/Automático)
- Botón Grafana solo si la URL responde
- Separación de `monitor_status` y `monitor_live`

### v1.0 — Septiembre 2026

**Sistema base:**
- Django + Waitress + APScheduler
- Modelos: Device, Interface, AlertRule, Alert, SystemConfig
- Pollers SNMP/ICMP/Core Health
- Cliente InfluxDB con timeouts agresivos
- Notificaciones Telegram
- Roles y permisos

**Usuarios:**
- Auto-envío de email de verificación
- Solo superadmin cambia emails
- Indicador visual de verificación
- Recuperación de contraseña por código
- Password 8-16 caracteres con validación de fuerza

**Configuración en BD:**
- `SystemConfig` con todos los parámetros
- `runtime_config.py` para carga lazy
- Signals para invalidar caché
- Panel de configuración UI

### v0.1-v0.9 — Agosto-Septiembre 2026

Iteraciones incrementales de construcción del sistema (ver sección de historia).

---

## 📄 Licencia

Uso interno de **Comfutech**. Todos los derechos reservados.

---

## 👥 Autores

- **Giscard** — Desarrollo del sistema
- **Comfutech** — Operación y requisitos

**Ubicación**: Güigüe, Estado Carabobo, Venezuela

---

## 🔗 Enlaces de interés

- [Django Documentation](https://docs.djangoproject.com/)
- [pysnmp Documentation](https://pysnmp.readthedocs.io/)
- [InfluxDB 2.x](https://docs.influxdata.com/influxdb/v2/)
- [Grafana](https://grafana.com/docs/)
- [APScheduler](https://apscheduler.readthedocs.io/)
- [NSSM](https://nssm.cc/usage)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Bootstrap 5.3](https://getbootstrap.com/docs/5.3/)

---

**Última actualización:** Octubre 2026  
**Versión del sistema:** 2.0  
**Estado:** Desarrollo activo

---

## 📋 Resumen de lo que cubre este README

| Sección | Contenido |
|---|---|
| **Descripción general** | Problema, alcance, beneficios |
| **Historia del proyecto** | Fase C++ (descartada) + 10 iteraciones Django |
| **Arquitectura** | Diagrama ASCII + tabla de componentes |
| **Stack tecnológico** | Backend, frontend, BD, deploy |
| **Características** | Inventario, discovery, polling, alertas multi-condicional, usuarios, config UI, navbar, export |
| **Estructura del proyecto** | Árbol de directorios completo |
| **Requisitos** | Software + cuentas externas |
| **Instalación** | 11 pasos desde cero |
| **Configuración** | Filosofía de dos niveles + runtime_config |
| **Base de datos** | Las 15+ tablas + InfluxDB |
| **Motor de monitoreo** | Servicios, comandos, auto-discovery |
| **Alertas multi-condicional** | JSON, máquina de estados, placeholders, ejemplos |
| **Usuarios** | Creación, verificación, recuperación |
| **Config UI v2.0** | 5 secciones + tests |
| **Interfaz web** | Sidebar, dropdowns, theme switcher, Grafana condicional |
| **Integraciones** | InfluxDB, Grafana, Telegram, SMTP |
| **Exports** | Excel + PDF |
| **Roles y permisos** | Matriz completa + protecciones |
| **Despliegue** | NSSM + scripts |
| **Operación** | Comandos, backups, logs |
| **Solución de problemas** | 12 problemas comunes con soluciones |
| **Glosario** | 30+ términos técnicos |
| **Changelog** | v0.1 → v2.0 |

---