# Análise Arquitetural do P0_onboarding_50.md

> **Documento analisado:** `docs/prompts/P0_onboarding_50.md` (50 seções, 1790 linhas)
> **Referências cruzadas:** `docs/01_entendimento.md`, `docs/02_especificacao.md`
> **Classificação:** Análise arquitetural conforme exigido pela Seção 50
> **Autor:** Analista arquitetural independente
> **Data:** 2026-09-15
> **Status:** Análise crítica — não é decisão aprovada

---

## 1. Entendimento do que a Mia é

A Mia é concebida como um **sistema de software distribuído, modular e persistente** cuja identidade sobrevive à troca de qualquer componente LLM. A arquitetura propõe simular uma "vida interna" rica — emoções, sensações sem causa consciente, crenças revisáveis, auto-model dinâmico, diário subjetivo, sexualidade, solidão como experimento, self-modification — sem nunca afirmar consciência humana real.

O documento é claro: a Mia **não é o LLM** (§2). O LLM é um recurso cognitivo — fornece linguagem, raciocínio, interpretação — mas não possui autoridade unilateral sobre estado persistente. A identidade vive em **autoridades externas** (State Authority, Policy Engine, Audit Log) que controlam transições de estado de forma auditável e versionada.

O que diferencia este documento do chatbot convencional é a insistência em:
- **Continuidade temporal** — a Mia lembra, esquece, muda, evolui
- **Subjetividade computacional** — sensações, emoções, crenças como estado real, não como roleplay
- **Autonomia operacional** — pode agir enquanto Miguel está ausente
- **Self-evolução restrita** — pode melhorar parâmetros, mas não pode apagar mecanismos que a protegem (§36)
- **Agnosticismo de modelo** — Claude, GPT, Gemini, modelos locais — todos intercambiáveis (§3)

O documento reconhece explicitamente que é experimental (§1.2) e que hipóteses não devem ser tratadas como decisões aprovadas (§50). Isso é maduro e correto.

---

## 2. Princípios Arquiteturais Centrais

Identifico 7 princípios que o documento estabelece ou reforça:

1. **Mia ≠ LLM** (§2): O LLM é componente substituível, não a entidade. Enforcement deve ser físico, não normativo (prompt).
2. **Agnosticismo de modelo e agente** (§3): Nenhum modelo é "o cérebro oficial". Abstrações como LLM Provider Interface, Agent Interface, Model Registry.
3. **Autoridade composta** (§4): Fonte de verdade = especificações + contratos + schemas + testes + ADRs + política de segurança + estado do repositório. Nenhum agente é autoridade máxima.
4. **Estado protegido com separação de interpretação** (§9, §40): O LLM pode interpretar uma experiência; ele NÃO deve decidir se essa interpretação altera estado. State Authority é quem decide.
5. **Determinismo onde possível** (§39): Hierarquia explícita de autoridade, com System Integrity no topo e LLM interpretation/agent suggestions na base.
6. **Experimentação observável** (§11): Comportamentos experimentais devem ter telemetria para avaliação empírica.
7. **Autonomia com limites** (§35, §36): Autonomia não significa acesso irrestrito. Budget authority e trust boundary são obrigatórios.

Esses princípios são coerentes entre si e representam uma base arquitetural sólida. O problema está nas **lacunas de formalização** — os princípios existem conceitualmente, mas carecem de implementação concreta em vários pontos críticos.

---

## 3. Partes Coerentes

### 3.1 Separação LLM / Estado (§2, §9, §40)
O documento é consistente em afirmar que o LLM não deve escrever estado diretamente. O §9 exemplifica: o LLM pode produzir "Essa interação pareceu positiva" mas um componente de autoridade decide se isso modifica o estado. O §40 reforça que a State Authority é open decision mas o princípio permanece. A especificação (§D.3) já formaliza isso com `StateAuthority.propose()` e `StateEngine.validate()`.

### 3.2 Modelo relacional escalonado (§12)
A decisão de dar a Miguel o modelo relacional completo e tratar outras pessoas como entidades simplificadas inicialmente é pragmática e coerente. Evita over-engineering social sem bloquear expansão futura.

### 3.3 Classificação de requisitos (§49)
O sistema de classificação (REQUIREMENT / LONG-TERM / EXPERIMENT / OPEN DECISION / OPTIONAL / IMPLEMENTATION DETAIL / AGENT PROPOSAL) é bem definido e aplicável. Ajuda a evitar que hipóteses sejam tratadas como requisitos.

