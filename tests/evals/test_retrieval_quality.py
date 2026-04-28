"""
Tests for retrieval quality scorer.
"""

import pytest
from evals.scorers.retrieval_quality import (
    score_retrieval_quality,
    _check_character_retention,
    _check_hook_tracking,
    _check_information_loss,
)


class TestScoreRetrievalQuality:
    def test_passes_when_all_checks_satisfied(self):
        story_state = {
            "characters": [
                {
                    "id": "char-1",
                    "name": "李明",
                    "status": "active",
                    "chapter_introduced": 1,
                },
                {
                    "id": "char-2",
                    "name": "王师兄",
                    "status": "dead",
                    "chapter_introduced": 1,
                },
            ],
            "hooks": [
                {
                    "id": "hook-1",
                    "type": "foreshadow",
                    "status": "open",
                    "description": "经脉之日的秘密",
                    "chapter_introduced": 1,
                }
            ],
            "chapters": [
                {
                    "chapter_id": "ch-1",
                    "chapter_number": 1,
                    "summary": "第1章：李明进入青云宗，王师兄带他熟悉山门。",
                    "word_count": 1200,
                    "state": "committed",
                },
                {
                    "chapter_id": "ch-2",
                    "chapter_number": 2,
                    "summary": "第2章：王师兄在宗门试炼中意外身亡，李明悲痛万分。",
                    "word_count": 1500,
                    "state": "committed",
                },
            ],
            "plot_markers": [],
        }
        summary = "第3章：李明在师父指导下开始修炼，想起王师兄身亡的悲痛，决心查明经脉之日的秘密。"

        result = score_retrieval_quality(
            chapter_summary=summary,
            story_state=story_state,
            target_chapter_num=3,
            checks={
                "character_retention": True,
                "hook_tracking": True,
                "no_information_loss": True,
            },
        )
        assert result["passed"] is True
        assert "character_retention" not in result["failures"]
        assert "hook_tracking" not in result["failures"]

    def test_fails_when_character_death_not_reflected(self):
        story_state = {
            "characters": [
                {
                    "id": "char-2",
                    "name": "王师兄",
                    "status": "dead",
                    "chapter_introduced": 1,
                },
            ],
            "hooks": [],
            "chapters": [
                {
                    "chapter_id": "ch-2",
                    "chapter_number": 2,
                    "summary": "第2章：王师兄在宗门试炼中意外身亡。",
                    "word_count": 1500,
                    "state": "committed",
                },
            ],
            "plot_markers": [],
        }
        # Summary mentions the character but NOT the death
        summary = "第3章：李明在师父指导下开始修炼，王师兄曾带他熟悉山门。"

        result = score_retrieval_quality(
            chapter_summary=summary,
            story_state=story_state,
            target_chapter_num=3,
            checks={"character_retention": True},
        )
        assert result["passed"] is False
        assert "character_retention" in result["failures"]

    def test_fails_when_active_character_not_mentioned(self):
        story_state = {
            "characters": [
                {
                    "id": "char-1",
                    "name": "李明",
                    "status": "active",
                    "chapter_introduced": 1,
                },
                {
                    "id": "char-2",
                    "name": "小芳",
                    "status": "active",
                    "chapter_introduced": 2,
                },
            ],
            "hooks": [],
            "chapters": [
                {
                    "chapter_id": "ch-2",
                    "chapter_number": 2,
                    "summary": "第2章：李明结识小芳，两人渐生情愫。",
                    "word_count": 1400,
                    "state": "committed",
                },
            ],
            "plot_markers": [],
        }
        # Summary talks about the chapter goal but never mentions 小芳
        summary = "第3章：李明在修炼中感到进展缓慢，师父前来指点。"

        result = score_retrieval_quality(
            chapter_summary=summary,
            story_state=story_state,
            target_chapter_num=3,
            checks={"character_retention": True},
        )
        assert result["passed"] is False
        assert "character_retention" in result["failures"]

    def test_fails_when_open_hook_not_tracked(self):
        story_state = {
            "characters": [],
            "hooks": [
                {
                    "id": "hook-1",
                    "type": "mystery",
                    "status": "open",
                    "description": "神秘古剑的秘密",
                    "chapter_introduced": 1,
                }
            ],
            "chapters": [
                {
                    "chapter_id": "ch-1",
                    "chapter_number": 1,
                    "summary": "第1章：李明进入青云宗，得知古剑传说。",
                    "word_count": 1200,
                    "state": "committed",
                },
            ],
            "plot_markers": [],
        }
        summary = "第3章：李明开始修炼，师父指导他运气的技巧。"

        result = score_retrieval_quality(
            chapter_summary=summary,
            story_state=story_state,
            target_chapter_num=3,
            checks={"hook_tracking": True},
        )
        assert result["passed"] is False
        assert "hook_tracking" in result["failures"]

    def test_passes_when_hook_resolution_detected(self):
        story_state = {
            "characters": [],
            "hooks": [
                {
                    "id": "hook-1",
                    "type": "mystery",
                    "status": "open",
                    "description": "古剑之谜",
                    "chapter_introduced": 1,
                }
            ],
            "chapters": [
                {
                    "chapter_id": "ch-4",
                    "chapter_number": 4,
                    "summary": "第4章：古剑异动加剧。",
                    "word_count": 1400,
                    "state": "committed",
                },
            ],
            "plot_markers": [],
        }
        # Summary shows the hook being resolved
        summary = "第5章：古剑之谜揭开，真相终于大白！"

        result = score_retrieval_quality(
            chapter_summary=summary,
            story_state=story_state,
            target_chapter_num=5,
            checks={"hook_tracking": True},
        )
        assert result["passed"] is True

    def test_fails_when_information_loss_detected(self):
        story_state = {
            "characters": [],
            "hooks": [],
            "chapters": [
                {
                    "chapter_id": "ch-1",
                    "chapter_number": 1,
                    "summary": "第1章：李明在后山发现一把古剑，剑身刻有「青云」二字，赵长老神色骤变。",
                    "word_count": 1300,
                    "state": "committed",
                },
            ],
            "plot_markers": [
                {"text": "青云二字", "chapter": 1},
                {"text": "赵长老神色骤变", "chapter": 1},
            ],
        }
        # Summary omits the key plot markers
        summary = "第2章：李明发现古剑，赵长老反应异常。"

        result = score_retrieval_quality(
            chapter_summary=summary,
            story_state=story_state,
            target_chapter_num=2,
            checks={"no_information_loss": True},
        )
        assert result["passed"] is False
        assert "no_information_loss" in result["failures"]

    def test_first_chapter_returns_true_no_prior_context(self):
        story_state = {
            "characters": [
                {
                    "id": "char-1",
                    "name": "李明",
                    "status": "active",
                    "chapter_introduced": 1,
                }
            ],
            "hooks": [
                {
                    "id": "hook-1",
                    "type": "foreshadow",
                    "status": "open",
                    "description": "入门考验",
                    "chapter_introduced": 1,
                }
            ],
            "chapters": [],
            "plot_markers": [],
        }
        summary = "第1章：李明站在青云宗山门外，深吸一口气准备入门考验。"

        result = score_retrieval_quality(
            chapter_summary=summary,
            story_state=story_state,
            target_chapter_num=1,
            checks={"character_retention": True, "hook_tracking": True},
        )
        assert result["passed"] is True

    def test_details_populated_on_failure(self):
        story_state = {
            "characters": [
                {
                    "id": "char-1",
                    "name": "李明",
                    "status": "active",
                    "chapter_introduced": 1,
                },
            ],
            "hooks": [
                {
                    "id": "hook-1",
                    "type": "mystery",
                    "status": "open",
                    "description": "古剑秘密",
                    "chapter_introduced": 1,
                }
            ],
            "chapters": [
                {
                    "chapter_id": "ch-1",
                    "chapter_number": 1,
                    "summary": "第1章：李明得知古剑秘密。",
                    "word_count": 1000,
                    "state": "committed",
                },
            ],
            "plot_markers": [],
        }
        summary = "第2章：李明开始修炼，与平日无异。"

        result = score_retrieval_quality(
            chapter_summary=summary,
            story_state=story_state,
            target_chapter_num=3,
            checks={"hook_tracking": True},
        )
        assert result["passed"] is False
        assert "details" in result
        assert "hook_tracking" in result["details"]
        assert len(result["details"]["hook_tracking"]["untracked"]) > 0


