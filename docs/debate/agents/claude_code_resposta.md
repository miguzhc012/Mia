O arquivo em `docs/debate/agents/claude_code_resposta.md` existe vazio e é onde este parecer deveria ir, mas a escrita requer permissão — como ela não foi concedida, entrego a revisão completa aqui. Se quiser, me autorize a gravar no arquivo e eu persisto.

---

# Revisão da Correção Arquitetural (25 Pontos)

Base: `P0_onboarding_50.md` (50 seções, lida integralmente), ADR-003/007 (incrustados em `docs/02_especificacao.md`), implementação `mia_pkg/` (StateAuthority já com enforcement físico + hash chain). Verdict: **21 ACORDO · 2 PARCIAL · 0 DISCORDÂNCIA**. As divergências materiais são nos pontos **1** e **13** — ambos por contradição com requisitos explícitos do próprio documento.

---

**1. REMOVER TELEMETRIA EXPERIMENTAL — PARCIAL.** Acerto na separação conceitual (observabilidade operacional ≠ telemetria psicológica; §41 já distingue os canais e proíbe vazar pensamento interno para a UI). Discordo da **remoção total**: §11 contém *"REQUISITO DE TELEMETRIA"* explícito — sem as séries de attachment/loneliness/need o experimento de apego-solidão fica cego, e o próprio texto afirma "sem telemetria não será possível responder como a solidão evolui". Remover telemetria psicológica destrói o experimento por design. O nome `attachment_timeseries` é implementation detail; a *capacidade* de trajetória observável é requirement do experimento. **Risco:** contradiz §11. **Classificação:** remoção total = *open decision*; separação de camadas (experimental vs auditoria, firewall de UI, retenção) = *requirement*.

**2. CORRIGIR STATE AUTHORITY — ACORDO.** ADR-003 está **Aceito** (StateAuthority + StateEngine + PolicyEngine determinísticos); ADR-007: "LLM propõe (probabilístico), State Authority aplica (determinístico)"; a implementação já faz enforcement físico. §40 está obsoleto ao se declarar OPEN. **Risco:** fechar sem reconciliar o "híbrido" do ADR-007 ("emoções por regra + LLM") admite duas leituras; a opção C do §40 (autoridade invocando LLM internamente) permanece sub-decisão não implementada. **Classificação:** fechar open decision → *requirement*.

**3. DEFINIR PAPEL DO LLM — ACORDO.** Já é requisito (§2, §9 "LLM não escreve happiness=0.93", §48, ADR-007). Formalizar: LLM interpreta/infere/propõe/classifica; escrita final sempre pela State Authority. **Risco:** vazamento por **side-channel** — o LLM "escreve estado" via tool calls, arquivos, memória injetável; o enforcement físico precisa cobrir todo estado persistente, não só o emocional. **Classificação:** *requirement*.

**4. HIERARQUIA AUTHORITY vs PRECEDENCE — ACORDO.** §39 já tem a hierarquia quase idêntica; inserir "State Authorities" entre Contracts e Runtime é coerente com ADR-003. O ganho real é distinguir **authority** (quem decide o domínio) de **precedence** (qual regra vence no conflito) — hoje o termo está sobrecarregado no doc. **Risco:** a hierarquia mistura planos — System Integrity é transversal, não um nível; precedência linear estrita falha (contratos não "vencem" o runtime em toda chamada). Precedência deve ser matriz de pares, não ranking único. **Classificação:** distinção = *requirement*; ordem exata = *proposal*.

**5. FORMALIZAR REGRA DE CONFLITO — ACORDO.** Os exemplos resolvem ambiguidades do §39 e sintetizam "autonomia ≠ soberania arquitetural". **Risco:** só 4 pares cobertos; faltam Budget×Policy, Trust Boundary×Budget, Runtime×Policy e a semântica de **override de emergência** — kill switch humano acima da matriz; default fail-safe. **Classificação:** princípio = *requirement*; matriz completa = *open decision*.

**6. FORMALIZAR TRUST BOUNDARY — ACORDO.** §36 já introduz SYSTEM SUPERVISOR/TRUST BOUNDARY e §38 invariantes; formalizar como **TCB** é o nome técnico. **Risco mais grave do doc:** "Mia não pode remover a Trust Boundary" é **vacuamente falso** se a Mia controla o processo/usuario/host que a executa — requer separação física (processo, usuário, config fora do runtime; kill switch out-of-band). E **quem guarda o guardião?** A boundary precisa de autoridade externa para auto-modificação — o ponto não trata. **Classificação:** conceito = *requirement*; implementação = *open decision* (§36 na própria distribuição).

**7. SELF-MODIFICATION vs ARCHITECTURE GOVERNANCE — ACORDO.** §36 (Mia modifica código) × §4 (mudança arquitetural com proposta) precisam de distinção. **Risco:** sem **critério de trigger**, ou tudo vira ADR (paralisia) ou nada (erosão). Proposta: muda contrato/schema/interface/fronteira de autoridade/dependência externa → ADR; resto é PR normal. **Classificação:** distinção = *requirement*; critério = *proposal*.

