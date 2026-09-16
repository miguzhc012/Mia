"""Testes de provenance e semântica de falha do EventBus (H15/H16)."""
import pytest

from mia_pkg.events import (
    Event, EventBus, EventRejectedError, EventType,
)


class TestEventProvenance:
    def test_event_has_provenance_fields(self):
        ev = Event(type=EventType.MIGUEL_SPOKE, source="test")
        assert ev.correlation_id is None
        assert ev.causation_id is None

    def test_correlation_flow(self):
        flow = "sessao-123"
        e1 = Event(type=EventType.MIGUEL_SPOKE, source="perception",
                   correlation_id=flow)
        e2 = Event(type=EventType.STATE_CHANGED, source="core",
                   correlation_id=flow, causation_id=str(e1.id))
        assert e2.correlation_id == "sessao-123"
        assert e2.causation_id == str(e1.id)

    def test_distinct_event_types(self):
        """MIGUEL_SPOKE e STATE_CHANGED são tipos distintos (não reusar um
        evento semântico para representar outro)."""
        assert EventType.MIGUEL_SPOKE != EventType.STATE_CHANGED
        # eventos internos existem como tipos próprios
        assert EventType.MEMORY_CREATED is not None
        assert EventType.PERSONALITY_CHANGED is not None
        assert EventType.RELATIONSHIP_UPDATED is not None
        assert EventType.EMOTION_CHANGED.value == "emotion_changed"


class TestEventBusFailureSemantics:
    def test_invalid_type_raises(self):
        bus = EventBus()
        ev = Event()
        ev.type = "nonsense"  # type: ignore[assignment]
        with pytest.raises(EventRejectedError):
            bus.emit(ev)

    def test_handler_error_returns_false(self):
        bus = EventBus()
        def boom(e): raise RuntimeError("x")
        bus.subscribe(EventType.MIGUEL_SPOKE, boom)
        assert bus.emit(Event(type=EventType.MIGUEL_SPOKE, source="s")) is False

    def test_all_ok_returns_true(self):
        bus = EventBus()
        got = []
        bus.subscribe(EventType.MIGUEL_SPOKE, lambda e: got.append(e))
        assert bus.emit(Event(type=EventType.MIGUEL_SPOKE, source="s")) is True
        assert len(got) == 1

    def test_circuit_breaker_by_source_type_combo(self):
        """Falha num (source,type) não bloqueia outro tipo do mesmo source."""
        bus = EventBus(circuit_breaker_threshold=2)
        def boom(e): raise RuntimeError("x")
        ok = []
        bus.subscribe(EventType.MIGUEL_SPOKE, boom)
        bus.subscribe(EventType.STATE_CHANGED, lambda e: ok.append(e))

        bus.emit(Event(type=EventType.MIGUEL_SPOKE, source="p"))
        bus.emit(Event(type=EventType.MIGUEL_SPOKE, source="p"))
        with pytest.raises(EventRejectedError):
            bus.emit(Event(type=EventType.MIGUEL_SPOKE, source="p"))
        # outro tipo, mesmo produtor: funciona
        bus.emit(Event(type=EventType.STATE_CHANGED, source="p"))
        assert len(ok) == 1

    def test_success_resets_circuit(self):
        """Um emit com todos os handlers OK reseta o contador de erros."""
        bus = EventBus(circuit_breaker_threshold=3)
        state = {"n": 0}
        def flaky(e):
            state["n"] += 1
            if state["n"] in (1, 2, 4, 5):  # falha nas rodadas 1,2 e 4,5
                raise RuntimeError("x")
        bus.subscribe(EventType.MIGUEL_SPOKE, flaky)
        # rodadas 1-2: falha → contador 2 (abaixo do threshold 3)
        assert bus.emit(Event(type=EventType.MIGUEL_SPOKE, source="p")) is False
        assert bus.emit(Event(type=EventType.MIGUEL_SPOKE, source="p")) is False
        # rodada 3: sucesso total → reset
        assert bus.emit(Event(type=EventType.MIGUEL_SPOKE, source="p")) is True
        # rodadas 4-5: falhas voltam a contar do zero (2 < 3 → emit ok, porém False)
        assert bus.emit(Event(type=EventType.MIGUEL_SPOKE, source="p")) is False
        assert bus.emit(Event(type=EventType.MIGUEL_SPOKE, source="p")) is False
        # rodada 6: sucesso sem ter aberto circuito
        assert bus.emit(Event(type=EventType.MIGUEL_SPOKE, source="p")) is True

    def test_error_not_silent_other_handlers_still_called(self):
        bus = EventBus()
        good = []
        def boom(e): raise RuntimeError("x")
        bus.subscribe(EventType.MIGUEL_SPOKE, boom)
        bus.subscribe(EventType.MIGUEL_SPOKE, lambda e: good.append(e))
        result = bus.emit(Event(type=EventType.MIGUEL_SPOKE, source="s"))
        assert result is False
        assert len(good) == 1  # bom handler ainda recebeu

    def test_no_subscribers_is_not_failure(self):
        bus = EventBus()
        assert bus.emit(Event(type=EventType.STATE_CHANGED, source="s")) is True