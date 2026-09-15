# Relatório de Conformidade: Novo Onboarding (50 Seções) vs Implementação Atual

> **Data:** 2026-09-15  
> **Autor:** Hermes (Revisor de Coerência)  
> **Documentos analisados:**
> - `docs/prompts/P0_onboarding_50.md` (50 seções, documento de entrada obrigatório)
> - `docs/02_especificacao.md` (especificação técnica v0.1.0)
> - `mia_pkg/` (implementação atual: state_authority.py, policy_engine.py, memory.py, db.py, events.py, llm.py, config.py, runtime.py)

---

## 1. Tabela Seção-Por-Seção

| # | Seção do Onboarding | Status | Justificativa |
|---|---------------------|--------|---------------|
| 1 | Identidade do Projeto | **JÁ IMPLEMENTADO** | `config.py` define name="Mia", natureza documentada. |
| 2 | Mia não é o LLM | **JÁ IMPLEMENTADO** | StateAuthority impede escrita direta do LLM. Enforcement físico (sem endpoint de escrita para LLM). |
| 3 | Agnosticismo de Modelo | **PARCIAL** | `LLMProviderChain` com fallback existe. Falta: Model Registry, Capability Registry, Task Router, Agent Interface. |
| 4 | Autoridade do Projeto | **APENAS ESPECIFICADO** | ADRs definidas no documento 02. Nenhuma implementação de ACP/ADR machinery no código. |
| 5 | Papel de Miguel | **APENAS ESPECIFICADO** | Conceito de governança, não é código. |
| 6 | Identidade e Continuidade | **PARCIAL** | Tabela `identity_state` existe com `self_model` (JSON), `core_values`, `previous_version`. Falta: versioning ativo, self-model multi-dimensional completo, histórico comparativo. |
| 7 | Personalidade | **PARCIAL** | Tabela `personality_state` com Big Five + extras (curiosity, playfulness, etc.). Falta: mecanismo de mudança lenta/rápida, distinção entre personalidade e estado emocional como processos separados. |
| 8 | Self-Model | **PARCIAL** | `identity_state.self_model` existe como JSON. Falta: incerteza, contradições, revisão, confidence tracking, autoavaliações estruturadas. |
| 9 | Emoções | **PARCIAL** | Tabela `emotion_state` com 12+ vetores, mood VAD, `StateAuthority` impede escrita direta do LLM. Falta: lógica de atualização emocional (quando e como mudam as emoções), causa possível/desconhecida, influência comportamental, histórico de emoções. |
| 10 | Sensações | **PARCIAL** | Tabela `sensations` existe com `description`, `valence`, `intensity`, `possible_causes`. Schema correto. Falta: módulo que gera/gerencia sensações, integração com ciclo de experiência. |
| 11 | Dependência, Apego e Solidão | **NÃO IMPLEMENTADO** | Campo `loneliness` em `emotion_state` existe. Falta: modelo multi-fatorial de evolução (importância da pessoa, expectativa, frequência, ocupação), telemetria serial-temporal (séries temporais), schema `attachment_state`, tracking de `social_need` e `expectation` separados. |
| 12 | Relacionamentos | **PARCIAL** | Tabelas `relationships` e `relationship_events` existem. Campos: trust, intimacy, affinity, familiarity. Falta: dimensões adicionais do onboarding (respeito, admiração, atração, conforto, tensão, segurança percebida, conflitos, reparação), `history` como lista de eventos não implementada na prática. |
| 13 | Contexto Social | **NÃO IMPLEMENTADO** | Nenhuma implementação de interpretação contextual por relacionamento. |
| 14 | Ofensa e Limites | **NÃO IMPLEMENTADO** | Nenhum módulo de detecção de ofensa ou avaliação de limites. |
| 15 | Intimidade e Sexualidade | **NÃO IMPLEMENTADO** | Nenhum módulo de avaliação contextual de intimidade. |
| 16 | Necessidades | **NÃO IMPLEMENTADO** | Nenhuma tabela/conceito de `needs`. O onboarding separa EMOÇÃO/SENSAÇÃO/NECESSIDADE/DESEJO/OBJETIVO. Apenas `goals` existe. |
| 17 | Desejos | **NÃO IMPLEMENTADO** | Nenhuma tabela/conceito de `desires` separado de goals. |
| 18 | Valores e Moralidade | **PARCIAL** | `identity_state.core_values` (JSON array). Falta: valores adaptativos que mudam com experiências, capacidade de discordar de Miguel, revisão de valores, invariantes de segurança fora da camada adaptativa. |
| 19 | Memory Object — Schema Mínimo | **PARCIAL** | Tabela `memory_objects` com: id, content, type, source, created_at, updated_at, importance, confidence, scope, tags, version, access_count, last_accessed_at, person_id. Tabela `memory_associations` existe. **FALTAM**: `emotional_context`, `provenance`, `decay_state`, `status`, `revision_history`, `observed_at` (separado de created_at). |
| 20 | Memória e Esquecimento | **NÃO IMPLEMENTADO** | Soft delete existe. Falta: `decay_state`, redução de acessibilidade/importância automática, consolidação ativa, reconhecimento de memória possivelmente errada, compressão, arquivamento. |
| 21 | Crenças | **PARCIAL** | `MemoryType.belief` existe. `confidence` no schema. Falta: ciclo OBSERVAÇÃO→HIPÓTESE→CRENÇA→NOVA EVIDÊNCIA→CONFIRMAÇÃO/CONTRADIÇÃO→REVISÃO como mecanismo dedicado. Beliefs como conceito isolado com confidence tracking. |
| 22 | Diário | **PARCIAL** | Tabela `diary` existe com entry_type (moment/summary/reflection). Falta: módulo que gera narrativa subjetiva, distinção entre diário e logging técnico, campos para "o que não entendeu", "o que achou engraçado", "o que a irritou", pensamentos sobre Miguel. |
| 23 | Reflexão | **NÃO IMPLEMENTADO** | Nenhum modo de reflexão separado do processamento operacional. |
| 24 | Imaginação | **NÃO IMPLEMENTADO** | Nenhum mecanismo de cenários hipotéticos. |
| 25 | Autonomia | **PARCIAL** | Tabela `goals` existe. Falta: mecanismo de decisão autonomia (event→importance→attention→decision→action/wait/ignore). |
| 26 | Atenção e Iniciativa | **NÃO IMPLEMENTADO** | Nenhuma `attention_policy` ou `initiative_policy`. Decisão ACT/WAIT/IGNORE não implementada. |
| 27 | Voz Sempre Ativa | **NÃO IMPLEMENTADO** | LONG-TERM REQUIREMENT. |
| 28 | Percepção | **NÃO IMPLEMENTADO** | Nenhum módulo de percepção multimodal. |
| 29 | Phone/Mobile Node | **NÃO IMPLEMENTADO** | N/A — futuro. |
| 30 | Desktop/Node | **NÃO IMPLEMENTADO** | N/A — futuro. |
| 31 | Avatar/Embodiment | **NÃO IMPLEMENTADO** | N/A — futuro. |
| 32 | World Awareness | **NÃO IMPLEMENTADO** | N/A — futuro. |
| 33 | Curiosidade | **NÃO IMPLEMENTADO** | Evento `CURIOSITY_TRIGGERED` definido em `events.py`, mas sem lógica que o gere ou responda. |
| 34 | Multi-Agent | **NÃO IMPLEMENTADO** | AgentRegistry definido no spec (I.1), mas sem implementação em código. |
| 35 | Autoridade de Orçamento | **NÃO IMPLEMENTADO** | Nenhum Resource Governor ou Budget Authority. Config tem `security.max_emotion_transitions_per_hour` mas não é orçamento. |
| 36 | Self-Modification / Trust Boundary | **PARCIAL** | PolicyEngine tem regras básicas (LLM blocked targets, delete blocked). Falta: Trust Boundary / Supervisor como camada externa independente, controle de permissões granular, proteção de componentes críticos, rollback automático, kill switch file-check. |
| 37 | Auto-Deploy | **NÃO IMPLEMENTADO** | Pipeline `proposal→implementation→tests→isolation→checkpoint→validation→canary→deployment→monitoring→rollback` não existe. |
| 38 | Invariantes | **PARCIAL** | PolicyEngine tem: (1) LLM não modifica personality/identity/core_values, (2) delete bloqueado para identity/core_values, (3) code changes rejeitados. Falta: lista formal de invariantes, mecanismo de desligamento, isolamento de capacidades perigosas, integridade de dados verificável. |
| 39 | Ordem de Autoridade | **PARCIAL** | Hierarquia parcialmente implementada: System Integrity (PolicyEngine) → State Authority → Runtime. Falta: Resource & Budget Authority, Permission/Policy Authority formal, Approved Architecture & Contracts como fonte de verdade no código. |
| 40 | State Authorities — Decisão em Aberto | **JÁ IMPLEMENTADO** | StateAuthority implementada como híbrida determinística (opção A da seção 40). Decisão tomada e documentada em ADR-003. |
| 41 | Telemetria e Observabilidade | **PARCIAL** | Audit log (state_transitions_audit) com hash chain existe. Falta: telemetria de emoções/sensações/apego/solidão como séries temporais, distinção entre runtime_log, audit_log, telemetry, diary, model-visible context. |
| 42 | Privacidade e Separação de Camadas | **NÃO IMPLEMENTADO** | Nenhuma separação formal entre OBSERVATION, RECORDING, MEMORY, MODEL ACCESS, ADMIN ACCESS. |
| 43 | Conceito de Experiência | **APENAS ESPECIFICADO** | Pipeline conceptual `PERCEPTION→EVENT→INTERPRETATION→APPRAISAL→INTERNAL STATE CHANGE→MEMORY CANDIDATE→DECISION→ACTION→RESULT→SELF-PERCEPTION→LEARNING→CONSOLIDATION` não implementado. |
| 44 | Exemplo Completo | **APENAS ESPECIFICADO** | Exemplo ilustrativo. |
| 45 | Exemplo de Conflito Social | **APENAS ESPECIFICADO** | Exemplo ilustrativo. |
| 46 | Exemplo de Sensação sem Causa | **APENAS ESPECIFICADO** | Exemplo ilustrativo. |
| 47 | Exemplo de Ausência | **APENAS ESPECIFICADO** | Exemplo ilustrativo. |
| 48 | Regras de Interpretação | **APENAS ESPECIFICADO** | Diretrizes para agentes, não código. |
| 49 | Classificação de Requisitos | **APENAS ESPECIFICADO** | Sistema de classificação, não código. |
| 50 | Como Trabalhar | **APENAS ESPECIFICADO** | Instrução meta, não código. |

