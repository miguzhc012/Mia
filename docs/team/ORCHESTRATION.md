# MIA — TEAM & ORCHESTRATION

## Equipe Atualizada

| Agente | Função | Provider | Local de Execução |
|--------|--------|----------|-------------------|
| **Hermes** | Lead/Builder/Orquestrador | Local (Gemini/Groq) | Terminal local |
| **Claude Code** | 🏗️ Architect + Debug/Forense | OmniRoute auto/best-chat | claude -p |
| **OpenCode** | 🎯 Security/Product + QA | NVIDIA Nemotron Ultra 550B | opencode run |
| **Goose** | 📚 Documentation Guardian + User Adversarial | OmniRoute auto/best-chat | goose run -t |
| **Kimi Code** | 🕷️ Red Team / Hacker | OmniRoute auto/best-coding | kimi -p |

## Regras de Ouro

### Regra de Reprodução de Bug (MANDATÓRIA)
> Após corrigir um bug, quem o encontrou deve tentar encontrá-lo novamente.
> Se não conseguir nem reproduzir o original, nem encontrar variante/novo bug,
> e a suíte estiver verde, o bug é considerado RESOLVIDO.

**Fluxo:**
1. Descobridor reporta bug com reprodução → Corretor corrige
2. Descobridor tenta reproduzir o mesmo bug → deve FALHAR
3. Descobridor tenta variante (mesmo alvo, vetor diferente) → deve FALHAR
4. Descobridor procura outro bug no mesmo módulo → se achar, volta ao passo 2
5. Somente quando NENHUM dos 3 fracassa → RESOLVIDO e avança

### Fluxo de Trabalho Padrão
```
Hermes (define tarefa → implementa → testa)
  ↓
Claude Code (architect review + debug, root-cause 5-Whys)
  ↓
OpenCode (security review — barreira técnica)
  ↓
Goose (user adversarial — UX/estado/uso hostil)
  ↓
Kimi Code (red team — tenta quebrar, comprometer)
  ↓
[Hermes aplica correções se houver findings]
  ↓
[Descobridor tenta reproduzir bug de novo (regra dourada)]
  ↓
Hermes commita com mensagem descritiva + push
```

## Convenções de Execução

### Claude Code (debug / architect)
```bash
# SEMPRE ler o prompt antes de invocar:
cat docs/team/architect_prompt.md | head -5
# Para debug:
cat docs/team/claude_code_prompt.md | head -5
# Invocação:
claude -p "<contexto>+<tarefa>" --allowedTools "Read,Edit,Write,Bash" --max-turns 15
```

### OpenCode (security / product)
```bash
# SEMPRE ler o prompt antes:
cat docs/team/opencode_prompt.md | head -5
# Invocação:
opencode run "<contexto>+<tarefa>" --model nvidia/nvidia/nemotron-3-ultra-550b-a55b
```

### Goose (user adversarial / documentation)
```bash
# SEMPRE ler o prompt antes:
cat docs/team/goose_prompt.md | head -5
# Invocação:
goose run -t "<contexto>+<tarefa>" --system "$(cat docs/team/goose_prompt.md)"
```

### Kimi Code (red team)
```bash
# SEMPRE ler o prompt antes:
cat docs/team/kimi_prompt.md | head -5
# Invocação:
kimi -p "<contexto>+<tarefa>" --allowedTools "Read,Edit,Write,Bash" --max-turns 20
```

## Skills Instaladas

### Claude (debug + architect)
- `debug-security-mia` — root-cause analysis, forensic
- `systems-architect-mia` — architecture review
- `security-review-mia` — security checklist

### OpenCode (security + QA)
- `security-review-mia` — security audit checklist
- `qa-test-mia` — test strategy, regression
- `requirements-guardian-mia` — feature scope check

### Goose (user + docs)
- `goose-adversarial-mia` — hostile user testing
- `documentation-guardian-mia` — doc/code consistency

### Kimi (red team)
- `red-team-mia` — attack playbooks (STRIDE/ATLAS)
- `security-review-mia` — severity classification
- 20 `cyber-*` skills de MITRE ATT&CK/ATLAS

### Hermes (lead)
- Todas as skills acima (coordena)

## Commands Rápidas

```bash
# Verificar que a suíte inteira verde
python3 -m pytest tests/ -q

# Kimi rodando red team
cat docs/team/kimi_prompt.md && kimi -p "Ataque a MIA nos 4 playbooks. Relatório + verificação." --max-turns 20

# Claude auditando (debug/architect)
claude -p "Leia o código do módulo X, aplique 5-Whys, reporte." --max-turns 15

# OpenCode security review
opencode run "Revise a segurança do módulo Y. Checklist completa." --model nvidia/nvidia/nemotron-3-ultra-550b-a55b

# Goose testando hostilmente
goose run -t "Teste o comando Z como usuário hostil que não lê docs." --system "$(cat docs/team/goose_prompt.md)"
```

## Ciclo Completo por Fase

```
[Ciclo 1 - Implementação]
  Hermes implementa → commits → push
  Claude audita (debug + architect)
  OpenCode security review
  Goose user test
  Kimi red team

[Ciclo 2 - Verificação]
  Se Kimi/Goose/OpenCode/Claude acharam algo → Hermes corrige
  Descobridor tenta reproduzir (regra dourada)
  Se não conseguir → RESOLVIDO, avança

[Ciclo 3 - Documentação]
  Documentation Guardian reconcilia
  Requirements Guardian valida escopo
  Hermes commita docs + push
```

## Regras Adicionais

1. **Prova > afirmação**: jamais declarar um bug resolvido sem mostrar output real
2. **Reprodutibilidade primeiro**: a primeira coisa a fazer ao investigar é reproduzir
3. **Correção mínima**: menos código = menos risco
4. **Testes obrigatórios**: toda correção de bug gera teste de regressão
5. **Suíte verde antes de commit**: `python3 -m pytest tests/ -q`
6. **Comunicação clara**: reportar resultados, não processos intermediários
7. **Limpeza de workspace**: working tree limpa antes de nova fase
8. **Autonomia respeitada**: não perguntar, fazer, mostrar resultado
9. **Revisão é barreira**: riscos técnicos discutidos antes de prosseguir
10. **Dados sensíveis**: nunca hardcoded, nunca commitados, sempre variável de ambiente