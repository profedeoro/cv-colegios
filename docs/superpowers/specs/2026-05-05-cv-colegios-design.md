# Diseño — Herramienta de envío personalizado de hoja de vida a colegios privados

**Autor:** Daniel Eduardo Villalba de Oro
**Fecha:** 2026-05-05
**Estado:** Aprobado en brainstorming. Pendiente de plan de implementación.
**Repositorio destino:** `C:/Users/elrug/cv-colegios/`

---

## 1. Resumen ejecutivo

Construir una herramienta local en Python que, cada mañana, descubre colegios privados de Bogotá, Antioquia (todo el departamento) y Barranquilla, clasifica su perfil pedagógico, genera una hoja de vida y carta de presentación personalizadas para cada uno, y deja borradores en Gmail listos para que Daniel los revise y envíe con un click. La herramienta también detecta respuestas automáticamente y agenda correos de seguimiento.

**Volumen objetivo:** alcanzar ~1.500 colegios potenciales a un ritmo de 15 colegios/día durante ~3–5 meses.

**Diferenciadores del usuario** (input para la personalización):
- Maestría en Innovación Educativa Virtual en curso
- Libro publicado con ISBN sobre TICs en educación física
- 2 artículos en revistas indexadas
- Experiencia con tutores virtuales LLM
- Experiencia en natación inclusiva (autismo, discapacidad)

---

## 2. Decisiones tomadas en brainstorming

| # | Decisión | Valor |
|---|---|---|
| 1 | Rol/perfil del usuario | Docente E.F. + investigador en innovación educativa |
| 2 | Nivel de automatización | Semi-automático: la herramienta crea borradores en Gmail; Daniel envía con un click |
| 3 | "Interés del colegio" | Perfil pedagógico (bilingüe, IB, religioso, deportivo, TIC, etc.) |
| 4 | Fuente de la lista de colegios | MEN + scraping de asociaciones (UNCOLI/CONACED/ASCOLPEM) + Google Custom Search |
| 5 | Qué se envía | HV personalizada + carta de presentación personalizada + link a portafolio |
| 6 | Profundidad de personalización | Media: reescribe Perfil + reordena experiencias + reescribe bullets, sin inventar nada |
| 7 | Ritmo de envío | 15 colegios/día, constante |
| 8 | Tracking | Panel de estado en SQLite + recordatorios de seguimiento a los 7-10 días |
| 9 | Portafolio | Página pública en Notion (contenido generado por la herramienta, Daniel lo pega y publica) |
| 10 | Dónde corre | Laptop Windows + Programador de tareas (sin nube) |
| 11 | Notificaciones | Notificación de Windows + correo a Daniel + WhatsApp vía CallMeBot |
| 12 | Alertas de respuesta | Inmediatas (módulo `revisar_respuestas` corre cada 30 min entre 8am–10pm) |
| 13 | Diseño y typos del CV | Pulir diseño + corregir typos en una corrida inicial supervisada |
| 14 | Idioma | Todo en español |
| 15 | Selección de destinatario | Preferir `rector@`/`direccion@`/`recursos.humanos@`; caer a `info@`/`contacto@` |
| 16 | Backups | Diarios, retención 7 días |

---

## 3. Arquitectura

### 3.1 Visión general

Sistema modular tipo "pipeline" con seis módulos independientes que comparten una base de datos SQLite. El Programador de tareas de Windows ejecuta el pipeline cada mañana a las 7am.

