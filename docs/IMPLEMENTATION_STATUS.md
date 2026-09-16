# MIA — Status de Implementação

> Atualizado em: 2026-09-16 (hardening & reconciliation — rodada H1–H26)
> Suíte: **452 testes passando** · Cobertura: **85%** · CI: GitHub Actions (3.11/3.12)

## Legenda
- ✅ Feito e verificado
- 🟡 Parcial / em andamento
- ⬜ Não iniciado

---

## 0. Rodada de Hardening & Reconciliation (H1–H26)

Estado real do código após a rodada de correção/segurança. Verificável por
execução: `python -m pytest tests/ -q` → 452 passed.

| Item | Severidade | Correção | Status |
|------|-----------|----------|--------|
| H1  | 🟠 Alto | MD5 documentado como checksum acidental (não autenticidade) | ✅ |
| H2  | 🟠 Alto | 1ª mudança de personalidade pós-boot não bloqueada por rate limit | ✅ |
| H3  | 🟠 Alto | Hard timeout real em task runners (não só guideline) | ✅ |
| H4  | 🟠 Alto | Profundidade real da árvore de delegação (subagentes) | ✅ |
| H5  | 🟠 Alto | BudgetAuthority autoridade global (governors subordinados) | ✅ |
| H6  | 🟠 Alto | Escopo de limites: process-local vs system/global (persistido) | ✅ |
| H7  | 🟠 Alto | Config imutável + carrega `.env` independente de cwd | ✅ |
| H8  | 🔴 Crítico | Source identity: declared ≠ authenticated (ComponentRegistry) | ✅ |
| H9  | 🔴 Crítico | Trust boundary: adaptive NUNCA muta trust/state | ✅ |
| H10 | ⬜ | (detalhe de baixa prioridade documentado) | 📋 |
| H11 | 🟠 Alto | Provider status exposto (disponibilidade consultável) | ✅ |
| H12 | 🟠 Alto | Circuit breaker real no EventBus (por source+tipo) | ✅ |
| H13 | 🟠 Alto | MemoryObject imutável + versionado (histórico preservado) | ✅ |
| H14 | 🟡 | (consolidação de memória por política) | 📋 |
| H15 | 🟡 | Provenance de eventos (correlation_id, causation_id) | ✅ |
| H16 | 🟠 Alto | Emit retorna bool; rejeição/circuito = exceção loud (nunca silencioso) | ✅ |
| H17 | 🟡 | Revisão de SDKs (documentado) | 📋 |
| H18 | 🟠 Alto | Source identity real (tokens) | ✅ |
| H19 | 🔴 Crítico | Kill switch REAL (is_blocked consultado por consumidores) | ✅ |
| H20 | 🟡 | Read-only mode (assert_mutable levanta ReadOnlyError) | ✅ |
| H21 | ⬜ | (baixa prioridade) | 📋 |
| H22 | 🟠 Alto | ReadOnlyMode impede mutação de verdade | ✅ |
| H23 | 🟠 Alto | E2E de falha honesta (LLM fora do ar, banco corrompido) | ✅ |
| H24 | 🟠 Alto | Restart tests (estado persiste entre processos) | ✅ |
| H25 | 🟠 Alto | SQLite thread-safe (writes serializados) | ✅ |
| H26 | 🟠 Alto | CI GitHub Actions (tests 3.11/3.12 + cobertura + lint) | ✅ |

## 1. Pipeline de Prompts (P1–P5)

| Prompt | Artefato | Status |
|--------|----------|--------|
| P1 — Entendimento | `docs/01_entendimento.md` | ✅ |
| P2 — Visual | `docs/art/mia_concept_prompt.md` | ✅ |
| P3 — Planejamento | `docs/02_especificacao.md` | ✅ |
| P4 — Roadmap | `docs/03_roadmap.md` | ✅ |
| P5 — Construção | `mia_pkg/` (módulos) + testes | ✅ |

## 2. Fases Implementadas (0–16)

| Fase | Módulos | Status |
|------|---------|--------|
| 0 — Fundação | events, state_authority, policy_engine, db, runtime | ✅ |
| 1 — LLM + Core + Context | llm, cognitive_core, context_assembly, chat | ✅ |
| 2 — Memória | memory, consolidation, attention_policy | ✅ |
| 3 — Identidade | identity, identity_authority | ✅ |
| 4 — Emoção/Mood | affective_engine, emotion_governor | ✅ |
| 5 — Social | social (people, relationships, boundaries) | ✅ |
| 6 — Autonomia | autonomy (goals, initiative, governor) | ✅ |
| 7 — Reflexão | reflection, belief_revision, beliefs | ✅ |
| 8 — Security | security (redactor, rate, integrity, sandbox) | ✅ |
| 9 — Voz | voice (VAD, STT, speaker, directed, TTS) | ✅ |
| 10 — Visão | perception (pipeline, aggregator, enricher) | ✅ |
| 11 — Avatar | avatar (mapper, renderer SVG, sync, api) | ✅ |
| 12 — Nós | distributed (manager, sync, offline, conflict) | ✅ |
| 13 — Subagentes | agents (registry, orchestrator, templates) | ✅ |
| 14 — World Awareness | world (interests, relevance, research) | ✅ |
| 15 — Autoevolução | evolution (engine, canary, rollback) | ✅ |
| 16 — Integração | monitoring (health, backup), test_e2e | ✅ |

### Testes (execução real verificada)
```
452 passed in ~3.5s
Cobertura mia_pkg: 85% (piso do CI: 60%)
```

## 3. Revisão Independente (04_revisao_fundacao.md)

Veredito: **APROVADO COM RESSALVAS** — críticos/altos corrigidos nesta rodada
(ver tabela H acima). SQL injection, f-string de tabela, apply parcial,
hash chain e total_changes acumulativo: ✅ corrigidos e testados.

## 4. Roadmap — Próximos Passos

Integrações reais (hoje stubs nos testes):
1. **LLM real** — provider OmniRoute configurado; testes usam stub determinístico
2. **Voz real** — Whisper STT + edge-tts/piper (grátis, local)
3. **Visão real** — modelo multimodal local
4. **Deploy distribuído** — VPS master + clientes em sync

## 5. Infra / Notas

- **LLM provider**: `~/.config/mia/config.yaml` → omniroute (`auto/best-chat`,
  fallback `auto/best-fast`). Chave em `.env` (gitignored), carregado via
  `_load_dotenv` independente de cwd.
- **Git**: https://github.com/miguzhc012/Mia — push após cada fase, commits
  descritivos com o que mudou.
- **CI**: `.github/workflows/tests.yml` — matrix 3.11/3.12, coverage ≥60%,
  ruff, mypy soft.
- **Agents externos** (codex, claude, gemini, opencode): auth quebrada no
  gateway omniroute — usar `delegate_task` do Hermes para o pipeline.