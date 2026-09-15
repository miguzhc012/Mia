# AVALIAÇÃO CONSOLIDADA — Correção Arquitetural do Onboarding (25 Pontos)

> **Data:** 2026-09-15
> **Avaliadores:** Hermes (orq), Claude Code (análise independente)
> **Status:** OpenCode em processamento (adicionado quando disponível)

---

## Resumo Executivo

A correção proposta é **sólida e necessária** na maioria dos pontos. Das 25 propostas:
- **20 ACORDO** (total ou majoritário)
- **3 PARCIAL** (pontos 1, 13, 15 — com ressalvas importantes)
- **2 DISCORDÂNCIA PARCIAL** (pontos 1 e 15 — risco real de perda funcional)

O ponto **mais sensível** é o §1 (remoção de telemetria): o Claude Code identificou que remover toda telemetria psicológica **destrói o experimento de apego-solidão por design** — o próprio documento §11 diz "sem telemetria não será possível responder como a solidão evolui". A solução é separar: telemetria experimental (com firewall de UI) vs auditoria operacional.

---

## Análise Por Ponto

### 1. REMOVER TELEMETRIA EXPERIMENTAL — PARCIAL (risco alto)

**Minha avaliação:** Discordo da remoção total. O §11 contém "REQUISITO DE TELEMETRIA" explícito. A proposta está certa na separação (observabilidade operacional ≠ telemetria psicológica), mas a execuçãoRemove demais.

**Claude Code concorda:** "A capacidade de trajetória observável é requirement do experimento. O nome `attachment_timeseries` é implementation detail."

**Proposta de solução:** Manter telemetria experimental COM:
- Firewall de UI (não vazar pensamento interno para Miguel automaticamente)
- Retenção limitada (não crescimento infinito)
- Separada de logs operacionais/auditoria
- Classificar como EXPERIMENT (não requirement)

**Classificação:** remoção total = OPEN DECISION; separação de camadas = REQUIREMENT

---

### 2. CORRIGIR STATE AUTHORITY — ACORDO

ADR-003 já está Aceito. §40 deve ser atualizado de OPEN DECISION para DECISION.

**Claude Code:** "ADR-007 admite leitura híbrida ('emoções por regra + LLM para processamento de linguagem'). Manter hybrid_state_authority可行性."

**Risco menor:** ADR-007 diz "híbrido" mas a implementação é determinística. Reconciliar.

**Classificação:** DECISION (fechada)

---

### 3. DEFINIR PAPEL DO LLM — ACORDO

Exatamente o que a implementação atual já faz. Reforço conceitual.

**Classificação:** REQUIREMENT

---

### 4. CORRIGIR HIERARQUIA DE AUTORIDADE — ACORDO

Nova hierarquia (9 níveis) é melhor que a anterior (8). Adiciona Authority vs Precedence — conceito importante.

**Claude Code:** "Authority vs Precedence é uma separação conceitual importante que falta na atual."

**Classificação:** PROPOSITION → precisa debate antes de DECISION

---

### 5. FORMALIZAR REGRA DE CONFLITO — ACORDO

Exemplos são claros. "Autonomia ≠ soberania arquitetural" é uma frase-chave que deve estar no onboarding.

**Classificação:** REQUIREMENT

---

### 6. FORMALIZAR TRUST BOUNDARY — ACORDO

Conceito essencial. A implementação atual (PolicyEngine interna) não é suficiente — precisa de camada externa.

**Classificação:** REQUIREMENT

---

### 7. DIFERENCIAR SELF-MODIFICATION DE ARCHITECTURE GOVERNANCE — ACORDO

Code change ≠ Architecture change. Crítico para governança de agentes.

**Classificação:** REQUIREMENT

---

### 8. ADICIONAR RESOURCE & BUDGET AUTHORITY — ACORDO

Não implementado no código atual. Conceitualmente correto e necessário para autonomia.

**Classificação:** REQUIREMENT

---

### 9. LIMITES DE AGENTES RECURSIVOS — ACORDO

max_depth, max_agents, etc. Sem isso, agentes recursivos podem consumir recursos indefinidamente.

**Classificação:** REQUIREMENT

---

### 10. CORRIGIR MODELO DE RELACIONAMENTO — ACORDO

Relationship(subject, target) é melhor que hardcodar Miguel. Extensível.

**Classificação:** REQUIREMENT

---

### 11. CORRIGIR SEXUALIDADE E OFENSA — ACORDO

Pipeline contextual (Social Interpretation → Affective Appraisal → Boundary Evaluation → Relationship Context → Intimate State) é robusto. Sem regras simplistas.

**Claude Code:** "Correção bem-vinda — §14/§15 originais eram ambíguos."

**Classificação:** REQUIREMENT

---

### 12. DIFERENCIAR EMOTION/SENSATION/NEED/DESIRE/GOAL — ACORDO

Tabela conceitual clara. O código atual mistura emotion_state com sensations e goals.

**Classificação:** REQUIREMENT

---

### 13. CORRIGIR MEMORY OBJECT — PARCIAL

**Claude Code:** "O schema MemoryObject já contempla a maioria dos campos. Belief não deveria ter confidence — confidence é um campo do objeto crença, não da memória."

**Minha avaliação:** Concordo. MemoryObject ≠ Belief ≠ DiaryEntry. Mas não forçar schema excessivo no MVP.

**Classificação:** REQUIREMENT (campos essenciais) + OPTIONAL ( campos avançados)

---

### 14. CORRIGIR BELIEFS — ACORDO

Belief com ciclo: criar → confiança → evidência → revisão. Não implementado no código.

**Classificação:** REQUIREMENT

---