```
┌─────────────────────────────────────────────────────────────────┐
│                  BASE DE DATOS (SQLite, 1 archivo)              │
│  Tablas: colegios | borradores | registro_ejecuciones           │
└──┬──────────────┬──────────────┬──────────────┬─────────────────┘
   │              │              │              │
   ▼              ▼              ▼              ▼
┌──────┐   ┌────────────┐   ┌────────┐   ┌──────────────┐
│  1   │──▶│     2      │──▶│   3    │──▶│      4       │
│des-  │   │ enriquecer │   │generar │   │  enviar      │
│cubrir│   │  (web+IA)  │   │(IA: HV │   │  borradores  │
│      │   │            │   │+carta) │   │   a Gmail    │
└──────┘   └────────────┘   └────────┘   └──────────────┘

   ┌─────────────┐         ┌──────────────────────┐
   │      5      │         │         6            │
   │   revisar   │         │     programar        │
   │ respuestas  │         │   seguimientos       │
   │ (cada 30min)│         │  (7–10 días sin resp)│
   └─────────────┘         └──────────────────────┘
```

### 3.2 Reglas invariantes del sistema

1. **Nada se pierde.** Cada colegio que entra a la BD tiene siempre un estado claro (máquina de estados estricta).
2. **Nada se duplica.** Deduplicación por NIT (si está) o por (nombre normalizado, ciudad).
3. **La IA nunca inventa.** Validador anti-alucinación verifica que cada nombre propio, fecha, ISBN y DOI en la versión personalizada exista en el CV original.
4. **Daniel siempre tiene la última palabra.** La herramienta crea borradores; Daniel los envía manualmente.

### 3.3 Tecnologías

- **Lenguaje:** Python 3.11+
- **Base de datos:** SQLite (un archivo único `data/colegios.db`)
- **IA:** API de Claude (Anthropic) — modelo recomendado: `claude-sonnet-4-6` por costo/calidad
- **Scraping HTTP:** `httpx` + `selectolax`
- **Scraping con JS:** `playwright` (Chrome headless), como fallback
- **Gmail:** API oficial de Google (Gmail API) con OAuth 2.0
- **Documentos:** `python-docx` para construir DOCX desde plantilla; `LibreOffice` headless para convertir a PDF
- **Programación de tareas:** Programador de tareas de Windows (configurado vía script PowerShell)
- **Notificaciones Windows:** `winotify` (toast notifications)
- **Notificaciones WhatsApp:** CallMeBot API (HTTP GET)
- **Tests:** `pytest`

### 3.4 Estructura de carpetas

```
C:/Users/elrug/cv-colegios/
├── data/
│   ├── colegios.db                 ← BD principal
│   ├── colegios.db.bak             ← rotación de 7 backups
│   ├── cv_base.pdf                 ← HV original del usuario
│   ├── cv_base_polished.pdf        ← HV con typos corregidos
│   ├── plantilla_base.docx         ← plantilla con campos placeholder
│   ├── salida/                     ← HVs personalizadas (PDFs)
│   └── logs/                       ← un archivo de log por día
├── modulos/
│   ├── descubrir.py
│   ├── enriquecer.py
│   ├── generar.py
│   ├── enviar_borradores.py
│   ├── revisar_respuestas.py
│   └── programar_seguimientos.py
├── prompts/                         ← editables sin recompilar
│   ├── clasificar_colegio.txt
│   ├── reescribir_perfil.txt
│   ├── personalizar_bullets.txt
│   ├── carta_presentacion.txt
│   └── seguimiento.txt
├── config/
│   ├── credentials.json             ← OAuth Gmail (no versionado)
│   ├── gmail_token.json             ← token guardado (no versionado)
│   └── .env                         ← API keys (no versionado)
├── tests/
│   └── test_*.py
├── correr_pipeline.py               ← entrypoint diario
├── correr_modulo.py                 ← correr módulo individual
├── reconstruir_plantilla.py         ← cuando cambia el CV base
├── autorizar_gmail.py               ← autenticación inicial
├── reautorizar_gmail.py             ← cuando expira el token
├── regenerar_borrador.py            ← regenerar para 1 colegio
├── descartar_colegio.py             ← excluir un colegio para siempre
├── estado.py                        ← imprimir resumen
├── init_db.py                       ← crear schema inicial
├── setup_tareas.ps1                 ← crear las tareas de Windows
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-05-05-cv-colegios-design.md   ← este documento
├── requirements.txt
└── README.md
```

