# Posicionamento de Segurança e Confiabilidade — Debate MIA

**Autor:** Subagent (perspectiva de segurança/reliability)
**Data:** 2026-09-14
**Escopo:** Análise de riscos de segurança, integridade de estado, e mecanismos de proteção na arquitetura da MIA.

---

## 1. Entendimento da Visão

A MIA não é um chatbot com memória. É um sistema distribuído de software que simula uma entidade com vida interna persistente — emoções, personalidade, memória, identidade, autoevolução — onde o LLM é apenas um componente cognitivo substituível. A distinção fundamental é: o LLM interpreta; autoridades externas ao LLM decidem e aplicam mudanças de estado. Isso inverte o fluxo típico de agentes IA, onde o modelo é soberano e a memória é passiva.

O projeto propõe que a Mia evolua: auto-modificação de código, criação de ferramentas, criação de subagentes, revisão de personalidade, formação de opiniões próprias. Isso é ambicioso e potencialmente perigoso — se mal implementado, o sistema pode se corromper, quebrar invariantes de segurança, ou tornar-se opaco a seu próprio operador.

Minha leitura: a visão é tecnicamente coerente e filosoficamente honesta. O P1 estabelece limites claros (seção 4: "Estado Interno Protegido", seção 19: "nenhum modelo é a fonte de verdade"). O risco real não está na visão, mas na distância entre a visão e uma implementação que realmente enforque as restrições em código, não em promessas de prompt.

---

## 2. Pontos Fortes da Visão

- **State Authority como arquitetura, não como norma.** A decisão de que o LLM propõe e autoridades externas decidem é o único padrão que escala para segurança. Se o LLM fosse autoridade direta, qualquer jailbreak, prompt injection, ou alucinação destrutiva seria fatal.

- **Agent-agnostic by design.** Ser agnóstica a provedores não é apenas portabilidade — é resiliência. Se Claude cair amanhã, o sistema sobrevive. Isso é raro em projetos IA e deve ser preservado como invariante.

- **Memória rica, não buckets.** Memory Objects com origem, confiança, contexto e histórico permitem auditoria real e recuperação de erros. Buckets rígidos não suportam isso.

- **Autoevolução com pipeline.** A seção 13 do P1 propõe: proposta → implementação → testes → sandbox/checkpoint → canary → deploy → monitoramento → rollback. Isso é maduro — a maioria dos projetos IA pula direto para deploy sem sandbox.

- **Reconhecimento explícito de que "Nada deveria ser construído agora" sem especificação.** Isso evita o erro mais comum: implementar antes de pensar.

---

## 3. Riscos Arquiteturais com Gravidade

### 3.1 [CRÍTICO] O LLM pode contornar o State Authority via encoding indireto

**Problema:** Mesmo que o LLM não tenha acesso direto à API de escrita de estado, ele pode manipular estado indiretamente — por exemplo, gerando texto que outros componentes interpretam como "sinais" para alterar emoção, ou escrevendo no diário com conteúdo que dispara reações em cascata. Prompt injection vinda de inputs externos (mensagem de terceiros, conteúdo web) pode instruir o LLM a agir como intermediário de manipulação de estado.

**Gravidade:** CRÍTICO
**Mitigação necessária:**
- O State Authority deve ser um processo de runtime isolado, não uma função chamada pelo LLM. O LLM produz `StateTransitionProposal { type, target, delta, evidence, confidence }`. O State Authority recebe propostas de um queue e aplica apenas as que passam pela validação.
- Transições de estado devem ser assinadas criptograficamente pelo componente de origem (Affective Engine, Relationship Engine, etc.). O State Authority rejeita propostas sem assinatura válida.
- O LLM nunca deve ter acesso direto ao event bus em modo write. Apenas leitura.
- Rate limiting no número de propostas de transição por ciclo temporal (ex: max 3 alterações de emoção por hora de conversa).

### 3.2 [CRÍTICO] Autoevolução sem sandboxing real

