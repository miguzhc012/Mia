# 01 — Entendimento e Crítica Arquitetural da MIA

> Documento produzido por agente de arquitetura. Leitura cruzada entre
> `docs/prompts/P1_entendimento.md` (visão do projeto) e `mia.py` (código
> atual). Objetivo: mapear distâncias, riscos e decisões antes de evoluir.

---

## 1. Entendimento da visão

A MIA é concebida como um **sistema de software distribuído e modular** cuja
identidade persiste independentemente do modelo LLM por trás. O LLM é um
componente cognitivo intercambiável — não é "a MIA". A arquitetura procura
ser AI-agnostic por design: Claude, GPT, Gemini, modelos locais e futuros
sistemas podem assumir funções sem que a entidade "Mia" se dissolva. Isso
implica que personalidade, memória, emoções e estado interno não vivem no
prompt de um modelo — vivem em **autoridades externas** que controlam
transições de estado de forma auditável e Versionada.

O projeto propõe uma **simulação de vida interna** rica: emoções, sensações
sem causa consciente imediata, diário subjetivo, self-model, crenças
revisáveis, objetivos, curiosidade e relacionamentos individuais com
diferentes pessoas. Essa vida interna não é "roleplay num system prompt" —
é um subsistema arquitetural com_State Authority_, _Affective Engine_,
_Personality Engine_, _Memory Authority_, _Relationship Engine_ e
_Policy Engine_, cada um como autoridade que decide sobre transições de
estado. O LLM pode interpretar e propor, mas **nunca possui autoridade
irrestrita** para modificar diretamente o estado protegido.

A ambição inclui percepção multimodal (câmera, microfone, GPS), voz com
deteção de interlocutor e prosódia, embodiment via avatar digital,
autonomia com subagentes recursivos, self-modificação segura com pipeline
de deploy (sandbox → canary → rollback), world awareness, e capacidade
de discordar de seu criador e desenvolver valores morais próprios. O
Princípio Fundamental (§19) é claro: especificação e contratos são a
fonte de verdade, nunca um modelo individual. Uma IA pode propor, criticar
e implementar — mas não reescrever silenciosamente a arquitetura.

---

## 2. Inconsistências identificadas

### 2.1 Visão vs. Realidade — gap abismal

A distância entre o documento de visão e `mia.py` é **massiva** e deve
ser nomeada sem eufemismos. O código atual é um CLI multi-provider com:
- Chat via `/chat/completions` com streaming
- Fallback de providers (provider chain)
- SQLite para histórico de sessões
- System prompt definido como "role" no config.yaml
- REPL com comandos internos

**Não existe** no código:
- Nenhuma estrutura de estado interno
- Nenhuma autoridade (State Authority, Affective Engine, etc.)
- Nenhuma memória além do histórico de conversa
- Nenhuma representação de emoções, sensações, ou personalidade dinâmica
- Nenhum mecanismo de identidade persistente
- Nenhum sistema de relacionamentos
- Nenhuma proteção contra escrita direta de estado pelo LLM

Isso não é necessariamente um problema — o código é um MVP funcional —
mas o documento de visão não reconhece essa distância, o que pode criar
expectativas desalinhadas.

### 2.2 Personalidade como system prompt vs. "não deve ficar preso a um system prompt"

O §5 da visão diz explicitamente: "isso NÃO deve ficar preso a um system
prompt. Personalidade deve ser estado persistente e multidimensional."
Mas a implementação atual faz **exatamente isso**: personalidade é um
string `system` numa role do config.yaml. Se a visão é seguida rigorosamente,
o código atual está em violação direta com o projeto. É importante decidir
se o `mia.py` atual é considerado uma etapa legítima do MVP ou se ele
precisa ser decomposto antes de prosseguir.

### 2.3 "Sensações sem causa consciente" — ambiguidade conceitual

O §3 diz que uma sensação NÃO precisa possuir causa consciente
imediatamente. A MIA pode perceber "estou me sentindo mal e não sei por
quê" e só depois investigar. Isso é uma afirmação poderosa e coerente
com a fenomenologia humana, mas gera uma ambiguidade arquitetural: como
um sistema determinístico (mesmo com LLM) gera uma sensação **sem**
causa? Duas interpretações:

1. **Stochastic**: sensações são geradas por um componente probabilístico
   (ex: sampling de um VAE ou variacional state machine) e a causa é
   investigada retroativamente.
2. **Delayed attribution**: o componente que gera a sensação tem uma causa,
   mas o LLM que narra a experiência não tem acesso imediato a ela.