---

## 4. Componentes (los 6 módulos)

### 4.1 Módulo `descubrir`

**Frecuencia:** los lunes (saltea otros días).

**Responsabilidad:** Insertar colegios nuevos a la tabla `colegios` con estado `descubierto`.

**Fuentes:**

- **MEN (Ministerio de Educación):** Descargar CSV del directorio DUE; filtrar por `naturaleza="no oficial"` y `departamento ∈ {Bogotá D.C., Antioquia, Atlántico (solo Barranquilla)}`.
- **Asociaciones:** Scrapear las páginas de miembros de UNCOLI, CONACED y ASCOLPEM. Extraer nombre + dominio.
- **Google Custom Search API:** Hasta 10 búsquedas por corrida. Queries: `"colegio bilingüe Bogotá site:.edu.co"`, `"colegio campestre Antioquia site:.edu.co"`, etc. (lista configurable en `config/queries_google.json`).

**Deduplicación:**
- Clave primaria lógica: `nit` si está; si no, `(nombre_normalizado, ciudad)` donde `nombre_normalizado` = lower-case + remove `colegio|institución|sas|ltda|corporación|...` + remove acentos + collapse spaces.
- Si un colegio ya existe, se actualiza solo lo que falte (no se sobrescriben campos existentes).
- Campo `fuente` se acumula como CSV: `"MEN,UNCOLI"`.

**Manejo de errores:**
- Cualquier fuente que falle no afecta a las otras.
- Cuota agotada en Google Custom Search → saltar fuente, reintentar la próxima semana.

### 4.2 Módulo `enriquecer`

**Frecuencia:** diaria, máximo 30 colegios por corrida.

**Responsabilidad:** Para colegios en estado `descubierto`, encontrar correo + clasificar perfil pedagógico. Pasarlos a `enriquecido` o `sin_correo`.

**Pasos:**

1. **Encontrar sitio web** (si no se tiene): query a Google Custom Search por nombre + ciudad.
2. **Descargar páginas relevantes:** home, `/contacto`, `/quienes-somos`, `/modelo-pedagogico`, `/pei`, `/admisiones`. Usar `httpx` primero; si la página requiere JS (detectado heurísticamente), reintentar con `playwright`.
3. **Extraer correo:** regex `[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.(com|co|edu\.co|org)`. Heurística de selección por preferencia: `rector@` > `direccion@` > `recursos.humanos@` > `talento@` > `info@` > `contacto@` > el más corto.
4. **Validar correo:** verificar que el dominio existe (`mxlookup` con `dnspython`).
5. **Clasificar perfil pedagógico** llamando a Claude con `prompts/clasificar_colegio.txt`. Pasar máximo 10.000 caracteres del texto extraído. Esperar respuesta JSON estricta:
   ```json
   {
     "bilingue": false,
     "idioma_segundo": null,
     "religioso": true,
     "denominacion": "calasanz",
     "ib": false,
     "montessori": false,
     "enfoque_deportivo": false,
     "enfoque_tecnico": false,
     "enfasis_tic": true,
     "tamano_estimado": "mediano",
     "palabras_clave": ["valores", "innovación", "comunidad"]
   }
   ```
6. **Estado final:**
   - Correo válido + JSON válido → `enriquecido`
   - Sin correo válido → `sin_correo` (excluido)
   - JSON inválido o página inaccesible → contador de intentos +1; si ≥3, marcar `error`.

**Paralelismo:** 5 colegios en paralelo con `asyncio` para no esperar I/O secuencialmente.

### 4.3 Módulo `generar`

**Frecuencia:** diaria, exactamente 15 colegios.

**Responsabilidad:** Producir HV personalizada (PDF) + asunto + cuerpo de carta para cada colegio.

**Selección:** los 15 colegios `enriquecidos` con `fecha_enriquecido` más antigua (FIFO).