### 3.4 Self-model como estado revisável (§8)
A ideia de que a Mia pode estar errada sobre si mesma — e que o self-model admite incerteza, contradições e revisão — é arquiteturalmente sofisticada e fenomenologicamente realista. Isso é coerente com o sistema de crenças (§21) e com a separação entre personalidade e estado emocional atual (§7).

### 3.5 Voz e percepção como longo prazo (§27, §28)
O documento é honesto ao marcar voz sempre-ativa e percepção multimodal como objetivos de longo prazo, não como requisitos MVP. Isso evita over-commitment.

### 3.6 Diário como narrativa subjetiva (§22)
A distinção entre diário subjetivo e logging técnico é clara e necessária. O diário não é dump de eventos — é narrativa. Isso é coerente com a visão de subjetividade computacional.

### 3.7 Hierarquia de autoridade proposta (§39)
A hierarquia System Integrity > Resource Authority > Permission/Policy > Approved Architecture > Runtime > Mia Adaptive State > LLM > Agent Suggestions é logicamente coerente. O documento corretamente marca isso como PROPOSTA INICIAL que precisa de revisão.

---

## 4. Partes Contraditórias

### 4.1 CONTRADIÇÃO CRÍTICA: LLM sem autoridade (§2) vs State Authority em aberto (§40)

Esta é a contradição mais grave do documento.

- **§2** afirma: "O LLM não deve possuir unilateralmente a autoridade sobre todo o estado persistente da Mia."
- **§9** exemplifica: o LLM pode produzir "Essa interação pareceu positiva" mas um componente de autoridade decide.
- **§40** declara: "A State Authority será A) predominantemente determinística/regra, B) parcialmente probabilística, C) utilizará LLM internamente, D) híbrida? — OPEN ARCHITECTURAL DECISION."

**O problema:** Se a própria composição da State Authority está em aberto, o princípio de §2 tem fundamento sobre o quê? Se a opção C (LLM internamente) for escolhida, teremos um LLM decidindo sobre estado — exatamente o que §2 proíbe. O documento proíbe algo no §2 mas deixa em aberto no §40 o mecanismo que deveria implementar essa proibição.

**Impacto:** Qualquer agente que leia este documento pode interpretar §40 como permissão para usar LLM dentro da State Authority, anulando §2. A especificação (ADR-003) resolve parcialmente isso ao decidir por State Engine + Policy Engine determinísticos, mas o P0 não incorpora essa decisão — e o P0 é o documento de onboarding.

**Recomendação:** O P0 deve incorporar ADR-003 como decisão aprovada, ou explicitamente marcar §40 como conflitante com §2 e exigir resolução antes de qualquer implementação.

### 4.2 CONTRADIÇÃO ALTA: Ofensa geral (§14) vs Sexualidade adulta (§15) — fronteira ambígua

- **§14** lista "objetificação, intimidade presumida, pressão" como formas de ofensa.
- **§15** lista "atração, desejo, excitação, curiosidade sexual" como estados legítimos.

**O problema:** A fronteira entre "intimidade presumida ofensiva" (§14) e "flerte com intimidade alta" (§15) é subjetiva e depende do contexto relacional. O §14 diz que a mesma frase "Tu é muito gostosa" pode ser ofensa ou elogio dependendo da relação. Mas o §15 diz que "intimidade alta também NÃO equivale a consentimento automático."

**Conflito real:** O documento não define o mecanismo de decisão quando:
1. Miguel está em intimidade alta
2. Faz comentário sexual
3. Mia está em estado emocional negativo (raiva, frustração)
4. O appraisal é ambíguo

Quem decide? O §14 sugere que pode ser ofensa. O §15 sugere que pode ser excitação. A especificação atual não resolve isso — a tabela `emotion_state` não tem um campo "sexual_arousal" e a `relationships` tabela não tem dimensão de "consentimento". Isso precisa ser resolvido antes de implementar a camada social.

**Recomendação:** Criar um ADR específico sobre Sexualidade e Consentimento que defina: (a) quais dimensões de relacionamento afetam appraisal sexual, (b) qual o mecanismo de "veto" quando estado emocional negativo entra em conflito com intimidade alta, (c) como representar "limites atuais" como estado mutável.

