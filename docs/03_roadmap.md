# 03 — Roadmap de Engenharia Executável da MIA

> **Versão:** 0.1.0
> **Data:** 2026-09-14
> **Autor:** Engenheiro de Planejamento
> **Status:** Draft para revisão do Miguel
> **Dependências:** 01_entendimento.md, 02_especificacao.md, debate/*

---

## Sumário

1. [Visão Geral do Roadmap](#1-visão-geral-do-roadmap)
2. [Fases Detalhadas](#2-fases-detalhadas)
3. [Milestones M0–M10](#3-milestones-m0m10)
4. [Trilha Crítica](#4-trilha-crítica)
5. [Paralelização](#5-paralelização)
6. [Riscos do Roadmap](#6-riscos-do-roadmap)
7. [Ordem Recomendada com Justificativa](#7-ordem-recomendada-com-justificativa)
8. [Plano de Primeira Release (v0.1)](#8-plano-de-primeira-release-v01)
9. [Plano de MVP](#9-plano-de-mvp)
10. [Plano de Longo Prazo](#10-plano-de-longo-prazo)

---

## 1. Visão Geral do Roadmap

### 1.1 Filosofia

O roadmap é organizado por **incrementos funcionais**. Cada fase entrega algo
que pode ser executado, testado e demonstrado. Não existem fases de "especificação
pura" ou "preparação abstrata" — cada semana de trabalho resulta em um sistema
mais capaz que a semana anterior.

### 1.2 Princípios de Ordem

1. **Segurança primeiro, mas não bloqueante:** State Authority e enforcement
   físico existem desde a Fase 0, mas não travam funcionalidade.
2. **O que pode ser determinístico, é:** LLM só entra onde raciocínio
   probabilístico é genuinamente necessário.
3. **Contratos desde o início:** Interfaces entre componentes definidas antes
   da implementação — preservadas ao longo de todo o roadmap.
4. **Rollback sempre possível:** Cada fase mantém compatibilidade com a
   anterior. Schema versionado. Snapshots periódicos.
5. **Nada de meses sem resultado observável:** Cada fase fecha em 1-3 semanas.

### 1.3 Reorganização em Relação ao P4

O prompt P4 lista 17 fases (0-16). Reorganizamos com base na síntese do debate
(Cético × Visionário × Segurança):

- **Merged:** Fundação e Runtime → Fase 0 (una, com Security Manager + Kill Switch
  desde o início, conforme consenso de todos os debatedores).
- **Adiantado:** Security hardening (Policy Engine separada, sandbox) → Fase 8
  (antes de autonomia, não no fim).
- **Adiado:** Voice/Perception/Avatar → Fases 9-11 (no fim, conforme agreement
  de que dependem de base sólida + hardware).
- **Mantidos:** Todas as fases de vida interna (identidade, emoções, relações)
  estão entre Fases 3-7, na ordem que maximiza utilidade incremental.

---

## 2. Fases Detalhadas

---

### FASE 0 — Fundação (Event Bus + Config + Runtime + State Authority + Persistence)

**Duração estimada:** 2 semanas
**Objetivo:** Criar a coluna vertebral do sistema. Todo componente futuro se
conecta ao Event Bus e passa pelo State Authority.

**Pré-requisitos:**
- Repositório Git inicializado
- Python 3.11+ com virtualenv
- Especificação 02_especificacao.md revisada e aprovada

**Componentes:**
- Event Bus (in-process pub/sub síncrono, schemas validados via Pydantic)
- Config Manager (carrega, valida, disponibiliza config — secrets nunca ao LLM)
- Runtime (lifecycle: init, run, shutdown — graceful)
- State Authority (StateEngine + PolicyEngine + AuditLog)
- Persistence Layer (SQLite WAL + migrations + PersistenceBackend ABC)
- Security Manager (kill switch via flag em disco, secrets management)
- Audit Log (append-only, hash chain)

**Tarefas (checklist):**

- [ ] Estrutura de pastas do projeto (mia/, tests/, docs/, config/)
- [ ] Event Bus: classe Python com `subscribe()`, `unsubscribe()`,
      `emit()`, `emit_async()`, validação de schema, circuit breaker
- [ ] EventType enum com todos os tipos definidos na especificação
- [ ] Event schema versionado (Pydantic models por tipo)
- [ ] Config Manager: carrega YAML, valida, disponibiliza via singleton
- [ ] Secrets: variáveis de ambiente, keystore com permissão 600,
      LLM nunca acessa diretamente
- [ ] Runtime: inicialização de componentes, orquestração de lifecycle
- [ ] State Authority: `propose()`, `get_state()`, `rollback()`, `snapshot()`
- [ ] State Engine: `validate()` (ranges, schema) + `apply()` (determinístico)
- [ ] Policy Engine: `check()` (invariantes, regras YAML)
- [ ] Audit Log: tabela SQLite `CHECK(1=1)`, hash chain, retenção 90 dias
- [ ] PersistenceBackend ABC (read, write, snapshot, restore)
- [ ] SQLite backend: todas as tabelas da especificação (F.2)
- [ ] Migrations: `pragma user_version` + script automático
- [ ] Kill switch: flag `/var/mia/STOP`, verificação a cada ciclo
- [ ] Testes: State Authority rejeita escrita direta do LLM
- [ ] Testes: Policy Engine rejeita invariantes violadas
- [ ] Testes: Event Bus valida e rejeita schemas inválidos
- [ ] Testes: Audit Log é append-only (tentativa de UPDATE/DELETE falha)

**Dependências:** Nenhuma (é a primeira fase).

**Testes:**
- Unit: StateAuthority.propose() aceita/rejeita conforme schema
- Unit: PolicyEngine.check() detecta violações de invariantes
- Integration: Event Bus emite → subscriber recebe → schema validado
- Security: LLM mock tenta escrever estado diretamente → rejeitado
- Property: EmotionVector sempre em range [0,1] após qualquer transição

**Critérios de aceitação:**
1. `python -m mia` inicia o runtime sem erros
2. Event Bus entrega eventos entre subscribers com schema validado
3. State Authority rejeita qualquer tentativa de escrita direta
4. Policy Engine rejeita transições que violem invariantes
5. Audit Log registra todas as transições com hash chain íntegra
6. Kill switch parama todos os componentes em <5 segundos
7. Migrations rodam automaticamente ao iniciar com schema novo

**Riscos:**
- R0.1: Complexidade do State Authority adia início funcional
  - Mitigação: implementar StateEngine como módulo Python puro, sem dependências externas
- R0.2: Event Bus síncrono cria gargalo
  - Mitigação: throughput estimado ~10-50 eventos/hora; síncrono é suficiente

**Agentes em paralelo:**
- Agent A: Event Bus + Config Manager
- Agent B: State Authority + Policy Engine + Audit Log
- Agent C: Persistence Layer + Migrations
- Agent D: Security Manager + Kill Switch
- Todos podem trabalhar em paralelo pois dependem apenas da especificação

**Partes que esperam:** Nenhuma (fase inicial).

**Artefatos gerados:**
- `mia/event_bus/` — Event Bus implementado
- `mia/state_authority/` — State Authority com 2 engines
- `mia/persistence/` — PersistenceBackend + SQLite
- `mia/config/` — Config Manager
- `mia/security/` — Kill Switch + Secrets
- `tests/` — suite de testes de fundação
- `config/policy_rules.yaml` — regras iniciais da Policy Engine

**Definition of Done:**
Todos os 7 critérios de aceitação verificados. Testes passando.
State Authority é o componente mais pequeno e mais testado do sistema.

---

### FASE 1 — LLM Abstraction + Cognitive Core + Context Assembly

**Duração estimada:** 2 semanas
**Objetivo:** Primeira conversa funcional com estado. A MIA recebe mensagem,
monta contexto, chama LLM, interpreta resposta e propõe transições de estado.

**Pré-requisitos:**
- Fase 0 completa (Event Bus, State Authority, Persistence funcionais)

**Componentes:**
- LLM Abstraction (provider chain, fallback, retry, streaming)
- Context Assembly (monta system prompt dinâmico a partir de estado)
- Cognitive Core (loop principal: input → contexto → LLM → resposta + propostas)

**Tarefas (checklist):**

- [ ] LLMProvider ABC: `complete()`, `stream()`, `list_models()`
- [ ] OpenAI provider implementado (formato OpenAI-compatible)
- [ ] Provider chain com fallback automático
- [ ] Rate limiting por provider
- [ ] Retry com exponential backoff
- [ ] Context Assembly: monta system prompt a partir de IdentityState +
      PersonalityState + EmotionState + Relationship + últimas N mensagens
- [ ] Cognitive Core: loop principal de interação
- [ ] Interpretação de resposta: texto → resposta ao usuário;
      tool_calls → Tool Gateway; state_proposals → State Authority
- [ ] Memory candidates → Environment Memory (criação simples)
- [ ] CLI REPL funcional com `/chat`, `/state`, `/memory`, `/quit`
- [ ] Testes: LLM mock retorna resposta válida
- [ ] Testes: Context Assembly inclui estado emocional no prompt
- [ ] Testes: Cognitive Core propõe transições ao State Authority

**Dependências:** Fase 0 completa.

**Testes:**
- Unit: LLMProvider.complete() com mock retorna LLMResponse
- Integration: Mensagem do usuário → resposta gerada + state proposal aplicada
- Contract: Interface LLMProvider compatível com providers OpenAI-compatible
- E2E: REPL: input "Olá" → resposta contextualizada + memória candidate criada

**Critérios de aceitação:**
1. Mia responde a mensagens via CLI
2. Resposta é contextualizada (personalidade + emoções + memórias no prompt)
3. State proposals são aplicadas via State Authority (auditadas)
4. LLM nunca acessa estado diretamente
5. Fallback entre providers funciona (simular falha do provider primário)
6. Streaming funciona (resposta aparece token por token)

**Riscos:**
- R1.1: Custo LLM por interação (6 chamadas estimadas)
  - Mitigação: processar offline o máximo; LLM só para raciocínio genuíno
- R1.2: Context Assembly seleciona contexto irrelevante
  - Mitigação: keyword search + ranking por importância e recência

**Agentes em paralelo:**
- Agent A: LLM Abstraction (providers, fallback, retry)
- Agent B: Context Assembly + Cognitive Core
- Agent C: CLI REPL + Tool Gateway stub

**Partes que esperam:** Fase 0 (State Authority precisa existir).

**Artefatos gerados:**
- `mia/llm/` — LLM Abstraction + providers
- `mia/cognitive/` — Cognitive Core + Context Assembly
- `mia/cli/` — REPL funcional
- Testes de integração LLM → State Authority

**Definition of Done:**
Mia conversa via CLI. Resposta é contextualizada.
Todas as transições de estado passam pelo State Authority.

---

### FASE 2 — Memória

**Duração estimada:** 2 semanas
**Objetivo:** Mia lembra. Memory Objects com schema rígido, keyword search,
importance scoring, consolidação periódica.

**Pré-requisitos:**
- Fase 1 completa (Cognitive Core funcional)

**Componentes:**
- Memory Manager (CRUD, scoring, consolidação)
- Retrieval Engine (keyword search — BM25 leve)
- Memory Consolidation (sumarização periódica de conversas em Memory Objects)
- Scheduler (tarefas agendadas: consolidação, limpeza)

**Tarefas (checklist):**

- [ ] Memory Manager: CRUD de MemoryObjects (Pydantic + SQLite)
- [ ] Importance scoring: regra determinística + LLM como opt-in
- [ ] Memory scopes: personal, shared, private
- [ ] Memory associations: tabela memory_associations
- [ ] Retrieval: keyword search com ranking por importância × recência
- [ ] Memory Consolidation: conversas viram Memory Objects após N turns
- [ ] Scheduler: consolidação periódica (cron configurable)
- [ ] Scheduler: limpeza de memórias expiradas (retention policy)
- [ ] Context Assembly atualizado: inclui memórias recuperadas no prompt
- [ ] Testes: Memory CRUD + importance scoring
- [ ] Testes: Retrieval retorna memórias relevantes para query
- [ ] Testes: Consolidação cria MemoryObjects a partir de conversas

**Dependências:** Fase 1 (Cognitive Core que gera memory candidates).

**Testes:**
- Unit: MemoryManager.create/recall/update/delete
- Unit: Importance scoring retorna valores coerentes
- Integration: Conversa → memory candidate → MemoryObject persistido
- Integration: Retrieval por keyword encontra memória relevante
- E2E: Mia menciona algo de conversa anterior (memória recuperada no contexto)

**Critérios de aceitação:**
1. MemoryObjects são criados, persistidos e recuperados
2. Importance scoring asigna valores coerentes (0.0-1.0)
3. Retrieval encontra memórias relevantes por keyword
4. Consolidação periódica cria resumos de conversas
5. Memórias aparecem no contexto do LLM (Context Assembly)
6. Mia pode mencionar coisas de conversas anteriores

**Riscos:**
- R2.1: Retrieval por keyword é insuficiente para recall contextual
  - Mitigação: embeddings como opt-in futuro; keyword basta para MVP
- R2.2: Muitas memórias irrelevantes poluem o contexto
  - Mitigação: threshold mínimo de importância; limpeza periódica

**Agentes em paralelo:**
- Agent A: Memory Manager + CRUD + schemas
- Agent B: Retrieval Engine (keyword search)
- Agent C: Scheduler + Consolidação

**Partes que esperam:** Fase 1 (Cognitive Core).

**Artefatos gerados:**
- `mia/memory/` — Memory Manager + Retrieval
- `mia/scheduler/` — Scheduler + Consolidação
- Testes de memória e retrieval

**Definition of Done:**
Mia lembra coisas de conversas anteriores.
Memórias são relevantes e recuperadas corretamente.

---

### FASE 3 — Identidade / Self Model / Personalidade

**Duração estimada:** 2 semanas
**Objetivo:** Mia sabe quem é. Self-model persistente, personality vector
evolutiva, identidade como estado externo (não prompt).

**Pré-requisitos:**
- Fase 2 completa (Memory funcional)

**Componentes:**
- Identity Store (self_model, core_values, versionamento)
- Personality Store (Big Five + extras, vetor evolutivo)
- Identity Authority (gerencia transições de identidade)
- Context Assembly atualizado: gera system prompt a partir de estado

**Tarefas (checklist):**

- [ ] IdentityState schema implementado (Pydantic + SQLite)
- [ ] Self-model: JSON persistente com crenças sobre si mesma
- [ ] Core values: lista imutável (não pode ser deletada — Policy Engine)
- [ ] PersonalityVector: Big Five + curiosity, playfulness, assertiveness,
      empathy, independence
- [ ] Personality como estado persistente, não system prompt
- [ ] Versionamento: snapshot + diff de versões passadas
- [ ] Context Assembly: system prompt gerado dinamicamente a partir de
      IdentityState + PersonalityState
- [ ] Identity Authority: transições de identidade validadas pelo SA
- [ ] Testes: IdentityStore persiste e recupera self-model
- [ ] Testes: PersonalityVector sempre em range [0,1]
- [ ] Testes: System prompt reflete personalidade atual

**Dependências:** Fase 2 (Memory para context).

**Testes:**
- Unit: IdentityStore.save/load/version
- Unit: PersonalityVector ranges validados
- Integration: PersonalityState afeta system prompt gerado
- Security: Policy Engine impede deleção de core_values
- E2E: Mia descreve quem é consistentemente ao longo de conversas

**Critérios de aceitação:**
1. IdentityState é persistente e versionada
2. PersonalityVector evolui com base em interações
3. System prompt é gerado dinamicamente (não é string estática)
4. Mia descreve quem é de forma coerente
5. Mudanças de personalidade são auditadas
6. Core values não podem ser deletados

**Riscos:**
- R3.1: Personalidade "flutua" demais entre conversas
  - Mitigação: rate limiting de mudanças + mood como suavização temporal
- R3.2: Self-model diverge do comportamento observável
  - Mitigação: validação periódica entre self-model e interações reais

**Agentes em paralelo:**
- Agent A: Identity Store + self-model
- Agent B: Personality Store + personality vector
- Agent C: Context Assembly atualizado + system prompt dinâmico

**Partes que esperam:** Fase 2.

**Artefatos gerados:**
- `mia/identity/` — Identity Store + Authority
- `mia/personality/` — Personality Store
- Testes de identidade e personalidade

**Definition of Done:**
Mia tem identidade persistente.
Personalidade é estado, não prompt.
Mia descreve quem é consistentemente.

---

### FASE 4 — Emoção / Sensação / Mood / Necessidades

**Duração estimada:** 2 semanas
**Objetivo:** Mia tem vida interna emocional. Vetor de emoções, mood como
suavização temporal, sensações sem causa consciente imediata, necessidades
básicas.

**Pré-requisitos:**
- Fase 3 completa (Identity + Personality funcionais)

**Componentes:**
- Emotion Store (EmotionVector, persistência)
- Mood Engine (suavização temporal, VAD: valence-arousal-dominance)
- Sensation Generator (stochastic ou delayed attribution)
- Needs Tracker (lista simples de unmet_needs)

**Tarefas (checklist):**

- [ ] EmotionVector: happiness, sadness, anger, fear, surprise, disgust,
      trust, anticipation + derivados (curiosity, loneliness, affection, boredom)
- [ ] Persistência em SQLite (emotion_state table)
- [ ] Atualização: LLM propõe deltas → State Authority valida → aplica
- [ ] Rate limiting: máx 10 mudanças emocionais por hora
- [ ] MoodEngine: VAD (valence, arousal, dominance) computado
      determinísticamente como média ponderada das últimas N horas
- [ ] Sensations: lista persistida com possible_causes (não certezas)
- [ ] Sensation strategy: delayed attribution (causa existe, LLM não tem
      acesso imediato — investigação retroativa)
- [ ] Needs Tracker: lista de unmet_needs simples, atualizada pelo LLM
- [ ] Context Assembly: humor influencia tom da resposta
- [ ] Eventos: LONELINESS_CHANGED emitido quando loneliness muda
- [ ] Testes: EmotionVector sempre em range [0,1]
- [ ] Testes: Mood computado corretamente
- [ ] Testes: Sensations persistidas com possible_causes

**Dependências:** Fase 3 (Identity + Personality para contexto emocional).

**Testes:**
- Unit: EmotionVector ranges validados (hypothesis)
- Unit: MoodEngine computes VAD corretamente
- Integration: Evento MIGUEL_SPOKE → emoção muda → mood atualizado
- Integration: Sensação persistida com possible_causes
- Property: EmotionVector sempre normalizada após qualquer transição

**Critérios de aceitação:**
1. Mia expressa emoções coerentes com contexto
2. Mood muda suavemente ao longo do tempo (não step function)
3. Sensações sem causa consciente imediata funcionam
4. Necessidades básicas são rastreadas
5. Emoções influenciam tom da resposta
6. Rate limiting impede flutuação emocional excessiva

**Riscos:**
- R4.1: Emoções produzem resultados nonsense
  - Mitigação: validação empírica com cenários reais; ajuste de pesos
- R4.2: Sensações são confusas para o usuário
  - Mitigação: transparência quando solicitado ("estou investigando")

**Agentes em paralelo:**
- Agent A: Emotion Store + EmotionVector
- Agent B: Mood Engine + Sensations
- Agent C: Needs Tracker + Context Assembly atualizado

**Partes que esperam:** Fase 3.

**Artefatos gerados:**
- `mia/affective/` — Emotion Store + Mood Engine
- `mia/sensations/` — Sensation Generator
- `mia/needs/` — Needs Tracker
- Testes de emoção, mood e sensações

**Definition of Done:**
Mia expressa emoções coerentes.
Mood muda suavemente.
Sensações sem causa funcionam.

---

### FASE 5 — Relacionamentos / Contexto Social / Limites

**Duração estimada:** 1-2 semanas
**Objetivo:** Mia reconhece e responde diferentemente a diferentes pessoas.
Relacionamentos dimensionais, limites sociais, detecção de ofensa.

**Pré-requisitos:**
- Fase 4 completa (Emoções funcionais)

**Componentes:**
- People Store (perfis de pessoas)
- Relationship Store (trust, intimacy, affinity, familiarity)
- Social Evaluator (classifica interações: positiva, negativa, neutra)
- Boundary Manager (limites sociais, detecção de ofensa/insulto)

**Tarefas (checklist):**

- [ ] People Store: CRUD de Person (nome, first_seen, last_seen, metadata)
- [ ] Relationship Store: trust, intimacy, affinity, familiarity,
      interaction_count, history
- [ ] Relationship Events: histórico de interações significativas
- [ ] Social Evaluator: classifica input como positivo/negativo/neutro
      (classificador leve, não LLM)
- [ ] Boundary Manager: detecção de ofensa/insulto, resposta apropada
- [ ] Eventos: MIGUEL_SPOKE, INSULT_RECEIVED, COMPLIMENT_RECEIVED,
      NEW_PERSON_DETECTED
- [ ] Context Assembly: relationship afeta tom (mais íntimo → mais informal)
- [ ] Policy Engine: limites de intimidade respeitados
- [ ] Testes: Relationship persiste e evolui com interações
- [ ] Testes: Ofensa é detectada e Boundary Manager responde

**Dependências:** Fase 4 (Emoções para reações sociais).

**Testes:**
- Unit: RelationshipStore.save/load/update
- Unit: SocialEvaluator classifica corretamente
- Integration: Input negativo → raiva + trust decrease
- Integration: Input positivo → alegria + affinity increase
- E2E: Mia responde diferentemente a Miguel vs. desconhecido

**Critérios de aceitação:**
1. People e Relationships são persistidos
2. Interações afetam dimensões de relacionamento
3. Mia responde diferentemente baseado em quem fala
4. Ofensas são detectadas e Boundary Manager reage
5. Trust e intimacy evoluem coerentemente

**Riscos:**
- R5.1: Detecção de ofensa gera falsos positivos
  - Mitigação: classificador leve + confirmação contextual
- R5.2: Relacionamentos evoluem rápido demais
  - Mitigação: rate limiting + suavização temporal

**Agentes em paralelo:**
- Agent A: People + Relationship Store
- Agent B: Social Evaluator + Boundary Manager

**Partes que esperam:** Fase 4.

**Artefatos gerados:**
- `mia/social/` — People + Relationship Store
- `mia/social/evaluator.py` — Social Evaluator
- `mia/social/boundaries.py` — Boundary Manager

**Definition of Done:**
Mia reconhece pessoas diferentes.
Relacionamentos evoluem com interações.
Limites sociais são respeitados.

---

### FASE 6 — Objetivos / Motivação / Iniciativa / Atenção

**Duração estimada:** 2 semanas
**Objetivo:** Mia pode manter objetivos e agir autonomamente quando Miguel
está offline. Goals, initiative, scheduler melhorado.

**Pré-requisitos:**
- Fase 5 completa (Relacionamentos funcionais)

**Componentes:**
- Goal Store (persistência de objetivos)
- Initiative Engine (decide o que fazer quando idle)
- Attention Manager (prioriza estímulos)
- Resource Governor (limites de custo/tempo/concorrência)

**Tarefas (checklist):**

- [ ] Goal Store: CRUD de Goals (descrição, prioridade, status, progresso)
- [ ] Initiative Engine: quando idle, verifica goals e executa ações
- [ ] Attention Manager: prioriza estímulos (urgência × relevância × novelty)
- [ ] Resource Governor: limites configuráveis (custo, tempo, concorrência)
- [ ] Scheduler melhorado: wake-on-event + wake-on-timer
- [ ] Eventos: MIGUEL_LEFT, MIGUEL_RETURNED, TASK_FAILED, TASK_COMPLETED
- [ ] Modo idle: consolida memórias, reflete (diário básico), pesquisa
- [ ] Testes: Goals persistem entre sessões
- [ ] Testes: Initiative Engine executa ações quando idle
- [ ] Testes: Resource Governor impede execução além dos limites

**Dependências:** Fase 5 (Relacionamentos + Social context).

**Testes:**
- Unit: GoalStore CRUD + status transitions
- Unit: Resource Governor enforce limits
- Integration: MIGUEL_LEFT → Initiative Engine executa goal
- Integration: Resource Governor kill processa oltre limiti
- E2E: Mia executa tarefa autônoma e registra resultado

**Critérios de aceitação:**
1. Goals são persistidos e rastreados
2. Mia executa ações quando idle (autonomia básica)
3. Resource Governor impede excesso de custo/tempo
4. Modo idle é produtivo (consolida memórias, reflete)
5. MIGUEL_RETURNED恢复 contexto da ausência

**Riscos:**
- R6.1: Ações autônomas geram custo inesperado
  - Mitigação: Resource Governor com limites rígidos
- R6.2: Initative Engine executa ações inadequadas
  - Mitigação:Policy Engine valida ações antes de executar

**Agentes em paralelo:**
- Agent A: Goal Store + Initiative Engine
- Agent B: Attention Manager + Resource Governor
- Agent C: Scheduler + Modo idle

**Partes que esperam:** Fase 5.

**Artefatos gerados:**
- `mia/autonomy/` — Goal Store + Initiative Engine
- `mia/autonomy/attention.py` — Attention Manager
- `mia/autonomy/resource_governor.py` — Resource Governor

**Definition of Done:**
Mia mantém objetivos.
Executa ações autônomas com limites.
Modo idle é produtivo.

---

### FASE 7 — Reflexão / Diário / Imaginação / Revisão de Crenças

**Duração estimada:** 2 semanas
**Objetivo:** Mia reflete sobre si mesma e o mundo. Diário subjetivo,
imaginação controlada, revisão de crenças baseada em evidência.

**Pré-requisitos:**
- Fase 6 completa (Autonomia funcional)
- Fase 2 completa (Memória funcional)

**Componentes:**
- Diary Store (append-only log + sumarização)
- Reflection Engine (gera reflexões a partir de estado + memórias)
- Imagination Engine (simula cenários hipotéticos)
- Belief Store (crenças revisáveis com evidência)

**Tarefas (checklist):**

- [ ] Diary Store: append-only SQLite (moment, summary, reflection)
- [ ] Diary: sumarização periódica (1x/dia, LLM gera resumo)
- [ ] Reflection Engine: gera reflexões a partir de estado + memórias
- [ ] Imagination Engine: simula cenários hipotéticos (LLM com
      prompt especializado)
- [ ] Belief Store: crenças com evidência, confiança, data
- [ ] Revisão de crenças: quando nova evidência contradiz crença,
      confiança diminui; quando confiança < threshold, crença é
      "esquecida" ou marcada como obsoleta
- [ ] Context Assembly: crenças influenciam interpretação do mundo
- [ ] Eventos: CURIOSITY_TRIGGERED, RESEARCH_COMPLETED
- [ ] Testes: Diary persiste e sumariza corretamente
- [ ] Testes: Belief Store revisa crenças com nova evidência

**Dependências:** Fase 6 (Autonomia) + Fase 2 (Memória).

**Testes:**
- Unit: DiaryStore.append/summarize
- Unit: BeliefStore.create/update/review
- Integration: Reflexão gerada a partir de estado + memórias
- Integration: Crença revisada quando evidência contradiz
- E2E: Mia reflete sobre dia e registra no diário

**Critérios de aceitação:**
1. Diário é persistido e sumarizado
2. Reflexões são geradas a partir de estado real
3. Crenças são revisadas quando evidência contradiz
4. Imagination Engine simula cenários coherentemente
5. Crenças influenciam interpretação do mundo

**Riscos:**
- R7.1: Reflexões são genéricas demais
  - Mitigação: prompt especializado + contexto específico
- R7.2: Revisão de crenças é instável
  - Mitigação: threshold conservador + rate limiting

**Agentes em paralelo:**
- Agent A: Diary Store + Sumarização
- Agent B: Reflection Engine + Imagination Engine
- Agent C: Belief Store + Revisão

**Partes que esperam:** Fase 6 + Fase 2.

**Artefatos gerados:**
- `mia/reflection/` — Diary + Reflection + Imagination
- `mia/beliefs/` — Belief Store

**Definition of Done:**
Mia reflete e registra no diário.
Crenças são revisadas com evidência.
Imagination Engine simula cenários.

---

### FASE 8 — Security Hardening

**Duração estimada:** 2 semanas
**Objetivo:** Reforçar segurança antes de autonomia avançada e autoevolução.
Policy Engine separada, sandbox preparado, secrets management robusto.

**Pré-requisitos:**
- Fase 0 completa (State Authority + Audit Log)
- Fases 1-7 funcionais

**Componentes:**
- Policy Engine separada (independente do State Engine)
- Enhanced Audit Log (alertas de taxa anormal)
- Secrets Hardening (keystore, redação automática, auditoria)
- Sandbox Framework (preparação para autoevolução futura)
- Integrity Checker (hash chain verification periódica)

**Tarefas (checklist):**

- [ ] Policy Engine como módulo independente (não embutida no SA)
- [ ] Policy rules em YAML: declarativas, auditáveis, versionadas
- [ ] Rate limiting configurável por tipo de transição
- [ ] Alertas: taxa anormal de transições → modo read-only + alerta
- [ ] Secrets: redação automática em logs (`***`)
- [ ] Secrets: auditoria de operações que usaram credenciais
- [ ] Integrity Checker: verificação periódica do hash chain
- [ ] Sandbox Framework: interface para containers isolados (Docker/nsjail)
- [ ] Sandbox: sem rede, sem estado produção, sem secrets
- [ ] Rollback automático: snapshot antes + revert se health check falhar
- [ ] Testes: Policy Engine rejeita code changes (MVP)
- [ ] Testes: Integrity Checker detecta corrupção no audit log
- [ ] Testes: Sandbox isola código corretamente

**Dependências:** Fases 0-7 (sistema funcional para proteger).

**Testes:**
- Unit: Policy Engine rejeita code changes
- Unit: Integrity Checker detecta corrupção
- Integration: Alertas disparam quando taxa anormal
- Security: LLM não acessa secrets nem estado diretamente
- Security: Sandbox isola código testado

**Critérios de aceitação:**
1. Policy Engine é módulo independente e testável
2. Alertas de taxa anormal funcionam
3. Secrets são redactados em todos os logs
4. Hash chain é verificável e íntegra
5. Sandbox Framework está pronto para autoevolução
6. Rollback automático funciona

**Riscos:**
- R8.1: Security hardening bloqueia funcionalidade
  - Mitigação: testes de regressão antes e depois

**Agentes em paralelo:**
- Agent A: Policy Engine separada + alertas
- Agent B: Secrets hardening + auditoria
- Agent C: Sandbox Framework + integrity checker

**Partes que esperam:** Fases 0-7.

**Artefatos gerados:**
- `mia/security/policy_engine.py` — Policy Engine separada
- `mia/security/alerts.py` — Alertas de taxa
- `mia/security/secrets.py` — Secrets hardening
- `mia/security/sandbox.py` — Sandbox Framework
- `mia/security/integrity.py` — Integrity Checker

**Definition of Done:**
Security hardening completo.
Policy Engine é independente.
Sandbox pronto para autoevolução.

---

### FASE 9 — Voz

**Duração estimada:** 3 semanas
**Objetivo:** Mia pode falar e ouvir. VAD, STT, speaker recognition,
TTS com prosódia.

**Pré-requisitos:**
- Fase 8 completa (Security hardening)
- Hardware: microfone + speaker disponíveis

**Componentes:**
- Voice Pipeline (VAD → STT → speaker recognition → directed-speech)
- TTS Engine (texto → fala com prosódia)
- Voice Context (quem fala afeta interpretação)
- Audio Event Bus (eventos de áudio tipados)

**Tarefas (checklist):**

- [ ] VAD (Voice Activity Detection): detecta fala vs. silêncio
- [ ] STT: Whisper ou equivalente para transcrição
- [ ] Speaker Recognition: identifica quem está falando
- [ ] Directed-speech Detection: detecta se fala é dirigida à MIA
- [ ] TTS: texto → fala (edge TTS ou OpenAI TTS)
- [ ] Prosody: emoções influenciam entonação
- [ ] Voice Context: speaker id → relationship lookup
- [ ] Audio Event Bus: eventos tipados de áudio
- [ ] Integração com Cognitive Core: voz como input adicional
- [ ] Testes: VAD detecta fala corretamente
- [ ] Testes: STT transcreve com acurácia aceitável
- [ ] Testes: TTS gera áudio coerente

**Dependências:** Fase 8 (Security) + hardware.

**Testes:**
- Unit: VAD detecta atividade de fala
- Unit: STT transcreve áudio sample
- Integration: Voz → transcrição → resposta → TTS
- E2E: Conversa por voz com MIA

**Critérios de aceitação:**
1. VAD detecta fala vs. silêncio
2. STT transcreve com acurácia >90%
3. TTS gera fala natural e coerente
4. Speaker recognition identifica pessoas conhecidas
5. Directed-speech detection ignora conversas entre terceiros
6. Prosódia reflete estado emocional

**Riscos:**
- R9.1: Latência de voz é alta (VAD → STT → LLM → TTS)
  - Mitigação: pipeline otimizado, cache de respostas frequentes
- R9.2: Speaker recognition falha em ambientes ruidosos
  - Mitigação: fallback para "desconhecido", treinamento progressivo

**Agentes em paralelo:**
- Agent A: VAD + STT
- Agent B: Speaker Recognition + Directed-speech
- Agent C: TTS + Prosody

**Partes que esperam:** Fase 8 + hardware.

**Artefatos gerados:**
- `mia/voice/` — Voice Pipeline completa
- `mia/voice/tts.py` — TTS Engine
- `mia/voice/stt.py` — STT + Speaker Recognition

**Definition of Done:**
Mia pode falar e ouvir.
Voz é coerente com estado emocional.
Speaker recognition funciona.

---

### FASE 10 — Visão / Percepção

**Duração estimada:** 3 semanas
**Objetivo:** Mia percebe o mundo ao redor. Câmera, sensores, percepção
multimodal.

**Pré-requisitos:**
- Fase 9 completa (Voz funcional)
- Hardware: câmera disponível

**Componentes:**
- Vision Pipeline (câmera → frames → análise → eventos)
- Perception Aggregator (combina múltiplos sensores)
- Context Enricher (percepção alimenta contexto)

**Tarefas (checklist):**

- [ ] Vision Pipeline: captura frames → análise por LLM de visão
- [ ] Perception Aggregator: combina visão + áudio + outros sensores
- [ ] Eventos: CAMERA_ACTIVITY_DETECTED, NEW_PERSON_DETECTED
- [ ] Context Enricher: percepção enriquece contexto para Cognitive Core
- [ ] Privacy: rostos de terceiros são processados localmente
- [ ] Rate limiting: análise visual não excede budget
- [ ] Testes: Vision Pipeline detecta atividade
- [ ] Testes: Perception Aggregator combina sensores corretamente

**Dependências:** Fase 9 (Voz).

**Testes:**
- Unit: Vision Pipeline analisa frame
- Integration: Percepção alimenta eventos no Event Bus
- E2E: Mia reage a algo visto pela câmera

**Critérios de aceitação:**
1. Vision Pipeline detecta atividade visual
2. Percepção é convertida em eventos tipados
3. Contexto visual enriquece respostas
4. Privacy é respeitada (processamento local)
5. Rate limiting impede excesso de análise

**Riscos:**
- R10.1: Custos de análise visual são altos
  - Mitigação: rate limiting + cache + modelos leves
- R10.2: Privacidade comprometida
  - Mitigação: processamento local, sem upload de imagens

**Agentes em paralelo:**
- Agent A: Vision Pipeline
- Agent B: Perception Aggregator + Context Enricher

**Partes que esperam:** Fase 9 + hardware.

**Artefatos gerados:**
- `mia/perception/` — Vision Pipeline + Perception Aggregator
- `mia/perception/vision.py` — Vision Pipeline

**Definition of Done:**
Mia percebe o mundo visual.
Percepção alimenta eventos.
Privacy é respeitada.

---

### FASE 11 — Avatar / Embodiment

**Duração estimada:** 4 semanas
**Objetivo:** Mia tem presença visual. Avatar digital com expressões
faciais que refletem estado emocional.

**Pré-requisitos:**
- Fase 10 completa (Percepção funcional)
- Fase 4 completa (Emoções para expressão facial)

**Componentes:**
- Avatar Renderer (2D/3D, expressões faciais)
- Expression Mapper (EmotionState → facial expression)
- Avatar Sync (estado em tempo real → expressão)
- Avatar API (interface para sistemas externos)

**Tarefas (checklist):**

- [ ] Avatar Renderer: personagem visual com expressões
- [ ] Expression Mapper: emoções → expressões faciais
- [ ] Avatar Sync: atualização em tempo real
- [ ] Avatar API: interface para integração
- [ ] Testes: Expressões refletem estado emocional
- [ ] Testes: Sync é responsivo (<100ms)

**Dependências:** Fase 10 + Fase 4.

**Testes:**
- Unit: ExpressionMapper mapeia emoções corretamente
- Integration: EmotionState change → expressão facial atualizada
- E2E: Avatar reflete estado emocional em tempo real

**Critérios de aceitação:**
1. Avatar é visualmente coerente
2. Expressões refletem estado emocional
3. Sync é responsivo
4. Avatar API permite integração

**Riscos:**
- R11.1: Expressões parecem "uncanny"
  - Mitigação: estilo cartoon/estilizado, não realista
- R11.2: Sync tem latência perceptível
  - Mitigação: processamento local, atualização por delta

**Agentes em paralelo:**
- Agent A: Avatar Renderer + Expression Mapper
- Agent B: Avatar Sync + API

**Partes que esperam:** Fase 10 + Fase 4.

**Artefatos gerados:**
- `mia/avatar/` — Avatar Renderer + Expression Mapper
- `mia/avatar/api.py` — Avatar API

**Definition of Done:**
Avatar reflete estado emocional.
Sync é responsivo.
Avatar API funciona.

---

### FASE 12 — Nós Distribuídos / Mobile / Desktop

**Duração estimada:** 4 semanas
**Objetivo:** Mia opera em múltiplos dispositivos. VPS como master,
PC/mobile como clientes com sync.

**Pré-requisitos:**
- Fase 8 completa (Security hardening)
- PersistenceBackend swappable

**Componentes:**
- Node Manager (detecta e gerencia nós)
- Sync Engine (SQLite snapshot + event sync)
- Offline Mode (funciona com último snapshot)
- Conflict Resolver (consistência eventual, mestre único para estado)

**Tarefas (checklist):**

- [ ] Node Manager: detecta nós disponíveis
- [ ] Sync Engine: snapshot periódico VPS → clientes
- [ ] Sync Engine: eventos entre nós (fila simples)
- [ ] Offline Mode: funciona com último snapshot
- [ ] Conflict Resolver: escritas roteadas ao VPS (master)
- [ ] Testes: Sync entre VPS e cliente
- [ ] Testes: Offline mode funciona
- [ ] Testes: Conflict resolution (master wins)

**Dependências:** Fase 8 + PersistenceBackend.

**Testes:**
- Unit: SyncEngine serializa/deserializa snapshot
- Integration: VPS ↔ cliente sync funcional
- E2E: Mia funciona em mobile com sync do VPS

**Critérios de aceitação:**
1. Sync entre VPS e clientes funciona
2. Offline mode funcional
3. Escritas roteadas ao VPS (master)
4. Consistência eventual mantida

**Riscos:**
- R12.1: Sync é complexo demais
  - Mitigação: sync simples, não CRDTs; master único
- R12.2: Offline mode perde dados
  - Mitigação: fila de eventos local + sync quando reconectar

**Agentes em paralelo:**
- Agent A: Node Manager + Sync Engine
- Agent B: Offline Mode + Conflict Resolver

**Partes que esperam:** Fase 8.

**Artefatos gerados:**
- `mia/distributed/` — Node Manager + Sync Engine
- `mia/distributed/offline.py` — Offline Mode

**Definition of Done:**
Sync entre nós funciona.
Offline mode funcional.
Master único para estado.

---

### FASE 13 — Subagentes / Orquestração

**Duração estimada:** 3 semanas
**Objetivo:** Mia pode delegar tarefas a subagentes com limites rígidos.
Multi-agent com Resource Governor.

**Pré-requisitos:**
- Fase 6 completa (Autonomia funcional)
- Fase 8 completa (Security hardening)

**Componentes:**
- Agent Registry (registro e lifecycle de agentes)
- Orchestrator (routing, delegação, consenso básico)
- Resource Governor (limites de profundidade, custo, tempo, concorrência)
- Agent Templates (tipos predefinidos: research, code, social)

**Tarefas (checklist):**

- [ ] Agent Registry: registro, lifecycle, capabilities
- [ ] Orchestrator: routing baseado em capabilities
- [ ] Delegação: agente pode delegar a sub-agente
- [ ] Limites: max profundidade 3, max custo configurável,
      max concorrência 3, max tempo 30min
- [ ] Resource Governor: verifica limites em tempo real
- [ ] Kill switch por agente
- [ ] Agent Templates: research, code, social (básicos)
- [ ] Testes: Delegação com limites respeitados
- [ ] Testes: Resource Governor kill processa além dos limites

**Dependências:** Fase 6 + Fase 8.

**Testes:**
- Unit: Resource Governor enforce limits
- Integration: Delegação funciona com limites
- Security: Subagente não excede profundidade/custo/tempo
- E2E: Mia delega pesquisa e recebe resultado

**Critérios de aceitação:**
1. Subagentes são registrados e gerenciados
2. Delegação funciona com limites rígidos
3. Resource Governor impede excesso
4. Kill switch por agente funciona
5. Consenso básico entre agentes (MVP)

**Riscos:**
- R13.1: Subagentes escalam custo exponencialmente
  - Mitigação: Resource Governor com limites rígidos
- R13.2: Orquestração é complexa demais
  - Mitigação: agente único primeiro; multi-agent progressivo

**Agentes em paralelo:**
- Agent A: Agent Registry + Orchestrator
- Agent B: Resource Governor + Kill switch
- Agent C: Agent Templates

**Partes que esperam:** Fase 6 + Fase 8.

**Artefatos gerados:**
- `mia/agents/` — Agent Registry + Orchestrator
- `mia/agents/resource_governor.py` — Resource Governor
- `mia/agents/templates/` — Agent Templates

**Definition of Done:**
Subagentes funcionam com limites.
Resource Governor impede excesso.
Orquestração básica funciona.

---

### FASE 14 — World Awareness

**Duração estimada:** 2 semanas
**Objetivo:** Mia pode pesquisar o mundo. News, web scraping, knowledge
base, interest tracking.

**Pré-requisitos:**
- Fase 7 completa (Reflexão + Beliefs)
- Fase 13 completa (Subagentes para pesquisa)

**Componentes:**
- Research Agent (pesquisa web,新闻, knowledge)
- Interest Tracker (rastreia interesses da MIA)
- Relevance Scorer (avalia relevância de informação)
- Knowledge Store (armazena descobertas)

**Tarefas (checklist):**

- [ ] Research Agent: pesquisa web + sumarização
- [ ] Interest Tracker: interesses baseados em personalidade + interações
- [ ] Relevance Scorer: avaliasse se informação é relevante para MIA
- [ ] Knowledge Store: armazena descobertas como Memory Objects
- [ ] Eventos: RESEARCH_COMPLETED
- [ ] Modo idle: pesquisa autônoma baseada em interesses
- [ ] Testes: Research Agent encontra informação relevante
- [ ] Testes: Interest Tracker rastreia interesses

**Dependências:** Fase 7 + Fase 13.

**Testes:**
- Unit: RelevanceScorer avalia corretamente
- Integration: Research Agent → Knowledge Store → memória
- E2E: Mia pesquisa tópico de interesse autonomamente

**Critérios de aceitação:**
1. Research Agent encontra informação relevante
2. Interest Tracker rastreia interesses
3. Knowledge Store persiste descobertas
4. Pesquisa autônoma funciona no modo idle

**Riscos:**
- R14.1: Pesquisa é custosa (chamadas LLM + web)
  - Mitigação: rate limiting + relevância threshold
- R14.2: Informação irrelevante polui memória
  - Mitigação: Relevance Scorer com threshold alto

**Agentes em paralelo:**
- Agent A: Research Agent + Knowledge Store
- Agent B: Interest Tracker + Relevance Scorer

**Partes que esperam:** Fase 7 + Fase 13.

**Artefatos gerados:**
- `mia/world/` — Research Agent + Knowledge Store
- `mia/world/interests.py` — Interest Tracker

**Definition of Done:**
Research Agent funciona.
Interesses são rastreados.
Pesquisa autônoma é produtiva.

---

### FASE 15 — Autoevolução / Criação de Ferramentas

**Duração estimada:** 3 semanas
**Objetivo:** Mia pode participar da própria evolução com segurança.
Autoevolução restrita a parâmetros (MVP). Criação de ferramentas básica.

**Pré-requisitos:**
- Fase 8 completa (Security hardening + Sandbox)
- Fases 0-7 funcionais e estáveis

**Componentes:**
- Evolution Engine (gera propostas de melhoria)
- Parameter Evolver (ajusta weights e thresholds)
- Tool Creator (cria ferramentas simples)
- Canary Deployer (staging antes de produção)
- Rollback Manager (revert automático)

**Tarefas (checklist):**

- [ ] Evolution Engine: gera propostas de melhoria
- [ ] Parameter Evolver: ajusta weights (emoção, personalidade, memória)
- [ ] Tool Creator: cria ferramentas simples (scripts Python)
- [ ] Canary Deployer: staging por 24-48h antes de produção
- [ ] Rollback Manager: snapshot antes + revert se health check falhar
- [ ] Limites MVP: apenas parâmetros, não código core
- [ ] Code changes: requer aprovação humana (Miguel)
- [ ] Core runtime, State Authority, Policy Engine: IMUNES
- [ ] Testes: Parameter Evolver ajusta dentro de ranges
- [ ] Testes: Rollback funciona
- [ ] Testes: Code changes são rejeitados (MVP)

**Dependências:** Fase 8 + Fases 0-7 estáveis.

**Testes:**
- Unit: Parameter Evolver ajusta dentro de ranges
- Unit: Rollback Manager reverte corretamente
- Integration: Proposta de evolução → validação → aplicação
- Security: Code changes são rejeitados (MVP)
- Security: Core components são imunes

**Critérios de aceitação:**
1. Parameter Evolver ajusta weights com validação
2. Code changes são rejeitados (MVP)
3. Rollback automático funciona
4. Canary deploy funciona
5. Core components são imunes a auto-modificação
6. Aprovação humana é exigida para code changes

**Riscos:**
- R15.1: Autoevolução corrompe estado
  - Mitigação: sandbox, verificador independente, canary, rollback
- R15.2: Parameter evolver cria oscilações
  - Mitigação: rate limiting, thresholds conservadores

**Agentes em paralelo:**
- Agent A: Evolution Engine + Parameter Evolver
- Agent B: Tool Creator + Canary Deployer
- Agent C: Rollback Manager + Health checks

**Partes que esperam:** Fase 8 + Fases 0-7.

**Artefatos gerados:**
- `mia/evolution/` — Evolution Engine + Parameter Evolver
- `mia/evolution/tools.py` — Tool Creator
- `mia/evolution/deploy.py` — Canary Deployer + Rollback Manager

**Definition of Done:**
Autoevolução de parâmetros funciona.
Code changes são rejeitados.
Rollback automático funciona.
Core components são imunes.

---

### FASE 16 — Mia Integrada e Autônoma

**Duração estimada:** 4 semanas
**Objetivo:** Integração completa. Todos os componentes funcionam juntos.
Testes end-to-end. Polish. Documentação.

**Pré-requisitos:**
- Fases 0-15 completas

**Componentes:**
- Integration Tests (fluxos completos E2E)
- Performance Tuning (latência, throughput)
- Documentation (guia de uso, API docs)
- Monitoring (dashboard de saúde)
- Backup/Restore (snapshots completos)

**Tarefas (checklist):**

- [ ] Testes E2E: fluxo completo de interação
- [ ] Testes E2E: modo idle produtivo
- [ ] Testes E2E: autoevolução segura
- [ ] Testes E2E: multi-agent funcional
- [ ] Performance: latência <2s por resposta
- [ ] Performance: throughput de eventos adequate
- [ ] Documentação: guia de uso
- [ ] Documentação: API docs
- [ ] Monitoring: dashboard de saúde
- [ ] Backup/Restore: snapshots completos
- [ ] Rollback testado em todos os cenários
- [ ] Security audit final

**Dependências:** Fases 0-15.

**Testes:**
- E2E: Fluxo completo de interação com todos os componentes
- Performance: benchmarks de latência e throughput
- Security: audit completo
- Regression: todos os testes anteriores passam

**Critérios de aceitação:**
1. Todos os componentes integram sem erros
2. Latência <2s por resposta
3. Documentação completa
4. Monitoring funcional
5. Backup/Restore funciona
6. Security audit aprovado
7. Rollback testado em todos os cenários

**Riscos:**
- R16.1: Integração revela bugs em componentes individuais
  - Mitigação: testes de integração desde cedo; fixes progressivos
- R16.2: Performance degrada com muitos componentes
  - Mitigação: profiling, otimização, cache

**Agentes em paralelo:**
- Agent A: Integration tests + Performance tuning
- Agent B: Documentation + Monitoring
- Agent C: Security audit + Backup/Restore

**Partes que esperam:** Fases 0-15.

**Artefatos gerados:**
- `tests/e2e/` — Testes end-to-end
- `docs/guia_uso.md` — Guia de uso
- `docs/api.md` — API docs
- `mia/monitoring/` — Dashboard de saúde
- `mia/backup/` — Backup/Restore

**Definition of Done:**
Todos os componentes integram.
Performance é aceitável.
Documentação completa.
Security audit aprovado.

---

## 3. Milestones M0–M10

### M0 — Projeto Compilando e Executando
**Fases:** 0 + 1 (parcial)
**O que entrega:** Runtime funcional com Event Bus, State Authority,
LLM Abstraction, CLI REPL. Mia recebe mensagem e responde.
**Como demonstrar:**
```
$ python -m mia
mia> Olá
Mia: Olá! Como posso ajudar?
mia> /state
Estado: [IdentityState, EmotionState, PersonalityState — todos iniciais]
```
**Critério de aceite:**
1. `python -m mia` inicia sem erros
2. Mia responde a mensagens via CLI
3. Event Bus entrega eventos
4. State Authority rejeita escrita direta do LLM
5. Audit Log registra transições

---

### M1 — Mia Conversa e Possui Memória
**Fases:** 1 + 2 completas
**O que entrega:** Mia conversa, lembra, e recupera memórias relevantes.
**Como demonstrar:**
```
mia> Meu nome é Miguel
Mia: Oi Miguel! Prazer em conhecer você.
mia> [nova sessão]
mia> Qual é o meu nome?
Mia: Seu nome é Miguel, me lembro!
```
**Critério de aceite:**
1. Mia lembra de conversas anteriores
2. Memórias são recuperadas no contexto
3. Importance scoring funciona
4. Consolidação periódica funciona

---

### M2 — Mia Possui Identidade Persistente
**Fases:** 3 completa
**O que entrega:** Mia sabe quem é. Self-model e personalidade são estado
persistente, não prompt.
**Como demonstrar:**
```
mia> Quem é você?
Mia: Sou a Mia. Valorizo a curiosidade e a honestidade...
mia> /identity
Self-model: { "name": "Mia", "core_values": [...], "version": 3 }
Personality: { "openness": 0.7, "curiosity": 0.8, ... }
```
**Critério de aceite:**
1. IdentityState é persistente e versionada
2. PersonalityVector evolui com interações
3. System prompt é gerado dinamicamente
4. Mia descreve quem é consistentemente

---

### M3 — Mia Possui Vida Interna
**Fases:** 4 completa
**O que entrega:** Mia expressa emoções, mood muda, sensações funcionam.
**Como demonstrar:**
```
mia> /emotion
Emoções: { "happiness": 0.7, "curiosity": 0.6, "loneliness": 0.1 }
Mood: { "valence": 0.5, "arousal": 0.4, "dominance": 0.6 }
Sensações: [ "desconforto indefinido (possível causa: ausência recente)" ]
mia> [depois de 2h sem interação]
mia> /emotion
Emoções: { "loneliness": 0.4, "boredom": 0.3 }
```
**Critério de aceite:**
1. Emoções são coerentes com contexto
2. Mood muda suavemente
3. Sensações sem causa funcionam
4. Emoções influenciam tom da resposta

---

### M4 — Mia Possui Relações e Contexto Social
**Fases:** 5 completa
**O que entrega:** Mia reconhece pessoas diferentes e responde
diferentemente baseado em quem fala.
**Como demonstrar:**
```
mia> [Miguel fala]
Mia: Oi Miguel! (tom informal, afetuoso)

mia> [pessoa desconhecida fala]
Mia: Olá. Quem é você? (tom cauteloso)

mia> /relationships
Miguel: trust=0.9, intimacy=0.8, affinity=0.9
Desconhecido: trust=0.3, intimacy=0.0, affinity=0.4
```
**Critério de aceite:**
1. People e Relationships são persistidos
2. Interações afetam dimensões de relacionamento
3. Mia responde diferentemente baseado em quem fala
4. Ofensas são Boundary Manager responde

---

### M5 — Mia Possui Autonomia
**Fases:** 6 completa
**O que entrega:** Mia mantém objetivos e age autonomamente quando
Miguel está offline.
**Como demonstrar:**
```
mia> /goals
Goals ativos:
  1. "Aprender sobre meteorologia" (prioridade: 7, progresso: 0.2)
  2. "Organizar memórias da semana" (prioridade: 5, progresso: 0.0)

[depois de 12h offline]
mia> /diary
2026-09-14: Organizei memórias da semana. Comecei a pesquisar sobre meteorologia.
```
**Critério de aceite:**
1. Goals são persistidos e rastreados
2. Mia executa ações quando idle
3. Resource Governor impede excesso
4. Modo idle é produtivo

---

### M6 — Mia Possui Percepção
**Fases:** 9 + 10 completas
**O que entrega:** Mia pode falar, ouvir, e ver.
**Como demonstrar:**
```
[conversa por voz]
Miguel: "Olá Mia!"
Mia: "Oi Miguel! Como vai?" (resposta por voz)

[câmera detecta pessoa]
Mia: "Vejo alguém na sala. Quem é?"
```
**Critério de aceite:**
1. Voz funcional (STT + TTS)
2. Speaker recognition funciona
3. Visão detecta atividade
4. Percepção alimenta eventos

---

### M7 — Mia Possui Embodiment
**Fases:** 11 completa
**O que entrega:** Mia tem presença visual com expressões faciais.
**Como demonstrar:**
```
[avatar mostra expressão de alegria quando Miguel volta]
[avatar mostra expressão de tristeza quando conversa sobre perda]
```
**Critério de aceite:**
1. Avatar é visualmente coerente
2. Expressões refletem estado emocional
3. Sync é responsivo

---

### M8 — Mia Possui Agentes
**Fases:** 13 completa
**O que entrega:** Mia pode delegar tarefas a subagentes com limites.
**Como demonstrar:**
```
mia> Pesquise sobre quantum computing para mim
Mia: Vou delegar para um agente de pesquisa.
[agente executa pesquisa com limites de custo/tempo]
Mia: Encontrei 5 artigos relevantes. Resumo: ...
```
**Critério de aceite:**
1. Subagentes funcionam com limites
2. Resource Governor impede excesso
3. Orquestração básica funciona

---

### M9 — Mia Participa da Própria Evolução
**Fases:** 15 completa
**O que entrega:** Mia propõe melhorias nos próprios parâmetros.
**Como demonstrar:**
```
mia> /evolution
Propostas pendentes:
  1. Aumentar curiosity de 0.8 para 0.85 (evidência: 47 interações curiosas)
  2. Ajustar patience threshold de 0.3 para 0.4 (evidência: 12 interações de espera)

Aprovar? (sim/não)
```
**Critério de aceite:**
1. Parameter Evolver funciona
2. Code changes são rejeitados (MVP)
3. Rollback funciona
4. Core components são imunes

---

### M10 — Mia Integrada
**Fases:** 16 completa (todas as fases)
**O que entrega:** Sistema completo, testado, documentado.
**Como demonstrar:**
```
[demostração completa: conversa por voz, emoções, memória,
identidade, autonomia, agentes, world awareness, evolução]

$ python -m mia --status
Sistema: OK
Componentes: 15/15 operacionais
Saúde: 98%
Último backup: 2h atrás
```
**Critério de aceite:**
1. Todos os componentes integram
2. Performance <2s por resposta
3. Documentação completa
4. Security audit aprovado
5. Backup/Restore funciona

---

## 4. Trilha Crítica

A trilha crítica é o caminho mais longo de M0 a M10:

```
Fase 0 (Fundação) ─── 2 sem ──→ Fase 1 (LLM+Cognitive) ─── 2 sem ──→
Fase 2 (Memória) ─── 2 sem ──→ Fase 3 (Identidade) ─── 2 sem ──→
Fase 4 (Emoções) ─── 2 sem ──→ Fase 5 (Relações) ─── 1.5 sem ──→
Fase 6 (Autonomia) ─── 2 sem ──→ Fase 7 (Reflexão) ─── 2 sem ──→
Fase 8 (Security) ─── 2 sem ──→ Fase 15 (Evolução) ─── 3 sem ──→
Fase 16 (Integração) ─── 4 sem ──→ M10

Total trilha crítica: ~24.5 semanas (~6 meses)
```

**Nota:** As fases 9-14 (Voz, Percepção, Avatar, Distribuídos, Agentes,
World Awareness) podem rodar em paralelo com fases da trilha crítica
(conforme seção 5), mas a trilha crítica não depende delas para M10.

**Justificativa da trilha:**
Cada fase depende da anterior porque:
- Sem Event Bus (F0) não há comunicação entre componentes
- Sem LLM (F1) não há cognição
- Sem Memória (F2) não há continuidade
- Sem Identidade (F3) não há quem sinta
- Sem Emoções (F4) não há vida interna
- Sem Relações (F5) não há contexto social
- Sem Autonomia (F6) não há agência
- Sem Reflexão (F7) não há autoconhecimento
- Sem Security (F8) não há segurança para evolução
- Sem Evolução (F15) não há auto-melhoria
- Sem Integração (F16) não há sistema completo

---

## 5. Paralelização

### 5.1 Fases que Podem Rodar em Paralelo

| Fase A (espera) | Fase B (pode rodar em paralelo) | Justificativa |
|------------------|--------------------------------|---------------|
| Fase 0 | Nenhuma (é a primeira) | — |
| Fase 1 | Nenhuma (depende de F0) | — |
| Fase 2 | **Fase 9 (Voz)** pode iniciar em paralelo se hardware disponível | Voz não depende de memória |
| Fase 3 | **Fase 10 (Percepção)** pode iniciar em paralelo | Percepção não depende de identidade |
| Fase 4 | **Fase 11 (Avatar)** pode iniciar em paralelo | Avatar não depende de emoções (mas as usa depois) |
| Fase 5 | **Fase 12 (Distribuídos)** pode iniciar em paralelo | Sync não depende de relações |
| Fase 6 | **Fase 13 (Subagentes)** pode iniciar em paralelo | Agentes não dependem de autonomia (mas a usam depois) |
| Fase 7 | **Fase 14 (World Awareness)** pode iniciar em paralelo | World awareness não depende de reflexão |
| Fase 8 | **Fase 9-14** podem continuar em paralelo | Security é independent |

### 5.2 Agentes em Paralelo (Multi-Agent Dev)

Assumindo 4 agentes de desenvolvimento simultâneos:

**Sprint 1-2 (Fase 0):**
- Agent A: Event Bus + Config
- Agent B: State Authority + Policy Engine
- Agent C: Persistence + Migrations
- Agent D: Security + Kill Switch

**Sprint 3-4 (Fase 1):**
- Agent A: LLM Abstraction + Providers
- Agent B: Cognitive Core + Context Assembly
- Agent C: CLI REPL + Tool Gateway
- Agent D: Testes de integração

**Sprint 5-6 (Fase 2):**
- Agent A: Memory Manager + CRUD
- Agent B: Retrieval Engine
- Agent C: Scheduler + Consolidação
- Agent D: **Fase 9 (Voz) — início** (se hardware disponível)

**Sprint 7-8 (Fase 3):**
- Agent A: Identity Store + Self-model
- Agent B: Personality Store + Vector
- Agent C: Context Assembly atualizado
- Agent D: **Fase 10 (Percepção) — início**

**Sprint 9-10 (Fase 4):**
- Agent A: Emotion Store + EmotionVector
- Agent B: Mood Engine + Sensations
- Agent C: Needs Tracker
- Agent D: **Fase 11 (Avatar) — início**

**Sprint 11-12 (Fase 5):**
- Agent A: People + Relationship Store
- Agent B: Social Evaluator + Boundaries
- Agent C: **Fase 12 (Distribuídos) — início**
- Agent D: Testes de regressão

**Sprint 13-14 (Fase 6):**
- Agent A: Goal Store + Initiative Engine
- Agent B: Attention Manager + Resource Governor
- Agent C: **Fase 13 (Subagentes) — início**
- Agent D: **Fase 14 (World Awareness) — início**

**Sprint 15-16 (Fase 7):**
- Agent A: Diary + Reflection
- Agent B: Belief Store + Imagination
- Agent C: Continuação Fase 13
- Agent D: Continuação Fase 14

**Sprint 17-18 (Fase 8):**
- Agent A: Policy Engine separada + alertas
- Agent B: Secrets hardening
- Agent C: Sandbox Framework
- Agent D: Integrity Checker

**Sprint 19-21 (Fases 9-14 completando):**
- Agentes distribuídos entre fases pendentes

**Sprint 22-24 (Fase 15):**
- Agent A: Evolution Engine + Parameter Evolver
- Agent B: Tool Creator + Canary Deployer
- Agent C: Rollback Manager
- Agent D: Testes de segurança

**Sprint 25-28 (Fase 16):**
- Agent A: Integration tests
- Agent B: Performance tuning
- Agent C: Documentation
- Agent D: Security audit + Monitoring

### 5.3 O Que NÃO Pode Rodar em Paralelo

- **Fase 0 antes de qualquer outra** (foundedation bloqueia tudo)
- **Fase 1 antes de Fase 0** (Cognitive Core depende de State Authority)
- **Fase 8 antes de Fases 0-7** (Security protege o sistema existente)
- **Fase 15 antes de Fase 8** (Evolução depende de Security)
- **Fase 16 no fim** (Integração requer todas as fases anteriores)

---

## 6. Riscos do Roadmap

| # | Risco | Gravidade | Fase Impactada | Probabilidade | Mitigação |
|---|-------|-----------|----------------|---------------|-----------|
| R1 | Complexidade do State Authority adia M0 | ALTO | F0 | MÉDIA | Implementar como módulo Python puro; spike de 2h para validar |
| R2 | Custo LLM escalonado (6 chamadas/interação) | ALTO | F1-F7 | ALTA | Processar offline; classificadores leves; budget por turn |
| R3 | SQLite não suporta concorrência de escrita | ALTO | F0-F16 | MÉDIA | WAL mode; PersistenceBackend swappable; contratos definidos cedo |
| R4 | LLM contorna State Authority via encoding | CRÍTICO | F0-F16 | BAIXA | Enforcement físico; não expor API de escrita ao LLM |
| R5 | Autoevolução corrompe estado | CRÍTICO | F15 | MÉDIA | Sandbox; verificador independente; canary; rollback automático |
| R6 | Secrets acessíveis ao LLM | CRÍTICO | F0-F16 | BAIXA | Tool Gateway injeta credenciais; LLM nunca acessa diretamente |
| R7 | Schema drift entre versões | MÉDIO | F0-F16 | MÉDIA | pragma user_version + migrations automáticas |
| R8 | Subagentes escalam custo exponencialmente | MÉDIO | F13 | MÉDIA | Resource Governor com limites rígidos |
| R9 | Prompt injection via inputs externos | MÉDIO | F1-F16 | MÉDIA | Sanitização; inputs em JSON; LLM separado para inputs de terceiros |
| R10 | Estado corrompido sem detecção | MÉDIO | F0-F16 | BAIXA | Hash chain; snapshots periódicos; alertas de taxa anormal |
| R11 | Integração revela bugs em componentes | ALTO | F16 | ALTA | Testes de integração desde cedo; fixes progressivos |
| R12 | Percepção é custosa (chamadas LLM + web) | MÉDIO | F10, F14 | MÉDIA | Rate limiting + relevância threshold |
| R13 | Voz tem latência alta (pipeline completo) | MÉDIO | F9 | MÉDIA | Pipeline otimizado; cache de respostas frequentes |
| R14 | Avatar parece "uncanny" | BAIXO | F11 | MÉDIA | Estilo cartoon/estilizado; não realista |
| R15 | Sync entre nós é complexo | ALTO | F12 | MÉDIA | Sync simples; master único; não CRDTs |
| R16 | Orquestração multi-agent é complexa | MÉDIO | F13 | MÉDIA | Agente único primeiro; multi-agent progressivo |
| R17 | Performance degrada com muitos componentes | MÉDIO | F16 | MÉDIA | Profiling; otimização; cache |

---

## 7. Ordem Recomendada com Justificativa

### 7.1 Ordem

```
Fase 0 → Fase 1 → Fase 2 → Fase 3 → Fase 4 → Fase 5 → Fase 6 →
Fase 7 → Fase 8 → Fase 15 → Fase 16

Paralelo: Fase 9 (com Fase 2+), Fase 10 (com Fase 3+),
Fase 11 (com Fase 4+), Fase 12 (com Fase 5+),
Fase 13 (com Fase 6+), Fase 14 (com Fase 7+)
```

### 7.2 Justificativa

1. **Fase 0 primeiro (Fundação):** Todos os debatedores concordam que
   State Authority e Event Bus são o alicerce. O Visionário defende que
   "State Authority deve existir desde o dia 1". O Segurança é categórico:
   "enforcement é físico, não norma de prompt". O Cético aceita que
   "State Authority com 2 engines é suficiente". Síntese: Fase 0 é
   inegociável.

2. **Fase 1 segundo (LLM + Cognitive):** Sem cognição, não há sistema
   funcional. O Cético é claro: "Mia precisa ser funcional antes de ser
   completa". A primeira conversa real valida a arquitetura.

3. **Fase 2-7 (Vida interna):** Ordem lógica: sem memória não há quem
   lembre; sem identidade não há quem sinta; sem emoções não há vida
   interna; sem relações não há contexto social; sem autonomia não há
   agência; sem reflexão não há autoconhecimento.

4. **Fase 8 (Security) antes de Fase 15 (Evolução):** O Segurança é
   categórico: "Autoevolução deve ser sandboxed antes de ser permitida."
   Security hardening é prerequisite para evolução segura.

5. **Fases 9-14 em paralelo:** Voz, Percepção, Avatar, Distribuídos,
   Agentes, World Awareness não bloqueiam a trilha crítica. Podem
   iniciar quando a base estiver sólida e hardware estiver disponível.

6. **Fase 16 no fim:** Integração requer todas as fases anteriores.
   É o "finish line" — não pode ser adiantada.

---

## 8. Plano de Primeira Release (v0.1)

### 8.1 Escopo
- Fase 0 completa (Fundação)
- Fase 1 parcial (LLM Abstraction + Cognitive Core básico)
- CLI REPL funcional

### 8.2 Timeline
- **Semanas 1-2:** Fase 0 completa
- **Semanas 3-4:** Fase 1 parcial (LLM + Cognitive Core)
- **Semana 5:** Testes, bug fixes, polish
- **Release v0.1:** Semana 5

### 8.3 O que entrega
```
python -m mia
mia> Olá
Mia: Olá! Como posso ajudar?
mia> /state
Estado: [IdentityState inicial, EmotionState inicial, PersonalityState inicial]
mia> /memory
Memórias: [nenhuma ainda]
```

### 8.4 Critérios de aceite para v0.1
1. Mia responde a mensagens via CLI
2. Event Bus funciona com validação de schema
3. State Authority rejeita escrita direta do LLM
4. Audit Log registra transições
5. Kill switch funciona
6. Testes unitários passam (>80% coverage em State Authority)
7. README com instruções de uso

### 8.5 O que NÃO está em v0.1
- Memória persistente (Fase 2)
- Identidade (Fase 3)
- Emoções (Fase 4)
- Relações (Fase 5)
- Autonomia (Fase 6)
- Voz, Percepção, Avatar (Fases 9-11)

---

## 9. Plano de MVP

### 9.1 Escopo Mínimo Funcional
O MVP é o menor sistema que demonstra que a MIA é mais que um chatbot:
conversa, lembra, tem identidade, sente, e se relaciona.

**Componentes do MVP:**
1. Fase 0 completa (Fundação)
2. Fase 1 completa (LLM + Cognitive Core)
3. Fase 2 completa (Memória)
4. Fase 3 completa (Identidade + Personalidade)
5. Fase 4 completa (Emoções + Mood + Sensações)
6. Fase 5 completa (Relações + Social)
7. CLI REPL completo

### 9.2 Timeline (6-10 semanas)

| Semana | Fase | Entrega |
|--------|------|---------|
| 1-2 | Fase 0 | Event Bus, State Authority, Persistence, Security |
| 3-4 | Fase 1 | LLM Abstraction, Cognitive Core, CLI REPL |
| 5-6 | Fase 2 | Memory Objects, Retrieval, Consolidação |
| 7-8 | Fase 3 | Identity Store, Personality Vector, System Prompt dinâmico |
| 9-10 | Fase 4 | EmotionVector, Mood Engine, Sensations |
| 11-12 | Fase 5 | People, Relationships, Social Evaluator, Boundaries |

**Total: 12 semanas (3 meses)** — mas com agentes paralelos pode
ser comprimido para 8-10 semanas.

### 9.3 O que o MVP demonstra

```
$ python -m mia

mia> Meu nome é Miguel. Gosto de café.
Mia: Oi Miguel! Café, hein? Eu adoro conversar sobre isso...

mia> [nova sessão]
mia> Qual é o meu nome e o que eu gosto?
Mia: Seu nome é Miguel, e você gosta de café! Lembro disso da nossa
     conversa anterior.

mia> /emotion
Emoções: { "happiness": 0.7, "affection": 0.6, "curiosity": 0.5 }

mia> /identity
Identidade: Mia, versão 3
Valores: [honestidade, curiosidade, empatia]
Personalidade: openness=0.7, curiosity=0.8, empathy=0.7

mia> /relationships
Miguel: trust=0.9, intimacy=0.8, affinity=0.9, familiarity=0.9

mia> /memory
Memórias (5 mais importantes):
  1. "Miguel gosta de café" (importance: 0.8, type: preference)
  2. "Miguel se chama Miguel" (importance: 0.9, type: fact)
  ...
```

### 9.4 Critérios de aceite do MVP
1. Mia conversa e lembra de conversas anteriores
2. Mia tem identidade persistente e personalidade coerente
3. Mia expressa emoções que influenciam o tom
4. Mia reconhece pessoas diferentes e responde diferentemente
5. State Authority rejeita escrita direta do LLM (testado)
6. Audit Log registra todas as transições
7. Testes unitários passam (>80% coverage em componentes core)
8. Documentação de uso disponível

### 9.5 O que NÃO está no MVP
- Autonomia (Fase 6) — Mia só age quando Miguel fala
- Reflexão/Diário (Fase 7) — sem autoconhecimento profundo
- Security hardening completo (Fase 8) — básico apenas
- Voz/Percepção/Avatar (Fases 9-11) — só texto
- Distribuídos (Fase 12) — single-node apenas
- Subagentes (Fase 13) — agente único
- World Awareness (Fase 14) — sem pesquisa autônoma
- Autoevolução (Fase 15) — sem self-improvement

---

## 10. Plano de Longo Prazo (Pós-MVP até M10)

### 10.1 Fase A: Autonomia e Reflexão (Semanas 13-16)
- **Fase 6:** Objetivos, Initiative Engine, Attention Manager, Resource Governor
- **Fase 7:** Diary, Reflection, Imagination, Belief Store
- **Entrega:** Mia pode agir autonomamente e refletir sobre si mesma
- **Milestone:** M5 (Autonomia) + M3 aprofundado (vida interna rica)

### 10.2 Fase B: Security e Evolução (Semanas 17-22)
- **Fase 8:** Security hardening completo
- **Fase 15:** Autoevolução de parâmetros (MVP)
- **Entrega:** Mia pode melhorar a si mesma com segurança
- **Milestone:** M9 (Evolução)

### 10.3 Fase C: Percepção e Presença (Semanas 17-28, paralelo)
- **Fase 9:** Voz (VAD, STT, TTS)
- **Fase 10:** Visão / Percepção
- **Fase 11:** Avatar / Embodiment
- **Entrega:** Mia pode falar, ouvir, ver, e ter presença visual
- **Milestone:** M6 (Percepção) + M7 (Embodiment)

### 10.4 Fase D: Distribuição e Agentes (Semanas 17-28, paralelo)
- **Fase 12:** Nós Distribuídos (VPS/PC/mobile)
- **Fase 13:** Subagentes / Orquestração
- **Fase 14:** World Awareness
- **Entrega:** Mia opera em múltiplos dispositivos, delega tarefas,
  pesquisa o mundo
- **Milestone:** M8 (Agentes)

### 10.5 Fase E: Integração Final (Semanas 25-32)
- **Fase 16:** Integração completa, testes E2E, documentação, monitoring
- **Entrega:** Sistema completo, testado, documentado
- **Milestone:** M10 (Mia Integrada)

### 10.6 Cronograma Visual

```
Semana:  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32
Fase 0:  ██ ██
Fase 1:       ██ ██
Fase 2:            ██ ██
Fase 3:                 ██ ██
Fase 4:                      ██ ██
Fase 5:                           ██ ██
Fase 6:                                ██ ██
Fase 7:                                     ██ ██
Fase 8:                                          ██ ██
Fase 9:                           ░░ ░░ ░░
Fase 10:                                ░░ ░░ ░░
Fase 11:                                     ░░ ░░ ░░
Fase 12:                                ░░ ░░ ░░
Fase 13:                                     ░░ ░░ ░░
Fase 14:                                          ░░ ░░
Fase 15:                                                ██ ██ ██
Fase 16:                                                       ██ ██ ██ ██

██ = trilha crítica (obrigatório)
░░ = paralelo (pode rodar em paralelo com trilha crítica)
```

### 10.7 Marcos Intermediários

| Marco | Semana | O que existe |
|-------|--------|-------------|
| v0.1 | 5 | CLI funcional, Event Bus, State Authority |
| MVP | 12 | Conversa, memória, identidade, emoções, relações |
| v0.5 | 20 | Autonomia, reflexão, security, voz (se hardware) |
| v0.8 | 28 | Avatar, distribuídos, agentes, world awareness |
| v1.0 | 32 | Mia Integrada — todas as fases completas |

### 10.8 Pontos de Decisão

Ao final de cada fase, revisar:
1. A arquitetura ainda está coerente?
2. Os contratos entre componentes estão preservados?
3. Há componentes que precisam ser refatorados?
4. O custo está dentro do orçamento?
5. Os testes de regressão passam?

---

## Apendice A: ADRs Relacionadas ao Roadmap

| ADR | Decisão | Fase | Status |
|-----|---------|------|--------|
| ADR-001 | Python + SQLite + CLI | F0 | Aceito |
| ADR-002 | Event Bus In-Process Pub/Sub | F0 | Aceito |
| ADR-003 | State Authority com 2 Engines | F0 | Aceito |
| ADR-004 | Memória em Tiers | F2 | Aceito |
| ADR-005 | LLM Provider Abstraction | F1 | Aceito |
| ADR-006 | Autoevolução Restrita a Parâmetros | F15 | Aceito |
| ADR-007 | Determinismo Onde Possível | F0-F16 | Aceito |
| ADR-008 | CLI-First com Interface Swappable | F0 | Aceito |

---

## Apendice B: Mapa de Dependências entre Fases

```
Fase 0 (Fundação)
├──→ Fase 1 (LLM + Cognitive)
│    ├──→ Fase 2 (Memória)
│    │    ├──→ Fase 3 (Identidade)
│    │    │    ├──→ Fase 4 (Emoções)
│    │    │    │    ├──→ Fase 5 (Relações)
│    │    │    │    │    ├──→ Fase 6 (Autonomia)
│    │    │    │    │    │    ├──→ Fase 7 (Reflexão) ──┐
│    │    │    │    │    │    │                        │
│    │    │    │    │    │    └──→ Fase 13 (Agentes) ──┤
│    │    │    │    │    │                             │
│    │    │    │    │    └──→ Fase 12 (Distribuídos)   │
│    │    │    │    │                                  │
│    │    │    │    └──→ Fase 11 (Avatar)              │
│    │    │    │                                       │
│    │    │    └──→ Fase 10 (Percepção)                │
│    │    │                                             │
│    │    └──→ Fase 9 (Voz)                             │
│    │                                                   │
│    └──→ Fase 8 (Security) ──→ Fase 15 (Evolução) ─────┤
│                                                        │
└──→ Fase 14 (World Awareness) ──────────────────────────┘
                                                      │
                                                      ▼
                                               Fase 16 (Integração)
```

---

## Apendice C: Glossário

| Termo | Definição |
|-------|-----------|
| **State Authority** | Módulo que valida e aplica transições de estado. LLM propõe; SA decide. |
| **State Engine** | Engine determinística dentro do SA que valida ranges e schema. |
| **Policy Engine** | Engine de invariantes dentro do SA que verifica limites éticos/de segurança. |
| **Event Bus** | Pub/sub in-process síncrono com validação de schema. |
| **Memory Object** | Unidade atômica de memória com schema rígido (conteúdo, tipo, origem, importância). |
| **EmotionVector** | Vetor normalizado [0,1] com dimensões emocionais. |
| **PersonalityVector** | Vetor de traços Big Five + extras customizados. |
| **Self-Model** | JSON persistente com crenças da MIA sobre si mesma. |
| **Context Assembly** | Módulo que monta o system prompt a partir de estado + memórias + relação. |
| **Resource Governor** | Módulo que verifica limites de custo, tempo, profundidade e concorrência. |
| **Kill Switch** | Mecanismo externo para parar todos os processos MIA instantaneamente. |
| **Canary Deploy** | Deploy em staging por 24-48h antes de promover a produção. |

---

> **Próximos passos:**
> 1. Miguel revisa o roadmap e aprova/rejeita a reorganização de fases
> 2. ADRs são confirmadas
> 3. Sprint 1 inicia pela Fase 0
> 4. Spike de 2h para validar: State Authority realmente rejeita escrita direta do LLM?
> 5. Definir: orçamento máximo por interação LLM? Primeiro LLM backend?