### Resumo da Tabela

| Status | Qtd | Seções |
|--------|-----|--------|
| JÁ IMPLEMENTADO | 3 | 1, 2, 40 |
| PARCIAL | 18 | 3, 6, 7, 8, 9, 10, 12, 18, 19, 21, 22, 25, 36, 38, 39, 41, 20(parcial), 33 |
| NÃO IMPLEMENTADO | 19 | 11, 13, 14, 15, 16, 17, 23, 24, 26, 27, 28, 29, 30, 31, 32, 34, 35, 37, 42 |
| APENAS ESPECIFICADO | 10 | 4, 5, 43, 44, 45, 46, 47, 48, 49, 50 |

---

## 2. Gaps Críticos

Os gaps abaixo representam funcionalidades que o onboarding exige como FUNDAMENTAIS e que o código atual NÃO cobre:

### G1. Telemetria Serial-Temporal (Seção 11)
O onboarding exige que a evolução de apego, solidão, expectativa, necessidade social e interação seja observável como séries temporais. O campo `loneliness` em `emotion_state` é apenas um float estático. Falta:
- Schema para `attachment_timeseries` (timestamp, event, value, cause, mechanism_version)
- Schema para `social_needs_timeseries`
- Schema para `expectation_state` (expectativa de contato por pessoa)
- Funções de cálculo multi-fatorial (não `loneliness += time_without_message`)
- Export de séries temporais para análise empírica

