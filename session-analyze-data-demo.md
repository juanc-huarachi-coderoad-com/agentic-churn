# Revisión del proyecto y nuevos eventos Gmail

**Session ID:** ses_fee4cd68effeLx9LbLwczvvEpB
**Created:** 8/17/2026, 5:49:09 PM
**Updated:** 8/17/2026, 8:03:10 PM

---

## User

revisar este proyecto, y ayudame a encontrar la manera para adicionar nuevos eventos de gmail, u otra fuente para probar la funcionalidad de la aplicacion por favor

---

## Assistant (Plan · GLM-5.2 · 5.2s)

Voy a explorar el proyecto para entender su estructura y encontrar cómo añadir nuevos eventos para probar la funcionalidad.

**Tool: read**

**Tool: read**

---

## Assistant (Plan · GLM-5.2 · 2.2s)

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant (Plan · GLM-5.2 · 1.7s)

**Tool: read**

**Tool: read**

---

## Assistant (Plan · GLM-5.2 · 1.9s)

**Tool: read**

**Tool: read**

---

## Assistant (Plan · GLM-5.2 · 4.3s)

Excelente. Ahora exploraré los adapters de ingestion y los scripts demo para entender cómo se añaden eventos.

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant (Plan · GLM-5.2 · 1.9s)

**Tool: read**

**Tool: read**

---

## Assistant (Plan · GLM-5.2 · 2.3s)

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant (Plan · GLM-5.2 · 1.9s)

**Tool: read**

**Tool: read**

---

## Assistant (Plan · GLM-5.2 · 2.5s)

**Tool: read**

**Tool: read**

---

## Assistant (Plan · GLM-5.2 · 3.9s)

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant (Plan · GLM-5.2 · 3.0s)

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant (Plan · GLM-5.2 · 4.4s)

Tengo una visión completa del proyecto. Déjame verificar un par de detalles finales sobre la configuración.

**Tool: read**

**Tool: grep**

---

## Assistant (Plan · GLM-5.2 · 113.3s)

He revisado el proyecto a fondo. Aquí está mi análisis y plan.

## Cómo entra un evento al sistema hoy

El proyecto tiene **un único colector concreto**: `SimulatedCollector` (`backend/app/ingestion/adapters/simulated_collector.py:152`), que lee un archivo JSON de fixtures en vez de una API real. La ruta se configura con `COLLECTOR_FIXTURE_PATH` (por defecto `./demo/fixtures/meridian-week.json`, ver `backend/app/config.py:47`).

El flujo completo para probar funcionalidad (según `README.md` y `demo/01-live-demo-runbook.md`):

```
scripts/run_collector.py --source simulated   # ingesta + append al ledger + replay
scripts/confirm_baseline.py                    # solo si quieres que Tone dispare
scripts/run_readers.py                         # 8 readers + validation gate
scripts/compute_score.py                       # scoring (corre 2x para asentar banda)
scripts/run_narrator.py                        # explicación
```

## Formato del fixture

Cada evento es un objeto JSON con `source_type` + campos por fuente. Los `source_type` soportados hoy en `SimulatedCollector` (`simulated_collector.py:142-149`) y sus campos obligatorios:

| `source_type` | Requiere | Se convierte en `event_type` |
|---|---|---|
| `gmail` | `source_native_id`, `occurred_at`, `from`, `text` | `message` |
| `slack` | `source_native_id`, `occurred_at`, `from`, `text` | `message` |
| `zendesk` | `source_native_id`, `occurred_at`, `reporter`, `ticket_number`, `title`, `product_area`, `state` (+ `reopen_count` opt) | `ticket_state_change` |
| `warehouse` | `source_native_id`, `occurred_at`, `metric`, `product_area`, `value_delta_pct` | `usage_measurement` |
| `csat` | `source_native_id`, `occurred_at`, `respondent`, `score` (+ `comment` opt) | `survey_response` |
| `calendar` | `source_native_id`, `occurred_at`, `attendee`, `series_id`, `consent_documented`, `transcript` | `meeting` |

**Reglas críticas que ya aprendí del código (no negociables):**
- **Idempotency**: la llave es `hash(source_type, source_native_id)`. Para añadir eventos *nuevos* debes usar `source_native_id` *nuevos*; si repites uno, se cuenta como duplicado y se salta (`use_cases.py:382-384`).
- **Identidad**: `from`/`reporter`/`respondent`/`attendee` se resuelve contra `demo/client-profile.yaml`. Hoy solo `ana.reyes@meridian.com`→`stk_ana` y `diego@meridian.com`→`stk_diego`. Un correo nuevo queda `unresolved` (lo cual es válido — el sistema se abstiene, no adivina, REQ-M1-05).
- **`product_area`** debe existir en el perfil (`tracking_api` o `reporting`) o se ignora.
- **Exclusiones** del perfil (`legal_threads`, `commercial_negotiation`) redactan el body si aparece una frase marcadora (`use_cases.py:219-236`).
- **Calendar** sin `consent_documented: true` se descarta antes de llegar al ledger (`simulated_collector.py:168-172`).
- Fuentes Phase 1 (`gmail`, `zendesk`, `warehouse`) siempre se esperan; las Phase 2 solo si el fixture las trae (`use_cases.py:283-297`).

## Tres caminos posibles para añadir eventos

Necesito que elijas uno antes de ejecutar, porque el alcance es muy distinto:

**Tool: question**

---

## Assistant (Plan · GLM-5.2 · 11.0s)

Permíteme verificar una cosa importante antes de finalizar el plan: si editar el fixture de Meridian rompería los golden tests.

**Tool: glob**

**Tool: glob**

**Tool: grep**

---

## Assistant (Plan · GLM-5.2 · 4.7s)

**Tool: read**

**Tool: read**

---

## Assistant (Plan · GLM-5.2 · 40.2s)

Hallazgo clave: `meridian-week.json` está **fijado por dos tests** (`tests/unit/test_simulated_collector.py:33` y `tests/ingestion/test_post_mvp_sources_real_db.py:43`), que asertan propiedades estructurales (redacción del item legal, resolución de Ana, conteos). **Editarlo en sitio rompería los tests.** La ruta segura es crear un fixture nuevo.

