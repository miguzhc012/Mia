"""CLI REPL — interface de conversa com Mia.

Comandos:
  /state        — mostra estado interno (emoções, humor, identidade)
  /memory       — lista memórias
  /beliefs      — lista crenças
  /needs        — lista necessidades/desejos
  /reset        — limpa histórico
  /help         — ajuda
  /quit         — sai
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from mia_pkg.config import load_config
from mia_pkg.db import SQLiteConnection
from mia_pkg.events import EventBus
from mia_pkg.llm import LLMProviderChain, OpenAICompatProvider
from mia_pkg.chat import ChatSession, ChatTurn
from mia_pkg.memory import MemoryStore
from mia_pkg.beliefs import BeliefStore
from mia_pkg.needs_desires import NeedsDesiresStore
from mia_pkg.affective_engine import AffectiveEngine
from mia_pkg.identity import IdentityManager

logger = logging.getLogger(__name__)


def build_llm_chain(config: Any) -> LLMProviderChain:
    """Constrói chain de providers a partir da config."""
    chain = LLMProviderChain()
    config_providers = config.get("llm.providers", [])
    for p in config_providers:
        chain.add_provider(
            OpenAICompatProvider(
                name=p.get("name", "openai"),
                base_url=p.get("base_url", "https://api.openai.com/v1"),
                model=p.get("model", "gpt-4o-mini"),
                api_key_env=p.get("api_key_env", "OPENAI_API_KEY"),
            )
        )
    return chain


def print_emotion_state(affective: AffectiveEngine) -> None:
    """Imprime estado emocional formatado."""
    state = affective.get_current()
    e = state.emotions.to_dict()
    mood = state.mood

    print("\n=== ESTADO EMOCIONAL ===")
    emotion_names = {
        "happiness": "felicidade", "sadness": "tristeza", "anger": "raiva",
        "fear": "medo", "surprise": "surpresa", "disgust": "desprezo",
        "trust_level": "confiança", "anticipation": "antecipação",
        "curiosity_level": "curiosidade", "loneliness": "solidão",
        "affection": "afeto", "boredom": "tédio",
    }
    for key, value in sorted(e.items(), key=lambda x: -abs(x[1] - 0.5))[:6]:
        name = emotion_names.get(key, key)
        bar = "#" * int(value * 20)
        print(f"  {name:<14} {value:.2f} |{bar:<20}|")
    print(
        f"\n  Mood: valence={mood.valence:+.2f}, arousal={mood.arousal:.2f}, "
        f"dominance={mood.dominance:.2f}"
    )


def print_identity(identity: IdentityManager) -> None:
    """Imprime identidade formatada."""
    ident = identity.get_identity()
    print("\n=== IDENTIDADE ===")
    print(f"  Nome: {ident.name}")
    if ident.self_model:
        for k, v in ident.self_model.items():
            print(f"  {k}: {v}")
    if ident.core_values:
        print(f"  Valores: {', '.join(ident.core_values)}")


def print_memories(memory: MemoryStore) -> None:
    """Imprime memórias."""
    mems = memory.list_by_importance(limit=10)
    print("\n=== MEMÓRIAS ===")
    if not mems:
        print("  (vazia)")
    for m in mems:
        content = m.content[:70] + "..." if len(m.content) > 70 else m.content
        print(f"  [{m.importance:.2f}] {content}")


def print_beliefs(beliefs: BeliefStore) -> None:
    """Imprime crenças."""
    active = beliefs.list_active(limit=10)
    print("\n=== CRENÇAS ===")
    if not active:
        print("  (nenhuma ativa)")
    for b in active:
        print(f"  [{b.confidence:.0%}] {b.proposition}")


def print_needs(needs_store: NeedsDesiresStore) -> None:
    """Imprime necessidades e desejos."""
    needs = needs_store.list_unfulfilled_needs(limit=10)
    desires = needs_store.list_unfulfilled_desires(limit=10)
    print("\n=== NECESSIDADES / DESEJOS ===")
    if not needs and not desires:
        print("  (tudo satisfeito)")
    for n in needs:
        print(f"  [need:{n.need_type.value}] intensity={n.intensity:.2f}")
    for d in desires:
        print(f"  [desire] {d.description[:60]} priority={d.priority:.2f}")


def format_turn(turn: ChatTurn) -> str:
    """Formata um ChatTurn para exibição."""
    decision = ""
    if turn.pipeline and turn.pipeline.attention_decision:
        decision = turn.pipeline.attention_decision.value if hasattr(turn.pipeline.attention_decision, "value") else str(turn.pipeline.attention_decision)
    provider = turn.provider or "rule-based"
    pipeline_note = f"\n\n  [pipeline: {decision}]" if decision else ""
    return (
        f"\n💜 Mia [{provider}] ({turn.latency_ms}ms):\n"
        f"{turn.response_text}"
        f"{pipeline_note}"
    )


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da CLI."""
    argv = argv or sys.argv[1:]
    logging.basicConfig(level=logging.WARNING)

    config = load_config()
    db_path = Path.home() / ".local" / "share" / "mia" / "mia.db"
    db = SQLiteConnection(db_path)
    db.connect()
    db.init_schema()

    # Components
    affective = AffectiveEngine(db)
    identity = IdentityManager(db)
    memory = MemoryStore(db)
    beliefs = BeliefStore(db)
    needs_store = NeedsDesiresStore(db)

    # LLM chain (graceful: usa rule-based se não disponível)
    chain = build_llm_chain(config)
    chat = ChatSession(db=db, llm_chain=chain)

    if chat.llm_available:
        print(f"🤖 Mia com LLM: {chain._providers[0].model}")
    else:
        print("⚠️  Nenhum LLM disponível — usando respostas por regras. Configure OPENAI_API_KEY para conversa real.")

    print("Bem-vindo(a) à Mia! Digite /help para comandos. /quit para sair.\n")

    while True:
        try:
            user_input = input("Você> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté logo! 💜")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            cmd = user_input.lower().split()[0]
            args = user_input[len(cmd):].strip()

            if cmd in ("/quit", "/exit", "/sair"):
                print("Até logo! 💜")
                break
            elif cmd == "/reset":
                chat.reset()
                print("Conversa resetada.")
            elif cmd == "/state":
                print_emotion_state(affective)
                print_identity(identity)
            elif cmd == "/memory":
                print_memories(memory)
            elif cmd == "/beliefs":
                print_beliefs(beliefs)
            elif cmd == "/needs":
                print_needs(needs_store)
            elif cmd == "/help":
                print(
                    "Comandos:\n"
                    "  /state        — estado interno (emoções, identidade)\n"
                    "  /memory       — memórias\n"
                    "  /beliefs      — crenças\n"
                    "  /needs        — necessidades/desejos\n"
                    "  /reset        — limpa histórico\n"
                    "  /help         — esta ajuda\n"
                    "  /quit         — sai\n"
                )
            else:
                print(f"Comando desconhecido: {cmd}. Use /help.")
            continue

        # Mensagem normal
        try:
            turn = chat.send(user_input)
            print(format_turn(turn))
        except Exception as e:
            print(f"\n⚠️  Erro: {e}")

    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())