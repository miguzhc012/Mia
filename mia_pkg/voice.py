"""Voice Pipeline — VAD, STT, Speaker Recognition, Directed-speech, TTS.

Fase 9 do roadmap:
- VAD (Voice Activity Detection): detecta fala vs. silêncio
- STT: transcrição (Whisper ou equivalente — output plugável)
- Speaker Recognition: identifica quem fala (baseado em PeopleStore)
- Directed-speech: detecta se fala é dirigida à MIA
- TTS: texto → fala com prosódia (emotion → entonação)
- Audio Event Bus: eventos tipados de áudio
- Integração com Cognitive Core: voz como input adicional

Tudo é plugável (stt_fn, tts_fn) — em produção aponta para Whisper/edge-tts,
em testes usa mocks determinísticos. Nenhuma dependência pesada no núcleo.
"""
from __future__ import annotations

import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Protocol

from mia_pkg.db import SQLiteConnection
from mia_pkg.events import Event, EventType, EventBus
from mia_pkg.social import PeopleStore, RelationshipStore

logger = logging.getLogger(__name__)


# ======================================================================
# Tipos
# ======================================================================

class SpeechSource(str, Enum):
    """Origem do áudio."""
    MICROPHONE = "microphone"
    CALL = "call"
    FILE = "file"


