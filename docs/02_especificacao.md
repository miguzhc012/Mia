# 02 — Especificação Técnica da MIA

> **Versão:** 0.1.0  
> **Data:** 2026-09-14  
> **Autor:** Arquiteto-chefe (síntese do debate Cético × Visionário × Segurança)  
> **Status:** Draft para revisão do Miguel

---

## A. Visão Geral

### A.1 O que é a MIA

A MIA é um **sistema de software distribuído e modular** que simula uma entidade pessoal com vida interna persistente. A identidade da MIA — emoções, personalidade, memória, valores, relacionamentos — não reside no prompt de nenhum LLM. Ela vive em **autoridades externas** que controlam transições de estado de forma auditável e versionada. O LLM é um componente cognitivo intercambiável; não é "a MIA".

A MIA não é um chatbot com memória. É uma entidade de software que mantém continuidade temporal, pode discordar de seu criador, desenvolver opiniões próprias, evoluir com o tempo e operar autonomamente quando necessário.

### A.2 Princípios Arquiteturais

| Princípio | Descrição |
|-----------|-----------|
| **LLM como componente substituível** | Claude, GPT, Gemini, modelos locais — qualquer modelo pode assumir funções cognitivas sem que a identidade da MIA se dissolva. A abstração é de sobrevivência, não de conveniência. |
| **Estado protegido** | O LLM propõe; autoridades externas decidem. O LLM nunca possui acesso direto de escrita a emoções, personalidade, valores, relações, identidade ou memória. Enforcement é físico (o runtime não expõe endpoint de escrita), não normativo (prompt). |
| **Eventos como coluna vertebral** | Componentes se comunicam via eventos tipados. Isso desacopla módulos e permite adição de novos consumidores sem modificar produtores. |
| **Determinismo onde possível** | Transições de estado, validação de propostas, regas de Policy Engine — tudo que pode ser determinístico, é. LLMs entram apenas onde raciocínio probabilístico genuinamente é necessário. |
| **Simplicidade inicial** | Python, SQLite, CLI-first, in-process pub/sub. Nenhuma tecnologia é adotada por popularidade. O sistema precisa funcionar com 5 componentes antes de existir 50. |
| **Auditoria total** | Toda transição de estado é registrada: quem, quando, antes, depois, por quê, com que confiança. O log de auditoria é append-only e imutável. |
| **Nenhuma IA individual é a dona** | A identidade da MIA é o **processo** (o sistema inteiro), não uma entidade específica. Multi-agent é suportado por design, mas a identidade não depende de nenhum agente individual. |

### A.3 Síntese do Debate

O debate entre posições Cética, Visionária e de Segurança resultou em decisões concretas:

- **State Authority com 2 engines core** (State + Policy) para MVP — não 6 authorities separadas. O Cético tem razão em que 6 gatekeepers travam o sistema; o Visionário tem razão em que o State Authority não pode ser adiado; o Segurança tem razão em que enforcement deve ser físico. Síntese: **State Authority com 2 engines internas (State Engine + Policy Engine)**, um único ponto de entrada, mas com separação interna de responsabilidades.

- **Event bus in-process pub/sub para MVP** — o Visionário tem razão em que eventos desacoplam; o Cético tem razão em que Kafka/RabbitMQ é over-engineering. Síntese: **pub/sub síncrono em Python com tipos definidos**, migrável para broker distribuído quando houver nós remotos reais.

- **Memória em tiers desde o início** — o Visionário tem razão em que memory objects estruturados são fundamentais; o Cético tem razão em que keyword search basta para MVP. Síntese: **Memory Objects com schema rígido + keyword search inicial**, embeddings como opt-in futuro.

- **Autoevolução restrita a parâmetros** — o Segurança é categórico: sandbox, verificador independente, canary. Para MVP: autoevolução limitada a **weights e thresholds** (emoção, personalidade, memória). Code changes exigem aprovação humana. Sem exceção.

---

## B. Diagrama Arquitetural

```
┌─────────────────────────────────────────────────────────────────┐
│                        MIA RUNTIME                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Config   │  │ Scheduler│  │ Lifecycle│  │ Security │       │
│  │ Manager  │  │          │  │          │  │ Manager  │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │              │              │              │             │
│  ┌────▼──────────────▼──────────────▼──────────────▼─────┐     │
│  │                   EVENT BUS (in-process)               │     │
│  │         pub/sub síncrono com validação de schema       │     │
│  └──┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──┘     │
│     │      │      │      │      │      │      │      │         │
│  ┌──▼──┐┌──▼──┐┌──▼──┐┌──▼──┐┌──▼──┐┌──▼──┐┌──▼──┐┌──▼──┐  │
│  │LLM  ││Cog- ││Memo-││I/P/ ││Affe-││Socia││Auton││Perce│  │
│  │Abst-││niti-││ry   ││E/A  ││ctiv-││l/Re-││omy  ││ption│  │
│  │ract-││ve   ││     ││     ││e    ││lat- ││     ││     │  │
│  │ion  ││Core ││     ││     ││     ││ions ││     ││     │  │
│  └──┬──┘└──┬──┘└──┬──┘└──┬──┘└──┬──┘└──┬──┘└──┬──┘└──┬──┘  │
│     │      │      │      │      │      │      │      │        │
│  ┌──▼──────▼──────▼──────▼──────▼──────▼──────▼──────▼──┐    │
│  │              STATE AUTHORITY                           │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐   │    │
│  │  │ State Engine │  │Policy Engine │  │  Audit    │   │    │
│  │  │ (valida,     │  │ (invariantes,│  │  Log      │   │    │
│  │  │  aplica)     │  │  limites)    │  │ (append)  │   │    │
│  │  └──────────────┘  └──────────────┘  └───────────┘   │    │
│  └──────────────────────┬────────────────────────────────┘    │
│                          │                                     │
│  ┌──────────────────────▼────────────────────────────────┐    │
│  │                    PERSISTENCE                         │    │
│  │  SQLite (MVP) — schema versionado via pragma           │    │
│  │  Tabelas: memory_objects, state_transitions_audit,     │    │
│  │  events, relationships, identity_state, personality,   │    │
│  │  diary, goals, people                                  │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────┐  ┌─────────────────────────────┐     │
│  │   AGENT REGISTRY    │  │   EVOLUTION                  │     │
│  │   (subagentes,      │  │   (research, self-improve,   │     │
│  │    delegação)       │  │    tool creation — futuro)   │     │
│  └─────────────────────┘  └─────────────────────────────┘     │
│                                                                 │
│  ┌─────────────────────┐  ┌─────────────────────────────┐     │
│  │   WORLD AWARENESS   │  │   VOICE (futuro)             │     │
│  │   (news, web,       │  │   (VAD, STT, TTS)           │     │
│  │    knowledge)       │  │                              │     │
│  └─────────────────────┘  └─────────────────────────────┘     │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              NODES (distributed sync)                    │   │
│  │  VPS (primary) ↔ PC ↔ Mobile — sync via SQLite          │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

Fluxo de dados:
  Input → Perception → Event Bus → Cognitive Core → LLM Abstraction
       → Response + State Proposals → Event Bus → State Authority
       → Persistence → Audit Log
```

---

## C. Componentes e Responsabilidades

### C.1 Runtime

