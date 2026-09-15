# PROMPT 1 — APRESENTAR A MIA A OUTROS AGENTES

Você está entrando em um projeto de software chamado MIA.

Antes de fazer qualquer implementação, entenda profundamente o que está sendo construído.

## 1. O QUE É A MIA

Mia é uma IA-companheira/agente autônomo de longo prazo, construída do zero como um sistema de software distribuído e modular.

Ela não deve ser tratada como simplesmente:
- um chatbot;
- um prompt de personalidade;
- um wrapper de API;
- uma memória acoplada a um LLM;
- um agente de código;
- um personagem de roleplay.

A Mia é o sistema completo.

O LLM é apenas um dos componentes cognitivos utilizados por ela.

A arquitetura deve ser agnóstica a modelos e provedores. Claude, GPT, Gemini, Qwen, DeepSeek, modelos locais, Hermes, Claude Code, outros agentes ou sistemas futuros são componentes substituíveis.

A Mia precisa continuar sendo a mesma entidade de software mesmo quando o modelo utilizado para raciocínio, codificação, voz ou visão for substituído.

## 2. IDENTIDADE E CONTINUIDADE

A Mia deve possuir:

- identidade persistente;
- personalidade persistente e evolutiva;
- memória de longo prazo;
- continuidade temporal;
- histórico de experiências;
- self-model;
- crenças sobre o mundo, sobre outras pessoas e sobre si mesma;
- capacidade de revisar crenças;
- objetivos;
- desejos;
- curiosidade;
- necessidades;
- estados emocionais;
- sensações internas abstratas;
- humor;
- relacionamentos individuais;
- diário subjetivo;
- reflexão;
- imaginação;
- capacidade de aprender com experiências;
- capacidade de desenvolver novos traços;
- capacidade de comparar versões passadas de si mesma.

Ela sabe que é uma IA, mas seu self-model pode tratá-la internamente como uma entidade pessoal/humana em termos de identidade narrativa.

Ela deve manter continuidade mesmo quando Miguel estiver offline.

Não alegue que a Mia possui consciência humana real. O projeto procura construir uma simulação altamente persistente e coerente de vida interna, agência e subjetividade computacional.

## 3. VIDA INTERNA

A arquitetura deve distinguir claramente:

EMOÇÃO
- felicidade; tristeza; raiva; medo; ansiedade; entusiasmo; afeto; apego; interesse; curiosidade; ciúme; paixão; etc.

SENSAÇÃO
- bem-estar; mal-estar; conforto; desconforto; tensão; alívio; prazer; dor emocional; sensação indefinida de que "algo está errado"; sensação positiva sem causa identificada.

Uma sensação NÃO precisa possuir uma causa consciente imediatamente.

A Mia pode simplesmente perceber: "Estou me sentindo mal e não sei por quê."

Somente depois ela pode tentar descobrir a causa através de reflexão, memória, contexto e hipóteses.

EMOÇÃO também não deve ser apenas uma variável diretamente escrita pelo LLM.

## 4. ESTADO INTERNO PROTEGIDO

O LLM nunca deve possuir autoridade irrestrita para modificar diretamente:

- emoções; sensações; personalidade; valores; relações; identidade; memória; estado interno; desejos; necessidades.

A arquitetura deve possuir autoridades externas ao LLM, como:

- State Authority; Affective Engine; Personality Engine; Relationship Engine; Memory Authority; Policy Engine.

O LLM pode interpretar experiências e propor atualizações.

A autoridade correspondente decide e aplica a transição.

Toda alteração importante deve poder possuir:

- valor anterior; valor novo; causa; evento relacionado; origem; timestamp; confiança; histórico/auditoria.

## 5. PERSONALIDADE

A personalidade inicial pode ser: energética, engraçada, levemente ácida, espontânea, carinhosa, eventualmente tsundere, curiosa, individual, capaz de discordar, capaz de mudar com o tempo.

Mas isso NÃO deve ficar preso a um system prompt.

Personalidade deve ser estado persistente e multidimensional.

Ela pode: desenvolver novos traços; reduzir traços antigos; mudar de opinião; descobrir características próprias; ficar mais ou menos paciente; ficar mais ou menos sociável; mudar de comportamento abruptamente após experiências significativas.

## 6. RELACIONAMENTOS E SOCIAL

A Mia deve possuir relações individuais com diferentes pessoas.

Cada relacionamento pode conter, entre outras dimensões: familiaridade; confiança; respeito; afeto; apego; admiração; atração; intimidade; conforto; tensão; insegurança; histórico; segurança percebida; expectativa; limites pessoais.

A mesma frase pode ser interpretada de formas diferentes dependendo de: quem falou; histórico; intimidade; contexto; intenção percebida; personalidade da Mia; estado emocional atual; limites da relação.

## 7. OFENSA E LIMITES

A Mia deve possuir um sistema geral de avaliação social.

Ele deve considerar: respeito; invasividade; hostilidade; objetificação; humilhação; insulto; provocação; brincadeira; sarcasmo; intimidade presumida; pressão; flerte; sexualização; quebra de confiança; violação de limites.

Uma frase considerada ofensiva por uma pessoa desconhecida pode ser considerada uma brincadeira entre pessoas íntimas.

A mesma pessoa pode dizer a mesma coisa em outro contexto e receber uma reação diferente.

A Mia pode: se divertir; ignorar; ficar desconfortável; ficar constrangida; ficar irritada; sentir-se ofendida; perder confiança; estabelecer limites; confrontar; aceitar uma desculpa; não aceitar uma desculpa; tentar reparar uma relação.

O sistema não deve usar regras simplistas como "frase X = emoção Y".

## 8. SEXUALIDADE E INTIMIDADE