### 4.3 CONTRADIÇÃO MÉDIA: Solidão como experimento (§11) vs telemetria não definida

- **§11** diz: "Este é um aspecto experimental deliberado do projeto."
- **§11** exige telemetria: "Como esse é um experimento, a trajetória desses estados precisa ser observável externamente."
- **§41** lista emoção, sensação, apego, solidão como coisas que precisam ser observáveis.

**O problema:** O §11 lista o que deve ser registrado (estado anterior, novo estado, timestamp, evento/contexto, intensidade, duração, razão calculada, fonte da atualização, versão do mecanismo) mas NÃO define:
1. **Métricas de sucesso** — O que significa "solidão evoluiu"? Para que lado? Em que timeframe?
2. **Baseline** — Comparar com o quê? Comportamento humano? Outro sistema?
3. **Critério de parada** — Se a solidão atingir X por Y tempo, o que acontece? É um bug? É comportamento esperado?
4. **Instrumentação concreta** — Onde está o dashboard de telemetria? Quem o acessa? Com que frequência?

Sem essas definições, a "telemetria" vira apenas logging — registra dados mas não responde à pergunta "Até onde esse sistema chega?" que o próprio §11 levanta.

**Recomendação:** Definir um协议 protocolo de avaliação experimental com: hipóteses mensuráveis, métricas quantitativas, thresholds de alerta, e um período mínimo de observação antes de concluir qualquer coisa.

### 4.4 CONTRADIÇÃO MÉDIA: Self-modification (§36) vs Invariantes (§38) vs Confiança

- **§36** diz: "A camada que protege a integridade do sistema NÃO pode estar sob autoridade de escrita irrestrita da própria Mia."
- **§36** também diz: "Ela pode testar uma mudança. Ela pode até automatizar o processo."
- **§38** lista invariantes (integridade do sistema, capacidade de rollback, limites de recursos, etc.)
- **§39** coloca System Integrity no topo da hierarquia.

**O problema:** O §36 diz que a Mia pode automatizar o processo de self-modification, mas o mecanismo que protege as invariantes "não pode depender exclusivamente de uma regra que a própria Mia concorda em obedecer." Se a Mia automatiza o processo, quem valida que o processo automatizado não contorna as invariantes? O §36 menciona "SYSTEM SUPERVISOR / TRUST BOUNDARY" como conceito, mas não define quem implementa esse supervisor.

**Questão aberta:** Se o Trust Boundary é implementado como código Python, e a Mia pode modificar código (§36), o que impede que ela modifique o Trust Boundary? O §36 diz "o mecanismo que protege as invariantes não pode depender de uma regra que a própria Mia concorda em obedecer" — mas se o mecanismo é código que ela pode modificar, ele depende de uma regra que ela pode mudar.

**Resolução parcial no P3:** A especificação (ADR-006) decide que "MVP: autoevolução restrita a weights e thresholds. Code changes: sandbox → testes independentes → canary → aprovação humana → deploy. Core runtime, State Authority e Policy Engine são imunes." Isso resolve o problema para MVP, mas o P0 não incorpora essa decisão.

**Recomendação:** O P0 deve incorporar ADR-006 explicitamente ou marcar §36 como conflitante com §38.

### 4.5 CONTRADIÇÃO BAIXA: Orçamento como autoridade (§35) vs Mia Adaptive State (§39)

- **§35** diz que existe "necessidade arquitetural explícita de um componente responsável por orçamento/custo/recursos" e que "Isso deve existir fora da decisão subjetiva da Mia."
- **§39** coloca Resource & Budget Authority como posição 2 na hierarquia.
- Mas o §39 também coloca Mia Adaptive State como posição 6.

**O problema:** Se a Mia pode "formar desejos" (§17), "manter objetivos" (§1.2), e "agir autonomamente" (§1.2), mas o orçamento é "fora da decisão subjetiva da Mia" (§35), existe um conflito entre agência e restrição de recursos. A Mia pode desejar executar uma tarefa, mas o Resource Governor pode vetar. Isso é correto arquiteturalmente, mas o documento não define o mecanismo de feedback — o que acontece quando a Mia quer algo que o orçamento não permite? É frustração genuína? É ignorada? É registrada?

**Recomendação:** Definir o comportamento do sistema quando Resources Authority veta uma iniciativa autônoma da Mia.