## Plan concreto

### 1. Crear un fixture nuevo (sin tocar `meridian-week.json`)

Archivo: `demo/fixtures/meridian-extra.json` — un array JSON con eventos usando los `source_type` ya soportados. Ejemplos realistas que ejercitan distintos readers:

```json
[
  {
    "source_type": "gmail",
    "source_native_id": "gmail-msg-9001",
    "occurred_at": "2026-08-15T10:00:00-05:00",
    "from": "ana.reyes@meridian.com",
    "text": "Any update on the tracking API fix? Renewal is coming up and I need to brief the board again."
  },
  {
    "source_type": "gmail",
    "source_native_id": "gmail-msg-9002",
    "occurred_at": "2026-08-16T11:30:00-05:00",
    "from": "carlos.it@meridian.com",
    "text": "Heard about the API issues from Ana — is there a workaround?"
  },
  {
    "source_type": "zendesk",
    "source_native_id": "zendesk-456-reopened-3rd",
    "occurred_at": "2026-08-15T08:00:00-05:00",
    "reporter": "support-desk@meridian.zendesk.com",
    "ticket_number": 456,
    "title": "Slow API response",
    "reopen_count": 3,
    "product_area": "tracking_api",
    "state": "reopened"
  },
  {
    "source_type": "zendesk",
    "source_native_id": "zendesk-600-resolved",
    "occurred_at": "2026-08-16T09:00:00-05:00",
    "reporter": "support-desk@meridian.zendesk.com",
    "ticket_number": 600,
    "title": "Cannot login from mobile",
    "product_area": "reporting",
    "state": "resolved"
  },
  {
    "source_type": "warehouse",
    "source_native_id": "usage-tracking_api-w35",
    "occurred_at": "2026-08-19T00:00:00-05:00",
    "metric": "weekly_active_usage",
    "product_area": "tracking_api",
    "value_delta_pct": -28
  },
  {
    "source_type": "csat",
    "source_native_id": "csat-resp-2300",
    "occurred_at": "2026-08-17T12:00:00-05:00",
    "respondent": "ana.reyes@meridian.com",
    "score": 5,
    "comment": "Still waiting on the API fix, this is getting hard to defend internally."
  },
  {
    "source_type": "slack",
    "source_native_id": "slack-msg-4600",
    "occurred_at": "2026-08-18T10:00:00-05:00",
    "from": "diego@meridian.com",
    "text": "back from leave — checking in on the tracking_api incident, where are we?"
  },
  {
    "source_type": "calendar",
    "source_native_id": "calendar-series-qbr-2026w34",
    "occurred_at": "2026-08-18T15:00:00-05:00",
    "attendee": "ana.reyes@meridian.com",
    "series_id": "meridian-qbr",
    "consent_documented": true,
    "transcript": "Ana: The API reliability is now a board-level concern. Diego: Engineering is prioritizing the root cause fix, ETA end of next week."
  }
]
```

Qué ejercita cada uno:
- `gmail-msg-9001` → Tone (Ana, "board"/"renewal") + Intent (escalation language)
- `gmail-msg-9002` → identidad **unresolved** (carlos.it@meridian.com no está en el perfil — prueba REQ-M1-05)
- `zendesk-456-reopened-3rd` → Recurrence (3er reopen) + Commitment (sigue overdue)
- `zendesk-600-resolved` → Commitment positivo (resuelto rápido)
- `usage-tracking_api-w35` → Usage deviation (-28%)
- `csat-resp-2300` → CSAT deviation (6→5)
- `slack-msg-4600` → Relationship/Absence (Diego vuelve tras ausencia)
- `calendar-...-w34` → Meeting reader (consent true, transcript con compromiso verbal)

### 2. Reglas a respetar al autorar eventos

- **`source_native_id` únicos** — la idempotency key es `hash(source_type, source_native_id)` (`use_cases.py:382`). Repetir un ID → se cuenta como duplicado y se salta.
- **`from`/`respondent`/`attendee`** → `ana.reyes@meridian.com` o `diego@meridian.com` (resueltos) o uno nuevo (unresolved, válido). El sistema **nunca adivina** (REQ-M1-05).
- **`product_area`** → `tracking_api` o `reporting` (de `demo/client-profile.yaml`); cualquier otro se ignora.
- **Frases marcadoras** que disparan redacción (`use_cases.py:219-222`): "legal team", "contract dispute", "lawsuit" → `legal_threads`; "discount", "renewal price", "contract terms", "negotiat" → `commercial_negotiation`. Úsalas a propósito para probar redacción, o evítalas si no quieres que el body quede `[REDACTED]`.
- **Calendar** sin `consent_documented: true` se descarta antes del ledger (`simulated_collector.py:168-172`).
- **Orden** — no importa; `fetch()` ordena por `occurred_at` antes de append (requisito del hash chain).

### 3. Apuntar el colector al fixture nuevo

En `.env` (junto a `demo/`):

```
COLLECTOR_FIXTURE_PATH=./demo/fixtures/meridian-extra.json
```

O inyectarlo solo al correr el script (sin tocar `.env`):

```bash
docker compose exec -e COLLECTOR_FIXTURE_PATH=./demo/fixtures/meridian-extra.json api \
  python scripts/run_collector.py --source simulated
```

Nota: `run_collector.py:46-49` pasa `window_start=window_end=now` — la ventana es no-op; `SimulatedCollector.fetch()` la ignora y devuelve todos los items del archivo. Lo que importa son los `occurred_at` del JSON.

### 4. Decidir: DB limpia o acumular

- **Acumular sobre la corrida existente**: los eventos nuevos se append al ledger junto a los de `meridian-week.json` ya ingeridos (idempotency los separa por `source_native_id`). El score refleja la historia combinada. Más realista.
- **DB limpia**: `docker compose down -v && docker compose up -d --build`, luego `python scripts/seed.py`, luego corres solo el fixture nuevo. Más reproducible.

