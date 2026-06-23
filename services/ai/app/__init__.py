"""Chess AI service.

Stateless inference behind the game service's AI boundary: given a FEN, a difficulty,
and optional constraints, return a single legal move. The service holds no game state —
the caller (services/api) is authoritative and re-validates every returned move with
python-chess. Baseline bots ship first; Stockfish is an optional stronger backend; a
custom model (e.g. chess-sim) can later register as another difficulty.
"""

__version__ = "0.1.0"
