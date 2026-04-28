from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session

from services.api.app.models.story_state import StoryState
from services.api.app.repositories.story_state_repository import StoryStateRepository

router = APIRouter(prefix="/projects", tags=["projects"])


def get_session():
    # 注意：实际使用时需通过依赖注入提供 session
    # 测试时由 conftest.py 的 client fixture 注入
    raise RuntimeError("Session not configured. Ensure session dependency is overridden in tests.")


@router.get("/{project_id}")
def get_project(project_id: str, session: Session = Depends(get_session)):
    """
    Read-only — returns 404 if project does not exist.

    Note: This is a breaking change from prior behavior where a missing project
    was automatically created (GET was effectively upsert). Callers that relied on
    auto-create should switch to POST /projects/{project_id}.
    """
    repo = StoryStateRepository(session)
    state = repo.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="project_not_found")
    return {
        "project_id": state.project_id,
        "title": state.title,
        "genre": state.genre,
        "style": state.style,
        "chapters_json": state.chapters_json,
    }


@router.post("/{project_id}")
def create_project(
    project_id: str,
    payload: dict,
    session: Session = Depends(get_session)
):
    """Create or update project — idempotent PUT semantics.

    - If project does not exist: creates it with given fields.
    - If project exists: updates title/genre/style with non-empty values from payload.
    """
    repo = StoryStateRepository(session)
    state = repo.upsert_project(
        project_id,
        title=payload.get("title", ""),
        genre=payload.get("genre", ""),
        style=payload.get("style", "")
    )
    return {
        "project_id": state.project_id,
        "title": state.title,
        "genre": state.genre,
        "style": state.style,
    }
