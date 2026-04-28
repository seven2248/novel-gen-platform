"""
Truth Files 导出器

从 Story State Core 投影出 Markdown 文件：
- chapters.md      — 各章节摘要和状态
- hooks.md         — 伏笔/钩子状态
- characters.md    — 角色状态

由 committer 成功后触发增量刷新。
"""
import json
from pathlib import Path
from datetime import datetime
from sqlmodel import select


def export_truth_files(repo, project_id: str, output_dir: str | Path | None = None) -> dict[str, Path]:
    """
    导出项目的所有 Truth Files。

    Args:
        repo: StoryStateRepository 实例
        project_id: 项目 ID
        output_dir: 输出目录（默认 ~/.novel-gen/{project_id}/truth_files/）

    Returns:
        导出文件路径字典 {"chapters": path, "hooks": path, "characters": path}
    """
    from services.api.app.models.story_state import ChapterState

    story_state = repo.get_or_create_project(project_id)
    chapters = repo.session.exec(select(ChapterState).where(
        ChapterState.project_id == project_id
    )).all()

    if output_dir is None:
        output_dir = Path.home() / ".novel-gen" / project_id / "truth_files"
    else:
        output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = {}

    # 导出 chapters.md
    chapters_path = output_dir / "chapters.md"
    files["chapters"] = chapters_path
    chapters_path.write_text(_render_chapters_md(story_state, chapters), encoding="utf-8")

    # 导出 hooks.md
    hooks_path = output_dir / "hooks.md"
    files["hooks"] = hooks_path
    hooks_path.write_text(_render_hooks_md(story_state), encoding="utf-8")

    # 导出 characters.md
    characters_path = output_dir / "characters.md"
    files["characters"] = characters_path
    characters_path.write_text(_render_characters_md(story_state), encoding="utf-8")

    return files


def export_chapter_delta(repo, project_id: str, chapter_id: str, output_dir: str | Path | None = None) -> dict[str, Path]:
    """
    增量刷新单个章节的 Truth Files 投影（不重写全量文件）。
    比 export_truth_files 更快，适合频繁调用。
    """
    if output_dir is None:
        output_dir = Path.home() / ".novel-gen" / project_id / "truth_files"
    else:
        output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    story_state = repo.get_or_create_project(project_id)
    chapter = repo.get_chapter(project_id, chapter_id)

    # 增量刷新 chapters.md（追加或更新该章节的段落）
    chapters_path = output_dir / "chapters.md"
    _update_chapters_md(chapters_path, story_state, chapter)

    return {"chapters": chapters_path}


# ------------------------------------------------------------------
# 渲染函数
# ------------------------------------------------------------------

def _render_chapters_md(story_state, chapters: list) -> str:
    lines = [
        "# 章节总览",
        "",
        f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]

    if not chapters:
        lines.append("*（暂无章节）*")
        return "\n".join(lines)

    for ch in sorted(chapters, key=lambda c: c.chapter_number):
        lines.append(f"## 第 {ch.chapter_number} 章 — {ch.title or ch.chapter_id}")
        lines.append("")
        lines.append(f"- **状态**: {ch.state}")
        lines.append(f"- **字数**: {ch.word_count}")
        lines.append(f"- **版本**: v{ch.version}")
        if ch.summary:
            lines.append(f"- **摘要**: {ch.summary}")
        lines.append("")
        # 如果有内容，附上关键字段
        if ch.content_json and ch.content_json != "{}":
            try:
                content = json.loads(ch.content_json)
                if content.get("draft_text"):
                    text = content["draft_text"]
                    excerpt = text[:300].replace("\n", " ")
                    lines.append(f"  > {excerpt}...")
            except Exception:
                pass
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def _render_hooks_md(story_state) -> str:
    lines = [
        "# 伏笔 / 钩子总览",
        "",
        f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]

    hooks = story_state.get_hooks() if hasattr(story_state, "get_hooks") else []
    if not hooks:
        lines.append("*（暂无伏笔）*")
        return "\n".join(lines)

    open_hooks = [h for h in hooks if h.get("status") == "open"]
    closed_hooks = [h for h in hooks if h.get("status") != "open"]

    if open_hooks:
        lines.append("## 进行中")
        lines.append("")
        for h in open_hooks:
            introduced = h.get("chapter_introduced", "?")
            lines.append(f"- [{h.get('id', '?')}] **{h.get('type', 'unknown')}** — {h.get('description', '')}")
            lines.append(f"  - 引出章节: 第 {introduced} 章 | 状态: {h.get('status')}")
            lines.append("")

    if closed_hooks:
        lines.append("## 已回收")
        lines.append("")
        for h in closed_hooks:
            introduced = h.get("chapter_introduced", "?")
            lines.append(f"- ~~[{h.get('id', '?')}] {h.get('type', 'unknown')}~~ — {h.get('description', '')}")
            lines.append(f"  - 引出章节: 第 {introduced} 章 | 状态: ~~{h.get('status')}~~")
            lines.append("")

    return "\n".join(lines)


def _render_characters_md(story_state) -> str:
    lines = [
        "# 角色总览",
        "",
        f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]

    characters = story_state.get_characters() if hasattr(story_state, "get_characters") else []
    if not characters:
        lines.append("*（暂无角色）*")
        return "\n".join(lines)

    for char in characters:
        lines.append(f"## {char.get('name', '?')}")
        lines.append("")
        lines.append(f"- **ID**: `{char.get('id', '')}`")
        lines.append(f"- **状态**: {char.get('status', 'unknown')}")
        if char.get("location"):
            lines.append(f"- **位置**: {char['location']}")
        if char.get("role"):
            lines.append(f"- **角色**: {char['role']}")
        if char.get("description"):
            lines.append(f"- **描述**: {char['description']}")
        lines.append("")

    return "\n".join(lines)


def _update_chapters_md(chapters_path: Path, story_state, chapter) -> None:
    """
    增量更新 chapters.md：若该章节段落已存在则替换，否则追加。
    """
    if chapters_path.exists():
        content = chapters_path.read_text(encoding="utf-8")
    else:
        content = ""

    new_section = _render_chapter_section(story_state, chapter)

    # 检查是否已存在该章节
    marker = f"## 第 {chapter.chapter_number} 章"
    if marker in content:
        # 替换旧段落
        import re
        pattern = re.compile(
            rf"(^## 第 {re.escape(str(chapter.chapter_number))} 章.*?)(?=\n## |$)",
            re.MULTILINE | re.DOTALL
        )
        new_content = pattern.sub(new_section.strip(), content)
    else:
        # 追加
        new_content = content.rstrip() + "\n" + new_section

    chapters_path.write_text(new_content, encoding="utf-8")


def _render_chapter_section(story_state, chapter) -> str:
    lines = [
        f"## 第 {chapter.chapter_number} 章 — {chapter.title or chapter.chapter_id}",
        "",
        f"- **状态**: {chapter.state}",
        f"- **字数**: {chapter.word_count}",
        f"- **版本**: v{chapter.version}",
    ]
    if chapter.summary:
        lines.append(f"- **摘要**: {chapter.summary}")
    lines.append("")
    return "\n".join(lines) + "\n"
