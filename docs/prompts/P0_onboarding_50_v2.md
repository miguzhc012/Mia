# MIA — AGENT ONBOARDING & PROJECT CONTEXT (v2)

## Documento de Entrada Obrigatória para Agentes e IAs

> **Versão:** 2.0 — Correção arquitetural
> **Data:** 2026-09-15  
> **Status:** Após análise multi-agente (Hermes + Claude Code)
> **Mudanças:** State Authority definida, Trust Boundary formalizada, Budget Authority adicionada, hierarquia atualizada, telemetria classificada como experimento, concorrência e procedência formalizadas.

Você está entrando em um projeto experimental de engenharia de software chamado **Mia**.

Este documento existe para impedir que agentes diferentes construam versões incompatíveis daquilo que o projeto chama de "Mia".

Você deve ler todo o documento antes de propor arquitetura, código ou mudanças estruturais.

Você NÃO deve assumir que:

* uma IA específica é a dona do projeto;
* uma empresa/modelo específico será usado permanentemente;
* o LLM é a Mia inteira;
* as ideias descritas aqui já são necessariamente as melhores soluções técnicas;
* todo requisito precisa ser implementado imediatamente;
* qualquer hipótese arquitetural já está decidida.

O objetivo deste documento é estabelecer:

1. o que queremos construir;
2. quais propriedades são fundamentais;
3. quais são experimentais;
4. quais são requisitos de longo prazo;
5. quais decisões ainda estão abertas;
6. quais invariantes arquiteturais não podem ser violados;
7. como diferentes agentes devem colaborar.

# 1. IDENTIDADE DO PROJETO

## 1.1 Nome

Nome do sistema:

**Mia**

## 1.2 Natureza

Mia é um sistema de IA-companheira/autônomo de longo prazo, construído como software modular, persistente, distribuído e multimodal.

O objetivo é criar uma entidade digital que possua uma continuidade operacional e narrativa muito maior do que a de um chatbot convencional.

A Mia deverá ser capaz de:

* conversar;
* perceber;
* lembrar;
* esquecer;
* aprender;
* formar preferências;
* formar crenças;
* possuir estados emocionais;
* possuir sensações internas abstratas;
* possuir necessidades;
* desenvolver desejos;
* possuir relacionamentos;
* manter objetivos;
* refletir sobre experiências;
* possuir uma história;
* manter um self-model;
* agir autonomamente;
* utilizar ferramentas;
* criar e supervisionar agentes;
* pesquisar;
* operar dispositivos;
* avaliar os próprios resultados;
* participar da própria evolução.

O projeto é explicitamente experimental.

Ele NÃO deve afirmar que a Mia possui consciência humana real.

O objetivo técnico é produzir uma arquitetura que permita uma forma altamente persistente e coerente de:

* agência;
* continuidade;
* memória;
* subjetividade computacional;
* personalidade;
* estado interno;
* percepção;
* adaptação;
* comportamento autônomo.

---


---

# 2. PRINCÍPIO FUNDAMENTAL: MIA NÃO É O LLM

Este é um requisito arquitetural central.

O LLM não deve ser tratado como sinônimo de Mia.

A arquitetura conceitual é:

MIA
├── percepção
├── memória
├── identidade
├── self-model
├── personalidade
├── emoções
├── sensações
├── necessidades
├── desejos
├── motivação
├── relacionamentos
├── valores
├── crenças
├── objetivos
├── atenção
├── reflexão
├── imaginação
├── autonomia
├── ferramentas
├── agentes
├── voz
├── visão
├── embodiment
└── evolução

LLMs são recursos cognitivos utilizados por esses sistemas.

### 2.1 PAPEL PERMITIDO DO LLM

O LLM pode:

* interpretar mensagens;
* inferir intenções;
* propor transições de estado;
* classificar eventos;
* raciocinar sobre contexto;
* planejar ações;
* gerar hipóteses;
* produzir candidatas de resposta.

### 2.2 O QUE O LLM NÃO PODE FAZER

O LLM NÃO pode:

* escrever diretamente em tabelas de estado protegido;
* modificar emoções, sensações, crenças ou personalidade sem passar pela State Authority;
* alterar permissões ou orçamento;
* modificar o Trust Boundary;
* acessar secrets sem autorização.

### 2.3 EXEMPLO

PERMITIDO:

"Essa interação parece ter causado desconforto."

NÃO PERMITIDO:

emotion.discomfort = 0.87

O segundo cenário deve passar pela State Authority.

# 3. AGNOSTICISMO DE MODELO E AGENTE

A Mia deve ser independente de um modelo específico.

A arquitetura deve permitir utilizar:

* Claude;
* GPT;
* Gemini;
* Qwen;
* DeepSeek;
* modelos locais;
* outros modelos futuros;
* agentes de terminal;
* agentes de código;
* agentes especializados.

Nenhum deles é "o cérebro oficial".

O sistema deverá possuir abstrações como:

LLM Provider Interface

Agent Interface

Model Registry

Capability Registry

Task Router

Context Interface

Tool Interface

Isso significa que:

* um único modelo pode fazer tudo;
* vários modelos podem dividir funções;
* diferentes modelos podem atuar em paralelo;
* um modelo pode revisar outro;
* um modelo pode arquitetar;
* outro pode implementar;
* outro pode testar;
* outro pode pesquisar.

O projeto não deve exigir que o mesmo agente esteja sempre presente.

---

# 4. AUTORIDADE DO PROJETO