### 5. Ejecutar el pipeline completo

```bash
# Ingesta + append al ledger + replay (rebuilds response_pairs/event_threads)
docker compose exec api python scripts/run_collector.py --source simulated

# SOLO si quieres que Tone dispare: confirma baseline con >=5 mensajes de Ana
# en una ventana de 60 días (REQ-M6-CAL-04). El fixture extra aporta más samples.
docker compose exec api python scripts/confirm_baseline.py --stakeholder ana \
  --metric email_style --window-days 60

# 8 readers + validation gate
docker compose exec api python scripts/run_readers.py

# Scoring (corre 2x para que la banda asiente con hysteresis)
docker compose exec api python scripts/compute_score.py
docker compose exec api python scripts/compute_score.py

# Narrador (explicación con fact-check)
docker compose exec api python scripts/run_narrator.py
```

Requisitos previos ya cubiertos por el README: `OPENAI_API_KEY` (Recurrence) y `ANTHROPIC_API_KEY` (Tone/Intent/Narrator) en `.env`.

### 6. Verificar

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"marta","password":"agentic-demo-2026"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# Dashboard (score, contribuciones, narrator)
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/dashboard | python3 -m json.tool

# Coverage (cuántas fuentes, cuántos findings en quarantine)
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/coverage | python3 -m json.tool

# Pregunta al ask agent
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"question":"why did the score go up?"}' http://localhost:8000/api/ask | python3 -m json.tool
```

Y a nivel DB, para ver los eventos nuevos realmente appendados:

```bash
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "SELECT id, event_type, occurred_at, stakeholder_id, product_area_id FROM events ORDER BY occurred_at DESC LIMIT 20;"
```

### 7. Caveat sobre el walkthrough/seed/fixture sync

`demo/03-environment-and-fixtures-checklist.md` documenta que el escenario canónico (`examples/01-end-to-end-walkthrough.md`), `data-base/11-seed-data.sql` y `demo/fixtures/meridian-week.json` se regeneran juntos. **Tu fixture nuevo es para prueba/experimentación, no parte del escenario canónico** — por eso lo mantenemos como archivo separado y no tocamos `meridian-week.json` ni el seed. Así los golden/unit tests siguen verdes y no rompes la consistencia documentada.

---

¿Quieres que proceda a crear `demo/fixtures/meridian-extra.json` con los eventos de ejemplo de arriba, o prefieres ajustar el contenido (más eventos, otro cliente, scores distintos) antes de que lo escriba?

---

## User

me puedes explicar sobre la ventana de 60 dias, y cual es significado y que valor ideal deberia usar para una demo impactante. Otra pregunta es necesario aplicar cada uno de los scripts? readers, compute_score, y run_narrator, acaso el proceso no es automatico?

---

## Assistant (Plan · GLM-5.2 · 10.5s)

Buena pregunta, ambas cosas merecen aclararse. Déjame investigar a fondo antes de responder.

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant (Plan · GLM-5.2 · 4.0s)

Déjame verificar el Tone reader y el main.py para entender qué es automático vs manual.

**Tool: read**

**Tool: grep**

---

## Assistant (Plan · GLM-5.2 · 4.0s)

**Tool: grep**

**Tool: read**

---

## Assistant (Plan · GLM-5.2 · 2.8s)

**Tool: grep**

---

## Assistant (Plan · GLM-5.2 · 2.6s)

**Tool: read**

---

## Assistant (Plan · GLM-5.2 · 39.8s)

**Tool: grep**

**Tool: grep**

---

## Assistant (Plan · GLM-5.2 · 49.4s)

Tengo todo lo necesario. Te respondo ambas preguntas con detalle.

---

## Pregunta 1 — La ventana de 60 días (`--window-days`)

### Qué significa exactamente

El script `confirm_baseline.py:48-49` hace:

```python
window_end = datetime.now(UTC)
window_start = window_end - timedelta(days=window_days)
```

Y inserta una fila en `baseline_confirmations` con esa ventana. Esa fila es la **"foto congelada de cómo escribe Ana cuando todo está bien"** — la que el Tone reader usa como comparador (principio P7: "contexto sobre sentimiento", nunca una escala universal).

Cuando luego corre `ToneReader.interpret()` (`tone_reader.py:78-89`):

1. Lee la confirmación más reciente para ese stakeholder.
2. Recolecta todos los mensajes de Ana con `occurred_at` **dentro** de `[window_start, window_end]` → son las **muestras de baseline** (su "normal").
3. Si hay **menos de 5** muestras → se abstiene (`REQ-M6-CAL-04`, "no history, no opinion"). No llama al modelo.
4. Los mensajes de Ana con `occurred_at` **posterior a** `window_end` → son **candidatos** a evaluar (el mensaje nuevo/concerning).
5. Para cada candidato, le pasa al LLM los samples del baseline + el mensaje nuevo y pregunta "¿esto se desvía del estilo propio de Ana?".

### El valor ideal para una demo impactante

Aquí está el detalle crítico que descubrí leyendo el fixture actual. En `meridian-week.json`, los mensajes de Ana que cuentan para Tone (`gmail` + `slack`, que mapean a `event_type='message'`) son **solo 3**:

| id | fecha | texto |
|---|---|---|
| `gmail-msg-8831` | 2026-08-10 | "Please advise on the timeline..." |
| `slack-msg-4502` | 2026-08-12 | "thanks for the quick turnaround..." |
| `gmail-msg-8845` | 2026-08-13 | "Separately — I'm forwarding the contract dispute..." |

**3 < 5 → Tone se abstiene para Ana con el fixture actual.** No va a disparar nunca, sin importar el `--window-days`. Esa es la razón por la que el runbook del demo (`demo/03-environment-and-fixtures-checklist.md:6-7`) habla de "4–6 semanas de historia health" pre-seeded: el fixture canónico está pensado para el walkthrough en prosa, no para hacer disparar Tone en vivo.

Para una demo impactante donde **Tone realmente dispare y el score se mueva**, necesitas:

1. **≥ 5 mensajes "sanos" de Ana** con `occurred_at` **dentro** de la ventana (el baseline).
2. **1 mensaje "concerning" de Ana** con `occurred_at` **después de** `window_end` (el candidato). Tiene que ser posterior a `window_end = datetime.now()` en el momento de correr `confirm_baseline`.

### Valor recomendado y plan de fechas

**`--window-days 45`** (recomendado) o **`60`** (más holgado). La diferencia práctica:

| `--window-days` | `window_start` (desde hoy 2026-08-17) | Cuántos mensajes sanos你需要 sembrar en ese rango |
|---|---|---|
| 30 | 2026-07-18 | 5+ mensajes entre jul-18 y ago-17 (3 semanas densas) |
| **45** | **2026-07-03** | **5+ mensajes entre jul-03 y ago-17 (6 semanas — calza con el runbook's "4–6 weeks")** |
| 60 | 2026-06-18 | 5+ mensajes entre jun-18 y ago-17 (más margen, pero incluye más historia) |

Yo te recomiendo **45 días** porque:
- Calza exactamente con la recomendación del runbook ("4–6 weeks of healthy history").
- Te da margen cómodo para sembrar 6 mensajes sanos espaciados (uno cada ~3 días) sin tener que apretarlos.
- No es tan ancho que capture ruido viejo irrelevante.

### Diseño concreto del fixture para que Tone dispare

Para que la demo sea impactante, el fixture nuevo (`meridian-extra.json`) debería tener:

**6 mensajes "sanos" de Ana** (estilo normal: con saludo, longitud media, tono colaborativo) con `occurred_at` distribuidos en los últimos 45 días, todos **anteriores a `window_end`**. Ejemplo de muestras realistas:

```
2026-07-07T10:00 — "Hi team, quick check-in on the tracking API roadmap — happy with the direction so far."
2026-07-14T11:00 — "Thanks for the update on ticket #398. The CSV export will unblock our reporting pipeline."
2026-07-24T09:30 — "Hi — looping in Diego on the integration questions, he'll follow up from his side."
2026-08-01T14:00 — "Quick note: the weekly sync was useful. Let's keep the cadence."
2026-08-08T10:15 — "Hi team, any news on the reporting roadmap? No rush, just planning our quarter."
2026-08-14T16:00 — "Thanks for the heads up on the deployment window, that works for us."
```

**1 mensaje "concerning" de Ana** con `occurred_at` **POSTERIOR a `window_end`** (es decir, posterior al momento en que corras `confirm_baseline`). Este es el que va a hacer disparar Tone + Intent:

```
2026-08-17T09:14 — "Need an update on the tracking API fix today. Renewal is coming up and I need to brief the board Thursday."   ← corto, sin saludo, menciona "board" y "renewal"
```

### Secuencia de ejecución para que calce

El orden importa porque `window_end = now` al momento de correr `confirm_baseline`:

1. `run_collector.py` — ingesta los 6 mensajes sanos (fechas pasadas) Y el mensaje concerning (fecha = hoy, pero **antes** de correr confirm_baseline, cae dentro de la ventana → MALO, se vuelve baseline).

Para evitar esto, **la forma limpia es de dos pasos**:

```bash
# Paso 1: fixture con SOLO los 6 mensajes sanos (fechas pasadas)
COLLECTOR_FIXTURE_PATH=./demo/fixtures/meridian-healthy-baseline.json \
  docker compose exec api python scripts/run_collector.py --source simulated