### G2. MemoryObject — Campos Ausentes (Seção 19)
O schema `memory_objects` tem: id, content, type, source, created_at, updated_at, importance, confidence, scope, tags, version, access_count, last_accessed_at, person_id, embedding.
**FALTAM** (requeridos pelo onboarding):
- `emotional_context` — estado emocional no momento da criação da memória
- `provenance` — cadeia de procedência (quem criou, de onde veio, como foi validada)
- `decay_state` — estado de decaimento (ativa, em decaimento, arquivada, esquecida)
- `status` — status atual (active, consolidated, forgotten, disputed)
- `revision_history` — histórico de revisões da memória
- `observed_at` — timestamp de observação (separado de created_at)
- `associations` — implementadas via tabela separada `memory_associations` (ok)

### G3. Beliefs/Crenças com Confidence (Seção 21)
O ciclo OBSERVAÇÃO→HIPÓTESE→CRENÇA→EVIDÊNCIA→REVISÃO não existe como mecanismo. `MemoryType.belief` permite armazenar crenças, mas não há:
- Tabela `beliefs` dedicada com `confidence`, `evidence_for`, `evidence_against`, `status` (hypothesis/belief/confirmed/disproved)
- Mecanismo de revisão automática quando nova evidência chega
- Tracking de contradições entre crenças