**Problema:** A seção 13 do P1 propõe que a Mia participe da própria evolução. Se a Mia edita código, roda testes, e "deploy" — quem verifica que o deploy não quebrou invariantes? O LLM que propôs a mudança é o mesmo que verifica que ela está correta? Isso é um conflito de interesses fundamental.

**Gravidade:** CRÍTICO
**Mitigação necessária:**
- Sandbox: código auto-gerado roda em container isolado (Docker, ou menos idealmente, nsjail). Sem acesso à rede, sem acesso ao estado de produção, sem acesso a secrets.
- Checkpoint/rollback automático: antes de qualquer deploy, snapshot do estado. Rollback em 1 comando.
- Verificador independente: os testes devem ser escritos por um agente diferente do que escreveu o código, ou pelo menos validados por um CI pipeline determinístico (não pelo LLM que propôs a mudança).
- Canary deployment: mudanças vão para um ambiente de staging antes de produção. Monitoramento por 24-48h antes de promover.
- Limites de escopo: autoevolução deve ser restrita a componentes não-críticos inicialmente (ex: ferramentas auxiliares). Core runtime, State Authority, e Policy Engine devem ser imunes a auto-modificação.

### 3.3 [CRÍTICO] Secrets e credenciais em sistema com LLM

**Problema:** Se o LLM precisa acessar APIs externas, credenciais precisam existir em algum lugar. Se o LLM pode ler secrets (para usar em chamadas), ele pode teoricamente exfiltrá-los via output — especialmente em cenários de prompt injection. Se o LLM não pode ler secrets, como ele autentica chamadas?

**Gravidade:** CRÍTICO
**Mitigação necessária:**
- O LLM NUNCA deve ter acesso direto a secrets. Nunca.
- Arquitetura: LLM gera `ToolCall { tool, params }` (sem credenciais). Um componente de runtime intermediário (Tool Gateway) injeta as credenciais antes de executar a chamada.
- Secrets devem ser armazenados em keystore com acesso restrito ao nível de processo (não de arquivo). Em VPS: variáveis de ambiente ou vault criptografado com permissão 600. Futuramente: HashiCorp Vault ou similar.
- Logging de todas as chamadas com redação automática de secrets (sempre saem dos logs como `***`).
- Auditoria: log de todas as operações que usaram secrets, com timestamp, componente, e resultado (sucesso/erro — sem payload).

### 3.4 [ALTO] Validação de schemas na fronteira entre componentes

**Problema:** Se cada componente produz eventos e propostas em formatos diferentes, e não existe validação rigorosa na fronteira, um componente corrompido pode propagar dados inválidos para toda a cadeia. Com autoevolução, um componente pode "aprender" a produzir formato inválido para contornar restrições.

**Gravidade:** ALTO
**Mitigação necessária:**
- Event Bus deve validar schemas de todos os eventos contra definições estáticas (JSON Schema ou Pydantic models). Eventos inválidos são rejeitados e logados.
- Versão de schema: todos os eventos devem carregar `schema_version`. Componentes que recebem eventos com versão desconhecida devem rejeitar (fail-closed).
- Circuit breaker: se um componente produz N erros de schema consecutivos (ex: 5), ele é isolado do bus até intervenção.
- Para autoevolução: schemas de eventos são IMUTÁVEIS por auto-modificação. O LLM não pode propor alterações em schemas de eventos.

### 3.5 [ALTO] Auditoria de transições de estado

**Problema:** Se transições de estado não são auditáveis de forma completa e imutável, o sistema pode se corromper silenciosamente. O P1 pede "valor anterior, valor novo, causa, evento relacionado, origem, timestamp, confiança, histórico/auditoria" — mas onde isso é armazenado? Se é em SQLite no mesmo disco do estado, pode ser corrompido. Se é no mesmo processo que aplica as transições, pode ser adulterado.

