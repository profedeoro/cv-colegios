# Plan 4 — Generación de HV personalizada + Envío Gmail

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Para cada colegio en estado `enriquecido`, generar (a) HV personalizada en PDF + (b) carta de presentación + (c) asunto del correo, y crear el borrador en Gmail listo para que Daniel lo revise y envíe.

**Architecture:** Dos módulos secuenciales: `generar` (3 llamadas a Claude por colegio: reescribir Perfil + reordenar bullets + carta) y `enviar_borradores` (OAuth Gmail + drafts.create). Validador anti-alucinación de Plan 1 protege cada generación. Procesamiento secuencial 15/día (target).

**Tech Stack:** Anthropic SDK (ya), python-docx (ya), LibreOffice (ya), `google-api-python-client`, `google-auth-oauthlib`, `google-auth-httplib2` (nuevas).

**Spec referenciado:** `docs/superpowers/specs/2026-05-05-cv-colegios-design.md` — secciones 4.3 y 4.4.

---

## Roadmap actualizado

| Plan | Producto al terminar | Estado |
|---|---|---|
| 1. Cimientos + plantilla | ✅ | DONE |
| 2. Descubrimiento | ✅ | DONE (3.116 colegios) |
| 3. Enriquecimiento | ✅ | DONE (258 enriquecidos, 2.639 retryables cuando Brave reponga) |
| **4. Generación + Envío Gmail (este)** | Borradores en Gmail listos | En curso |
| 5. Respuestas + Seguimientos | Loop cerrado | Próximo |
| 6. Orquestación + Programador Windows | Sistema en producción | Final |

---

## Conceptos clave para Daniel

- **OAuth de Gmail:** Una sola vez, Google te pide permiso de acceder a tu Gmail. Después se guarda un token en tu laptop que sirve por meses (renovable). Sin contraseña expuesta — Google maneja todo.
- **Gmail Drafts API:** la herramienta NO envía correos; crea borradores en tu carpeta "Borradores". Tú abres Gmail, revisas el borrador, le das "Enviar" si quieres.
- **3 llamadas a Claude por colegio:** ~$0.05 cada uno. Total para 258 colegios: ~$13 USD.
- **PDF personalizado:** cada colegio tiene su propio PDF en `data/salida/{slug}.pdf` — útil si quieres revisarlos antes de mandar.
- **Validador anti-alucinación:** Si Claude inventa un dato (ISBN/año/nombre que no está en tu CV), se detecta y se regenera. Si tras 3 intentos sigue alucinando, se marca `revisar_manualmente` y NO se manda.

---

## Estructura de archivos a crear

```
modulos/
├── generar.py                    ← orquestador del módulo 3 (Tarea 5)
├── docx_personalizado.py         ← rellena plantilla con valores personalizados (Tarea 4)
├── gmail_oauth.py                ← flujo OAuth + cliente Gmail (Tarea 6)
└── enviar_borradores.py          ← orquestador del módulo 4 (Tarea 7)

prompts/
├── reescribir_perfil.txt         ← prompt 1/3 (Tarea 3)
├── personalizar_bullets.txt      ← prompt 2/3 (Tarea 3)
├── carta_presentacion.txt        ← prompt 3/3 (Tarea 3)
└── seguimiento.txt               ← (Plan 5, no en este)

correr_modulo.py                  ← agregar subcomandos generar y enviar_borradores
autorizar_gmail.py                ← script one-shot para OAuth (Tarea 6)
```

---

## Tarea 0: Daniel hace setup de Gmail API OAuth (~15 min, manual)

Reusas tu Google Cloud project `cv-colegios` que creaste en Plan 2.

- [ ] **Paso 1: Habilitar Gmail API**

1. Ve a https://console.cloud.google.com
2. Asegúrate de estar en el proyecto `cv-colegios` (selector arriba a la izquierda).
3. Menú hamburguesa `≡` → "APIs & Services" → "Library".
4. Busca: `Gmail API`. Click en "Gmail API". Click "Enable".

- [ ] **Paso 2: Configurar OAuth Consent Screen**

1. Menú `≡` → "APIs & Services" → "OAuth consent screen".
2. User type: **External** (única opción disponible si no tienes Workspace). Click "Create".
3. Llena el formulario mínimo:
   - **App name:** `cv-colegios`
   - **User support email:** `danedu348@gmail.com`
   - **Developer contact:** `danedu348@gmail.com`
   - Resto déjalo vacío. Click "Save and Continue".
