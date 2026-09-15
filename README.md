# MIA — Inteligência Artificial Companheira

IA autônoma com memória, emoção, identidade e autoevolução. Construída como
um sistema cognitivo completo: percebe eventos, interpreta com um modelo de
si mesma (self-model), sente, lembra, se relaciona, reflete e evolui
autonomamente.

> **Status atual: 271 testes passando · 26 commits · 31 módulos · Fases 0–16 cobertas**

---

## Como usar

```bash
# Iniciar o REPL (modo chat)
python3 -m mia_pkg.cli

# Rodar a suíte de testes
python3 -m pytest tests/ -q
```

O projeto é uma biblioteca Python (`mia_pkg/`) + CLI (`mia_pkg/cli.py`).
Requires apenas Python 3.10+ e SQLite (stdlib).

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                        Chat / CLI                            │
├─────────────────────────────────────────────────────────────┤
│  Cognitive Core: EVENT → INTERPRET → APPRAISE → FEEL → ACT  │
├──────────────┬──────────────┬──────────────┬────────────────┤
│   Memória    │  Identidade  │   Emoção     │  Social        │
│  MemoryStore │  Self-model  │  Affective   │  Relationships │
│  Retrieval   │  Personality │  Mood/Valence│  Boundaries    │
│  Consolidation│  Authority  │  Governor    │  Limits        │
├──────────────┴──────────────┴──────────────┴────────────────┤
│  Autonomia: Goals · Initiative · Attention · Resource Gov    │
│  Reflexão: Diary · Reflection · Imagination · Beliefs        │
│  Autoevolução: Evolution Engine · Canary · Rollback          │
│  World: Interests · Research · Knowledge Store               │
│  Subagentes: Registry · Orchestrator · kill switch           │
├─────────────────────────────────────────────────────────────┤
│  Estado: State Authority (hash-chain audit) · SQLite         │
│  Segurança: Redactor · Rate Limiter · Integrity · Sandbox    │
│  Monitoria: Health Monitor · Backup/Restore                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Fases implementadas

Cada fase tem seus módulos e testes dedicados. Os commits narram a evolução
com mensagens descritivas — veja `git log --oneline` para o histórico completo.

### Fase 0 — Fundação
Event Bus pub/sub com circuit breaker, State Authority (propose → policy →
validate → apply → audit com hash-chain), Policy Engine determinística
(whitelist de targets, bloqueio de escrita LLM), SQLite com 20 tabelas.

- `mia_pkg/events.py` — EventBus tipado, Event, EventType, circuit breaker
- `mia_pkg/state_authority.py` — escrita única de estado + auditoria
- `mia_pkg/policy_engine.py` — regras determinísticas (whitelist, invariantes)
- `mia_pkg/db.py` — SQLiteConnection, schema 20 tabelas, migrações
- `mia_pkg/runtime.py` — orquestração do runtime
- Commit: `1e121ca`, `fe7b671` (fix revisão), `58595e9` (schema)

### Fase 1 — LLM + Cognitive Core + Context Assembly
Providers substituíveis (LLMProviderChain com fallback/retry/backoff),
pipeline cognitivo completo, assembly de contexto com personalidade e memórias.

- `mia_pkg/llm.py` — ProviderChain, retry com jitter, streaming
- `mia_pkg/cognitive_core.py` — EVENT → INTERPRET → APPRAISE → FEEL → ACT
- `mia_pkg/context_assembly.py` — sistema prompt dinâmico (personalidade + memória)
- `mia_pkg/chat.py` — ChatSession com fallback a regras se LLM indisponível
- Commit: `6ab2b8b`, `ccdf823`

### Fase 2 — Memória
MemoryObject tipado, retrieval por importância, associações, consolidação
de conversas longas, decay e cleanup.

- `mia_pkg/memory.py` — MemoryStore, MemoryObject, RetrievalEngine
- `mia_pkg/consolidation.py` — consolidator + scheduler + associações
- `mia_pkg/attention_policy.py` — ACT/WAIT/IGNORE (seletividade)
- Commit: `6ab2b8b`, `e6d8a61`, `45298cf`

### Fase 3 — Identidade / Self Model / Personalidade
Self-model persistente, personalidade Big Five (traços com ranges validados),
evolução de traços por interações reais (Identity Authority), rate limit
anti-flutuação, transições de personalidade versionadas.

- `mia_pkg/identity.py` — IdentityManager, PersonalityVector, valores
- `mia_pkg/identity_authority.py` — evolução autonômica de personalidade
- Commit: `f48829d`

### Fase 4 — Emoção / Sensação / Mood
Emoções PAD com fuzzy membership, sensações, humor, appraisals, governor
com rate limit (máx 10 mudanças/hora) e evento LONELINESS_CHANGED, mood
temporal por média ponderada das últimas horas.

