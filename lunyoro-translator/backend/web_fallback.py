"""
Web fallback for translation — stub implementation.
Returns None to fall through to dictionary/corpus fallback.
"""


def lookup_static(word: str, direction: str) -> str | None:
    """Static word lookup — returns None (no static entries)."""
    return None


def web_search_fallback(text: str, direction: str) -> str | None:
    """Web search fallback — disabled in production."""
    return None
