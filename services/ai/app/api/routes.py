from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from app.registry import BotRegistry
from app.schemas import DifficultiesResponse, MoveRequest, MoveResponse
from app.service import MoveService

router = APIRouter(tags=["ai"])


def get_registry(request: Request) -> BotRegistry:
    return request.app.state.registry


def get_service(registry: BotRegistry = Depends(get_registry)) -> MoveService:
    return MoveService(registry)


@router.post("/v1/move", response_model=MoveResponse)
async def choose_move(
    body: MoveRequest, service: MoveService = Depends(get_service)
) -> MoveResponse:
    return await service.choose_move(body)


@router.get("/v1/difficulties", response_model=DifficultiesResponse)
async def difficulties(registry: BotRegistry = Depends(get_registry)) -> DifficultiesResponse:
    return DifficultiesResponse(
        difficulties=registry.names(), stockfish_available=registry.stockfish_available
    )


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(
    response: Response, registry: BotRegistry = Depends(get_registry)
) -> dict[str, object]:
    # The service is stateless and ready as soon as the baseline bots load; the engine
    # is optional, so its absence does not make the service unready.
    return {"ready": True, "stockfish_available": registry.stockfish_available}
