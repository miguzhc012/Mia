# MIA — Status de Implementação

> Atualizado em: 2026-09-15 (sessão de implementação autônoma — rodada completa)
> Abrange: Prompts P1–P5 processados · Fases 0–16 do roadmap · 271 testes

## Legenda
- ✅ Feito e verificado
- 🟡 Parcial / em andamento
- ⬜ Não iniciado

---

## 1. Pipeline de Prompts (P1–P5)

| Prompt | Artefato | Status | Verificação |
|--------|----------|--------|-------------|
| P1 — Entendimento | `docs/01_entendimento.md` (221 linhas) | ✅ | Estrutura verificada; 6 inconsistências, 8 riscos, propostas |
| P2 — Visual | `docs/art/mia_concept_prompt.md` (142 linhas) | ✅ | Prompt master + 3 variações + parâmetros técnicos |
| P3 — Planejamento | `docs/02_especificacao.md` (1160 linhas) | ✅ | Seções A–O completas; schemas, contratos, ADRs |
| P4 — Roadmap | `docs/03_roadmap.md` (1986 linhas) | ✅ | 17 fases, M0–M10, trilha crítica, paralelização |
| P5 — Construção | `mia_pkg/` (31 módulos) + testes | ✅ | 271 testes passando (verificado por execução real) |

## 2. Debate Arquitetural (Onda 0)

| Posicionamento | Arquivo | Linhas | Perspectiva |
|----------------|---------|--------|-------------|
| Cético | `docs/debate/cetico_posicao.md` | 191 | MVP enxuto, cortar over-engineering, 2 authorities |
| Visionário | `docs/debate/visionario_posicao.md` | 377 | State Authority + event bus + Memory Objects desde o início |
| Segurança | `docs/debate/seguranca_posicao.md` | 286 | Enforcement físico, auditoria, kill switch, sandbox |

**Síntese do debate aplicada na especificação:** event bus in-process (pub/sub) + State Authority com 2 engines (State + Policy) para o MVP, evoluível depois. Documentado em `02_especificacao.md` seção D.5.

## 3. Fases Implementadas (0–16)

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
357 passed in 2.71s
```
Cobertura: EventBus (pub/sub, filtro, unsubscribe, circuit breaker), StateAuthority
(transições, LLM bloqueado, SQL injection, hash chain), Memory (CRUD, importância,
consolidação, decay), PolicyEngine, AffectiveEngine (PAD, fuzzy, humor, sensações),
Identity (Big Five, evolução por interações), Beliefs, NeedsDesires, AttentionPolicy,
Social (pessoas, relações, limites), Autonomy (goals, iniciativa, recursos),
Reflection (diário, crenças), Security, Voice (VAD, STT, speaker, directed, TTS,
pipeline), Perception (visão, rate limit, fusão, enricher), Avatar (expression
mapper, SVG, sync, API), Distributed (nodes, sync snapshot, offline, conflito),
Agents (registry, orchestrator, kill switch), World (interesses persistidos em DB,
pesquisa, knowledge), Evolution (canary, rollback), Monitoring (health, backup/
restore), E2E (fluxos completos).

## 4. Revisão Independente

Relatório: `docs/04_revisao_fundacao.md` (301 linhas)
Veredito: **APROVADO COM RESSALVAS** (2 críticos, 3 altos encontrados)

| Bug | Severidade | Correção | Status |
|-----|-----------|----------|--------|
| #1 SQL injection via f-string em key | 🔴 Crítico | Whitelist `_TARGET_COLUMNS` validada antes de interpolar | ✅ Corrigido |
| #2 f-string para nome de tabela | 🔴 Crítico (baixo risco real) | Eliminado com map hardcoded + whitelist | ✅ Corrigido |
| #3 Apply só para 3 de 10 targets | 🟠 Alto | Apply para identity, relationship, person, goal, diary | ✅ Corrigido |
| #4 Hash chain não verificada/persistente | 🟠 Alto | `_load_last_hash` + `verify_chain()` + coluna `hash` | ✅ Corrigido |
| #5 `total_changes` acumulativo | 🟠 Alto | `cursor.rowcount` em update_importance/delete | ✅ Corrigido |
| #6–13 (médios/baixos) | 🟡/🟢 | Documentados para Fase 1+ (LIKE injection, imutabilidade, etc.) | 📋 Registrado |

## 5. Roadmap — Próximos Passos

Conforme `docs/03_roadmap.md` e `docs/roadmap_mia.excalidraw`:

Próximas (integrações reais — hoje mocks/stubs nos testes):
1. **LLM real** — conectar ChatSession a um provider de verdade (chave Groq/HF/OpenRouter)
2. **Voz real** — Whisper STT + edge-tts/piper (grátis, local); VAD real (WebRTC)
3. **Visão real** — LLaVA / modelo multimodal local para analyze_fn
4. **Deploy distribuído** — VPS como master (n8n ou serviço), clientes PC/mobile sync

Melhorias pós-MVP:
- Autoevolução de código (hoje só parâmetros)
- Multi-usuário / identidades separadas

## 6. Decisões-Chave (ADRs resumidos — detalhe em 02_especificacao.md M)

- **ADR-001**: Python 3.10+ · SQLite inicial · CLI-first · stdlib (sem deps pesadas)
- **ADR-002**: Event bus in-process (pub/sub síncrono) — distribuído depois
- **ADR-003**: State Authority com 2 engines (State + Policy) — simplicidade no MVP
- **ADR-004**: Memória em tiers (working/episodic/semantic) com Memory Objects
- **ADR-005**: LLM provider abstraction (ABC + chain fallback) — agnóstico

## 7. Infra / Notas

- **Agents externos** (codex, claude, gemini, opencode): **auth quebrada** no gateway
  omniroute (chave `sk-153...4377` inválida). O pipeline foi executado com
  **subagentes Hermes** (delegate_task), que funcionam. Para usar os agents externos,
  corrigir a chave no gateway omniroute.
- **Orca**: run `run_0243e679c3ce` criado, mas workers parados por auth. Worktrees
  em `~/orca/workspaces/Mia/` (estrutura preservada).
- **Git**: repositório remoto criado em https://github.com/miguzhc012/Mia
  (commit inicial `6885f4f`; 31 commits até as Fases 9–12 + persistência de interesses).
  Push após cada fase com mensagens descritivas.