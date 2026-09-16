# MIA — Equipe 6-Agentes

## Arquitetura

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

## Funções X Agente

| Agente | Função | Provider |
|--------|--------|----------|
| Claude Code | 🏗️ Architect + 🐛 Debug/Forense | OmniRoute auto/best-chat |
| OpenCode | 🧪 QA + 🎯 Security/Product | NVIDIA Nemotron Ultra 550B |
| Goose | 📚 Documentation Guardian + Testador hostil | OmniRoute auto/best-chat |
| Kimi Code | 🕷️ Red Team / Hacker | OmniRoute auto/best-coding |

## Fallbacks
- **Goose down** → Hermes roda testes adversariais
- **OpenCode down** → Hermes delega revisão de segurança
- **Claude Code down** → Hermes debuga diretamente
- **Kimi Code down** → Hermes faz red team manual (skill red-team-mia)

## Status dos Agentes (verificado em 2026-09-16)
- ✅ Claude Code (v2.1.273) via OmniRoute auto/best-chat
- ✅ OpenCode (v1.18.31) via NVIDIA Nemotron Ultra 550B (--model flag)
- ✅ Goose (v1.49.0) via OmniRoute auto/best-chat
- ✅ Kimi Code (v0.43.0) via OmniRoute auto/best-coding
- ✅ Hermes Agent (eu) via OmniRoute auto/best-coding

## ⚠️ Regra de Reprodução de Bug
> Após achar um bug e corrigir, quem ENCONTROU tenta encontrá-lo de novo
> (mesmo bug por outro caminho + bug diferente no mesmo local).
> Só é RESOLVIDO quando não consegue mais. Suíte verde + tentativas falhas.