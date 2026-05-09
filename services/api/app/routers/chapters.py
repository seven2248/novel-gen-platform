from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session

from services.api.app.repositories.story_state_repository import StoryStateRepository
from packages.agents.src.orchestrator import validate_state_transition

router = APIRouter(prefix="/projects", tags=["chapters"])


def get_session():
    raise RuntimeError(
        "Session not configured. Ensure session dependency is overridden in tests."
    )


@router.get("/{project_id}/chapters/{chapter_id}")
def get_chapter(
    project_id: str, chapter_id: str, session: Session = Depends(get_session)
):
    repo = StoryStateRepository(session)
    ch = repo.get_chapter(project_id, chapter_id)
    if not ch:
        raise HTTPException(status_code=404, detail="chapter_not_found")
    return {
        "chapter_id": ch.chapter_id,
        "project_id": ch.project_id,
        "chapter_number": ch.chapter_number,
        "title": ch.title,
        "state": ch.state,
        "version": ch.version,
        "content_json": ch.content_json,
    }


@router.post("/{project_id}/chapters")
def create_chapter(
    project_id: str, payload: dict, session: Session = Depends(get_session)
):
    repo = StoryStateRepository(session)
    # 确保 project 存在
    repo.get_or_create_project(project_id)
    ch = repo.create_chapter(
        project_id,
        chapter_id=payload["chapter_id"],
        chapter_number=payload["chapter_number"],
        title=payload.get("title", ""),
    )
    return {
        "chapter_id": ch.chapter_id,
        "project_id": ch.project_id,
        "chapter_number": ch.chapter_number,
        "title": ch.title,
        "state": ch.state,
        "version": ch.version,
    }


@router.patch("/{project_id}/chapters/{chapter_id}/state")
def patch_chapter_state(
    project_id: str,
    chapter_id: str,
    payload: dict,
    session: Session = Depends(get_session),
):
    repo = StoryStateRepository(session)
    ch = repo.get_chapter(project_id, chapter_id)
    if not ch:
        raise HTTPException(status_code=404, detail="chapter_not_found")

    # 状态机合法性检查（W19: committed→drafting 必须 explicit_reset）
    explicit_reset = payload.get("explicit_reset", False)
    new_state = payload["state"]
    is_valid, reason = validate_state_transition(ch.state, new_state, explicit_reset)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_state_transition",
                "message": reason,
                "current_state": ch.state,
                "requested_state": new_state,
                "explicit_reset": explicit_reset,
            },
        )

    _, success = repo.update_chapter_state(
        project_id,
        chapter_id,
        new_state=new_state,
        expected_version=payload.get("version"),
    )
    if not success:
        raise HTTPException(status_code=409, detail="version_conflict")
    return {
        "chapter_id": ch.chapter_id,
        "project_id": ch.project_id,
        "chapter_number": ch.chapter_number,
        "title": ch.title,
        "state": new_state,
        "version": ch.version,
    }
