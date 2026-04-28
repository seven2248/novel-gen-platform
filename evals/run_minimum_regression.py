"""
Minimum regression runner — loads YAML suite and runs checks against agent outputs.
"""
import yaml
from pathlib import Path
from evals.scorers.story_constraints import score_story_constraints, score_local_rewrite


def load_suite(suite_path: str) -> dict:
    """
    Load an evaluation suite from a YAML file.

    Args:
        suite_path: Path to the YAML suite file (e.g. "evals/cases/minimum_set.yaml")

    Returns:
        The parsed YAML dict with 'cases' list
    """
    path = Path(suite_path)
    if not path.exists():
        raise FileNotFoundError(f"Eval suite not found: {suite_path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_case(case: dict, agent_output: dict) -> dict:
    """
    Run a single eval case against agent output.

    Args:
        case: A case dict from the suite YAML
        agent_output: Output from run_main_flow() or run_local_rewrite()

    Returns:
        {"case_id": str, "passed": bool, "results": list[dict]}
    """
    checks = case.get("checks", {})
    case_type = case.get("id", "unknown")

    if "local_rewrite" in case_type or "rewrite" in agent_output:
        scored = score_local_rewrite(agent_output, checks)
    else:
        draft_text = agent_output.get("draft", {}).get("draft_text", "")
        scored = score_story_constraints(draft_text, checks)

    return {
        "case_id": case["id"],
        "passed": scored["passed"],
        "failures": scored["failures"],
    }


def run_suite(suite_path: str, agent_outputs: list[dict]) -> dict:
    """
    Run all cases in a suite against a list of agent outputs.

    Args:
        suite_path: Path to YAML suite
        agent_outputs: List of outputs from agent runs

    Returns:
        Summary dict with total, passed, failed counts
    """
    suite = load_suite(suite_path)
    if len(suite["cases"]) != len(agent_outputs):
        raise ValueError(
            f"Suite has {len(suite['cases'])} cases but {len(agent_outputs)} agent outputs provided"
        )
    results = []
    for case, output in zip(suite["cases"], agent_outputs):
        results.append(run_case(case, output))

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    return {
        "suite": suite["name"],
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "results": results,
    }