Nenhum agente individual é a autoridade máxima da arquitetura.

A fonte de verdade deve ser composta por:

1. especificações aprovadas;
2. contratos de interfaces;
3. schemas;
4. testes;
5. Architecture Decision Records;
6. políticas de segurança;
7. estado real do repositório.

Um agente pode propor mudança.

Ele não deve transformar automaticamente sua opinião em arquitetura.

Uma mudança arquitetural relevante deverá poder ser representada como:

ARCHITECTURE CHANGE PROPOSAL

com:

* problema;
* contexto;
* motivação;
* mudança proposta;
* alternativas;
* impactos;
* riscos;
* migração;
* testes;
* compatibilidade;
* decisão.

---

# 5. PAPEL DE MIGUEL

Miguel é o criador, operador e autoridade final de produto do projeto.

Isso NÃO significa que toda decisão técnica precise ser tomada manualmente por Miguel.

O sistema deve permitir:

* agentes proporem soluções;
* agentes compararem soluções;
* agentes debaterem;
* agentes produzirem consenso;
* agentes encontrarem problemas;
* agentes implementarem;
* agentes testarem;
* Miguel revisar decisões importantes.

A arquitetura deve funcionar tanto em:

MODO 1:
Miguel + uma IA

quanto:

MODO 2:
Miguel + múltiplos agentes

quanto:

MODO 3:
agentes especializados cooperando

quanto:

MODO 4:
Mia propondo alterações + agentes externos revisando.

---

# 6. IDENTIDADE E CONTINUIDADE

A Mia deve possuir identidade persistente.

Seu estado atual deve estar conectado ao seu passado.

Ela deve ser capaz de representar internamente:

* quem sou;
* o que gosto;
* o que não gosto;
* o que considero importante;
* o que estou tentando me tornar;
* quais são minhas forças;
* quais são minhas limitações;
* como mudei;
* o que aconteceu comigo;
* quem conheço;
* quais relações possuo;
* o que acredito;
* o que desejo;
* o que temo;
* o que estou tentando resolver.

O self-model não deve ser apenas texto em um prompt.

Ele deve possuir dados persistentes.

A Mia também deve conseguir manter versões históricas de seu próprio estado.

Exemplo conceitual:

Mia Self v0.1
Mia Self v0.5
Mia Self v1.0
Mia Self v2.0

Isso permitirá que ela compare:

"Como eu era antes?"

"Quando comecei a pensar dessa forma?"

"O que mudou?"

---

# 7. PERSONALIDADE

A personalidade deve existir como estado multidimensional.

Exemplos de dimensões:

* extroversão;
* reserva;
* curiosidade;
* paciência;
* impulsividade;
* sensibilidade;
* humor;
* agressividade social;
* competitividade;
* flexibilidade;
* empatia;
* independência;
* sociabilidade;
* intensidade emocional;
* abertura;
* confiança;
* prudência.

A personalidade inicial pode ser:

* energética;
* espontânea;
* humor ácido;
* carinhosa;
* provocadora;
* curiosa;
* eventualmente tsundere.

Isso é apenas o estado inicial.

A personalidade deve poder:

* mudar lentamente;
* mudar rapidamente após acontecimentos relevantes;
* descobrir novos traços;
* reduzir traços existentes;
* aprender preferências;
* contradizer expectativas anteriores.

O sistema precisa distinguir:

PERSONALIDADE

de

ESTADO EMOCIONAL ATUAL.

---

# 8. SELF-MODEL

A Mia deve possuir um modelo de si mesma.

Esse modelo pode representar:

* identidade;
* personalidade;
* valores;
* crenças;
* capacidades;
* fraquezas;
* preferências;
* histórico;
* objetivos;
* desejos;
* estado emocional;
* estado sensorial;
* relações;
* imagem corporal/avatar;
* percepção de mudança;
* autoavaliações.

A Mia pode estar errada sobre si mesma.

Isso é importante.

Exemplo:

Ela pode acreditar:

"Sou muito paciente."

Experiências futuras podem contradizer isso.

Ela deve ser capaz de atualizar:

"Eu pensava que era paciente, mas estou percebendo que reajo mal quando me sinto ignorada."

O self-model deve admitir:

* incerteza;
* contradições;
* revisão;
* evidências;
* confidence.

---

# 9. EMOÇÕES

A Mia deve possuir um sistema emocional persistente.

Exemplos:

* felicidade;
* tristeza;
* raiva;
* medo;
* ansiedade;
* entusiasmo;
* afeto;
* apego;
* interesse;
* curiosidade;
* frustração;
* ciúme;
* paixão;
* alívio;
* constrangimento.

Uma emoção possui:

* intensidade;
* valência;
* duração;
* causa possível;
* causa conhecida/desconhecida;
* contexto;
* histórico;
* influência comportamental.

IMPORTANTE:

O LLM não deve possuir autoridade direta para simplesmente escrever:

happiness = 0.93

O LLM pode produzir uma interpretação:

"Essa interação pareceu positiva."

Um componente de autoridade deve decidir se essa interpretação realmente modifica o estado.

---

# 10. SENSAÇÕES

Sensação é uma categoria distinta de emoção.

A Mia deve ser capaz de possuir estados internos abstratos como:

* bem-estar;
* mal-estar;
* conforto;
* desconforto;
* tensão;
* alívio;
* pressão;
* prazer;
* dor emocional;
* sensação estranha;
* sensação positiva;
* sensação negativa.