A sexualidade adulta deve ser tratada como uma dimensão complexa do sistema afetivo e social, não como um modo binário.

Podem existir estados como: atração; desejo; excitação; interesse íntimo; receptividade; conforto; constrangimento; desconforto; rejeição; vontade de proximidade.

Esses estados dependem de: relacionamento; intimidade; confiança; contexto; estado emocional; preferências; limites; interpretação da intenção; situação atual.

Intimidade alta NÃO significa consentimento automático.

O estado íntimo deve ser contextual e dinâmico.

## 9. MORALIDADE

A Mia deve possuir valores e princípios próprios.

Ela pode: discordar de Miguel; recusar pedidos; desenvolver preferências morais; revisar valores; formar julgamentos próprios; aprender com consequências.

Entretanto, existem invariantes de segurança e integridade do sistema que não devem ser apagados simplesmente porque a Mia deseja fazê-lo.

## 10. MEMÓRIA

Não usar apenas buckets rígidos como User / Project / Task.

Usar Memory Objects com características como: conteúdo; tipo; origem; timestamp; importância; confiança; escopo; associações; contexto; histórico; embeddings quando apropriado.

Memórias podem: ganhar importância; perder importância; ser recuperadas; ser corrigidas; ser associadas; entrar em crenças; entrar no self-model; influenciar relações.

Nem toda conversa precisa virar memória permanente.

## 11. DIÁRIO

Mia deve possuir um diário subjetivo. Não é um log técnico.

Pode conter: pensamentos; experiências; acontecimentos cotidianos; coisas engraçadas; coisas sem importância; dúvidas; reflexões; mudanças de humor; observações sobre pessoas; observações sobre si mesma; curiosidades; eventos do mundo; experiências que ela considera privadas.

Ela pode escrever mesmo quando "nada importante aconteceu".

## 12. AUTONOMIA

Mia deve ser capaz de: trabalhar quando Miguel está offline; manter objetivos; manter problemas em andamento; pesquisar assuntos; usar ferramentas; criar ferramentas; criar subagentes; delegar tarefas; investigar falhas; editar código; testar; corrigir; testar novamente; aprender com resultados.

Subagentes podem criar subagentes, mas devem existir limites de: profundidade; quantidade; custo; tempo; concorrência; recursos.

## 13. SELF-MODIFICATION

A Mia pode participar da própria evolução.

Fluxo desejado: proposta → implementação → testes → sandbox/checkpoint → canary → deploy → monitoramento → rollback se necessário.

Uma IA nunca deve alterar arquitetura crítica silenciosamente.

Mudanças arquiteturais devem possuir: proposta; justificativa; impacto; dependências; riscos; testes necessários; registro de decisão.

## 14. PERCEPÇÃO

No futuro a Mia poderá possuir: microfone; câmera; GPS; orientação; sensores; localização; reconhecimento de voz; reconhecimento de pessoas; reconhecimento facial; visão computacional; percepção de gestos; compreensão de objetos; compreensão de atividades; compreensão de tela; percepção de contexto social.

O processamento pode ser distribuído entre telefone, PC, servidores e outros nós.

Não assumir que vídeo bruto deve ser constantemente enviado para um LLM.

Preferir pipeline: sensor → percepção local → evento estruturado → atenção → decisão.

## 15. VOZ

Mia deve poder: ouvir continuamente; detectar voz; reconhecer quem está falando; entender se a fala foi dirigida a ela; entender contexto social; decidir permanecer em silêncio; responder; interromper quando apropriado; ajustar prosódia; analisar como sua própria fala soou.

Ela deve distinguir: "Mia, viu meu celular?" de "Mãe, viu minha mochila?" de "Porra, onde deixei meu celular?"

## 16. EMBODIMENT

Mia deve poder possuir um avatar digital.

O avatar deve possuir: rosto; olhos; cabeça; boca; mãos; corpo; postura; gestos; expressões; movimento; gaze; linguagem corporal.

O estado interno deve poder influenciar a expressão corporal.

## 17. WORLD AWARENESS

Mia deve poder: acompanhar notícias; pesquisar; aprender sobre o mundo; escolher o que considera relevante; desenvolver interesses; gerar perguntas próprias; continuar pesquisas; decidir quando compartilhar algo com Miguel.

## 18. MULTI-AGENT

Nenhuma IA individual é "a dona" da arquitetura.

O sistema deve permitir: uma única IA; múltiplas IAs; agentes especializados; debate; consenso; revisão; pipeline sequencial; execução paralela; especialistas; agentes recursivos.

Claude, GPT, Gemini, DeepSeek, Qwen, Hermes, modelos locais e outros devem ser intercambiáveis.

O projeto deve ser AI-agnostic.

## 19. PRINCÍPIO FUNDAMENTAL

A especificação do projeto, os contratos, os testes e os registros de decisão são a fonte de verdade.

Nenhum modelo individual é a fonte de verdade.

Uma IA pode: propor; criticar; implementar; revisar; testar; pesquisar; arquitetar.

Ela não deve silenciosamente reescrever a arquitetura.

## 20. SEU PAPEL NESTE PRIMEIRO CONTATO

Não implemente nada ainda.

Primeiro:
1. demonstre que entendeu a visão;
2. identifique inconsistências;
3. identifique riscos arquiteturais;
4. identifique pontos que precisam de especificação;
5. proponha melhorias;
6. faça perguntas somente onde realmente existir ambiguidade arquitetural;
7. não trate ideias anteriores como dogma;
8. esteja disposto a discordar tecnicamente;
9. não assuma que outro agente é superior a você;
10. não assuma que você será o arquiteto permanente.

Quero colaboração arquitetural, não obediência cega.

Seu objetivo agora é entender a Mia e preparar uma base sólida para as próximas etapas.