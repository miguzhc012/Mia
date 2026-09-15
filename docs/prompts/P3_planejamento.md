# PROMPT 3 — PLANEJAR A MIA

Você será responsável por realizar o planejamento técnico aprofundado do projeto MIA.

A Mia é uma IA-companheira/autônoma de longo prazo construída do zero, modular, distribuída e agnóstica a LLMs/provedores.

Não implemente código neste momento.

Seu trabalho é transformar a visão em uma especificação técnica implementável.

## OBJETIVO

Produza um planejamento técnico completo contendo:

1. princípios arquiteturais;
2. arquitetura geral;
3. componentes;
4. responsabilidades;
5. fronteiras entre componentes;
6. contratos;
7. eventos;
8. fluxos de dados;
9. schemas;
10. persistência;
11. protocolos;
12. integração de LLMs;
13. integração de agentes;
14. segurança;
15. execução distribuída;
16. testes;
17. observabilidade;
18. evolução futura.

## SISTEMAS QUE DEVEM SER PLANEJADOS

Inclua pelo menos:

CORE: runtime; lifecycle; configuration; event bus; scheduler.

COGNITION: context; reasoning; planning; decision; imagination; curiosity.

MEMORY: experiences; memory objects; retrieval; consolidation; forgetting; belief revision.

INNER LIFE: emotions; sensations; mood; needs; loneliness; desires.

IDENTITY: self-model; identity; personality; values; historical self states.

SOCIAL: people; relationships; social context; boundaries; offense; trust; attachment; intimacy; attraction; adult sexuality states.

PERCEPTION: audio; vision; location; sensors; environment; activity recognition; social context.

VOICE: VAD; STT; speaker recognition; directed-speech detection; prosody; TTS; self-perception of speech.

EMBODIMENT: avatar; gestures; body language; facial expression; gaze.

AUTONOMY: goals; initiative; attention; scheduling; interruption policy.

AGENTS: registry; orchestration; delegation; recursive agents; capability system; routing; consensus; budget limits.

EVOLUTION: research; self-improvement; tool creation; code modification; testing; rollback.

WORLD: news; web; knowledge; interests; relevance.

NODES: mobile; desktop; VPS; cameras; future devices.

SECURITY: identity; secrets; permissions; policy engine; audit; sandbox; rollback; kill switch.

## ARQUITETURA

Não produza apenas uma lista de pastas.

Explique:

- como os sistemas conversam;
- quem pode chamar quem;
- quem pode escrever em cada estado;
- quais estados são protegidos;
- quais sistemas devem permanecer independentes;
- quais dependências são permitidas;
- onde os LLMs entram;
- onde os agentes entram;
- onde decisões determinísticas devem existir;
- onde modelos probabilísticos são aceitáveis.

## STATE AUTHORITY

Defina uma arquitetura em que o LLM não possa diretamente alterar: emoção; sensação; personalidade; valores; relações; identidade; memória.

Defina os mecanismos necessários para isso.

## EVENT SYSTEM

Modele exemplos completos como:

MIGUEL_SPOKE
MIGUEL_LEFT
MIGUEL_RETURNED
INSULT_RECEIVED
COMPLIMENT_RECEIVED
NEW_PERSON_DETECTED
CAMERA_ACTIVITY_DETECTED
TASK_FAILED
TASK_COMPLETED
NEW_MEMORY_CANDIDATE
LONELINESS_CHANGED
CURIOSITY_TRIGGERED
RESEARCH_COMPLETED
SELF_IMPROVEMENT_PROPOSED

Explique quais sistemas recebem cada evento e quais podem reagir.

## MEMORY

Não crie uma hierarquia simplista de User/Project/Task.

Projete Memory Objects e seus relacionamentos.

## IMPLEMENTAÇÃO

Assuma como ponto de partida:

- Python;
- CLI-first;
- SQLite inicialmente;
- arquitetura modular;
- possibilidade futura de PostgreSQL/Redis/etc.;
- execução em VPS;
- PC e celular como nós distribuídos;
- API/LLM provider abstraction.

Não escolha tecnologias desnecessárias apenas por serem populares.

Priorize simplicidade inicial sem destruir a capacidade de evolução.

## SAÍDA

Entregue:

A. visão geral;
B. diagrama arquitetural;
C. componentes;
D. contratos;
E. eventos;
F. schemas;
G. fluxos;
H. segurança;
I. multi-agent;
J. distributed nodes;
K. testes;
L. riscos;
M. decisões arquiteturais;
N. pontos ainda indefinidos;
O. sugestões de ADRs.

Questione decisões ruins em vez de simplesmente concordar.

Não implemente nada.