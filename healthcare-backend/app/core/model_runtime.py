"""Coordination primitives for memory-heavy local AI models."""

from threading import RLock


# BGE-M3 and faster-whisper must not load or infer concurrently on the
# constrained Windows demo machine. RLock permits a caller to release another
# model while already holding the shared runtime lock.
HEAVY_MODEL_LOCK = RLock()