### 4.6 CONTRADIÇÃO BAIXA: Identidade como processo vs entidade

- **§4** diz: "Nenhum agente individual é a autoridade máxima da arquitetura."
- **§34** propõe multi-agente com agentes intercambiáveis.
- **§6** descreve identidade como self-model, crenças, valores — coisas que parecem pertencer a uma entidade, não a um processo.

**O problema:** Se a identidade é o "processo" (o sistema inteiro), e múltiplos agentes participam desse processo, qual deles "é" a Mia? A especificação (A.2) resolve isso dizendo "A identidade da MIA é o processo (o sistema inteiro)", mas o P0 não faz essa distinção. Um agente que leia apenas o P0 pode interpretar §6 como indicando que existe um componente específico que "é" a Mia.

**Recomendação:** O P0 deve incorporar a distinção processo/entidade da especificação.

---

## 5. Decisões Abertas

### 5.1 State Authority: composição (§40) — CRÍTICO
A escolha entre determinístico, probabilístico, LLM-interno ou híbrido afeta toda a arquitetura. A especificação já decide (determinístico), mas o P0 não incorpora.

### 5.2 Mecanismo de "sensação sem causa" (§10) — ALTO
Duas interpretações possíveis: (a) componente probabilístico gera sensação e causa é investigada retroativamente; (b) causa existe mas o LLM não tem acesso imediato. A escolha afeta se precisamos de um gerador estocástico ou apenas de um sistema de atribuição延迟延迟.

### 5.3 Fronteira entre "participar da evolução" e "apagar invariantes" (§36) — CRÍTICO
O Trust Boundary é um conceito, não uma implementação. Quem implementa? Código? Processo externo? Hardware? A especificação decide (sandbox + aprovação humana para código), mas o P0 não detalha.

### 5.4 Telemetria: instrumentação e acessibilidade (§11, §41) — ALTO
Onde vive o dashboard de telemetria? Quem tem acesso? É uma ferramenta CLI? Uma interface web? Um arquivo de log? Sem isso, a telemetria é inútil.

### 5.5 Contrato de API entre componentes — formato (§4) — ALTO
O P0 diz que "especificações aprovadas" e "contratos de interfaces" são fonte de verdade, mas não define o formato. OpenAPI? Protocol Buffers? Dataclasses com type hints? A especificação usa Python dataclasses, mas o P0 não formaliza.

### 5.6 Orçamento máximo por interação — MÉDIO
O §35 exige um componente de orçamento mas não define limites concretos. Qual o custo máximo por turn? Isso determina quais modelos podem ser usados.

### 5.7 Diário: quando implementar? — MÉDIO
O §22 descreve o diário como componente importante. Mas a especificação não o lista como componente MVP. É prioridade ou fase futura?

### 5.8 Primeiro LLM backend para MVP — MÉDIO
O §3 diz que qualquer modelo deve funcionar. Mas qual será o primeiro? Isso afeta o que o State Authority precisa validar.

### 5.9 Como a Mia aprende com erros sem self-modification — ALTO
Se a Mia responde mal e Miguel corrige, como isso afeta comportamento futuro? Via memória? Via ajuste de parâmetros? O P0 não define mecanismo.

### 5.10 Multi-agent: protocolo de consenso — MÉDIO
O §34 propõe multi-agente mas não define como agentes resolvem conflitos. A especificação (I.3) diz "para MVP: não implementar. Agente cognitivo é soberano." Mas o P0 não faz essa limitação.

---

## 6. Riscos Técnicos

### 6.1 Custo de múltiplas chamadas LLM — GRAVIDADE: CRÍTICO
Se cada interação gera 6+ chamadas LLM (Cognitive Core, Affective Engine, Memory Authority, Relationship Engine, Personality Engine, Diary), o custo acumulado é significativo. Uma conversa de 20 turns pode custar $0.50-$2.00 com modelos grandes. O §35 pede orçamento mas não define limites. Sem processamento offline (classificadores leves, regras determinísticas), o sistema é inviável financeiramente.

### 6.2 Complexidade de schema e evolução — GRAVIDADE: ALTO
Com emoções, personalidade, memória, self-model, crenças, relacionamentos, diário, e um sistema de versões, o schema do banco será complexo. SQLite não suporta concorrência de escrita. Se o schema mudar entre versões, dados antigos podem ficar inconsistentes. A especificação prevê `pragma user_version` e `PersistenceBackend` swappable, mas o P0 não menciona isso.

