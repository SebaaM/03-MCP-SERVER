# 03 — Integración con Django

## Propósito

Agregar MCP como adaptador sobre la aplicación de actividades ya existente. La lógica del dominio debe seguir viviendo en el service layer: MCP y REST son interfaces distintas sobre las mismas reglas.

## Requisitos

- La etapa 02 completada.
- Python y `uv` instalados.

El proyecto Django de actividades **ya viene implementado** en esta carpeta
(`config/`, `manage.py`, `activities/` con modelos, service layer, views y
seed de ejemplo). No hay que modificarlo: es el dominio existente sobre el
que se monta el adaptador MCP. El trabajo de esta etapa está únicamente en
`mcp_server/`.

## Estructura sugerida

```text
03-integracion-con-django/
├── server.py          # lanzador stdio: mcp.run()
├── config/            # settings y urls del proyecto Django (dado)
├── manage.py          # gestión Django: migrate, seed_activities, shell
├── activities/        # app Django: models, services, views (dado)
└── mcp_server/        # adaptador MCP: TRABAJO DEL ALUMNO
    ├── server.py          # configura Django y registra las capacidades
    ├── tools.py           # search_activities, request_confirmation, register_for_activity
    ├── resources.py       # activities://available y activities://{activity_id}
    ├── prompts.py         # guia_inscripcion
    ├── confirmations.py   # tokens de confirmación del host + auditoría
    └── audit.log          # auditoría JSONL (se regenera sola)
```

La estructura exacta puede variar. El criterio importante es que el servidor MCP delegue en servicios existentes y no copie queries o reglas de negocio.

## Backend Django (dado, no modificar)

El dominio ya funciona. Para prepararlo:

```sh
uv sync
uv run python manage.py migrate
uv run python manage.py seed_activities
```

Correr el server:

```sh
uv run python manage.py runserver
```

La API REST (`/api/activities/`, detalle, `search/` y `register/`) usa el
mismo `ActivityService` que debe usar el adaptador MCP.

## Endpoints REST disponibles (backend dado, no modificar)

Base: `http://127.0.0.1:8000/api/` (con `uv run python manage.py runserver`).
Montadas en `config/urls.py` → `activities/urls.py`, implementadas en
`activities/views.py` sobre `ActivityService` (`activities/services.py`).
Serialización en `activities/serializers.py`.

Objeto `activity`:

```json
{
  "id": "1",
  "title": "Taller de robótica",
  "description": "Introducción a Arduino.",
  "available": true,
  "seats": 12,
  "capacity": 20
}
```

| Método | Ruta | Descripción |
| ------ | ---- | ----------- |
| `GET` | `/api/activities/` | Catálogo de actividades disponibles (con cupo y activas). |
| `GET` | `/api/activities/<activity_id>/` | Detalle de una actividad por ID. |
| `GET` | `/api/activities/search/?query=...[&only_available=false]` | Búsqueda por título, con filtro opcional de disponibilidad. |
| `POST` | `/api/activities/<activity_id>/register/` | Inscribe un estudiante en una actividad. |

### `GET /api/activities/` — catálogo

Sin parámetros. Responde `200` con un array (vacío si no hay disponibles).

```sh
curl http://127.0.0.1:8000/api/activities/
```

```json
[{"id": "1", "title": "Taller de robótica", "description": "...", "available": true, "seats": 12, "capacity": 20}]
```

Fuente: `ActivityService.list_available()`.

### `GET /api/activities/<activity_id>/` — detalle

Ejemplo: `GET /api/activities/1/`.

- `200`: objeto `activity`.
- `404`: `{"error": "activity_not_found", "activity_id": "<id>"}` (ID inexistente o no numérico).

```sh
curl http://127.0.0.1:8000/api/activities/1/
```

Fuente: `ActivityService.get_activity(activity_id)`; lanza `ActivityNotFound`.

### `GET /api/activities/search/?query=...` — búsqueda

Query params:

- `query` (opcional, default `""`): subcadena de título, case-insensitive. Vacío = todo el catálogo.
- `only_available` (opcional, default `"true"`): sólo `false` (exacto, case-insensitive) desactiva el filtro; cualquier otro valor filtra por disponibles.

Responde `200` con un array.

```sh
curl "http://127.0.0.1:8000/api/activities/search/?query=robotica"
curl "http://127.0.0.1:8000/api/activities/search/?query=&only_available=false"
```

