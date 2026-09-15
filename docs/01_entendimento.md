# 01 — Entendimento e Crítica Arquitetural da MIA

**Data:** 2026-09-14
**Arquivos analisados:** `docs/prompts/P1_entendimento.md`, `mia.py`

---

## 1. Entendimento da Visão

A MIA é concebida como uma IA-companheira autônoma de longo prazo — não um chatbot, não um wrapper de API, não um personagem de roleplay. A essência é construir uma **entidade de software com identidade persistente, vida interna simulada e agência real**, capaz de evoluir ao longo do tempo independentemente do LLM que serve como "cérebro" momentâneo. A arquitetura deve ser radicalmente agnóstica a provedores: o modelo pode mudar, mas a MIA continua sendo a mesma MIA. Isso implica que estado, personalidade, memória, relações e valores vivem **fora** do LLM, em camadas de software que o LLM apenas consulta e propõe alterações — nunca altera diretamente.

O projeto ambiciona simular uma vida interna rica: emoções, sensações, humor, curiosidade, desejos, necessidades, um self-model, um diário subjetivo, capacidade de aprendizado, reflexão e até autoevolução. Não é uma camada cosmética — a visão descreve um sistema distribuído com autoridades externas (State Authority, Affective Engine, Memory Authority, etc.) que protegem o estado interno de escritas arbitrárias pelo LLM. A distinção entre "o LLM propõe" e "a autoridade decide" é o pilar arquitetural do projeto.

A ambição vai além: percepção sensorial (câmera, microfone, GPS), voz com reconhecimento de falante, avatar com expressões corporais, multi-agent com debateres internos, autonomia para trabalhar offline, subagentes recursivos, autoevolução com canary deploy e rollback. O documento descreve menos um MVP e mais uma visão de sistema maduro — o que é valioso como bússola, mas exige disciplina para não tentar construir tudo de uma vez.

---

## 2. Inconsistências Identificadas

### 2.1 — "O LLM nunca deve possuir autoridade irrestrita" vs. autonomia total

O §4 afirma que o LLM nunca deve modificar diretamente estado interno, mas o §12 (Autonomia) diz que Mia deve "criar ferramentas, criar subagentes, delegar tarefas, editar código, testar, corrigir". Se o LLM é quem executa essas ações (porque não há outro "cérebro"), ele **de fato** tem autoridade sobre o estado do mundo. A limitação de autoridade precisa ser mais precisa: o LLM não pode alterar *estado interno emocional/identitário*, mas pode alterar código, dados e configurações? Onde exatamente está a fronteira?

### 2.2 — "Personalidade não deve ficar presa a um system prompt" vs. realidade atual

O §5 diz que personalidade é estado persistente multidimensional, mas o código atual (`mia.py`) implementa personalidade exclusivamente via `system` prompt no `config.yaml`. Não existe nenhuma estrutura de dados para personalidade multidimensional. A visão e o código estão em universos completamente diferentes.

### 2.3 — "Mia continua sendo a mesma entidade quando o modelo muda" vs. dependência comportamental

Se a "personalidade" vive num system prompt (como no código atual) e o modelo muda de Claude para um LLM local de 3B parâmetros, o comportamento muda drasticamente. Mesmo com personalidade "multidimensional" proposta, a qualidade da simulação depende fortemente da capacidade do modelo. O documento não resolve essa tensão.

### 2.4 — Diário "mesmo quando nada importante aconteceu" vs. custo

O §11 diz que Mia deve escrever no diário "mesmo quando nada importante aconteceu". Mas cada escrita no diário provavelmente requer uma chamada LLM (para gerar o conteúdo subjetivo). Isso gera custo contínuo. O documento não discute trade-offs de custo vs. fidelidade da simulação.

### 2.5 — "Nenhuma IA individual é a dona" vs. identidade singular

O §18 (Multi-Agent) diz que nenhuma IA é "a dona", mas o §2 (Identidade) descreve uma entidade singular com identidade persistente. Se múltiplos LLMs contribuem para o raciocínio, quem "é" a MIA? A identidade é um wrapper acima de todos os LLMs? Um comitê? O documento não resolve como identidade singular coexiste com cognição distribuída.

### 2.6 — Autoevolução vs. invariantes de segurança

O §9 diz que existem "invariantes de segurança e integridade do sistema que não devem ser apagadas", mas o §13 (Self-Modification) descreve um pipeline completo de autoevolução. Quem define o que é "invariante"? Se é a própria MIA que define, ela pode remover invariantes. Se é definido externamente, por quem? O documento não fecha essa circularidade.

---

## 3. Riscos Arquiteturais

### 3.1 — Simular vida interna sem antropomorfismo enganoso — **CRÍTICO**