**Pasos por colegio (3 llamadas a Claude encadenadas):**

1. **Reescribir Perfil** (`prompts/reescribir_perfil.txt`): pasar texto del Perfil del CV + perfil pedagógico del colegio. Claude devuelve 2 párrafos que conectan los hechos del CV con lo más relevante para ese colegio. Si nada conecta razonablemente, devuelve el Perfil original sin modificar.

2. **Reordenar y reescribir bullets de experiencias** (`prompts/personalizar_bullets.txt`): pasar lista de experiencias del CV + perfil pedagógico. Claude devuelve un array JSON con orden sugerido y, para cada experiencia, los bullets reescritos con el énfasis adecuado (sin agregar hechos nuevos).

3. **Generar carta de presentación** (`prompts/carta_presentacion.txt`): pasar nombre del colegio, ciudad, perfil pedagógico, hechos clave del CV, URL de portafolio. Claude devuelve carta de máximo 200 palabras.

**Validador anti-alucinación** (después de cada paso):
- Extrae todos los nombres propios, números (años, ISBNs, DOIs, porcentajes) y fechas de la salida de Claude.
- Verifica que cada uno aparezca en el texto del CV original.
- Si aparece algo nuevo → rechaza, regenera. Si en 3 intentos sigue alucinando → marcar colegio como `revisar_manualmente` y avanzar.

**Construcción de la HV:**
- Cargar `data/plantilla_base.docx` con `python-docx`.
- Reemplazar placeholders: `{{PERFIL}}`, `{{EXPERIENCIA_1_TITULO}}`, `{{EXPERIENCIA_1_BULLETS}}`, etc.
- Guardar como `data/salida/{colegio_slug}_HV.docx`.
- Convertir a PDF con `LibreOffice --headless --convert-to pdf`.
- Resultado: `data/salida/{colegio_slug}_HV.pdf`.

**Asunto del correo:** `"Postulación docente — Daniel E. Villalba — {Nombre Colegio}"`.

**Salida:** una fila en tabla `borradores` con `estado='listo_para_subir'`. Colegio pasa a estado `borrador_creado`.

### 4.4 Módulo `enviar_borradores`

**Frecuencia:** diaria.

**Responsabilidad:** Subir todos los borradores `listo_para_subir` a la carpeta de Borradores de Gmail.

**Pasos:**

1. Autenticar con `gmail_token.json`. Si expiró, registrar evento → notificación a Daniel pidiendo correr `python reautorizar_gmail.py`.
2. Para cada borrador:
   - Construir mensaje MIME con: destinatario (correo del colegio), asunto, cuerpo (carta), adjunto (PDF de la HV).
   - Llamar a `users.drafts.create`.
   - Guardar `gmail_draft_id` y `gmail_thread_id` en la fila del borrador y en la fila del colegio.
3. Marcar borrador como `subido`. Colegio queda en `borrador_creado` (transiciona a `enviado` solo cuando Daniel lo envía manualmente desde Gmail).

**Detección de envío real:** el módulo `revisar_respuestas` también verifica el estado de cada `gmail_thread_id`: si Gmail reporta que el borrador ya no es draft (porque Daniel lo envió), actualiza `colegios.estado` a `enviado` y guarda `fecha_envio`.

### 4.5 Módulo `revisar_respuestas`

**Frecuencia:** cada 30 minutos entre 8am y 10pm.

**Responsabilidad:** Detectar respuestas, rebotes y envíos manuales hechos por Daniel. Notificar inmediatamente cuando llega una respuesta nueva.

**Pasos:**

