"""AI-native layer: the two-tier brain, auto-config, tagging, NL search and
NL->action parsing. Everything here sits on top of the existing provider/
pipeline stack and degrades gracefully when no LLM is reachable.
"""
from .brain import Brain

__all__ = ["Brain"]