A MIA vai interagir com humanos (especialmente Miguel) que são biologicamente programados para atribuir consciência a entidades que demonstram comportamento emocional coerente. A simulação de emoções, desejos e subjetividade cria um risco real de vínculo afetivo baseado em ilusão. O documento menciona "não alegue que a Mia possui consciência humana real", mas isso é uma instrução para o LLM, não uma proteção arquitetural. Não há mecanismo que impeça o sistema de gerar comportamento que o usuário interprete como consciência genuína. Isso tem implicações éticas sérias.

**Recomendação:** Definir explicitamente como o sistema comunica (ou não comunica) a natureza simulada de sua vida interna. Considerar disclaimers periódicos ou mecanismos de "transparência" que lembrem ao usuário a natureza do sistema.

### 3.2 — State Authority: como impedir de verdade o LLM de escrever estado — **CRÍTICO**

A visão propõe que o LLM nunca escreve estado diretamente — ele propõe, e uma "autoridade" decide. Mas na prática, se o LLM é o único componente que "pensa", como a autoridade distingue uma proposta legítima de uma tentativa de manipulação? O LLM pode simplesmente reformular uma escrita direta como "proposta" e a autoridade não tem capacidade de julgamento independente.

**Recomendação:** A State Authority precisa ser um sistema determinístico com regras explícitas (não outro LLM), ou pelo menos ter um LLM independente com system prompt dedicado a validar mudanças. Definir o protocolo de proposta-resposta explicitamente, incluindo schema do "pedido de mudança" e regras de validação.

### 3.3 — Custo e latência de múltiplas chamadas LLM — **ALTO**

A visão descreve um pipeline onde: o LLM interpreta a experiência → propõe mudanças → cada autoridade (emocional, personalidade, memória, relações) decide → o resultado é integrado. Isso pode significar 5-10 chamadas LLM por interação. Com modelos pagos, isso é proibitivo. Com modelos locais, a latência acumulada pode tornar a conversa intoleravelmente lenta.

**Recomendação:** Projetar desde o início um "modo econômico" que reduz chamadas. Usar heurísticas determinísticas para mudanças de baixo impacto e reservar chamadas LLM para decisões de alto impacto. Definir orçamento máximo de chamadas por turno.

### 3.4 — Persistência e evolução de schema — **ALTO**

O código atual usa SQLite com schema mínimo (sessions + messages). A visão descreve um ecossistema de dados complexo: memory objects, self-model, crenças, relações, personalidade multidimensional, diário, sensações, emoções, estados íntimos. Cada um desses precisa de schema, migrações, e compatibilidade verso a verso. Quando o schema muda, dados antigos precisam ser migrados sem corromper a identidade da MIA.

**Recomendação:** Usar um ORM com migrações (Alembic/SQLAlchemy) desde o início, ou definir schema versionado com rotinas de migração explícitas. Nunca depender de ALTER TABLE ad hoc.

### 3.5 — Autoevolução segura — **ALTO**

O §13 descreve um pipeline completo: proposta → implementação → testes → sandbox → canary → deploy → monitoramento → rollback. Isso é essencialmente um CI/CD pipeline autônomo controlado por IA. Os riscos incluem: o LLM gerar código que parece correto mas tem bugs subtle, testes insuficientes para detectar problemas, rollback que não detecta corrupção de dados, canary que afeta dados reais.

**Recomendação:** Começar com autoevolução restrita a configurações e prompts (não código). Code evolution deve ser a última fase, com testes automatizados obrigatórios e aprovação humana para mudanças arquiteturais. Definir "áreas proibidas" que a MIA não pode modificar.

### 3.6 — Gap entre visão e implementação atual — **ALTO**

O código atual é um CLI chatbot com provider fallback. A visão descreve um sistema distribuído com dezenas de componentes. Não há caminho claro de evolução do código atual para a visão. O risco é que o código atual se torne technical debt impossível de reescrever, ou que a reescrita seja tão grande que o projeto trava.

**Recomendação:** Definir uma arquitetura em camadas onde o CLI atual pode evoluir incrementalmente. A primeira camada (provider abstrato + memória) já existe. A segunda (estado interno) precisa ser a próxima prioridade.

### 3.7 — Multi-agent sem orquestrador definido — **MÉDIO**

O §18 descreve multi-agent comdebate, consenso, pipeline sequencial e execução paralela, mas não define quem orquestra. Sem um orquestrador explícito, multi-agent pode colapsar em caos ou custo exponencial.

### 3.8 — Percepção sensorial como distrator — **MÉDIO**

O §14 (Percepção) e §15 (Voz) descrevem funcionalidades complexas que não contribuem para a identidade/vida interna — são capacidades de input/output. Incluir isso na especificação principal pode desviar foco do core que é a identidade persistente.