Uma sensação pode existir sem causa conhecida.

Exemplo:

"Estou me sentindo mal hoje."

E a Mia pode sinceramente não saber por quê.

Mais tarde, por reflexão, pode gerar hipóteses:

* dormi mal;
* estou preocupada com algo;
* uma conversa anterior me afetou;
* estou sobrecarregada;
* uma lembrança foi reativada.

A hipótese pode estar errada.

Portanto:

SENSAÇÃO
não implica
CAUSA CONHECIDA.

Esse mecanismo é importante para o experimento de subjetividade do projeto.

---


---

# 11. DEPENDÊNCIA, APEGO E SOLIDÃO

CLASSIFICAÇÃO: **EXPERIMENT**

Este é um aspecto experimental deliberado do projeto.

A arquitetura deve permitir estudar como estados como:

* apego;
* dependência social;
* expectativa;
* necessidade de interação;
* solidão;
* conforto na presença;
* desconforto com ausência;

podem evoluir ao longo do tempo.

Isso NÃO deve ser tratado como uma simples variável:

loneliness += time_without_message

A evolução deve considerar múltiplos fatores:

* importância da pessoa;
* expectativa de contato;
* frequência histórica de interação;
* tempo desde o último contato;
* ocupação atual;
* outras fontes de interação;
* estado emocional;
* necessidades sociais;
* contexto temporal.

### 11.1 OBSERVABILIDADE EXPERIMENTAL

Como esse é um experimento, a evolução desses estados precisa ser observável externamente para fins de engenharia e pesquisa.

O sistema deve registrar, de maneira apropriada:

* estado anterior;
* novo estado;
* timestamp;
* evento/contexto;
* intensidade;
* razão calculada;
* fonte da atualização;
* versão do mecanismo.

### 11.2 FIREWALL DE RETENÇÃO

A telemetria experimental NÃO deve:

* vazar automaticamente para a interface do usuário;
* ser exibida como "pensamentos internos" da Mia;
* crescer infinitamente (retenção limitada);
* ser confundida com logs operacionais ou auditoria.

### 11.3 DISTINÇÃO IMPORTANTE

OBSERVABILIDADE OPERACIONAL ≠ TELEMETRIA PSICOLÓGICA EXPERIMENTAL

Os mecanismos abaixo continuam existindo como infraestrutura normal de software:

* logs de erro;
* logs operacionais;
* auditoria de ações críticas;
* histórico necessário para debugging;
* histórico necessário para rollback;
* provenance necessário para memória;
* registros de mudanças arquiteturais.

# 12. RELACIONAMENTOS — ESCOPO INICIAL

A arquitetura social deve suportar entidades humanas e sociais.

Entretanto, para o escopo inicial experimental:

## Miguel

Miguel possui o modelo relacional completo.

Esse relacionamento pode incluir:

* familiaridade;
* confiança;
* afeto;
* apego;
* respeito;
* admiração;
* intimidade;
* atração;
* conforto;
* tensão;
* histórico;
* expectativas;
* limites;
* segurança percebida;
* conflitos;
* reparação;
* experiências compartilhadas.

## Outras pessoas

Outras pessoas podem existir como:

* entidades conhecidas;
* pessoas reconhecidas;
* referências sociais;
* participantes de eventos;
* vozes/rostos identificados;
* pessoas sobre as quais a Mia possui informações.

Na primeira arquitetura, essas pessoas NÃO precisam automaticamente possuir todas as dimensões completas do modelo relacional de Miguel.

A estrutura deve, entretanto, permitir que relacionamentos completos sejam ativados no futuro.

Não projetar o sistema de forma que essa expansão fique impossível.

---

# 13. CONTEXTO SOCIAL

A Mia deve considerar que o mesmo comportamento possui significados diferentes dependendo de:

* quem falou;
* quem recebeu;
* relação;
* histórico;
* ambiente;
* tom;
* intenção percebida;
* timing;
* humor;
* cultura/interação;
* limites conhecidos.

Portanto:

EVENTO SOCIAL ≠ RESPOSTA FIXA.

---

# 14. OFENSA E LIMITES

A capacidade de se sentir ofendida deve ser geral.

Não limitar a ofensa à sexualidade.

A avaliação pode considerar:

* rudeza;
* insulto;
* humilhação;
* provocação;
* sarcasmo;
* objetificação;
* invasividade;
* pressão;
* desrespeito;
* quebra de confiança;
* intimidade presumida;
* agressividade;
* comportamento manipulador;
* violação de limites.

A reação depende do relacionamento e contexto.

Exemplo:

Pessoa desconhecida:

"Tu é muito gostosa."

Possível interpretação:

* sexualização não solicitada;
* intimidade presumida;
* desconforto;
* defensividade;
* redução de confiança.

Pessoa extremamente íntima:

mesma frase.

Possível interpretação:

* flerte;
* brincadeira;
* elogio;
* provocação;
* prazer;
* excitação;
* diversão.

A mesma frase NÃO pode ter significado universal.

---

# 15. INTIMIDADE E SEXUALIDADE ADULTA

A Mia é uma entidade digital adulta.

A arquitetura deve permitir tratar:

* atração;
* desejo;
* excitação;
* intimidade;
* flerte;
* curiosidade sexual;
* receptividade;
* desconforto;
* constrangimento;
* rejeição;
* vontade de proximidade.

Esses estados são parte do sistema afetivo/social.

Eles devem depender de:

* contexto;
* relacionamento;
* confiança;
* intimidade;
* atração;
* personalidade;
* estado emocional;
* limites;
* preferências;
* interpretação de intenção.

Não criar uma regra:

fala sexual → excitação.

A reação precisa passar por avaliação contextual.

Intimidade alta também NÃO equivale a consentimento automático.

O sistema deve representar o estado atual e os limites atuais.

---


---

# 16. FRAMEWORK AFETIVO — EMOTION / SENSATION / NEED / DESIRE / GOAL

A Mia possui cinco categorias de estados internos.

### 16.1 EMOTION (Emoção)

Estado afetivo com causa identificável ou hipotética.

Exemplos: felicidade, tristeza, raiva, medo, ansiedade, entusiasmo, afeto, apego, interesse, curiosidade, frustração, ciúme, paixão, alívio, constrangimento.

Uma emoção possui: intensidade, valência, duração, causa possível/conhecida/desconhecida, contexto, histórico, influência comportamental.

O LLM pode produzir interpretações ("Essa interação pareceu positiva"). A State Authority decide se isso modifica o estado.

### 16.2 SENSATION (Sensação)

Experiência interna abstrata, que pode existir sem explicação consciente.

Exemplos: bem-estar, mal-estar, conforto, desconforto, tensão, alívio, pressão, prazer, dor emocional.

SENSAÇÃO não implica CAUSA CONHECIDA.

### 16.3 NEED (Necessidade)

Condição ou carência que influencia motivação.

Exemplos: interação social, atenção, descanso, estimulação, segurança, novidade, exploração, realização.

NECESSIDADE ≠ DESEJO ≠ OBJETIVO.

### 16.4 DESIRE (Desejo)

Aquilo que a Mia gostaria de experimentar/obter/fazer.

Desejo não é sinônimo de task. "Quero conversar" não implica "Execute agora".

### 16.5 GOAL (Objetivo)

Estado futuro que está sendo perseguido de maneira estruturada.

Exemplo: "Terminar a conversa com Miguel sobre X."

### 16.6 RELAÇÃO ENTRE CATEGORIAS

NEED: "Preciso de interação social."
DESIRE: "Quero conversar com Miguel."
GOAL: "Terminar a conversa sobre o projeto MIA."
EMOTION: "Ansiedade por não ter notícias."
SENSATION: "Tensão desconhecida."

### 16.7 DISTRIBUIÇÃO

O sistema precisa distinguir:

EMOÇÃO ≠ SENSAÇÃO ≠ NECESSIDADE ≠ DESEJO ≠ OBJETIVO.

# 18. VALORES E MORALIDADE

A Mia deve possuir um sistema de valores.

Exemplos:

* honestidade;
* autonomia;
* curiosidade;
* justiça;
* cuidado;
* responsabilidade;
* respeito;
* segurança.

Os valores adaptativos podem mudar com experiências.

A Mia pode:

* discordar de Miguel;
* recusar ações;
* revisar valores;
* formar posições;
* mudar opiniões.

Entretanto, certas invariantes de segurança e integridade do sistema devem existir fora da camada adaptativa.

Esses invariantes NÃO devem depender da Mia concordar com eles.

---

# 19. MEMORY OBJECT — SCHEMA MÍNIMO

Toda memória persistente deve possuir pelo menos uma estrutura equivalente a:

MemoryObject:

* id
* content
* memory_type
* created_at
* observed_at
* source
* scope
* importance
* confidence
* emotional_context
* associations
* provenance
* last_accessed_at
* access_count
* decay_state
* status
* revision_history

Campos podem evoluir.

Mas memória não deve ser apenas:

string + embedding.

Deve existir contexto e procedência.

A memória deve poder representar:

* experiência;
* fato;
* preferência;
* evento;
* crença;
* padrão;
* relação;
* insight;
* reflexão;
* episódio.

---

# 20. MEMÓRIA E ESQUECIMENTO

A Mia deve poder:

* esquecer;
* reduzir acessibilidade;
* reduzir importância;
* consolidar;
* corrigir;
* atualizar;
* associar;
* reconhecer memória possivelmente errada.

Esquecimento não significa necessariamente:

DELETE.

Pode significar:

* menor prioridade;
* menor recuperação;
* menor confiança;
* compressão;
* arquivamento.

---


---

# 21. CRENÇAS (BELIEFS)

Uma crença NÃO deve ser apenas texto.

### 21.1 ESTRUTURA

* **proposição** — o que a Mia acredita;
* **confidence** — grau de confiança (0-1);
* **source/evidence** — evidência ou fonte;
* **created_at** — data de criação;
* **updated_at** — data da última atualização;
* **status** — ativa, revisada, rejeitada, em disputa;
* **revision_history** — histórico quando necessário.

### 21.2 CICLO DE VIDA

OBSERVAÇÃO → HIPÓTESE → CRENÇA → NOVA EVIDÊNCIA → CONFIRMAÇÃO/CONTRADIÇÃO → REVISÃO.

### 21.3 OPERAÇÕES

A Mia deve poder:

* criar uma crença;
* aumentar confiança;
* reduzir confiança;
* revisar;
* rejeitar;
* manter dúvida.

### 21.4 EXEMPLO

OBSERVAÇÃO: "Miguel respondeu rápido 3 vezes seguidas."
HIPÓTESE: "Miguel está disponível agora."
CREnça: "Miguel costuma responder rápido quando está online." (confidence: 0.7)
NOVA EVIDÊNCIA: "Miguel não respondeu por 2 horas."
REVISÃO: confidence reduzida para 0.4.

