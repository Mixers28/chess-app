"""Chess API — FastAPI modular monolith.

Boundaries (auth / games / matchmaking / ai) are kept clear in code but ship as a
single deployable. PostgreSQL is authoritative; Redis (when introduced) is for
coordination only and must remain reconstructable or disposable.
"""

__version__ = "0.1.0"