Fuente: `ActivityService.search(query, only_available)`.

### `POST /api/activities/<activity_id>/register/` — inscripción

Body JSON: `{"student_email": "alumno@untdf.edu.ar"}`. El email se normaliza (trim + minúsculas) y se valida.

```sh
curl -X POST http://127.0.0.1:8000/api/activities/1/register/ \
  -H "Content-Type: application/json" \
  -d '{"student_email": "alumno@untdf.edu.ar"}'
```

Respuestas:

- `201`: `{"status": "registered", "activity_id": "1", "student_email": "alumno@untdf.edu.ar"}`
- `400` `{"error": "invalid_json"}`: body no es JSON válido.
- `400` `{"error": "invalid_email", "message": "..."}`: email inválido.
- `404` `{"error": "activity_not_found", "activity_id": "<id>"}`: actividad inexistente.
- `409` `{"error": "activity_full", "message": "..."}`: sin cupos.
- `409` `{"error": "already_registered", "message": "..."}`: email ya inscripto en esa actividad.

Fuente: `ActivityService.register(activity_id, student_email)`; usa transacción + `select_for_update`, restricción única `(activity, student_email)`.

## Actividad

El esqueleto incluye `server.py`, `mcp_server/` y el backend Django ya
conectable vía `ActivityService`. Prepará sus dependencias con `uv sync`,
prepará la base con `uv run python manage.py migrate` y
`uv run python manage.py seed_activities`, y abrí Inspector desde esta
carpeta:

```sh
uv run mcp dev server.py
```

El catálogo y la búsqueda responden vacíos hasta conectar el service layer. La
inscripción responde `not_implemented` a propósito. El prompt devuelve un
marcador `TODO(alumno)` hasta implementarlo. Implementá las capacidades
en este orden (sólo en `mcp_server/`, sin tocar `activities/` ni `config/`):

1. Resource `activities://available` para el catálogo de actividades disponibles.
2. Resource template `activities://{activity_id}` para el detalle de una actividad.
3. Tool `search_activities(query, only_available=True)` para una búsqueda por criterios variables.
4. Tool `register_for_activity(activity_id, student_email)` para la acción de inscripción.
5. Prompt `guia_inscripcion(query="", student_email="")` para el flujo guiado completo: explorar catálogo → buscar → ver detalle → pedir confirmación y email → inscribir. El prompt no inscribe por sí mismo: devuelve mensajes que orquestan los resources y tools anteriores.

Probá cada capacidad con MCP Inspector antes de pasar a la siguiente. Al
integrarlo con el proyecto real, configurá Django antes de importar modelos u
objetos que dependan del ORM.

## Implementado (puntos desarrollados)

Todo el trabajo está en `mcp_server/`; `activities/` y `config/` quedaron
intactos. El server se llama `Actividades UNTDF` y se lanza con
`uv run python server.py`. Todas las capacidades delegan en `ActivityService`
(`get_activity_service()`); el adaptador no copia queries ni reglas.

| Capacidad          | Tipo             | Nombre / URI                                                |
| ------------------ | ---------------- | ------------------------------------------------------------ |
| Catálogo           | Resource         | `activities://available` (título, ID y cupos libres)          |
| Detalle            | Resource template| `activities://{activity_id}` (Markdown: título, estado, cupos, descripción) |
| Búsqueda           | Tool             | `search_activities(query="", only_available=True)`           |
| Confirmación       | Tool             | `request_confirmation(activity_id, student_email)`           |
| Inscripción        | Tool             | `register_for_activity(activity_id, student_email, confirmation="")` |
| Flujo guiado       | Prompt           | `guia_inscripcion(query="", student_email="")`               |

Punto por punto del enunciado:

1. **Resource `activities://available`** — lista las actividades con cupo usando
   `ActivityService.list_available()`. Si no hay nada, responde un Markdown
   informativo ("No hay actividades cargadas todavía").
2. **Resource template `activities://{activity_id}`** — valida que el `activity_id`
   sea numérico antes de tocar el dominio; si la actividad no existe (o el ID no
   es numérico) devuelve `activity_not_found: ...` en el texto del resource.
