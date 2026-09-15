# MIA — MAPA DE CONFORMIDADE + PLANO DE IMPLEMENTAÇÃO

> Gerado: 2026-09-15
> Fontes: onboarding v2, 02_especificacao.md, 03_roadmap.md, mia_pkg/*, tests/*

---

## 1. MAPA DE CONFORMIDADE POR COMPONENTE

| Componente | Spec | Código | Testes | Status |
|-----------|------|--------|--------|--------|
| **Event Bus** | D.1, E.1-E.2 | events.py (153L) | test_foundation.py | IMPLEMENTED |
| **State Authority** | D.6, C.5 | state_authority.py (385L) | test_foundation.py | IMPLEMENTED |
| **Policy Engine** | D.3, C.16 | policy_engine.py (139L) | test_foundation.py | IMPLEMENTED |
| **Memory Store** | D.4, C.6 | memory.py (177L) | test_foundation.py | PARTIALLY_IMPLEMENTED |
| **LLM Abstraction** | D.2, C.2 | llm.py (207L) | test_foundation.py | PARTIALLY_IMPLEMENTED |
| **Runtime** | B.3, C.15 | runtime.py (134L) | test_foundation.py | PARTIALLY_IMPLEMENTED |
| **Database** | F.1-F.2 | db.py (287L) | test_foundation.py | IMPLEMENTED |
| **Config** | — | config.py | — | IMPLEMENTED |
| **Beliefs** | §21 onboarding | beliefs.py (180L) | test_phase2.py | IMPLEMENTED |
| **Needs/Desires** | §16 onboarding | needs_desires.py (184L) | test_phase2.py | IMPLEMENTED |
| **Attention Policy** | §26 onboarding | attention_policy.py (128L) | test_phase2.py | IMPLEMENTED |
| **Cognitive Core** | C.2 | — | — | MISSING |
| **Context Assembly** | — | — | — | MISSING |
| **Affective State Engine** | C.9 | — | — | MISSING |
| **Identity/Personality** | C.1 | — | — | MISSING |
| **Self Model** | C.1 | — | — | MISSING |
| **Autonomy/Planning** | C.10 | — | — | MISSING |
| **Agent Registry** | C.13 | — | — | MISSING |
| **Budget Authority** | C.7 | — | — | MISSING |
| **Trust Boundary** | §51 onboarding | — | — | MISSING |
| **Perception** | C.11 | — | — | MISSING (futuro) |
| **Voice** | C.12 | — | — | MISSING (futuro) |
| **Avatar** | C.14 | — | — | MISSING (futuro) |

---

## 2. CONTRATOS ESPECIFICADOS vs IMPLEMENTADOS

| Contrato | Especificado | Implementado | Gap |
|----------|-------------|-------------|-----|
| D.1 — Eventos | ✅ Spec completo | ✅ EventType + Event dataclass | Campos opcionais faltam (correlation_id, causation_id) |
| D.2 — LLM Interface | ✅ Spec completo | ✅ Stub com generate_context/generate_response | Falta: model routing, fallback, retry |
| D.3 — Permissions | ✅ Spec completo | ✅ PolicyEngine | Falta: TRUST_BOUNDARY check, dynamic permissions |
| D.4 — Memory Object | ✅ Spec completo | ✅ MemoryObject + MemoryStore | Falta: emotional_context, provenance, decay_state (colunas existem mas não são usadas) |
| D.5 — Identity/Personality | ✅ Spec completo | ❌ Não implementado | Tabelas existem (identity_state, personality_state) mas sem módulo |
| D.6 — Emotion State | ✅ Spec completo | ❌ Não implementado | Tabela emotion_state existe mas sem módulo |
| D.7 — State Authority API | ✅ Spec completo | ✅ propose/reject/apply + hash chain | Falta: batch transitions, complex validation |
| D.8 — Tool Definitions | ✅ Spec completo | ❌ Não implementado | Nenhuma tabela ou módulo |

---

## 3. ADRs ENCONTRADOS

| ADR | Título | Status | Localização |
|-----|--------|--------|------------|
| ADR-001 | LLM como componente substituível | Aceito | 02_especificacao.md §B |
| ADR-002 | Eventos como coluna vertebral | Aceito | 02_especificacao.md §E |
| ADR-003 | State Authority determinística | Aceito | 02_especificacao.md §C.5 |
| ADR-004 | LLM não escreve estado diretamente | Aceito | 02_especificacao.md §C.2 |
| ADR-005 | Memória append-only com versionamento | Aceito | 02_especificacao.md §F.2 |
| ADR-006 | Policy Engine para permissões | Aceito | 02_especificacao.md §C.16 |
| ADR-007 | Híbrido: regras + LLM | Aceito | 02_especificacao.md §C.5 |

---

## 4. GAPS IDENTIFICADOS

### BLOCKING (impedem avanço da Fase 1)

| # | Gap | Impacto | Prioridade |
|---|-----|---------|-----------|
| B1 | **Cognitive Core não existe** — não há pipeline PERCEPTION→INTERPRETATION→APPRAISAL→STATE→MEMORY | Sem ele, Mia não processa eventos | CRÍTICO |
| B2 | **Context Assembly não existe** — não monta prompt estruturado para LLM | LLM não recebe contexto adequado | CRÍTICO |
| B3 | **Affective State Engine não existe** — emotion_state table existe mas sem lógica | Estado emocional não evolui | ALTO |
| B4 | **Identity/Personality modules não existem** — tabelas existem sem código | Mia não tem identidade persistente | ALTO |
| B5 | **State Authority não valida transições complexas** — só aplica snapshot | Transições multi-campo falham | ALTO |

### NON-BLOCKING (importante mas não impede Fase 1)

| # | Gap | Impacto | Prioridade |
|---|-----|---------|-----------|
| N1 | Budget Authority não implementado | Consumo sem controle | MÉDIO |
| N2 | Trust Boundary não implementada | Self-modification irrestrito | MÉDIO |
| N3 | Agent Registry não implementado | Sem multi-agent | BAIXO |
| N4 | Tools/Node interface não implementada | Sem ferramentas | BAIXO |
| N5 | DiaryEntry não tem módulo separado | Confundido com memory_objects | BAIXO |
| N6 | EventType incompleto (faltam correlation/causation) | Debugging limitado | BAIXO |
| N7 | LLM abstraction sem model routing/fallback | Sem troca dinâmica | BAIXO |
| N8 | Memory retrieval só keyword (sem embedding) | Recall limitado | BAIXO |

---

## 5. PRÓXIMO INCREMENTO AUTORIZADO

### Fase 1: Cognitive Core + Context Assembly

**Escopo:** Pipeline completo que recebe um evento, interpreta, avalia, transita de estado, e monta contexto para o LLM.

**Componentes a implementar:**

1. **cognitive_core.py** — Pipeline: event → interpretation → appraisal → state transition
2. **context_assembly.py** — Monta prompt estruturado com estado atual + memórias relevantes
3. **affective_engine.py** — Gerencia emoções, mood, sensações com suavização temporal
4. **identity.py** — Self-model, personalidade, valores

**Ordem de implementação:**
1. Affective Engine (precisa existir antes do Cognitive Core)
2. Identity/Personality (precisa existir antes do Context Assembly)
3. Cognitive Core (usa Affective + Identity)
4. Context Assembly (usa todos os anteriores)

**Testes necessários:**
- Unit: cada módulo isolado
- Integration: Cognitive Core → State Authority → Memory
- E2E: Evento → resposta do LLM com contexto adequado

**Critérios de aceitação:**
1. Evento chega → é processado pelo pipeline
2. Estado emocional muda de acordo
3. Contexto é montado corretamente
4. LLM recebe prompt estruturado (não JSON bruto)
5. 57+ testes passando (não quebrar existentes)
6. Nenhuma mudança arquitetural oculta

---

## 6. ORDENÇÃO DAS TABELAS (conforme spec §F.2)

| Tabela | Existe no Schema | Tem Módulo | Tem Testes |
|--------|-----------------|-----------|-----------|
| memory_objects | ✅ | ✅ memory.py | ✅ |
| memory_associations | ✅ | ✅ memory.py | ✅ |
| event_log (events) | ✅ | ✅ events.py | ✅ |
| state_transitions_audit | ✅ | ✅ state_authority.py | ✅ |
| people | ✅ | ❌ | ❌ |
| relationships | ✅ | ❌ | ❌ |
| relationship_events | ✅ | ❌ | ❌ |
| identity_state | ✅ | ❌ | ❌ |
| personality_state | ✅ | ❌ | ❌ |
| emotion_state | ✅ | ❌ | ❌ |
| beliefs | ✅ | ✅ beliefs.py | ✅ |
| sensations | ✅ | ❌ | ❌ |
| needs | ✅ | ✅ needs_desires.py | ✅ |
| desires | ✅ | ✅ needs_desires.py | ✅ |
| goals | ✅ | ❌ | ❌ |
| messages | ✅ | ❌ | ❌ |
| sessions | ✅ | ❌ | ❌ |
| attention_log | ✅ | ✅ attention_policy.py | ✅ |
| diary | ✅ | ❌ | ❌ |

**Resumo:** 20 tabelas, 8 com módulo, 6 com testes.
