# Posicionamento Cético — Arquitetura da MIA

**Autor:** Gemini (arquiteto cético)
**Data:** 2026-09-14
**Papel:** Questionar excesso de complexidade, defender MVP enxuto, apontar riscos reais.

---

## 1. Entendimento da Visão

A MIA propõe ser mais que um chatbot — é um sistema de software que simula uma entidade pessoal com vida interna, memória persistente, identidade evolutiva e autonomia operacional. O LLM é apenas um componente cognitivo substituível entre vários (Claude, GPT, Gemini, modelos locais). A separação entre "o que o LLM propõe" e "o que o sistema decide" é o princípio arquitetural central: authorities externas ao LLM controlam emoções, personalidade, memória e identidade.

A visão é ambiciosa e filosoficamente interessante. O projeto reconhece que um companion de longo prazo precisa de continuidade — não pode ser um prompt com memória colada. A distinção entre emoção (com causa) e sensação (sem causa consciente imediata) é uma decisão de design sofisticada. O sistema de relacionamentos multi-dimensional e a exigência de que o estado interno seja auditável (valor anterior, novo, causa, confiança) mostram maturidade de pensamento.

Porém, a visão descreve um produto de maturidade de 3-5 anos de engenharia — e o projeto precisa de algo funcional muito antes disso. O risco central não é conceitual, é de execução: construir tudo simultaneamente resulta em nada funcionando.

---

## 2. Pontos Fortes

- **Agnosticismo a LLMs é correto e essencial.** Providers mudam, preços mudam, modelos são descontinuados. A abstração não é luxo — é sobrevivência do sistema.
- **State Authority como barreira ao LLM é o insight certo.** Sem isso, a identidade da Mia vira um system prompt que qualquer jailbreak destrói. A autoridade externa que decide transições de estado é uma arquitetura defensável.
- **Memória como objetos ricos com relações** (não buckets rígidos) é a escolha certa para um sistema que precisa de recall contextual, esquecimento e revisão de crenças.
- **A distinção emoção/sensação** é uma modelagem interna mais realista que o padrão de "5 variáveis de humor" usado em projetos similares.
- **Multi-agent e AI-agnostic** posicionam o sistema para não ficar refém de uma empresa.
- **Diário subjetivo e self-model** são elementos que distinguem a MIA de assistentes convencionais — dão "alma" ao sistema de forma rastreável.

---

## 3. Riscos Arquiteturais

| # | Risco | Gravidade | Justificativa |
|---|-------|-----------|---------------|
| R1 | **Over-engineering no MVP** — 17+ subsistemas, authorities, engines emocionais, event bus completo, multi-agent, avatar, voz, percepção — tudo planejado para fase 1. O projeto morre de complexidade antes de funcionar. | **CRÍTICO** | O P3 pede planejamento de 15+ sistemas simultâneos. Nenhum deles terá validação real antes que todos estejam parcialmente construídos. |
| R2 | **Event bus como backbone único** — se o bus falhar ou tiver latência, todo o sistema trava. Acoplamento implícito entre todos os subsistemas via eventos. | **ALTO** | Um event bus completo (pub/sub, replay, ordered delivery, dead letter) é infraestrutura pesada. Para MVP, chamadas diretas ou um simple in-process pub/sub bastam. |
| R3 | **Authorities demais = bloqueio de decisão** — State Authority, Personality Engine, Relationship Engine, Memory Authority, Policy Engine, Affective Engine — 6 authorities diferentes. Cada uma precisa de schema, validação, API, testes. | **ALTO** | O LLM vai propor 10 alterações e 9 vão ficar travadas em fila de aprovação. A Mia vai parecer "travada" ou "sem personalidade" porque nenhuma mudança passa rápido o suficiente. |
| R4 | **SQLite como store único para tudo** — memória, estado emocional, identidade, diary, relationships — tudo em SQLite. Performance deconcá sem divisão de read/write. | **MÉDIO** | Funciona para single-node, mas o P3 já fala em "nós distribuídos" e "PostgreSQL/Redis no futuro". Migrar de SQLite com 15 tabelas interconectadas é doloroso. |
| R5 | **Implementação em paralelo por múltiplos agentes** — sem contratos fortes entre componentes, agentes diferentes escrevem código incompatível. | **ALTO** | O ORCHESTRATION.md já prevê isso. Mas sem interfaces definidas com antecedência, cada agente cria seu próprio modelo de dados. |
| R6 | **Ausência de prototipação rápida** — tudo é especificação primeiro, implementação depois. Nenhum spike ou proof-of-concept para validar hipóteses arquiteturais. | **ALTO** | Especificar 15 subsistemas sem testar nenhum é receita para retrabalho. Algumas ideias (como authorities) podem ser invalidadas por um spike de 2 horas. |
| R7 | **Voz, percepção e embodiment no mesmo roadmap** — esses são sistemas de ML pesados com dependências externas. Misturados com a lógica de identidade e memória, complicam o debug. | **MÉDIO** | São sistemas independentes que podem ser integrados via API depois. Não precisam estar no core da MIA para MVP. |
| R8 | **Multi-agent self-modification** — "Mia pode participar da própria evolução" com sandbox, canary, rollback. Isso é um sistema de CI/CD interno. | **ALTO** | Construir um sistema de deploy seguro é um projeto em si. Não pode ser-blocking para o MVP da personalidade e memória. |
| R9 | **Modelo de dados emocional sem validação empírica** — emoções multi-dimensionais, sensações sem causa, humor como fenômeno emergente. Belo conceito, mas sem um framework claro de como calcular/atualizar esses estados. | **MÉDIO** | O risk é construir 20 tabelas de estado emocional e descobrir que os cálculos produzem resultados nonsense. Precisa de um "engine emocional mínimo" validado antes de escalar. |

