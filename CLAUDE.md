# MIA — Projeto de IA Companheira

## Contexto
MIA é uma IA autônoma com memória, emoção, identidade e autoevolução.
Python 3.10+, SQLite, sem dependências pesadas (PyYAML, rich).

## Estrutura
- `mia_pkg/` — módulos principais (~25 módulos)
- `tests/` — 452 testes, 85% cobertura
- `docs/` — especificação, roadmap, debate arquitetural

## Comandos Importantes
- `python3 -m pytest tests/ -q` — rodar todos os testes
- `python3 -m pytest tests/test_X.py -q` — rodar um módulo específico
- `python3 -m pytest tests/ --cov=mia_pkg --cov-report=term` — cobertura

## Estado Atual
- Fases 0–16 implementadas
- Hardening H1–H27 concluído (SQL injection, memory versionado, trust boundary, etc.)
- 452 testes passando, 85% cobertura
- CI: GitHub Actions (3.11/3.12)

## Papel do Claude Code
1. **DEBUG**: quando eu (Hermes) encontrar bugs, você investiga e corrige
2. **CODE REVIEW**: revisa código novo/alterado antes de commit
3. **TESTES**: cria testes para cobrir gaps identificados
4. **REFACTORING**: melhora qualidade do código quando solicitado

## Regras
- NUNCA execute testes sem antes alterar código (executar para verificar)
- Sempre comente o que mudou e por quê
- Não mude a API pública sem necessidade
- Prefira patches menores a reescritas grandes
- Rode testes antes de declarar "feito"