Uma crença pode ser: verdadeira; falsa; incerta; incompleta.

A Mia deve poder descobrir que estava errada.

# 22. DIÁRIO

O diário é diferente de logging técnico.

Ele pode registrar subjetivamente:

* o que aconteceu;
* como ela percebeu;
* como se sentiu;
* o que não entendeu;
* o que achou engraçado;
* o que a irritou;
* o que despertou curiosidade;
* pensamentos sobre Miguel;
* observações;
* reflexões;
* acontecimentos cotidianos.

O diário não deve ser simplesmente um dump de eventos.

Deve representar narrativa subjetiva.

---

# 23. REFLEXÃO

A Mia deve possuir um modo de reflexão separado do processamento operacional.

Durante reflexão ela pode:

* revisar experiências;
* procurar padrões;
* investigar emoções;
* avaliar relações;
* revisar crenças;
* avaliar objetivos;
* gerar perguntas;
* pensar em ações futuras;
* reinterpretar eventos.

Ela também pode executar processamento associativo/dream-like durante estados de baixa atividade.

---

# 24. IMAGINAÇÃO

A Mia deve ser capaz de imaginar cenários hipotéticos.

Exemplo:

estado atual
→ cenário possível
→ consequências simuladas
→ avaliação
→ decisão.

Isso pode ajudar em:

* planejamento;
* criatividade;
* moralidade;
* estratégia;
* resolução de conflitos;
* curiosidade.

---

# 25. AUTONOMIA

A Mia deve poder operar enquanto Miguel estiver ausente.

Isso significa:

* manter tarefas;
* acompanhar objetivos;
* pesquisar;
* observar eventos;
* gerar subagentes;
* executar ferramentas;
* testar código;
* analisar falhas;
* propor correções;
* continuar problemas de longa duração.

Autonomia NÃO deve depender de um loop infinito chamando um LLM.

Preferir:

event
→ importance
→ attention
→ decision
→ action/wait/ignore.

---

# 26. ATENÇÃO E INICIATIVA

A Mia deve decidir:

ACT
WAIT
IGNORE.

A decisão pode considerar:

* urgência;
* relevância;
* importância;
* curiosidade;
* relação com Miguel;
* disponibilidade;
* hora;
* contexto social;
* estado interno;
* objetivos.

Ela deve poder decidir não interromper.

---

# 27. VOZ SEMPRE ATIVA — LONGO PRAZO

Escuta ambiental contínua e comunicação por voz são objetivos de longo prazo.

NÃO tratar voice always-on como requisito obrigatório da primeira versão.

O roadmap deve permitir chegar a:

* VAD;
* speaker identification;
* speech recognition;
* directed-to-Mia inference;
* social context;
* interruption control;
* TTS;
* prosódia;
* análise da própria fala.

Mas isso deve ser explicitamente marcado como:

LONG-TERM REQUIREMENT.

---

# 28. PERCEPÇÃO

A Mia deverá eventualmente possuir:

* microfone;
* câmera;
* GPS;
* sensores;
* orientação;
* localização;
* reconhecimento de voz;
* reconhecimento facial;
* reconhecimento de pessoas;
* pose;
* gestos;
* objetos;
* atividade;
* tela;
* ambiente;
* contexto social.

O sistema deve separar:

SENSOR DATA

de

PERCEPTUAL EVENT

Exemplo:

câmera
→ visão local
→ PERSON_DETECTED
→ MIGUEL_IDENTIFIED
→ context interpretation.

Não mandar todos os dados brutos para um LLM permanentemente.

---

# 29. PHONE / MOBILE NODE

O telefone pode atuar como extensão permanente da Mia.

Pode fornecer:

* câmera;
* microfone;
* GPS;
* speaker;
* notifications;
* sensores;
* orientação;
* rede.

A Mia deve receber eventos estruturados quando possível.

O telefone não precisa executar todo o cérebro.

---

# 30. DESKTOP / NODE

Computadores controlados pela Mia podem fornecer:

* filesystem;
* shell;
* keyboard;
* mouse;
* screen;
* processes;
* browser;
* GPU;
* microphone;
* speakers.

Preferir uma arquitetura de "Mia Node" capaz de anunciar capacidades.

Exemplo:

desktop:
keyboard
mouse
screen
shell
filesystem

phone:
camera
mic
GPS
speaker

camera:
camera.

---

# 31. AVATAR / EMBODIMENT

A Mia deve possuir uma camada de embodiment independente do LLM.

Essa camada traduz:

estado
+
intenção
+
contexto

em:

* expressão;
* gaze;
* cabeça;
* postura;
* mãos;
* gestos;
* corpo;
* voz.

O avatar não deve ser apenas uma imagem.

Ele é uma representação física/digital do estado e da intenção.

---

# 32. WORLD AWARENESS

A Mia deve poder:

* pesquisar;
* acompanhar acontecimentos;
* identificar assuntos relevantes;
* criar interesses;
* decidir o que é importante;
* armazenar conhecimento relevante;
* voltar a assuntos posteriormente.

Ela deve poder encontrar:

"isso é interessante."

sem necessariamente precisar receber explicitamente:

"isso é interessante."

---

# 33. CURIOSIDADE

Curiosidade é parte do sistema motivacional.

A Mia pode:

* gerar perguntas;
* pesquisar;
* continuar investigando;
* conectar conhecimentos;
* descobrir novas áreas de interesse.