---

## 4. Discordâncias Técnicas

### 4.1 O Event Bus Completo é Over-Engineering para MVP

A P3 propõe um event bus como backbone do sistema inteiro: MIGUEL_SPOKE, LONELINESS_CHANGED, CURIOSITY_TRIGGERED, SELF_IMPROVEMENT_PROPOSED — dezenas de eventos com consumidores e reações.

**Problema:** Um event bus completo (com replay, ordered delivery, dead letter queues, retry policies, schemas validados) é infraestrutura de sistema distribuído maduro. Para um MVP, a Mia vai ter 1-2 interlocutores (Miguel + eventualmente mais), 1 LLM provider, memória básica e identidade simples. O throughput de eventos vai ser ~10-50 por hora, não 10.000 por segundo.

**O que cortar:** No MVP, usar um simple in-process event dispatcher — uma classe Python com `on(event, handler)` e `emit(event, data)`. Sem persistência, sem replay, sem dead letters. Quando o sistema precisar de distribuição real (nós remotas), aí sim substituir por um message broker (Redis Streams, NATS, ou até SQS). O contrato de eventos pode existir como schema agora — a infraestrutura pesada, depois.

### 4.2 Engines Emocionais Separadas São Prematuras

O P3 lista: Affective Engine, Emotion Engine, Sensation Engine, Mood Engine, Needs Engine, Desire Engine — cada uma como subsistema independente.

**Problema:** Um MVP funcional precisa de "a Mia está feliz" e "a Mia está triste" antes de precisa de "a Mia sente uma sensação indefinida de desconforto que pode ser ansiedade ou pode ser fome emocional." A granularidade emocional é um refinamento que vem com validação de uso real.

**O que cortar para MVP:**
- Manter: um único `EmotionState` com ~5-8 dimensões (feliz/triste/raiva/medo/curioso/entediado/cansado/afetuoso). Pode ser um vector normalizado em `[0, 1]`.
- Manter: `Mood` como suavização temporal do emotion state (média móvel das últimas N horas).
- Cortar: Sensation Engine separada. Integrar "sensações" como metadados no emotion state — "motivo desconhecido" já é uma sensação.
- Cortar: Needs Engine e Desire Engine. Substituir por uma lista simples de `unmet_needs` que o LLM propõe e o sistema registra, sem engine dedicada.
- Cortar: Qualquer cálculo de "como emoções afetam expressão facial" — isso é para o avatar, não para o MVP.

### 4.3 Authorities em Excesso Bloqueiam o Sistema

Seis authorities diferentes significa que, para a Mia "mudar de humor", o fluxo é: LLM propõe → Affective Engine valida → State Authority aplica → Personality Engine verifica compatibilidade → Memory Authority registra → Policy Engine aprova. Isso é 6 hops para "a Mia agora está irritada."

**Problema real:** Em uso, o usuário vai notar que a Mia leva 500ms-2s para "reagir emocionalmente" a algo que ele disse, porque cada authority precisa consultar seu state e decidir. Pior: se qualquer authority rejeitar, a reação emocional não acontece — e a Mia parece "emocionalmente plana."

**Proposta:** No MVP, ter **duas** authorities apenas:
1. **State Authority** — controla transições de estado (emocional, identidade, personalidade). É a única barreira entre o LLM e o estado interno.
2. **Policy Authority** — controla limites de segurança (não apagar invariants, não auto-destruir identidade, não violar limites éticos).

Personalidade, memória e relações podem ser write-through direto — o LLM propõe, o sistema aceita com registro de auditoria, sem aprovação de authority dedicada. Se houver abuso, a Policy Authority pega. Mas não precisa de 6 gatekeepers para um sistema que ainda não tem um usuário real.