@dataclass
class AudioChunk:
    """Um pedaço de áudio (amostras ou metadados)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    samples: list[float] = field(default_factory=list)  # amplitude normalizada
    source: SpeechSource = SpeechSource.MICROPHONE
    duration_s: float = 0.0
    sample_rate: int = 16000


@dataclass
class SpeechSegment:
    """Segmento de fala detectado pelo VAD."""
    start_s: float
    end_s: float
    level: float  # amplitude média normalizada 0-1
    text: str = ""  # preenchido pelo STT


@dataclass
class Transcript:
    """Resultado de STT + speaker + directed."""
    text: str
    speaker_id: str | None
    speaker_name: str
    confidence: float
    directed_to_mia: bool
    language: str = "pt-BR"
    is_known_speaker: bool = False


# ======================================================================
# VAD — Voice Activity Detection
# ======================================================================

class VAD:
    """Detecta fala vs. silêncio por amplitude/energia.

    Implementação leve: threshold de energia + duração mínima.
    Em produção pode ser substituído por WebRTC VAD — mesma interface.
    """

    def __init__(
        self,
        energy_threshold: float = 0.02,
        min_speech_ms: float = 120.0,
        min_silence_ms: float = 300.0,
        sample_rate: int = 16000,
    ) -> None:
        self._threshold = energy_threshold
        self._min_speech = min_speech_ms / 1000.0
        self._min_silence = min_silence_ms / 1000.0
        self._sample_rate = sample_rate

    def detect_speech(self, chunk: AudioChunk) -> list[SpeechSegment]:
        """Detecta segmentos de fala num chunk de áudio."""
        if not chunk.samples:
            return []

        # calcula energia por janela de 20ms
        win = max(1, int(self._sample_rate * 0.02))
        segments: list[SpeechSegment] = []
        in_speech = False
        start = 0.0
        level = 0.0

        for i in range(0, len(chunk.samples), win):
            window = chunk.samples[i:i + win]
            energy = sum(abs(s) for s in window) / max(1, len(window))
            t = i / self._sample_rate

            if energy > self._threshold and not in_speech:
                in_speech = True
                start = t
                level = energy
            elif energy <= self._threshold and in_speech:
                in_speech = False
                if t - start >= self._min_speech:
                    segments.append(SpeechSegment(start_s=start, end_s=t, level=min(1.0, level)))
            elif in_speech:
                level = max(level, energy)

        # fecha segmento em aberto
        if in_speech:
            end = len(chunk.samples) / self._sample_rate
            if end - start >= self._min_speech:
                segments.append(SpeechSegment(start_s=start, end_s=end, level=min(1.0, level)))

        # junta segmentos separados por silêncio curto
        merged: list[SpeechSegment] = []
        for seg in segments:
            if merged and seg.start_s - merged[-1].end_s < self._min_silence:
                merged[-1].end_s = seg.end_s
                merged[-1].level = max(merged[-1].level, seg.level)
            else:
                merged.append(seg)
        return merged

    def has_speech(self, chunk: AudioChunk) -> bool:
        """True se o chunk contém fala (qualquer segmento)."""
        segs = self.detect_speech(chunk)
        return any(s.end_s - s.start_s >= self._min_speech for s in segs)


# ======================================================================
# STT — Speech to Text
# ======================================================================

class STTEngine:
    """Transcreve áudio para texto.

    `transcribe_fn` plugável (Whisper local, API, mock). Recebe o chunk
    e retorna (text, confidence). Padrão: mock que só funciona se o VAD
    detectou fala (para testes de integração).
    """

    def __init__(
        self,
        transcribe_fn: Callable[[AudioChunk], tuple[str, float]] | None = None,
    ) -> None:
        self._fn = transcribe_fn or self._default_transcribe

    @staticmethod
    def _default_transcribe(chunk: AudioChunk) -> tuple[str, float]:
        # mock: sem fala → texto vazio
        if not chunk.samples:
            return "", 0.0
        # energia média baixa = silêncio
        avg = sum(abs(s) for s in chunk.samples) / len(chunk.samples)
        if avg < 0.02:
            return "", 0.0
        return "[transcrição não configurada]", 0.5

    def transcribe(self, chunk: AudioChunk) -> tuple[str, float]:
        return self._fn(chunk)


# ======================================================================
# Speaker Recognition
# ======================================================================

class SpeakerRecognizer:
    """Identifica quem fala, baseado em PeopleStore.

    Em produção, usa embeddings de voz (ex.: ECAPA-TDNN); aqui o match
    é plugável via `profile_fn(audio) → speaker_id | None`. O fallback
    consulta a relação mais provável (para testes/demo).
    """

    def __init__(
        self,
        db: SQLiteConnection,
        profile_fn: Callable[[AudioChunk], str | None] | None = None,
    ) -> None:
        self._db = db
        self._people = PeopleStore(db)
        self._rels = RelationshipStore(db)
        self._profile_fn = profile_fn

    def identify(self, chunk: AudioChunk) -> tuple[str | None, bool, float]:
        """Retorna (speaker_id, is_known, confidence)."""
        if self._profile_fn:
            sid = self._profile_fn(chunk)
            if sid:
                person = self._people.get(sid)
                return sid, person is not None, 0.9

        # fallback demo: se só existe 1 pessoa, associa a ela
        people = self._people.list()
        if len(people) == 1:
            return people[0].id, True, 0.7
        return None, False, 0.0


# ======================================================================
# Directed-speech Detection
# ======================================================================

class DirectedSpeechDetector:
    """Detecta se fala é dirigida à MIA.

    Sinais:
    - Chamar pelo nome ("Mia", "ei Mia", "Mia, ...")
    - Contexto: só 1 pessoa falando com a MIA em interação direta
    - Comandos no imperativo ("me conta", "o que você acha")
    """

    # Nomes que Mia responde
    TRIGGER_NAMES = ("mia", "mia!", "mia,", "ei mia", "mia?")
    # Padrões de comando direto
    DIRECT_PATTERNS = (
        r"\b(me conta|me diz|me fala|o que voce acha|o que você acha|me ajuda)\b",
        r"\b(conta uma historia|conta uma história)\b",
        r"\b(como voce esta|como você está|o que voce fez|o que você fez)\b",
        r"\b(qual e|qual é|quem e|quem é)\b",
        r"\b(obrigado|obrigada|bom dia|boa tarde|boa noite)\b",
    )

    def __init__(self, name: str = "Mia") -> None:
        self._name = name

    def is_directed(self, text: str, speaker_known: bool = False,
                    solo_speaker: bool = True) -> tuple[bool, float]:
        """Retorna (dirigido, confiança)."""
        lowered = text.lower().strip()
        if not lowered:
            return False, 0.0

        # 1. Chamou pelo nome
        for name in self.TRIGGER_NAMES:
            if name in lowered:
                return True, 0.9

        # 2. Comando direto
        for pat in self.DIRECT_PATTERNS:
            if re.search(pat, lowered):
                return True, 0.7

        # 3. Contexto: pessoa conhecida em interação direta (só ela)
        if speaker_known and solo_speaker:
            return True, 0.6

        return False, 0.2


# ======================================================================
# TTS Engine
# ======================================================================

class TTSVoice(str, Enum):
    """Vozes disponíveis (mapeadas em produção para edge-tts etc.)."""
    MIA_PTBR = "pt-BR-MiaNeural"
    MIA_EN = "en-US-JennyNeural"


class TTSProsody:
    """Mapeia estado emocional → parâmetros de prosódia."""

    # emoção → (rate, pitch, volume)
    EMOTION_MAP = {
        "joy": (1.1, 1.1, 1.0),
        "sadness": (0.9, 0.85, 0.9),
        "anger": (1.05, 1.2, 1.1),
        "calm": (0.95, 1.0, 0.95),
        "curiosity": (1.0, 1.05, 0.95),
        "love": (0.95, 1.0, 1.0),
        "surprise": (1.15, 1.15, 1.05),
        "default": (1.0, 1.0, 1.0),
    }

    @classmethod
    def for_emotion(cls, emotion: str) -> dict[str, float]:
        """Mapeia emoção para prosódia (rate, pitch, volume)."""
        rate, pitch, volume = cls.EMOTION_MAP.get(
            emotion.lower().strip(), cls.EMOTION_MAP["default"]
        )
        return {"rate": rate, "pitch": pitch, "volume": volume}


class TTSEngine:
    """Texto → fala (áudio WAV). `synthesize_fn` plugável.

    Em produção pode apontar para edge-tts (grátis, pt-BR), piper (local),
    ou OpenAI TTS. Padrão: gera um WAV placeholder válido (PCM 16-bit)
    com a prosódia codificada nos metadados.
    """

    def __init__(
        self,
        synthesize_fn: Callable[[str, dict[str, float]], bytes] | None = None,
        voice: TTSVoice = TTSVoice.MIA_PTBR,
    ) -> None:
        self._fn = synthesize_fn or self._default_synthesize
        self._voice = voice
        self._last_audio: bytes | None = None

    @staticmethod
    def _default_synthesize(text: str, prosody: dict[str, float]) -> bytes:
        """Gera WAV placeholder (PCM 16-bit mono 16kHz) com duração ~len(text)."""
        import math
        import struct
        duration = max(0.1, min(5.0, len(text) * 0.06))
        rate = prosody.get("rate", 1.0)
        samples_per_sec = int(16000 * rate)
        n = int(duration * samples_per_sec)
        freq = 220 * prosody.get("pitch", 1.0)
        vol = max(0.1, min(1.0, prosody.get("volume", 1.0)))
        data = bytearray()
        for i in range(n):
            # senoide simples com envelope suave
            v = math.sin(2 * math.pi * freq * i / samples_per_sec)
            env = min(1.0, i / max(1, int(samples_per_sec * 0.01)), (n - i) / max(1, int(samples_per_sec * 0.05)))
            sample = int(32767 * vol * env * v)
            data += struct.pack("<h", sample)
        header = bytearray()
        header += b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE"
        header += b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, 16000, 32000, 2, 16)
        header += b"data" + struct.pack("<I", len(data))
        return bytes(header + data)

    def synthesize(self, text: str, emotion: str = "default") -> bytes:
        """Sintetiza fala com prosódia do estado emocional."""
        prosody = TTSProsody.for_emotion(emotion)
        audio = self._fn(text, prosody)
        self._last_audio = audio
        return audio

    @property
    def last_audio(self) -> bytes | None:
        return self._last_audio


# ======================================================================
# Audio Event Bus — wrapper de eventos de áudio
# ======================================================================

class AudioEventBus:
    """Emite eventos tipados de áudio no EventBus global."""

    def __init__(self, bus: EventBus | None = None) -> None:
        self._bus = bus or EventBus()

    def speech_detected(self, segment: SpeechSegment, source: str = "voice") -> None:
        self._bus.emit(Event(
            type=EventType.SPEECH_DETECTED,
            payload={"start": segment.start_s, "end": segment.end_s, "level": segment.level},
            source=source,
        ))

    def speech_transcribed(self, transcript: Transcript, source: str = "voice") -> None:
        self._bus.emit(Event(
            type=EventType.SPEECH_TRANSCRIBED,
            payload={"text": transcript.text, "confidence": transcript.confidence},
            source=source,
        ))

    def speaker_identified(self, speaker_id: str | None, is_known: bool, source: str = "voice") -> None:
        self._bus.emit(Event(
            type=EventType.SPEAKER_IDENTIFIED,
            payload={"speaker_id": speaker_id, "is_known": is_known},
            source=source,
        ))

    def speech_directed(self, directed: bool, confidence: float, source: str = "voice") -> None:
        etype = EventType.SPEECH_DIRECTED if directed else EventType.SPEECH_IGNORED
        self._bus.emit(Event(
            type=etype,
            payload={"confidence": confidence},
            source=source,
        ))

    def tts_generated(self, emotion: str, duration_s: float, source: str = "voice") -> None:
        self._bus.emit(Event(
            type=EventType.TTS_GENERATED,
            payload={"emotion": emotion, "duration_s": duration_s},
            source=source,
        ))


# ======================================================================
# Voice Pipeline — orquestra tudo
# ======================================================================

class VoicePipeline:
    """Pipeline completo: áudio → VAD → STT → speaker → directed → eventos.

    Integração com Cognitive Core: quando fala dirigida é detectada,
    emite MIGUEL_SPOKE (ou evento genérico) que o Cognitive Core processa.
    """

    def __init__(
        self,
        db: SQLiteConnection,
        stt_fn: Callable[[AudioChunk], tuple[str, float]] | None = None,
        profile_fn: Callable[[AudioChunk], str | None] | None = None,
        tts_fn: Callable[[str, dict[str, float]], bytes] | None = None,
        bus: EventBus | None = None,
    ) -> None:
        self._db = db
        self.vad = VAD()
        self.stt = STTEngine(stt_fn)
        self.speaker = SpeakerRecognizer(db, profile_fn)
        self.directed = DirectedSpeechDetector()
        self.tts = TTSEngine(tts_fn)
        self.audio_events = AudioEventBus(bus)
        self._bus = bus or EventBus()

    def process_audio(self, chunk: AudioChunk) -> Transcript | None:
        """Processa um chunk de áudio. Retorna Transcript se houve fala dirigida."""
        segments = self.vad.detect_speech(chunk)
        if not segments:
            return None

        # VAD
        for seg in segments:
            self.audio_events.speech_detected(seg)

        # STT (usa o primeiro segmento com texto)
        text, conf = self.stt.transcribe(chunk)
        if not text.strip():
            return None

        # Speaker
        speaker_id, is_known, sconf = self.speaker.identify(chunk)
        speaker_name = "conhecido" if is_known else "desconhecido"
        if speaker_id:
            from mia_pkg.social import Person
            person = PeopleStore(self._db).get(speaker_id)
            if person:
                speaker_name = person.name
        self.audio_events.speaker_identified(speaker_id, is_known)

        # Directed
        directed, dconf = self.directed.is_directed(
            text, speaker_known=is_known, solo_speaker=True
        )
        self.audio_events.speech_directed(directed, dconf)

        transcript = Transcript(
            text=text,
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            confidence=min(conf, sconf, 1.0),
            directed_to_mia=directed,
            is_known_speaker=is_known,
        )
        self.audio_events.speech_transcribed(transcript)

        # Integração com Cognitive Core: fala dirigida → MIGUEL_SPOKE
        if directed:
            self._bus.emit(Event(
                type=EventType.MIGUEL_SPOKE,
                payload={"text": text, "speaker": speaker_name},
                source="voice_pipeline",
            ))
        return transcript

    def speak(self, text: str, emotion: str = "default") -> bytes:
        """Gera fala para a Mia (TTS) e emite evento."""
        audio = self.tts.synthesize(text, emotion)
        dur = len(audio) / 32000.0  # estimativa WAV 16kHz mono 16-bit
        self.audio_events.tts_generated(emotion, round(dur, 2))
        return audio