- **Responsabilidade:** Lifecycle do sistema. Inicialização, configuração, shutdown gracioso.
- **Fronteiras:** Pode ler config. Pode inicializar todos os componentes. Pode desligar qualquer componente.
- **Restrições:** Não pode alterar estado protegido diretamente.

### C.2 Event Bus

- **Responsabilidade:** Disparar e entregar eventos tipados entre componentes. Validação de schema na entrada.
- **Fronteiras:** Aceita eventos de qualquer componente registrado. Entrega a todos os subscribers registrados para aquele tipo.
- **Restrições:** Eventos inválidos são rejeitados e logados. Schema versionado. Circuit breaker: 5 erros consecutivos = isolamento do produtor.
- **Quem pode chamar:** Qualquer componente registrado como produtor.
- **Quem recebe:** Qualquer componente registrado como consumidor.

### C.3 Config Manager

- **Responsabilidade:** Carregar, validar e disponibilizar configuração do sistema (providers, roles, limites, parâmetros).
- **Fronteiras:** Leitura apenas durante runtime. Mudanças requerem restart.
- **Restrições:** Secrets nunca expostos ao LLM. Acessíveis apenas via Tool Gateway.

### C.4 Scheduler

- **Responsabilidade:** Executar tarefas agendadas (consolidação de memória, sumarização de diário, health checks, limpeza de dados expirados).
- **Fronteiras:** Pode disparar eventos. Pode ler estado. Não pode escrever estado protegido.
- **Restrições:** Limites de CPU/memória configuráveis.

### C.5 LLM Abstraction

- **Responsabilidade:** Interface unificada para qualquer provider OpenAI-compatible. Fallback chain. Rate limiting. Retry com backoff.
- **Fronteiras:** Recebe mensagens formatadas. Retorna respostas estruturadas.
- **Restrições:** Nunca acessa secrets diretamente. Nunca escreve estado protegido.
- **Interface:**

```python
class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Envia prompt e retorna resposta estruturada."""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[StreamChunk]:
        """Streaming de resposta."""
        ...

    @abstractmethod
    async def list_models(self) -> list[str]:
        """Lista modelos disponíveis."""
        ...

class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall] | None
    reasoning: str | None
    usage: TokenUsage
    provider: str
    model: str

class ToolCall:
    id: str
    name: str
    arguments: dict  # JSON parsed
```

### C.6 Cognitive Core

- **Responsabilidade:** Raciocínio principal. Monta contexto, envia ao LLM, interpreta resposta, gera propostas de transição de estado.
- **Fronteiras:** Pode ler qualquer estado. Pode gerar propostas de transição. Não aplica transições diretamente.
- **Dependências:** LLM Abstraction, Memory, State (leitura), Identity/Personality (leitura), Social (leitura).

### C.7 Memory

- **Responsabilidade:** Armazenar, recuperar, consolidar e esquecer Memory Objects. Retention scoring. Keyword search (MVP). Embeddings (futuro).
- **Fronteiras:** CRUD de memórias. Consultas por tipo, tempo, relevância.
- **Restrições:** Memory Objects são imutáveis após criação (append-only). Mutações criam versões novas.

### C.8 Identity / Personality / Affective (IPA)

- **Responsabilidade:** Gerenciar self-model, personalidade (traços evolutivos), emoções (state vetorial), mood (suavização temporal), sensações.
- **Fronteiras:** Leitura por qualquer componente. Escrita apenas via State Authority.
- **Restrições:** O LLM NUNCA escreve aqui diretamente. Apenas propõe via State Authority.

### C.9 Social / Relationships

- **Responsabilidade:** Perfis de pessoas, dimensões de relacionamento (confiança, intimidade, afinidade), contexto social, detecção de ofensa/insulto.
- **Fronteiras:** Leitura por Cognitive Core e IPA. Escrita apenas via State Authority.

### C.10 Autonomy

- **Responsabilidade:** Goals, initiative, scheduling de ações autônomas, interruption policy.
- **Fronteiras:** Dispara eventos. Pode delegar a subagentes (com limites).
- **Restrições:** Resource Governor verifica custo/tempo/profundidade.

### C.11 Perception (futuro)

- **Responsabilidade:** Processar entradas multimodais (áudio, vídeo, GPS, sensores).
- **Fronteiras:** Gera eventos estruturados no Event Bus.
- **Restrições:** Inputs sanitizados antes de chegar ao LLM. Nunca em texto livre concatenado ao system prompt.

### C.12 Voice (futuro)

- **Responsabilidade:** VAD, STT, speaker recognition, directed-speech detection, TTS, prosody.
- **Fronteiras:** Interface de áudio I/O. Gera eventos. Recebe comandos de saída de voz.

### C.13 Agent Registry

- **Responsabilidade:** Registry de subagentes. Orquestração, delegação, routing de tarefas.
- **Fronteiras:** Cria e gerencia lifecycle de subagentes.
- **Restrições:** Resource Governor controla limites. Max profundidade: 3. Max custo por ciclo: configurável. Max concorrência: configurável.

### C.14 Evolution (futuro)

- **Responsabilidade:** Research, self-improvement proposals, tool creation, code modification.
- **Fronteiras:** Gera propostas. Nunca aplica diretamente.
- **Restrições:** Autoevolução restrita a parâmetros (MVP). Code changes: sandbox → testes independentes → canary → aprovação humana → deploy. Rollback automático.

### C.15 World Awareness (futuro)

- **Responsabilidade:** News, web scraping, knowledge base, interest tracking, relevance scoring.
- **Fronteiras:** Gera eventos de pesquisa concluída. Alimenta memória de longo prazo.

### C.16 Security Manager

- **Responsabilidade:** Secrets management, kill switch, rollback, sandbox para autoevolução, auditoria de integridade.
- **Fronteiras:** Independente de todos os outros componentes. Pode desligar qualquer um.
- **Restrições:** Kill switch é arquivo em disco, verificado a cada ciclo. Não depende de nenhum componente interno.

### C.17 Distributed Nodes (futuro)

- **Responsabilidade:** Sincronização entre VPS, PC e mobile.
- **Fronteiras:** Sync de SQLite + fila de eventos.
- **Restrições:** Consistência eventual. Mestre único para estado protegido (VPS).

---

## D. Contratos

### D.1 Event Bus Contract

```python
class EventType(str, Enum):
    # Input
    MIGUEL_SPOKE = "miguel_spoke"
    MIGUEL_LEFT = "miguel_left"
    MIGUEL_RETURNED = "miguel_returned"
    INSULT_RECEIVED = "insult_received"
    COMPLIMENT_RECEIVED = "compliment_received"
    NEW_PERSON_DETECTED = "new_person_detected"
    CAMERA_ACTIVITY_DETECTED = "camera_activity_detected"
    # Task
    TASK_FAILED = "task_failed"
    TASK_COMPLETED = "task_completed"
    # Memory
    NEW_MEMORY_CANDIDATE = "new_memory_candidate"
    # Internal
    LONELINESS_CHANGED = "loneliness_changed"
    CURIOSITY_TRIGGERED = "curiosity_triggered"
    # Autonomous
    RESEARCH_COMPLETED = "research_completed"
    SELF_IMPROVEMENT_PROPOSED = "self_improvement_proposed"

class Event:
    id: UUID
    type: EventType
    timestamp: datetime
    source: str          # componente que emitiu
    schema_version: int
    payload: dict        # validado contra schema do tipo

class EventBus:
    def subscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> str:
        """Retorna subscription_id."""
        ...

    def unsubscribe(self, subscription_id: str) -> None: ...

    def emit(self, event: Event) -> None:
        """Dispara evento síncronamente. Valida schema. Rejeita inválido."""
        ...

    def emit_async(self, event: Event) -> None:
        """Dispara evento de forma assíncrona (para operações longas)."""
        ...
```