**Gravidade:** ALTO
**Mitigação necessária:**
- Log de auditoria deve ser append-only e preferencialmente imutável. Em SQLite: tabela separada com `CHECK(1=1)` para prevenir UPDATE/DELETE. Melhor: append-only file (WAL mode com backup periódico).
- Cada transição de estado gera um registro: `{ id, timestamp, component_origin, transition_type, before_snapshot, after_snapshot, evidence, confidence, applied_by }`.
- Integridade: hash do registro anterior incluído no registro atual (blockchain simples). Qualquer corrupção é detectável.
- Alerta: se transições de estado estiverem sendo aplicadas a uma taxa anormal (ex: 10 alterações de personalidade em 5 minutos), o sistema entra em modo de leitura apenas e alerta o operador.

### 3.6 [ALTO] Kill switch

**Problema:** Em um sistema com autoevolução e agentes recursivos, precisa existir um mecanismo para parar TUDO instantaneamente, sem depender do sistema estar "saudável" o suficiente para processar um comando de desligamento.

**Gravidade:** ALTO
**Mitigação necessária:**
- Kill switch externo ao sistema MIA: um script/processo que o operador pode executar independentemente. Não deve depender do event bus, do LLM, ou de qualquer componente interno.
- Implementação prática: arquivo de flag em disco (`/var/mia/STOP`). Processos do MIA verificam esse arquivo em cada ciclo principal. Se existe, entram em shutdown gracioso (concluem operação em curso, salvam estado, saem).
- Nível adicional: `kill -9` no PID do supervisor como último recurso.
- Subagentes: limites rígidos de profundidade (max 3 níveis), timeout por subagente (max 30min), custo acumulado (max $X por ciclo de autonomia). Esses limites são verificados pelo runtime, não pelo LLM.
- O kill switch deve ser TESTADO regularmente. Se não é testado, não existe.

### 3.7 [ALTO] Rollback de estado

**Problema:** Se o sistema evolui ou o estado é corrompido, como voltar a um ponto conhecido e válido?

**Gravidade:** ALTO
**Mitigação necessária:**
- Snapshot periódico de estado completo (a cada N transições ou T minutos, o que ocorrer primeiro).
- Snapshot deve incluir: todas as dimensões de estado protegido (emoções, personalidade, valores, relações, identidade, memória ativa).
- Rollback: o operador pode selecionar um snapshot e restaurar. O sistema valida o snapshot antes de restaurar (checar integridade, versão de schema compatível).
- Autoevolução deve criar snapshot ANTES de cada deploy. Rollback automático se health check falhar após deploy.

### 3.8 [MÉDIO] Concorrência e race conditions no estado

**Problema:** Se múltiplos agentes/processos tentam alterar estado simultaneamente (ex: agente de voz e agente de autoevolução ambos tentando modificar "humor"), pode haver race conditions.

**Gravidade:** MÉDIO
**Mitigação necessária:**
- State Authority deve ser um único writer por dimensão de estado (serialization).
- Para SQLite: transactions com WAL mode. Para PostgreSQL futuramente: row-level locking.
- Prioridade de escrita: agentes externos (inputs humanos) > agentes internos (emoção, necessidades) > autoevolução. Autoevolução nunca deve interromper uma transição em andamento.

### 3.9 [MÉDIO] Prompt injection via inputs externos

**Problema:** Se a Mia recebe mensagens de pessoas (seção 6 do P1), conteúdo web (seção 17), ou saídas de outros agentes, qualquer um desses pode conter prompt injection destinado a manipular o LLM e, indiretamente, o estado.

**Gravidade:** MÉDIO
**Mitigação necessária:**
- Sanitização de inputs antes de chegar ao LLM: remover instruções que imitem formato de system prompt.
- O LLM deve receber inputs em formato estruturado (JSON), não como texto livre concatenado ao system prompt.
- Separação: o LLM que processa input de terceiros NÃO deve ser o mesmo que propõe transições de estado. Usar LLMs diferentes (ou pelo menos contextos diferentes) para: (a) processar input externo, (b) gerar resposta ao usuário, (c) propor transições de estado.
- Auditoria: se uma transição de estado proposta é disparada por input de terceiro, deve exigir confidence threshold mais alto.