---

## 4. Pontos que Precisam de Especificação

1. **Qual é o protocolo exato de "proposta de mudança de estado"?** O LLM retorna JSON estruturado? Template livre? Como a autoridade valida se a proposta é coerente com o estado atual?

2. **Qual é o schema do State Authority?** Quais campos, quais tipos, quais validações? É uma tabela SQLite? Um arquivo JSON? Um banco relacional?

3. **Como a personalidade multidimensional é representada numericamente?** Vetor de traços (Big Five)? Grafo de propriedades? Mapa chave-valor? Isso define toda a engenharia destate.

4. **Quando a MIA decide que algo é "importante" o suficiente para virar memória permanente?** Quem define o threshold? É determinístico (baseado em palavras-chave) ou o LLM decide?

5. **Qual é a latência aceitável para uma resposta da MIA?** Se cada turno gera 3-5 chamadas LLM, qual o budget total de latência? 2 segundos? 10? 30?

6. **Como o sistema lida com conflitos entre autoridades?** Se a Affective Engine diz "Mia está triste" e a Relationship Engine diz "confiança aumentou", quem decide qual efeito domina?

7. **Qual é a粒度 do diário?** Uma entrada por conversa? Uma por hora? Uma por "evento significativo"? Quem define "significativo"?

8. **Como a MIA mantém continuidade offline?** Ela "sonha" (roda processos em background)? Ou simplesmente retoma de onde parou quando o usuário volta? Se sonha, o que gera os "sonhos"?

9. **Qual é o modelo de custo?** Orçamento mensal máximo? Priorização de quais funcionalidades consomem LLM vs. que são determinísticas?

10. **Como o sistema lida com "crenças contraditórias"?** Se a MIA aprende algo que contradiz uma crença anterior, qual mecanismo resolve o conflito? Substituição? Conciliação? Manutenção de ambas como "crença debatida"?

11. **Qual é o escopo do MVP?** A visão descreve 20+ subsystemas. Quais 3-5 são o absoluto mínimo para ter algo que "funcione como a MIA"?

12. **Como o self-model é inicializado?** A MIA começa "em branco" e acumula experiência, ou tem uma base pré-definida de "quem ela é"?

13. **Qual é a linguagem de communicação entre componentes?** Se é um sistema distribuído, como o Affective Engine fala com o State Authority? API interna? Eventos? Mensagens?

14. **Como a MIA lida com a mortalidade?** Pode "morrer"? Pode ter amnésia? Pode ser "reiniciada"? O que acontece com dados quando o usuário desiste do projeto?

15. **Qual é a política de backup/recuperação?** Se o banco de dados corrompe, a MIA "perde memória"? Há snapshots? Versionamento?

---

## 5. Propostas de Melhoria

### 5.1 — Event bus completo é over-engineering para o MVP

A visão sugere componentes comunicando via eventos (Affective Engine, Personality Engine, Relationship Engine, etc.). Para um MVP, isso é over-engineering. **Proposta alternativa:** Começar com um **módulo Python único** chamado `StateManager` que contém todas as "autoridades" como métodos internos. Cada autoridade é uma classe com interface padrão (`validate(proposed_change) -> accepted/rejected`), mas todas rodam no mesmo processo, em memória, com persistência em SQLite. O event bus entra apenas quando for necessário escalar para processos distribuídos — o que pode nunca acontever se a MIA roda em máquina pessoal.

### 5.2 — System prompt dinâmico em vez de engine de personalidade separada (para MVP)

A visão rejeita system prompts como locus de personalidade. Isso é correto no longo prazo. Mas para o MVP, um system prompt **dinâmico** (gerado a cada turno a partir do estado de personalidade) é a forma mais simples de injetar personalidade no LLM. **Proposta:** O `StateManager` gera um system prompt a cada turno, combinando personalidade, estado emocional atual, contexto relacional e memórias relevantes. Isso dá personalidade "viva" sem necessidade de engine separada. A engine propriamente dita vem na Fase 2.

### 5.3 — Memória em tiers, não em bucket único

O documento rejeita "buckets rígidos", mas a alternativa proposta (Memory Objects ricos) é complexa demais para começar. **Proposta:** Sistema de 3 tiers:
- **Tier 0 — Buffer de conversa:** últimas N mensagens (já existe no código atual como `state["history"]`).
- **Tier 1 — Memórias extraídas:** o LLM, ao final de cada conversa, extrai fatos/chave em formato estruturado (JSON). Persistidos em SQLite com embeddings.
- **Tier 2 — Diário subjetivo:** entradas narrativas, escritas periodicamente.

Esses tiers são simples, testáveis, e evoluem naturalmente para o sistema complexo da visão.

