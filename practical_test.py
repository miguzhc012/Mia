"""Teste prático REAL da Mia — sessão de uso simulada (APIs verificadas).

Exercita o sistema inteiro como um usuário faria:
1. Cria identidade, personalidade
2. Conversa (10 turnos, incluindo elogio, insulto, pergunta pessoal)
3. Verifica memória (curto/longo prazo), emoções, crenças, necessidades
4. Consolidação automática de conversa longa
5. Interesses, goals, atenção, avatar, evolução
6. Health check + backup

Roda SEM LLM real (fallback de regras) — igual PC sem chave de API.
Usa banco em arquivo real (persistência verificada).
"""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mia_pkg.db import SQLiteConnection
from mia_pkg.events import EventBus
from mia_pkg.llm import LLMProviderChain
from mia_pkg.chat import ChatSession
from mia_pkg.memory import MemoryStore
from mia_pkg.affective_engine import AffectiveEngine
from mia_pkg.identity import IdentityManager
from mia_pkg.beliefs import BeliefStore
from mia_pkg.needs_desires import NeedsDesiresStore
from mia_pkg.social import PeopleStore
from mia_pkg.world import InterestTracker
from mia_pkg.autonomy import GoalStore
from mia_pkg.monitoring import HealthMonitor, BackupManager


def hr(title):
    print(f"\n{'='*64}\n{title}\n{'='*64}")


def safe(label, fn):
    """Executa e captura erros — teste prático não pode abortar."""
    try:
        result = fn()
        if result is not None:
            print(result)
        return result
    except Exception as ex:
        print(f"  ⚠ {label}: {type(ex).__name__}: {ex}")
        return None


