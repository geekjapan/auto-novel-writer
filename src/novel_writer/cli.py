from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
from typing import Any

from novel_writer.llm_client import build_llm_client
from novel_writer.pipeline import PIPELINE_STEP_ORDER, StoryPipeline
from novel_writer.rerun_policy import ContinuityRerunPolicy
from novel_writer.schema import StoryInput
from novel_writer.storage import build_project_layout, load_artifact, load_project_manifest, save_project_manifest


DEFAULT_OUTPUT_DIR = "data/latest_run"
DEFAULT_PROJECTS_DIR = "data/projects"


def add_generation_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--theme", help="Story theme")
    parser.add_argument("--genre", help="Story genre")
    parser.add_argument("--tone", help="Story tone")
    parser.add_argument("--target-length", type=int, help="Target length in words or characters")


def add_runtime_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--provider", default="mock", choices=["mock", "openai"], help="LLM provider")
    parser.add_argument("--model", default="gpt-4.1-mini", help="Model name for provider=openai")
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
    run_candidate = _build_run_candidate(run_manifest, output_dir)
    run_candidates = _merge_run_candidates(existing_project_manifest.get("run_candidates", []), run_candidate)
    best_run = _select_best_run(run_candidates)
    chapter_statuses = _build_project_chapter_statuses(run_manifest)
    long_run_status = dict(run_manifest.get("long_run_status", {}))
    policy_snapshot = dict(run_manifest.get("policy_snapshot", {}))
    save_project_manifest(
        projects_dir,
        project_id,
        {
            "project_id": project_layout["project_id"],
            "project_slug": project_layout["project_slug"],
            "projects_dir": str(projects_dir),
            "current_run": {
                "name": output_dir.name,
                "output_dir": str(output_dir),
                "current_step": run_manifest.get("current_step"),
                "completed_steps": run_manifest.get("completed_steps", []),
                "summary": run_manifest.get("summary", {}),
                "chapter_statuses": chapter_statuses,
                "long_run_status": long_run_status,
                "policy_snapshot": policy_snapshot,
            },
            "run_candidates": run_candidates,
            "best_run": best_run,
        },
        file_format,
    )


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

    for reason in best_run.get("selection_reason", []):
        lines.append(f"  best_reason: {reason}")
    return lines


def load_project_run_context(projects_dir: Path, project_id: str) -> tuple[dict, Path]:
    project_layout = build_project_layout(projects_dir, project_id)
    project_manifest = load_project_manifest(project_layout["project_dir"])
    return project_layout, Path(project_manifest["current_run"]["output_dir"])


def _load_existing_project_manifest(project_dir: Path) -> dict[str, Any]:
    try:
        return load_project_manifest(project_dir)
    except FileNotFoundError:
        return {}


def _build_run_candidate(run_manifest: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    comparison_metrics = _build_comparison_metrics(run_manifest)
    score = comparison_metrics["total_issue_score"]
    return {
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
    metrics = best.get("comparison_metrics", {})
    return {
        "run_name": best.get("run_name"),
        "output_dir": best.get("output_dir"),
        "score": best.get("score"),
        "policy_snapshot": dict(best.get("policy_snapshot", {})),
        "comparison_metrics": metrics,
        "comparison_basis": [
            "long_run_should_stop",
            "continuity_issue_total",
            "quality_issue_total",
            "project_issue_total",
            "high_severity_chapter_count",
            "rerun_attempt_total",
            "revision_attempt_total",
            "completed_step_count",
        ],
        "selection_reason": [
            f"long_run_should_stop={metrics.get('long_run_should_stop')}",
            f"total_issue_score={metrics.get('total_issue_score')}",
            f"high_severity_chapter_count={metrics.get('high_severity_chapter_count')}",
            f"rerun_attempt_total={metrics.get('rerun_attempt_total')}",
            f"revision_attempt_total={metrics.get('revision_attempt_total')}",
            f"completed_step_count={metrics.get('completed_step_count')}",
        ],
    }


def run_pipeline(
    args: argparse.Namespace,
    output_dir: Path,
    story_input: StoryInput | None = None,
    resume_from: Path | None = None,
    rerun_from: str | None = None,
):
    llm_client = build_llm_client(provider=args.provider, model=args.model)
    pipeline = StoryPipeline(
        llm_client=llm_client,
        output_dir=output_dir,
        file_format=args.format,
        rerun_policy=build_rerun_policy_from_args(args),
    )
    return pipeline.run(story_input=story_input, resume_from=resume_from, rerun_from=rerun_from)


def rerun_project_chapter(args: argparse.Namespace, output_dir: Path):
    llm_client = build_llm_client(provider=args.provider, model=args.model)
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
    for line in build_run_comparison_lines(project_manifest or {}):
        print(line)


def build_project_status_lines(project_manifest: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    if not project_manifest:
        return lines

    current_run = project_manifest.get("current_run", {})
    best_run = project_manifest.get("best_run", {})
    lines.append(f"Project: {project_manifest.get('project_slug') or project_manifest.get('project_id', 'unknown')}")

    if current_run:
        completed_steps = current_run.get("completed_steps", [])
        chapter_statuses = current_run.get("chapter_statuses", [])
        long_run_status = current_run.get("long_run_status", {})
        lines.append(f"Current run: {current_run.get('name', 'unknown')}")
        lines.append(f"  output_dir: {current_run.get('output_dir', 'unknown')}")
        lines.append(f"  current_step: {current_run.get('current_step', 'unknown')}")
        lines.append(f"  completed_steps: {len(completed_steps)}")
        lines.extend(_build_chapter_status_summary_lines(chapter_statuses))
        lines.extend(_build_long_run_status_lines(long_run_status))

    if best_run:
        lines.append(f"Best run: {best_run.get('run_name', 'unknown')}")
        lines.append(f"  output_dir: {best_run.get('output_dir', 'unknown')}")
        lines.append(f"  score: {best_run.get('score', 'unknown')}")
        comparison_metrics = best_run.get("comparison_metrics", {})
        if comparison_metrics:
            lines.append(
                "  comparison_metrics: "
                f"total_issue_score={comparison_metrics.get('total_issue_score', 'n/a')}, "
                f"completed_step_count={comparison_metrics.get('completed_step_count', 'n/a')}"
            )

    run_candidates = project_manifest.get("run_candidates", [])
    lines.append(f"Run candidates: {len(run_candidates)}")
    return lines


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


def print_project_status(project_manifest: dict[str, Any]) -> None:
    for line in build_project_status_lines(project_manifest):
        print(line)


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
        artifacts = run_pipeline(args, output_dir, resume_from=output_dir, rerun_from=args.rerun_from)
        save_project_state(project_layout, Path(args.projects_dir), args.project_id, output_dir, args.format)
        project_manifest = load_project_manifest(project_layout["project_dir"])
        print_run_summary(artifacts, output_dir, project_manifest)
        return 0

    if args.command == "show-project-status":
        project_layout = build_project_layout(Path(args.projects_dir), args.project_id)
        project_manifest = load_project_manifest(project_layout["project_dir"])
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