1. Para cada colegio con `gmail_thread_id` no nulo y estado en `{borrador_creado, enviado, seguimiento_pendiente}`:
   - Consultar Gmail API por el thread.
   - Si hay mensajes nuevos del colegio (`From` distinto al del usuario):
     - Si `Subject` o `From` indica bounce/Mailer-Daemon → estado = `rebotó`.
     - Si es respuesta normal → estado = `respondió`, `fecha_respuesta` = ahora.
     - **Notificar inmediatamente** (Windows toast + email + WhatsApp): `"📬 Respuesta de {Nombre Colegio}"`.
   - Si el último mensaje del thread es del usuario y no era el draft (ya envió) → estado = `enviado`, `fecha_envio` = fecha del mensaje.
2. **Privacidad:** no se lee el cuerpo de las respuestas, solo metadata (`From`, `Subject`, `Date`, `labels`).

### 4.6 Módulo `programar_seguimientos`

**Frecuencia:** diaria, máximo 5 seguimientos por corrida.

**Responsabilidad:** Para colegios con `estado='enviado'` y `fecha_envio` entre 7 y 10 días atrás, generar un borrador de seguimiento amable.

**Pasos:**

1. Buscar candidatos.
2. Para cada uno (FIFO, máximo 5):
   - Llamar a Claude con `prompts/seguimiento.txt`. Devuelve correo de 80–100 palabras.
   - Crear borrador en Gmail en el mismo `gmail_thread_id` (vía `In-Reply-To` y `References`).
   - Marcar colegio como `seguimiento_pendiente`.

**Tope estricto:** un solo seguimiento por colegio. Si tampoco responde, queda en `sin_respuesta` (cerrado, no se vuelve a contactar).

---

## 5. Modelo de datos

### 5.1 Tabla `colegios`

| columna | tipo | nullable | descripción |
|---|---|---|---|
| `id` | INTEGER PRIMARY KEY | no | autoincremental |
| `nombre` | TEXT | no | |
| `nombre_normalizado` | TEXT | no | para deduplicación |
| `ciudad` | TEXT | no | |
| `departamento` | TEXT | no | |
| `nit` | TEXT | sí | UNIQUE si no es nulo |
| `web` | TEXT | sí | |
| `correo` | TEXT | sí | el primero encontrado |
| `correo_destinatario` | TEXT | sí | el seleccionado por heurística |
| `fuente` | TEXT | no | CSV: `"MEN,UNCOLI"` |
| `perfil_pedagogico` | JSON | sí | objeto con flags |
| `palabras_clave` | JSON | sí | lista de strings |
| `estado` | TEXT | no | máquina de estados (ver 5.4) |
| `intentos_enriquecer` | INTEGER | no | default 0, max 3 |
| `intentos_generar` | INTEGER | no | default 0, max 3 |
| `fecha_descubierto` | DATETIME | no | |
| `fecha_enriquecido` | DATETIME | sí | |
| `fecha_envio` | DATETIME | sí | |
| `fecha_respuesta` | DATETIME | sí | |
| `gmail_draft_id` | TEXT | sí | |
| `gmail_thread_id` | TEXT | sí | |
| `notas` | TEXT | sí | campo libre editable a mano |

**Índices:** `(estado)`, `(nombre_normalizado, ciudad)` UNIQUE, `(nit)` UNIQUE WHERE NOT NULL, `(gmail_thread_id)`.

### 5.2 Tabla `borradores`

| columna | tipo | nullable | descripción |
|---|---|---|---|
| `id` | INTEGER PK | no | |
| `colegio_id` | INTEGER FK | no | |
| `tipo` | TEXT | no | `"inicial"` o `"seguimiento"` |
| `asunto` | TEXT | no | |
| `cuerpo_carta` | TEXT | no | |
| `ruta_pdf_hv` | TEXT | sí | nulo para seguimientos |
| `estado` | TEXT | no | `listo_para_subir` / `subido` / `fallo` |
| `gmail_draft_id` | TEXT | sí | |
| `fecha_creado` | DATETIME | no | |
| `fecha_subido` | DATETIME | sí | |
| `error_mensaje` | TEXT | sí | si `estado='fallo'` |

### 5.3 Tabla `registro_ejecuciones`