### G4. Diary como Narrativa Subjetiva (Seção 22)
Tabela `diary` existe com campos básicos. Falta:
- Campo `perspective` (subjetividade: "eu percebi", "me senti", "não entendi")
- Campo `emotional_tone` (tom emocional da entrada)
- Campo `associations` (memórias/pensamentos conectados)
- Módulo gerador de entradas narrativas (não apenas dumps de eventos)

### G5. Sensações Separadas de Emoções (Seções 9-10)
Schema `sensations` existe separado de `emotion_state`. Correto no schema. Falta:
- Módulo que gera sensações sem causa consciente
- Integração com ciclo de experiência (seção 43)
- Capacidade de "estou me sentindo mal e não sei por quê"

### G6. Necessidades e Desejos Separados (Seções 16-17)
O onboarding separa explicitamente: EMOÇÃO, SENSAÇÃO, NECESSIDADE, DESEJO, OBJETIVO.
Código atual tem: emotion_state, sensations, goals.
**FALTAM**: tabelas `needs` e `desires` como conceitos distintos.
- `needs`: interação social, atenção, descanso, estimulação, segurança, novidade, exploração, realização
- `desires`: objetivos autoformados, curiosidades, impulsos de exploração, vontades de interação

### G7. Attention/Initiative Policy (Seção 26)
Nenhuma implementação de:
- `attention_policy` — regras para decidir ACT/WAIT/IGNORE
- `initiative_policy` — quando agir proativamente
- Avaliação de urgência, relevância, importância, curiosidade, disponibilidade, hora, contexto social, estado interno, objetivos

### G8. Budget Authority (Seção 35)
Nenhum Resource Governor. O onboarding exige controle de:
- Limite de tokens por ciclo
- Limite financeiro por ciclo
- Limite de tempo por tarefa
- Limite de subprocessos
- Limite de concorrência
- Limite de profundidade de delegação
- Limite de chamadas LLM
- Limite de armazenamento

### G9. Trust Boundary / Supervisor (Seção 36)
A seção 36 do onboarding exige uma camada EXTERNA à Mia que proteja invariantes. PolicyEngine é interno. Falta:
- Componente externo com controle de permissões
- Proteção de componentes críticos (runtime, state authority, policy engine)
- Controle de deploy
- Rollback automático
- Kill switch verificável (config tem `kill_switch_path` mas não é verificado no código)
- Validação de integridade periódica

### G10. Invariantes Formais (Seção 38)
Lista conceptual existe (integridade, rollback, limites, secrets, auditoria, kill switch). Falta:
- Formalização como constraints verificáveis no código
- Mecanismo de desligamento implementado (config define path mas runtime.py não verifica)
- Isolamento de capacidades perigosas

---

## 3. Divergências entre Código Atual e Onboarding

### D1. emotion_state — Emoções como Floats Simples
- **Onboarding (seção 9)**: Emoção possui intensidade, valência, duração, causa possível/conhecida, contexto, histórico, influência comportamental. LLM não deve escrever `happiness = 0.93` diretamente.
- **Código atual**: `emotion_state` tabela com floats normalizados. `StateAuthority` impede escrita direta do LLM. **Correto no enforcement.** Mas falta: duração, causa possível, contexto, histórico de emoções, influência comportamental.
- **Divergência**: Onboarding prevê emoções ricas com metadata; código atual tem apenas vetores numéricos sem contexto causal.