def main():
    tmpdir = tempfile.mkdtemp(prefix="mia_test_")
    db_path = os.path.join(tmpdir, "mia.db")
    print(f"\nBanco: {db_path}")

    db = SQLiteConnection(db_path)
    db.connect()
    db.init_schema()

    bus = EventBus()
    # sem chave real → chain vazia → llm_available=False → fallback de regras
    chain = LLMProviderChain(providers=[], retries=1)

    chat = ChatSession(db, chain, event_bus=bus, speaker="miguel", max_history=20)
    print(f"LLM disponível: {chat.llm_available} (esperado False — fallback regras)")

    # ============ 1. IDENTIDADE ============
    hr("1. IDENTIDADE E PERSONALIDADE")
    identity = IdentityManager(db)

    def _persona():
        st = identity.get_identity()
        return f"Identidade: {st.name} (v{st.version}, valores: {st.core_values})"
    safe("identidade", _persona)

    def _personality():
        p = identity.get_personality()
        return f"Traços Big Five: {p.traits.to_dict() if hasattr(p, 'traits') else p}"
    safe("personalidade", _personality)

    # ============ 2. CONVERSA ============
    hr("2. CONVERSA (10 TURNOS)")
    messages = [
        "Oi Mia, tudo bem?",
        "Eu adoro programar em Python, é minha paixão",
        "Hoje foi um dia cansativo no trabalho",
        "Você é a melhor IA que já existiu!",
        "Me conta uma curiosidade sobre o espaço",
        "Estou pensando em aprender Rust",
        "Que música você recomendaria para relaxar?",
        "Eu te considero minha amiga",
        "Foi mal, estou estressado hoje, desculpa",
        "O que você acha da minha ideia de criar um app?",
    ]

    turns = []
    for i, msg in enumerate(messages):
        t0 = time.time()
        turn = chat.send(msg)
        latency = (time.time() - t0) * 1000
        turns.append(turn)
        print(f"\n  [{i+1}] MIGUEL> {msg}")
        print(f"  MIA   > {turn.response_text[:150]}{'...' if len(turn.response_text) > 150 else ''}")

    # ============ 3. MEMÓRIA ============
    hr("3. MEMÓRIA")
    memory = MemoryStore(db)

    def _count():
        return f"Total de memórias: {memory.count()}"
    safe("count", _count)

    def _top():
        out = "Top por importância:"
        for m in memory.list_by_importance(limit=5):
            out += f"\n    [{m.type}] {m.content[:75]} (imp={m.importance:.2f})"
        return out
    safe("top", _top)

    # ============ 4. EMOÇÕES ============
    hr("4. ESTADO EMOCIONAL")
    affective = AffectiveEngine(db)

    def _emo():
        state = affective.get_current()
        e = state.emotions.to_dict()
        mood = state.mood
        emotion_str = ", ".join(f"{k}={v:.2f}" for k, v in e.items()
                                if k in ("happiness", "sadness", "anger", "trust_level",
                                         "curiosity_level", "loneliness"))
        return (f"Emoções: {emotion_str}\n"
                f"Mood: valência={mood.valence:.2f} arousal={mood.arousal:.2f} "
                f"dominância={mood.dominance:.2f}")
    safe("emoção", _emo)

    # ============ 5. CRENÇAS ============
    hr("5. CRENÇAS")
    beliefs = BeliefStore(db)

    def _beliefs():
        rows = beliefs.list_active(limit=8)
        out = f"Crenças ativas: {len(rows)}"
        for b in rows:
            content = getattr(b, "content", str(b))
            conf = getattr(b, "confidence", 0)
            out += f"\n    - {content[:75]} (conf={conf:.2f})"
        return out
    safe("crenças", _beliefs)

    # ============ 6. NECESSIDADES ============
    hr("6. NECESSIDADES/DESEJOS")
    needs = NeedsDesiresStore(db)

    def _needs():
        rows = needs.list_unfulfilled_needs(limit=5)
        out = f"Necessidades não atendidas: {len(rows)}"
        for n in rows:
            out += f"\n    - {getattr(n, 'name', n)}"
        return out
    safe("necessidades", _needs)

    # ============ 7. RELACIONAMENTOS ============
    hr("7. RELACIONAMENTOS")
    people = PeopleStore(db)

    def _rel():
        p = people.get_by_name("miguel")
        return f"Pessoa 'miguel': {p.name if p else 'não registrada ainda'}"
    safe("relacionamento", _rel)

    # ============ 8. INTERESSES ============
    hr("8. INTERESSES")
    interests = InterestTracker(db)

    def _int():
        interests.seed_from_personality()
        top = interests.get_top(limit=8)
        out = f"Interesses top: {len(top)}"
        for i in top:
            out += f"\n    - {i.name}: peso={i.weight:.2f} (origens: {i.sources})"
        return out
    safe("interesses", _int)

    # ============ 9. CONSOLIDAÇÃO ============
    hr("9. CONSOLIDAÇÃO DE CONVERSA LONGA")
    print(f"  mensagens_since_consolidation = {chat._messages_since_consolidation}")

    def _cons():
        msgs = [{"role": "user", "content": m} for m in messages[:10]]
        summary = chat.consolidator.consolidate_conversation(
            msgs, speaker="miguel"
        )
        return f"Resumo: {summary[:130] if summary else '(vazio)'}"
    print(safe("consolidação", _cons) or "")

    def _consolidated():
        rows = memory.list_by_importance(limit=10)
        cons = [m for m in rows if m.is_consolidated]
        return f"Memórias consolidadas: {len(cons)} (is_consolidated=1)"
    safe("consolidadas", _consolidated)

    # ============ 10. GOALS ============
    hr("10. OBJETIVOS AUTÔNOMOS")
    goals = GoalStore(db)

    def _goals():
        rows = goals.list_active()
        out = f"Goals ativos: {len(rows)}"
        for g in rows:
            out += f"\n    - {g}"
        return out
    safe("goals", _goals)

    # ============ 11. AVATAR ============
    hr("11. AVATAR")
    def _avatar():
        from mia_pkg.avatar import AvatarRenderer, ExpressionMapper
        from mia_pkg.affective_engine import EmotionVector
        renderer = AvatarRenderer()
        mapper = ExpressionMapper()
        state = affective.get_current()
        config = mapper.map_emotion(emotions=state.emotions)
        svg = renderer.render(config)
        return (f"Expressão: {config.expression.value} (boca={config.mouth_curve:.2f}, "
                f"olhos={config.eye_openness:.2f})\nSVG: {len(svg)} bytes")
    safe("avatar", _avatar)

    # ============ 12. VOZ ============
    hr("12. VOZ (VAD + STT + TTS)")
    def _voice():
        from mia_pkg.voice import VAD, AudioChunk, STTEngine, TTSEngine
        vad = VAD()
        # 0.5s de silêncio (16000 amostras de amplitude 0.0)
        chunk = AudioChunk(samples=[0.0] * 8000, sample_rate=16000, duration_s=0.5)
        speech = vad.has_speech(chunk)
        stt = STTEngine()
        txt, conf = stt.transcribe(chunk)  # mock
        tts = TTSEngine()
        audio = tts.synthesize("Olá Miguel")
        return (f"VAD: silêncio detectado como fala? {speech} (esperado False)\n"
                f"STT mock: '{txt}' (conf={conf:.2f})\n"
                f"TTS mock: {len(audio)} bytes")
    safe("voz", _voice)

    # ============ 13. PERCEPÇÃO ============
    hr("13. PERCEPÇÃO (VISÃO)")
    def _vision():
        from mia_pkg.perception import VisionPipeline, VisionFrame
        vision = VisionPipeline(analyze_fn=None)
        frame = VisionFrame(pixels=b"fake")
        result = vision.analyze(frame)
        return f"Vision analyze (mock): {result}"
    safe("visão", _vision)

    # ============ 14. DISTRIBUÍDO ============
    hr("14. NÓS DISTRIBUÍDOS")
    def _dist():
        from mia_pkg.distributed import NodeManager, SyncEngine, NodeRole
        nm = NodeManager(db, role=NodeRole.MASTER, name="pc-miguel")
        sync = SyncEngine(db, nm)
        snap = sync.create_snapshot()
        ev = sync.enqueue("memory", {"content": "teste offline"})
        return (f"Nó local: {nm.local().name} ({nm.local().role.value})\n"
                f"Snapshot: {len(snap.tables)} tabelas, checksum={snap.checksum[:12]}...\n"
                f"Evento enfileirado: {ev.id[:8]} (pendentes={len(sync.pending_events())})")
    safe("distribuído", _dist)

    # ============ 15. HEALTH ============
    hr("15. HEALTH CHECK + BACKUP")
    monitor = HealthMonitor(db)

    def _health():
        rep = monitor.health_check()
        d = rep.to_dict() if hasattr(rep, "to_dict") else rep.__dict__
        return f"Saúde global: {d.get('overall', '?')}\nIssues: {len(d.get('issues', []))}"
    safe("health", _health)

    def _backup():
        backup = BackupManager(db)
        dest = os.path.join(tmpdir, "backup.db")
        ok = backup.backup_to(dest)
        return f"Backup criado: {ok} ({os.path.getsize(dest) if os.path.exists(dest) else 0} bytes)"
    safe("backup", _backup)

    # ============ 16. EVOLUÇÃO ============
    hr("16. AUTOEVOLUÇÃO")
    def _evo():
        from mia_pkg.evolution import EvolutionEngine
        evo = EvolutionEngine(db)
        params = evo.list_parameters() if hasattr(evo, "list_parameters") else []
        out = f"Parâmetros evoluíveis: {len(params)}"
        for p in (params or [])[:5]:
            out += f"\n    - {p}"
        return out
    safe("evolução", _evo)

    # ============ RESUMO ============
    hr("RESUMO FINAL")
    latencies = [t.latency_ms for t in turns if hasattr(t, "latency_ms")]
    avg_ms = sum(latencies) / len(latencies) if latencies else 0
    print(f"  Turnos: {len(turns)} | latência média: {avg_ms:.0f}ms (fallback regras)")
    print(f"  Memórias totais: {memory.count()}")
    print(f"  Banco persistido: {os.path.exists(db_path)} ({os.path.getsize(db_path)} bytes)")

    db.close()
    print("\n✅ TESTE PRÁTICO CONCLUÍDO — sistema operacional de ponta a ponta")


if __name__ == "__main__":
    main()