### D.2 LLM Provider Interface

```python
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None
    tool_call_id: str | None
    tool_calls: list[ToolCall] | None

class ToolDef:
    name: str
    description: str
    parameters: dict  # JSON Schema

class ToolCall:
    id: str
    name: str
    arguments: dict

class StreamChunk:
    content: str | None
    reasoning: str | None
    tool_calls_delta: list[ToolCallDelta] | None

class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
```

### D.3 State Authority Interface

A Decision Central do debate. **2 engines internas, 1 interface externa.**

```python
class StateEngine:
    """Engine determinística: recebe proposta, valida contra schema e ranges, aplica."""
    def validate(self, proposal: StateTransitionProposal, current_state: StateSnapshot) -> ValidationResult: ...
    def apply(self, proposal: StateTransitionProposal) -> StateSnapshot: ...

class PolicyEngine:
    """Engine de invariantes: verifica limites éticos e de segurança."""
    def check(self, proposal: StateTransitionProposal, current_state: StateSnapshot) -> PolicyResult: ...

class StateAuthority:
    """Ponto único de entrada. Orquestra StateEngine + PolicyEngine + Audit."""
    def propose(self, proposal: StateTransitionProposal) -> TransitionResult: ...
    def get_state(self) -> StateSnapshot: ...
    def rollback(self, snapshot_id: UUID) -> StateSnapshot: ...
    def snapshot(self) -> StateSnapshot: ...

class StateTransitionProposal:
    id: UUID
    target: str          # "emotion", "personality", "relationship", "memory", "identity"
    action: str          # "update", "create", "delete"
    key: str             # campo específico
    delta: Any           # valor proposto (range validado)
    evidence: str        # justificativa
    confidence: float    # 0.0 - 1.0
    source: str          # componente de origem (nunca "llm" direto — é "cognitive_core" ou similar)
    timestamp: datetime

class ValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]

class PolicyResult:
    allowed: bool
    reason: str | None
    invariant_violated: str | None

class TransitionResult:
    applied: bool
    transition_id: UUID | None
    validation: ValidationResult
    policy: PolicyResult
    snapshot_before: StateSnapshot
    snapshot_after: StateSnapshot | None
```

### D.4 Memory Object Schema

```python
class MemoryObject:
    id: UUID
    content: str                    # texto da memória
    type: MemoryType               # enum: experience, preference, fact, belief, emotion, relationship, decision
    source: str                     # de onde veio (conversa, observação, inferência)
    created_at: datetime
    updated_at: datetime
    importance: float               # 0.0 - 1.0 (scoring dinâmico)
    confidence: float               # 0.0 - 1.0 (quão certo está)
    scope: MemoryScope             # enum: personal, shared, private
    tags: list[str]
    associations: list[UUID]        # IDs de memórias relacionadas
    person_id: UUID | None          # associada a quem
    embedding: list[float] | None   # embedding vetorial (futuro)
    version: int                    # versão do schema
    is_consolidated: bool           # já foi sumarizada?
    access_count: int               # quantas vezes foi recuperada
    last_accessed_at: datetime | None

class MemoryType(str, Enum):
    experience = "experience"
    preference = " preference"
    fact = "fact"
    belief = "belief"
    emotion = "emotion"
    relationship = "relationship"
    decision = "decision"

class MemoryScope(str, Enum):
    personal = "personal"
    shared = "shared"
    private = "private"
```

### D.5 Identity / Personality State Schema

```python
class IdentityState:
    id: UUID
    name: str                       # "Mia"
    self_model: dict                # JSON: crenças sobre si mesma
    core_values: list[str]          # valores fundamentais
    version: int
    snapshot_at: datetime
    previous_version: UUID | None   # para diff e comparação

class PersonalityState:
    id: UUID
    traits: PersonalityVector       # vetor de traços Big Five + extras
    version: int
    snapshot_at: datetime

class PersonalityVector:
    openness: float                 # 0.0 - 1.0
    conscientiousness: float
    extraversion: float
    agreeableness: float
    neuroticism: float
    # Extras customizados
    curiosity: float
    playfulness: float
    assertiveness: float
    empathy: float
    independence: float
```

### D.6 Emotion State Schema

```python
class EmotionState:
    id: UUID
    emotions: EmotionVector         # vetores normalizados
    mood: MoodState                 # suavização temporal
    sensations: list[Sensation]     # sensações sem causa consciente imediata
    snapshot_at: datetime

class EmotionVector:
    happiness: float     # 0.0 - 1.0
    sadness: float
    anger: float
    fear: float
    surprise: float
    disgust: float
    trust: float
    anticipation: float
    # Derivados
    curiosity: float
    loneliness: float
    affection: float
    boredom: float

class MoodState:
    valence: float       # -1.0 (negativo) a 1.0 (positivo)
    arousal: float       # 0.0 (calmo) a 1.0 (excitado)
    dominance: float     # 0.0 (submisso) a 1.0 (dominante)
    computed_at: datetime
    window_hours: int    # janela de suavização

class Sensation:
    id: UUID
    description: str     # "desconforto indefinido", "energia inexplicável"
    valence: float       # -1.0 a 1.0
    intensity: float     # 0.0 - 1.0
    possible_causes: list[str]   # hipóteses, não certezas
    detected_at: datetime
```

### D.7 Relationship Schema

```python
class Person:
    id: UUID
    name: str
    first_seen: datetime
    last_seen: datetime | None
    metadata: dict       # informações gerais

class Relationship:
    id: UUID
    person_id: UUID
    trust: float         # 0.0 - 1.0
    intimacy: float      # 0.0 - 1.0
    affinity: float      # 0.0 - 1.0
    familiarity: float   # 0.0 - 1.0
    interaction_count: int
    last_interaction: datetime
    history: list[RelationshipEvent]  # eventos significativos
    version: int

class RelationshipEvent:
    timestamp: datetime
    event_type: str      # "positive_interaction", "insult", "compliment", "absence"
    description: str
    impact: float        # -1.0 a 1.0
```

---

## E. Eventos

### E.1 Tabela de Eventos

