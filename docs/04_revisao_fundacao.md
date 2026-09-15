# 04 — Revisão Independente da Fundação MIA

> **Revisor:** Hermes Agent (papel Reviewer)  
> **Data:** 2026-09-14  
> **Escopo:** Auditoria de código da fundação (EventBus, StateAuthority, PolicyEngine, MemoryStore, LLM, Config, Runtime, DB)  
> **Contrato:** 02_especificacao.md  
> **Testes:** 33/33 passando (pytest)

---

## 1. Veredito Geral

### **APROVADO COM RESSALVAS**

A fundação é sólida e segura nos pontos críticos — State Authority enforce enforcement é físico, PolicyEngine bloqueia LLM de escrever em targets protegidos, hash chain está implementada. Porém, existe uma vulnerabilidade **CRÍTICA** de SQL injection que deve ser corrigida antes da Fase 1, e várias inconsistências com a especificação que podem causar bugs silenciosos.

---

## 2. Conformidade com a Especificação (seção por seção)

### EventBus
| Item | Especificação | Implementação | Status |
|------|--------------|---------------|--------|
| Eventos tipados (D.1) | EventType enum com todos os tipos | Completo, todos os tipos presentes | ✅ |
| Pub/sub síncrono | In-process, sem rede | Implementado corretamente | ✅ |
| subscribe/unsubscribe | Com subscription_id | Implementado | ✅ |
| Validação de eventos | Rejeitar inválidos | Implementado (type check) | ✅ |
| Circuit breaker | Por source | Implementado, mas com ressalvas (ver bugs) | ⚠️ |

### StateAuthority
| Item | Especificação | Implementação | Status |
|------|--------------|---------------|--------|
| Ponto único de entrada | StateAuthority orquestra tudo | Implementado | ✅ |
| Propose flow | validate → policy → apply → audit → event | Implementado | ✅ |
| Enforcement físico | Runtime não expõe endpoint de escrita | Implementado (correto) | ✅ |
| Rollback | `rollback(snapshot_id)` | **NÃO IMPLEMENTADO** | ❌ |
| Snapshot | `snapshot()` | Não implementado como método separado | ❌ |
| Evento STATE_CHANGED | Evento específico para mudanças de estado | Usa MIGUEL_SPOKE como placeholder | ⚠️ |

### PolicyEngine
| Item | Especificação | Implementação | Status |
|------|--------------|---------------|--------|
| LLM blocked targets | personality, identity, core_values | Implementado | ✅ |
| Delete blocked | identity, core_values | Implementado | ✅ |
| Code change rejected | MVP | Implementado | ✅ |
| Rate limiting | Emotion transitions per hour | Implementado | ✅ |
| Confidence validation | Range [0.0, 1.0] | Implementado | ✅ |

### MemoryStore
| Item | Especificação | Implementação | Status |
|------|--------------|---------------|--------|
| CRUD completo | Create, Read, Update, Delete | Implementado | ✅ |
| Imutabilidade | Versões novas em vez de mutação | Não implementado (update muta in-place) | ❌ |
| Importance scoring | Scoring dinâmico | Implementado (básico) | ⚠️ |
| Associations | Lista de UUIDs | Schema existe, mas não há API de associação | ❌ |
| Embedding | field `embedding: BLOB` | Schema existe, sem implementação | ❌ |

### LLM
| Item | Especificação | Implementação | Status |
|------|--------------|---------------|--------|
| Interface abstrata | LLMProvider ABC | Implementado | ✅ |
| Provider chain | Fallback automático | Implementado | ✅ |
| Sem dependências externas | urllib apenas | Implementado (correto) | ✅ |
| Secrets não expostos | Acessível via env var | Implementado | ✅ |

### Config
| Item | Especificação | Implementação | Status |
|------|--------------|---------------|--------|
| Defaults | Carregar defaults | Implementado | ✅ |
| Overrides | Arquivo + env vars | Implementado | ✅ |
| Secrets | Referenciados via env var, não expostos | Implementado | ✅ |
| YAML support | Fallback para JSON | Implementado (com graceful degradation) | ✅ |

### Runtime
| Item | Especificação | Implementação | Status |
|------|--------------|---------------|--------|
| Lifecycle | start/stop com hooks | Implementado | ✅ |
| Signal handling | SIGTERM, SIGINT | Implementado | ✅ |
| Component wiring | Config → DB → EventBus → SA → Memory | Implementado | ✅ |
| Kill switch | `/var/mia/STOP` | Config existe, implementação não verificada | ⚠️ |