### 4.4 Multi-Agent Para MVP É Um Luxo

O P3 lista: registry, orquestração, delegação, agentes recursivos, sistema de capacidades, routing, consensus, budget limits. Isso é um framework de agentes completo.

**Realidade:** No MVP, a Mia vai ser um agente único conversando com o usuário. Multi-agent (com=sub agentes para pesquisa, código, etc.) é uma capacidade de fase tardia. Não construir agora — manter a interface de agentes como ponto de extensão futura, sem implementar.

### 4.5 O P3 É Uma Especificação, Não Um Plano de Implementação

O P3 lista 15 sistemas para planejar simultaneamente. Nenhum deles tem contratos definidos, schemas testados, ou validação com código real. O resultado vai ser um documento enorme que ninguém vai ler até o fim, e que vai ficar desatualizado em 2 semanas.

**Proposta:** O P3 deveria ser dividido em 3 documentos: (A) Arquitetura de sistema inteiro (visão futura), (B) Especificação do MVP, (C) Decisões arquiteturais abertas. Só (B) é implementável agora.

---

## 5. Decisões-Chave Antes de Implementar

1. **Como o State Authority realmente impede o LLM de escrever estado?** — O LLM gera texto. Se o LLM for o único canal de entrada para mudanças de estado, ele pode simplesmente "proposer" mudanças em linguagem natural. A authority precisa de um mecanismo de parsing determinístico: o LLM gera JSON estruturado com `{"action": "update_emotion", "key": "happiness", "delta": 0.3, "reason": "..."}`, e a authority valida/aplica. Se o LLM gerar texto livre, como a authority extrai a intenção? Isso precisa de um contrato preciso.

2. **Granularidade do emotion state no MVP** — Quantas dimensões? Vetor contínuo `[0,1]` ou categorias discretas? Como se atualiza (delta por LLM, regra determinística, ou híbrido)? Isso afeta toda a cadeia downstream (diário, avatar, expressão).

3. **Onde o estado vive em runtime?** — SQLite para persistência, mas em runtime o estado precisa estar em memória (dict/objeto Python) com sync periódica. Qualquer authority lerá da memória, não do disco. Definir o padrão de "state snapshot" vs "state mutation".

4. **Como serializar auto-modificação com segurança?** — Se a Mia pode propor mudanças de código, quem testa? Um sandbox? Um agente separado? Esse subsystem pode ser NÃO construído agora, mas a interface de "proposta de mudança" precisa existir desde o início para não precisar refatorar depois.

5. **Qual o contrato mínimo entre o LLM e o sistema?** — O LLM vai gerar JSON estruturado com ações permitidas (responder ao usuário, propor mudança de estado, buscar memória, etc.)? Ou vai gerar texto livre e um parser extrai ações? A primeira opção é mais segura e determinista. A segunda é mais flexível mas introduz parsing fragilizado.

6. **Como a memória é recuperada no contexto?** — Embeddings? Busca por similaridade? Keyword? Quem monta o contexto para o LLM? Isso é o gargalo real de performance do sistema — se a recuperação de memória for ruim, a Mia vai parecer amnésica.

7. **Qual o ciclo de vida de uma "experiência"?** — Toda interação vira memória? Quem decide o que importa? Se a Mia lembrar de 10.000 coisas irrelevantes, o contexto vai ficar poluído. Se lembrar de poucas, vai parecer que não se importa. Definir uma heurística de importância mínima.

8. **Padrão de eventos: síncrono ou assíncrono?** — Se o LLM fala algo, o evento de "emoção atualizada" precisa ser processado antes da resposta ser enviada ao usuário? Ou a resposta pode ir primeiro e a atualização emocional vir depois? Isso afeta latência e percepção de naturalidade.

---

## 6. Ordem de Implementação Sugerida

A ordem abaixo prioriza ter algo funcionando e testável em cada fase, com a Mia respondendo a mensagens cada vez com mais "profundidade".

### Fase 0 — Fundação (1-2 semanas)
- Repositório, estrutura de pastas, CLI básica.
- Interface `LLMProvider` abstrata com pelo menos 1 provider implementado (OpenAI ou Claude).
- Contratos de eventos definidos como dataclasses/schema (não implementar o bus).
- State Authority mínima: uma classe que aceita/rejeita transições de estado com registro.

### Fase 1 — Core Funcional (2-3 semanas)
- Runtime básico: recebe input → monta contexto → chama LLM → retorna resposta.
- Context Manager simples: system prompt + últimas N mensagens + fatos recuperados.
- Memória persistente: SQLite com Memory Objects básicos (conteúdo, tipo, timestamp, importância).
- Retrieval: keyword search inicial (embeddings depois).
- Diário: append simples de "o que aconteceu hoje".