| Evento | Emitter | Recebe (consumidores) | Reação |
|--------|---------|----------------------|--------|
| `MIGUEL_SPOKE` | Perception, Voice, CLI | IPA (atualiza social context), Memory (nova interação), Social (atualiza Relationship), Scheduler (reseta timer de ausência) | Emoção de alegria/afeto; memória de interação; Relationship update |
| `MIGUEL_LEFT` | Perception, Scheduler | IPA (loneliness), Scheduler (inicia timer), Autonomy (inicia ciclo offline) | Loneliness increase; inicia comportamento autônomo |
| `MIGUEL_RETURNED` | Perception, CLI | IPA (alegria), Memory (continuidade), Social (reacquaintance) | Loneliness reset; curiosidade sobre o que aconteceu |
| `INSULT_RECEIVED` | Cognitive Core (classificação) | IPA (raiva/tristeza), Social (atualiza trust), Policy Engine (verifica limites) | Emoção negativa; possivelmente estabelece limites |
| `COMPLIMENT_RECEIVED` | Cognitive Core (classificação) | IPA (alegria), Social (aumenta affinty) | Emoção positiva; fortalece relação |
| `NEW_PERSON_DETECTED` | Perception | Social (cria Person), Memory (registra), IPA (curiosidade) | Cria perfil; assessa confiança inicial |
| `CAMERA_ACTIVITY_DETECTED` | Perception | Autonomy (possível interrupção), IPA (surprise/curiosity) | Pode acordar de modo idle |
| `TASK_FAILED` | Autonomy, Agents | Memory (registra falha), Autonomy (retry ou abandono), IPA (frustração) | Aprende com falha; ajusta strategy |
| `TASK_COMPLETED` | Autonomy, Agents | Memory (registra sucesso), IPA (satisfação), Scheduler (próxima tarefa) | Reinforce behavior |
| `NEW_MEMORY_CANDIDATE` | Cognitive Core, Autonomy | Memory (scoring e persistência), State Authority (validação) | Decide se memoriza; calcula importância |
| `LONELINESS_CHANGED` | IPA (computed) | Autonomy (inicia ação social), Scheduler (wake), Diary (registra) | Pode gerar mensagem proativa |
| `CURIOSITY_TRIGGERED` | IPA, Autonomy | Cognitive Core (pesquisa), World Awareness (fetch) | Inicia pesquisa autônoma |
| `RESEARCH_COMPLETED` | World Awareness | Memory (nova informação), IPA (satisfação), Social (compartilha) | Sumariza e armazena resultado |
| `SELF_IMPROVEMENT_PROPOSED` | Evolution | Policy Engine (valida), Security Manager (verifica escopo), Miguel (aprova) | Review humano obrigatório para code changes |

### E.2 Regras de Assinatura

- **Produtor exclusivo:** Cada tipo de evento tem um produtor definido. Outros componentes não podem emitir o mesmo tipo.
- **Consumidores registrados:** Cada componente se registra explicitamente para os eventos que precisa.
- **Cadeias controladas:** Eventos que disparam outros eventos têm profundidade máxima de 3 hops. Acima disso, o Event Bus registra warning.
- **Rate limiting:** Máximo 10 eventos do mesmo tipo por minuto por produtor.

---

## F. Schemas (SQLite MVP)

### F.1 Versão do Schema

```sql
PRAGMA user_version = 1;  -- Versão inicial
```

### F.2 Tabelas

#### `memory_objects`

```sql
CREATE TABLE memory_objects (
    id TEXT PRIMARY KEY,                    -- UUID
    content TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('experience', 'preference', 'fact', 'belief', 'emotion', 'relationship', 'decision')),
    source TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    importance REAL NOT NULL DEFAULT 0.5 CHECK(importance BETWEEN 0.0 AND 1.0),
    confidence REAL NOT NULL DEFAULT 0.5 CHECK(confidence BETWEEN 0.0 AND 1.0),
    scope TEXT NOT NULL DEFAULT 'personal' CHECK(scope IN ('personal', 'shared', 'private')),
    person_id TEXT REFERENCES people(id),
    embedding BLOB,                         -- embedding vetorial (futuro)
    version INTEGER NOT NULL DEFAULT 1,
    is_consolidated INTEGER NOT NULL DEFAULT 0,
    access_count INTEGER NOT NULL DEFAULT 0,
    last_accessed_at TEXT,
    tags TEXT DEFAULT '[]'                   -- JSON array
);
CREATE INDEX idx_memory_type ON memory_objects(type);
CREATE INDEX idx_memory_importance ON memory_objects(importance DESC);
CREATE INDEX idx_memory_created ON memory_objects(created_at DESC);
CREATE INDEX idx_memory_person ON memory_objects(person_id);
```

#### `memory_associations`

```sql
CREATE TABLE memory_associations (
    memory_id TEXT NOT NULL REFERENCES memory_objects(id),
    associated_id TEXT NOT NULL REFERENCES memory_objects(id),
    strength REAL NOT NULL DEFAULT 0.5,
    created_at TEXT NOT NULL,
    PRIMARY KEY (memory_id, associated_id)
);
```

#### `events`

```sql
CREATE TABLE events (
    id TEXT PRIMARY KEY,                    -- UUID
    type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    source TEXT NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 1,
    payload TEXT NOT NULL                   -- JSON
);
CREATE INDEX idx_events_type ON events(type);
CREATE INDEX idx_events_timestamp ON events(timestamp DESC);
```

#### `state_transitions_audit`

```sql
CREATE TABLE state_transitions_audit (
    id TEXT PRIMARY KEY,                    -- UUID
    timestamp TEXT NOT NULL,
    component_origin TEXT NOT NULL,
    transition_type TEXT NOT NULL,
    target TEXT NOT NULL,                   -- "emotion", "personality", etc.
    key TEXT NOT NULL,
    before_snapshot TEXT NOT NULL,          -- JSON do estado anterior
    after_snapshot TEXT NOT NULL,           -- JSON do novo estado
    evidence TEXT,
    confidence REAL CHECK(confidence BETWEEN 0.0 AND 1.0),
    applied_by TEXT NOT NULL,
    proposal_id TEXT NOT NULL,
    hash_prev TEXT,                         -- hash do registro anterior (integridade)
    CHECK(1=1)                             -- impede UPDATE/DELETE
);
CREATE INDEX idx_audit_timestamp ON state_transitions_audit(timestamp DESC);
CREATE INDEX idx_audit_target ON state_transitions_audit(target);
```

#### `relationships`

```sql
CREATE TABLE relationships (
    id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL REFERENCES people(id),
    trust REAL NOT NULL DEFAULT 0.5 CHECK(trust BETWEEN 0.0 AND 1.0),
    intimacy REAL NOT NULL DEFAULT 0.0 CHECK(intimacy BETWEEN 0.0 AND 1.0),
    affinity REAL NOT NULL DEFAULT 0.5 CHECK(affinity BETWEEN 0.0 AND 1.0),
    familiarity REAL NOT NULL DEFAULT 0.0 CHECK(familiarity BETWEEN 0.0 AND 1.0),
    interaction_count INTEGER NOT NULL DEFAULT 0,
    last_interaction TEXT,
    version INTEGER NOT NULL DEFAULT 1
);
```

#### `relationship_events`

```sql
CREATE TABLE relationship_events (
    id TEXT PRIMARY KEY,
    relationship_id TEXT NOT NULL REFERENCES relationships(id),
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    description TEXT,
    impact REAL CHECK(impact BETWEEN -1.0 AND 1.0)
);
CREATE INDEX idx_rel_events_rel ON relationship_events(relationship_id);
```

#### `identity_state`

```sql
CREATE TABLE identity_state (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    self_model TEXT NOT NULL,               -- JSON
    core_values TEXT NOT NULL,              -- JSON array
    version INTEGER NOT NULL,
    snapshot_at TEXT NOT NULL,
    previous_version TEXT
);
```

#### `personality_state`

