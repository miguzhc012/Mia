# MIA — Inteligência Artificial Companheira

IA autônoma com memória, emoção, identidade e autoevolução. Construída como
um sistema cognitivo completo: percebe eventos, interpreta com um modelo de
si mesma (self-model), sente, lembra, se relaciona, reflete e evolui
autonomamente.

> **Status atual: 452 testes passando · 85% cobertura · CI (3.11/3.12) · Fases 0–16 + hardening H1–H26**

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

### Fase 9 — Voz
Voice Pipeline: VAD detecta fala vs. silêncio (energia + janelas + merge),
STT plugável (Whisper/mock), Speaker Recognition (PeopleStore ou profile_fn),
Directed-speech (nome/imperativo/pergunta; conversa de terceiros ignorada),
TTS com prosódia mapeada da emoção (rate/pitch/volume), eventos de áudio
tipados no bus, integração com Cognitive Core (fala dirigida → MIGUEL_SPOKE).

- `mia_pkg/voice.py` — VoicePipeline, VAD, STTEngine, SpeakerRecognizer, TTSEngine
- Commit: Fase 9

### Fase 10 — Visão / Percepção
VisionPipeline (analyze_fn plugável → CAMERA_ACTIVITY_DETECTED,
NEW_PERSON_DETECTED), VisionRateLimiter (budget visual), PerceptionAggregator
(fusão visão+áudio → person_interacting, bidirecional), ContextEnricher
(percepção → contexto do Cognitive Core), privacy (análise local plugável).

- `mia_pkg/perception.py` — VisionPipeline, PerceptionAggregator, ContextEnricher
- Commit: Fase 10

### Fase 11 — Avatar / Embodiment
ExpressionMapper (EmotionVector+MoodState → FacialConfig, thresholds por
baseline), AvatarRenderer SVG cartoon puro (olhos, sobrancelhas, boca, blush),
AvatarSync (reage a STATE_CHANGED via event bus), AvatarAPI
(current_expression / current_svg / save_snapshot).

- `mia_pkg/avatar.py` — ExpressionMapper, AvatarRenderer, AvatarSync, AvatarAPI
- Commit: Fase 11

### Fase 12 — Nós Distribuídos
NodeManager (roles master/client, heartbeat, NODE_ONLINE/OFFLINE),
SyncEngine (snapshot JSON + checksum MD5, apply substitui estado, fila de
eventos offline com serialize/load), OfflineMode (snapshot em disco),
ConflictResolver (master wins; clientes: mais recente).

- `mia_pkg/distributed.py` — NodeManager, SyncEngine, OfflineMode, ConflictResolver
- Commit: Fase 12

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
| `test_foundation.py` | Fase 0 + EventBus/StateAuthority/Security |
| `test_phase2..20.py` | Fases 2–20 (módulos dedicados) |
| `test_e2e.py` + `test_e2e_failure.py` | Integração completa + degradação honesta |
| `test_restart.py` | Persistência entre restart de processo |
| `test_trust.py` | Trust boundary (identidade, kill switch, read-only) |
| `test_memory_versioning.py` | MemoryObject imutável/versionado |
| `test_events_provenance.py` | Provenance + contrato de falha do EventBus |
| `test_config_hardening.py` | Config imutável + dotenv |

Rodar: `python3 -m pytest tests/ -q` → **452 passed** (~3.5s), cobertura 85%.

---

## Hardening & Segurança (rodada H1–H26)

- **SQL injection** — whitelist de colunas por tabela antes de qualquer SQL em `distributed.py`
- **MemoryObject imutável** — updates criam nova versão, histórico preservado (PK composta `(id, version)`)
- **EventBus** — `emit()` retorna bool; rejeição e circuito aberto levantam exceção (nunca silencioso); provenance `correlation_id`/`causation_id`
- **Trust boundary** (`mia_pkg/trust.py`) — source declarada ≠ caller autenticado; kill switch real; read-only mode com `assert_mutable()`
- **BudgetAuthority** — orçamento global persistido (restart não zera): custos e chamadas por dia
- **Config** — imutável após carregamento; lê `.env` independente de cwd
- **Restart tests** — memória, identidade e orçamento sobrevivem entre processos
- **CI** — GitHub Actions: matrix 3.11/3.12, cobertura ≥60%, ruff, mypy soft

Detalhes por item: `docs/IMPLEMENTATION_STATUS.md` (seção 0).

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