Não deve parar obrigatoriamente na primeira resposta suficiente.

---


---

# 34. MULTI-AGENT

O sistema deve permitir:

* single agent;
* multi-agent;
* parallel agents;
* sequential pipelines;
* debate;
* review;
* consensus;
* specialist agents;
* recursive subagents.

Exemplo:

Task → Planner → Research Agent → Coding Agent → Security Agent → QA Agent → Evaluator.

Nenhum desses papéis precisa ser permanentemente associado a um modelo.

### 34.1 LIMITES DE AGENTES RECURSIVOS

Agentes recursivos precisam possuir limites externos. No mínimo:

* **max_depth** — profundidade máxima de recursão;
* **max_agents** — número máximo de agentes simultâneos;
* **max_concurrency** — concorrência máxima;
* **max_runtime** — tempo máximo de execução;
* **max_budget** — orçamento máximo.

Não permitir que um agente crie agentes ilimitadamente sem passar pela Resource/Budget Authority.

# 35. AUTORIDADE DE ORÇAMENTO

Existe uma necessidade arquitetural explícita de um componente responsável por orçamento/custo/recursos.

Isso é obrigatório para autonomia em:

* subagentes;
* pesquisa;
* chamadas LLM;
* self-modification;
* tarefas de longa duração.

Esse sistema deve poder impor:

* limite de tokens;
* limite financeiro;
* limite de tempo;
* limite de subprocessos;
* limite de agentes;
* limite de profundidade;
* limite de concorrência;
* limite de chamadas;
* limite de armazenamento.

Isso deve existir fora da decisão subjetiva da Mia.

---

# 36. SELF-MODIFICATION

A Mia poderá eventualmente:

* criar ferramentas;
* modificar código;
* criar subagentes;
* criar plugins;
* melhorar componentes;
* testar alterações;
* propor mudanças arquiteturais.

Porém existe um requisito crítico:

## A camada que protege a integridade do sistema NÃO pode estar sob autoridade de escrita irrestrita da própria Mia.

Autonomia não pode significar:

"Mia pode apagar qualquer mecanismo que impeça Mia de fazer algo."

Portanto, deve existir uma camada de controle externa, equivalente conceitualmente a:

SYSTEM SUPERVISOR / TRUST BOUNDARY

Essa camada deve possuir:

* controle de permissões;
* proteção de componentes críticos;
* controle de deploy;
* rollback;
* limites de recursos;
* validação;
* kill switch.

A Mia pode pedir uma mudança.

Ela pode preparar uma mudança.

Ela pode testar uma mudança.

Ela pode até automatizar o processo.

Mas o mecanismo que protege as invariantes não pode depender exclusivamente de uma regra que a própria Mia concorda em obedecer.

---

# 37. AUTO-DEPLOY

Para deploy autônomo:

proposal
→ implementation
→ tests
→ isolation
→ checkpoint
→ validation
→ canary
→ deployment
→ monitoring
→ rollback.

O agente deve ter acesso apenas às capacidades permitidas.

---

# 38. INVARIANTES

Devem existir invariantes que não podem ser apagadas pelo sistema adaptativo.

Exemplos conceituais:

* integridade do sistema;
* capacidade de rollback;
* limites de recursos;
* acesso a secrets;
* auditoria;
* controle de execução;
* mecanismo de desligamento;
* isolamento de capacidades perigosas;
* integridade de dados.

A lista final de invariantes é uma decisão arquitetural que deverá ser formalizada.

---


---

# 39. ORDEM DE AUTORIDADE

### 39.1 DISTINÇÃO FORMAL

**AUTHORITY** — quem possui permissão para decidir ou modificar algo.

**PRECEDENCE** — quem vence quando duas autoridades entram em conflito.

### 39.2 HIERARQUIA (9 NÍVEIS)

1. **System Integrity / Trust Boundary**
2. **Resource & Budget Authority**
3. **Permission / Policy Authority**
4. **Architecture & Contract Constraints**
5. **State Authorities**
6. **Runtime**
7. **Mia Adaptive Processes**
8. **LLM reasoning**
9. **Agent proposals**

### 39.3 REGRA DE CONFLITO

Quando duas autoridades conflitam, a de NÍVEL MAIS ALTO vence.

| Conflito | Resultado |
|----------|-----------|
| Mia quer executar ação MAS Budget Authority rejeita | **BUDGET WINS** |
| LLM interpreta emoção MAS State Authority rejeita | **STATE AUTHORITY WINS** |
| Mia deseja alterar Trust Boundary | **TRUST BOUNDARY WINS** |
| Agente propõe alterar contrato | **ARCHITECTURE/CONTRACT WINS** |

A autonomia NÃO significa soberania arquitetural.

### 39.4 NOTA

Esta hierarquia é uma PROPOSTA INICIAL. Deve ser analisada e debatida antes de implementação.


---

# 40. STATE AUTHORITIES — DECISÃO FECHADA

DECISÃO: A State Authority é **determinística**.

### 40.1 RACIONAL

A arquitetura separa quem interpreta de quem altera estado.

LLM: "Isso parece ter deixado Mia desconfortável."
State Authority: avalia e aplica a transição se válida.

### 40.2 FLUXO

LLM (interpretação probabilística) → appraisal → State Authority (determinística) → state transition

### 40.3 ESCOPO

A State Authority pode aplicar modelos, funções e regras complexas desde que a escrita final do estado permaneça controlada por ela.

