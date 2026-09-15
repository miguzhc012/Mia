"""Testes da Fase 9: Voz (VAD, STT, Speaker, Directed, TTS, Pipeline)."""
import math
import struct
import wave
import io

import pytest

from mia_pkg.db import SQLiteConnection
from mia_pkg.events import EventBus, EventType
from mia_pkg.voice import (
    AudioChunk, SpeechSource, VAD, STTEngine, SpeakerRecognizer,
    DirectedSpeechDetector, TTSEngine, TTSProsody, TTSVoice,
    AudioEventBus, VoicePipeline, Transcript,
)


@pytest.fixture
def db():
    d = SQLiteConnection(":memory:")
    d.connect()
    d.init_schema()
    yield d
    d.close()


def make_chunk(duration_s=0.5, amplitude=0.3, freq=200, rate=16000) -> AudioChunk:
    """Gera chunk de áudio sintético (senoide)."""
    n = int(duration_s * rate)
    samples = [amplitude * math.sin(2 * math.pi * freq * i / rate) for i in range(n)]
    return AudioChunk(samples=samples, duration_s=duration_s, sample_rate=rate)


def silence_chunk(duration_s=0.5, rate=16000) -> AudioChunk:
    return AudioChunk(samples=[0.0] * int(duration_s * rate), duration_s=duration_s, sample_rate=rate)


# ======================================================================
# VAD
# ======================================================================

class TestVAD:
    def test_detects_speech_amplitude(self):
        vad = VAD(energy_threshold=0.02)
        chunk = make_chunk(duration_s=0.5, amplitude=0.3)
        segs = vad.detect_speech(chunk)
        assert len(segs) >= 1
        assert segs[0].end_s - segs[0].start_s > 0.1

    def test_silence_not_detected(self):
        vad = VAD(energy_threshold=0.02)
        chunk = silence_chunk(0.5)
        segs = vad.detect_speech(chunk)
        assert segs == []

    def test_empty_chunk_no_segments(self):
        vad = VAD()
        assert vad.detect_speech(AudioChunk(samples=[])) == []

    def test_short_blip_ignored(self):
        """Duração mínima: blips < 120ms são ignorados."""
        vad = VAD(energy_threshold=0.02, min_speech_ms=120)
        chunk = make_chunk(duration_s=0.05, amplitude=0.5)
        assert vad.detect_speech(chunk) == []

    def test_has_speech(self):
        vad = VAD()
        assert vad.has_speech(make_chunk(0.3, 0.3))
        assert not vad.has_speech(silence_chunk(0.3))

    def test_segments_merged_across_short_silence(self):
        """Silêncio < 300ms entre falas é fundido."""
        vad = VAD(energy_threshold=0.02, min_speech_ms=50, min_silence_ms=300)
        # fala 200ms + silêncio 100ms + fala 200ms
        n1 = int(0.2 * 16000)
        n2 = int(0.1 * 16000)
        samples = [0.3] * n1 + [0.0] * n2 + [0.3] * n1
        chunk = AudioChunk(samples=samples, duration_s=0.5, sample_rate=16000)
        segs = vad.detect_speech(chunk)
        assert len(segs) == 1
        assert segs[0].end_s - segs[0].start_s > 0.3


# ======================================================================
# STT
# ======================================================================

class TestSTT:
    def test_default_returns_empty_for_silence(self):
        stt = STTEngine()
        text, conf = stt.transcribe(silence_chunk(0.3))
        assert text == ""

    def test_plugged_fn_used(self):
        def fake(chunk):
            return "olá Mia", 0.95
        stt = STTEngine(fake)
        text, conf = stt.transcribe(make_chunk(0.3))
        assert text == "olá Mia"
        assert conf == 0.95

    def test_empty_chunk(self):
        stt = STTEngine()
        assert stt.transcribe(AudioChunk()) == ("", 0.0)


# ======================================================================
# Speaker Recognition
# ======================================================================

class TestSpeaker:
    def test_unknown_when_no_people(self, db):
        rec = SpeakerRecognizer(db)
        sid, known, conf = rec.identify(make_chunk(0.3))
        assert sid is None
        assert not known

    def test_single_person_fallback(self, db):
        from mia_pkg.social import PeopleStore
        PeopleStore(db).ensure("miguel")
        rec = SpeakerRecognizer(db)
        sid, known, conf = rec.identify(make_chunk(0.3))
        assert sid == "miguel"
        assert known

    def test_profile_fn_return(self, db):
        from mia_pkg.social import PeopleStore
        PeopleStore(db).ensure("miguel")
        rec = SpeakerRecognizer(db, profile_fn=lambda c: "miguel")
        sid, known, conf = rec.identify(make_chunk(0.3))
        assert sid == "miguel"
        assert known
        assert conf == 0.9


# ======================================================================
# Directed-speech
# ======================================================================