# Paso 2: confirma la ventana (window_end = ahora, captura los 6 como baseline)
docker compose exec api python scripts/confirm_baseline.py --stakeholder ana \
  --metric email_style --window-days 45

# Paso 3: ahora sí, añade el mensaje concerning al fixture y vuelve a correr
# (idempotency key distinto → solo se appenda el nuevo)
COLLECTOR_FIXTURE_PATH=./demo/fixtures/meridian-concerning.json \
  docker compose exec api python scripts/run_collector.py --source simulated

# Paso 4: readers — Tone ahora dispara sobre el mensaje concerning
docker compose exec api python scripts/run_readers.py
```

El paso 3 funciona porque `RunCollectorUseCase` salta los 6 ya ingeridos por su idempotency key (`use_cases.py:382-384`) y solo appenda el nuevo. Esto te da un demo narrativa limpia: "así escribe Ana normalmente" → lock-in → "y hoy llegó esto".

**Alternativa más simple (un solo fixture, pero con fecha futura):** pon el mensaje concerning con `occurred_at` un minuto después del momento planificado para correr `confirm_baseline`. Funciona pero narrativamente es raro ("Ana envió un email en el futuro"). No la recomiendo para demo en vivo.

---

## Pregunta 2 — ¿Es automático o hay que correr cada script?

**No es automático.** Lo verifiqué en el código. El `worker.py` (APScheduler) solo agenda **tres** jobs:

| Job | Trigger | Cadencia | Script manual equivalente |
|---|---|---|---|
| `_run_absence_detection` | `hourly_heartbeat` | cada 1h | — (automático) |
| `_run_score_recompute` | `hourly_heartbeat` | cada 1h | `compute_score.py` (manual) |
| `_run_retention` | daily | cada 24h | — (automático) |

**Lo que NO está agendado** y **solo se dispara manualmente** via scripts:

| Paso | Script | ¿Automático? |
|---|---|---|
| Ingesta (collector → ledger) | `run_collector.py` | **No** — manual únicamente. No hay webhook ni scheduler para `SimulatedCollector`. |
| Confirmar baseline | `confirm_baseline.py` | **No** — manual (no hay UI de Profile Editor aún, es Post-MVP). |
| Readers (8 interpretadores → findings) | `run_readers.py` | **No** — manual. `RunReadersUseCase` no se invoca desde ningún route ni scheduler. |
| Scoring | `compute_score.py` | **Sí, pero cada 1 hora** vía heartbeat. Manual para demo (inmediato). |
| Narrator | `run_narrator.py` | **No** — manual. `NarrateScoreRunUseCase` no tiene route ni scheduler. |

### Por qué es así (no es un bug, es el diseño)

El código lo deja claro en los docstrings:

- `run_collector.py:1-6`: *"SimulatedCollector triggered by a script, not a route or a timer"* — decisión explícita de research.md.
- `run_narrator.py` (mismo patrón): *"a separate manual script, mirroring compute_score.py/run_readers.py — no live/chained trigger path exists yet anywhere in this pipeline"*.

La arquitectura está diseñada para que los triggers reales en producción sean: webhooks de Gmail/Zendesk (ingesta), `new_event`/`burst_batch`/`urgent_fast_path` (scoring al instante, no hourly), `profile_edit_replay`/`weight_edit_replay` (tras editar perfil/pesos). Pero como `SimulatedCollector` es un stand-in sin webhook, **en este repo todo el upstream es manual**.

### Qué significa para tu demo

**Sí, tienes que correr los tres scripts en orden.** No hay forma de evitarlo con el código actual. La secuencia completa es:

```
run_collector.py          ← ingesta + append al ledger + replay projections
  ↓ (solo si quieres Tone): confirm_baseline.py
