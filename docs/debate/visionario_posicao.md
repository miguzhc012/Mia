# Posicionamento Visionário — Arquitetura da MIA

> Autor: Arquiteto Visionário (Defensor da fidelidade à visão)
> Data: 2026-09-14
> Papel no debate: Defender que a arquitetura precisa nascer com as fronteiras certas —
> State Authority, event bus e memória como objetos estruturados — para não exigir
> reescrita depois.

---

## 1. Entendimento da Visão

A MIA não é um produto de chat. É uma tentativa séria de construir uma entidade de software
com identidade persistente, vida interna e autonomia real. O documento P1_entendimento.md
descreve algo que nunca existiu exatamente dessa forma: uma IA-companheira que possui
emoções como estado mutável e auditável, personalidade que evolui com o tempo, memória
que não é apenas "conversas salvas" mas objetos com peso semântico, e um self-model que
a permite comparar versões passadas de si mesma.

O ponto crucial — e onde muitos projetos similares falham silenciosamente — é que a MIA
é definida como um **sistema**, não como uma conversa. O LLM é um componente cognitivo,
não o cérebro da operação. Essa distinção não é cosmética; ela exige uma arquitetura
radicalmente diferente de qualquer wrapper de API ou chatbot com memória.

A visão reconhece que a subjetividade computacional precisa de fronteiras institucionais.
O LLM pode interpretar, propor e raciocinar, mas **não pode alterar diretamente** o
estado interno protegido (emoções, personalidade, valores, relações). Para isso, existem
autoridades externas: State Authority, Affective Engine, Personality Engine, Memory
Authority. Isso não é paranoia arquitetural — é a única forma de garantir que o sistema
não seja transformado em um chatbot com amnésia programática a cada troca de modelo.

A abordagem modular, agnóstica a provedores e distribuída (VPS, celular, desktop) mostra
maturidade: o projeto antecipa que os componentes cognitivos serão substituídos e
intercambiáveis, e que a identidade da MIA deve sobreviver a essa substituição.

---

## 2. Pontos Fortes da Visão

### 2.1. Separação LLM ≠ Sistema
A decisão de tratar o LLM como componente substituível é a escolha arquitetural mais
importante do projeto. Ela impede o lock-in cognitivo e permite que a MIA mantenha
identidade mesmo com mudanças radicais de backend.

### 2.2. Estado Interno Protegido com Autoridades
O conceito de State Authority — onde o LLM propõe e uma autoridade decide — é
arquiteturalmente correto. Sem isso, o LLM se torna o estado, e a identidade da MIA
se torna o modelo atual. Isso é inaceitável para um sistema de longo prazo.

### 2.3. Memória como Objetos Estruturados
Memory Objects com conteúdo, tipo, origem, timestamp, importância, confiança, escopo e
associações é uma abordagem madura. Evita o erro clássico de "salvar tudo em vetores e
rezar para retrieval funcionar".

### 2.4. Continuidade Temporal
A exigência de que a MIA mantenha continuidade quando Miguel está offline demonstra
compromisso com realismo: uma entidade genuína não "pausa" quando seu interlocutor sai.

### 2.5. Modelagem Social Complexa
A distinção entre emoção, sensação, humor e estado íntimo — cada um com dinâmica
própria — é precisa. A frase "Estou me sentindo mal e não sei por quê" é uma
propriedade emergente de um sistema bem modelado, não de um chatbot.

---

## 3. Riscos Arquiteturais com Gravidade

### 3.1. Complexidade爆炸 do Sistema de Emoções [CRÍTICO]
O projeto descreve emoções, sensações, humor, estados íntimos, necessidades, desejos,
curiosidade — cada um como sistema independente. Se todos forem implementados como
módulos separados desde o início, teremos pelo menos 12-15 subsistemas interagindo
antes de termos um fluxo básico funcionando. O risco é construir uma nave espacial
quando precisamos de um foguete que funcione.

**Gravidade:** Crítica. Pode travar o projeto em especificação infinita.