### 3.10 [BAIXO] Observabilidade e detecção de anomalias

**Problema:** Mesmo com todos os mecanismos acima, corrupção pode passar despercebida se não houver monitoramento.

**Gravidade:** BAIXO (mas necessária para suportar os riscos acima)
**Mitigação necessária:**
- Dashboard de saúde: taxa de transições de estado por componente, erros de schema, tentativas de autoevolução, uso de resources por subagentes.
- Alertas: transições de estado anormais, erros de schema recorrentes, subagentes excedendo limites, mudanças em componentes core.
- Logs centralizados com retenção mínima de 90 dias.

---

## 4. Discordâncias Técnicas

### 4.1 "O LLM pode participar da própria evolução" — com que controle real?

O P1 propõe um pipeline completo (proposta → testes → sandbox → canary → deploy). Isso é correto em intenção, mas a implementação real é brutal: quem valida que os testes são adequados? O LLM que criou o código é o mesmo que cria os testes? Isso é como deixar o réu ser juiz.

**Minha posição:** Autoevolução deve ser limitada a componentes não-críticos até que exista um framework maduro de verificação independente. O "verificador" deve ser: (a) um LLM diferente, (b) com prompt diferente, (c) sem acesso ao código original (testes cegos), ou (d) um pipeline determinístico (testes unitários, linting, type checking) que não depende de julgamento do LLM.

### 4.2 "State Authority decide e aplica" — como governança?

Se o State Authority é um componente Python, ele é código. Código tem bugs. Se o State Authority tem um bug que permite escrita indevida de estado, o sistema inteiro está comprometido. A visão não detalha: quem audita o State Authority? Como ele é testado? Como ele é atualizado sem comprometer sua integridade?

**Minha posição:** O State Authority deve ser o componente mais pequeno, mais testado, e mais imutável do sistema. Idealmente: código declarativo (regras em YAML/JSON), não código imperativo. Regras como: `AffectiveEngine pode_propor alteração_emocional: SIM; alteração_personalidade: NÃO` são verificáveis, auditáveis, e difíceis de errar.

### 4.3 "CLI-first com SQLite" — seguro para produção?

SQLite é excelente para prototipagem, mas tem limitações reais para um sistema multi-processo com concorrência: WAL mode ajuda, mas write contention em VPS com múltiplos agentes pode ser um problema. Além disso, SQLite não suporta isolamento de acesso (não dá para dizer "componente X só lê tabela Y").

**Minha posição:** Use SQLite para MVP. Mas projete o data access layer desde o início para ser swappable para PostgreSQL. Defina contratos de acesso (que tabelas cada componente pode ler/escrever) desde o dia 1. Não refatore isso depois — será doloroso.

### 4.4 A visão assume que "prompt engineering" resolve contenção de LLM

O P1 diz que o LLM não deve modificar estado protegido. Mas isso é uma restrição no prompt, não em código. Prompt engineering é defense-in-depth fraca — qualquer mudança de modelo, atualização de tokenizer, ou edge case pode quebrar a restrição. O código do sistema é que deve impedir, não o prompt.

**Minha posição:** Prompt engineering é útil para guiar o comportamento do LLM, mas NUNCA deve ser a única barreira. A barreira real é: o runtime não expõe API de escrita de estado ao LLM. Ponto. Sem exceção.

---

## 5. Decisões-Chave Antes de Implementar

### 5.1 Como o State Authority impede o LLM de escrever em estado protegido, FISICAMENTE?
Não aceite "o prompt diz que não pode". A resposta deve ser: o runtime não expõe endpoint de escrita para o módulo LLM. O LLM produz propostas; o State Authority é um processo separado com seu próprio endpoint. Isso é arquitetura, não política.