run_readers.py            ← 8 readers + validation gate → findings
  ↓
compute_score.py          ← scoring (corre 2x para que la banda asiente con hysteresis)
  ↓
run_narrator.py           ← explicación fact-checked
```

Lo único que te podrías ahorrar es `compute_score.py` si estás dispuesto a esperar hasta 1 hora al heartbeat del worker — pero para una demo obviamente no querrás eso. Y `run_narrator.py` no tiene atajo: sin él, el dashboard muestra el score pero sin headline/reasons/actions (`narrator_outputs` queda vacío).

### Atajo: encadenarlos en un solo comando

Para no escribir 4 comandos a mano cada vez, podrías encadenarlos (esto es solo lectura/plan, no lo voy a ejecutar):

```bash
docker compose exec api bash -c '
  python scripts/run_collector.py --source simulated && \
  python scripts/confirm_baseline.py --stakeholder ana --metric email_style --window-days 45 && \
  python scripts/run_readers.py && \
  python scripts/compute_score.py && \
  python scripts/compute_score.py && \
  python scripts/run_narrator.py
'
```

`compute_score.py` dos veces es intencional: la primera crea el `score_run`, la segunda confirma la banda (regla de 2-runs-consecutivos de `REQ-M6-CAL-07`/`sequences/06-state-band-hysteresis.md`).

---

## Resumen accionable para tu demo

1. **`--window-days 45`** es el valor ideal — calza con el runbook y da margen para 6 mensajes sanos.
2. **Necesitas sembrar 6 mensajes sanos de Ana** con fechas en los últimos 45 días (el fixture actual solo tiene 3 → Tone se abstiene siempre).
3. **El mensaje concerning debe tener `occurred_at` posterior a `window_end`** → por eso el flujo limpio es de dos pasos (healthy primero, lock baseline, concerning después).
4. **Sí, hay que correr los 4-5 scripts manualmente** — ingestion, readers, narrator no están automatizados; solo score-recompute y absence lo están (hora/día).

¿Quieres que prepare el plan de implementación con los dos archivos fixture (`meridian-healthy-baseline.json` + `meridian-concerning.json`) y los comandos encadenados, o prefieres un solo fixture con la fecha futura del mensaje concerning (más simple, menos narrativo)?

---

## User

ok quiero un plan para preparar y tener un demo con datos muy aparte, datos reales osea que tenga contenido real, pero con personas y empresa ficticia. una ventana de 45 dias, datos cargados en esa ventana de 45 dias, luego gran ingesta de datos para que se pueda probar todas las caracteristidas de la aplicacion. un plan e instrucciones para ejecutar todo la ingesta de inicio a fin.

---

## Assistant (Plan · GLM-5.2 · 235.9s)

Voy a investigar a fondo los detalles técnicos necesarios para diseñar un plan sólido: umbrales de cada reader, cómo se carga un perfil nuevo, y la data semilla. Estoy en modo plan (solo lectura).

**Tool: task**

**Tool: task**

---

## Assistant (Plan · GLM-5.2 · 79.4s)

---

## User

puedes continuar 

---

## Assistant (Plan · GLM-5.2 · 223.3s)

Tengo toda la investigación que necesito. Déjame verificar un par de detalles finales sobre los horarios laborales y el `commitment_lookup` antes de presentarte el plan completo.

**Tool: grep**

**Tool: read**

---

## Assistant (Plan · GLM-5.2 · 69.9s)

Confirmado: `last_contact_at()` es `SELECT MAX(occurred_at) FROM events WHERE event_type != 'absence'` — **global, no per-stakeholder**. Esto valida que la ingesta debe ser en dos etapas para que el absence collector dispare. Ahora tengo todo verificado. Aquí está el plan completo.

---

# Plan: Demo completo con cliente ficticio "Norte Carga"

## 0. Diseño del cliente ficticio

**Empresa:** Norte Carga (logística de carga) — contenido realista del dominio, personas y empresa ficticias.

| Campo | Valor |
|---|---|
| Cliente | Norte Carga |
| Renewal | 2026-11-15 |
| Contract band | strategic |
| Working hours | 08:00-18:00, America/Bogota |
| Languages | es, en |
| Norms | Directos. La brevedad es habitual, no hostil. |
| Exclusions | legal_threads, commercial_negotiation |

**Stakeholders:**

| external_id | Nombre | Rol | Influence | Multiplicador | signs_renewal | Email |
|---|---|---|---|---|---|---|
| `stk_lucia` | Lucía Vargas | CTO | sponsor | 1.6x | sí | lucia.vargas@nortecarga.com |
| `stk_pablo` | Pablo Herrera | Dev lead | daily_user | 1.2x | no | pablo.herrera@nortecarga.com |

**Product areas:**

| Key | Criticality | Multiplicador |
|---|---|---|
| `routing_engine` | critical | 1.5x |
| `billing` | standard | 1.0x |

**Commitments:**
- `first_response`, P1, 4 business hours
- `recurring_sync`, weekly (cadencia 7 días → alimenta el absence collector)

## 1. Archivos a crear (sin tocar archivos canónicos)

| Archivo | Propósito |
|---|---|
| `demo/norte-carga-profile.yaml` | Perfil del cliente ficticio (formato idéntico a `client-profile.yaml`) |
| `demo/fixtures/norte-carga-healthy.json` | Eventos "sanos" de 45 días (baseline) |
| `demo/fixtures/norte-carga-concerning.json` | Eventos concernientes ("gran ingesta") |

**No se modifica** `data-base/11-seed-data.sql`, `demo/client-profile.yaml`, ni `demo/fixtures/meridian-week.json`. Los tests canónicos quedan intactos.

## 2. Estrategia de carga del perfil

El seed SQL (`scripts/seed.py`) es la única fuente de `users`, `finding_type_config`, `playbook_actions`, y `sources` — y todo eso es genérico (no client-specific). El flujo:

1. **Seed** con el SQL canónico → carga infraestructura + perfil Meridian como v1
2. **POST /api/profile/reload** con `CLIENT_PROFILE_PATH` apuntando al nuevo YAML → crea perfil Norte Carga como v2 (Meridian v1 queda no-current)
3. **SQL cosmético** → renombra `sources.display_name` de "Meridian" a "Norte Carga"
4. La resolución de identidad funciona automáticamente: los emails `@nortecarga.com` no están en `identity_map` → fallback a `stakeholders.identifiers` del perfil current (v2) → match exacto → `resolved_by = exact_match`

## 3. Fixture "healthy" — ventana de 45 días (base para todos los readers)

**Principio clave:** cada reader necesita historia para poder detectar desviación. El fixture healthy construye ese historio.

| # | source_type | Fecha | Contenido | Reader que alimenta |
|---|---|---|---|---|
| 1 | gmail | Jul 3, 10:00 | Lucía: "Hi team, checking in on the routing engine roadmap. Happy with the progress so far." | Tone baseline (sample 1/6) |
| 2 | gmail | Jul 10, 11:00 | Lucía: "Thanks for the update on ticket #201. The fix unblocked our dispatch pipeline." | Tone baseline (2/6) |
| 3 | gmail | Jul 17, 09:30 | Lucía: "Quick note — the weekly sync was productive. Let's keep the cadence going." | Tone baseline (3/6) |
| 4 | gmail | Jul 24, 14:00 | Lucía: "Hi — looping in Pablo on the integration questions, he'll follow up from his side." | Tone baseline (4/6) |
| 5 | gmail | Jul 31, 10:15 | Lucía: "Any news on the billing module roadmap? No rush, just planning our quarter." | Tone baseline (5/6) |
| 6 | gmail | Aug 7, 16:00 | Lucía: "Thanks for the heads up on the deployment window, that works for us." | Tone baseline (6/6) — **último contacto antes del silencio** |
| 7-14 | warehouse | Jun 7, Jul 2 (8 mediciones semanales domingos) | routing_engine: +1, -2, +3, -1, +2, 0, -1, +1 | Usage z-score baseline (8 históricos) |
| 15 | csat | Jul 10, 12:00 | Lucía score 9, sin comentario | CSAT z-score baseline (1/3) |
| 16 | csat | Jul 24, 12:00 | Lucía score 9 | CSAT baseline (2/3) |
| 17 | csat | Aug 7, 12:00 | Lucía score 8 | CSAT baseline (3/3) |
| 18 | slack | Jul 15, 10:00 | Pablo: "checking the routing_engine integration, all looking good on our side" | Relationship (Pablo activo) |
| 19 | slack | Jul 18, 11:00 | Pablo: "quick one — the billing export job ran clean overnight" | Relationship — **último evento de Pablo (silencio de 30 días después)** |
| 20 | zendesk | Jul 9, 09:00 | ticket #201 "routing_engine slow response" created | Commitment (abre par) + Recurrence (semilla para clustering) |
| 21 | zendesk | Jul 9, 11:00 | ticket #201 resolved (2 business hours) | Commitment → `commitment_met` (2h ≤ 2h = 0.5 × 4h) |
| 22 | zendesk | Jul 20, 10:00 | ticket #202 "billing export format" created | Commitment (abre par) |
| 23 | zendesk | Jul 20, 13:00 | ticket #202 resolved (3 business hours) | Commitment → `commitment_met` |
| 24 | calendar | Jul 17, 15:00 | QBR transcript (consent=true): "Lucía: routing engine roadmap on track. Pablo: integration testing next week." | Meeting → `meeting_commitment` |

**Totales:** 24 eventos. Lucía tiene 6 mensajes en la ventana (≥5 req. por REQ-M6-CAL-04). Warehouse tiene 8 históricos (≥3 req. por z-score). CSAT tiene 3 históricos (≥3 req.). Pablo tiene 2 eventos en julio (activo), luego silencio.

## 4. Fixture "concerning" — la gran ingesta (dispara los 8 readers)

**Cronología:** ticket reopened Aug 14 (para que esté claramente overdue), emails y otros Aug 17. Todo posterior a `window_end` del baseline (Aug 14 23:59:59).

| # | source_type | Fecha | Contenido | Reader + finding_type |
|---|---|---|---|---|
| 1 | zendesk | Aug 14, 08:00 | ticket #201 "routing_engine slow response" reopened | **Commitment** → `broken_response_promise` (3 business days > 4h → overdue) + **Recurrence** → `recurring_issue` (mismo título que Jul 9, embedding distance ~0 → cluster) |
| 2 | warehouse | Aug 17, 00:00 | routing_engine -22% | **Usage** → `usage_deviation` (z-score contra 8 históricos: \|z\| >> 2.0) |
| 3 | gmail | Aug 17, 09:14 | Lucía: "Need an update on the routing engine fix today. Board briefing Thursday." (terse, sin saludo) | **Tone** → `tone_deterioration` (desviación vs baseline de 6 mensajes) + **Intent** → `escalation_language` ("board") |
| 4 | gmail | Aug 17, 10:00 | Lucía: "Looking at AcmeLog as an alternative — can we discuss roadmap commitments?" | **Intent** → `competitive_mention` ("AcmeLog" competitor) |
| 5 | gmail | Aug 17, 10:30 | Lucía: "Contract terms for renewal need discussion before we commit further." | **Intent** → `contractual_reference` ("contract terms", "renewal") |
| 6 | csat | Aug 17, 12:00 | Lucía score 6, comment: "Support has been slower, and the reopened ticket is affecting our dispatch operations." | **Usage** → `csat_deviation` (6 vs históricos 9,9,8 → \|z\| > 2.0) |
| 7 | zendesk | Aug 17, 11:00 | ticket #204 "billing export format" created | Commitment (abre par) |
| 8 | zendesk | Aug 17, 12:00 | ticket #204 resolved (1 business hour) | **Commitment** → `commitment_met` (1h ≤ 2h) |
| 9 | calendar | Aug 17, 15:00 | QBR transcript (consent=true): "Lucía: We need the routing engine fix before the board review. Pablo: Engineering will prioritize the root cause, ETA end of next week." | **Meeting** → `meeting_commitment` |

**Totales:** 9 eventos. Dispara: Tone ✓, Intent ✓ (3 findings), Commitment ✓ (broken + met), Recurrence ✓, Usage ✓ (warehouse), CSAT ✓, Meeting ✓.

**Absence** se dispara **entre etapas** (ver §5): después del healthy, antes del concerning. El `last_contact_at()` global = Aug 7 → `window_start = Aug 17 - 7d = Aug 10` → `Aug 7 < Aug 10` → absence event creado → `contact_absence` finding ✓.

**Relationship** se dispara con Pablo: último evento Jul 18 → `since = Aug 17 - 28d = Jul 20` → Pablo no activo desde Jul 18 < Jul 20 → `relationship_change` ✓.

### Resumen de los 12 finding types cubiertos

| finding_type | Se dispara con | base_points |
|---|---|---|
| `tone_deterioration` | Email terse de Lucía | 10 |
| `escalation_language` | "Board briefing Thursday" | 14 |
| `competitive_mention` | "AcmeLog as an alternative" | 14 |
| `contractual_reference` | "Contract terms for renewal" | 14 |
| `broken_response_promise` | Ticket #201 reopen overdue | 20 |
| `commitment_met` | Ticket #204 resuelto en 1h | 10 (positivo) |
| `recurring_issue` | #201 mismo título cluster | 12 |
| `usage_deviation` | routing_engine -22% | 15 |
| `csat_deviation` | Score 6 vs 9,9,8 | 10 |
| `contact_absence` | Silencio del 7-17 Aug | 12 |
| `relationship_change` | Pablo inactivo 30 días | 8 |
| `meeting_commitment` | Transcript QBR Aug 17 | 10 |

Los 12 finding types del `finding_type_config` seed se ejercitan. 5 de ellos tienen `playbook_actions` (broken_response_promise, escalation_language, contact_absence, usage_deviation, csat_deviation) → el narrador y draft composer tendrán templates que renderizar.

## 5. Secuencia de ejecución completa (inicio a fin)

```bash
# ═══════════════════════════════════════════════
# FASE 0 — Reset e infraestructura
# ═══════════════════════════════════════════════
docker compose down -v && docker compose up -d --build

