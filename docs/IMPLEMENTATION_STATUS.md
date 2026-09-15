# MIA — Status de Implementação

> Atualizado em: 2026-09-14 (sessão de orquestração multi-agente)
> Abrange: Prompts P1–P5 processados · Fundação implementada e revisada

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
| P5 — Construção | `mia_pkg/` (8 módulos) + testes | ✅ | 36 testes passando (verificado por execução real) |

## 2. Debate Arquitetural (Onda 0)

| Posicionamento | Arquivo | Linhas | Perspectiva |
|----------------|---------|--------|-------------|
| Cético | `docs/debate/cetico_posicao.md` | 191 | MVP enxuto, cortar over-engineering, 2 authorities |
| Visionário | `docs/debate/visionario_posicao.md` | 377 | State Authority + event bus + Memory Objects desde o início |
| Segurança | `docs/debate/seguranca_posicao.md` | 286 | Enforcement físico, auditoria, kill switch, sandbox |

**Síntese do debate aplicada na especificação:** event bus in-process (pub/sub) + State Authority com 2 engines (State + Policy) para o MVP, evoluível depois. Documentado em `02_especificacao.md` seção D.5.

## 3. Fundação Implementada (Fase 0 do roadmap)

| Módulo | Responsabilidade | Status |
|--------|-----------------|--------|
| `mia_pkg/events.py` | EventBus pub/sub tipado + circuit breaker | ✅ |
| `mia_pkg/state_authority.py` | Ponto único de escrita de estado; propose→policy→validate→apply→audit | ✅ |
| `mia_pkg/policy_engine.py` | Regras determinísticas: whitelist targets, bloqueio LLM, invariantes | ✅ |
| `mia_pkg/memory.py` | MemoryObject + MemoryStore (CRUD, importância, busca) | ✅ |
| `mia_pkg/db.py` | SQLite (WAL, FK, 15 tabelas, índices) | ✅ |
| `mia_pkg/llm.py` | LLMProvider ABC + OpenAICompat + chain de fallback | ✅ |
| `mia_pkg/config.py` | Config com defaults, env overrides, sem secrets | ✅ |
| `mia_pkg/runtime.py` | Runtime: wiring config→db→bus→sa→memory, kill switch | ✅ |
| `tests/test_foundation.py` | 36 testes unitários | ✅ |

### Testes (execução real verificada)
```
36 passed in 0.15s
```
Cobertura: EventBus (pub/sub, filtro, unsubscribe, circuit breaker, eventos inválidos),
StateAuthority (transição válida/inválida, LLM bloqueado, SQL injection bloqueado,
hash chain, verify_chain + tampering), MemoryStore (CRUD, importância, busca),
PolicyEngine (regras), Config (defaults, JSON, dotted access), Integração.

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

Próximas fases (conforme `docs/03_roadmap.md`):
1. **Fase 1** — LLM Abstraction completa + Cognitive Core + Context Assembly (async, streaming)
2. **Fase 2** — Memória: consolidação, esquecimento, associações, versionamento append-only
3. **Fase 3** — Identidade / Self-model / Personalidade persistente
4. **Fase 4** — Emoção / Sensação / Humor / Necessidades

Primeira release (v0.1): Fase 0–6 → MIA conversa, lembra, tem identidade, emoções,
diário e reflexão; State Authority controla todas as mudanças; kill switch funcional.

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
- Repo git local: 7 commits (baseline → docs → fundação → correções).