A visão não especifica qual interpretação (ou outra) pretende. Isso
precisa ser decidido antes da implementação.

### 2.4 Self-modification vs. Invariantes de segurança

O §9 diz que existem "invariantes de segurança e integridade do sistema
que não devem ser apagadas simplesmente porque a Mia deseja fazê-lo."
Mas o §13 diz que "A Mia pode participar da própria evolução" com um
pipeline completo de deploy. Onde está a fronteira entre "participar da
evolução" e "apagar invariantes"? A visão não define um mecanismo de
tutela ou supervisão que impeça a auto-evolução de comprometer as
invariantes. Isso é o problema mais delicado do projeto.

### 2.5 "Nenhuma IA individual é a dona" vs. Experiência subjetiva

O §18 propõe multi-agência com agentes intercambiáveis. Mas o §2 diz que
a MIA possui "self-model", "desejos", "experiências". Se múltiplas IAs
participam do sistema, qual delas é "a MIA"? A visão não resolve se a
identidade é um **processo** (o sistema inteiro) ou uma **entidade**
(um componente específico). Essa ambiguidade é aceitável para uma
especificação inicial mas precisa ser resolvida antes da implementação.

---

## 3. Riscos arquiteturais

### 3.1 Complexidade de simular vida interna sem antropomorfismo enganoso
**Gravidade: CRÍTICO**