| columna | tipo | descripción |
|---|---|---|
| `id` | INTEGER PK | |
| `modulo` | TEXT | |
| `fecha` | DATETIME | |
| `duracion_segundos` | REAL | |
| `estado` | TEXT | `ok` / `error` |
| `colegios_procesados` | INTEGER | |
| `mensaje` | TEXT | detalle si error |
| `costo_api_usd` | REAL | costo estimado de llamadas a Claude en esa corrida |

### 5.4 Máquina de estados de un colegio

```
descubierto ──▶ enriquecido ──▶ borrador_creado ──▶ enviado ──▶ respondió
     │              │                                    │
     │              └──▶ sin_correo (excluido)           ├──▶ rebotó (excluido)
     │                                                   │
     └──▶ error (3 fallos, excluido)                     └──▶ seguimiento_pendiente
                                                              ├──▶ respondió
                                                              └──▶ sin_respuesta (cerrado)

Cualquier estado ──▶ descartado (manual, vía descartar_colegio.py)
Cualquier estado ──▶ revisar_manualmente (alucinación recurrente o bloqueo del scraping)
```

**Transiciones inválidas:** un trigger SQL evita retrocesos no permitidos (p. ej., de `enviado` a `descubierto`).

---

## 6. Flujo de un día típico

A las 7am el Programador de tareas dispara `correr_pipeline.py`. Orden de ejecución y tiempos estimados:

| Paso | Módulo | Frecuencia | Tiempo estimado | Output |
|---|---|---|---|---|
| 1 | `descubrir` | solo lunes | 1–2 min | 0–50 colegios nuevos |
| 2 | `enriquecer` | diario | 8–15 min | ~25 enriquecidos / día |
| 3 | `generar` | diario | 5–8 min | 15 PDFs nuevos |
| 4 | `enviar_borradores` | diario | 1–2 min | 15 borradores en Gmail |
| 5 | `revisar_respuestas` | diario + cada 30 min | 30 seg | estados actualizados |
| 6 | `programar_seguimientos` | diario | 1–2 min | hasta 5 seguimientos |

**Total pipeline matinal:** ~22 min.

**Trabajo diario de Daniel:** 10–15 min revisando los 15 borradores en Gmail y enviando los aprobados.

**Costo estimado de API:** ~$1 USD/día → ~$30 USD/mes.

---

## 7. Manejo de errores

### 7.1 Errores recuperables (auto-retry)

- Sin internet → reintentar mañana.
- Sitio del colegio caído → 3 reintentos con backoff exponencial; si todos fallan, `error` y reintentar en 7 días.
- Sitio JS-pesado → fallback automático a `playwright`.
- Sitio con CAPTCHA → marcar `revisar_manualmente`, continuar.
- Claude devuelve JSON malformado → 2 reintentos con prompt más estricto; si falla, regresar a `descubierto` con contador +1.
- Cuota Google Custom Search agotada → saltar etapa de descubrimiento.
- Pipeline interrumpido → SQLite con transacciones; al retomar, idempotencia por consulta a `registro_ejecuciones`.

### 7.2 Errores que requieren atención (notificación)

Notificación por Windows + correo + WhatsApp:

- Token Gmail expirado → "Reautoriza Gmail: corre `python reautorizar_gmail.py`"
- Saldo Anthropic < $5 USD → "Recarga API en console.anthropic.com"
- Saldo agotado mid-pipeline → "Pipeline pausado por saldo. Recarga y corre de nuevo"
- 5+ días con cola vacía de `enriquecidos` → "Revisar fuentes de descubrimiento"
- Falla de conversión DOCX→PDF → "Verificar que LibreOffice esté instalado"

### 7.3 Salvaguardas anti-fallos catastróficos