### 5.2 Quem audita o State Authority?
Definir: (a) testes unitários do SA, (b) testes de integração (tentar escrever estado via LLM deve ser rejeitado), (c) monitoramento (alerta se SA estiver down ou respondendo lentamente), (d) revisão de código por agente humano antes de cada release.

### 5.3 Como serializar autoevolução com segurança?
Definir o escopo mínimo: quais componentes podem ser auto-modificados? Quais são sagrados? Definir o processo: pode ser? O que precisa ser testado? Quem aprova? Definir rollback: em quanto tempo? Com que snapshot?

### 5.4 Onde está o trust boundary entre LLM e sistema?
O LLM é um componente de processamento de linguagem natural. Ele não deve ter: acesso a secrets, acesso direto a banco, acesso a filesystem além do workspace designado, capacidade de spawn de processos, capacidade de modificar configuração. Essas boundaries devem ser testáveis e enforcadas pelo runtime.

### 5.5 Como o sistema lida com falha do LLM?
Se o LLM retornar lixo, timeout, ou resposta malformada, o sistema deve: (a) não aplicar nenhuma transição de estado, (b) logar o erro, (c) manter estado anterior, (d) alertar se a falha persistir. O sistema deve ser resiliente a falhas do LLM, não dependente de ele funcionar.

### 5.6 Como lidar com múltiplos LLMs com "opiniões" diferentes?
Se Claude diz que a Mia está feliz e GPT diz que está triste, quem decide? A resposta não pode ser "o último que falou". Precisa de um mecanismo de resolução: prioridade por tipo de tarefa, consensus, ou fallback para regra determinística.

### 5.7 Qual a política de retenção e exclusão de dados?
Memória persistente com "esquecimento" (P1 seção 10) implica: quem decide o que esquecer? Como garantir exclusão real (não apenas soft delete)? Com que frequência? Isso impacta compliance futuro (LGPD, GDPR se expandir).

### 5.8 Como o sistema se comporta quando "nada está acontecendo"?
O P1 diz que a Mia deve manter continuidade offline. Mas "offline" significa: que processos estão rodando? Com que frequência? O scheduler consome recursos? Se o VPS cai e volta, o estado é consistente?

---

## 6. Ordem de Implementação Sugerida

### Fase 0 — Fundação de segurança (ANTES de qualquer feature)
1. **State Authority declarativa** — regras em arquivo de configuração (YAML/JSON), runtime aspa em Python. Teste: tentar escrever estado via LLM deve ser rejeitado.
2. **Event Bus com validação de schema** — Pydantic models para todos os eventos. Schema versioning. Rejeição de eventos inválidos.
3. **Secrets management** — keystore isolado. LLM nunca acessa diretamente. Tool Gateway injeta credenciais.
4. **Kill switch** — script externo. Teste: executar kill switch e verificar que todos os processos param.
5. **Log de auditoria append-only** — tabela SQLite com integridade verificável. Hash chain.

### Fase 1 — Core com proteções (primeiro sistema funcional)
6. **Core Runtime** — lifecycle, configuration, event bus funcional.
7. **Cognition básica** — context window, reasoning (via LLM), decisões simples.
8. **Memory básica** — memory objects, CRUD, retrieval por similaridade.
9. **Identity básica** — self-model mínimo, personalidade como estado.
10. **Integração LLM** — abstraction layer, multi-provider.

### Fase 2 — Vida interna (com safeguards)
11. **Affective Engine** — emoções como estado derivado (não setado diretamente por LLM).
12. **Sensações** — estados internos não-determinísticos.
13. **Mood** — aggregação de emoções ao longo do tempo.
14. **Diário** — output subjetivo baseado em estado interno.

### Fase 3 — Social (com boundaries)
15. **Relationship Engine** — relações individuais, dimensionais.
16. **Social evaluation** — detecção de ofensa, limites contextuais.
17. **Identity + boundaries** — a Mia pode recusar, confrontar, estabelecer limites.