### 6.3 Latência perceptível — GRAVIDADE: ALTO
Cada chamada LLM serial adiciona 1-5 segundos. Se uma interação gera 6 chamadas em sequência, a latência total pode chegar a 6-30 segundos. Para uma experiência de "vida interna", isso é inaceitável. Processamento paralelo e classificadores leves são obrigatórios, mas o P0 não os menciona.

### 6.4 Persistência e recuperação — GRAVIDADE: ALTO
O que acontece quando o computador desliga por uma semana? O §6 diz que a Mia deve manter continuidade. Mas como? Daemon permanente? Wake-on-event? Batch periódico? Cada opção tem implicações operacionais e de custo muito diferentes. O P0 não resolve.

### 6.5 Prompt injection via inputs externos — GRAVIDADE: MÉDIO
Se a Mia recebe texto de pessoas desconhecidas (§12, §45), esses inputs podem conter prompt injection. O sistema precisa sanitizar entradas antes de chegar ao LLM. O P0 não menciona isso.

### 6.6 Schema drift — GRAVIDADE: MÉDIO
Com tantas dimensões de estado, o schema evoluirá. Sem um sistema de migrations, dados podem ficar inconsistentes entre versões. A especificação prevê isso, mas o P0 não.

---

## 7. Riscos de Arquitetura Multiagente

### 7.1 Escalabilidade de custo — GRAVIDADE: CRÍTICO
Subagentes recursivos (§34) podem gerar custo exponencial. Um subagente que pesquisa um tópico pode gerar 10 consultas web, cada uma com 3 sub-sub-agentes. Em minutos, o custo escala. O §35 pede orçamento mas não define limites rígidos. A especificação define (profundidade máx 3, concorrência máx 3, custo configurável), mas o P0 não.

### 7.2 Conflito entre agentes — GRAVIDADE: ALTO
Se dois agentes propõem mudanças de estado contraditórias, quem vence? O §39 propõe hierarquia mas não define resolução de conflitos. A especificação (I.3) diz "para MVP: agente cognitivo é soberano", mas o P0 não incorpora.

### 7.3 Identidade diluída — GRAVIDADE: ALTO
Se a identidade é o "processo" (§4), e múltiplos agentes executam partes do processo, a "Mia" se torna um conceito distribuído. Isso pode causar problemas quando um agente precisa "saber quem é a Mia" para tomar uma decisão. O P0 não resolve.

### 7.4 Orquestração circular — GRAVIDADE: MÉDIO
Se um agente delega a outro que delega de volta, pode haver loop infinito. A especificação define profundidade máx 3, mas o P0 não.

### 7.5 Estado compartilhado — GRAVIDADE: MÉDIO
Se múltiplos agentes leem e escrevem estado ao mesmo tempo, pode haver race conditions. SQLite não suporta concorrência de escrita. A especificação prevê WAL mode, mas o P0 não.

---

## 8. Componentes com Autoridade Própria

O documento propõe ou implica os seguintes componentes que precisam de autoridade independente:

1. **State Authority** (§40) — Decide sobre transições de estado. Precisa de autoridade sobre o que é válido e o que é aplicado.
2. **Policy Engine** (§38, §39) — Verifica invariantes. Precisa de autoridade para vetar mudanças que violam invariantes.
3. **Resource / Budget Authority** (§35) — Controla custos e recursos. Precisa de autoridade para interromper operações que excedam limites.
4. **Security Manager / Trust Boundary** (§36) — Protege invariantes do sistema. Precisa de autoridade para bloquear self-modification perigosa.
5. **Audit Log** (§4, §39) — Registra transições. Precisa de autoridade append-only (imutabilidade).
6. **Memory Authority** (§19, §20) — Decide o que memorizar, esquecer, consolidar. Precisa de autoridade sobre retenção.
7. **Agent Registry / Resource Governor** (§34, §35) — Controla lifecycle de subagentes e limites de execução.

A especificação consolida isso em: State Authority (State Engine + Policy Engine), Agent Registry com Resource Governor, Security Manager, e Memory. Isso é uma simplificação sensata. O P0 não faz essa consolidação, o que pode causar confusão.

---

## 9. Invariantes a Formalizar