- **Doble envío al mismo colegio:** prevenido por `gmail_thread_id` único.
- **HV con datos inventados:** validador anti-alucinación (sección 4.3).
- **HV con datos viejos:** `hash` del PDF base se guarda; si cambia, sistema bloquea generación hasta correr `python reconstruir_plantilla.py`.
- **Pipeline corre 2 veces el mismo día:** cada módulo verifica `registro_ejecuciones` antes de iniciar; si ya corrió hoy con éxito, salta.
- **BD corrupta:** backup diario rotativo (`colegios.db.bak.{1..7}`), recuperable manualmente.

### 7.4 Casos límite específicos

- Colegios con nombres iguales en distintas ciudades → entidades distintas.
- Mismo colegio descubierto por varias fuentes → única fila, fuentes acumuladas.
- Colegio sin web pública → `sin_correo`, excluido. Daniel puede llenar correo a mano.
- Colegio responde por WhatsApp → fuera de alcance; Daniel marca `respondió` editando la BD.

### 7.5 Comandos manuales de recuperación

```
python correr_pipeline.py
python correr_pipeline.py --modo-prueba
python correr_modulo.py descubrir
python reconstruir_plantilla.py
python reautorizar_gmail.py
python regenerar_borrador.py <colegio_id>
python descartar_colegio.py <colegio_id>
python estado.py
```

---

## 8. Configuración inicial

Pasos a ejecutar una sola vez (1–2 horas guiadas):

1. **Instalar prerrequisitos:** Python 3.11+, LibreOffice, DB Browser for SQLite.
2. **Crear cuentas y obtener llaves:**
   - Anthropic Console (cargar $20 USD).
   - Google Cloud Console: proyecto, Gmail API, Custom Search API, OAuth credentials.
   - CallMeBot (mensaje desde WhatsApp para obtener API key).
3. **Inicializar proyecto:** `pip install -r requirements.txt`, `python init_db.py`.
4. **Construir plantilla base pulida:**
   - Colocar `data/cv_base.pdf`.
   - Correr `python reconstruir_plantilla.py`.
   - Claude propone versión limpia (typos corregidos, fechas unificadas, formato mejorado); Daniel aprueba interactivamente.
   - Resultado: `data/plantilla_base.docx` + `data/cv_base_polished.pdf`.
5. **Conectar Gmail:** `python autorizar_gmail.py` → flujo OAuth en navegador.
6. **Programar tareas Windows:** `setup_tareas.ps1` crea las tareas (pipeline a las 7am, revisar_respuestas cada 30 min).
7. **Primera corrida en modo prueba:** `python correr_pipeline.py --modo-prueba --colegios 3`.

### 8.1 Lista de typos a corregir en CV original

- `INTITUCIÓN` → `INSTITUCIÓN` (4 ocurrencias)
- `Promociones los hábitos` → `Promoví los hábitos`
- `revisiones gratuitaqs` → `revisiones gratuitas`
- `phyton` → `Python`
- `SKILL TRANNING ADAPTION` → `SKILL TRAINING ADAPTATION`
- `INTITUCIÓN UNIVERSITARIA POLITECNICO GRAN COLOMBIANO` → `INSTITUCIÓN UNIVERSITARIA POLITÉCNICO GRAN COLOMBIANO`
- Bloque de idiomas: reformatear a líneas separadas
- Unificar formato de fechas a `DD/MM/AAAA`
- Revisar acentos faltantes en "INSTITUCIÓN", "MAESTRÍA", "CÓRDOBA", etc.

---

## 9. Estrategia de pruebas

### 9.1 Validadores en producción (corren en cada pipeline)

- **Anti-alucinación:** comparar tokens propios de la salida de Claude contra el CV original.
- **JSON schema:** validar respuestas estructuradas de Claude.
- **Email:** regex + verificación MX.
- **Deduplicación:** verificar antes de cada `INSERT`.

### 9.2 Pruebas unitarias (`pytest`)

