from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

from novel_writer.llm_client import build_llm_client
from novel_writer.pipeline import PIPELINE_STEP_ORDER, StoryPipeline
from novel_writer.rerun_policy import ContinuityRerunPolicy
from novel_writer.schema import (
    StoryInput,
    build_publish_ready_bundle_summary,
    comparison_reason_detail_codes,
    project_manifest_contract,
    validate_publish_ready_bundle,
)
from novel_writer.storage import (
    build_project_layout,
    load_artifact,
    load_publish_ready_bundle,
    load_next_action_decision,
    load_project_manifest,
    load_run_comparison_summary,
    save_project_manifest,
    save_run_comparison_summary,
)


DEFAULT_OUTPUT_DIR = "data/latest_run"
DEFAULT_PROJECTS_DIR = "data/projects"


def add_generation_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--theme", help="Story theme")
    parser.add_argument("--genre", help="Story genre")
    parser.add_argument("--tone", help="Story tone")
    parser.add_argument("--target-length", type=int, help="Target length in words or characters")


def add_runtime_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--provider",
        default="mock",
        choices=["mock", "openai", "openai-compatible", "lmstudio", "ollama"],
        help="LLM provider",
    )
    parser.add_argument("--model", default="gpt-4.1-mini", help="Model name for the selected provider")
    parser.add_argument(
        "--base-url",
        help="Override the provider base URL. Required for provider=openai-compatible.",
    )
    parser.add_argument(
        "--api-key",
        help="Override the provider API key. Local OpenAI-compatible providers can use a dummy value if needed.",
    )
    parser.add_argument("--format", default="json", choices=["json", "yaml"], help="Artifact serialization format")
    parser.add_argument(
        "--max-high-severity-chapters",
        type=int,
        help="Override long-run policy limit for high-severity chapters before stopping",
    )
    parser.add_argument(
        "--max-total-rerun-attempts",
        type=int,
        help="Override long-run policy limit for total rerun attempts before stopping",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Short-story generation support pipeline MVP")
    add_generation_arguments(parser)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Directory for generated artifacts")
    parser.add_argument("--project-id", help="Project/story identifier for project-scoped run layout")
    parser.add_argument("--projects-dir", default=DEFAULT_PROJECTS_DIR, help="Base directory for project-scoped runs")
    parser.add_argument(
        "--resume-from-output-dir",
        help="Read existing artifacts and manifest from this directory before continuing",
    )
    parser.add_argument(
        "--rerun-from",
        choices=PIPELINE_STEP_ORDER,
        help="When resuming, rerun from the named pipeline step",
    )
    add_runtime_arguments(parser)

    subparsers = parser.add_subparsers(dest="command")

    create_project = subparsers.add_parser("create-project", help="Create or refresh a project-scoped run")
    add_generation_arguments(create_project)
    create_project.add_argument("--project-id", required=True, help="Project/story identifier")
    create_project.add_argument("--projects-dir", default=DEFAULT_PROJECTS_DIR, help="Base directory for project-scoped runs")
    create_project.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Optional custom run directory")
    add_runtime_arguments(create_project)

    resume_project = subparsers.add_parser("resume-project", help="Resume the current run recorded in a project manifest")
    resume_project.add_argument("--project-id", required=True, help="Project/story identifier")
    resume_project.add_argument("--projects-dir", default=DEFAULT_PROJECTS_DIR, help="Base directory for project-scoped runs")
    resume_project.add_argument("--rerun-from", choices=PIPELINE_STEP_ORDER, help="Optional rerun start step for the current run")
    add_runtime_arguments(resume_project)

    show_project_status = subparsers.add_parser(
        "show-project-status",
        help="Show the current project manifest summary without rerunning the pipeline",
    )
    show_project_status.add_argument("--project-id", required=True, help="Project/story identifier")
    show_project_status.add_argument("--projects-dir", default=DEFAULT_PROJECTS_DIR, help="Base directory for project-scoped runs")
    show_project_status.add_argument(
        "--reason-detail-mode",
        default="summary",
        choices=["summary", "codes"],
        help="How much structured reason detail to show in status output",
    )

    show_run_comparison = subparsers.add_parser(
        "show-run-comparison",
        help="Show the saved run comparison summary without rerunning the pipeline",
    )
    show_run_comparison.add_argument("--project-id", required=True, help="Project/story identifier")
    show_run_comparison.add_argument("--projects-dir", default=DEFAULT_PROJECTS_DIR, help="Base directory for project-scoped runs")
    show_run_comparison.add_argument(
        "--reason-detail-mode",
        default="summary",
        choices=["summary", "codes"],
        help="How much structured reason detail to show in comparison output",
    )

    select_best_run = subparsers.add_parser(
        "select-best-run",
        help="Manually promote a run candidate to best_run in the project manifest",
    )
    select_best_run.add_argument("--project-id", required=True, help="Project/story identifier")
    select_best_run.add_argument("--projects-dir", default=DEFAULT_PROJECTS_DIR, help="Base directory for project-scoped runs")
    select_best_run.add_argument("--run-name", required=True, help="Run candidate name to promote")

    rerun_chapter = subparsers.add_parser("rerun-chapter", help="Rerun chapter generation for the current project run")
    rerun_chapter.add_argument("--project-id", required=True, help="Project/story identifier")
    rerun_chapter.add_argument("--projects-dir", default=DEFAULT_PROJECTS_DIR, help="Base directory for project-scoped runs")
    rerun_chapter.add_argument("--chapter-number", required=True, type=int, help="Chapter number to rerun")
    add_runtime_arguments(rerun_chapter)
    return parser


def build_story_input_from_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> StoryInput:
    if not all([args.theme, args.genre, args.tone, args.target_length is not None]):
        parser.error("--theme, --genre, --tone, and --target-length are required unless resuming.")
    return StoryInput(
        theme=args.theme,
        genre=args.genre,
        tone=args.tone,
        target_length=args.target_length,
    )


def save_project_state(
    project_layout: dict,
    projects_dir: Path,
    project_id: str,
    output_dir: Path,
    file_format: str,
) -> None:
    run_manifest = load_artifact(output_dir, "manifest")
    existing_project_manifest = _load_existing_project_manifest(project_layout["project_dir"])
    autonomy_level = _resolve_project_autonomy_level(existing_project_manifest)
    run_candidate = _build_run_candidate(run_manifest, output_dir)
    run_candidates = _merge_run_candidates(existing_project_manifest.get("run_candidates", []), run_candidate)
    best_run = _select_best_run(run_candidates)
    chapter_statuses = _build_project_chapter_statuses(run_manifest)
    long_run_status = dict(run_manifest.get("long_run_status", {}))
    policy_snapshot = dict(run_manifest.get("policy_snapshot", {}))
    comparison_summary = _build_run_comparison_summary(
        project_layout=project_layout,
        current_run_name=output_dir.name,
        current_output_dir=output_dir,
        run_candidates=run_candidates,
        best_run=best_run,
    )
    save_project_manifest(
        projects_dir,
        project_id,
        {
            "project_id": project_layout["project_id"],
            "project_slug": project_layout["project_slug"],
            "projects_dir": str(projects_dir),
            "autonomy_level": autonomy_level,
            "current_run": {
                "name": output_dir.name,
                "output_dir": str(output_dir),
                "current_step": run_manifest.get("current_step"),
                "completed_steps": run_manifest.get("completed_steps", []),
                "summary": run_manifest.get("summary", {}),
                "chapter_statuses": chapter_statuses,
                "long_run_status": long_run_status,
                "policy_snapshot": policy_snapshot,
                **_build_candidate_comparison_context(run_candidate),
            },
            "run_candidates": run_candidates,
            "best_run": best_run,
        },
        file_format,
    )
    save_run_comparison_summary(project_layout["project_dir"], comparison_summary, file_format)


def _resolve_project_autonomy_level(existing_project_manifest: dict[str, Any]) -> str:
    contract = project_manifest_contract()["autonomy_level"]
    if "autonomy_level" in existing_project_manifest:
        return existing_project_manifest["autonomy_level"]
    return contract["default"]


def build_run_comparison_lines(project_manifest: dict[str, Any]) -> list[str]:
    current_run = project_manifest.get("current_run", {})
    best_run = project_manifest.get("best_run", {})
    if not current_run or not best_run:
        return []

    current_output_dir = current_run.get("output_dir")
    best_output_dir = best_run.get("output_dir")
    if current_output_dir == best_output_dir:
        return [f"Best run: current run ({current_run.get('name', 'unknown')})"]

    run_candidates = {
        candidate.get("output_dir"): candidate
        for candidate in project_manifest.get("run_candidates", [])
    }
    current_candidate = run_candidates.get(current_output_dir, {})
    best_candidate = run_candidates.get(best_output_dir, {})
    current_metrics = current_candidate.get("comparison_metrics", {})
    best_metrics = best_run.get("comparison_metrics", best_candidate.get("comparison_metrics", {}))

    lines = [
        f"Best run: {best_run.get('run_name', 'unknown')} (current: {current_run.get('name', 'unknown')})",
        (
            "Comparison metrics: "
            f"current total_issue_score={current_metrics.get('total_issue_score', 'n/a')}, "
            f"best total_issue_score={best_metrics.get('total_issue_score', 'n/a')}"
        ),
    ]
    metric_labels = [
        "long_run_should_stop",
        "high_severity_chapter_count",
        "rerun_attempt_total",
        "revision_attempt_total",
        "completed_step_count",
    ]
    for label in metric_labels:
        current_value = current_metrics.get(label, "n/a")
        best_value = best_metrics.get(label, "n/a")
        if current_value != best_value:
            lines.append(f"  {label}: current={current_value}, best={best_value}")

    for reason in current_candidate.get("comparison_reason", _build_candidate_reason_lines(current_metrics)):
        lines.append(f"  current_reason: {reason}")
    for reason in best_run.get("selection_reason", []):
        lines.append(f"  best_reason: {reason}")
    return lines


def load_project_run_context(projects_dir: Path, project_id: str) -> tuple[dict, Path]:
    project_layout = build_project_layout(projects_dir, project_id)
    project_manifest = load_project_manifest(project_layout["project_dir"])
    return project_layout, Path(project_manifest["current_run"]["output_dir"])


def _enforce_resume_project_review_gate(project_manifest: dict[str, Any], output_dir: Path) -> None:
    review_gate = _build_manual_review_gate(project_manifest, output_dir)
    if review_gate is not None:
        reason = review_gate["reason"]
        if reason == "stop_for_review":
            raise ValueError(
                "resume-project is blocked for manual projects when next_action_decision.action is stop_for_review."
            )


def _build_manual_review_gate(project_manifest: dict[str, Any], output_dir: Path) -> dict[str, Any] | None:
    """manual project の review gate を resume/status 共通の source of truth として返す。"""
    if project_manifest.get("autonomy_level") != "manual":
        return None

    next_action_decision = _load_next_action_decision_for_status(output_dir)
    if next_action_decision is None:
        return None

    if next_action_decision.get("action") == "stop_for_review":
        return {"reason": "stop_for_review"}
    return None


def _load_next_action_decision_for_status(output_dir: Path) -> dict[str, Any] | None:
    """read-only の status/manual gate 用に legacy next_action_decision を互換読み込みする。"""
    try:
        return load_next_action_decision(output_dir)
    except FileNotFoundError:
        return None
    except ValueError as strict_error:
        if "missing required fields: story_state_summary" not in str(strict_error):
            raise

        raw_payload = load_artifact(output_dir, "next_action_decision")
        if not isinstance(raw_payload, dict) or "story_state_summary" in raw_payload:
            raise

        return raw_payload


def _build_project_resume_gate_summary(
    project_manifest: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any] | None:
    """互換用の薄い wrapper として manual review gate を返す。"""
    return _build_manual_review_gate(project_manifest, output_dir)


def _load_existing_project_manifest(project_dir: Path) -> dict[str, Any]:
    try:
        return load_project_manifest(project_dir)
    except FileNotFoundError:
        return {}


def _build_run_candidate(run_manifest: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    comparison_metrics = _build_comparison_metrics(run_manifest)
    score = comparison_metrics["total_issue_score"]
    candidate = {
        "run_name": output_dir.name,
        "output_dir": str(output_dir),
        "completed_steps": run_manifest.get("completed_steps", []),
        "summary": run_manifest.get("summary", {}),
        "chapter_statuses": _build_project_chapter_statuses(run_manifest),
        "long_run_status": dict(run_manifest.get("long_run_status", {})),
        "policy_snapshot": dict(run_manifest.get("policy_snapshot", {})),
        "score": score,
        "continuity_issue_total": comparison_metrics["continuity_issue_total"],
        "quality_issue_total": comparison_metrics["quality_issue_total"],
        "project_issue_total": comparison_metrics["project_issue_total"],
        "comparison_metrics": comparison_metrics,
    }
    candidate.update(_build_candidate_comparison_context(candidate))
    return candidate


def _build_comparison_metrics(run_manifest: dict[str, Any]) -> dict[str, Any]:
    continuity_report = run_manifest.get("artifacts", {}).get("continuity_report", {})
    quality_report = run_manifest.get("artifacts", {}).get("quality_report", {})
    project_quality_report = run_manifest.get("artifacts", {}).get("project_quality_report", {})
    continuity_history = run_manifest.get("continuity_history", [])
    rerun_history = run_manifest.get("rerun_history", [])
    revise_history = run_manifest.get("revise_history", [])
    completed_steps = run_manifest.get("completed_steps", [])
    long_run_status = run_manifest.get("long_run_status", {})

    continuity_issue_total = sum(continuity_report.get("issue_counts", {}).values())
    quality_issue_total = int(quality_report.get("total_issue_count", 0) or 0)
    project_issue_total = int(project_quality_report.get("issue_count", 0) or 0)
    high_severity_chapter_count = sum(1 for entry in continuity_history if entry.get("severity") == "high")
    rerun_attempt_total = len(rerun_history)
    revision_attempt_total = len(revise_history)
    completed_step_count = len(completed_steps)
    long_run_should_stop = bool(long_run_status.get("should_stop"))

    return {
        "continuity_issue_total": continuity_issue_total,
        "quality_issue_total": quality_issue_total,
        "project_issue_total": project_issue_total,
        "total_issue_score": continuity_issue_total + quality_issue_total + project_issue_total,
        "high_severity_chapter_count": high_severity_chapter_count,
        "rerun_attempt_total": rerun_attempt_total,
        "revision_attempt_total": revision_attempt_total,
        "completed_step_count": completed_step_count,
        "long_run_should_stop": long_run_should_stop,
    }


def _build_project_chapter_statuses(run_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    chapter_histories = run_manifest.get("chapter_histories", [])
    chapter_statuses: list[dict[str, Any]] = []
    for chapter_history in chapter_histories:
        continuity_entries = chapter_history.get("continuity", [])
        rerun_entries = chapter_history.get("reruns", [])
        revision_entries = chapter_history.get("revisions", [])
        latest_continuity = continuity_entries[-1] if continuity_entries else {}
        latest_rerun = rerun_entries[-1] if rerun_entries else {}
        latest_revision = revision_entries[-1] if revision_entries else {}
        chapter_statuses.append(
            {
                "chapter_index": chapter_history.get("chapter_index"),
                "chapter_number": chapter_history.get("chapter_number"),
                "continuity_issue_total": sum(latest_continuity.get("issue_counts", {}).values()),
                "continuity_severity": latest_continuity.get("severity"),
                "continuity_recommended_action": latest_continuity.get("recommended_action"),
                "latest_rerun_attempt": latest_rerun.get("attempt"),
                "latest_rerun_action": latest_rerun.get("action_taken") or latest_rerun.get("action"),
                "latest_revision_attempt": latest_revision.get("attempt"),
                "latest_revision_stop_reason": latest_revision.get("stop_reason"),
            }
        )
    return chapter_statuses


def _merge_run_candidates(existing_candidates: list[dict[str, Any]], current_candidate: dict[str, Any]) -> list[dict[str, Any]]:
    filtered = [candidate for candidate in existing_candidates if candidate.get("output_dir") != current_candidate["output_dir"]]
    filtered.append(current_candidate)
    return sorted(filtered, key=_candidate_sort_key)


def _candidate_sort_key(candidate: dict[str, Any]) -> tuple[Any, ...]:
    metrics = candidate.get("comparison_metrics", {})
    return (
        int(bool(metrics.get("long_run_should_stop"))),
        int(metrics.get("total_issue_score", candidate.get("score", 0))),
        int(metrics.get("high_severity_chapter_count", 0)),
        int(metrics.get("rerun_attempt_total", 0)),
        int(metrics.get("revision_attempt_total", 0)),
        -int(metrics.get("completed_step_count", len(candidate.get("completed_steps", [])))),
        candidate.get("run_name", ""),
    )


def _select_best_run(run_candidates: list[dict[str, Any]]) -> dict[str, Any]:
    if not run_candidates:
        return {}
    best = min(run_candidates, key=_candidate_sort_key)
    return {
        "run_name": best.get("run_name"),
        "output_dir": best.get("output_dir"),
        "score": best.get("score"),
        "policy_snapshot": dict(best.get("policy_snapshot", {})),
        **_build_candidate_selection_metadata(best),
    }


def _build_run_comparison_summary(
    project_layout: dict[str, Any],
    current_run_name: str,
    current_output_dir: Path,
    run_candidates: list[dict[str, Any]],
    best_run: dict[str, Any],
) -> dict[str, Any]:
    current_candidate = next(
        (candidate for candidate in run_candidates if candidate.get("output_dir") == str(current_output_dir)),
        {},
    )
    return {
        "schema_name": "run_comparison_summary",
        "schema_version": "1.0",
        "project_id": project_layout["project_id"],
        "project_slug": project_layout["project_slug"],
        "current_run": {
            "run_name": current_run_name,
            "output_dir": str(current_output_dir),
            **_build_candidate_comparison_context(current_candidate),
        },
        "best_run": best_run,
        "candidate_count": len(run_candidates),
        "compact_summary": _build_run_comparison_compact_summary(current_candidate, best_run),
        "run_candidates": run_candidates,
    }


def _build_run_comparison_compact_summary(current_candidate: dict[str, Any], best_run: dict[str, Any]) -> dict[str, Any]:
    current_metrics = current_candidate.get("comparison_metrics", {})
    best_metrics = best_run.get("comparison_metrics", {})
    current_policy = current_candidate.get("policy_snapshot", {}).get("long_run", {})
    best_policy = best_run.get("policy_snapshot", {}).get("long_run", {})
    return {
        "selection_source": best_run.get("selection_source", "automatic"),
        "issue_score": {
            "current": current_metrics.get("total_issue_score"),
            "best": best_metrics.get("total_issue_score"),
        },
        "completed_step_count": {
            "current": current_metrics.get("completed_step_count"),
            "best": best_metrics.get("completed_step_count"),
        },
        "long_run_should_stop": {
            "current": current_metrics.get("long_run_should_stop"),
            "best": best_metrics.get("long_run_should_stop"),
        },
        "policy_limits": {
            "max_high_severity_chapters": {
                "current": current_policy.get("max_high_severity_chapters"),
                "best": best_policy.get("max_high_severity_chapters"),
            },
            "max_total_rerun_attempts": {
                "current": current_policy.get("max_total_rerun_attempts"),
                "best": best_policy.get("max_total_rerun_attempts"),
            },
        },
    }


def _comparison_basis_fields() -> list[str]:
    return [
        "long_run_should_stop",
        "continuity_issue_total",
        "quality_issue_total",
        "project_issue_total",
        "high_severity_chapter_count",
        "rerun_attempt_total",
        "revision_attempt_total",
        "completed_step_count",
    ]


def _build_candidate_reason_lines(metrics: dict[str, Any]) -> list[str]:
    return [_reason_detail_to_text(detail) for detail in _build_candidate_reason_details(metrics)]


def _build_candidate_reason_details(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"code": "long_run_should_stop", "value": metrics.get("long_run_should_stop")},
        {"code": "total_issue_score", "value": metrics.get("total_issue_score")},
        {"code": "high_severity_chapter_count", "value": metrics.get("high_severity_chapter_count")},
        {"code": "rerun_attempt_total", "value": metrics.get("rerun_attempt_total")},
        {"code": "revision_attempt_total", "value": metrics.get("revision_attempt_total")},
        {"code": "completed_step_count", "value": metrics.get("completed_step_count")},
    ]


def _build_candidate_comparison_context(candidate: dict[str, Any]) -> dict[str, Any]:
    metrics = dict(candidate.get("comparison_metrics", {}))
    comparison_reason_details = _build_candidate_reason_details(metrics)
    return {
        "comparison_metrics": metrics,
        "comparison_basis": _comparison_basis_fields(),
        "comparison_reason": [_reason_detail_to_text(detail) for detail in comparison_reason_details],
        "comparison_reason_details": comparison_reason_details,
    }


def _build_candidate_selection_metadata(
    candidate: dict[str, Any],
    selection_source: str = "automatic",
    manual_selection_run_name: str | None = None,
) -> dict[str, Any]:
    selection_reason_details = []
    if manual_selection_run_name:
        selection_reason_details.append({"code": "manual_selection", "value": manual_selection_run_name})
    comparison_context = _build_candidate_comparison_context(candidate)
    selection_reason_details.extend(comparison_context["comparison_reason_details"])
    return {
        "policy_snapshot": dict(candidate.get("policy_snapshot", {})),
        "comparison_metrics": comparison_context["comparison_metrics"],
        "comparison_basis": comparison_context["comparison_basis"],
        "selection_reason": [_reason_detail_to_text(detail) for detail in selection_reason_details],
        "selection_reason_details": selection_reason_details,
        "selection_source": selection_source,
    }


def _reason_detail_to_text(detail: dict[str, Any]) -> str:
    return f"{detail.get('code')}={detail.get('value')}"


def _reason_detail_summary(details: list[dict[str, Any]], limit: int = 2) -> str:
    return "; ".join(_reason_detail_to_text(detail) for detail in details[:limit])


def _reason_detail_codes(details: list[dict[str, Any]]) -> list[str]:
    order = {code: index for index, code in enumerate(comparison_reason_detail_codes())}
    codes = [str(detail.get("code")) for detail in details if detail.get("code") is not None]
    return sorted(codes, key=lambda code: order.get(code, len(order)))


def run_pipeline(
    args: argparse.Namespace,
    output_dir: Path,
    story_input: StoryInput | None = None,
    resume_from: Path | None = None,
    rerun_from: str | None = None,
):
    llm_client = build_llm_client(
        provider=args.provider,
        model=args.model,
        base_url=getattr(args, "base_url", None),
        api_key=getattr(args, "api_key", None),
    )
    pipeline = StoryPipeline(
        llm_client=llm_client,
        output_dir=output_dir,
        file_format=args.format,
        rerun_policy=build_rerun_policy_from_args(args),
    )
    return pipeline.run(story_input=story_input, resume_from=resume_from, rerun_from=rerun_from)


def rerun_project_chapter(args: argparse.Namespace, output_dir: Path):
    llm_client = build_llm_client(
        provider=args.provider,
        model=args.model,
        base_url=getattr(args, "base_url", None),
        api_key=getattr(args, "api_key", None),
    )
    pipeline = StoryPipeline(
        llm_client=llm_client,
        output_dir=output_dir,
        file_format=args.format,
        rerun_policy=build_rerun_policy_from_args(args),
    )
    return pipeline.rerun_chapter(resume_from=output_dir, chapter_number=args.chapter_number)


def build_rerun_policy_from_args(args: argparse.Namespace) -> ContinuityRerunPolicy:
    config = deepcopy(ContinuityRerunPolicy().config)
    long_run = dict(config.get("long_run", {}))
    if getattr(args, "max_high_severity_chapters", None) is not None:
        long_run["max_high_severity_chapters"] = args.max_high_severity_chapters
    if getattr(args, "max_total_rerun_attempts", None) is not None:
        long_run["max_total_rerun_attempts"] = args.max_total_rerun_attempts
    config["long_run"] = long_run
    return ContinuityRerunPolicy(config)


def _build_publish_bundle_summary_lines(payload: dict[str, Any]) -> list[str]:
    summary = build_publish_ready_bundle_summary(payload)
    lines = [
        f"publish_bundle.title: {summary['title']}",
        f"publish_bundle.chapter_count: {summary['chapter_count']}",
        f"publish_bundle.section_names: {', '.join(summary['section_names']) or 'none'}",
        f"publish_bundle.source_artifact_names: {', '.join(summary['source_artifact_names']) or 'none'}",
    ]
    story_bible_summary = summary.get("story_bible_summary", {})
    if isinstance(story_bible_summary, dict) and story_bible_summary:
        lines.append(
            "publish_bundle.story_bible_summary: "
            f"core_premise={story_bible_summary.get('core_premise', '')}, "
            f"theme_statement={story_bible_summary.get('theme_statement', '')}, "
            f"ending_reveal={story_bible_summary.get('ending_reveal', '')}"
        )
    thread_summary = summary.get("thread_summary", {})
    if isinstance(thread_summary, dict) and thread_summary:
        lines.append(
            "publish_bundle.thread_summary: "
            f"thread_count={thread_summary.get('thread_count', 0)}, "
            f"unresolved_count={thread_summary.get('unresolved_thread_count', 0)}, "
            f"resolved_count={thread_summary.get('resolved_thread_count', 0)}, "
            f"seeded_count={thread_summary.get('seeded_thread_count', 0)}, "
            f"progressed_count={thread_summary.get('progressed_thread_count', 0)}"
        )
    story_state_summary = summary.get("story_state_summary", {})
    if isinstance(story_state_summary, dict) and story_state_summary:
        lines.append(
            "publish_bundle.story_state_summary: "
            f"evaluated_through_chapter={story_state_summary.get('evaluated_through_chapter', 0)}, "
            f"canon_chapter_count={story_state_summary.get('canon_chapter_count', 0)}, "
            f"thread_count={story_state_summary.get('thread_count', 0)}, "
            f"unresolved_count={story_state_summary.get('unresolved_thread_count', 0)}, "
            f"resolved_count={story_state_summary.get('resolved_thread_count', 0)}, "
            f"open_question_count={story_state_summary.get('open_question_count', 0)}, "
            f"latest_timeline_event_count={story_state_summary.get('latest_timeline_event_count', 0)}"
        )
    handoff_summary = summary.get("handoff_summary", {})
    if isinstance(handoff_summary, dict) and handoff_summary:
        lines.append(
            "publish_bundle.handoff_summary: "
            f"title={handoff_summary.get('title', '')}, "
            f"logline={handoff_summary.get('selected_logline_title', '')}, "
            f"recommendation={handoff_summary.get('quality_recommendation', '')}, "
            f"issue_count={handoff_summary.get('issue_count', 0)}, "
            f"chapter_count={handoff_summary.get('chapter_count', 0)}"
        )
    return lines


def print_run_summary(artifacts, output_dir: Path, project_manifest: dict[str, Any] | None = None) -> None:
    issue_count = sum(artifacts.continuity_report.get("issue_counts", {}).values())
    print(f"Generated short-story artifacts in: {output_dir.resolve()}")
    print(f"Selected logline: {artifacts.loglines[0]['title']}")
    print(f"Chapter count: {len(artifacts.chapter_plan)}")
    print(f"Continuity severity: {artifacts.continuity_report.get('severity', 'unknown')}")
    print(f"Continuity issues flagged: {issue_count}")
    long_run_status = (project_manifest or {}).get("current_run", {}).get("long_run_status", {})
    if long_run_status:
        print(
            "Long-run status: "
            f"should_stop={long_run_status.get('should_stop')}, "
            f"reason={long_run_status.get('reason') or 'none'}, "
            f"remaining_rerun_budget={long_run_status.get('remaining_rerun_attempt_budget', 'n/a')}"
        )
    if getattr(artifacts, "publish_ready_bundle", None):
        for line in _build_publish_bundle_summary_lines(artifacts.publish_ready_bundle):
            print(line)
    for line in build_run_comparison_lines(project_manifest or {}):
        print(line)


def _build_saved_publish_bundle_summary_lines(output_dir: Path) -> list[str]:
    publish_ready_bundle = _load_saved_publish_bundle_for_display(output_dir)
    return _build_publish_bundle_summary_lines(publish_ready_bundle)


def _load_saved_publish_bundle_for_display(output_dir: Path) -> dict[str, Any]:
    """read-only CLI 用に strict load を優先し、summary 欠落だけ互換表示する。"""
    try:
        return load_publish_ready_bundle(output_dir)
    except ValueError as strict_error:
        if "summary must be an object" not in str(strict_error):
            raise

        raw_payload = load_artifact(output_dir, "publish_ready_bundle")
        if not isinstance(raw_payload, dict) or "summary" in raw_payload:
            raise

        patched_payload = dict(raw_payload)
        patched_payload["summary"] = build_publish_ready_bundle_summary(raw_payload)
        validate_publish_ready_bundle(patched_payload)
        return patched_payload


def build_project_status_summary(
    project_manifest: dict[str, Any],
    reason_detail_mode: str = "summary",
) -> dict[str, Any]:
    if not project_manifest:
        return {}

    current_run = project_manifest.get("current_run", {})
    best_run = project_manifest.get("best_run", {})
    summary: dict[str, Any] = {
        "project_label": project_manifest.get("project_slug") or project_manifest.get("project_id", "unknown"),
        "run_candidate_count": len(project_manifest.get("run_candidates", [])),
        "autonomy_level": project_manifest.get("autonomy_level", project_manifest_contract()["autonomy_level"]["default"]),
    }

    if current_run:
        chapter_statuses = current_run.get("chapter_statuses", [])
        long_run_status = current_run.get("long_run_status", {})
        comparison_metrics = current_run.get("comparison_metrics", {})
        current_output_dir = current_run.get("output_dir")
        resume_gate = (
            _build_manual_review_gate(project_manifest, Path(current_output_dir))
            if current_output_dir
            else None
        )
        resume_gate_line = _build_resume_gate_status_line(summary["autonomy_level"], current_output_dir)
        saved_story_state_summary_line = _build_saved_story_state_summary_line(current_output_dir)
        summary["current_run"] = {
            "name": current_run.get("name", "unknown"),
            "output_dir": current_run.get("output_dir", "unknown"),
            "current_step": current_run.get("current_step", "unknown"),
            "completed_steps": comparison_metrics.get("completed_step_count", "n/a"),
            "resume_gate_line": resume_gate_line,
            "saved_story_state_summary_line": saved_story_state_summary_line,
            "comparison_lines": _build_current_comparison_summary_lines(current_run, reason_detail_mode),
            "chapter_status_lines": _build_chapter_status_summary_lines(chapter_statuses),
            "long_run_status_lines": _build_long_run_status_lines(long_run_status),
            "resume_gate": resume_gate,
        }

    if best_run:
        comparison_metrics = best_run.get("comparison_metrics", {})
        summary["best_run"] = {
            "name": best_run.get("run_name", "unknown"),
            "output_dir": best_run.get("output_dir", "unknown"),
            "score": best_run.get("score", "unknown"),
            "selection_lines": _build_selection_summary_lines(best_run, reason_detail_mode),
            "diff_lines": _build_status_diff_summary_lines(current_run, best_run),
            "policy_diff_lines": _build_policy_diff_lines(
                current_run.get("policy_snapshot", {}),
                best_run.get("policy_snapshot", {}),
            ),
            "comparison_metrics_line": (
                "  best_comparison_metrics: "
                f"total_issue_score={comparison_metrics.get('total_issue_score', 'n/a')}, "
                f"completed_step_count={comparison_metrics.get('completed_step_count', 'n/a')}"
                if comparison_metrics
                else None
            ),
        }

    return summary


def build_project_status_lines(project_manifest: dict[str, Any], reason_detail_mode: str = "summary") -> list[str]:
    summary = build_project_status_summary(project_manifest, reason_detail_mode=reason_detail_mode)
    lines: list[str] = []
    if not summary:
        return lines

    lines.append(f"Project: {summary['project_label']}")
    lines.append(f"Autonomy level: {summary['autonomy_level']}")

    current_run = summary.get("current_run")
    if current_run:
        resume_gate = current_run.get("resume_gate")
        if resume_gate:
            lines.append(f"Resume gate: {resume_gate['reason']}")
        lines.append(f"Current run: {current_run['name']}")
        lines.append(f"  output_dir: {current_run['output_dir']}")
        if current_run["resume_gate_line"]:
            lines.append(current_run["resume_gate_line"])
        if current_run["saved_story_state_summary_line"]:
            lines.append(current_run["saved_story_state_summary_line"])
        lines.append(f"  current_step: {current_run['current_step']}")
        lines.append(f"  completed_steps: {current_run['completed_steps']}")
        lines.extend(current_run["comparison_lines"])
        lines.extend(current_run["chapter_status_lines"])
        lines.extend(current_run["long_run_status_lines"])

    best_run = summary.get("best_run")
    if best_run:
        lines.append(f"Best run: {best_run['name']}")
        lines.append(f"  output_dir: {best_run['output_dir']}")
        lines.append(f"  score: {best_run['score']}")
        lines.extend(best_run["selection_lines"])
        lines.extend(best_run["diff_lines"])
        if best_run["comparison_metrics_line"]:
            lines.append(best_run["comparison_metrics_line"])
        lines.extend(best_run["policy_diff_lines"])

    lines.append(f"Run candidates: {summary['run_candidate_count']}")
    return lines


def _build_resume_gate_status_line(autonomy_level: str, output_dir: Any) -> str | None:
    if autonomy_level != "manual" or not output_dir:
        return None

    next_action_decision = _load_next_action_decision_for_status(Path(output_dir))
    if next_action_decision is None:
        return None

    if next_action_decision.get("action") == "stop_for_review":
        return "  Resume gate: blocked_by_review (saved next_action_decision.action=stop_for_review)"

    return None


def _build_saved_story_state_summary_line(output_dir: Any) -> str | None:
    if not output_dir:
        return None

    next_action_decision = _load_next_action_decision_for_status(Path(output_dir))
    if not next_action_decision:
        return None

    story_state_summary = next_action_decision.get("story_state_summary")
    if not isinstance(story_state_summary, dict):
        return None

    return (
        "  saved_story_state_summary: "
        f"evaluated_through_chapter={story_state_summary.get('evaluated_through_chapter', 'n/a')}, "
        f"canon_chapter_count={story_state_summary.get('canon_chapter_count', 'n/a')}, "
        f"thread_count={story_state_summary.get('thread_count', 'n/a')}, "
        f"unresolved_count={story_state_summary.get('unresolved_thread_count', 'n/a')}, "
        f"resolved_count={story_state_summary.get('resolved_thread_count', 'n/a')}, "
        f"open_question_count={story_state_summary.get('open_question_count', 'n/a')}, "
        f"latest_timeline_event_count={story_state_summary.get('latest_timeline_event_count', 'n/a')}"
    )


def build_saved_run_comparison_summary(
    summary_artifact: dict[str, Any],
    reason_detail_mode: str = "summary",
) -> dict[str, Any]:
    if not summary_artifact:
        return {}

    current_run = summary_artifact.get("current_run", {})
    best_run = summary_artifact.get("best_run", {})
    compact_summary = summary_artifact.get("compact_summary", {})
    return {
        "project_label": summary_artifact.get("project_slug") or summary_artifact.get("project_id", "unknown"),
        "candidate_count": summary_artifact.get("candidate_count", 0),
        "run_candidates": _build_saved_run_candidate_section(summary_artifact.get("run_candidates", [])),
        "current_run": _build_saved_run_current_section(current_run, reason_detail_mode) if current_run else None,
        "best_run": _build_saved_run_best_section(best_run, reason_detail_mode) if best_run else None,
        "compact_summary": _build_saved_run_compact_summary_section(compact_summary),
    }


def build_saved_run_comparison_lines(summary_artifact: dict[str, Any], reason_detail_mode: str = "summary") -> list[str]:
    summary = build_saved_run_comparison_summary(summary_artifact, reason_detail_mode=reason_detail_mode)
    if not summary:
        return []

    lines = _build_saved_run_header_lines(summary["project_label"])
    section_renderers = _build_saved_run_section_renderers(summary["candidate_count"])
    for section_name, renderer in section_renderers:
        section = summary.get(section_name)
        if section:
            lines.extend(renderer(section))
    return lines


def _build_saved_run_header_lines(project_label: str) -> list[str]:
    return [f"Project: {project_label}"]


def _build_saved_run_section_renderers(
    candidate_count: int,
) -> tuple[tuple[str, Callable[[dict[str, Any]], list[str]]], ...]:
    return (
        ("current_run", _build_saved_run_current_section_lines),
        ("best_run", _build_saved_run_best_section_lines),
        ("compact_summary", _build_saved_run_compact_section_lines),
        ("run_candidates", lambda section: _build_saved_run_candidate_section_lines(candidate_count, section)),
    )


def _build_saved_run_current_section_lines(current_run: dict[str, Any]) -> list[str]:
    lines = [
        f"Current run: {current_run['name']}",
        f"  output_dir: {current_run['output_dir']}",
    ]
    lines.extend(current_run["comparison_summary"]["lines"])
    if current_run["comparison_metrics_line"]:
        lines.append(current_run["comparison_metrics_line"])
    return lines


def _build_saved_run_best_section_lines(best_run: dict[str, Any]) -> list[str]:
    lines = [
        f"Best run: {best_run['name']}",
        f"  output_dir: {best_run['output_dir']}",
    ]
    lines.extend(best_run["selection_summary"]["lines"])
    if best_run["comparison_metrics_line"]:
        lines.append(best_run["comparison_metrics_line"])
    return lines


def _build_saved_run_compact_section_lines(compact_summary: dict[str, Any]) -> list[str]:
    return list(compact_summary["lines"])


def _build_saved_run_candidate_section_lines(candidate_count: int, run_candidates: dict[str, Any]) -> list[str]:
    lines = [f"Run candidates: {candidate_count}"]
    lines.extend(run_candidates["lines"])
    return lines


def _build_saved_run_compact_summary_section(compact_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "selection_source": compact_summary.get("selection_source", "unknown"),
        "issue_score": dict(compact_summary.get("issue_score", {})),
        "completed_step_count": dict(compact_summary.get("completed_step_count", {})),
        "long_run_should_stop": dict(compact_summary.get("long_run_should_stop", {})),
        "policy_limits": deepcopy(compact_summary.get("policy_limits", {})),
        "lines": _build_compact_summary_lines(compact_summary),
    }


def _build_saved_run_candidate_section(run_candidates: list[dict[str, Any]]) -> dict[str, Any]:
    names = [candidate.get("run_name", "unknown") for candidate in run_candidates]
    scores = [
        f"{candidate.get('run_name', 'unknown')}={candidate.get('score', 'n/a')}"
        for candidate in run_candidates
    ]
    output_dirs = [
        f"{candidate.get('run_name', 'unknown')}={candidate.get('output_dir', 'unknown')}"
        for candidate in run_candidates
    ]
    lines: list[str] = []
    if names:
        lines.append(f"  run_candidate_names: {', '.join(names)}")
    if scores:
        lines.append(f"  run_candidate_scores: {', '.join(scores)}")
    if output_dirs:
        lines.append(f"  run_candidate_output_dirs: {', '.join(output_dirs)}")
    return {
        "names": names,
        "scores": scores,
        "output_dirs": output_dirs,
        "lines": lines,
    }


def _build_saved_run_current_section(current_run: dict[str, Any], reason_detail_mode: str) -> dict[str, Any]:
    comparison_metrics = dict(current_run.get("comparison_metrics", {}))
    return {
        "name": current_run.get("run_name", "unknown"),
        "output_dir": current_run.get("output_dir", "unknown"),
        "comparison_metrics": comparison_metrics,
        "comparison_summary": _build_saved_run_current_comparison_section(current_run, reason_detail_mode),
        "comparison_metrics_line": _build_comparison_metrics_line("current_comparison_metrics", comparison_metrics),
    }


def _build_saved_run_best_section(best_run: dict[str, Any], reason_detail_mode: str) -> dict[str, Any]:
    comparison_metrics = dict(best_run.get("comparison_metrics", {}))
    return {
        "name": best_run.get("run_name", "unknown"),
        "output_dir": best_run.get("output_dir", "unknown"),
        "comparison_metrics": comparison_metrics,
        "selection_summary": _build_saved_run_best_selection_section(best_run, reason_detail_mode),
        "comparison_metrics_line": _build_comparison_metrics_line("best_comparison_metrics", comparison_metrics),
    }


def _build_comparison_metrics_line(label: str, comparison_metrics: dict[str, Any]) -> str | None:
    if not comparison_metrics:
        return None
    return (
        f"  {label}: "
        f"total_issue_score={comparison_metrics.get('total_issue_score', 'n/a')}, "
        f"completed_step_count={comparison_metrics.get('completed_step_count', 'n/a')}"
    )


def _build_saved_run_current_comparison_section(current_run: dict[str, Any], reason_detail_mode: str) -> dict[str, Any]:
    comparison_basis = current_run.get("comparison_basis", [])
    comparison_reason_details = current_run.get("comparison_reason_details", [])
    basis_summary = ", ".join(comparison_basis[:3]) if comparison_basis else None
    reason_summary = _reason_detail_summary(comparison_reason_details) if comparison_reason_details else None
    reason_codes = (
        _reason_detail_codes(comparison_reason_details[:3])
        if reason_detail_mode == "codes" and comparison_reason_details
        else []
    )
    lines: list[str] = []
    if basis_summary:
        lines.append(f"  current_comparison_basis_summary: {basis_summary}")
    if reason_summary:
        lines.append(f"  current_comparison_reason_summary: {reason_summary}")
    if reason_codes:
        lines.append(f"  current_comparison_reason_codes: {', '.join(reason_codes)}")
    return {
        "basis_summary": basis_summary,
        "reason_summary": reason_summary,
        "reason_codes": reason_codes,
        "lines": lines,
    }


def _build_saved_run_best_selection_section(best_run: dict[str, Any], reason_detail_mode: str) -> dict[str, Any]:
    selection_source = best_run.get("selection_source", "automatic")
    comparison_basis = best_run.get("comparison_basis", [])
    selection_reason_details = best_run.get("selection_reason_details", [])
    basis_summary = ", ".join(comparison_basis[:3]) if comparison_basis else None
    reason_summary = _reason_detail_summary(selection_reason_details) if selection_reason_details else None
    reason_codes = (
        _reason_detail_codes(selection_reason_details[:3])
        if reason_detail_mode == "codes" and selection_reason_details
        else []
    )
    lines = [f"  best_selection_source: {selection_source}"]
    if basis_summary:
        lines.append(f"  best_comparison_basis_summary: {basis_summary}")
    if reason_summary:
        lines.append(f"  best_selection_reason_summary: {reason_summary}")
    if reason_codes:
        lines.append(f"  best_selection_reason_codes: {', '.join(reason_codes)}")
    return {
        "selection_source": selection_source,
        "basis_summary": basis_summary,
        "reason_summary": reason_summary,
        "reason_codes": reason_codes,
        "lines": lines,
    }


def _build_compact_summary_lines(compact_summary: dict[str, Any]) -> list[str]:
    if not compact_summary:
        return ["Compact summary: none"]

    issue_score = compact_summary.get("issue_score", {})
    completed_step_count = compact_summary.get("completed_step_count", {})
    long_run_should_stop = compact_summary.get("long_run_should_stop", {})
    policy_limits = compact_summary.get("policy_limits", {})
    high_severity_limit = policy_limits.get("max_high_severity_chapters", {})
    rerun_limit = policy_limits.get("max_total_rerun_attempts", {})
    return [
        f"Compact summary: selection_source={compact_summary.get('selection_source', 'unknown')}",
        "  compact.issue_score: "
        f"current={issue_score.get('current', 'n/a')}, best={issue_score.get('best', 'n/a')}",
        "  compact.completed_step_count: "
        f"current={completed_step_count.get('current', 'n/a')}, best={completed_step_count.get('best', 'n/a')}",
        "  compact.long_run_should_stop: "
        f"current={long_run_should_stop.get('current', 'n/a')}, best={long_run_should_stop.get('best', 'n/a')}",
        "  compact.policy_limits.max_high_severity_chapters: "
        f"current={high_severity_limit.get('current', 'n/a')}, best={high_severity_limit.get('best', 'n/a')}",
        "  compact.policy_limits.max_total_rerun_attempts: "
        f"current={rerun_limit.get('current', 'n/a')}, best={rerun_limit.get('best', 'n/a')}",
    ]


def _build_chapter_status_summary_lines(chapter_statuses: list[dict[str, Any]]) -> list[str]:
    if not chapter_statuses:
        return ["  chapter_statuses: none"]

    issue_chapter_count = sum(1 for status in chapter_statuses if int(status.get("continuity_issue_total", 0) or 0) > 0)
    high_severity_count = sum(1 for status in chapter_statuses if status.get("continuity_severity") == "high")
    lines = [
        f"  chapter_statuses: {len(chapter_statuses)} tracked",
        f"  chapters_with_issues: {issue_chapter_count}",
        f"  chapters_high_severity: {high_severity_count}",
    ]
    lines.extend(_build_chapter_status_detail_lines(chapter_statuses))
    return lines


def _build_chapter_status_detail_lines(chapter_statuses: list[dict[str, Any]]) -> list[str]:
    lines = ["  chapter_details:"]
    for status in chapter_statuses:
        lines.append(
            "    "
            f"chapter_{status.get('chapter_number', 'unknown')}: "
            f"continuity_issues={status.get('continuity_issue_total', 0)}, "
            f"rerun_attempt={status.get('latest_rerun_attempt', 'n/a')}, "
            f"revision_attempt={status.get('latest_revision_attempt', 'n/a')}"
        )
    return lines


def _build_long_run_status_lines(long_run_status: dict[str, Any]) -> list[str]:
    if not long_run_status:
        return ["  long_run_status: none"]

    return [
        "  long_run_status: "
        f"should_stop={long_run_status.get('should_stop')}, "
        f"reason={long_run_status.get('reason') or 'none'}",
        "  long_run_budget: "
        f"remaining_rerun_attempt_budget={long_run_status.get('remaining_rerun_attempt_budget', 'n/a')}, "
        f"remaining_high_severity_chapter_budget={long_run_status.get('remaining_high_severity_chapter_budget', 'n/a')}",
    ]


def _build_policy_diff_lines(current_policy: dict[str, Any], best_policy: dict[str, Any]) -> list[str]:
    current_long_run = current_policy.get("long_run", {})
    best_long_run = best_policy.get("long_run", {})
    if not current_long_run and not best_long_run:
        return []

    diff_lines: list[str] = []
    compared_keys = [
        "max_high_severity_chapters",
        "max_total_rerun_attempts",
    ]
    for key in compared_keys:
        current_value = current_long_run.get(key, "n/a")
        best_value = best_long_run.get(key, "n/a")
        if current_value != best_value:
            diff_lines.append(f"  policy_diff.{key}: current={current_value}, best={best_value}")
    return diff_lines


def _build_selection_summary_lines(best_run: dict[str, Any], reason_detail_mode: str) -> list[str]:
    selection_source = best_run.get("selection_source", "automatic")
    comparison_basis = best_run.get("comparison_basis", [])
    selection_reason_details = best_run.get("selection_reason_details", [])
    lines = [f"  best_selection_source: {selection_source}"]
    if comparison_basis:
        lines.append(f"  best_comparison_basis_summary: {', '.join(comparison_basis[:3])}")
    if selection_reason_details:
        lines.append(f"  best_selection_reason_summary: {_reason_detail_summary(selection_reason_details)}")
    if reason_detail_mode == "codes" and selection_reason_details:
        lines.append(f"  best_selection_reason_codes: {', '.join(_reason_detail_codes(selection_reason_details[:3]))}")
    return lines


def _build_current_comparison_summary_lines(current_run: dict[str, Any], reason_detail_mode: str) -> list[str]:
    comparison_basis = current_run.get("comparison_basis", [])
    comparison_metrics = current_run.get("comparison_metrics", {})
    comparison_reason_details = current_run.get("comparison_reason_details", [])
    lines: list[str] = []
    if comparison_basis:
        lines.append(f"  current_comparison_basis_summary: {', '.join(comparison_basis[:3])}")
    if comparison_reason_details:
        lines.append(f"  current_comparison_reason_summary: {_reason_detail_summary(comparison_reason_details)}")
    if reason_detail_mode == "codes" and comparison_reason_details:
        lines.append(
            f"  current_comparison_reason_codes: {', '.join(_reason_detail_codes(comparison_reason_details[:3]))}"
        )
    if comparison_metrics:
        lines.append(
            "  current_comparison_metrics: "
            f"total_issue_score={comparison_metrics.get('total_issue_score', 'n/a')}, "
            f"completed_step_count={comparison_metrics.get('completed_step_count', 'n/a')}"
        )
    return lines


def _build_status_diff_summary_lines(current_run: dict[str, Any], best_run: dict[str, Any]) -> list[str]:
    current_metrics = current_run.get("comparison_metrics", {})
    best_metrics = best_run.get("comparison_metrics", {})
    current_policy = current_run.get("policy_snapshot", {}).get("long_run", {})
    best_policy = best_run.get("policy_snapshot", {}).get("long_run", {})

    return [
        "  diff_summary: "
        f"issue_score current={current_metrics.get('total_issue_score', 'n/a')} best={best_metrics.get('total_issue_score', 'n/a')}; "
        f"completed_steps current={current_metrics.get('completed_step_count', 'n/a')} best={best_metrics.get('completed_step_count', 'n/a')}; "
        f"stop current={current_metrics.get('long_run_should_stop', 'n/a')} best={best_metrics.get('long_run_should_stop', 'n/a')}",
        "  diff_policy: "
        f"max_high_severity_chapters current={current_policy.get('max_high_severity_chapters', 'n/a')} "
        f"best={best_policy.get('max_high_severity_chapters', 'n/a')}; "
        f"max_total_rerun_attempts current={current_policy.get('max_total_rerun_attempts', 'n/a')} "
        f"best={best_policy.get('max_total_rerun_attempts', 'n/a')}",
    ]


def print_project_status(project_manifest: dict[str, Any], reason_detail_mode: str = "summary") -> None:
    for line in build_project_status_lines(project_manifest, reason_detail_mode=reason_detail_mode):
        print(line)


def print_run_comparison(
    summary_artifact: dict[str, Any],
    reason_detail_mode: str = "summary",
) -> None:
    lines = build_saved_run_comparison_lines(summary_artifact, reason_detail_mode=reason_detail_mode)
    current_run = summary_artifact.get("current_run", {})
    current_output_dir = current_run.get("output_dir")
    if current_output_dir:
        lines.extend(_build_saved_publish_bundle_summary_lines(Path(current_output_dir)))

    for line in lines:
        print(line)


def promote_best_run(project_dir: Path, run_name: str, projects_dir: Path, file_format: str = "json") -> dict[str, Any]:
    project_manifest = load_project_manifest(project_dir)
    candidate = next(
        (item for item in project_manifest.get("run_candidates", []) if item.get("run_name") == run_name),
        None,
    )
    if candidate is None:
        raise ValueError(f"Unknown run candidate: {run_name}")

    best_run = {
        "run_name": candidate.get("run_name"),
        "output_dir": candidate.get("output_dir"),
        "score": candidate.get("score"),
        **_build_candidate_selection_metadata(
            candidate,
            selection_source="manual",
            manual_selection_run_name=run_name,
        ),
    }
    project_manifest["best_run"] = best_run
    save_project_manifest(projects_dir, project_manifest["project_id"], project_manifest, file_format)
    comparison_summary = _build_run_comparison_summary(
        project_layout={
            "project_id": project_manifest["project_id"],
            "project_slug": project_manifest["project_slug"],
        },
        current_run_name=project_manifest.get("current_run", {}).get("name", ""),
        current_output_dir=Path(project_manifest.get("current_run", {}).get("output_dir", "")),
        run_candidates=project_manifest.get("run_candidates", []),
        best_run=best_run,
    )
    save_run_comparison_summary(project_dir, comparison_summary, file_format)
    return project_manifest


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "create-project":
        project_layout = build_project_layout(Path(args.projects_dir), args.project_id)
        output_dir = Path(args.output_dir)
        if args.output_dir == DEFAULT_OUTPUT_DIR:
            output_dir = project_layout["run_dir"]
        story_input = build_story_input_from_args(parser, args)
        artifacts = run_pipeline(args, output_dir, story_input=story_input)
        save_project_state(project_layout, Path(args.projects_dir), args.project_id, output_dir, args.format)
        project_manifest = load_project_manifest(project_layout["project_dir"])
        print_run_summary(artifacts, output_dir, project_manifest)
        return 0

    if args.command == "resume-project":
        project_layout, output_dir = load_project_run_context(Path(args.projects_dir), args.project_id)
        project_manifest = load_project_manifest(project_layout["project_dir"])
        _enforce_resume_project_review_gate(project_manifest, output_dir)
        artifacts = run_pipeline(args, output_dir, resume_from=output_dir, rerun_from=args.rerun_from)
        save_project_state(project_layout, Path(args.projects_dir), args.project_id, output_dir, args.format)
        project_manifest = load_project_manifest(project_layout["project_dir"])
        print_run_summary(artifacts, output_dir, project_manifest)
        return 0

    if args.command == "show-project-status":
        project_layout = build_project_layout(Path(args.projects_dir), args.project_id)
        project_manifest = load_project_manifest(project_layout["project_dir"])
        print_project_status(project_manifest, reason_detail_mode=args.reason_detail_mode)
        return 0

    if args.command == "show-run-comparison":
        project_layout = build_project_layout(Path(args.projects_dir), args.project_id)
        summary_artifact = load_run_comparison_summary(project_layout["project_dir"])
        print_run_comparison(summary_artifact, reason_detail_mode=args.reason_detail_mode)
        return 0

    if args.command == "select-best-run":
        project_layout = build_project_layout(Path(args.projects_dir), args.project_id)
        project_manifest = promote_best_run(
            project_layout["project_dir"],
            args.run_name,
            Path(args.projects_dir),
        )
        print_project_status(project_manifest)
        return 0

    if args.command == "rerun-chapter":
        project_layout, output_dir = load_project_run_context(Path(args.projects_dir), args.project_id)
        artifacts = rerun_project_chapter(args, output_dir)
        save_project_state(project_layout, Path(args.projects_dir), args.project_id, output_dir, args.format)
        project_manifest = load_project_manifest(project_layout["project_dir"])
        print_run_summary(artifacts, output_dir, project_manifest)
        return 0

    resume_from = Path(args.resume_from_output_dir) if args.resume_from_output_dir else None
    if args.rerun_from and resume_from is None:
        parser.error("--rerun-from requires --resume-from-output-dir.")

    story_input = None
    if resume_from is None:
        story_input = build_story_input_from_args(parser, args)

    project_layout = None
    if args.project_id:
        project_layout = build_project_layout(Path(args.projects_dir), args.project_id)
        if resume_from is not None:
            try:
                project_manifest = load_project_manifest(project_layout["project_dir"])
            except FileNotFoundError:
                project_manifest = None
            else:
                _enforce_resume_project_review_gate(project_manifest, Path(resume_from))

    output_dir = Path(args.output_dir)
    if resume_from is not None and args.output_dir == DEFAULT_OUTPUT_DIR:
        output_dir = resume_from
    elif project_layout is not None and args.output_dir == DEFAULT_OUTPUT_DIR:
        output_dir = project_layout["run_dir"]

    artifacts = run_pipeline(args, output_dir, story_input=story_input, resume_from=resume_from, rerun_from=args.rerun_from)
    if project_layout is not None:
        save_project_state(project_layout, Path(args.projects_dir), args.project_id, output_dir, args.format)
    project_manifest = load_project_manifest(project_layout["project_dir"]) if project_layout is not None else None
    print_run_summary(artifacts, output_dir, project_manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