4. **Scopes:** click "Add or Remove Scopes". Busca `gmail.compose` y márcalo. Click "Update". Click "Save and Continue".
5. **Test users:** click "Add Users". Agrega `danedu348@gmail.com`. Click "Save and Continue".
6. Click "Back to Dashboard".

- [ ] **Paso 3: Crear OAuth Client ID**

1. Menú `≡` → "APIs & Services" → "Credentials".
2. "+ Create Credentials" → "OAuth client ID".
3. **Application type:** "Desktop app".
4. **Name:** `cv-colegios-desktop`.
5. Click "Create". Te muestra un modal con tus credenciales.
6. Click el botón **"Download JSON"** y guarda el archivo. Lo vas a renombrar.

- [ ] **Paso 4: Mover el archivo al proyecto**

```powershell
Move-Item "C:\Users\elrug\Downloads\client_secret_*.json" "C:\Users\elrug\cv-colegios\config\credentials.json"
```

(Si el nombre es distinto, ajusta — busca el `.json` que descargaste.)

Verifica que existe:
```powershell
ls C:\Users\elrug\cv-colegios\config\credentials.json
```

⚠️ Este archivo es **secreto** — está gitignored. NUNCA lo subas a git ni lo compartas.

- [ ] **Paso 5: Avísame** "listo Gmail OAuth" y los sub-agentes pueden continuar.

---

## Tarea 1: Agregar dependencias Gmail

**Files:**
- Modify: `requirements.txt`

- [ ] **Paso 1: Agregar al final de `requirements.txt`**

```
google-api-python-client>=2.140.0
google-auth-oauthlib>=1.2.0
google-auth-httplib2>=0.2.0
```

- [ ] **Paso 2: Instalar**

```bash
C:/Users/elrug/cv-colegios/.venv/Scripts/pip.exe install -r C:/Users/elrug/cv-colegios/requirements.txt
```

- [ ] **Paso 3: Verificar suite verde y commit**

```bash
C:/Users/elrug/cv-colegios/.venv/Scripts/pytest.exe C:/Users/elrug/cv-colegios/tests/ -v
git -C C:/Users/elrug/cv-colegios add requirements.txt
git -C C:/Users/elrug/cv-colegios commit -m "chore(plan4): dependencias de Gmail API"
```

---

## Tarea 2: Helpers BD para módulo generar

**Files:**
- Modify: `modulos/db.py` — agregar 3 funciones
- Create: `tests/test_db_generar.py`

Funciones:
- `colegios_para_generar(ruta_bd, limite=15)`: enriquecidos con menos de 3 intentos_generar
- `marcar_borrador_creado(ruta_bd, colegio_id, gmail_draft_id, gmail_thread_id)`
- `incrementar_intento_generar(ruta_bd, colegio_id)`
- `insertar_borrador(ruta_bd, colegio_id, tipo, asunto, cuerpo_carta, ruta_pdf_hv)`

(El detalle del SQL es estándar — ver implementación en Tarea 6 si necesitas referencia.)

Tests cubren cada función con tmp_path.

---

## Tarea 3: 3 prompts de generación

**Files:**
- Create: `prompts/reescribir_perfil.txt`
- Create: `prompts/personalizar_bullets.txt`
- Create: `prompts/carta_presentacion.txt`

Cada prompt:
- Recibe: el bloque relevante del CV de Daniel + perfil pedagógico del colegio (JSON).
- Devuelve: texto reescrito (no JSON, solo texto).
- Estricto sobre NO inventar datos.
- Tono profesional, español colombiano.

(Contenido detallado de cada prompt se completa en la implementación; cada uno ~30-50 líneas.)

---

## Tarea 4: Módulo `docx_personalizado.py`

**Files:**
- Create: `modulos/docx_personalizado.py`
- Create: `tests/test_docx_personalizado.py`

Función `generar_pdf_personalizado(plantilla_path, valores, salida_pdf)`:
- Usa `rellenar_plantilla` de Plan 1 para insertar valores en placeholders.
- Convierte a PDF con `convertir_docx_a_pdf` de Plan 1.
- Limpia DOCX intermedio.

---

## Tarea 5: Orquestador `generar`

**Files:**
- Create: `modulos/generar.py`
- Create: `tests/test_generar.py`