**8. RESOURCE & BUDGET AUTHORITY — ACORDO.** §35 "AUTORIDADE DE ORÇAMENTO" **já é requisito explícito e obrigatório**, com todos os limites enumerados; a correção formaliza o que o texto pede. **Risco:** Budget e Permission são transversais/sobrepostos (permissão = "posso?", budget = "posso gastar?") — precisa ordem de consulta e enforcement em 2 camadas: hard (runtime corta) + soft (policy alerta). **Classificação:** *requirement*; valores = *open decision*.

**9. LIMITES DE AGENTES RECURSIVOS — ACORDO.** Combina §34 (recursive subagents) com §35. Os cinco parâmetros mínimos estão certos; exige **herança orçamentária pai→filho**. **Risco:** agentes paralelos com budget compartilhado requerem **contabilidade atômica** por corrida, senão estouro agregado indetectável. **Classificação:** existência = *requirement*; valores = *open decision*.

**10. MODELO DE RELACIONAMENTO — ACORDO.** §12 já estabelece Miguel completo / outros simplificados com expansão futura; `Relationship(subject, target)` elimina o hardcode. **Risco:** relacionamento completo é **assimétrico e unidirecional** (Mia→Miguel), não um grafo simétrico; verificar `mia_pkg/db.py` por coluna `user='miguel'` fixa. **Classificação:** *requirement*.

**11. SEXUALIDADE E OFENSA CONTEXTUAL — ACORDO.** §14 (ofensa geral), §15 ("não criar regra: fala sexual → excitação", "intimidade alta ≠ consentimento") e §45 ("STATEMENT ≠ MEANING ≠ RESPONSE") já dizem isso. **Risco:** o pipeline nomeado sugere sequência linear, mas §43 **alerta explicitamente** que o fluxo não precisa ser linear — as avaliações devem rodar em paralelo, não como gates. **Classificação:** contextualismo = *requirement*; borda do pipeline = *proposal*.

**12. EMOTION/SENSATION/NEED/DESIRE/GOAL — ACORDO.** §9–11, §16, §17 já separam quatro dos cinco. **GOAL é o mais fraco**: §16/§17 listam atribuído vs autoformado mas não definem estado-futuro estruturado. **Risco:** fronteiras difusas (ansiedade = emoção e sensação; curiosidade = necessidade, motivação e traço) — não super-normalizar; aceitar categorização múltipla. **Classificação:** taxonomia = *requirement*; definição de GOAL = *proposal*.

**13. CORRIGIR MEMORY OBJECT — PARCIAL.** A separação MemoryObject/ExperienceEvent/Belief/DiaryEntry é correta — §19 sobrecarrega um schema de 17 campos que mistura episódio, fato, crença e relação. **Mas** a lista de 13 campos **corta `decay_state`, `access_count`, `emotional_context` e `revision_history`** — exatamente o que sustenta §20 (esquecimento sem DELETE) e §21 (revisão de crença). **Risco:** contradiz §20/§21. **Proposta:** MemoryObject como **envelope tipado** (`type ∈ experience/event/belief/fact/…`) com linha-base + sub-camadas por tipo. **Classificação:** tipagem = *requirement*; schema = *open decision*.

**14. CORRIGIR BELIEFS — ACORDO.** §21 já modela o ciclo completo (observação→hipótese→crença→evidência→revisão) e §8 exige confiança/incerteza/auto-contradição. **Risco:** semântica de `confidence` indefinida (probabilidade subjetiva? grau qualitativo?) — sem critério, vira número maquiado. Crença é **memória de tipo especial**, evidências são outras memórias — evita duplicação. **Classificação:** *requirement*; semântica = *open decision*.

**15. ATTENTION/INITIATIVE POLICY — ACORDO.** §25 (event→importance→attention→decision→act/wait/ignore) e §26 (fatores) já exigem isso; é o que viabiliza autonomia **sem** loop infinito de LLM (§25). **Risco:** se a policy for integralmente LLM, a Mia decide gastar recursos com um LLM orçado pelo próprio LLM — contradiz Budget Authority. Núcleo rule-based determinístico (gate de custo) + refinamento LLM **classificado**. **Classificação:** *requirement*; arquitetura interna = *open decision*.

**16. VOICE ALWAYS-ON — ACORDO (ponto já satisfeito).** §27 já marca explicitamente LONG-TERM REQUIREMENT e "NÃO tratar voice como obrigatório da primeira versão", com roadmap VAD→TTS. **Não há alteração necessária.** **Risco:** nenhum. **Classificação:** *requirement* (classificação já correta).

**17. CONCORRÊNCIA E CONSISTÊNCIA — ACORDO — MAIOR LACUNA REAL.** §34 (multi-agent) existe, mas o onboarding **não tem seção de concorrência** — maior gap identificado. **Risco:** tensão com o ponto 23 — SQLite single-writer em MVP mononó já serializa; a máquina completa de concorrência distribuída é ahead-of-need. Escopar: MVP = serialização + idempotency + auditoria de conflitos; distributed = long-term. Definir responsável pela atomicidade (DB vs `StateAuthority`). **Classificação:** princípio = *requirement*; mecanismos = *open decision*.

