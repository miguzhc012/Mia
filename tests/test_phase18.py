"""Testes da Fase 10: Visão/Percepção (Vision, RateLimit, Aggregator, Enricher)."""
import pytest

from mia_pkg.db import SQLiteConnection
from mia_pkg.events import EventBus, EventType
from mia_pkg.perception import (
    VisionFrame, VisualObservation, VisionPipeline, VisionRateLimiter,
    PerceptionAggregator, PerceptionEvent, ContextEnricher,
)


@pytest.fixture
def db():
    d = SQLiteConnection(":memory:")
    d.connect()
    d.init_schema()
    yield d
    d.close()


class TestVisionPipeline:
    def test_no_activity_no_event(self, db):
        bus = EventBus()
        got = []
        bus.subscribe(EventType.CAMERA_ACTIVITY_DETECTED, lambda e: got.append(e))

        pipe = VisionPipeline(bus=bus)
        frame = VisionFrame()
        obs = pipe.analyze(frame)
        assert obs.activity == "none"
        assert got == []  # nada emitido

    def test_person_detected_emits_events(self, db):
        bus = EventBus()
        cam = []
        new_person = []
        bus.subscribe(EventType.CAMERA_ACTIVITY_DETECTED, lambda e: cam.append(e))
        bus.subscribe(EventType.NEW_PERSON_DETECTED, lambda e: new_person.append(e))

        def fake(frame):
            return VisualObservation(
                frame_id=frame.id, activity="person",
                description="uma pessoa entrou na sala",
                people_visible=1, confidence=0.9,
            )

        pipe = VisionPipeline(analyze_fn=fake, bus=bus)
        obs = pipe.analyze(VisionFrame())
        assert len(cam) == 1
        assert len(new_person) == 1
        assert cam[0].payload["people"] == 1

    def test_movement_emits_camera_only(self, db):
        bus = EventBus()
        cam = []
        new_person = []
        bus.subscribe(EventType.CAMERA_ACTIVITY_DETECTED, lambda e: cam.append(e))
        bus.subscribe(EventType.NEW_PERSON_DETECTED, lambda e: new_person.append(e))

        def fake(frame):
            return VisualObservation(
                frame_id=frame.id, activity="movement",
                description="movimento detectado", confidence=0.6,
            )

        pipe = VisionPipeline(analyze_fn=fake, bus=bus)
        pipe.analyze(VisionFrame())
        assert len(cam) == 1
        assert new_person == []

    def test_low_confidence_no_event(self, db):
        bus = EventBus()
        got = []
        bus.subscribe(EventType.CAMERA_ACTIVITY_DETECTED, lambda e: got.append(e))

        def fake(frame):
            return VisualObservation(frame.id, "person", "duvidoso", 1, [], "neutral", 0.2)

        pipe = VisionPipeline(analyze_fn=fake, bus=bus)
        pipe.analyze(VisionFrame())
        assert got == []

    def test_last_observation(self, db):
        pipe = VisionPipeline()
        pipe.analyze(VisionFrame())
        assert pipe.last_observation is not None


class TestVisionRateLimiter:
    def test_allows_up_to_max(self):
        rl = VisionRateLimiter(max_per_minute=3, window_s=60)
        assert rl.allow()
        assert rl.allow()
        assert rl.allow()
        assert not rl.allow()  # 4ª bloqueada

    def test_remaining_decreases(self):
        rl = VisionRateLimiter(max_per_minute=5, window_s=60)
        rl.allow()
        rl.allow()
        assert rl.remaining() == 3

    def test_window_resets(self):
        import time as _time
        rl = VisionRateLimiter(max_per_minute=2, window_s=0.05)
        rl.allow()
        rl.allow()
        assert not rl.allow()
        _time.sleep(0.06)
        assert rl.allow()  # janela expirou


class TestPerceptionAggregator:
    def test_person_plus_speech_fuses(self, db):
        bus = EventBus()
        fused = []
        bus.subscribe(EventType.PERCEPTION_FUSED, lambda e: fused.append(e))

        agg = PerceptionAggregator(bus)
        agg.add(PerceptionEvent("vision", "person", {"count": 1}))
        result = agg.add(PerceptionEvent("audio", "speech", {"text": "oi"}))
        assert result.kind == "person_interacting"
        assert result.importance == 0.8
        assert len(fused) == 1

    def test_single_sensor_no_fusion(self, db):
        agg = PerceptionAggregator()
        result = agg.add(PerceptionEvent("vision", "movement", {"motion": True}))
        assert result.kind == "movement"

    def test_current_picture(self, db):
        agg = PerceptionAggregator()
        agg.add(PerceptionEvent("vision", "person", {}))
        agg.add(PerceptionEvent("audio", "speech", {}))
        pic = agg.current_picture()
        assert "vision" in pic and "audio" in pic


class TestContextEnricher:
    def test_empty_context_without_perception(self, db):
        agg = PerceptionAggregator()
        enr = ContextEnricher(agg)
        assert enr.enrich("base") == "base"
        assert not enr.has_perception()

    def test_enriches_with_perception_block(self, db):
        agg = PerceptionAggregator()
        agg.add(PerceptionEvent("vision", "person", {"count": 1}))
        enr = ContextEnricher(agg)
        enriched = enr.enrich("base context")
        assert "Percepção atual:" in enriched
        assert "vision/person" in enriched
        assert enriched.startswith("base context")

    def test_has_perception(self, db):
        agg = PerceptionAggregator()
        enr = ContextEnricher(agg)
        assert not enr.has_perception()
        agg.add(PerceptionEvent("vision", "movement", {}))
        assert enr.has_perception()