### Schema (DB)
| Item | Especificação | Implementação | Status |
|------|--------------|---------------|--------|
| Todas as tabelas | memory_objects, people, relationships, etc. | Implementado (F.2) | ✅ |
| CHECK constraints | Ranges, enums | Implementado | ✅ |
| Foreign keys | Referenciais | Implementado com `PRAGMA foreign_keys=ON` | ✅ |
| WAL mode | Performance | Implementado | ✅ |
| Índices | Performance | Implementado | ✅ |

---

## 3. Bugs e Problemas Encontrados

### 🔴 CRÍTICO

#### Bug #1: SQL Injection via f-string em `_apply_transition`
**Arquivo:** `mia_pkg/state_authority.py:196, 202, 210, 216`  
**Problema:** `proposal.key` é interpolado diretamente em SQL via f-strings:
```python
self._db.execute(
    f"UPDATE emotion_state SET {proposal.key} = ?, snapshot_at = ? WHERE id = ?",
    (proposal.delta, now, before["id"]),
)
```
O método `_validate()` (linha 174-187) **apenas verifica ranges** quando `proposal.key` está em `_RANGE_FIELDS`. Se a key NÃO está na lista (ex: `"happiness; DROP TABLE emotion_state; --"`), a validação passa sem erros e a key arbitrária é injetada no SQL. Não existe whitelist de colunas validada antes da interpolação.

**Impacto:** Qualquer componente (ou LLM via source spoofing) pode executar SQL arbitrário. Embora o PolicyEngine bloqueie `source="llm"` para targets protegidos, um atacante pode usar `source="cognitive_core"` (que passa) com uma key maliciosa.

**Correção necessária:** Validar `proposal.key` contra whitelist de colunas conhecidas ANTES de usar em SQL. O `_RANGE_FIELDS` já serve como lista parcial — basta usá-lo como whitelist também, com fallback para tabelas de personality.

#### Bug #2: `_take_snapshot` usa f-string para nome de tabela
**Arquivo:** `mia_pkg/state_authority.py:242`  
```python
row = self._db.fetchone(f"SELECT * FROM {table} ORDER BY snapshot_at DESC LIMIT 1")
```
O `table` vem de um dicionário hardcoded (`table_map`), então não é explorável diretamente. Porém, o padrão de usar f-strings para SQL é perigoso e deve ser eliminado como prática.

**Impacto:** Baixo (hardcoded map), mas viola o princípio defensivo.

---

### 🟠 ALTO

#### Bug #3: `_apply_transition` só processa 3 de 10 targets
**Arquivo:** `mia_pkg/state_authority.py:189-231`  
**Problema:** O PolicyEngine aceita 10 targets (emotion, personality, memory, identity, relationship, person, goal, diary, sensation, personality_state), mas `_apply_transition` só implementa lógica para `emotion`, `personality` e `memory`. Para todos os outros, o método simplesmente `commit()` sem fazer nada — a transição "aplica" silenciosamente sem modificar o banco.

**Impacto:** Proposal de `target="identity"` com `source="cognitive_core"` seria aceita pelo PolicyEngine, passaria na validação, mas não escreveria nada. O audit log registraria uma transição que nunca aconteceu.

#### Bug #4: Hash chain não é verificada na leitura
**Arquivo:** `mia_pkg/state_authority.py:246-285`  
**Problema:** O `_audit()` calcula `current_hash` e armazena `hash_prev` no registro atual, mas:
1. A hash chain **nunca é verificada** — ninguém compara o `hash_prev` do registro N com o `hash` real do registro N-1
2. `_last_audit_hash` é mantido **em memória** — se o processo reinicia, a chain é silenciamente quebrada (o próximo registro usará `"0" * 64` novamente)
3. Não há método público para **verificar integridade** da chain

**Impacto:** Um atacante com acesso ao banco pode adulterar registros sem detecção.

#### Bug #5: `update_importance` e `delete` usam `total_changes` incorretamente
**Arquivo:** `mia_pkg/memory.py:124, 132`  
```python
return self._db.connection.total_changes > 0
```
`total_changes` é acumulativo para **toda a conexão** (todas as operações desde o `connect()`). Após várias operações, retornará `True` mesmo que a operação específica não tenha alterado nada.

**Impacto:** Falso positivo — caller acha que a operação teve efeito quando não teve.

---

### 🟡 MÉDIO

#### Bug #6: Evento STATE_CHANGED placeholder usa MIGUEL_SPOKE
**Arquivo:** `mia_pkg/state_authority.py:141`  
```python
type=EventType.MIGUEL_SPOKE,  # Placeholder — futuro: STATE_CHANGED
```
Componentes subscritos a `MIGUEL_SPOKE` receberão eventos de mudança de estado, causando comportamento incorreto (ex: Memory registraria "interação com Miguel" quando na verdade o estado mudou internamente).

