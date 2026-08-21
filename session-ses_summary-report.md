# Resumen ejecutivo — Agentic Churn

Plataforma de prevención de churn B2B, **event-sourced** (ledger append-only, bitemporal, con hash-chaining). Arquitectura de 4 tiers, donde **cada tier tiene prohibido hacer el trabajo del siguiente** (principio P3). Tres loops: *Sense* (continuo, recalcula score), *Ask* (bajo demanda, solo explica), *Learning* (humano, ajusta pesos futuros sin tocar scores pasados).

Para probar seguir el manual en el archivo demo-wara/RUNBOOK.md.

Para esta fase los procesos se los ejecuta con comandos scripts.

## Tier 1 · Ingestión — "Meter material al ledger sin interpretarlo"
- Ingesta de datos simulados desde archivos json, y audio de reunión, todo el contenido generado por IA.
- **M1 Signal collectors** — tickets, email, chat, uso, encuestas, reuniones, CRM. Código determinístico (adapters API/webhook).
- **M1a Absence collector** — detecta lo que **no** ocurrió (lo que debería haber pasado y no pasó).
- **M2 Event ledger** — base relacional append-only, bitemporal, hash-chained. Fuente única de verdad y evidencia.

## Tier 2 · Contexto — "La lente que convierte una señal en severidad"
- **M3 Client profile** — personas, prioridades, promesas y multiplicadores del cliente (YAML/DB, humano).
- **M4 Feedback memory** — los veredictos humanos se convierten en pesos de *damping* para futuras corridas.

## Tier 3 · Razonamiento — "Material crudo → número defendible + explicación"
- **M5 Interpreters** — lectores por dimensión:
  - Determinísticos: *Commitment, Usage, Absence, Relationship* (estadística clásica).
  - *Recurrence*: embeddings + clustering (sin llamada generativa).
  - **LLM con output estructurado**: **Tone, Intent, Meeting**.
- **M5a Validation gate** — código determinístico: valida schema, eventos citados, piso de evidencia y piso de confianza. Rechazado → *Quarantine* (nunca se puntúa, pasa a dataset de eval).
- **M6 Scoring engine** — aritmética determinista. **NUNCA llama a un modelo** (principio P2, enforced por CI).
- **M7 Narrator (LLM)** — genera headline, razones y plan de acción en prosa, sobre el score ya calculado.

## Tier 4 · Experiencia — "Mostrar, responder, redactar — nunca calcular"
- **M8 Health dashboard** — UI read-only de lecturas precomputadas.
- **M9 Ask agent (LLM)** — mapea intención del usuario a componente; **explica el score existente, nunca recalcula**.
- **M10 Draft composer (LLM)** — redacta comunicaciones; **sin capacidad de envío** (principio P4: "un humano siempre envía").

## IA/Agentes involucrados (resumen)
| Agente | Tier | Tipo | Qué hace |
|---|---|---|---|
| Tone reader | 3 | LLM | Compara tono contra baseline del stakeholder (P7: contexto, no sentimiento universal) |
| Intent reader | 3 | LLM | Interpreta intención en feedback |
| Meeting reader | 3 | LLM | Extrae compromisos y señales de reuniones |
| Narrator | 3 | LLM | Convierte score numérico en narrativa accionable |
| Ask agent | 4 | LLM | Q&A sobre ledger y score existentes |
| Draft composer | 4 | LLM | Redacta borradores sin enviar |

**Invariantes clave**: cada *finding* cita IDs de eventos reales (evidencia obligatoria, CHECK non-empty); estado degradado se ve distinto del completo (P5); cuenta sana → pantalla casi vacía (P6).

---

¿Quieres que lo formatee en un slide/deck de una sola página, o que lo baje a bullets aún más corto?

---