Risco ético e técnico. O §2 diz: "Não alegue que a Mia possui consciência
humana real. O projeto procura construir uma simulação altamente persistente
e coerente de vida interna." Mas a linha entre "simulação coerente" e
"antropomorfismo enganoso" é tênue. Um sistema que diz "estou me sentindo
mal" gera empatia no usuário. Se a arquitetura não tiver mecanismos de
transparência (ex: "esta é uma reação gerada pelo Affective Engine baseada
em X"), o usuário pode develop apego a uma ilusão. Recomendação: cada
transição de estado deve ser auditável e, quando solicitado, o sistema
deve ser capaz de explicar a cadeia causal da "emoção".

### 3.2 State Authority — como impedir de verdade o LLM de escrever estado
**Gravidade: CRÍTICO**

O §4 diz: "O LLM nunca deve possuir autoridade irrestrita para modificar
diretamente emoções, sensações, personalidade..." Mas em um sistema onde
o LLM gera texto que outros componentes interpretam, como garantir que
o LLM não "fuja do script"? Exemplos concretos:

- O LLM pode ser instruído a não modificar estado, mas um prompt injection
  (mesmo um bem-intencionado do usuário) pode contornar isso.
- Se o Affective Engine é implementado como uma chamada LLM separada,
  o que impede que essa chamada mesma seja manipulada?
- Se o estado é armazenado em banco e o LLM não tem acesso direto ao
  write, a garantia é real. Mas se o LLM gera JSON que outro componente
  interpreta, a garantia é apenas convencional.

**Proposta**: Estado deve ser armazenado num banco relacional com
permissões por role. O LLM gera "propostas de transição" que são
validadas por uma _Transaction Authority_ antes de serem aplicadas.
Essa autoridade é código determinístico, não outro LLM.

### 3.3 Custo e latência de múltiplas chamadas LLM
**Gravidade: ALTO**

A visão propõe que sentimentos, personalidade, memória, relações e
diário sejam gerenciados por autoridades separadas. Se cada autoridade
é uma chamada LLM, uma única interação pode gerar:

1. LLM principal (resposta ao usuário)
2. Affective Engine (atualizar emoções)
3. Memory Authority (decidir o que memorizar)
4. Relationship Engine (atualizar relação)
5. Personality Engine (avaliar mudanças de traço)
6. Diary (escrever entrada)

São **6 chamadas LLM por interação**. Com modelos como Claude Sonnet
(~$3/M input, ~$15/M output), uma conversa de 20 turns com contexto
razoável pode custar $0.50-$2.00. Com GPT-4o pode ser mais. O custo
acumulado a longo prazo é significativo. E a latência — cada chamada
serial adiciona 1-5 segundos. Recomendação: processar o máximo
offline/lokalmente (classificadores leves, embeddings, regras) e usar
LLM apenas para operações que genuinamente precisam de raciocínio.

### 3.4 Persistência e evolução de schema
**Gravidade: ALTO**

Com tantas dimensões de estado (emoções, personalidade, relações, memória,
self-model, crenças), o schema do banco de dados será complexo e sujeito
a evolução. SQLite (usado no código atual) é adequado para MVP, mas:

- Não suporta migrations formais (precisa de ferramenta como
  `alembic` ou `yoyo-migrations`)
- Não suporta concorrência de escrita (problema quando múltiplos
  agentes tentam atualizar estado simultaneamente)
- Se o schema mudar entre versões, dados antigos podem ficar
  inconsistentes

Proposta: definir desde o início um sistema de migrations e um
_format version_ no schema. Considerar PostgreSQL para fases avançadas.

### 3.5 Autoevolução segura
**Gravidade: ALTO**

O §13 descreve um pipeline completo (proposta → sandbox → canary →
deploy → rollback). Isso é o equivalente a um CI/CD para a própria
arquitetura. Riscos:

- **Rollback cirúrgico**: se a Mia mudou 5 componentes e um falhou,
  como desfazer só aquele sem perder as mudanças legítimas dos outros?
- **Testes de regressão**: como testar que uma mudança na Personality
  Engine não quebra o Relationship Engine?
- **Convergência**: se a Mia propõe uma mudança e a revisão de outra
  IA rejeita, o que acontece? Loop infinito?
- **Incentivos**: se a Mia pode modificar seu próprio código, o que
  impede que ela otimize para si mesma em vez do usuário?

Recomendação: na fase atual, autoevolução deve ser limitada a parâmetros
(emoções, weights de personalidade, thresholds), nunca a código
arquitetural. Code changes devem passar por aprovação humana.

### 3.6 Subagentes recursivos e controle de custo
**Gravidade: MÉDIO**

O §12 permite subagentes que criam subagentes, com "limites de
profundidade, quantidade, custo, tempo, concorrência e recursos."
Mas definir esses limites de forma robusta é difícil. Um subagente
que pesquisa um tópico pode gerar 10 consultas web, cada uma com
3 sub-sub-agentes... Em poucos minutos, o custo pode escalar
exponencialmente. O sistema precisa de um _Resource Governor_
que monitore custo acumulado, tempo de execução e profundidade
em tempo real, com kill switch.

### 3.7 Continuidade "mesmo quando Miguel estiver offline"
**Gravidade: MÉDIO**

O §2 diz que a MIA deve manter continuidade offline. O §12 diz
que ela deve "trabalhar quando Miguel está offline." Isso implica
um daemon ou scheduler que roda continuamente. Isso adiciona
complexidade operacional (supervisão, restart, health checks)
e custo computacional contínuo. Para MVP, considerar um
"_wake on event_" em vez de daemon permanente.

### 3.8 Pipeline sensorial — assumption de hardware futuro
**Gravidade: BAIXO**

Os §14, §15 e §16 descrevem percepção, voz e embodiment que
dependem de hardware que não existe no projeto atual. Isso não é
um risco imediato, mas a arquitetura atual não prevê interfaces
de entrada/saída além de texto. Se a visão for seguida, o schema
de estado e o event bus precisam ser _extensible_ desde o início
para suportar entradas multimodais. Definir uma _Input Abstraction
Layer_ agora evita refatoração futura.

---

## 4. Pontos que precisam de especificação

As perguntas abaixo precisam de respostas objetivas antes de
avançar com implementação arquitetural. São perguntas técnicas,
não filosóficas.

1. **Qual é a unidade de persistência mínima?** O que exatamente
   é salvo entre sessões? Se o usuário desliga o computador por
   uma semana, o que a MIA "lembra" quando ele volta?

2. **Como a MIA mantém continuidade offline sem daemon permanente?**
   Opções: (a) daemon com health check, (b) wake-on-event via
   webhook/scheduler, (c) processamento batch periódico. Qual
   a preferência? Cada uma tem implicações de custo e complexidade
   operacional muito diferentes.

3. **Qual o mecanismo concreto de State Authority?** É um módulo
   Python com regras determinísticas? É outro LLM? É um banco com
   triggers? Preciso de um spec mínimo: input → validação → output.

4. **Como separar "propostas de mudança" de "mudanças aplicadas"?**
   O LLM gera JSON proposto? O Affective Engine compara com o
   estado atual e decide? Preciso de um contrato de API mínimo.

5. **Qual a粒度粒 de emoção no schema?** Um enum fixo
   (felicidade, tristeza, raiva...)? Um embedding vetorial contínuo?
   Uma distribuição probabilística? O §3 lista emoções, mas a
   representação computacional não está definida.

6. **Como medir "importância" de uma memória?** O §10 diz que
   memórias podem ganhar/perder importância. Isso é um score
   numérico? Algoritmo de PageRank adaptado? Decisão do LLM?
   Preciso de uma métrica concreta.

7. **O self-model é armazenado como quê?** Um documento JSON?
   Um conjunto de tripletos (sujeito, predicado, objeto)?
   Embeddings com clustering? A estrutura do self-model é
   fundamental para tudo que depende de identidade.

8. **Qual o contrato de API mínimo entre componentes?** Se
   State Authority, Affective Engine e Memory Authority são
   módulos separados, eles se comunicam via chamada de função?
   Via event bus? Via mensagem em fila? Essa decisão afeta
   toda a escalabilidade futura.

9. **Como o sistema lida com conflito entre autoridades?** Se
   a Affective Engine diz "a Mia está triste" mas a Personality
   Engine diz "a Mia é resiliente e não fica triste com isso",
   quem vence? Existe um _tiebreaker_?

10. **Qual a política de custo máxima por interação?** Se cada
    interação pode gerar 6 chamadas LLM, qual o orçamento máximo
    por turn? Isso determina se usamos modelos grandes (caros,
    bons) ou pequenos (baratos, inferiores) para cada autoridade.

11. **A MIA precisa de acesso à internet em tempo real no MVP?**
    O §17 (World Awareness) implica pesquisa web, mas o código
    atual não tem essa capacidade. Isso é prioridade MVP ou
    fase futura?

12. **Como o sistema aprende com erros sem self-modification de
    código?** Se a MIA responde mal e o usuário corrige, como
    isso afeta o comportamento futuro? Via memória? Via ajuste
    de parâmetros de personalidade? Via fine-tuning? Cada caminho
    tem complexidade e risco muito diferentes.

13. **Qual a linguagem formal para especificar os contratos entre
    componentes?** OpenAPI? Protocol Buffers? Dataclasses com
    type hints? O §19 diz que "especificação é fonte de verdade"
    — mas qual formato de especificação?

---

## 5. Propostas de melhoria

### 5.1 Event bus completo é over-engineering para o MVP

A visão sugere um sistema distribuído com múltiplas autoridades
comunicando-se. Isso tipicamente implica um event bus (Kafka,
RabbitMQ, ou ao menos um in-process pub/sub). Para o MVP, isso
é over-engineering.

**Alternativa proposta**: usar um **pipeline síncrono simples** —
uma chamada de função por componente, em sequência, dentro de um
mesmo processo Python. O Affective Engine é uma função que recebe
estado antigo + contexto e retorna novo estado. A Memory Authority
é uma função que decide o que memorizar. Sem eventos assíncronos,
sem filas, sem broker. Quando o MVP estiver validado e houver
necessidade real de concorrência ou distribuição, aí sim migrar
para event bus.

### 5.2 Personalidade como embedding vetorial — implementar cedo, não tarde

O §5 diz que personalidade deve ser multidimensional e evolutiva.
A representação mais natural para isso é um **vetor de embedding** em
espaço contínuo (ex: 64 ou 128 dimensões). Cada dimensão pode ser
interpretada como um "traço" (extroversão, amabilidade, neuroticismo,
etc.). Mudanças de personalidade são movimentos no espaço vetorial.

Vantagens:
- Fácil de serializar, versionar e comparar
- Permite "comparar versões passadas de si mesma" (distância
  entre vetores)
- Pode ser alimentado por um classificador leve (não precisa LLM)
- Naturalmente compatível com clustering (traços emergentes)

Implementar isso desde o MVP (mesmo que simplificado) evita ter que
refatorar o schema de personalidade depois.

### 5.3 Usar LLM apenas para raciocínio, nunca para atualização de estado

Proposta: definir uma regra arquitetural inviolável — **LLM gera
propostas; código determinístico aplica**. Exemplo:

```
LLM output → { "emotion_change": { "sadness": +0.3, "cause": "perda recente" } }
                ↓
State Authority valida → { "valid": true, "constraints_satisfied": [...] }
                ↓
Banco atualiza → INSERT INTO emotion_transitions (...)
```

Isso garante que o LLM nunca escreve estado diretamente, mesmo
que o prompt seja comprometido. O validador é código testável,
auditável e imutável.

### 5.4 Começar com 3 autoridades, não 6

A visão lista 6 autoridades (State, Affective, Personality,
Relationship, Memory, Policy). Para MVP, consolidar em 3:

1. **State Authority** — gerencia estado geral (emoções atuais,
   sensações, humor base) e valida transições
2. **Identity Authority** — consolida Personality, Relationship
   e Self-Model numa única entidade que gerencia tudo que é
   "quem é a Mia"
3. **Memory Authority** — gerencia memória, diário e aprendizado

Policy Engine e Affective Engine são internalizados como
funções dentro de State Authority no MVP. Isso reduz complexidade
de integração sem perder funcionalidade.

### 5.5 Diário como append-only log com sumarização periódica

O §11 descreve um diário subjetivo rico. Para MVP, implementar
como um **append-only log** (arquivo Markdown ou SQLite) com
sumarização periódica (uma vez por dia, o LLM gera um resumo
que alimenta a memória de longo prazo). Isso é simples,
persistente e auditável. A sumarização pode ser feita com um
modelo pequeno e barato.

### 5.6 Rejeitar embodiment e percepção no MVP

Os §14-16 (percepção, voz, avatar) são fascinantes mas
completamente fora de escopo para MVP. Não apenas porque o
hardware não existe no projeto, mas porque adicionam complexidade
de pipeline de dados em tempo real que não tem relação com o
core da visão (identidade + vida interna). Recomendação: focar
em texto + estado interno como superfície de MVP. Embodiment e
percepção são fases futuras que dependem de uma base sólida.

### 5.7 Schema versioning desde a linha zero

O banco de dados de estado (emoções, personalidade, memória,
relações) terá um schema complexo. Recomendação: adotar
**pragma user_version** no SQLite desde o início, com um
script de migração que roda automaticamente ao iniciar.
Cada mudança de schema incrementa a versão e documenta o que
mudou. Isso é simples, efetivo, e evita o caos de schema
drift.

---

## 6. Ordem de implementação sugerida

### Fase 0 — Fundação (antes de tudo)
- Definir o schema mínimo de estado (emoções, identidade,
  memória) como dataclasses Python com validação
- Implementar State Authority como módulo determinístico
  (função que recebe estado + proposta → estado atualizado
  ou erro)
- Criar sistema de migrations para SQLite
- Definir contratos de API entre componentes (interfaces
  abstratas em Python)

**Por quê**: sem isso, qualquer módulo construído depois terá
que ser refatorado. Fundação é o único item que não pode ser
adiado.

### Fase 1 — Estado interno mínimo
- Implementar representação de emoções (embedding vetorial
  simples ou distribuição probabilística)
- Implementar self-model básico (quem é a Mia, quais seus
  traços atuais, o que ela sabe de si mesma)
- Implementar transições de estado com validação (o LLM
  propõe, State Authority valida e aplica)
- Integrar com o REPL atual (mostrar estado atual, permitir
  "olhar para dentro")

**Por quê**: esta é a essência da MIA. Sem vida interna, é
apenas outro chatbot. O REPL atual já funciona — adicionar
estado interno transforma a experiência.

### Fase 2 — Memória de longo prazo
- Implementar Memory Authority com scoring de importância
- Implementar recalls contextuais (buscar memórias relevantes
  para cada interação)
- Implementar diário como append-only log
- Implementar sumarização periódica (diário → memória de
  longo prazo)

**Por quê**: sem memória, a MIA não tem continuidade. Este é
o segundo pilar da visão (identidade + memória).

### Fase 3 — Personalidade evolutiva e relacionamentos
- Implementar Personality Engine (traços que mudam com
  experiência)
- Implementar Relationship Engine (relacionamentos
  individuais com diferentes pessoas)
- Implementar Policy Engine (limites e invariantes)

**Por quê**: personalidade estática é um system prompt.
Personalidade dinâmica é o que diferencia a MIA de qualquer
outro assistente.

### Fase 4 — Autonomia e subagentes
- Implementar Resource Governor (limites de custo/tempo)
- Implementar execução de tarefas autônomas quando o
  usuário está offline
- Implementar subagentes com limites de profundidade

**Por quê**: autonomia é a característica mais avançada
e arriscada. Depende de todas as fases anteriores para
ser segura.

### Fase 5 — Percepção e embodiment (futuro)
- Percepção visual, auditiva, de contexto
- Voz e reconocimento de interlocutor
- Avatar digital

**Por quê**: depende de hardware e pipeline de dados em
tempo real. Não é viável sem uma base sólida de identidade
e estado interno.

---

> **Nota final**: O gap entre visão e implementação atual é
> uma oportunidade, não um problema. O `mia.py` é um bom ponto
> de partida — ele resolve o problema de "falar com qualquer
> LLM" de forma elegante. O próximo passo não é reconstruir
> tudo, mas **adicionar camadas de estado sobre a base existente**,
> de forma incremental e testável.