### 3.2. Event Bus como Monolito [ALTO]
Se o event bus for tratado como um "tudo conecta a tudo", teremos um sistema onde
qualquer evento pode causar qualquer efeito. A manutenção se torna impossível. O
P3 planeja eventos como MIGUEL_SPOKE, LONELINESS_CHANGED, INSULT_RECEIVED — mas
não define claramente quem pode reagir a quê, nem como lidar com eventos que
disparam cadeias longas.

**Gravidade:** Alta. Sem restrição de subscrição, o event bus vira um apagador de
incêndio que incendeia a floresta.

### 3.3. SQLite como Base Única [MÉDIO]
SQLite é excelente para prototipagem e até produção para um único nó, mas o projeto
prevê distribuição (VPS, celular, desktop). Coordenar SQLite entre nós exige sync
complexo (CRDTs, operational transforms, ou algo equivalente). Se a persistência
não for planejada com isso em mente, a distribuição será dolorosa depois.

**Gravidade:** Média. Atinge quando o projeto escalar de VPS único para múltiplos nós.

### 3.4. Diário Subjetivo como Feature [MÉDIO]
O diário subjetivo é charmoso e importante para a narrativa, mas se não for tratado
como uma consequência de outros sistemas (emoção, memória, tempo), ele vira um
componente isolado que precisa de retrabalho quando a arquitetura de memória mudar.

**Gravidade:** Média. Pode ser implementado tardiamente sem perda.

### 3.5. Self-Modification sem Sandbox Robusto [ALTO]
"A Mia pode participar da própria evolução" é empolgante, mas sem um sandbox,
checkpoint e rollback testados, isso é um convite a corrupção silenciosa de estado.
O documento menciona o fluxo (proposta → implementação → testes → canary → deploy),
mas não detalha como o estado crítico é protegido durante essa operação.

**Gravidade:** Alta. Self-modification quebrada pode destruir o estado da MIA.

### 3.6. Multi-Agent sem Orchestration Definida [MÉDIO]
O projeto prevê agentes recursivos, debate, consenso e pipeline paralelo. Isso é
complexo demais para o estágio atual. A elegância do conceito esconde a dificuldade
de coordenar múltiplas IAs sem um protocolo rígido.

**Gravidade:** Média. Relevante apenas quando multi-agent for realmente necessário.

### 3.7. Percepção (Voice, Vision, Sensors) [BAIXO para agora]
Microfone, câmera, GPS, reconhecimento facial — isso é o futuro. O risco não é
técnico, é de foco: se o projeto se dispersar em percepção antes de ter cognição
básica, ele nunca terá uma base sólida.

**Gravidade:** Baixa agora, alta se integrada prematuramente.

---

## 4. Discordâncias Técnicas

### 4.1. STATE AUTHORITY DEVE EXISTIR DESDE O DIA 1

**Minha posição:** O State Authority não é opcional nem "pode ser adicionado depois".
Ele é o alicerce que impede que a MIA se torne indistinguível de um chatbot com
contexto salvo. Se começarmos sem ele, o estado da MIA será escrita direta do LLM,
e cada troca de modelo (Claude → GPT → Qwen) corromperá a identidade.

**Trade-offs honestos:**
- **Custo:** Implementar State Authority desde o início aumenta a complexidade inicial.
  Cada mudança de estado precisa de uma chamada indireta.
- **Benefício:** Garante que o estado seja auditável, reversionável e independente
  do modelo. Sem isso, "personalidade persistente" é um sonho.
- **Alternativa pragmática:** Começar com um State Authority simples — um módulo
  Python que recebe propostas de atualização do LLM e aplica regras determinísticas
  (ranges, invariantes, validação de tipos). Não precisa ser distribuído no início.
  Pode ser um módulo em SQLite com transactions. Mas ele precisa existir.