class TestCheckCharacterRetention:
    def test_no_prior_chapters_returns_true(self):
        story_state = {"characters": [], "chapters": []}
        result = _check_character_retention("", story_state, 1)
        assert result["passed"] is True

    def test_first_chapter_returns_true(self):
        story_state = {
            "characters": [
                {
                    "id": "char-1",
                    "name": "李明",
                    "status": "active",
                    "chapter_introduced": 1,
                }
            ],
            "chapters": [],
        }
        result = _check_character_retention("第1章：李明进入宗门。", story_state, 1)
        assert result["passed"] is True


class TestCheckHookTracking:
    def test_target_chapter_2_returns_true(self):
        story_state = {
            "hooks": [
                {
                    "id": "hook-1",
                    "type": "foreshadow",
                    "status": "open",
                    "chapter_introduced": 1,
                }
            ],
            "chapters": [
                {
                    "chapter_id": "ch-1",
                    "chapter_number": 1,
                    "summary": "intro",
                    "state": "committed",
                }
            ],
        }
        result = _check_hook_tracking("第2章：李明通过考验。", story_state, 2)
        assert result["passed"] is True


class TestCheckInformationLoss:
    def test_no_prior_chapters_returns_true(self):
        story_state = {"chapters": [], "plot_markers": []}
        result = _check_information_loss("第1章：开始。", story_state, 1)
        assert result["passed"] is True

    def test_one_hook_resolved_other_not_tracked(self):
        """
        当章节摘要解决了 hook-1 但未提及 hook-2 时，
        hook_tracking 应该 FAIL —— hook-2 未被追踪。
        这是对 line 207 全局解决标记检查 Bug 的回归测试。
        """
        story_state = {
            "characters": [],
            "hooks": [
                {
                    "id": "hook-1",
                    "type": "mystery",
                    "status": "open",
                    "description": "古剑之谜",
                    "chapter_introduced": 1,
                },
                {
                    "id": "hook-2",
                    "type": "foreshadow",
                    "status": "open",
                    "description": "神秘遗迹",
                    "chapter_introduced": 1,
                },
            ],
            "chapters": [
                {
                    "chapter_id": "ch-1",
                    "chapter_number": 1,
                    "summary": "第1章：李明进入青云宗，得知古剑传说。",
                    "word_count": 1200,
                    "state": "committed",
                },
            ],
            "plot_markers": [],
        }
        # 摘要解决了 hook-1（古剑之谜），但完全没有提及 hook-2（神秘遗迹）
        summary = "第5章：古剑之谜揭开，真相终于大白。"

        result = score_retrieval_quality(
            chapter_summary=summary,
            story_state=story_state,
            target_chapter_num=5,
            checks={"hook_tracking": True},
        )

        assert result["passed"] is False
        assert "hook_tracking" in result["failures"]
        assert len(result["details"]["hook_tracking"]["untracked"]) == 1
        assert result["details"]["hook_tracking"]["untracked"][0]["hook_id"] == "hook-2"


