# MIA — AGENTS TEAM

> Este arquivo define a equipe, papéis, fluxo de trabalho e regras de verificação.
> Todos os agentes devem lê-lo ao iniciar qualquer trabalho no Mia.

## Estrutura da Equipe

```
                         ┌─────────────────┐
                         │     HERMES      │
                         │ Lead / Builder  │
                         └────────┬────────┘
                                  │
          ┌───────────────┬───────┼───────┬───────────────┐
          ↓               ↓       ↓       ↓               ↓
      CLAUDE          OPENCODE   GOOSE  ARCHITECT         QA
      DEBUG           SECURITY   USER   SYSTEM          TESTS
          │               │       │       │               │
          └───────────────┴───────┼───────┴───────────────┘
                                  ↓
                           REQUIREMENTS
                             GUARDIAN
                                  │
                                  ↓
                         DOCUMENTATION
                             GUARDIAN

                                  +
                             KIMI CODE
                              RED TEAM
```

## Fungões X Agente (compatibilidade)

| Função | Agente | Provider |
|--------|--------|----------|
| **🏗️ Architect Agent** (visão sistêmica) | `claude` | OmniRoute |
| **🐛 Debug/Cyber Forensics** | `claude` | OmniRoute |
| **🧪 QA/Test Engineer** (estratégia) | `hermes` (skills) | — |
| **📚 Documentation Guardian** | `goose` | OmniRoute |
| **🎯 Product/Requirements Guardian** | `opencode` | NVIDIA |
| **🕷️ Kimi Code — Red Team** | `kimi` | OmniRoute |

## Prompts de Papel (docs/team/)

- `hermes_prompt.md` — Lead/Build
- `claude_code_prompt.md` — Debug + Forense
- `opencode_prompt.md` — Security
- `goose_prompt.md` — User adversarial
- `architect_prompt.md` — Systems Architect
- `qa_prompt.md` — QA/Test Engineer
- `requirements_prompt.md` — Requirements Guardian
- `documentation_prompt.md` — Documentation Guardian
- `kimi_prompt.md` — Red Team

## Skills de Cada Agente (instaladas em ~/.agents/skills/ + espelhos)

- Claude → `debug-security-mia`, `systems-architect-mia`, `security-review-mia`
- OpenCode → `security-review-mia`, `qa-test-mia`, `requirements-guardian-mia`
- Goose → `goose-adversarial-mia`, `documentation-guardian-mia`
- Kimi → `red-team-mia`, `security-review-mia`
- Hermes → todas (coordena)

## ⚠️ REGRA DOURADA — Reprodução de Bug (obrigatória)

> Após achar um bug e alguém corrigir, quem ENCONTROU deve tentar
> encontrar o MESMO bug de novo, e também um bug DIFERENTE no mesmo
> local.

Só é considerado **RESOLVIDO** quando o descobridor não conseguir mais:

1. reproduzir o bug original;
2. encontrar o mesmo bug por outro caminho (variante);
3. encontrar um bug diferente no mesmo código.

**Sequência obrigatória (de quem acha → de quem corrige → de quem verifica):**

```
[Descobridor] acha bug → reporta com reprodução
[Corretor] corrige → mostra evidência (testes passando)
[Descobridor] tenta de novo  → original ❌ falha (bug morto)
[Descobridor] tenta variante  → ❌ falha (não ressurge)
[Descobridor] procura outro bug no mesmo local → se achar, VOLTA para correção
[Equipe] só então marca RESOLVIDO e avança
```

## Fluxo de Trabalho Padrão

```
1. HERMES define a tarefa (requisito → plano)
2. HERMES implementa + testes
3. CLAUDE audita/debuga (root cause, 5 whys)
4. OPENCODE revisa segurança (barreira técnica)
5. GOOSE testa como usuário hostil (UX/estado)
6. KIMI ataca (red team) — SEMPRE depois de correções
7. ARCHITECT valida arquitetura (se mudança estrutural)
8. QA converte bugs em testes de regressão
9. REQUIREMENTS Guardian confirma que é o que foi pedido
10. DOCUMENTATION Guardian reconcilia docs
11. HERMES commita com mensagem descritiva + push
```

## Regras de Equipe

1. **Ninguém declara RESOLVIDO sem o ciclo de reprodução completo** (regra dourada)
2. Toda correção de bug → teste de regressão correspondente
3. Suíte completa deve passar: `python3 -m pytest tests/ -q`
4. Evidência real de execução em qualquer veredito (nunca "deveria funcionar")
5. Kimi ataca DEPOIS de cada correção de segurança; se achar algo, bloqueia o avanço
6. OpenCode tem poder de veto técnico (barreira de segurança)
7. Documentação que mente é bug — Documentation Guardian pode bloquear
8. Se um agente não conseguir executar, reportar logo (fallback: Hermes faz)
9. Discussões importantes registradas em `docs/decisions/` (quando aplicável)
10. Working tree limpo antes de nova fase

## Providers & Invocação

```bash
# Claude Code (debug/audit/architect)
claude -p "<tarefa>" --allowedTools "Read,Edit,Write,Bash" --max-turns 15

# OpenCode (security/product) — usa NVIDIA Nemotron Ultra 550B
opencode run "<tarefa>" --model nvidia/nvidia/nemotron-3-ultra-550b-a55b

# Goose (user adversarial / docs)
goose run -t "<tarefa>" --system "$(cat docs/team/goose_prompt.md)"

# Kimi (red team)
kimi -p "<tarefa>" --allowedTools "Read,Edit,Write,Bash" --max-turns 20

# Hermes — coordena todos, implementa, commita, push
```

## Fallbacks

| Agente fora | Fallback |
|-------------|----------|
| Claude down | Hermes debuga |
| OpenCode down | Hermes delega revisão de segurança |
| Goose down | Hermes testa adversarial |
| Kimi down | Hermes faz red team manual com skill red-team-mia |