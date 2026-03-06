"""Langfuse tracing helpers for Cascade agent loop."""

from __future__ import annotations

import random
import structlog
from functools import lru_cache

from cascade_api.config import settings

log = structlog.get_logger()

try:
    from langfuse import Langfuse
    from langfuse.decorators import observe, langfuse_context
    HAS_LANGFUSE = True
except ImportError:
    HAS_LANGFUSE = False
    def observe(**kwargs):
        def decorator(fn):
            return fn
        return decorator
    langfuse_context = None
    Langfuse = None


TRIVIAL_MESSAGES = {"status", "tasks", "today", "review"}
EVAL_SAMPLE_RATE = 0.2


@lru_cache
def get_langfuse():
    """Get or create the Langfuse singleton. Returns None if not configured."""
    if not settings.langfuse_public_key or not HAS_LANGFUSE:
        return None
    try:
        return Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    except Exception as e:
        log.warning("langfuse.init_failed", error=str(e))
        return None


def should_eval(user_message, is_scheduled, sample_rate=EVAL_SAMPLE_RATE):
    """Decide whether to run evals on this trace."""
    if is_scheduled:
        return True
    if user_message.strip().lower() in TRIVIAL_MESSAGES:
        return False
    return random.random() < sample_rate


def flush_langfuse():
    """Flush pending Langfuse events. Call at shutdown."""
    lf = get_langfuse()
    if lf:
        try:
            lf.flush()
        except Exception:
            pass