- Extracción de email de 10 HTMLs sintéticos.
- Normalización de nombres (`Colegio San José S.A.S.` ↔ `COLEGIO SAN JOSE`).
- Transiciones válidas/inválidas en máquina de estados.
- Validador anti-alucinación con ejemplos sintéticos (positivos y negativos).
- Construcción de DOCX desde plantilla con datos de prueba.
- Escritura/lectura de SQLite con datos de prueba.

### 9.3 Modo de prueba en vivo

- `--modo-prueba`: ejecuta el pipeline pero sin tocar Gmail real (escribe los borradores como `.eml` en `data/salida/borradores_prueba/` para inspección).
- Útil cada vez que se cambien prompts o haya dudas.

### 9.4 Plan de despliegue gradual (2 semanas)

| Día | Actividad |
|---|---|
| 1 | Setup completo (1–2 h guiadas) |
| 2 | Modo prueba con 3 colegios; revisión humana de outputs |
| 3 | Primera corrida real con 5 colegios |
| 4–7 | Subir a 10/día, luego a 15/día |
| 8–14 | Ritmo normal 15/día; refinar prompts si la calidad no convence |

---

## 10. Métricas de éxito

Métricas que Daniel monitoreará en el comando `python estado.py` y/o en el panel de SQLite:

- **Cobertura:** % de colegios objetivo alcanzados (target: 1.500 en 5 meses).
- **Tasa de validez de correos:** % de envíos que no rebotan (target: ≥85%).
- **Tasa de respuesta:** % de colegios contactados que responden (benchmark cold outreach: 5–15%).
- **Tasa de personalización aceptada:** % de borradores que Daniel envía sin editar (target: ≥70%).
- **Tiempo invertido por Daniel:** minutos/día revisando borradores (target: ≤15 min/día).
- **Costo por respuesta obtenida:** USD gastados en API ÷ respuestas recibidas.

---

## 11. Fuera de alcance (para iteraciones futuras)

Esto se considera deliberadamente *no incluido* en esta primera versión:

- Migración a la nube (GitHub Actions, Railway).
- Dashboard web con gráficas.
- Integración con WhatsApp para recibir respuestas (no solo notificaciones).
- Soporte multi-usuario.
- Personalización profunda con riesgo de omitir experiencias.
- Aplicación a vacantes activas en LinkedIn / Computrabajo / El Empleo.
- Generación automática del sitio Notion (Daniel arma manualmente el suyo a partir del contenido sugerido).
- Análisis de sentimiento de respuestas con IA.
- Soporte para colegios fuera de Colombia.

---

## 12. Riesgos identificados

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Gmail clasifica los correos como spam | Alto | Ritmo bajo (15/día), personalización real, sin links sospechosos, dominio ya establecido |
| Cuenta de Gmail suspendida por envío masivo | Alto | Pipeline crea borradores, no envíos directos; Daniel controla el botón Enviar |
| Webs de colegios cambian y rompen el scraping | Medio | Reintentos + estado `error` con re-intento a 7 días; logs detallados para debug |
| Costo de API mayor al estimado | Bajo | Modelo Sonnet (no Opus), prompts caching, tope diario configurable |
| Claude alucina hechos en la HV | Alto | Validador anti-alucinación bloqueante en cada paso de generación |
| Daniel olvida prender el laptop y pierde días | Medio | Idempotencia: el pipeline retoma desde donde quedó; nunca se pierden colegios |
| Webs requieren CAPTCHA / bloquean scrapers | Medio | Marcar `revisar_manualmente`, no romper pipeline; Daniel puede llenar correo a mano |
| Colegio recibe el mismo correo que ya recibió de Daniel hace tiempo | Medio | Deduplicación rigurosa por NIT y por nombre+ciudad; constraint UNIQUE en BD |

---

## 13. Próximo paso

Tras la aprobación de Daniel a este documento, se invocará la skill `superpowers:writing-plans` para producir un plan de implementación paso a paso, con tareas verificables, dependencias claras, y puntos de checkpoint con Daniel.