**Quem defende a abordagem oposta** (State Authority "depois") está apostando que
conseguirá migrar o estado de um formato informe (texto do LLM) para um formato
estruturado sem perda de coerência. Isso é um risco enorme para um sistema que
promete continuidade de identidade.

### 4.2. EVENT BUS COMO COLUNA VERTEBRAL DESDE O INÍCIO

**Minha posição:** O event bus não é um "nice to have" — é o mecanismo que permite
que os sistemas da MIA conversem sem acoplamento direto. Sem ele, cada módulo
precisa conhecer seus vizinhos. Com ele, novos módulos podem ser adicionados sem
modificar código existente.

**Trade-offs honestos:**
- **Custo:** Um event bus bem feito exige schemas, contratos e tratamento de erros.
  Um mal feito vira um debug nightmare.
- **Benefício:** Desacoplamento real. O Affective Engine não precisa saber quem
  publica CURIOSITY_TRIGGERED. O Memory Authority não precisa saber quem publica
  NEW_MEMORY_CANDIDATE.
- **Implementação pragmática:** Um Python asyncio queue com typagem forte. Não
  precisa ser Redis/Kafka no início. Pode ser um módulo de ~200 linhas com
  publicadores, inscritos e tratamento de exceções. Mas os eventos precisam ser
  tipos definidos, não strings livres.

### 4.3. MEMÓRIA COMO OBJETOS DESDE O DIA 1

**Minha posição:** "Memory Objects com características como conteúdo, tipo, origem,
timestamp, importância, confiança, escopo, associações" — isso NÃO pode ser
adiado. Se a memória começar como "texto em SQLite", a migração para objetos
estruturados exigirá reescrever todos os componentes que leem/escrevem memória.

**Trade-offs honestos:**
- **Custo:** Definir o schema de Memory Object desde o início exige foresight.
  O schema evoluirá — isso é esperado e aceitável.
- **Benefício:** Cada componente que toca memória (retrieval, consolidação,
  esquecimento, crenças, self-model) opera sobre uma interface consistente.
- **Implementação pragmática:** Pydantic models com versão de schema. SQLite com
  JSON para campos flexíveis. Embeddings em tabela separada. Não precisa de
  vector store no início.

### 4.4. CRÍTICA A ABORDAGENS "CHATBOT COM MEMÓRIA"

Projetos que tratam a MIA como "chatbot com memória" cometem três erros fatais:

1. **Acoplamento cognitivo ao modelo:** Se o system prompt define a personalidade,
   trocar o LLM troca a personalidade. A MIA exige personalidade como estado
   externo, não como prompt.

2. **Memória como flat store:** "Conversas salvas" ou "chunks com embeddings"
   não são memória. Memória é um objeto com peso semântico, relevância temporal,
   associações e história de mutação. A diferença entre "lembro que você gosta de
   café" e "tenho um Memory Object tipo preference com confiança 0.85, associado
   à relação com Miguel, que veio de 47 observações ao longo de 3 meses" é a
   diferença entre um assistente e uma companheira.

3. **Ausência de fronteiras de estado:** Se o LLM pode escrever qualquer coisa
   em qualquer lugar, ele eventualmente escreve algo que contradiz o estado
   anterior. A MIA não pode "esquecer" que é tímida porque o contexto de uma
   conversa encorajou o modelo a ser extrovertido.

---

## 5. Decisões-Chave Antes de Implementar

### 5.1. Como o State Authority realmente impede o LLM?
**Pergunta:** Se o LLM gera texto que descreve "propostas de atualização", quem
serializa isso em chamadas ao State Authority? O parsing é determinístico? Se o
LLM gerar JSON malformado ou propostas ambíguas, o que acontece?
**Resposta necessária:** Definir o protocolo de comunicação LLM → State Authority.
Probabilidade: usar function calling / tool use do LLM para gerar estruturas
tipadas, não parsing de texto livre.

