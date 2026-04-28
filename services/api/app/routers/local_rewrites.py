import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
import json

from packages.agents.src.local_rewrite import run_local_rewrite
from services.api.app._shared import _llm_pool, LLM_TIMEOUT_SECONDS, MAX_STORY_STATE_SIZE

router = APIRouter(prefix="/local-rewrites", tags=["local-rewrites"])


class LocalRewritePayload(BaseModel):
    selected_text: str
    context_before: str
    context_after: str
    story_state: dict
    rewrite_instructions: str = ""
    chapter_id: str = "unknown"

    @field_validator("story_state")
    @classmethod
    def check_story_state_size(cls, v: dict) -> dict:
        size = len(json.dumps(v, ensure_ascii=False).encode("utf-8"))
        if size > MAX_STORY_STATE_SIZE:
            raise ValueError(f"story_state exceeds 10 MB limit ({size} bytes)")
        return v


@router.post(
    "",
    responses={
        422: {"description": "story_state exceeds 10 MB limit"},
        504: {"description": "Rewrite timed out after 10 minutes"},
        500: {"description": "Rewrite failed due to internal error"},
    },
)
async def create_local_rewrite(
    payload: LocalRewritePayload,
):
    """
    Thin HTTP wrapper around run_local_rewrite() with 10-minute timeout.

    Cancellation note: asyncio.wait_for cannot forcibly stop a blocking thread.
    If a timeout fires, the thread continues running in the background until the
    LLM call returns; we can only abandon (not kill) it. For true cancellation,
    move to a subprocess or use an async-aware LLM client.
    """
    future = _llm_pool.submit(
        run_local_rewrite,
        selected_text=payload.selected_text,
        context_before=payload.context_before,
        context_after=payload.context_after,
        story_state=payload.story_state,
        rewrite_instructions=payload.rewrite_instructions,
        chapter_id=payload.chapter_id,
    )
    afuture = asyncio.wrap_future(future)
    try:
        return await asyncio.wait_for(afuture, timeout=float(LLM_TIMEOUT_SECONDS))
    except asyncio.TimeoutError:
        afuture.cancel()
        raise HTTPException(
            status_code=504,
            detail="Rewrite timed out after 10 minutes. "
                   "The underlying thread has been abandoned; "
                   "verify no duplicate operations occur.",
        )
    except ValueError:
        raise  # let FastAPI's native Pydantic/validation handler return 422
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Rewrite failed: {e!s}",
        )
