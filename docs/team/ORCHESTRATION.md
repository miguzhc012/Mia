# MIA — ORQUESTRAÇÃO DA EQUIPE DE AGENTES

## Composição da Equipe

| Agente | Ferramenta | Papel | Provider |
|--------|-----------|-------|----------|
| **Hermes** | Hermes Agent | Lead Engineer / Implementador | OmniRoute |
| **Claude Code** | `claude` CLI | Debugger / Root-cause / Auditor técnico | OmniRoute |
| **OpenCode** | `opencode` CLI | Segurança / Performance / Risco | NVIDIA Nemotron Ultra 550B |
| **Goose** | `goose` CLI | Usuário adversarial / UX / Testador | OmniRoute |

## Prompts de Papel

- `docs/team/hermes_prompt.md` — missão do Hermes
- `docs/team/claude_code_prompt.md` — missão do Claude Code
- `docs/team/opencode_prompt.md` — missão do OpenCode
- `docs/team/goose_prompt.md` — missão do Goose

## Fluxo de Trabalho Padrão

```
1. Hermes implementa (código + testes)
2. Claude Code debuga/audita a implementação (causa raiz, não sintoma)
3. OpenCode revisa segurança/risco (barreira técnica)
4. Goose testa como usuário adversarial (UX, casos de borda)
5. Hermes consolida, commita, documenta
```

## Comandos de Invocação

### Claude Code (debug/correção)
```bash
cd /home/miguel/Documentos/projetos/Mia
claude -p "<tarefa>" --allowedTools "Read,Edit,Write,Bash" --max-turns 12
```

### OpenCode (segurança/revisão)
```bash
cd /home/miguel/Documentos/projetos/Mia
opencode run "<tarefa>" --model nvidia/nvidia/nemotron-3-ultra-550b-a55b
```

### Goose (teste adversarial)
```bash
cd /home/miguel/Documentos/projetos/Mia
goose run -t "<tarefa>" --system "$(cat docs/team/goose_prompt.md)"
```

## Regras de Orquestração

1. **Hermes** decide o que fazer e coordena
2. **Claude Code** aponta bugs com evidência (sintoma → causa raiz → correção → validação)
3. **OpenCode** bloqueia mudanças que introduzam risco — sua avaliação é barreira
4. **Goose** testa como usuário real (apressado, distraído, que faz merda)
5. Todo trabalho é commitado com mensagem descritiva
6. A suíte de testes DEVE passar após cada mudança: `python3 -m pytest tests/ -q`
7. Discussões entre agentes são registradas para decisões importantes