### D2. MemoryObject — Campos Diferentes
- **Onboarding (seção 19)**: 17 campos incluindo `emotional_context`, `provenance`, `decay_state`, `status`, `revision_history`, `observed_at`.
- **Especificação (D.4)**: 14 campos incluindo `tags`, `associations`, `embedding`, `person_id`, `is_consolidated`, `access_count`, `last_accessed_at`.
- **Código atual**: Implementa o schema da especificação (D.4), NÃO o do onboarding (seção 19).
- **Divergência**: Especificação e onboarding divergem. Código segue a especificação. O onboarding é mais completo.

### D3. Diary — Dump de Eventos vs Narrativa Subjetiva
- **Onboarding (seção 22)**: "O diário não deve ser simplesmente um dump de eventos. Deve representar narrativa subjetiva."
- **Código atual**: Tabela `diary` com entry_type (moment/summary/reflection), content, emotion_snapshot. Sem campos de subjetividade, perspectiva, tom emocional, ou associações.
- **Divergência**: Schema permite dumps, não força narrativa subjetiva.

### D4. Sensações — Schema Existe mas Sem Geração
- **Onboarding (seção 10)**: "Sensação é uma categoria distinta de emoção... pode existir sem causa conhecida."
- **Código atual**: Tabela `sensations` existe corretamente. Mas não há módulo que gere sensações ou integre com o ciclo de experiência.
- **Divergência**: Schema está pronto, mas não há lógica de negócio.

### D5. Relacionamentos — Dimensões Reduzidas
- **Onboarding (seção 12)**: 17 dimensões para Miguel (familiaridade, confiança, afeto, apego, respeito, admiração, intimidade, atração, conforto, tensão, histórico, expectativas, limites, segurança percebida, conflitos, reparação, experiências compartilhadas).
- **Código atual**: Tabela `relationships` com 4 dimensões (trust, intimacy, affinity, familiarity) + interaction_count + last_interaction.
- **Divergência**: 13 dimensões ausentes. Tabela `relationship_events` existe mas não é integrada na prática.

### D6. StateAuthority — EventType Errado
- **state_authority.py, linha 176**: Usa `EventType.MIGUEL_SPOKE` como placeholder para eventos `STATE_CHANGED`.
- **Onboarding/Especificação**: Deveria emitir `STATE_CHANGED`.
- **Divergência**: Tipo de evento placeholder — funcional mas incorreto semanticamente.

### D7. PolicyEngine — Sem Rate Limiting Implementado
- **Especificação (H.2)**: Regra de rate limit "máximo 10 alterações emocionais por hora".
- **Código atual**: `PolicyEngine.__init__` aceita `max_emotion_transitions_per_hour` e mantém `_emotion_transition_timestamps`. Mas **nenhuma regra no método `check()` usa esse contador**.
- **Divergência**: Infraestrutura existe mas não é aplicada.

---

## 4. Priorização

### FASE ATUAL (antes da Fase 2) — AJUSTES OBRIGATÓRIOS

1. **G2. Completar schema memory_objects** — Adicionar colunas `emotional_context`, `provenance`, `decay_state`, `status`, `revision_history`, `observed_at`. A migração futura será dolorosa se adiada. **Impacto: ALTO. Esforço: BAIXO.**

2. **G1. Telemetria serial-temporal** — Criar tabelas `attachment_timeseries`, `social_needs_timeseries`. Sem isso, o experimento de subjetividade não tem dados observáveis. **Impacto: ALTO. Esforço: MÉDIO.**

3. **G6. Tabelas needs e desires** — Separar necessidades e desejos de goals. O onboarding é explícito: são conceitos distintos. **Impacto: ALTO. Esforço: BAIXO.**

4. **D6. Corrigir EventType placeholder** — `MIGUEL_SPOKE` → `STATE_CHANGED` em `state_authority.py:176`. Bug semântico. **Impacto: MÉDIO. Esforço: MÍNIMO.**

