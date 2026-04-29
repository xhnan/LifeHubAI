"""Health Check Endpoints"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from collections.abc import Iterator

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse

from agent.health.health_main import run_health_agent, stream_health_agent
from app.models import HealthAgentRequest, HealthAgentResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "LifeHubAI",
    }


def _to_sse(event: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def _log_sse_event(event: str, data: dict) -> None:
    logger.info("SSE send event=%s payload=%s", event, json.dumps(data, ensure_ascii=False))


def _build_progress_message(last_event_at: float) -> dict:
    idle_seconds = int(time.time() - last_event_at)
    return {
        "status": "running",
        "message": "health agent is still processing",
        "idle_seconds": idle_seconds,
    }


def _health_agent_event_iter(request: HealthAgentRequest) -> Iterator[dict]:
    try:
        for item in stream_health_agent(message=request.message, user_id=request.user_id):
            yield item
    except Exception as exc:
        yield {
            "event": "error",
            "data": {
                "message": "health agent stream failed",
                "detail": str(exc),
            },
        }


async def _health_agent_event_stream(request: HealthAgentRequest):
    iterator = _health_agent_event_iter(request)
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[dict] = asyncio.Queue()
    done = threading.Event()
    last_event_at = time.time()
    sequence = 0

    def _producer():
        try:
            for item in iterator:
                loop.call_soon_threadsafe(queue.put_nowait, item)
        finally:
            done.set()
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {"event": "__stream_end__", "data": {}},
            )

    threading.Thread(target=_producer, daemon=True).start()

    while True:
        try:
            item = await asyncio.wait_for(queue.get(), timeout=3.0)
            if item["event"] == "__stream_end__":
                break
            sequence += 1
            last_event_at = time.time()
            payload = {"sequence": sequence, "timestamp": int(last_event_at * 1000), **item["data"]}
            _log_sse_event(item["event"], payload)
            yield _to_sse(item["event"], payload)
            if item["event"] in {"done", "error"}:
                break
        except TimeoutError:
            sequence += 1
            payload = {
                "sequence": sequence,
                "timestamp": int(time.time() * 1000),
                **_build_progress_message(last_event_at),
            }
            _log_sse_event("progress", payload)
            yield _to_sse("progress", payload)
            if done.is_set() and queue.empty():
                break


@router.post("/health/agent", response_model=HealthAgentResponse, status_code=status.HTTP_200_OK)
async def health_agent(request: HealthAgentRequest):
    return run_health_agent(message=request.message, user_id=request.user_id)


@router.post("/health/agent/stream", status_code=status.HTTP_200_OK)
async def health_agent_stream(request: HealthAgentRequest):
    return StreamingResponse(
        _health_agent_event_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
