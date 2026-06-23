# Coolify deployment notes (Phase 0/1)

The API ships as one container (`services/api/Dockerfile`) plus managed Postgres.
Redis is provisioned but unused until Phase 4.

## Services

| Service     | Phase | Responsibility |
|-------------|-------|----------------|
| chess-api   | 0     | HTTP API, health/readiness, runs migrations as a release step |
| postgres    | 0     | Durable users/games/moves; automated backups + tested restore |
| redis       | 0     | Coordination only; introduced for real in Phase 4 |

## Required environment

| Variable               | Example                                                    |
|------------------------|------------------------------------------------------------|
| `CHESS_ENVIRONMENT`    | `production`                                               |
| `CHESS_DATABASE_URL`   | `postgresql+asyncpg://USER:PASS@HOST:5432/chess`          |
| `CHESS_LOG_LEVEL`      | `INFO`                                                     |
| `CHESS_REDIS_URL`      | unset until Phase 4 (`redis://HOST:6379/0`)               |

## Health checks

- Liveness: `GET /health` → `200 {"status":"ok"}` (no dependencies touched).
- Readiness: `GET /ready` → `200` when Postgres (and Redis, if configured) answer;
  `503` otherwise. Point Coolify's health check at `/ready`.

## Migrations

Run as an explicit, observable release action — never as a hidden startup hook in
multiple replicas:

```
alembic upgrade head      # forward
alembic downgrade -1      # rollback one revision
```

## Release checklist

- Migrations applied and verified before new image serves traffic.
- A database restore has been exercised (a backup is not real until restored).
- Prior image tag + `alembic downgrade` target recorded for rollback.
- Separate staging and production environments, secrets, and databases.