class TestDirected:
    def test_calls_name(self):
        det = DirectedSpeechDetector()
        assert det.is_directed("Mia, me conta uma história")[0]

    def test_direct_command(self):
        det = DirectedSpeechDetector()
        assert det.is_directed("me conta o que você fez hoje")[0]

    def test_question_pattern(self):
        det = DirectedSpeechDetector()
        assert det.is_directed("qual é o seu filme favorito?")[0]

    def test_known_speaker_solo(self):
        det = DirectedSpeechDetector()
        directed, conf = det.is_directed("olha o que eu comprei", speaker_known=True, solo_speaker=True)
        assert directed
        assert conf >= 0.5

    def test_third_party_conversation_ignored(self):
        det = DirectedSpeechDetector()
        directed, conf = det.is_directed(
            "vamos marcar a reunião amanhã", speaker_known=False, solo_speaker=True
        )
        assert not directed

    def test_empty_text(self):
        det = DirectedSpeechDetector()
        assert det.is_directed("") == (False, 0.0)


# ======================================================================
# TTS
# ======================================================================

class TestTTS:
    def test_prosody_maps_emotions(self):
        assert TTSProsody.for_emotion("joy")["rate"] > 1.0
        assert TTSProsody.for_emotion("sadness")["pitch"] < 1.0
        assert TTSProsody.for_emotion("desconhecida") == {"rate": 1.0, "pitch": 1.0, "volume": 1.0}

    def test_synthesize_returns_wav(self):
        tts = TTSEngine()
        audio = tts.synthesize("olá Miguel!")
        assert audio[:4] == b"RIFF"
        assert b"WAVE" in audio[:12]
        assert len(audio) > 100

    def test_emotion_changes_audio(self):
        tts = TTSEngine()
        joy = tts.synthesize("teste", emotion="joy")
        sad = tts.synthesize("teste", emotion="sadness")
        assert joy != sad  # prosódia diferente → áudio diferente

    def test_plugged_fn(self):
        def fake(text, prosody):
            return b"<audio>" + text.encode()
        tts = TTSEngine(fake)
        assert tts.synthesize("oi", "joy") == b"<audio>oi"

    def test_last_audio(self):
        tts = TTSEngine()
        tts.synthesize("oi")
        assert tts.last_audio is not None


# ======================================================================
# Audio Event Bus
# ======================================================================

class TestAudioEventBus:
    def test_events_emitted(self, db):
        bus = EventBus()
        got = []
        bus.subscribe(EventType.SPEECH_DETECTED, lambda e: got.append(e))
        bus.subscribe(EventType.SPEECH_TRANSCRIBED, lambda e: got.append(e))
        bus.subscribe(EventType.SPEECH_DIRECTED, lambda e: got.append(e))
        bus.subscribe(EventType.TTS_GENERATED, lambda e: got.append(e))

        aeb = AudioEventBus(bus)
        from mia_pkg.voice import SpeechSegment
        aeb.speech_detected(SpeechSegment(0, 0.5, 0.3))
        aeb.speech_transcribed(Transcript("oi", "miguel", "Miguel", 0.9, True))
        aeb.speech_directed(True, 0.9)
        aeb.tts_generated("joy", 1.2)
        assert len(got) == 4


# ======================================================================
# Voice Pipeline (integração)
# ======================================================================

class TestVoicePipeline:
    def test_full_pipeline_directed(self, db):
        bus = EventBus()
        miguel_spoke = []
        bus.subscribe(EventType.MIGUEL_SPOKE, lambda e: miguel_spoke.append(e))

        def fake_stt(chunk):
            return "Mia, me conta uma história", 0.95

        pipe = VoicePipeline(db, stt_fn=fake_stt, bus=bus)
        transcript = pipe.process_audio(make_chunk(0.5))
        assert transcript is not None
        assert transcript.directed_to_mia
        assert transcript.text == "Mia, me conta uma história"
        # integração com cognitive core: MIGUEL_SPOKE emitido
        assert len(miguel_spoke) == 1
        assert miguel_spoke[0].payload["text"] == "Mia, me conta uma história"

    def test_silence_no_transcript(self, db):
        pipe = VoicePipeline(db)
        assert pipe.process_audio(silence_chunk(0.5)) is None

    def test_third_party_ignored(self, db):
        bus = EventBus()

        def fake_stt(chunk):
            return "vamos marcar a reunião para amanhã", 0.9

        pipe = VoicePipeline(db, stt_fn=fake_stt, bus=bus)
        transcript = pipe.process_audio(make_chunk(0.5))
        assert transcript is not None
        assert not transcript.directed_to_mia

    def test_speak_generates_audio(self, db):
        pipe = VoicePipeline(db)
        audio = pipe.speak("Olá", emotion="joy")
        assert audio[:4] == b"RIFF"

    def test_known_speaker_identified(self, db):
        from mia_pkg.social import PeopleStore
        PeopleStore(db).ensure("miguel")

        def fake_stt(chunk):
            return "Mia, bom dia", 0.9

        pipe = VoicePipeline(db, stt_fn=fake_stt)
        transcript = pipe.process_audio(make_chunk(0.5))
        assert transcript.speaker_name == "miguel"
        assert transcript.is_known_speaker

    def test_wav_valid(self):
        """O WAV gerado pelo TTS deve ser legível por wave module."""
        tts = TTSEngine()
        audio = tts.synthesize("teste de áudio", "calm")
        wav = wave.open(io.BytesIO(audio))
        assert wav.getframerate() == 16000
        assert wav.getsampwidth() == 2
        assert wav.getnframes() > 0