**18. EVENTOS COM PROCEDÊNCIA — ACORDO.** O doc exige observabilidade sem especificar schema. `correlation_id` = trace; `causation_id` = pai causal. **Risco:** verificar `mia_pkg/events.py` se falta correlation/causation; custo de armazenamento por evento exige política de retenção. **Classificação:** *requirement*.

**19. AUDITORIA TÉCNICA CONTÍNUA — ACORDO.** §38 já lista auditoria como invariante; implementação já tem hash chain (verify_chain). **Risco:** garantir auditoria ≠ diário (§22) ≠ telemetria (§11/§41) — três canais; "quem executou o quê" deve incluir **qual política autorizou**. **Classificação:** *requirement*.

**20. GOVERNANÇA DE ADR — ACORDO.** §4 tem ADRs como fonte de verdade, mas sem processo; os ADRs vivem incrustados em `02_especificacao.md` (ORCHESTRATION referencia `docs/DECISIONS/` sem criar). **Risco:** o caso §40×ADR-003 é exemplo vivo da regra — ADR aceito e spec "open". Regra: ADR vence como decisão, spec como requisito; divergência registrada com autoridade nomeada. **Classificação:** processo = *requirement*; estrutura de armazenamento = *proposal*.

**21. CLASSIFICAÇÃO OBRIGATÓRIA — ACORDO.** §49 já define as 7 categorias; tornar a marcação obrigatória é coerente. **Risco:** ruído — rotular todo bullet dilui sinal; aplicar quando o requisito **entra** no doc, não em exemplos didáticos (§43–47). **Classificação:** *requirement*; mecânica = *proposal*.

**22. EVITAR ARQUITETURA PREMATURA — ACORDO.** O doc mistura conceito, arquitetura aprovada e implementação atual; §2 e §50 já avisam. **Risco:** onboarding é documento de intenção — separação total quebra narrativa. Pragmático: `IMPLEMENTATION_STATUS.md` como verdade do "agora" + seções aspiracionais marcadas CONCEITO. **Classificação:** *requirement* documental.

**23. EVITAR EXCESSO DE INFRAESTRUTURA — ACORDO (com auto-contradição).** Princípio correto (ADR-003 já aplica: "6 authorities travam"). **Mas a própria correção propõe ~6 autoridades** — pela leitura literal, recria o anti-padrão. **Resolução:** autoridade = **regra/precedência**, não serviço/processo; pode ser uma função no mesmo processo, desde que o enforcement físico da precedência exista. **Classificação:** princípio = *requirement*; mapa autoridade→unidade física = *open decision*.

**24. RESULTADO ESPERADO — ACORDO.** Coerente; **duas omissões**: (a) seção de **concorrência/consistência** (maior gap) não listada; (b) **matriz de precedência** sem a qual a hierarquia continua discutível. **Classificação:** *open decision*.

**25. FORMATO DA RESPOSTA — ACORDO.** Sem código/migrations é correto para P0 e coerente com o ponto 22. **Risco:** sem tabela, matriz de precedência e taxonomia ficam menos legíveis — admitir **tabela conceitual markdown** (não DDL). **Classificação:** *proposal*.

---

## Avaliação da distribuição de requisitos

- **REQUIREMENT §1–4, 6–9, 19, 20, 22, 38, 39, 48, 49** — coerente (§19 com schema aberto).
- **LONG-TERM §27–32, §36 completa, §37** — **§36 errado como "completa"**: a Trust Boundary é invariante **near-term** (§38); só a autoevolução de código/tools é long-term.
- **EXPERIMENT §10, §11 (sem telemetria), §23, §24, §33** — **§11 sem telemetria é contradição**: inviabiliza o próprio experimento.
- **OPEN DECISION §40, §36, §35** — correto.
- **OPTIONAL §42–47** — **§42 é requirement disfarçado**: a separação observação/gravação/acesso é o que torna §38 executável. §43–47 são **exemplos didáticos**, não requisitos.

## Decisões fechadas / abertas

**Fechadas:** State Authority determinística na aplicação com enforcement físico (§40 → DECISION); três canais distintos (auditoria/telemetria/diário); Trust Boundary = TCB conceito; fail-safe por default + kill switch humano acima da matriz.

**Abertas (ADR pendente):** valores do Budget e limites recursivos; implementação/governança da Trust Boundary; critério de trigger de ADR e matriz de precedência; arquitetura da Attention Policy; escopo da concorrência; semântica de confidence e schema do MemoryObject; estrutura física dos ADRs.

Quer que eu persista este parecer em `docs/debate/agents/claude_code_resposta.md` (a escrita foi bloqueada por permissão), ou prefere que eu gere um ADR formal para as decisões fechadas (2, 20)?