# Verificar que api/db/worker/web están healthy
docker compose ps

# Crear la encryption key (si no existe)
mkdir -p secrets
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > secrets/data.key
docker compose restart api worker

# Configurar API keys en .env (si no están)
# OPENAI_API_KEY=sk-...      (Recurrence reader embeddings)
# ANTHROPIC_API_KEY=sk-ant-... (Tone/Intent/Meeting readers + Narrator)
echo "CLIENT_PROFILE_PATH=./demo/norte-carga-profile.yaml" >> .env
docker compose restart api worker

# ═══════════════════════════════════════════════
# FASE 1 — Seed + cargar perfil Norte Carga
# ═══════════════════════════════════════════════
docker compose exec api python scripts/seed.py

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"marta","password":"agentic-demo-2026"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# Cargar perfil Norte Carga (crea v2, Meridian v1 → non-current)
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/profile/reload | python3 -m json.tool

# Cosmético: renombrar sources
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
  "UPDATE sources SET display_name = REPLACE(display_name, 'Meridian', 'Norte Carga');"

# ═══════════════════════════════════════════════
# FASE 2 — Etapa 1: ingesta healthy (45 días)
# ═══════════════════════════════════════════════
docker compose exec -e COLLECTOR_FIXTURE_PATH=./demo/fixtures/norte-carga-healthy.json \
  api python scripts/run_collector.py --source simulated