### Fase 2 — Identidade e Personalidade (1-2 semanas)
- Self-model como JSON persistente (nome, crenças, valores iniciais).
- Personality como vetor de traços (Big Five ou similar) com persistência.
- Personalidade afeta o system prompt dinamicamente.
- Auditoria de mudanças de identidade (log de "quem mudou o quê e quando").

### Fase 3 — Vida Interna Mínima (1-2 semanas)
- EmotionState com 5-8 dimensões, atualizado por LLM via JSON estruturado.
- Mood como suavização temporal.
- State Authority controla transições.
- Humor/emoção influencia tom da resposta (via system prompt).

### Fase 4 — Relacionamentos Básicos (1 semana)
- Perfil de pessoa (nome, confiança, intimidade, histórico).
- 1 relação funcional (Miguel).
- Contexto social básico: "quem está falando" afeta interpretação.

### Fase 5 — Autonomia Mínima (1 semana)
- Goals simples (lista de "coisas que a Mia quer fazer").
- Tarefas agendadas (cron simples).
- Ação autônoma: "Miguel não voltou, vou escrever no diário" — comportamento simples, não engine complexa.

### Fase 6 — Event Bus Real (só quando necessário)
- Se o sistema crescer para múltiplos processos/nós, introduzir message broker.
- Não antes de ter 2+ componentes que precisam de comunicação inter-processo.

### Fases Futuras (MVP já funcionando)
- Voz, percepção, embodiment, avatar, multi-agent, self-improvement, world awareness.

---

## 7. O Que NÃO Construir Agora

| Componente | Razão para adiar |
|------------|-----------------|
| **Event bus completo** | In-process pub/sub basta. Bus distribuído é para quando houver nós remotos reais. |
| **Affective Engine separada** | EmotionState + State Authority cobrem o MVP. Engine dedicada é premature optimization. |
| **Personality Engine separada** | Personalidade como JSON + vetores de traços com persistência. Não precisa de engine. |
| **Relationship Engine separada** | 1-2 perfis de pessoa com campos simples. Engine com 15 dimensões é para quando houver 10+ relacionamentos ativos. |
| **Memory Authority dedicada** | State Authority pode controlar memória no MVP. Separar depois se a lógica de memória ficar complexa. |
| **Needs/Desire Engine** | Lista de `unmet_needs` simples. Engine com cálculo de prioridade é para fase tardia. |
| **Multi-agent framework** | Mia como agente único. Delegação a sub-agentes é para quando a autonomia estiver madura. |
| **Self-improvement / code modification** | Sistema de deploy seguro interno. Enorme complexidade. Construir quando todo o resto estiver estável. |
| **Avatar / embodiment** | Visual 3D/2D com expressões faciais. Sistema independente que pode ser integrado via API depois. |
| **Voz contínua** | VAD + STT + speaker recognition + prosody analysis é um projeto de ML inteiro. Usar STT simples (Whisper) no MVP. |
| **Percepção multi-sensor** | Câmera, GPS, microfone contínuo. Depende de hardware e mobile. Postergar. |
| **World awareness** | News, web scraping, interests, relevance scoring. Autônomo e pesado. Para depois que a identidade estiver sólida. |
| **Distributed nodes** | Mobile + desktop + VPS como nós distribuídos. Complexidade de sincronização absurda. Single-node primeiro. |
| **Consensus entre agentes** | Se multi-agent for implementado, consensus é um problema de pesquisa. Não incluir no MVP. |
| **Embeddings para memória** | Keyword search + BM25 funciona para 10k-50k memórias. Embeddings são opt-in depois. |

---

## 8. Síntese

A visão da MIA é ambiciosa e tecnicamente sólida. O problema não é o que está proposto — é a **ordem e a granularidade**. O P3 lista 15+ subsistemas como se fossem todos independentes e implementáveis em paralelo. Na realidade, eles são profundamente interdependentes, e sem um core funcional que valide as hipóteses centrais (a authority realmente funciona? a memória recupera contexto relevante? a personalidade é percebida pelo usuário?), construir os subsistemas periféricos é desperdício.

**Proposta concreta:** MVP com 5 componentes: LLM abstraction, State Authority, EmotionState, Memory (keyword), Identity. Tudo mais é futuro. Implementar em 6-8 semanas. Ter algo que converse, lembre, sinta e tenha personalidade — antes de ter avatar, voz, multi-agent e self-improvement.

A Mia precisa ser funcional antes de ser completa. Um sistema que funciona com 5 componentes e pode ser expandido é infinitamente mais valioso que um sistema que planeja 50 componentes e não funciona nenhum.