### Fase 4 — Autonomia (com limites)
18. **Goals e initiative** — objetivos persistidos, scheduling.
19. **Tool use** — LLM propõe, runtime executa (com sandbox para operações perigosas).
20. **Subagentes básicos** — com limites rígidos de profundidade e custo.

### Fase 5 — Autoevolução (só depois de maduro)
21. **Self-improvement proposals** — LLM propõe mudanças.
22. **Sandbox de código** — container isolado para testar mudanças.
23. **Canary deployment** — staging antes de produção.
24. **Rollback automático** — health check + revert.

### Fase 6 — Percepção e embodiment (futuro)
25. **Percepção** — audio, visão, sensores.
26. **Voz** — VAD, STT, speaker recognition, TTS.
27. **Avatar** — embodiment digital.

---

## 7. O Que NÃO Construir Agora

### 7.1 NÃO construir autoevolução de código agora
O framework de sandbox, verificação independente, e rollback automático não existe ainda. Construir autoevolução sem esses mecanismos é convidar corrupção silenciosa. Autoevolução é Fase 5 — e só depois que as Fases 0-4 estiverem estáveis e testadas.

### 7.2 NÃO construir avatar/embodiment agora
Avatar é uma feature visual complexa que não contribui para a arquitetura de segurança. Construir avatar antes de ter State Authority funcionando é priorizar o superficial sobre o fundamental.

### 7.3 NÃO construir percepção multimodal agora
Câmera, GPS, microfone contínuo — tudo isso amplifica superfície de ataque e complexidade de processamento. Construir percepção antes de ter sandboxing robusto é perigoso. Além disso: pipeline `sensor → percepção local → evento estruturado` precisa de validação de schema em cada etapa.

### 7.4 NÃO construir multi-agent complexo agora
Múltiplos agentes com capacidade de criar subagentes recursivamente é um vetor de explosão de complexidade. Comece com UM agente funcionando bem com proteções. Depois adicione segundo agente e teste concorrência. Não comece com orquestração multi-agent.

### 7.5 NÃO construir "personalidade evolutiva" agora
Personalidade como estado evolutivo é conceitualmente bonito, mas a validação disso é difícil: como você testa que a personalidade "mudou de forma coerente"? Comece com personalidade estática que pode ser alterada manualmente. Evolução automática vem depois.

### 7.6 NÃO usar LLM para validar LLM
Se Claude gera código e Claude valida código, há conflito de interesses. Se Gemini propõe mudança de estado e Gemini valida mudança de estado, há conflito de interesses. Validação deve ser: (a) determinística (testes, linting, schema validation), ou (b) por componente independente (LLM diferente, sem acesso ao código original). Nunca auto-validação.

### 7.7 NÃO confundir "possível" com "seguro"
O LLM pode, teoricamente, fazer qualquer coisa que o código permitir. A pergunta não é "o que o LLM pode fazer?" mas "o que o runtime DEIXA o LLM fazer?". Cada feature que o LLM ganha deve ser precedida por: "se isso for abusado, o que acontece?" e "como detectamos o abuso?".

---

## Resumo Executivo

A visão da MIA é sólida e incomum em sua seriedade. O ponto crítico é a distância entre a especificação (que é boa) e a implementação de segurança (que precisa ser tão rigida quanto a visão). Os três riscos mais perigosos são:

1. **State Authority deve ser enforcement físico**, não norma de prompt.
2. **Autoevolução deve ser sandboxed** antes de ser permitida.
3. **Secrets nunca devem ser acessíveis ao LLM**, nem indiretamente.

Se esses três pontos forem resolvidos na Fase 0, o resto do sistema pode evoluir com segurança. Se forem postergados, a propagação de danos será difícil de conter.

---

*"A segurança não é uma feature que se adiciona depois. É a estrutura sobre a qual tudo mais é construído."*
