from __future__ import annotations

# Synthetic account that "owns" the AI side of an ai-mode game. Moves the orchestrator
# applies are attributed to this user so the existing turn/authorization checks in
# GameService work unchanged. It is a fixed, reserved id.
AI_USER_ID = "00000000-0000-0000-0000-0000000000a1"
AI_USERNAME = "AI"

# Engine label recorded on a move when the AI service could not be used and the
# orchestrator fell back to a locally-chosen legal move.
FALLBACK_ENGINE = "fallback-random"