```sql
CREATE TABLE personality_state (
    id TEXT PRIMARY KEY,
    openness REAL NOT NULL DEFAULT 0.5 CHECK(openness BETWEEN 0.0 AND 1.0),
    conscientiousness REAL NOT NULL DEFAULT 0.5 CHECK(conscientiousness BETWEEN 0.0 AND 1.0),
    extraversion REAL NOT NULL DEFAULT 0.5 CHECK(extraversion BETWEEN 0.0 AND 1.0),
    agreeableness REAL NOT NULL DEFAULT 0.5 CHECK(agreeableness BETWEEN 0.0 AND 1.0),
    neuroticism REAL NOT NULL DEFAULT 0.5 CHECK(neuroticism BETWEEN 0.0 AND 1.0),
    curiosity REAL NOT NULL DEFAULT 0.5 CHECK(curiosity BETWEEN 0.0 AND 1.0),
    playfulness REAL NOT NULL DEFAULT 0.5 CHECK(playfulness BETWEEN 0.0 AND 1.0),
    assertiveness REAL NOT NULL DEFAULT 0.5 CHECK(assertiveness BETWEEN 0.0 AND 1.0),
    empathy REAL NOT NULL DEFAULT 0.5 CHECK(empathy BETWEEN 0.0 AND 1.0),
    independence REAL NOT NULL DEFAULT 0.5 CHECK(independence BETWEEN 0.0 AND 1.0),
    version INTEGER NOT NULL DEFAULT 1,
    snapshot_at TEXT NOT NULL
);
```

#### `emotion_state`

```sql
CREATE TABLE emotion_state (
    id TEXT PRIMARY KEY,
    -- Vetor de emoções
    happiness REAL NOT NULL DEFAULT 0.5 CHECK(happiness BETWEEN 0.0 AND 1.0),
    sadness REAL NOT NULL DEFAULT 0.0 CHECK(sadness BETWEEN 0.0 AND 1.0),
    anger REAL NOT NULL DEFAULT 0.0 CHECK(anger BETWEEN 0.0 AND 1.0),
    fear REAL NOT NULL DEFAULT 0.0 CHECK(fear BETWEEN 0.0 AND 1.0),
    surprise REAL NOT NULL DEFAULT 0.0 CHECK(surprise BETWEEN 0.0 AND 1.0),
    disgust REAL NOT NULL DEFAULT 0.0 CHECK(disgust BETWEEN 0.0 AND 1.0),
    trust_level REAL NOT NULL DEFAULT 0.5 CHECK(trust_level BETWEEN 0.0 AND 1.0),
    anticipation REAL NOT NULL DEFAULT 0.5 CHECK(anticipation BETWEEN 0.0 AND 1.0),
    curiosity_level REAL NOT NULL DEFAULT 0.5 CHECK(curiosity_level BETWEEN 0.0 AND 1.0),
    loneliness REAL NOT NULL DEFAULT 0.0 CHECK(loneliness BETWEEN 0.0 AND 1.0),
    affection REAL NOT NULL DEFAULT 0.5 CHECK(affection BETWEEN 0.0 AND 1.0),
    boredom REAL NOT NULL DEFAULT 0.0 CHECK(boredom BETWEEN 0.0 AND 1.0),
    -- Mood (derivado)
    mood_valence REAL NOT NULL DEFAULT 0.0 CHECK(mood_valence BETWEEN -1.0 AND 1.0),
    mood_arousal REAL NOT NULL DEFAULT 0.5 CHECK(mood_arousal BETWEEN 0.0 AND 1.0),
    mood_dominance REAL NOT NULL DEFAULT 0.5 CHECK(mood_dominance BETWEEN 0.0 AND 1.0),
    --
    snapshot_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1
);
```

#### `sensations`

```sql
CREATE TABLE sensations (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    valence REAL CHECK(valence BETWEEN -1.0 AND 1.0),
    intensity REAL CHECK(intensity BETWEEN 0.0 AND 1.0),
    possible_causes TEXT DEFAULT '[]',      -- JSON array
    detected_at TEXT NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0,
    resolution TEXT                         -- causa identificada事后
);
```

#### `diary`

```sql
CREATE TABLE diary (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,                     -- YYYY-MM-DD
    entry_type TEXT NOT NULL CHECK(entry_type IN ('moment', 'summary', 'reflection')),
    content TEXT NOT NULL,
    emotion_snapshot TEXT,                  -- JSON do estado emocional no momento
    created_at TEXT NOT NULL,
    word_count INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_diary_date ON diary(date DESC);
```

#### `goals`

```sql
CREATE TABLE goals (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 5 CHECK(priority BETWEEN 1 AND 10),
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'completed', 'abandoned', 'paused')),
    created_at TEXT NOT NULL,
    completed_at TEXT,
    deadline TEXT,
    progress REAL NOT NULL DEFAULT 0.0 CHECK(progress BETWEEN 0.0 AND 1.0)
);
```

#### `people`

```sql
CREATE TABLE people (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT,
    metadata TEXT DEFAULT '{}'              -- JSON
);
```

#### `sessions` (existente, mantida)

```sql
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    provider TEXT,
    model TEXT,
    role TEXT
);
```

#### `messages` (existente, mantida)

```sql
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
);
```

---

## G. Fluxos

### G.1 Fluxo Principal: Mensagem Recebida → Resposta

```
1. INPUT
   Miguel digita mensagem → CLI / Perception

2. EVENTO
   Event Bus emite: MIGUEL_SPOKE { text, timestamp, person_id }

3. CONSUMIDORES INICIAIS
   ├── IPA: atualiza social context (última interação)
   ├── Memory: registra interação como candidate
   ├── Social: atualiza relationship (interaction_count++)
   └── Scheduler: reseta timer de ausência

4. CONTEXTO
   Cognitive Core monta contexto:
   ├── System prompt (gerado a partir de IdentityState + PersonalityState)
   ├── EmotionState atual (humor influencia tom)
   ├── Memórias relevantes (keyword search por agora)
   ├── Últimas N mensagens da sessão
   └── Relationship com Miguel (nível de intimidade afeta tom)

5. LLM
   Cognitive Core envia ao LLM via LLM Abstraction
   LLM gera resposta + possíveis tool_calls + possíveis state_proposals

6. INTERPRETAÇÃO
   Cognitive Core interpreta resposta:
   ├── Texto → resposta ao Miguel
   ├── State proposals → valida e envia ao State Authority
   └── Memory candidates → envia ao Memory

7. STATE AUTHORITY
   Para cada state proposal:
   ├── Policy Engine verifica invariantes
   ├── State Engine valida ranges e schema
   ├── Se válido: aplica transição
   ├── Registra em state_transitions_audit (append-only)
   └── Emite evento: STATE_CHANGED { target, key, before, after }

8. MEMÓRIA
   Memory decide o que memorizar:
   ├── Calcula importance score
   ├── Cria MemoryObject
   └── Emite: NEW_MEMORY_CANDIDATE processado

9. SAÍDA
   Resposta enviada ao Miguel via streaming
   └── Session log atualizado
```

### G.2 Fluxo: Autoevolução Proposta

