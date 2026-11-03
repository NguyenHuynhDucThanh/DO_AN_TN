"""Runtime compatibility check for the faster-whisper audio decoder."""

from __future__ import annotations

import io
import wave

from faster_whisper.audio import decode_audio


def test_faster_whisper_decodes_wav_with_installed_pyav() -> None:
    """Catch incompatible PyAV upgrades before they break every voice upload."""
    wav_bytes = io.BytesIO()
    with wave.open(wav_bytes, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16_000)
        audio.writeframes(b"\x00\x00" * 1_600)

    wav_bytes.seek(0)
    decoded = decode_audio(wav_bytes, sampling_rate=16_000)

    assert decoded.shape == (1_600,)