Función `procesar_colegio(ruta_bd, colegio, cliente_claude)`:
1. Lee perfil_pedagogico del colegio.
2. Lee texto del CV polished (data/cv_base_polished.pdf via leer_pdf, o desde la plantilla con valores).
3. Llama Claude 3 veces (perfil/bullets/carta).
4. Cada respuesta pasa por `detectar_alucinaciones` (si encuentra hechos inventados, regenera; max 3 intentos).
5. Genera PDF personalizado en `data/salida/{slug}.pdf`.
6. Inserta fila en `borradores` con asunto + cuerpo + ruta_pdf.

Función `ejecutar(ruta_bd, cliente_claude, max_colegios=15)`:
- Toma `colegios_para_generar(limite=max_colegios)`.
- Procesa secuencialmente.
- Registra ejecución.

---

## Tarea 6: Cliente Gmail OAuth

**Files:**
- Create: `modulos/gmail_oauth.py`
- Create: `autorizar_gmail.py` (one-shot script)
- Create: `tests/test_gmail_oauth.py` (con mocks)

`autorizar_gmail.py`:
- Carga `config/credentials.json`.
- Inicia flujo OAuth — abre el navegador, Daniel da permiso.
- Guarda `config/gmail_token.json`.
- Imprime confirmación.

`modulos/gmail_oauth.py`:
- Función `obtener_servicio_gmail()`: lee `gmail_token.json`, refresh si es necesario, devuelve un `service` de la API.
- Función `crear_borrador(service, destinatario, asunto, cuerpo, adjunto_pdf)`: construye MIME, llama `users.drafts.create`, devuelve `(draft_id, thread_id)`.

Tests usan mocks de `googleapiclient.discovery.build`.

---

## Tarea 7: Orquestador `enviar_borradores`

**Files:**
- Create: `modulos/enviar_borradores.py`
- Create: `tests/test_enviar_borradores.py`

Función `ejecutar(ruta_bd)`:
- Toma todos los borradores con estado `listo_para_subir`.
- Para cada uno: lee del BD, llama `crear_borrador` en Gmail, marca como `subido` con `gmail_draft_id`.
- Registra ejecución.

Manejo de errores: si Gmail rechaza un correo (correo inválido, etc.), marca colegio como `correo_invalido` (terminal).

---

## Tarea 8: CLI subcomandos

**Files:**
- Modify: `correr_modulo.py`
- Modify: `tests/test_correr_modulo.py`

Agregar subcomandos:
- `python correr_modulo.py generar --max 15`
- `python correr_modulo.py enviar_borradores`

---

## Tarea 9: Smoke test (Daniel manual)

Pre-requisitos:
- Tarea 0 completada (`config/credentials.json` existe).
- `python autorizar_gmail.py` corrido una vez (crea `gmail_token.json`).
- BD tiene colegios enriquecidos (258 en este momento).

Pasos:

```powershell
# Generar 5 borradores
.\.venv\Scripts\python.exe correr_modulo.py generar --max 5

# Subir a Gmail
.\.venv\Scripts\python.exe correr_modulo.py enviar_borradores
```

Después abre Gmail (en navegador) → carpeta "Borradores". Deberías ver 5 borradores nuevos.

Para cada uno:
- Léelo.
- Revisa que la HV adjunta abra bien y se vea con tu estilo original.
- Verifica que la carta mencione algo coherente del perfil del colegio (bilingüe / IB / religioso / etc).
- Si todo bien, le das "Enviar". Si está mal, "Descartar" (la BD recordará no regenerarlo).

---

## Verificación final del Plan 4

- [ ] Gmail API habilitada y OAuth configurado
- [ ] `pytest tests/ -v` → todos verdes (~190+ tests)
- [ ] Smoke test de 5 colegios genera 5 borradores en Gmail
- [ ] HVs personalizadas se ven bien (estilo preservado, datos correctos)
- [ ] Cartas de presentación coherentes con el perfil del colegio
- [ ] Costo por colegio ≤ $0.10 USD

Si todo se cumple, **Plan 4 está completo** y pasamos al **Plan 5** (Respuestas + Seguimientos + Notificaciones).

---

## Notas

- **Costo estimado total** para 258 colegios: ~$15 USD ($0.06 por colegio promedio entre 3 llamadas).
- **Tiempo estimado** para 258 colegios a 15/día: ~17 días.
- **Calidad** depende de la calidad del enriquecimiento (perfil_pedagogico). Los 258 actuales son de alta calidad.