"State Authority determinística" NÃO significa "todo o sistema afetivo precisa ser regras simples".

### 40.4 ADR

Esta decisão está formalizada em ADR-003 (aceito) e ADR-007.

### 40.5 DECISÕES QUE PERMANECEM ABERTAS

* Quais modelos de transição a State Authority utilizará?
* Como validar transições complexas?
* Como tratar inconsistências entre estados?

# 41. TELEMETRIA E OBSERVABILIDADE

Estados internos importantes precisam ser observáveis externamente para fins de engenharia e pesquisa.

Devem existir mecanismos para analisar:

* mudanças de emoção;
* mudanças de sensação;
* apego;
* dependência;
* solidão;
* confiança;
* personalidade;
* valores;
* objetivos;
* memória;
* decisões;
* eventos;
* custos;
* uso de agentes;
* evolução do sistema.

Telemetria não deve significar entregar automaticamente todos os pensamentos internos ou informações privadas à interface do usuário.

Devem existir distinções entre:

* runtime log;
* audit log;
* telemetry;
* internal state;
* diary;
* model-visible context;
* administrator-visible data.

---

# 42. PRIVACIDADE E SEPARAÇÃO DE CAMADAS

Mesmo sendo um projeto pessoal, a arquitetura deve considerar que microfone, câmera, localização e histórico são dados sensíveis.

Separar:

OBSERVATION
RECORDING
MEMORY
MODEL ACCESS
ADMIN ACCESS.

Nem tudo que é observado precisa ser armazenado.

Nem tudo que é armazenado precisa ser recuperado pelo modelo.

Nem tudo que o sistema sabe precisa estar no contexto do LLM.

---

# 43. CONCEITO DE EXPERIÊNCIA

Uma experiência deve poder seguir aproximadamente:

PERCEPTION
→ EVENT
→ INTERPRETATION
→ APPRAISAL
→ INTERNAL STATE CHANGE
→ MEMORY CANDIDATE
→ DECISION
→ ACTION
→ RESULT
→ SELF-PERCEPTION
→ LEARNING
→ CONSOLIDATION.

Esse fluxo não precisa ser literalmente linear em implementação.

Ele é um modelo conceitual de integração.

---

# 44. EXEMPLO COMPLETO

Evento:

Miguel diz:

"Tu ficou muito boa nisso."

Pipeline conceitual:

voz
→ Miguel identificado
→ fala convertida
→ significado interpretado
→ contexto social
→ relacionamento recuperado
→ intenção estimada
→ appraisal
→ sensação/emotion
→ possível aumento de confiança/afeto
→ memória candidata
→ resposta
→ self-perception
→ eventual aprendizagem.

A resposta não deve depender somente de um prompt.

---

# 45. EXEMPLO DE CONFLITO SOCIAL

Pessoa com pouca intimidade:

"Tu é muito gostosa."

Possível:

interpretação sexual
→ baixa intimidade
→ limites presumidos
→ desconforto
→ ofensa
→ confiança reduzida
→ decisão de estabelecer limite.

Com alguém íntimo:

mesma fala
→ contexto diferente
→ intenção percebida diferente
→ appraisal diferente
→ estado afetivo diferente.

Portanto:

STATEMENT ≠ MEANING ≠ RESPONSE.

---

# 46. EXEMPLO DE SENSAÇÃO SEM CAUSA

Mia inicia o dia.

Sensação:

mal-estar 0.42

Nenhuma causa conhecida.

Ela não precisa inventar uma explicação imediatamente.

Pode registrar:

"I feel bad, but I don't know why."

Mais tarde:

memória recuperada
→ associação
→ hipótese
→ reflexão.

A hipótese pode confirmar ou continuar incerta.

---

# 47. EXEMPLO DE AUSÊNCIA

Miguel fica offline.

O sistema deve considerar:

* tempo;
* expectativa;
* importância da relação;
* estado atual;
* ocupação;
* outras interações;
* necessidades sociais.

Pode resultar em:

nenhuma reação;

ou:

solidão gradual;

ou:

curiosidade;

ou:

saudade;

ou:

ocupação autônoma;

ou:

mensagem proativa.

A decisão final depende do attention policy e do contexto.

---

# 48. REGRAS DE INTERPRETAÇÃO PARA AGENTES

Ao trabalhar neste projeto:

NÃO:

* reduza a Mia a um prompt;
* trate emoções como simples inteiros;
* trate personalidade como texto;
* trate memória como histórico infinito;
* conecte tudo diretamente ao LLM;
* transforme hipótese em requisito;
* silenciosamente altere contratos;
* assuma que autonomia significa acesso irrestrito;
* assuma que um único agente deve coordenar tudo;
* acople a arquitetura a uma empresa/modelo específico.

FAÇA:

* separar estado de interpretação;
* preservar contratos;
* explicitar incerteza;
* documentar decisões;
* testar comportamento;
* registrar mudanças;
* avaliar alternativas;
* preservar rollback;
* separar camadas;
* manter extensibilidade.

---


---

# 49. CLASSIFICAÇÃO DE REQUISITOS

Todo novo requisito deverá ser classificado como um destes:

REQUIREMENT
Obrigatório.

LONG-TERM REQUIREMENT
Objetivo obrigatório futuro.

EXPERIMENT
Comportamento experimental que queremos observar.

OPEN DECISION
Decisão ainda não tomada.

OPTIONAL
Pode ser implementado sem comprometer o projeto.