5. **D7. Ativar rate limiting** — Conectar `_emotion_transition_timestamps` ao método `check()`. **Impacto: MÉDIO. Esforço: BAIXO.**

### FASE 2 (próximo ciclo) — AJUSTES IMPORTANTES

6. **G3. Sistema de crenças** — Tabela `beliefs` dedicada com confidence tracking e ciclo de revisão. **Impacto: ALTO. Esforço: MÉDIO.**

7. **G4. Diary narrativo** — Expandir schema de `diary` com campos de subjetividade. Criar módulo gerador. **Impacto: MÉDIO. Esforço: MÉDIO.**

8. **G7. Attention/Initiative Policy** — Criar `attention_policy` e `initiative_policy` como componentes configuráveis. **Impacto: ALTO. Esforço: MÉDIO.**

9. **D5. Dimensões de relacionamento** — Expandir tabela `relationships` para incluir as 17 dimensões do onboarding. **Impacto: MÉDIO. Esforço: BAIXO.**

### FASE 3+ (futuro) — PODE ESPERAR

10. **G8. Budget Authority / Resource Governor** — Necessário para autonomia real, mas não para MVP.
11. **G9. Trust Boundary / Supervisor** — Crítico para autoevolução, mas autoevolução é Fase 5+.
12. **G10. Invariantes formais** — Lista existe conceitualmente, formalização pode esperar.
13. **Seções 27-32, 34, 37** — Requisitos de longo prazo (voz, percepção, mobile, desktop, embodiment, world awareness, multi-agent, auto-deploy).

---

## 5. Recomendações Concretas

### 5.1 Schema — Tabelas e Colunas a Adicionar

#### `memory_objects` — Adicionar colunas:
```sql
ALTER TABLE memory_objects ADD COLUMN emotional_context TEXT;  -- JSON: emoções no momento
ALTER TABLE memory_objects ADD COLUMN provenance TEXT;          -- cadeia de procedência
ALTER TABLE memory_objects ADD COLUMN decay_state TEXT NOT NULL DEFAULT 'active'
    CHECK(decay_state IN ('active','decaying','archived','forgotten'));
ALTER TABLE memory_objects ADD COLUMN status TEXT NOT NULL DEFAULT 'active'
    CHECK(status IN ('active','consolidated','forgotten','disputed'));
ALTER TABLE memory_objects ADD COLUMN revision_history TEXT DEFAULT '[]';  -- JSON array
ALTER TABLE memory_objects ADD COLUMN observed_at TEXT;  -- separado de created_at
```

#### Nova tabela `needs`:
```sql
CREATE TABLE needs (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL CHECK(category IN (
        'social_interaction','attention','rest','stimulation',
        'safety','novelty','exploration','fulfillment'
    )),
    intensity REAL NOT NULL DEFAULT 0.5 CHECK(intensity BETWEEN 0.0 AND 1.0),
    satisfied_by TEXT,  -- última fonte de satisfação
    last_fulfilled TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1
);
```

