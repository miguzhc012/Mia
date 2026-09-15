"""Testes da Fase 11: Avatar / Embodiment (Mapper, Renderer, Sync, API)."""
import os
import tempfile

import pytest

from mia_pkg.db import SQLiteConnection
from mia_pkg.events import EventBus, EventType
from mia_pkg.affective_engine import EmotionVector, MoodState
from mia_pkg.avatar import (
    Expression, ExpressionMapper, FacialConfig, AvatarRenderer, AvatarSync, AvatarAPI,
)


@pytest.fixture
def db():
    d = SQLiteConnection(":memory:")
    d.connect()
    d.init_schema()
    yield d
    d.close()


class TestExpressionMapper:
    def test_neutral_default(self):
        mapper = ExpressionMapper()
        config = mapper.map_emotion()
        assert config.expression == Expression.NEUTRAL

    def test_happy_dominant(self):
        mapper = ExpressionMapper()
        emotions = EmotionVector(happiness=0.9, sadness=0.0, anger=0.0)
        config = mapper.map_emotion(emotions)
        assert config.expression == Expression.HAPPY
        assert config.mouth_curve > 0

    def test_sad_dominant(self):
        mapper = ExpressionMapper()
        emotions = EmotionVector(happiness=0.1, sadness=0.85, anger=0.0)
        config = mapper.map_emotion(emotions)
        assert config.expression == Expression.SAD
        assert config.mouth_curve < 0

    def test_angry_brows(self):
        mapper = ExpressionMapper()
        emotions = EmotionVector(happiness=0.1, anger=0.9)
        config = mapper.map_emotion(emotions)
        assert config.expression == Expression.ANGRY
        assert config.brow_angle < 0

    def test_low_intensity_neutral(self):
        mapper = ExpressionMapper()
        emotions = EmotionVector(happiness=0.2, sadness=0.2)  # tudo fraco
        config = mapper.map_emotion(emotions)
        assert config.expression == Expression.NEUTRAL

    def test_mood_adjusts(self):
        mapper = ExpressionMapper()
        emotions = EmotionVector(happiness=0.7)
        config_joy = mapper.map_emotion(emotions, MoodState(valence=0.8, arousal=0.9))
        config_sad = mapper.map_emotion(emotions, MoodState(valence=-0.8, arousal=0.3))
        assert config_joy.mouth_curve > config_sad.mouth_curve

    def test_loving_affection(self):
        mapper = ExpressionMapper()
        emotions = EmotionVector(affection=0.95, happiness=0.4)
        config = mapper.map_emotion(emotions)
        assert config.expression == Expression.LOVING
        assert config.blush > 0.3

    def test_map_contains_all_expressions(self):
        mapper = ExpressionMapper()
        assert set(mapper.MAP.keys()) == set(Expression)


class TestAvatarRenderer:
    def test_renders_svg(self):
        renderer = AvatarRenderer()
        svg = renderer.render(FacialConfig())
        assert svg.startswith("<svg")
        assert "viewBox" in svg
        assert "</svg>" in svg

    def test_happy_and_sad_differ(self):
        renderer = AvatarRenderer()
        happy = renderer.render(FacialConfig(expression=Expression.HAPPY, mouth_curve=0.8))
        sad = renderer.render(FacialConfig(expression=Expression.SAD, mouth_curve=-0.8))
        assert happy != sad

    def test_size_respected(self):
        renderer = AvatarRenderer(size=300)
        svg = renderer.render(FacialConfig())
        assert 'width="300"' in svg

    def test_render_to_file(self):
        renderer = AvatarRenderer()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "avatar.svg")
            renderer.render_to_file(FacialConfig(), path)
            assert os.path.exists(path)
            with open(path) as f:
                assert "<svg" in f.read()


class TestAvatarSync:
    def test_initial_update_from_engine(self, db):
        sync = AvatarSync(db, AvatarRenderer())
        config = sync.update()
        assert config is not None
        assert sync.current_expression in Expression

    def test_emotion_change_triggers_update(self, db):
        from mia_pkg.affective_engine import AffectiveEngine
        engine = AffectiveEngine(db)
        updates = []
        sync = AvatarSync(db, AvatarRenderer(), on_update=lambda c: updates.append(c))
        # forçar emoção feliz via apply_validated_change
        engine.apply_validated_change(
            EmotionVector(happiness=0.95).to_dict(),
            MoodState(valence=0.8, arousal=0.6).to_dict(),
            reason="test",
        )
        sync.update()  # explícito (teste determinístico)
        assert sync.current_expression == Expression.HAPPY

    def test_responsive_sync(self, db):
        import time
        sync = AvatarSync(db, AvatarRenderer())
        t0 = time.time()
        sync.update()
        elapsed = time.time() - t0
        assert elapsed < 0.5  # responsivo (<500ms; na prática µs)


class TestAvatarAPI:
    def test_current_expression_dict(self, db):
        sync = AvatarSync(db, AvatarRenderer())
        sync.update()
        api = AvatarAPI(sync, AvatarRenderer())
        expr = api.current_expression()
        assert "expression" in expr
        assert "mouth_curve" in expr

    def test_current_svg(self, db):
        sync = AvatarSync(db, AvatarRenderer())
        sync.update()
        api = AvatarAPI(sync, AvatarRenderer())
        svg = api.current_svg()
        assert svg.startswith("<svg")

    def test_save_snapshot(self, db):
        sync = AvatarSync(db, AvatarRenderer())
        sync.update()
        api = AvatarAPI(sync, AvatarRenderer())
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snap.svg")
            api.save_snapshot(path)
            assert os.path.exists(path)