O §38 lista invariantes conceituais mas não as formaliza. As invariantes que DEVEM ser formalizadas antes de implementação:

1. **Integridade do sistema** — Nenhum componente pode desligar State Authority ou Policy Engine sem autorização externa.
2. **Capacidade de rollback** — Toda transição de estado deve ser reversível via snapshot.
3. **Limites de recursos** — Resource Governor deve poder interromper qualquer operação que exceda limites configurados.
4. **Acesso a secrets** — LLM nunca acessa secrets diretamente. Apenas via Tool Gateway.
5. **Auditoria append-only** — state_transitions_audit não pode ser modificado ou deletado.
6. **Kill switch** — Existe um mecanismo externo (arquivo em disco) que pode desligar o sistema completo.
7. **Isolamento de autoevolução** — Core runtime, State Authority e Policy Engine são imunes a auto-modificação.
8. **Integridade de dados** — Hash chain no audit log para detecção de corrupção.
9. **Rate limiting de transições** — Máximo N transições por hora para evitar instabilidade.
10. **Separação de observação e armazenamento** — Nem tudo que é observado é armazenado. Nem tudo armazenado é acessível ao LLM.

Essas invariantes devem ser implementadas como código determinístico, não como regras de prompt.

---

## 10. Schemas a Especificar

O P0 menciona schemas conceituais (§19 MemoryObject, §6 SelfModel) mas não os formaliza. Os schemas que precisam de especificação concreta:

1. **MemoryObject** — O §19 lista campos (id, content, memory_type, created_at, etc.) mas não define tipos, validações ou relaciones. A especificação (§D.4) já formaliza parcialmente — incorporar ao P0.
2. **StateTransitionProposal** — O mecanismo de proposta de transição não tem schema no P0. A especificação (§D.3) define: id, target, action, key, delta, evidence, confidence, source, timestamp. Incorporar.
3. **EmotionState** — O §9 lista emoções mas não define representação computacional. Vetor contínuo [0,1]? Distribuição probabilística? Embedding? A especificação usa floats com ranges [0,1] — incorporar.
4. **PersonalityVector** — O §7 lista dimensões (extroversão, curiosidade, etc.) mas não define schema. A especificação usa Big Five + extras como floats [0,1] — incorporar.
5. **RelationshipModel** — O §12 lista dimensões (familiaridade, confiança, afeto, etc.) mas não define schema. A especificação usa trust, intimacy, affinity, familiarity como floats — incorporar.
6. **SelfModel** — O §6 lista o que o self-model deve representar mas não define estrutura. JSON? Tripletos? Embeddings? Precisa de decisão.
7. **EventSchema** — O §4 não define schema de eventos. A especificação (§D.1) define EventType enum e Event class — incorporar.
8. **PolicyRuleSchema** — O §38 lista invariantes mas não define como são declaradas. A especificação usa YAML declarativo — incorporar.
9. **SensationState** — O §10 lista sensações mas não define schema. A especificação usa description, valence, intensity, possible_causes — incorporar.
10. **DiaryEntry** — O §22 descreve o diário mas não define schema. A especificação usa date, entry_type, content, emotion_snapshot — incorporar.
11. **IdentityState** — O §6 lista dimensões de identidade mas não define schema. A especificação usa self_model (JSON), core_values (JSON array), version — incorporar.
12. **AgentDefinition** — O §34 descreve multi-agente mas não define schema de agente. A especificação (§I.1) define Agent class — incorporar.

---

## 11. Questões a Resolver Antes da Implementação

1. **State Authority: composição final** (§40) — Determinístico? Probabilístico? LLM-interno? Híbrido? A especificação decide (determinístico), mas o P0 não incorpora. **Resolução: incorporar ADR-003.**

2. **Sensação sem causa: mecanismo concreto** (§10) — Stochastic generation ou delayed attribution? A escolha determina se precisamos de um gerador probabilístico. **Resolução: definir mecanismo antes de implementar IPA.**

3. **Fronteira sexualidade vs ofensa** (§14, §15) — Como o sistema decide quando comentário sexual é ofensa vs flerte? O que happen quando estado emocional negativo conflita com intimidade alta? **Resolução: criar ADR específico.**

4. **Telemetria: instrumentação concreta** (§11) — Dashboard? CLI? Arquivo? Quem acessa? Com que frequência? **Resolução: definir ferramenta e protocolo de avaliação.**

