import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
import json

from packages.agents.src.main_flow import run_main_flow
from services.api.app._shared import _llm_pool, LLM_TIMEOUT_SECONDS, MAX_STORY_STATE_SIZE

router = APIRouter(prefix="/agent-runs", tags=["agent-runs"])


class MainFlowPayload(BaseModel):
    story_state: dict
    chapter_goal: str
    chapter_id: str | None = None
    chapter_num: int | None = None

    @field_validator("story_state")
    @classmethod
    def check_story_state_size(cls, v: dict) -> dict:
        size = len(json.dumps(v, ensure_ascii=False).encode("utf-8"))
        if size > MAX_STORY_STATE_SIZE:
            raise ValueError(f"story_state exceeds 10 MB limit ({size} bytes)")
        return v


@router.post(
    "/main-flow",
    responses={
        422: {"description": "story_state exceeds 10 MB limit"},
        504: {"description": "Agent run timed out after 10 minutes"},
        500: {"description": "Agent run failed due to internal error"},
    },
)
async def create_main_flow_run(
    payload: MainFlowPayload,
):
    """
    Thin HTTP wrapper around run_main_flow() with 10-minute timeout.

    Cancellation note: asyncio.wait_for cannot forcibly stop a blocking thread.
    If a timeout fires, the thread continues running in the background until the
    LLM call returns; we can only abandon (not kill) it. For true cancellation,
    move to a subprocess or use an async-aware LLM client.
    """
    future = _llm_pool.submit(
        run_main_flow,
        story_state=payload.story_state,
        chapter_goal=payload.chapter_goal,
        chapter_id=payload.chapter_id,
        chapter_num=payload.chapter_num,
    )
    # Convert concurrent.futures.Future → asyncio.Future for wait_for
    afuture = asyncio.wrap_future(future)
    try:
        return await asyncio.wait_for(afuture, timeout=float(LLM_TIMEOUT_SECONDS))
    except asyncio.TimeoutError:
        # Request cancellation of the asyncio.Future; the concurrent thread
        # will continue running (we cannot kill it from here). On next call the
        # pool reuses a worker thread after this one finishes.
        afuture.cancel()
        raise HTTPException(
            status_code=504,
            detail="Agent run timed out after 10 minutes. "
                   "The underlying thread has been abandoned; "
                   "verify no duplicate operations occur.",
        )
    except ValueError:
        raise  # let FastAPI's native Pydantic/validation handler return 422
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent run failed: {e!s}",
        )