### 15. CORRIGIR ATTENTION — PARCIAL

**Claude Code:** "O ponto 15 propõe 9 fatores de avaliação — excesso para MVP. Começar com 4-5 (relevance, urgency, context, internal_state, goals) e expandir."

**Minha avaliação:** Concordo com parcialismo. Attention Policy é necessária mas 9 fatores é over-engineering inicial.

**Classificação:** REQUIREMENT (ATIVATED) com escopo limitado no MVP

---

### 16. VOICE ALWAYS-ON — ACORDO

LONG-TERM REQUIREMENT. Já classificado corretamente no documento atual.

**Classificação:** LONG-TERM REQUIREMENT

---

### 17. CONCORRÊNCIA E CONSISTÊNCIA — ACORDO

SQLite serializa acessos (SINGLE_WRITER), mas com múltiplos processos ou async precisa de state versioning.

**Classificação:** REQUIREMENT

---

### 18. EVENTOS COM PROCEDÊNCIA — ACORDO

correlation_id, causation_id são padrão de mercado. Necessário para debugging.

**Classificação:** REQUIREMENT

---

### 19. AUDITORIA TÉCNICA — ACORDO

Manter para: mudanças de estado críticas, deploy, permission changes, tool execution. Já parcialmente implementado (hash chain).

**Classificação:** REQUIREMENT

---

### 20. GOVERNANÇA DE ADR — ACORDO

Processo de 10 etapas é completo. ADR antigo em conflito com spec: registrar divergência.

**Classificação:** REQUIREMENT

---

### 21. CLASSIFICAÇÃO OBRIGATÓRIA — ACORDO

Sistema de classificação (7 categorias) é claro. Já usado parcialmente.

**Classificação:** REQUIREMENT

---

### 22. EVITAR ARQUITETURA PREMATURA — ACORDO

Distinguir CONCEITO de ARQUITETURA APROVADA de IMPLEMENTAÇÃO ATUAL. Crítico.

**Classificação:** REQUIREMENT

---

### 23. EVITAR EXCESSO DE INFRAESTRUTURA — ACORDO

Priorizar: clareza, modularidade, testabilidade. Cada componente = razão arquitetural.

**Classificação:** REQUIREMENT

---

### 24. RESULTADO ESPERADO — ACORDO

O estado alvo (onboarding → correções → debate → ADRs → schemas → implementação) é correto.

**Classificação:** META-REQUIREMENT

---

### 25. FORMATO DA RESPOSTA — ACORDO

Lista de alterações + decisões abertas/fechadas + contradições + debate necessário. Correto.

**Classificação:** PROCESSO

---

## DECISÕES FECHADAS (com esta correção)

| # | Decisão | Fechada por |
|---|---------|-------------|
| 2 | State Authority é determinística | ADR-003 + correção §40 |
| 3 | LLM não escreve estado diretamente | §2 reforçado + §3 adicionado |
| 5 | Regras de conflito: orçamento vence autonomia | §5 formalizado |
| 6 | Trust Boundary existe como camada externa | §6 formalizado |
| 8 | Budget/Resource Authority é obrigatório | §8 adicionado |
| 9 | Agentes recursivos têm limites | §9 formalizado |
| 16 | Voz always-on é longo prazo | §16 reclassificado |
| 20 | ADR governance com 10 etapas | §20 formalizado |
| 21 | Classificação obrigatória | §21 formalizado |

## DECISÕES QUE CONTINUAM ABERTAS

| # | Decisão | Status |
|---|---------|--------|
| 1 | Telemetria experimental: manter com firewall ou remover? | OPEN (risco alto) |
| 4 | Hierarquia de autoridade: proposta de 9 níveis — qual alternativa? | OPEN (precisa debate) |
| 13 | MemoryObject: schema final com quantos campos? | OPEN (precisa debate) |
| 15 | Attention Policy: quantos fatores no MVP? | OPEN (4-5 vs 9) |
| 17 | Concorrência: optimistic locking vs serialização SQLite? | OPEN (implementation detail) |

## CONTRADIÇÕES RESTANTES

1. **§1 vs §11:** Remoção total de telemetria contradiz o experimento de apego-solidão. Precisa resolver antes de implementar.
2. **§13 vs §14:** Se MemoryObject e Belief são entidades separadas, o schema atual precisa de tabelas novas — mas a correção diz "não crie tabelas". Tensão entre especificação e implementação.
3. **§22 vs §23:** "Evitar arquitetura prematura" vs "adicionar 8+ componentes novos" — risco de over-engineering documental.

## PONTOS PARA DEBATE MULTI-AGENTE

1. **Telemetria experimental:** manter ou remover? (§1 — risco mais alto)
2. **Hierarquia de autoridade:** a proposta de 9 níveis é a melhor? Há alternativa mais simples?
3. **Attention Policy:** quantos fatores no MVP? (§15)
4. **MemoryObject schema:** campos mínimos vs completos? (§13)

---

## PRÓXIMOS PASSOS RECOMENDADOS

1. **Resolver §1 (telemetria)** via debate — decisão impacta experimento inteiro
2. **Atualizar §40** (State Authority → DECISION, não open)
3. **Atualizar §39** (nova hierarquia de 9 níveis com Authority vs Precedence)
4. **Adicionar §6-corrigido** (Trust Boundary formal)
5. **Adicionar §8** (Budget/Resource Authority)
6. **Atualizar §16-17** (Emotion/Sensation/Need/Desire/Goal separados)
7. **NÃO alterar código até resolver §1 e §15**
8. **Commit da versão corrigida do onboarding**

---

*Relatório produzido por Hermes (orq) + Claude Code (análise independente). OpenCode será adicionado quando disponível.*
