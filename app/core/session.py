"""
app/core/session.py

Conversation pattern detection module.
Provides get_pattern_signal(history) which scans conversation history for
repeated psychological/emotional themes and signals Dev 2 when a persistent
pattern emerges after the 5th turn (> 10 messages).
"""

from __future__ import annotations

# ── Pattern theme keyword mapping ─────────────────────────────────────────────
# Each key is a pattern name; values are keyword lists to scan for in user text.
# Patterns are distinct from session-level emotions — these are structural
# patterns that indicate something recurring across the conversation.
_PATTERN_KEYWORDS: dict[str, list[str]] = {
    "isolation":       ["alone", "lonely", "no one", "nobody", "no friends", "disconnected",
                        "isolated", "left out", "excluded", "by myself"],
    "guilt":           ["my fault", "i caused", "blame myself", "blame me", "guilty", "guilt",
                        "shouldn't have", "i should have", "i failed", "i ruined"],
    "comparison":      ["everyone else", "other people", "they have", "they don't", "compared to",
                        "better than me", "worse than me", "they're so", "i'm the only one",
                        "nobody else feels"],
    "helplessness":    ["nothing helps", "nothing works", "what's the point", "no point",
                        "can't do anything", "can't change", "stuck", "trapped", "no way out",
                        "i give up"],
    "catastrophising": ["everything is ruined", "it's all over", "worst thing", "will never",
                        "always like this", "nothing ever", "everything goes wrong",
                        "disaster", "end of the world"],
    "self_criticism":  ["i'm so stupid", "i'm useless", "i'm a failure", "i'm worthless",
                        "i hate myself", "i'm terrible", "i can't do anything right",
                        "i'm the problem", "i'm broken"],
    "rumination":      ["keep thinking", "can't stop thinking", "over and over", "in my head",
                        "replay", "obsessing", "can't let it go", "stuck on", "thought spiral"],
    "exhaustion":      ["exhausted", "so tired", "burnt out", "burned out", "drained",
                        "no energy", "can't get up", "sleep all day", "too tired to"],
}

# Minimum number of messages in history before analysis runs (5 full turns = 10 msgs)
_MIN_MESSAGES_FOR_ANALYSIS = 10

# Minimum keyword hits (across the whole conversation) to declare a pattern
_MIN_HIT_THRESHOLD = 2


def get_pattern_signal(history: list[dict]) -> dict | None:
    """
    Scans conversation history for repeated psychological themes.

    Only activates after turn 5 (i.e., when `history` has > 10 messages).
    Scans only user-role messages. Counts keyword hits per pattern theme.
    Returns the dominant pattern if any theme meets the threshold.

    Parameters
    ----------
    history : list[dict]
        A list of message dicts with at minimum ``role`` and ``content`` keys,
        as returned by ``memory.fetch_history()``.

    Returns
    -------
    dict | None
        ``{"pattern": str, "count": int}`` if a repeated pattern is found.
        ``None`` if history is too short or no pattern clears the threshold.

    Examples
    --------
    >>> get_pattern_signal([])
    None
    >>> get_pattern_signal(history_with_isolation_messages)
    {"pattern": "isolation", "count": 3}
    """
    if len(history) < _MIN_MESSAGES_FOR_ANALYSIS:
        return None  # Too early in conversation to detect patterns

    # Only scan user-side messages
    user_texts = [
        m["content"].lower()
        for m in history
        if m.get("role") == "user" and m.get("content")
    ]

    if not user_texts:
        return None

    corpus = " ".join(user_texts)

    # Score each pattern theme
    pattern_scores: dict[str, int] = {}
    for pattern, keywords in _PATTERN_KEYWORDS.items():
        hits = sum(corpus.count(kw) for kw in keywords)
        if hits >= _MIN_HIT_THRESHOLD:
            pattern_scores[pattern] = hits

    if not pattern_scores:
        return None  # No recurring theme met the threshold

    # Return the most prominent pattern
    dominant = max(pattern_scores, key=lambda p: pattern_scores[p])
    return {"pattern": dominant, "count": pattern_scores[dominant]}