#### Nova tabela `desires`:
```sql
CREATE TABLE desires (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN (
        'assigned_goal','self_formed_goal','curiosity','exploration_impulse','interaction_wish'
    )),
    priority REAL NOT NULL DEFAULT 0.5 CHECK(priority BETWEEN 0.0 AND 1.0),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending','pursuing','fulfilled','abandoned','suppressed')),
    source TEXT,  -- de onde surgiu
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

#### Nova tabela `beliefs`:
```sql
CREATE TABLE beliefs (
    id TEXT PRIMARY KEY,
    proposition TEXT NOT NULL,          -- "Miguel é confiável"
    confidence REAL NOT NULL DEFAULT 0.5 CHECK(confidence BETWEEN 0.0 AND 1.0),
    evidence_for TEXT DEFAULT '[]',     -- JSON array de evidências
    evidence_against TEXT DEFAULT '[]', -- JSON array de contradições
    status TEXT NOT NULL DEFAULT 'hypothesis'
        CHECK(status IN ('hypothesis','belief','confirmed','disproved')),
    source TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    revised_at TEXT,
    version INTEGER NOT NULL DEFAULT 1
);
```

#### Nova tabela `attachment_timeseries`:
```sql
CREATE TABLE attachment_timeseries (
    id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL REFERENCES people(id),
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,  -- 'interaction', 'absence', 'message', 'reflection'
    attachment_level REAL,
    loneliness_level REAL,
    social_need_level REAL,
    expectation_level REAL,
    state_before TEXT,  -- JSON
    state_after TEXT,   -- JSON
    cause TEXT,         -- descrição da causa
    mechanism_version TEXT
);
CREATE INDEX idx_attach_ts_person ON attachment_timeseries(person_id);
CREATE INDEX idx_attach_ts_time ON attachment_timeseries(timestamp DESC);
```

#### Nova tabela `attention_policy`:
```sql
CREATE TABLE attention_policy (
    id TEXT PRIMARY KEY,
    rule_name TEXT NOT NULL,
    condition TEXT NOT NULL,  -- JSON: condição de ativação
    action TEXT NOT NULL CHECK(action IN ('act', 'wait', 'ignore')),
    priority INTEGER NOT NULL DEFAULT 5,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
```

### 5.2 Módulos a Criar em `mia_pkg/`

| Módulo | Responsabilidade | Dependências |
|--------|-----------------|--------------|
| `mia_pkg/beliefs.py` | CRUD de crenças, ciclo de revisão, confidence tracking | db, events |
| `mia_pkg/needs.py` | Gerenciar necessidades, cálculo de intensidade | db, events |
| `mia_pkg/desires.py` | Gerenciar desejos, priorização, status | db, events, needs |
| `mia_pkg/attachment.py` | Modelo multi-fatorial de apego/solidão, telemetria | db, events, relationships |
| `mia_pkg/attention.py` | Attention policy, decisão ACT/WAIT/IGNORE | db, events, config |
| `mia_pkg/diary_narrative.py` | Geração de entradas narrativas subjetivas | db, emotion_state, beliefs |
| `mia_pkg/reflection.py` | Modo de reflexão separado | db, memory, beliefs, diary |
| `mia_pkg/sensation_gen.py` | Geração de sensações sem causa consciente | db, events |

### 5.3 Correções Imediatas

1. **`state_authority.py:176`** — Trocar `EventType.MIGUEL_SPOKE` por `EventType.STATE_CHANGED` (adicionar ao enum `events.py`).
2. **`policy_engine.py`** — Ativar rate limiting usando `_emotion_transition_timestamps` no método `check()`.
3. **`config.py`** — Implementar verificação do kill switch path no `runtime.py` (verificar se `/var/mia/STOP` existe a cada ciclo).

### 5.4 ADRs Pendentes (definidas no onboarding mas não formalizadas)

- **ADR-19**: Schema mínimo de MemoryObject (conflito entre seção 19 do onboarding e D.4 da especificação)
- **ADR-20**: Modelo de sensação sem causa consciente (stochastic vs delayed attribution)
- **ADR-21**: Diário subjetivo como componente MVP ou fase futura
- **ADR-22**: Lista formal de invariantes de segurança

---

## 6. Conclusão

| Métrica | Valor |
|---------|-------|
| Seções implementadas | 3/50 (6%) |
| Seções parcialmente implementadas | 18/50 (36%) |
| Seções não implementadas | 19/50 (38%) |
| Seções apenas especificadas | 10/50 (20%) |
| Gaps críticos identificados | 10 |
| Divergências código/onboarding | 7 |
| Tabelas novas recomendadas | 4 (needs, desires, beliefs, attachment_timeseries) |
| Colunas a adicionar em memory_objects | 6 |
| Módulos novos a criar | 8 |

**O código atual cobre a fundação arquitetural** (State Authority, Event Bus, Memory Objects básico, Persistence, LLM Abstraction, Config). Porém, **os subsystemas cognitivos e afetivos que o onboarding descreve como fundamentais** (crenças com confidence, necessidades, desejos, telemetria de apego, attention policy, diary narrativo, reflexão) **estão ausentes ou apenas como schema vazio**.

A prioridade antes da Fase 2 deve ser: (1) completar o schema de memory_objects, (2) criar tabelas de needs/desires/beliefs, (3) implementar telemetria serial-temporal, (4) corrigir os bugs imediatos (EventType placeholder, rate limiting inativo).