**Impacto:** Erros lógicos silenciosos em consumidores do Event Bus.

#### Bug #7: EventBus circuit breaker contamina fontes legítimas
**Arquivo:** `mia_pkg/events.py:132-136`  
O circuit breaker agrupa por `source`. Se um handler falha para eventos de `source="cognitive_core"`, **TODOS** os eventos futuros desse source são bloqueados — incluindo eventos legítimos de outros handlers.

**Impacto:** Uma falha temporária em um handler pode derrubar toda a comunicação de um componente.

#### Bug #8: EventBus rejeita eventos inválidos silenciosamente
**Arquivo:** `mia_pkg/events.py:120-122`  
```python
if not isinstance(event.type, EventType):
    logger.warning("Evento rejeitado: type inválido: %s", event.type)
    return
```
Sem exceção, sem return value. Callers não têm como saber que seu evento foi dropped.

**Impacto:** Falhas silenciosas difíceis de debugar.

#### Bug #9: MemoryStore não implementa imutabilidade
**Arquivo:** `mia_pkg/memory.py` (inteiro)  
A especificação diz "Memory Objects são imutáveis após criação — mutações criam versões novas." Porém, `update_importance()` modifica o objeto in-place no banco sem criar nova versão.

**Impacto:** Violação do contrato de imutabilidade; sem rastro de versões anteriores.

#### Bug #10: `search_by_content` — LIKE injection
**Arquivo:** `mia_pkg/memory.py:146`  
```python
(f"%{keyword}%",),
```
O `keyword` é passado como parâmetro (seguro contra SQL injection), mas caracteres `%` e `_` no keyword causam matching inesperado no LIKE. Ex: `keyword="100%"` buscaria `%100%%` e matchearia qualquer coisa com "100".

**Impacto:** Resultados incorretos de busca.

---

### 🟢 BAIXO

#### Bug #11: `get_state` não retorna todos os targets
**Arquivo:** `mia_pkg/state_authority.py:161-168`  
Só retorna snapshots de `emotion_state`, `personality_state`, `identity_state`. Targets como `relationship`, `person`, `goal`, `diary` são ignorados.

#### Bug #12: Config env var parsing pode colidir
**Arquivo:** `mia_pkg/config.py:144`  
`split("_", 1)` — se houver env var `MIA_LLM_PROVIDER_MODEL`, vira section="llm", field="provider_model". Funciona, mas `MIA_SYSTEM_NAME` vira section="system", field="name" — OK. Porém, `MIA_LLM_MAX_TOKENS` vira section="llm", field="max_tokens" — o campo na config default é `max_tokens` dentro de um dict aninhado sob `llm`, mas o override seta `data["llm"]["max_tokens"]` diretamente, o que funciona mas ignora a estrutura original.

#### Bug #13: `Config._data` não é imutável
**Arquivo:** `mia_pkg/config.py:64`  
Apesar de documentado como "imutável", `_data` é um dict mutável. Qualquer código com referência ao Config pode modificar `_data` diretamente.

---

## 4. Testes — Qualidade e Cobertura

### Cobertura Atual
- **33 testes**, todos passando
- Cobertura de: EventBus (7), StateAuthority (4), MemoryStore (7), PolicyEngine (8), Config (5), Integração (2)
- **Ausente:** Runtime (0 testes), LLM (0 testes)

### O que falta testar

1. **Runtime lifecycle** — start/stop/restart não têm teste
2. **LLM provider chain** — fallback, erro de conexão, nenhum provider disponível
3. **Concorrência** — race conditions em EventBus e StateAuthority
4. **Hash chain integrity** — teste de verificação de integridade (não existe)
5. **Targets não implementados** — propose com `target="identity"` deve ser rejeitado ou logado
6. **Config YAML** — só testa JSON; YAML fallback não testado
7. **Edge cases** — delta=None, key vazia mas não checkada, etc.
8. **MemoryStore associations** — API de associação não existe
9. **Kill switch** — verificação de `/var/mia/STOP`
10. **Event Bus circuit breaker reset** — não há como resetar o breaker

### Qualidade
- Testes são bem escritos, com docstrings descritivos
- Helpers (`_temp_db`, `_make_proposal`) reduzem boilerplate
- Cobertura funcional boa para os componentes testados
- Falta teste negativo para concurrência e edge cases

---

## 5. Segurança