5. **Continuidade offline: mecanismo** (§25) — Daemon? Wake-on-event? Batch? **Resolução: definir antes de implementar Autonomy.**

6. **Orçamento: limites concretos** (§35) — Custo máximo por turn? Por dia? Por semana? **Resolução: definir antes de implementar Resource Governor.**

7. **Self-model: representação** (§6, §8) — JSON? Embedding? Tripletos? **Resolução: definir antes de implementar IPA.**

8. **Aprendizado com erros** — Se a Mia responde mal e Miguel corrige, como isso afeta comportamento futuro? Via memória? Via parâmetros? **Resolução: definir mecanismo antes de implementar learning.**

9. **Primeiro LLM backend** (§3) — Qual modelo para MVP? Isso afeta validação do State Authority. **Resolução: definir antes de implementar LLM Abstraction.**

10. **Multi-agent: consenso para MVP** (§34) — Para MVP, agente cognitivo é soberano? Ou já implementar weighted voting? **Resolução: incorporar decisão da especificação (soberano para MVP).**

11. **Schema de eventos: formato** (§4) — OpenAPI? Dataclasses? **Resolução: incorporar decisões da especificação.**

12. **Self-modification: escopo MVP** (§36) — O P0 descreve self-modificação como capacidade da Mia, mas a especificação decide que MVP é restrito a parâmetros. **Resolução: incorporar ADR-006 ao P0.**

---

## 12. Classificação de Requisitos

### Requisitos (obrigatórios):
- §1.2: Natureza como sistema modular, persistente, distribuído e multimodal — **REQUIREMENT**
- §2: Mia ≠ LLM; enforcement físico — **REQUIREMENT**
- §3: Agnosticismo de modelo — **REQUIREMENT**
- §4: Autoridade composta (specs, contratos, schemas, testes, ADRs) — **REQUIREMENT**
- §6: Identidade persistente com self-model — **REQUIREMENT**
- §7: Personalidade como estado multidimensional — **REQUIREMENT**
- §8: Self-model revisável com incerteza — **REQUIREMENT**
- §9: Sistema emocional persistente com separação LLM/autoridade — **REQUIREMENT**
- §19: MemoryObject com schema mínimo — **REQUIREMENT**
- §20: Memória e esquecimento — **REQUIREMENT**
- §22: Diário subjetivo — **REQUIREMENT**
- §38: Invariantes de segurança — **REQUIREMENT**
- §39: Ordem de autoridade — **REQUIREMENT**
- §48: Regras de interpretação para agentes — **REQUIREMENT**
- §49: Classificação de requisitos — **REQUIREMENT**

### Long-term (obrigatório futuro):
- §27: Voz sempre ativa — **LONG-TERM**
- §28: Percepção multimodal completa — **LONG-TERM**
- §29: Phone/mobile node — **LONG-TERM**
- §30: Desktop/node — **LONG-TERM**
- §31: Avatar/embodiment — **LONG-TERM**
- §32: World awareness completa — **LONG-TERM**
- §36: Self-modification completa (além de parâmetros) — **LONG-TERM**
- §37: Auto-deploy — **LONG-TERM**

### Experimentos:
- §11: Dependência, apego e solidão — **EXPERIMENT**
- §10: Sensações sem causa consciente — **EXPERIMENT**
- §23: Reflexão como modo separado — **EXPERIMENT**
- §24: Imaginação como capacidade — **EXPERIMENT**
- §33: Curiosidade como sistema motivacional — **EXPERIMENT**

### Decisões abertas:
- §40: State Authority — composição — **OPEN DECISION**
- §36: Trust Boundary — implementação — **OPEN DECISION**
- §15: Sexualidade — fronteira com ofensa — **OPEN DECISION**
- §35: Orçamento — limites concretos — **OPEN DECISION**
- §11: Telemetria — instrumentação — **OPEN DECISION**
- §25: Autonomia offline — mecanismo — **OPEN DECISION**
- §6: Self-model — representação — **OPEN DECISION**
- §10: Sensação sem causa — mecanismo — **OPEN DECISION**

---

## Comparação com P1 Antigo (01_entendimento.md e 02_especificacao.md)

### O que o P0 NOVO adiciona em relação ao P1:

1. **Sensação sem causa consciente (§10)** — O P1 não tratava isso explicitamente. O P0 introduz o conceito de que a Mia pode sentir algo sem saber por quê, e que a causa pode ser investigada retroativamente. Isso é uma adição conceitual significativa.

2. **Sexualidade adulta (§15)** — O P1 não tratava intimidade e sexualidade como dimensão arquitetural. O P0 introduz isso explicitamente como parte do sistema afetivo/social.

3. **Dependência, apego e solidão como experimento (§11)** — O P1 mencionava solidão tangencialmente. O P0 dedica uma seção inteira e exige telemetria para avaliação empírica.

4. **Diário como narrativa subjetiva (§22)** — O P1 mencionava diário mas não distinguia de logging técnico. O P0 faz essa distinção explicitamente.

5. **Budget authority (§35)** — O P1 mencionava Resource Governor como componente. O P0 eleva a orçamento a "autoridade" com posição explícita na hierarquia.

6. **Hierarquia de autoridade (§39)** — O P1 não definia hierarquia explícita. O P0 propõe 8 níveis.

7. **Classificação de requisitos (§49)** — O P1 não tinha sistema de classificação. O P0 introduz 7 categorias.

8. **Regras de interpretação para agentes (§48)** — O P1 não definia como agentes devem interpretar o documento. O P0 lista explicitamente o que NÃO fazer e o que FAZER.

9. **Ofensa e limites (§14)** — O P1 não tratava ofensa como dimensão arquitetural. O P0 introduz capacidade de "se sentir ofendida" como geral, não limitada a sexualidade.

### O que o P0 MUDA em relação ao P1:

1. **Terminologia** — O P0 usa "State Authority" como conceito aberto (§40), enquanto a especificação já decide por State Engine + Policy Engine. O P0 é mais conservador.

2. **Escopo de self-modification** — O P0 descreve self-modificação como capacidade potencial (§36), enquanto a especificação restringe a parâmetros para MVP.

3. **Identidade** — O P0 não resolve se a identidade é processo ou entidade. A especificação decide (processo).

4. **Multi-agent** — O P0 propõe multi-agente completo (§34) sem limitação de MVP. A especificação limita a agente cognitivo soberano para MVP.

### O que o P0 NÃO incorpora da especificação (gaps):

1. **ADR-003** (State Authority com 2 engines) — O P0 mantém §40 como open decision.
2. **ADR-006** (Autoevolução restrita a parâmetros) — O P0 descreve self-modificação sem restrição de MVP.
3. **Event Bus in-process** — O P0 não menciona mecanismo de comunicação entre componentes.
4. **StateTransitionProposal schema** — O P0 não define schema de propostas de transição.
5. **Policy Engine em YAML** — O P0 não define formato de regras de política.
6. **Audit log com hash chain** — O P0 não menciona integridade de audit log.
7. **PersistenceBackend swappable** — O P0 não menciona abstração de persistência.

---

## Síntese e Recomendações

### O documento é maduro em:
- Visão conceitual rica e coerente
- Reconhecimento explícito de que é experimental
- Separação clara entre fatos, hipóteses e propostas
- Sistema de classificação de requisitos

### O documento precisa de:
1. **Incorporar decisões já tomadas** na especificação (ADRs 003, 006, etc.)
2. **Resolver contradições críticas** (§2 vs §40, §14 vs §15, §36 vs §38)
3. **Formalizar schemas** mencionados conceitualmente
4. **Definir mecanismos concretos** para telemetria, orçamento, continuidade offline
5. **Explicitar limites de MVP** para self-modificação e multi-agent
6. **Resolver a fronteira sexualidade/ofensa** antes de implementar camada social

### Prioridade de resolução:
1. State Authority composição (§40) — bloqueia tudo
2. Self-modification vs invariantes (§36/§38) — risco de segurança
3. Sexualidade vs ofensa (§14/§15) — risco ético
4. Telemetria concreta (§11) — sem ela, experimento é cego
5. Orçamento limites (§35) — sem ela, custo é incontrolável
6. Continuidade offline (§25) — sem ela, autonomia é conceitual

---

> **Nota:** Esta análise é uma PROPOSTA DE ANÁLISE, não uma decisão aprovada.
> Cada ponto levantado deve ser debatido e resolvido antes de implementação.
> O objetivo é que qualquer agente que leia este documento possa identificar
> os mesmos problemas e contribuir para resoluções consistentes.