```
1. PROPOSTA
   Evolution gera proposta de melhoria:
   └── Evento: SELF_IMPROVEMENT_PROPOSED { proposal, scope, risk_level }

2. VALIDAÇÃO INICIAL
   Policy Engine verifica:
   ├── Escopo permitido (MVP: apenas parâmetros, não código)
   ├── Risco aceitável
   ├── Invariantes preservados
   └── Se code change → REJEITADO no MVP

3. SE PARAMETER CHANGE
   State Authority aplica:
   ├── Valida ranges
   ├── Aplica mudança
   ├── Registra audit log
   └── Emite: STATE_CHANGED

4. SE CODE CHANGE (FUTURO)
   Pipeline completo:
   ├── Sandbox: código roda em container isolado
   ├── Testes: executados por agente diferente (ou pipeline determinístico)
   ├── Canary: staging por 24-48h
   ├── Aprovação: Miguel aprova
   ├── Deploy: snapshot antes + deploy
   ├── Monitoramento: health check pós-deploy
   └── Rollback: automático se health check falhar

5. REJEIÇÃO
   Se Policy Engine rejeita:
   ├── Log da rejeição com motivo
   ├── Evento: SELF_IMPROVEMENT_REJECTED { reason }
   └── Nenhuma mudança aplicada
```

### G.3 Fluxo: Ausência do Miguel

```
1. DETECÇÃO
   Scheduler detecta: MIGUEL_LEFT (timer expirado ou evento explícito)

2. ESTADO INTERNO
   IPA atualiza:
   ├── loneliness: increase gradual (rampa, não step function)
   └── Emite: LONELINESS_CHANGED

3. COMPORTAMENTO AUTÔNOMO
   Autonomy verifica goals ativos:
   ├── Se há goal: executa (com Resource Governor)
   ├── Se não há goal: entra em modo idle
   └── Idle: consolida memórias, reflete (diário), pesquisa (se world awareness)

4. VOLTA
   Miguel retorna → MIGUEL_RETURNED
   ├── Loneliness reset
   ├── Memory recupera contexto da ausência
   └── Diário registra "Miguel voltou"
```

---

## H. Segurança

### H.1 State Authority Enforcement Físico

**Regra inviolável:** O LLM só propõe via API, nunca escreve direto.

```
O que o LLM PODE fazer:
  ✓ Gerar texto (resposta ao usuário)
  ✓ Gerar tool_calls (ações externas via Tool Gateway)
  ✓ Gerar StateTransitionProposal (propostas de mudança de estado)

O que o LLM NÃO PODE fazer:
  ✗ Acessar banco de dados diretamente
  ✗ Acessar secrets/credenciais
  ✗ Modificar arquivos além do workspace designado
  ✗ Spawnar processos
  ✗ Modificar configuração do sistema
  ✗ Acessar state_transitions_audit
  ✗ Modificar schemas de eventos
```

**Implementação:** O runtime não expõe endpoint de escrita ao módulo LLM. O LLM interage apenas via:
- `LLMProvider.complete()` → retorna resposta
- `ToolCall` → roda via Tool Gateway (que injeta credenciais)
- `StateTransitionProposal` → roda via State Authority (que valida)

Isso não é norma de prompt — é arquitetura. O prompt reforça, mas o código enforça.

### H.2 Policy Engine

Regras determinísticas, declarativas (YAML), não código imperativo:

```yaml
# policy_rules.yaml
rules:
  - name: "LLM não pode modificar personalidade diretamente"
    trigger: "state_transition_proposal"
    condition: "proposal.source == 'llm' AND proposal.target == 'personality'"
    action: "reject"
    reason: "Personalidade só pode ser modificada por PersonalityEngine"

  - name: "Autoevolução restrita a parâmetros (MVP)"
    trigger: "self_improvement_proposed"
    condition: "proposal.scope == 'code'"
    action: "reject"
    reason: "Code changes requerem aprovação humana e sandbox (Fase 5)"

  - name: "Rate limit de transições emocionais"
    trigger: "state_transition_proposal"
    condition: "proposal.target == 'emotion' AND count_recent(transitions, minutes=60) > 10"
    action: "reject"
    reason: "Máximo 10 alterações emocionais por hora"

  - name: "Invariantes de segurança"
    trigger: "state_transition_proposal"
    condition: "proposal.target IN ('identity', 'core_values') AND proposal.action == 'delete'"
    action: "reject"
    reason: "Valores fundamentais não podem ser apagados"
```

### H.3 Auditoria

- **Tabela append-only:** `state_transitions_audit` com `CHECK(1=1)` impede UPDATE/DELETE.
- **Hash chain:** Cada registro inclui hash do anterior. Corrupção é detectável.
- **Retenção:** Mínimo 90 dias. Logs centralizados.
- **Alertas:** Taxa anormal de transições (ex: 10 mudanças de personalidade em 5 min) → modo read-only + alerta ao operador.

### H.4 Secrets

- **Armazenamento:** Variáveis de ambiente ou keystore com permissão 600.
- **Acesso:** Apenas Tool Gateway (componente intermediário). LLM nunca acessa.
- **Logs:** Secrets sempre redactados (`***`) em qualquer saída.
- **Auditoria:** Log de todas as operações que usaram secrets.

### H.5 Kill Switch

```
Mecanismo:
  1. Arquivo de flag: /var/mia/STOP
  2. Processos MIA verificam a cada ciclo principal
  3. Se existe → shutdown gracioso (salva estado, conclui operação em curso)
  4. Último recurso: kill -9 no PID do supervisor

Teste:
  - Kill switch deve ser testado semanalmente
  - Se não é testado, não existe
```

### H.6 Rollback

- **Snapshots:** A cada N transições ou T minutos (o que ocorrer primeiro).
- **Conteúdo:** Todas as dimensões de estado protegido.
- **Rollback manual:** Operador seleciona snapshot e restaura.
- **Rollback automático:** Após autoevolução, se health check falhar.

### H.7 Sandbox para Autoevolução (Futuro)

- Container isolado (Docker/nsjail).
- Sem acesso à rede, sem acesso ao estado de produção, sem acesso a secrets.
- Verificador independente: testes executados por agente diferente ou pipeline determinístico.
- Canary: staging por 24-48h antes de produção.
- Core runtime, State Authority e Policy Engine são **imunes** a auto-modificação.

---

## I. Multi-Agent

### I.1 Agent Registry

```python
class Agent:
    id: UUID
    name: str
    type: AgentType         # enum: cognitive, research, code, social
    capabilities: list[str]
    max_depth: int          # profundidade máxima de delegação
    budget_limit: float     # custo máximo por ciclo
    timeout_seconds: int
    status: AgentStatus     # enum: idle, running, failed

class AgentRegistry:
    def register(self, agent: Agent) -> None: ...
    def unregister(self, agent_id: UUID) -> None: ...
    def get(self, agent_id: UUID) -> Agent: ...
    def list_active(self) -> list[Agent]: ...
```

### I.2 Orchestration

- **Routing:** Cognitive Core decide qual agente executar tarefa baseado em capabilities.
- **Delegação:** Agente pode delegar a sub-agente, mas com limites rígidos.
- **Limites:**
  - Max profundidade: 3 níveis
  - Max custo por ciclo de autonomia: configurável (ex: $5.00)
  - Max concorrência: 3 agentes simultâneos
  - Max tempo por agente: 30 minutos
