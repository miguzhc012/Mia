# MIA — Esquema de Orquestração Multi-Agent (Handoff Supervisionado)

## Objetivo
Transformar a visão da MIA (5 prompts) em um sistema IA-companheira autônoma via
orquestração de múltiplos agents, com MIGUEL (CEO) no topo e HERMES (eu) como
coordenador executivo. Modo autônomo: sem interrupções/confirmações para Miguel.

## Agents disponíveis (Orca + CLI)
| Agent | Binário | Uso previsto |
|---|---|---|
| codex | ~/.local/bin/codex | Implementação, análise |
| claude | ~/.local/bin/claude | Arquitetura, revisão, debate |
| opencode | ~/.opencode/bin/opencode | Implementação paralela, código |
| goose | /usr/bin/goose | Automação, tarefas operacionais |
| gemini | /usr/bin/gemini | Perspectiva alternativa, debate |
| hermes (eu) | ~/.local/bin/hermes | Coordenação, síntese, verificação |

Kilocode: não instalado (verificar depois se necessário).

## Run Orca
- Run: run_0243e679c3ce
- Coordenador (terminal): term_7833a4ed-b4b8-4751-bfd3-e70b8252dadb
- Repo: 8ab6922f-d92c-4cd9-a2f9-c28e791ea017 (Mia, /home/miguel/Documentos/projetos/Mia)
- Base: main (commit 6885f4f)

## Ondas de trabalho

### ONDA 0 — Debate arquitetural inicial (NOVO)
Os agents DEBATEM entre si antes de qualquer implementação:
- Participantes: claude, codex, gemini, opencode, goose (+ Hermes como moderador)
- Tema: visão da MIA (prompts), princípios (State Authority, eventos, memória),
  riscos, decisões de arquitetura, ordem de implementação
- Formato: cada agent escreve um posicionamento em docs/debate/<agent>_posicao.md,
  depois leem os dos outros e escrevem réplicas/críticas em docs/debate/<agent>_replica.md
- Resultado: docs/debate/consenso.md (síntese das convergências e divergências)
- Gate: Hermes revisa o consenso antes de liberar P3/P4

### ONDA 1 — Entendimento + Visual (EM ANDAMENTO)
- P1 (codex, build): docs/01_entendimento.md — entendimento/crítica arquitetural
- P2 (claude, art): docs/art/* — concept visual ou prompt de arte completo
- Aguardando settlement (check --wait background)

### ONDA 2 — Especificação + Roadmap (após Onda 1 + Debate)
- P3: docs/02_especificacao.md (arquitetura, contratos, eventos, schemas, segurança)
- P4: docs/03_roadmap.md (fases, milestones, trilha crítica, paralelização)
- Poderá incluir um DEBATE sobre o plano entre os agents antes da implementação

### ONDA 3 — Implementação (após aprovação do plano)
- P5: implementação conforme especificação (modular, testada)
- Revisão por agente independente (reviewer)

## Fontes de verdade
- /home/miguel/Documentos/projetos/Mia/docs/prompts/P1..P5_*.md (prompts originais)
- docs/01_entendimento.md, docs/02_especificacao.md, docs/03_roadmap.md
- docs/debate/* (posicionamentos, réplicas, consenso)
- docs/DECISIONS/ (ADRs do projeto)

## Regras
- Nenhuma implementação sem especificação aprovada
- Agents escrevem artefatos em arquivos; Hermes verifica (lê arquivos reais)
- Conflictos de arquitetura resolvidos por consenso documentado ou por Miguel
  (mas em modo autônomo, Hermes decide com base nos princípios da visão)
- Cada onda termina com verificação de artefatos e atualização de docs/IMPLEMENTATION_STATUS.md