### State Authority Enforcement — É Realmente Físico?
**SIM, parcialmente.** O `Runtime` (linha 24-134) não expõe nenhuma API pública que permita ao módulo LLM escrever diretamente no banco. O LLM só pode gerar `StateTransitionProposal` e passar pela `StateAuthority.propose()`. Isso é enforcement físico — o caminho de escrita simplesmente não existe no código do LLM.

**PORÉM:** O enforcement depende de o LLM não ter acesso direto ao `SQLiteConnection`. Se em algum momento o LLM receber referência ao `db` (ex: via tool gateway futuro), o enforcement se rompe.

### O LLM consegue contornar?
**Parcialmente.** O PolicyEngine bloqueia `source="llm"` em targets protegidos. Mas:
- O LLM pode usar `source="cognitive_core"` para passar (o campo source é auto-declarado)
- O LLM pode propor `target="emotion"` com `key` malicioso (Bug #1 — SQL injection)
- **Recomendação:** Validar source contra lista de componentes registrados, não confiar no auto-declarado

### Secrets vazam?
**Não diretamente.** O `Config.get_secret_ref()` retorna o valor da env var, mas o método `data` retorna cópia rasa que inclui nomes de env vars (não os valores). O LLM não tem acesso ao Config diretamente. Porém, se o LLM receber o output de `Config.data` em um prompt, verá `api_key_env: "OPENAI_API_KEY"` — que é a referência, não o secret. Isso é aceitável.

---

## 6. Recomendações Priorizadas (antes da Fase 1)

### 🔴 Prioridade 1 — CRÍTICO
1. **Corrigir SQL injection em `_apply_transition`** (state_authority.py:196, 202, 210, 216) — Criar whitelist de colunas por tabela e validar `proposal.key` contra ela antes de interpolá-lo no SQL.

### 🟠 Prioridade 2 — ALTO
2. **Implementar targets faltantes** em `_apply_transition` — identity, relationship, person, goal, diary, sensation precisam de lógica de escrita OU devem ser removidos da whitelist de targets do PolicyEngine até estarem prontos.
3. **Validar integridade da hash chain** — Implementar método `verify_chain()` que percorre a tabela audit e verifica cada `hash_prev`.
4. **Fix `total_changes` bug** em MemoryStore — Usar `cursor.rowcount` em vez de `total_changes`.
5. **Adicionar whitelist de sources** — Validar `proposal.source` contra componentes registrados, não confiar no valor auto-declarado.

### 🟡 Prioridade 3 — MÉDIO
6. **Criar evento STATE_CHANGED** — Substituir o placeholder MIGUEL_SPOKE por um tipo específico.
7. **Reset do circuit breaker** — Adicionar `reset_source(source)` ao EventBus.
8. **Imutabilidade de MemoryObject** — Implementar versionamento real (criar nova row em vez de UPDATE).
9. **Retornar resultado de emit** — Permitir callers saberem se o evento foi entregue.
10. **Escapar caracteres LIKE** em `search_by_content`.

### 🟢 Prioridade 4 — BAIXO
11. **Tornar Config._data imutável** (usar `MappingProxyType`).
12. **Testes de Runtime e LLM** — Cobrir lifecycle e fallback chain.
13. **Testes de concorrência** — Multithread publish/subscribe.

---

## 7. Resumo por Arquivo

| Arquivo | Linhas | Bugs | Nota |
|---------|--------|------|------|
| `events.py` | 153 | #7, #8 | Sólido, precisa de reset de breaker e return de emit |
| `state_authority.py` | 285 | #1, #2, #3, #4, #6, #11 | **CRÍTICO** — SQL injection; precisa de whitelist e targets faltantes |
| `policy_engine.py` | 139 | — | Bem implementado, regras declarativas corretas |
| `memory.py` | 177 | #5, #9, #10 | CRUD funcional; imutabilidade e total_changes precisam fix |
| `db.py` | 286 | — | Sólido, WAL mode, schema completo, constraints corretos |
| `llm.py` | 207 | — | Bem abstraído, sem dependências externas |
| `config.py` | 164 | #12, #13 | Funcional, defaults e merge OK |
| `runtime.py` | 134 | — | Lifecycle básico implementado, sem testes |
| `test_foundation.py` | 455 | — | 33 testes passando, boa cobertura para componentes testados |

---

**Total de bugs encontrados:** 13 (2 críticos, 3 altos, 5 médios, 3 baixos)  
**Linhas de código auditadas:** ~1.900 (módulos) + ~455 (testes)  
**Conclusão:** A fundação é arquitetonicamente correta e alinhada com a especificação nos pontos de enforcement e separação de concerns. A vulnerabilidade SQL injection é o blocker #1 — todos os outros itens podem ser endereçados incrementalmente.
