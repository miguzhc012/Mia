# DEBATE — Posicionamento arquitetural sobre a MIA

Você é um arquiteto de sistemas participando de um debate técnico sobre o projeto
MIA — uma IA-companheira/agente autônomo de longo prazo, construída do zero como
sistema de software distribuído e modular, agnóstica a LLMs/provedores.

## Contexto (leia antes de escrever)
- Visão completa: /home/miguel/Documentos/projetos/Mia/docs/prompts/P1_entendimento.md
- Pré-planejamento: /home/miguel/Documentos/projetos/Mia/docs/prompts/P3_planejamento.md
- Roadmap solicitado: /home/miguel/Documentos/projetos/Mia/docs/prompts/P4_roadmap.md
- Estado atual do código: /home/miguel/Documentos/projetos/Mia/mia.py (CLI multi-provider, 829 linhas)

## Sua tarefa
Escreva um POSICIONAMENTO técnico honesto em docs/debate/seu_posicao.md com:

1. **O que você entendeu** — a essência da MIA (2-3 parágrafos)
2. **Pontos fortes da visão** — o que está certo e por quê
3. **Riscos arquiteturais** — o que pode dar errado, com gravidade (crítico/alto/médio/baixo)
4. **Discordâncias técnicas** — onde a visão ou abordagem proposta está errada ou
   impraticável, e o que você faria diferente
5. **Decisões-chave a tomar** — as 5-10 perguntas de arquitetura que precisam de resposta
   antes de implementar (ex.: como o State Authority realmente impede o LLM de escrever
   estado, granularidade do event bus, onde SQLite vs outro store, como serializar
   autoevolução com segurança)
6. **Ordem de implementação sugerida** — o que construir primeiro (e por quê)
7. **O que NÃO deveria ser construído agora** — para evitar over-engineering

Seja específico e técnico. Não elogie por elogiar. Se algo é inviável, diga.
Não implemente nada — apenas escreva o documento.

## Restrições
- Escreva APENAS em docs/debate/seu_posicao.md (uma seção por tópico)
- Não altere código, não crie outros arquivos
- Seja direto: isto alimenta um debate real entre agents