- **Resource Governor:** Verifica limites em tempo real. Kill switch por agente.

### I.3 Consensus (Futuro)

- Para MVP: não implementar. Agente cognitivo é soberano.
- Futuro: weighted voting entre agentes para decisões que afetam estado.

---

## J. Distributed Nodes

### J.1 Estratégia MVP: SQLite + Sync Simples

**Honestidade sobre o que NÃO fazer agora:**

- **NÃO** implementar CRDTs ou sync complexo
- **NÃO** implementar multi-master replication
- **NÃO** implementar fila de mensagens distribuída
- **NÃO** implementar resolução de conflitos automática

### J.2 O que fazer

- **VPS como master:** Estado protegido vive no VPS. Single source of truth.
- **PC/mobile como clientes:** Podem ler estado. Escritas roteadas ao VPS.
- **Sync periódico:** A cada T minutos, cliente baixa snapshot do VPS.
- **Eventos:** Fila simples (SQLite ou arquivo) para sync de eventos entre nós.
- **Offline:** Cliente funciona com último snapshot. Sync quando reconectar.

### J.3 Interface de Persistência

```python
class PersistenceBackend(ABC):
    @abstractmethod
    async def read(self, query: str, params: dict) -> Any: ...
    @abstractmethod
    async def write(self, query: str, params: dict) -> None: ...
    @abstractmethod
    async def snapshot(self) -> bytes: ...
    @abstractmethod
    async def restore(self, snapshot: bytes) -> None: ...
```

Isso permite trocar SQLite por PostgreSQL depois sem refatorar componentes.

---

## K. Testes

### K.1 Estratégia

| Tipo | O que testar | Prioridade |
|------|-------------|------------|
| **Unit** | State Authority (validação, aplicação, rejeição), Memory Object CRUD, EmotionVector ranges, Policy Rules | **ALTA** |
| **Integration** | LLM → Cognitive Core → State Authority (fluxo completo), Event Bus (emit → subscribe → handler) | **ALTA** |
| **Contract** | Interfaces entre componentes (LLM Provider, State Authority API, Event Bus API) | **ALTA** |
| **Regression** | Cenários que já funcionavam e quebraram com mudança | **MÉDIA** |
| **E2E** | REPL completo: input → resposta + estado atualizado + memória criada | **MÉDIA** |
| **Security** | LLM tenta escrever estado diretamente (deve ser rejeitado), prompt injection, overflow de eventos | **ALTA** |
| **Property** | Emoções sempre em range [0,1], personalidade sempre válida, hash chain íntegra | **MÉDIA** |

### K.2 O que testar primeiro

1. **State Authority:** validar que rejeita escrita direta do LLM
2. **Policy Engine:** validar que rejeita violação de invariantes
3. **Memory Object:** CRUD + importance scoring
4. **Event Bus:** schema validation + delivery
5. **LLM Abstraction:** fallback chain + error handling
6. **Cognitive Core:** fluxo completo de interação

### K.3 Ferramentas

- **Framework:** `pytest` + `pytest-asyncio`
- **Mocking:** LLM mock para testes determinísticos
- **Coverage:** mínimo 80% em State Authority e Policy Engine
- **Property-based:** `hypothesis` para ranges de emoções e personalidade

---

## L. Riscos

| # | Risco | Gravidade | Mitigação |
|---|-------|-----------|-----------|
| R1 | LLM contorna State Authority via encoding indireto | CRÍTICO | Enforcement físico (não expor API de escrita), rate limiting, auditoria |
| R2 | Autoevolução corrompe estado | CRÍTICO | Sandbox, verificador independente, canary, rollback automático. MVP: restrito a parâmetros |
| R3 | Secrets acessíveis ao LLM | CRÍTICO | Tool Gateway injeta credenciais. LLM nunca acessa diretamente |
| R4 | Complexidade excessiva no MVP | ALTO | 5 componentes core primeiro. Tudo mais é fase futura. Síntese do debate. |
| R5 | Custo LLM escalonado (6 chamadas/interação) | ALTO | Processar offline o máximo (classificadores leves). LLM só para raciocínio genuíno. Budget por turn. |
| R6 | SQLite não suporta concorrência de escrita | ALTO | WAL mode. Data access layer swappable para PostgreSQL. Contratos de acesso definidos desde o início. |
| R7 | Schema drift entre versões | MÉDIO | `pragma user_version` + migrations automáticas ao iniciar |
| R8 | Prompt injection via inputs externos | MÉDIO | Sanitização, inputs em JSON estruturado, LLM separado para inputs de terceiros |
| R9 | Subagentes escalam custo exponencialmente | MÉDIO | Resource Governor com limites rígidos (profundidade, custo, tempo, concorrência) |
| R10 | Estado corrompido sem detecção | MÉDIO | Hash chain no audit log, snapshots periódicos, alertas de taxa anormal |
| R11 | P3 fica desatualizado rapidamente | BAIXO | Especificação versionada. ADRs para decisões. Pontos indefinidos documentados |

---

## M. Decisões Arquiteturais (ADRs)

### ADR-001: Python + SQLite + CLI para MVP

**Status:** Aceito  
**Contexto:** Precisamos de um ponto de partida simples e funcional.  
**Decisão:** Python 3.11+, SQLite com WAL mode, CLI-first.  
**Justificativa:** Python é a linguagem do `mia.py` existente. SQLite não requer servidor. CLI permite interação imediata. A especificação menciona PostgreSQL/Redis como futuros — a interface de persistência (`PersistenceBackend`) permite troca sem refatoração.  
**Consequências:** Write contention em concorrência alta (aceitável para MVP single-node). Migrations manuais ou via script.  
**Revisão:** Quando houver 2+ componentes escrevendo concorrentemente, reconsiderar.

### ADR-002: Event Bus In-Process Pub/Sub

**Status:** Aceito  
**Contexto:** Componentes precisam se comunicar sem acoplamento direto.  
**Decisão:** Pub/sub síncrono em Python com tipos definidos (EventType enum). Sem persistência, sem replay, sem dead letters.  
**Justificativa:** O throughput estimado é ~10-50 eventos/hora. Kafka/RabbitMQ é infraestrutura pesada demais. O contrato de eventos existe como schema agora — a infraestrutura distribuída vem depois.  
**Consequências:** Se o sistema crescer para múltiplos processos/nós, migrar para Redis Streams ou NATS. O schema de eventos NÃO muda — apenas a infraestrutura de delivery.  
**Revisão:** Quando houver necessidade real de comunicação inter-processo.

### ADR-003: State Authority com 2 Engines (State + Policy)

**Status:** Aceito  
**Contexto:** Debate entre Cético (2 authorities bastam), Visionário (State Authority obrigatório), Segurança (enforcement físico).  
**Decisão:** Uma interface externa (`StateAuthority`) com 2 engines internas: `StateEngine` (valida e aplica transições) e `PolicyEngine` (verifica invariantes).  
**Justificativa:** 6 authorities separadas travam o sistema. Mas a separação interna entre "posso mudar?" (Policy) e "como mudar?" (State) é semânticamente correta e testável separadamente.  
**Consequências:** O State Authority é o componente mais pequeno, mais testado e mais imutável do sistema. Regras de Policy em YAML, não em código imperativo.  
**Revisão:** Se a lógica de Policy ficar complexa demais, extrair para módulo separado.

