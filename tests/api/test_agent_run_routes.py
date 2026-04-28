import pytest


def test_agent_run_route_returns_plan_draft_review_and_preview(client, fake_story_state):
    response = client.post(
        "/agent-runs/main-flow",
        json={
            "story_state": fake_story_state,
            "chapter_goal": "生成第1章：主角进入宗门",
            "chapter_id": "ch-1",
            "chapter_num": 1,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["plan"]["beats"]
    assert body["draft"]["draft_text"]
    assert body["review"]["actionable_suggestions"] is not None
    assert body["commit_preview"]["state_diff"] is not None


def test_local_rewrite_route_returns_diff_lines(client, fake_story_state):
    response = client.post(
        "/local-rewrites",
        json={
            "selected_text": "师父看了他一眼，没有说话。",
            "context_before": "夜雨刚停，山门仍冷。",
            "context_after": "李明低头，不敢再问。",
            "story_state": fake_story_state,
            "rewrite_instructions": "加强压抑感",
            "chapter_id": "ch-1",
        },
    )
    assert response.status_code == 200
    assert "diff_lines" in response.json()