# Confirmar baseline Tone con ventana fija (Jul 3 – Aug 14)
# window_end = Aug 14 23:59:59 → los eventos concernientes (Aug 14+) quedan fuera
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
INSERT INTO baseline_confirmations
  (subject_type, subject_id, metric, window_start, window_end, confirmed_by_user_id)
SELECT 'stakeholder'::rollup_subject_type, s.id, 'email_style',
  '2026-07-03T00:00:00+00:00'::timestamptz,
  '2026-08-14T23:59:59+00:00'::timestamptz,
  '00000000-0000-0000-0000-000000000001'::uuid
FROM stakeholders s
JOIN client_profile_versions pv ON pv.id = s.profile_version_id
WHERE pv.is_current AND s.external_id = 'stk_lucia';"

# Run absence collector — last_contact = Aug 7, window_start = Aug 10
# Aug 7 < Aug 10 → absence event fires ✓
docker compose exec api python -m app.worker --run-once absence

# Run readers (primera pasada — estado "healthy-ish")
# Esperado: commitment_met x2, contact_absence x1, relationship_change x1,
#           meeting_commitment x1. Tone abstiene (sin candidatos post-window_end).
docker compose exec api python scripts/run_readers.py

# ═══════════════════════════════════════════════
# FASE 3 — Etapa 2: gran ingesta de eventos concernientes
# ═══════════════════════════════════════════════
docker compose exec -e COLLECTOR_FIXTURE_PATH=./demo/fixtures/norte-carga-concerning.json \
  api python scripts/run_collector.py --source simulated