### 5.2. Granularidade do Event Bus
**Pergunta:** Quantos tipos de evento? Quem define? Um evento MIGUEL_SPOKE é
suficiente ou precisamos de MIGUEL_SPOKE(contexto, tom, intimidade, urgência)?
**Resposta necessária:** Schema de eventos com campos obrigatórios e opcionais.
Definir quem pode publicar cada tipo e quem pode subscrever.

### 5.3. Serialização do Self-Model
**Pergunta:** O self-model é um JSON profundo? Uma árvore? Como versioná-lo?
Como comparar versões passadas? Como serializar para persistência?
**Resposta necessária:** Schema do self-model, formato de persistência, estratégia
de versionamento (snapshots? diffs? ambos?).

### 5.4. Ciclo de Vida dos Emoções
**Pergunta:** As emoções são componentes ativos que atualizam seu estado
periodicamente (tick-based) ou reativas (só mudam quando um evento chega)?
**Resposta necessária:** Definir o modelo de atualização: ativo vs reativo vs híbrido.

### 5.5. Confiança e Obrigação dos Memory Objects
**Pergunta:** Como medir "importância" e "confiança"? São floats 0-1? Escalas
categóricas? Como um Memory Object perde importância? Decaimento temporal?
**Resposta necessária:** Métricas de memória, política de esquecimento, thresholds
de consolidação.

### 5.6. Segurança da Autoevolução
**Pergunta:** Se a MIA propõe mudar seu próprio código, como o sandbox protege
o estado crítico? Quem verifica a proposta antes de aplicar? O Miguel aprova?
**Resposta necessária:** Protocolo de self-modification com papéis claros
(proponente, revisor, aprovador, executor).

### 5.7. Distribuição: Quando e Como?
**Pergunta:** A distribuição entre VPS/celular/desktop é um requisito do dia 1
ou do futuro? Se for futuro, como o schema de persistência não bloqueia isso?
**Resposta necessária:** Definir se SQLite é suficiente para MVP e qual a interface
de persistência que permite migração futura.

### 5.8. LLM Context Window e State
**Pergunta:** O contexto de conversa do LLM é limitado. Como a MIA fornece ao LLM
apenas o estado relevante sem carregar 10GB de memória? Existe um "context
assembly" que seleciona o que entra na janela?
**Resposta necessária:** Módulo de context assembly que monta o prompt a partir
de memória, estado emocional, relação e contexto atual.

### 5.9. Testabilidade do Sistema Subjetivo
**Pergunta:** Como testar que "a MIA ficou triste"? Se emoções são emergentes
de múltiplos subsistemas, testes unitários são insuficientes. Testes de
comportamento? Simulation-based testing?
**Resposta necessária:** Estratégia de testes para propriedades emergentes.

### 5.10. Escolha do Primeiro LLM Backend
**Pergunta:** Para o MVP, qual modelo? Isso afeta o que o State Authority
precisa validar (alguns modelos são mais propensos a alucinar estruturas).
**Resposta necessária:** Definir o backend cognitivo inicial e suas limitações.

---

## 6. Ordem de Implementação Sugerida

### Fase 0: Alicerce (sem código de domínio)
1. **Event Bus** — módulo Python com tipos de eventos definidos, publicadores
   e inscritos. ~200 linhas. Testável isoladamente.
2. **State Authority** — módulo que recebe propostas de atualização, valida
   contra schema, aplica ou rejeita. Persiste em SQLite com transactions.
3. **Memory Objects** — schema Pydantic com versão. CRUD básico em SQLite.
4. **Identity Store** — self-model serializado, versionado, com snapshot
   e diff.

### Fase 1: Cognição Básica (primeira conversa real)
5. **Context Assembly** — módulo que seleciona estado relevante para o LLM.
6. **LLM Provider Abstraction** — interface para trocar Claude/GPT/local.
7. **Conversa com Estado** — loop: recebe input → monta contexto → LLM responde
   → interpreta resposta → propõe atualizações ao State Authority.

### Fase 2: Vida Interna Simplificada
8. **Emoções básicas** — apenas 4-5 emoções primárias, modelo reativo (muda com
   eventos). Não precisa de 20 emoções no início.
