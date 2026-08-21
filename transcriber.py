"""
On-device voice transcription for StickyNotes.

Records the microphone and transcribes locally with whisper.cpp
(pywhispercpp) using the base.en model -- the same model EchoNotes proved
reliable on CPU. No cloud, no account; the model downloads once on first use
and then everything runs offline.

Tiering:
    - Free ("Preview"): each clip is capped at PREVIEW_SECONDS.
    - Pro: unlimited clip length.

All heavy dependencies are imported lazily and defensively, so StickyNotes
still runs if audio/whisper libraries are missing or fail to load -- callers
check available() first and fall back gracefully.
"""

import os
import threading
import tempfile
from pathlib import Path

APP_MODEL = "base.en"        # matches EchoNotes' proven CPU model
SAMPLE_RATE = 16000          # whisper expects 16 kHz mono
PREVIEW_SECONDS = 15         # free-tier per-clip cap

_import_error = None

try:
    import numpy as np
    import sounddevice as sd
    _HAVE_AUDIO = True
except Exception as e:          # ImportError, OSError (no PortAudio), etc.
    _HAVE_AUDIO = False
    _import_error = e

try:
    from pywhispercpp.model import Model as _WhisperModel
    _HAVE_WHISPER = True
except Exception as e:
    _HAVE_WHISPER = False
    if _import_error is None:
        _import_error = e


def available():
    """True if voice transcription can run in this build/environment."""
    return _HAVE_AUDIO and _HAVE_WHISPER


def unavailable_reason():
    if available():
        return ""
    return ("Voice transcription needs the audio libraries, which aren't "
            "available here.\n\n(%s)" % _import_error)


def _models_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = Path(base) / "StickyNotes" / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


def model_present():
    """True if the whisper model file has already been downloaded."""
    try:
        for f in _models_dir().glob("*base.en*.bin"):
            if f.stat().st_size > 1_000_000:
                return True
    except Exception:
        pass
    return False


_model = None
_model_lock = threading.Lock()


def _get_model():
    """Load (and, on first use, download) the whisper model. Blocking --
    must be called off the UI thread."""
    global _model
    with _model_lock:
        if _model is None:
            _model = _WhisperModel(
                APP_MODEL,
                models_dir=str(_models_dir()),
                redirect_whispercpp_logs_to=False,
            )
        return _model


class Recorder:
    """Records mic audio until stopped (or, on the free tier, until the
    preview cap is reached), then transcribes it. One Recorder per clip."""

    def __init__(self, is_pro=False, on_cap=None):
        self.is_pro = bool(is_pro)
        self.on_cap = on_cap                 # called from the audio thread on cap
        self._frames = []
        self._stream = None
        self._recording = False
        self._capped = False
        self._collected = 0
        self._max_frames = None if self.is_pro else int(PREVIEW_SECONDS * SAMPLE_RATE)

    # -- recording ----------------------------------------------------------
    def start(self):
        if not available():
            raise RuntimeError(unavailable_reason())
        self._frames = []
        self._collected = 0
        self._capped = False
        self._recording = True
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32",
            callback=self._callback,
        )
        self._stream.start()

    def _callback(self, indata, frames, time_info, status):
        if not self._recording:
            return
        self._frames.append(indata.copy())
        self._collected += frames
        if self._max_frames is not None and self._collected >= self._max_frames:
            self._recording = False
            self._capped = True
            if self.on_cap:
                try:
                    self.on_cap()
                except Exception:
                    pass

    def stop(self):
        self._recording = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    @property
    def capped(self):
        return self._capped

    def has_audio(self):
        return bool(self._frames)

    # -- transcription ------------------------------------------------------
    def transcribe(self):
        """Transcribe the recorded audio. Blocking -- call off the UI thread.
        Returns the recognized text (possibly empty)."""
        if not self._frames:
            return ""
        audio = np.concatenate(self._frames, axis=0).astype("float32").flatten()
        if self._max_frames is not None and len(audio) > self._max_frames:
            audio = audio[: self._max_frames]
        if len(audio) < SAMPLE_RATE // 4:       # < ~0.25s -> nothing useful
            return ""
        model = _get_model()
        try:
            segments = model.transcribe(audio)
        except Exception:
            # Some pywhispercpp builds want a file path rather than an array.
            segments = self._transcribe_via_wav(audio, model)
        parts = []
        for seg in segments:
            t = getattr(seg, "text", "") or ""
            t = t.strip()
            if t:
                parts.append(t)
        return " ".join(parts).strip()

    def _transcribe_via_wav(self, audio, model):
        import wave
        pcm = np.clip(audio, -1.0, 1.0)
        pcm16 = (pcm * 32767.0).astype("<i2")
        tmp = Path(tempfile.gettempdir()) / ("stickynotes_rec_%d.wav" % os.getpid())
        with wave.open(str(tmp), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(pcm16.tobytes())
        try:
            return model.transcribe(str(tmp))
        finally:
            try:
                tmp.unlink()
            except Exception:
                pass