# Run readers (segunda pasada — todos los readers disparan)
# Esperado: tone_deterioration, escalation_language, competitive_mention,
#           contractual_reference, broken_response_promise, commitment_met,
#           recurring_issue, usage_deviation, csat_deviation, meeting_commitment
docker compose exec api python scripts/run_readers.py

# ═══════════════════════════════════════════════
# FASE 4 — Scoring + Narración
# ═══════════════════════════════════════════════
# Compute score x2 (hysteresis: 2 runs consecutivos para asentar la banda)
docker compose exec api python scripts/compute_score.py
docker compose exec api python scripts/compute_score.py

# Narrador (headline + reasons + actions con playbook templates)
docker compose exec api python scripts/run_narrator.py

# ═══════════════════════════════════════════════
# FASE 5 — Verificación y demo interactivo
# ═══════════════════════════════════════════════
# Dashboard completo
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/dashboard | python3 -m json.tool

# Coverage (fuentes leídas, quarantine)
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/coverage | python3 -m json.tool

# Ask agent
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"question":"why did the score go up?"}' \
  http://localhost:8000/api/ask | python3 -m json.tool

# Draft composer (obtener issue_id y stakeholder_id del dashboard)
# curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
#   -d '{"issue_id":"<id>","stakeholder_id":"<id>","tone_variant":"direct"}' \
#   http://localhost:8000/api/drafts | python3 -m json.tool

# Feedback (marcar un finding como false_alarm)
# curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
#   -d '{"finding_id":"<id>","verdict":"false_alarm"}' \
#   http://localhost:8000/api/feedback
```

## 6. Por qué la ventana es de 45 días y el `window_end` es fijo (Aug 14)

| Parámetro | Valor | Razón |
|---|---|---|
| `window_start` | Jul 3 (hoy - 45d) | Captura los 6 mensajes healthy de Lucía (req. ≥5 por REQ-M6-CAL-04) |
| `window_end` | Aug 14 23:59:59 | **Fijo vía SQL**, no `now()`. Garantiza que los eventos concernientes (Aug 14+) queden después del window_end → son candidatos a evaluar, no baseline |
| ¿Por qué no `confirm_baseline.py --window-days 45`? | Porque ese script setea `window_end = now()`. Si corres el script a las 10:00 y luego ingestas eventos con `occurred_at = 10:30`, funciona. Pero si los timestamps del fixture son fijos (Aug 17 09:14) y corres el script después de esa hora, los eventos quedan dentro del baseline → Tone no dispara. El SQL con window_end fijo elimina esa race condition. |

## 7. Por qué la ingesta es en dos etapas (no todo de una vez)

El `DetectAbsenceUseCase` usa `last_contact_at()` = `SELECT MAX(occurred_at) FROM events WHERE event_type != 'absence'` (`sqlalchemy_repositories.py:532-541`) — **global, no per-stakeholder**. Si ingestas todo de una vez:

- `last_contact` = Aug 17 (eventos concernientes) → `window_start` = Aug 10 → `Aug 17 >= Aug 10` → **no absence** ✗

Con dos etapas:
- **Etapa 1:** ingesta solo healthy (último evento Aug 7) → run absence → `last_contact = Aug 7`, `window_start = Aug 10` → `Aug 7 < Aug 10` → **absence fires** ✓
- **Etapa 2:** ingesta concernientes → run absence otra vez → `last_contact = Aug 17` → no new absence (y el anterior está deduped por idempotency key)

## 8. Prerequisitos de entorno

```bash
# .env debe tener:
OPENAI_API_KEY=sk-...           # Recurrence reader (embeddings text-embedding-3-small)
ANTHROPIC_API_key=sk-ant-...    # Tone/Intent/Meeting + Narrator (claude-haiku-4-5 + claude-sonnet-5)
READER_MODEL_ID=claude-haiku-4-5-20251001
GENERATION_MODEL_ID=claude-sonnet-5
CLIENT_PROFILE_PATH=./demo/norte-carga-profile.yaml
ENCRYPTION_KEY_PATH=./secrets/data.key
```

## 9. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| `confirm_baseline.py` no acepta `--window-end` custom | Usar INSERT SQL directo (pasos FASE 2) |
| `sources.display_name` dice "Meridian" | SQL UPDATE cosmético después del reload |
| Recurrence clustering no agrupa si títulos difieren mucho | Fixture usa títulos idénticos: "routing_engine slow response" en ambos #201 eventos |
| Tone model no detecta desviación | Email concerniente es deliberadamente terse (12 palabras, sin saludo) vs baseline (~15-20 palabras con "Hi") |
| Absence no dispara si hay eventos recientes | Two-stage ingestion: absence corre antes de la ingesta concerniente |
| Pablo's `relationship_change` no dispara si tiene eventos <28 días | Pablo's último evento es Jul 18 (30 días antes de Aug 17) |
| Los 12 findings podrían no agruparse en issues | El scoring engine agrupa por shared_entity o embedding_similarity; la narrativa del demo no depende de un agrupamiento específico |

---

¿Quieres que proceda con la implementación (crear los 3 archivos + verificar que los timestamps calzan con business hours), o quieres ajustar algo del escenario primero (nombres, áreas de producto, contenido de los emails, fechas)?

---

## User

---

## Assistant (Build · GLM-5.2 · 2.6s)

**Tool: bash**

---

## User

---

## Assistant (Build · GLM-5.2 · 1.8s)

**Tool: bash**

---

## User

---

## Assistant (Build · GLM-5.2 · 2.1s)

**Tool: bash**

---

## User

---

## Assistant (Build · GLM-5.2 · 1.9s)

**Tool: bash**

---

## User

---

## Assistant (Build · GLM-5.2 · 2.0s)

**Tool: bash**

---