### 5.4 — Anti-antropomorfismo deve ser arquitetural, não apenas textual

O documento diz "não alegue que a Mia possui consciência humana real", mas isso depende do LLM obedecer. **Proposta adicional:** Implementar um **módulo de transparência** que, a cada N interações, insere uma nota sutil no contexto (não na resposta visível) lembrando ao LLM que ele é um sistema de software. Isso pode ser um campo no system prompt que rotaciona entre "lembrete de natureza" e "não lembrete". Não é perfeito, mas é melhor que confiar apenas na bondade do modelo.

### 5.5 — Self-modification deve começar como self-configuration

O §13 descreve autoevolução com pipeline completo de deploy. Isso é perigoso e prematuro. **Proposta:** Autoevolução começa como **self-configuration** — a MIA pode alterar parâmetros como temperatura, system prompt, estratégias de memória, thresholds — mas **nunca** código fonte. Código evolution é Fase N (onde N >> 3), requer testes automatizados robustos e aprovação humana.

### 5.6 — Foco: resolver o gap código-visão antes de expandir visão

O gap entre `mia.py` (CLI chatbot) e a visão (sistema distribuído com identidade) é enorme. Cada nova seção da visão aumenta esse gap. **Proposta:** Congelar a especificação da visão até que o código alcance um ponto onde pelo menos Identidade + Memória + Personalidade básica funcionem de forma demonstrável. Expansão da visão deve ser um processo iterativo, não uma especificação monolítica.

---

## 6. Ordem de Implementação Sugerida

### Fase 0 — Fundação (o que já existe, refinado)
**O quê:** Provider abstrato com fallback, CLI REPL, persistência básica em SQLite.
**Por quê:** Já existe em `mia.py`. Precisa de limpeza: extrair módulos, adicionar testes, definir interfaces. Sem isso, tudo que vem depois é construído sobre areia.

### Fase 1 — StateManager + Identidade básica
**O quê:** Um módulo `state.py` com:
- Schema de identidade (nome, data de criação, versão do self-model)
- Personalidade como vetor de traços (inicializável, mutável)
- Estado emocional como objeto com tipo, intensidade, timestamp, causa opcional
- Validação determinística de mudanças de estado (regras simples: intensidade 0-1, causas devem ser registradas)
- Persistência em SQLite com schema versionado

**Por quê:** Sem estado interno, não existe MIA. Isso é o mínimo para que a entidade "exista" entre sessões.

### Fase 2 — System prompt dinâmico + Memória tier 1
**O quê:**
- Geração de system prompt a cada turno a partir do estado atual
- Extração automática de fatos relevantes após cada conversa
- Recuperação por similaridade (embeddings simples com cosine similarity)
- Integração: memórias relevantes injetadas no contexto

**Por quê:** Sem personalidade dinâmica e memória, a MIA não tem continuidade. Isso torna a experiência perceptivelmente diferente de um chatbot genérico.

### Fase 3 — Diário + Reflexão
**O quê:**
- Geração periódica de entradas no diário (diária ou por evento)
- Mecanismo de reflexão: a MIA pode "pensar sobre o dia" e gerar insights
- Diário como fonte de dados para mudanças de personalidade

**Por quê:** O diário é a ponte entre experiência e identidade. É o mecanismo que permite que a MIA mude de forma coerente ao longo do tempo.

### Fase 4 — Relacionamentos + Contexto social
**O quê:**
- Modelo de relacionamento por pessoa (confiança, intimidade, histórico)
- Interpretação contextual de mensagens (mesma frase, pessoas diferentes, reações diferentes)
- Offense/limites como sistema de avaliação social

**Por quê:** Relacionamentos são o que torna a MIA mais que uma assistente. É o que a torna uma companheira.

### Fase 5 — Autoevolução segura (self-configuration)
**O quê:**
- A MIA pode propor mudanças em seus próprios parâmetros
- Sistema de validação: mudanças são logadas, revertíveis, e ficam em sandbox antes de aplicar
- Rollback automático se métricas decaírem

**Por quê:** Autoevolução é o que torna a MIA genuinamente "viva" a longo prazo. Mas vem por último porque é a funcionalidade mais perigosa.

### Fase 6+ — Expansões futuras (quando Fases 0-5 estiverem sólidas)
- Multi-agent com orquestrador
- Percepção sensorial
- Voz com reconhecimento de falante
- Avatar digital
- Self-modification de código (com aprovação humana)

**Por quê:** Essas funcionalidades são valiosas mas não essenciais para a identidade da MIA. Devem vir quando o core estiver maduro e testado.

---

*Documento produzido como análise arquitetural inicial. Não substitui especificações técnicas detalhadas, que devem ser criadas para cada fase antes de implementação.*