3. **Tool `search_activities(query="", only_available=True)`** — filtra por
   título (case-insensitive) y disponibilidad. La query se recorta y se limita a
   100 caracteres (`MAX_QUERY_LENGTH`). Devuelve una lista con
   `{id, title, available, seats}`. Nota: con SQLite el `icontains` del service
   es sensible a tildes, así que `robótica` encuentra y `robotica` no (mismo
   comportamiento que la API REST).
4. **Tool `register_for_activity(activity_id, student_email, confirmation="")`** —
   la acción de inscripción. **No acepta un booleano que el modelo pueda
   inventar**: exige el token emitido por el host (ver `confirmations.py`).
5. **Prompt `guia_inscripcion(query="", student_email="")`** — devuelve los
   mensajes (assistant + user) que orquestan el flujo completo en 6 pasos:
   explorar catálogo → buscar por tema → ver detalle → pedir confirmación y
   email → `request_confirmation` → `register_for_activity`. No inscribe por sí
   mismo ni toca el service layer.

### Validación de entradas

- `activity_id` → obligatorio y numérico (`invalid_activity_id`).
- `student_email` → trim + minúsculas + `validate_email` del core de Django
  (`invalid_email`).
- `confirmation` → `is_host_confirmation_valid`: el token debe ser un string
  no vacío, existir en el issuer, no estar consumido, no haber vencido y
  pertenecer al par (actividad, email) pedido. Los booleanos y los tokens
  inventados se rechazan (`confirmation_required`).

### Errores accionables (siempre un dict con `status` y, en general, `message`)

| status                | Cuándo                                                     |
| --------------------- | ---------------------------------------------------------- |
| `confirmation_issued` | `request_confirmation` OK: incluye `confirmation` (token), `ttl_seconds` (600) |
| `confirmation_required`| `register_for_activity` sin token válido (falta, inventado, vencido, reusado o de otro par) |
| `invalid_activity_id` | ID vacío o no numérico                                     |
| `invalid_email`       | Email vacío o mal formado                                  |
| `activity_not_found`  | La actividad no existe o está archivada                    |
| `activity_full`       | La actividad no tiene cupos                                |
| `already_registered`  | El email ya está inscripto (constraint único de Django)    |
| `registered`          | Inscripción concretada                                     |

### Confirmación del host y auditoría (`mcp_server/confirmations.py`)

- `request_confirmation` emite un **token opaco de un solo uso**
  (`uuid4().hex`, 32 caracteres, TTL 600 s). Es el host (interfaz) quien debe
  mostrarlo y pedir la confirmación explícita del estudiante antes de inscribir.
- `register_for_activity` consume el token al inscribirse: el mismo token no
  puede usarse dos veces.
- Toda operación sensible queda en **auditoría JSONL** (`mcp_server/audit.log`):
  timestamp ISO UTC, acción, activity_id, student_email, resultado y hash
  SHA-256 del token (**nunca el token crudo**). El archivo se regenera solo y
  si no puede escribir no rompe la inscripción.

## Probar el proyecto

### Preparar los datos

```sh
uv sync
uv run python manage.py migrate
uv run python manage.py seed_activities
```

`seed_activities` es idempotente por título (no resetea `seats_taken`). El seed
deja este baseline:

| ID | Actividad                     | Cupos libres | Nota                              |
| -- | ----------------------------- | ------------ | --------------------------------- |
| 1  | Taller de robótica            | 15 de 20     | sirve para inscribirse            |
| 2  | Club de lectura               | 15 de 15     |                                   |
| 3  | Fútbol 5                      | 0 de 10      | **llena** → probar `activity_full`|
| 4  | Coro universitario            | 18 de 30     |                                   |
| 5  | Fotografía nocturna (archivada)| 9 de 12     | inactiva → no inscribible         |

Para volver al baseline entre pruebas (borra las filas `e2e.*` del E2E y
reacomoda cupos):

```sh
uv run python manage.py shell -c "from activities.models import Activity, Registration; Registration.objects.filter(student_email__regex=r'^e2e\.').delete(); [Activity.objects.filter(title=t).update(seats_taken=s) for t, s in {'Taller de robótica': 5, 'Club de lectura': 0, 'Fútbol 5': 10, 'Coro universitario': 12, 'Fotografía nocturna (archivada)': 3}.items()]"
```

### MCP Inspector

Desde la carpeta del proyecto (vida útil = mientras la terminal siga abierta):