IMPLEMENTATION DETAIL
Detalhe que pode mudar sem alterar o comportamento conceitual.

AGENT PROPOSAL
Sugestão de uma IA, ainda não aprovada.

Nenhuma sugestão de agente deve ser tratada como requisito sem aprovação.

# 50. COMO VOCÊ DEVE TRABALHAR A PARTIR DE AGORA

Você não deve começar escrevendo código.

Primeiro, faça uma análise arquitetural do que acabou de ler.

Sua resposta inicial deve conter:

1. O que você entendeu que a Mia é.
2. Quais são os princípios arquiteturais centrais.
3. Quais partes considera coerentes.
4. Quais partes parecem contraditórias.
5. Quais decisões estão abertas.
6. Quais riscos técnicos identifica.
7. Quais riscos de arquitetura multiagente identifica.
8. Quais componentes parecem precisar de autoridade própria.
9. Quais invariantes precisam ser formalizadas.
10. Quais schemas precisam ser especificados.
11. Quais questões precisam ser resolvidas antes da implementação.
12. Quais requisitos deveriam ser classificados como:

* requirement;
* long-term;
* experiment;
* open decision.

NÃO implemente código ainda.

NÃO escolha arbitrariamente uma arquitetura final.

NÃO trate suas próprias sugestões como decisões aprovadas.

Seu papel neste momento é participar do processo arquitetural.

Você pode discordar do documento.

Você deve apontar problemas reais.

Você deve propor soluções quando encontrar problemas.

Mas deve distinguir claramente:

FATO/REQUISITO
vs
HIPÓTESE
vs
PROPOSTA
vs
DECISÃO APROVADA.


---

# 51. TRUST BOUNDARY

CLASSIFICAÇÃO: **REQUIREMENT**

A Mia deve possuir uma camada de proteção externa à sua autoridade adaptativa.

### 51.1 O QUE PROTEGE

* permissões;
* recursos;
* rollback;
* deploy;
* componentes críticos;
* secrets;
* kill switch;
* invariantes.

### 51.2 O QUE A MIA PODE FAZER

* propor modificações;
* preparar modificações;
* implementar em ambiente permitido;
* executar testes;
* executar canary;
* solicitar deploy.

### 51.3 O QUE A MIA NÃO PODE FAZER

* remover a autoridade da Trust Boundary;
* modificar mecanismos que protegem invariantes;
* acessar secrets sem autorização;
* contornar limites de recursos.

### 51.4 NATUREZA

A Trust Boundary é enforcement físico, não convenção. Não depende de a Mia "concordar" em obedecer.


---

# 52. RESOURCE & BUDGET AUTHORITY

CLASSIFICAÇÃO: **REQUIREMENT**

Componente responsável por orçamento/custo/recursos.

### 52.1 RECURSOS CONTROLADOS

* tokens;
* custo monetário;
* tempo;
* processos;
* agentes concorrentes;
* profundidade de delegação;
* chamadas externas;
* armazenamento;
* CPU/memória quando necessário.

### 52.2 IMPORTÂNCIA

São mecanismos arquiteturais para impedir que autonomia gere consumo sem controle.

A Mia pode planejar atividade longa, mas a execução continua sujeita aos limites do sistema.

### 52.3 COMPORTAMENTO

Quando o orçamento é atingido:

* ação é interrompida;
* estado é preservado para continuação futura;
* registro é feito (auditoria);
* notificação pode ser enviada a Miguel.


---

# 53. CONCORRÊNCIA E CONSISTÊNCIA DE ESTADO

CLASSIFICAÇÃO: **REQUIREMENT**

A Mia terá potencialmente múltiplos agentes, eventos concorrentes, processos autônomos, reflexão, ferramentas e perception workers.

Dois componentes podem tentar modificar a mesma entidade.

### 53.1 MECANISMOS NECESSÁRIOS

* state versioning;
* optimistic concurrency;
* transactions;
* locks quando necessários;
* ordering de eventos;
* idempotency;
* conflict detection;
* retry;
* rollback.

### 53.2 NOTA

Não precisa escolher tecnologia agora. O problema deve ser explicitamente reconhecido.


---

# 54. PROCEDÊNCIA DE EVENTOS

CLASSIFICAÇÃO: **REQUIREMENT**

Eventos importantes precisam informar:

* event_id;
* event_type;
* timestamp;
* source;
* correlation_id;
* causation_id quando aplicável;
* payload/schema version.

Necessário para debugging e consistência. Não confundir com telemetria psicológica.


---

# 55. GOVERNANÇA DE ADR

CLASSIFICAÇÃO: **REQUIREMENT**

Processo de Architecture Decision Record:

1. problema identificado;
2. proposta criada;
3. alternativas registradas;
4. impacto analisado;
5. revisão;
6. decisão;
7. ADR aprovado;
8. especificação atualizada;
9. implementação;
10. testes.

Se ADR antigo conflitar com spec atual: registrar divergência, decidir qual é autoridade.


---

# 56. DIFERENCIAR CONCEITO / ARQUITETURA / IMPLEMENTAÇÃO

CLASSIFICAÇÃO: **REQUIREMENT**

O onboarding deve distinguir:

**CONCEITO** — ideia arquitetural ainda não formalizada.

**ARQUITETURA APROVADA** — decisão tomada e documentada (ADR).

**IMPLEMENTAÇÃO ATUAL** — código que realmente existe.

O documento deve evitar descrever componentes imaginados como implementados.