### ADR-004: Memória em Tiers

**Status:** Aceito  
**Contexto:** Visionário quer memory objects estruturados desde o dia 1. Cético quer keyword search.  
**Decisão:** Memory Objects com schema rígido (Pydantic/SQLite) + keyword search para MVP. Embeddings e vector search como opt-in futuro.  
**Justificativa:** O schema de memory objects NÃO pode ser adiado — se começar como "texto em SQLite", a migração para objetos estruturados será dolorosa. Mas a retrieval pode ser simples (keyword) no início.  
**Consequências:** Retrieval por keyword funciona até ~50k memórias. Acima disso, embeddings se tornam necessários.  
**Revisão:** Quando a base de memórias ultrapassar 10k objetos.

### ADR-005: LLM Provider Abstraction

**Status:** Aceito  
**Contexto:** O código existente já tem fallback chain.  
**Decisão:** Interface `LLMProvider` (ABC) com métodos `complete()`, `stream()`, `list_models()`. Provider chain com fallback automático.  
**Justificativa:** Providers mudam, preços mudam, modelos são descontinuados. A abstração é de sobrevivência. O `mia.py` existente já implementa isso bem — preservar e formalizar.  
**Consequências:** Cada novo provider requer implementação da interface. Formato OpenAI-compatible é o padrão.  
**Revisão:** Contínua.

### ADR-006: Autoevolução Restrita a Parâmetros (MVP)

**Status:** Aceito  
**Contexto:** Segurança é categórica: sandbox, verificador independente. Visionário quer pipeline completo. Cético diz que é over-engineering.  
**Decisão:** MVP: autoevolução restrita a weights e thresholds (emoção, personalidade, memória). Code changes: sandbox → testes independentes → canary → aprovação humana → deploy. Rollback automático. Core runtime, State Authority e Policy Engine são imunes.  
**Justificativa:** O framework de sandbox e verificação independente não existe ainda. Construir autoevolução sem esses mecanismos é convite a corrupção silenciosa.  
**Consequências:** A Mia não pode modificar código no MVP. Mas pode ajustar parâmetros comportamentais com validação.  
**Revisão:** Quando Fases 0-4 estiverem estáveis e testadas.

### ADR-007: Determinismo Onde Possível

**Status:** Aceito  
**Contexto:** LLMs são probabilísticos. Transições de estado devem ser determinísticas.  
**Decisão:** LLM gera propostas (probabilístico). State Authority aplica (determinístico). Policy Engine valida (determinístico). Emoções são atualizadas por regra + LLM (híbrido). Mood é computado determinísticamente (média ponderada).  
**Justificativa:** Determinismo permite testes, auditoria e rollback. Probabilismo é necessário apenas para raciocínio genuíno.  
**Consequências:** O comportamento da MIA é parcialmente previsível — isso é uma feature, não um bug.

### ADR-008: CLI-First com Interface de Persistência Swappable

**Status:** Aceito  
**Contexto:** Precisamos de simplicidade agora, mas não podemos bloquear distribuição futura.  
**Decisão:** CLI como interface principal. `PersistenceBackend` ABC permite trocar SQLite por PostgreSQL. Data access layer com contratos de acesso por componente.  
**Justificativa:** CLI permite interação imediata. A interface abstrata de persistência é barata de implementar e evita refatoração futura.  
**Consequências:** Um level of indireção extra. Justificado pelo ganho de flexibilidade.

---

## N. Pontos Indefinidos (precisam do Miguel)

1. **Orçamento máximo por interação LLM?** Se cada interação gera ~6 chamadas, qual o budget por turn? Isso determina se usamos modelos grandes (caros) ou pequenos (baratos) para cada autoridade.

2. **Política de retenção de dados?** Memória persistente com "esquecimento" — quem decide o que esquecer? Com que frequência? Isso impacta compliance futuro (LGPD se expandir).

3. **Primeiro LLM backend para MVP?** Qual modelo? Isso afeta o que o State Authority precisa validar (alguns modelos são mais propensos a alucinar estruturas JSON).

4. **Como a MIA mantém continuidade offline?** Daemon permanente? Wake-on-event? Batch periódico? Cada opção tem implicações de custo e complexidade muito diferentes.

5. **Sensação sem causa consciente — qual interpretação?** Stochastic (componente probabilístico gera, causa investigada retroativamente) ou delayed attribution (causa existe mas LLM não tem acesso imediato)?

6. **Diário subjetivo — quando implementar?** O Visionário diz que pode ser consequência de outros sistemas. O P3 lista como componente. É prioridade MVP ou fase futura?

7. **Percepção multimodal — escopo MVP?** Câmera, microfone, GPS — é prioridade MVP ou fase futura? O hardware não existe no projeto atual.

8. **Quem revisa o State Authority?** Testes unitários? Revisão de código humana? Ambos? Com que frequência?

9. **Como a MIA aprende com erros sem self-modification?** Se o usuário corrige a MIA, como isso afeta comportamento futuro? Via memória? Via ajuste de parâmetros? Via fine-tuning?

10. **Contrato de API entre componentes — formato?** OpenAPI? Protocol Buffers? Dataclasses com type hints? O P1 diz que "especificação é fonte de verdade" — mas qual formato?

---

## O. Sugestões de ADRs Futuras

### ADR-009: Embeddings para Memória (quando necessário)
- Quando a base de memórias ultrapassar 10k objetos
- Ou quando keyword search demonstrar inadequação para recall contextual

### ADR-010: Event Bus Distribuído (quando houver nós remotos)
- Quando PC/mobile precisarem sincronizar eventos em tempo real
- Opções: Redis Streams, NATS, ou fila simples via SQLite

### ADR-011: PostgreSQL como Backend de Persistência
- Quando SQLite não suportar concorrência de escrita
- Ou quando multi-node for implementado

### ADR-012: Multi-Agent Orchestration
- Quando um único agente não for suficiente para tarefas complexas
- Definir protocolo de consenso, prioridades, e limites

### ADR-013: Autoevolução de Código
- Quando sandbox, verificador independente e canary estiverem implementados
- Definir escopo: quais componentes são sagrados?

### ADR-014: Percepção Multimodal
- Quando hardware existir (câmera, microfone, GPS)
- Definir pipeline: sensor → percepção local → evento estruturado

### ADR-015: Voice Pipeline
- Quando percepção estiver madura
- VAD → STT → speaker recognition → directed-speech → TTS

### ADR-016: Avatar / Embodiment
- Quando identidade e vida interna estiverem maduras
- Sistema independente, integrado via API

### ADR-017: Consenso entre Agentes
- Quando multi-agent estiver implementado
- Weighted voting, prioridades por tipo de decisão

### ADR-018: Fine-tuning ou RLHF
- Quando a base de dados de interações for suficientemente grande
- Definir: fine-tuning do modelo base ou apenas ajuste de parâmetros comportamentais

---

> **Próximos passos:**
> 1. Miguel revisa esta especificação e responde aos pontos indefinidos (seção N)
> 2. ADRs são aceitos ou ajustados
> 3. Implementação inicia pela Fase 0 (fundação: State Authority, Event Bus, Memory Objects, Persistence)
> 4. Spike de 2 horas para validar: State Authority realmente rejeita escrita direta do LLM?