- `mia_pkg/affective_engine.py` — AffectiveEngine, emotion PAD, sensations
- `mia_pkg/emotion_governor.py` — rate limit + TemporalMoodEngine
- Commit: `23d0048`

### Fase 5 — Relacionamentos / Social / Limites
Pessoas, relacionamentos com confiança/afeto, eventos de relação, limites
de tópico (BoundaryManager), persona "miguel" automática no primeiro contato.

- `mia_pkg/social.py` — PeopleStore, RelationshipStore, BoundaryManager
- Commit: `7ab59e5`

### Fase 6 — Autonomia
Goals com ciclo de vida, Initiative (iniciativa proativa), ResourceGovernor
(limite de ações/turnos), atenção seletiva.

- `mia_pkg/autonomy.py` — GoalStore, Goal, Initiative, ResourceGovernor
- Commit: `7ab59e5`, `6ab2b8b`

### Fase 7 — Reflexão / Diário / Crenças
Diário, reflexões, imaginação (contrafactuais), revisão de crenças por
evidência (confirma/contradiz, auto-revisão, threshold de rejeição).

- `mia_pkg/reflection.py` — Diary, Reflection, Imagination
- `mia_pkg/belief_revision.py` — BeliefRevisionEngine
- `mia_pkg/beliefs.py` — ciclo de vida de crenças
- Commit: `7ab59e5`, `e133348`

### Fase 8 — Security Hardening
Redactor (PII), rate limiter, integridade (hash de módulos), sandbox
de comandos, kill switch.

- `mia_pkg/security.py` — Redactor, RateLimiter, Integrity, Sandbox
- Commit: `7ab59e5`

### Fase 9 — Voz · Fase 10 — Visão · Fase 11 — Avatar · Fase 12 — Nós
Stubs prontos no roadmap (`docs/03_roadmap.md`); dependem de integrações
externas (TTS, câmera, embodied agent, rede) — planejadas, não implementadas
nesta rodada de fundação cognitiva.

### Fase 13 — Subagentes / Orquestração
AgentRegistry com capacidades e role, Orchestrator com delegação por
capability/role, limites de concorrência, kill switch, templates Research/
Code/Social com report estruturado.

- `mia_pkg/agents.py` — AgentRegistry, Orchestrator, SubAgent templates
- Commit: `866d630`

### Fase 14 — World Awareness
InterestTracker (decay + seed por personalidade), RelevanceScorer (threshold
anti-poluição), KnowledgeStore (memórias taggeadas `[knowledge:...]`),
WorldResearchAgent (rate limit + evento RESEARCH_COMPLETED), IdleResearcher
(pesquisa autônoma quando idle).

- `mia_pkg/world.py` — WorldResearchAgent, InterestTracker, KnowledgeStore
- Commit: `e39d923`

### Fase 15 — Autoevolução
EvolutionEngine gera propostas de melhoria, ParameterRegistry com ranges e
parâmetros imunes, CanaryDeployer (snapshot → aplica → health check →
promove/rollback), RollbackManager (restaura automaticamente se health check
falha). Mudanças de código são rejeitadas (MVP: só parâmetros).

- `mia_pkg/evolution.py` — EvolutionEngine, ParameterRegistry, RollbackManager
- Commit: `28fb762`

### Fase 16 — Integração e Monitoria
HealthMonitor (health check das tabelas + latência), component_status
(imports de todos os módulos), BackupManager (backup/restore via SQLite
backup API), testes E2E de fluxo completo: chat → memória → social →
consolidação → autonomia → evolução → subagentes → pesquisa idle.

- `mia_pkg/monitoring.py` — HealthMonitor, BackupManager
- `tests/test_e2e.py` — fluxos E2E integrados
- Commit: próximo push

---

## Testes

| Arquivo | Cobre |
|---------|-------|
| `test_foundation.py` | Fase 0 (36 testes) |
| `test_phase2..16.py` | Fases 2–16 (módulos dedicados) |
| `test_e2e.py` | Integração completa (fluxos E2E) |

Rodar: `python3 -m pytest tests/ -q`

---

## Documentação

| Documento | Conteúdo |
|-----------|----------|
| `docs/01_entendimento.md` | Entendimento arquitetural (P1) |
| `docs/02_especificacao.md` | Especificação técnica 1160 linhas (P3) |
| `docs/03_roadmap.md` | Roadmap 1986 linhas, 17 fases, M0–M10 (P4) |
| `docs/IMPLEMENTATION_STATUS.md` | Tabela de status por módulo |
| `docs/art/` | Concept art e prompts visuais (P2) |
| `docs/debate/` | Debate arquitetural (cético/visionário/segurança) |

---

## Repositório

Git remoto: `origin` → https://github.com/miguzhc012/Mia