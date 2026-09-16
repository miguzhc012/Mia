# MIA — Equipe 4-Agentes

## Arquitetura

```
     ┌─────────────┐
     │    HERMES    │  ← Orquestrador / Lead Engineer
     │ (eu)         │
     └──┬───┬───┬──┘
        │   │   │
   ┌────┘   │   └────┐
   │        │        │
   ▼        ▼        ▼
CLAUDE    OPENCODE   GOOSE
CODE      (NVIDIA)   (OmniRoute)
Debug     Segurança  Testador
```

## Fallbacks
- **Goose down** → Hermes roda testes adversariais via delegate_task
- **OpenCode down** → Hermes delega revisão de segurança via delegate_task  
- **Claude Code down** → Hermes debuga diretamente

## Status dos Agentes (verificado em 2026-09-16)
- ✅ Claude Code (v2.1.273) via OmniRoute auto/best-chat
- ✅ OpenCode (v1.18.31) via NVIDIA Nemotron Ultra 550B (--model flag)
- ✅ Goose (v1.49.0) via OmniRoute auto/best-chat
- ✅ Hermes Agent (eu) via OmniRoute auto/best-coding