```sh
uv run mcp dev server.py
```

Imprime la URL con un token de autenticación, por ejemplo
`http://127.0.0.1:6274?MCP_INSPECTOR_API_TOKEN=...`. Cargala en el navegador.
En la vista del servidor se ven las pestañas:

- **Resources**: leer `activities://available`, o reemplazar el ID en
  `activities://1`; probá también un ID inexistente (`activities://999`) y uno
  no numérico (`activities://abc`) para ver el manejo de `activity_not_found`.
- **Tools**: editar el payload JSON y ejecutar. Flujo completo:
  1. `search_activities` con `{"query": "Cor", "only_available": true}`.
  2. `request_confirmation` con `{"activity_id": "1", "student_email": "estudiante@untdf.edu.ar"}` → copiá el `confirmation`.
  3. `register_for_activity` con `{"activity_id": "1", "student_email": "estudiante@untdf.edu.ar", "confirmation": "<token>"}` → `registered`. Si re-ejecutás con el mismo token: `confirmation_required`.
- **Prompts**: invocar `guia_inscripcion` con `query` y `student_email`
  opcionales y ver los mensajes que devuelve.

### Test de extremo a extremo (stdio, sin GUI)

El repo incluye `test_e2e.py`, un cliente stdio del SDK MCP que ejercita todo
el server sin GUI. Con la DB en baseline:

```sh
uv run python test_e2e.py
```

Cubre 16 casos (0 fallas con la DB en baseline):

- Resources: catálogo, detalle, ID inexistente e ID no numérico.
- Búsqueda: `search_activities` devuelve resultados.
- Confirmación: `request_confirmation` emite un token de 32 caracteres.
- Inscripción: registro OK, token de un solo uso, sin token, token inventado.
- Errores: email inválido, ID de actividad inválido, actividad inexistente,
  doble inscripción y cupo agotado.

El E2E deja filas `e2e.*` en la DB: volvé al baseline con el comando de la
sección anterior antes de re-ejecutarlo.

## Conectar el MCP a opencode

En la **raíz del repo** (donde vive el `.git`) crear o ajustar `opencode.json`
con un server MCP local por stdio:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "actividades-untdf": {
      "type": "local",
      "command": ["uv", "run", "python", "server.py"],
      "cwd": "C:/ruta/absoluta/a/03-integracion-con-django",
      "enabled": true
    }
  }
}
```

- `type: "local"`: proceso local que habla por stdio. `command` arranca el
  server con el venv que maneja `uv`; `cwd` (absoluto) hace que Django resuelva
  el settings aunque abras opencode desde otra carpeta.
- opencode carga la config **al iniciar** y no en caliente: hay que cerrar y
  reabrir opencode después de crear/editar el archivo.
- Para ver el estado de los servers y sus tools: comando `/mcp`.
- `uv` debe estar en el PATH de la terminal desde la que lanzas opencode
  (`where uv` para verificarlo; el valor mostrado en esta carpeta es
  `C:\Users\pity_\.local\bin\uv.exe`).

## Criterios de diseño

- Catálogo y detalle son contexto legible: corresponden a resources.
- La búsqueda depende de criterios que el modelo puede decidir: corresponde a una tool.
- La inscripción cambia el estado: es una tool con efectos secundarios y requiere una autorización explícita.
- El flujo guiado es reutilizable y orquesta las capacidades anteriores sin lógica de negocio propia: corresponde a un prompt (no llama al service layer, devuelve mensajes que indican qué resource leer y qué tool ejecutar en cada paso).
- Las respuestas deben tener datos útiles para que el host pueda continuar el flujo.

## Punto de control

- El catálogo se lee mediante su URI.
- El template devuelve el detalle correcto y maneja un identificador inexistente.
- La búsqueda no expone SQL, ORM ni views como parte de su contrato.
- Una inscripción usa el mismo servicio de dominio que usaría una vista REST.
- El prompt `guia_inscripcion` se lista en Inspector, acepta `query` y `student_email` (ambos opcionales), nombra los resources/tools en orden y pide confirmación antes de inscribir.

## Entrega mínima

Un servidor MCP conectado a Django con las cinco capacidades (dos resources, dos tools, un prompt), una explicación de por qué cada una es resource, tool o prompt, y una demostración en Inspector de al menos catálogo, búsqueda, inscripción y el prompt guiado.