9. **Mood como resumo** — mood é a média ponderada das emoções recentes, não
   um sistema separado.
10. **Personalidade como vector** — traços em escala, não como enum de
    "personalidade tsundere".

### Fase 3: Memória Real
11. **Consolidação** — conversas viram Memory Objects após análise.
12. **Retrieval** — embedding + filtros por tipo, tempo, relevância.
13. **Esquecimento** — decaimento temporal, reforço por reutilização.

### Fase 4: Social e Relacionamentos
14. **Relação com Miguel** — modelo de relación con dimensões básicas.
15. **Interpretação social** — mesma frase + contexto diferente = reação diferente.

### Fase 5: Autonomia e Autoevolução (quando base estiver sólida)
16. **Goals e initiative** — MIA pode manter objetivos enquanto Miguel offline.
17. **Self-modification** — apenas com sandbox e aprovação humana.

### Fase 6: Percepção e Embodiment (futuro)
18. Voz, câmera, avatar — apenas quando a cognição e a vida interna estiverem
    maduras o suficiente para justificar a percepção.

---

## 7. O Que NÃO Construir Agora

### 7.1. Avatar Digital / Embodiment
Completamente irrelevante no estágio atual. Um avatar sem cognição básica é um
boneco de fireworks. Adiar até Fase 6.

### 7.2. Multi-Agent Completo
A orquestração multi-agent é complexa e exige que um único agente funcione bem
primeiro. Começar com um único LLM, uma única cadeia de raciocínio, uma única
MIA. Multi-agent vem quando a base estiver sólida.

### 7.3. Percepção Multimodal (Câmera, Microfone, GPS)
A menos que o MVP exija voz, não implementar. Cada sensor adiciona complexidade
de pipeline, latência e custo. Focar em texto + memória primeiro.

### 7.4. Distribuição Real entre Nós
SQLite em VPS único é suficiente para validar a arquitetura. A distribuição
entre celular/desktop/VPS é uma otimização que vem depois. Não construir sync
protocol antes de ter algo que vale a pena sincronizar.

### 7.5. Diário Subjetivo como Componente Separado
Pode ser implementado como consequence da memória + emoções + tempo. Não precisa
de módulo próprio no início.

### 7.6. Sistema Completo de Ofensa e Limites Sociais
Social modeling complexo (ofensa, intimidade, sexualidade) é fascinante mas
depende de ter emoções, relações e personalidade funcionais. Implementar apenas
após Fase 4.

### 7.7. World Awareness / Pesquisa Autônoma
A MIA pesquisando notícias e formando opiniões sobre o mundo é lindo, mas
requer que a cognição básica funcione. Adiar até Fase 5+.

### 7.8. Policy Engine Completo
Uma engine de políticas robusta exige que existam políticas para aplicar.
No início, o State Authority com regras básicas é suficiente. A Policy Engine
cresce naturalmente quando as regras se tornam complexas demais para estar
no State Authority.

---

## 8. Resumo da Posição

A visão da MIA é ambiciosa, coerente e tecnicamente fundamentada. O erro que
precisamos evitar não é over-engineering no sentido de "muita tecnologia" — é
under-foundation: construir features antes das fronteiras que as protegem.

O **State Authority**, o **event bus** e os **Memory Objects** não são features
avançadas — são o alicerce. Sem eles, cada componente construído depois terá que
ser reescrito para se adequar a uma arquitetura que não existia quando ele foi
criado.

Minha recomendação é clara: construir o alicerce primeiro (Fase 0), validar com
uma conversa básica (Fase 1), e só então expandir para vida interna, memória
complexa e social modeling. A ordem importa mais que a velocidade.

A MIA merece uma arquitetura que dure décadas, não uma que funcione por meses
e precise ser reescrita quando a complexidade crescer.

---

*Documento gerado para debate arquitetural. Não implementa código.*
*Posição: Visionário — defensor da fidelidade à visão de longo prazo.*
