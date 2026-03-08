from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from novel_writer.llm_client import build_llm_client
from novel_writer.pipeline import PIPELINE_STEP_ORDER, StoryPipeline
from novel_writer.schema import StoryInput
from novel_writer.storage import build_project_layout, load_artifact, save_project_manifest


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
            },
            "run_candidates": run_candidates,
            "best_run": best_run,
        },
        file_format,
    )


def load_project_run_context(projects_dir: Path, project_id: str) -> tuple[dict, Path]:
    project_layout = build_project_layout(projects_dir, project_id)
    project_manifest = load_artifact(project_layout["project_dir"], "project_manifest")
    return project_layout, Path(project_manifest["current_run"]["output_dir"])


def _load_existing_project_manifest(project_dir: Path) -> dict[str, Any]:
    try:
        return load_artifact(project_dir, "project_manifest")
    except FileNotFoundError:
        return {}


def _build_run_candidate(run_manifest: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    continuity_report = run_manifest.get("artifacts", {}).get("continuity_report", {})
    quality_report = run_manifest.get("artifacts", {}).get("quality_report", {})
    project_quality_report = run_manifest.get("artifacts", {}).get("project_quality_report", {})
    continuity_issue_total = sum(continuity_report.get("issue_counts", {}).values())
    quality_issue_total = quality_report.get("total_issue_count", 0)
    project_issue_total = project_quality_report.get("issue_count", 0)
    score = continuity_issue_total + quality_issue_total + project_issue_total
    return {
        "run_name": output_dir.name,
        "output_dir": str(output_dir),
        "completed_steps": run_manifest.get("completed_steps", []),
        "summary": run_manifest.get("summary", {}),
        "chapter_statuses": _build_project_chapter_statuses(run_manifest),
        "score": score,
        "continuity_issue_total": continuity_issue_total,
        "quality_issue_total": quality_issue_total,
        "project_issue_total": project_issue_total,
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
    return sorted(filtered, key=lambda candidate: (candidate.get("score", 0), candidate.get("run_name", "")))


def _select_best_run(run_candidates: list[dict[str, Any]]) -> dict[str, Any]:
    if not run_candidates:
        return {}
    best = min(run_candidates, key=lambda candidate: (candidate.get("score", 0), candidate.get("run_name", "")))
    return {
        "run_name": best.get("run_name"),
        "output_dir": best.get("output_dir"),
        "score": best.get("score"),
        "comparison_basis": [
            "continuity_issue_total",
            "quality_issue_total",
            "project_issue_total",
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
    pipeline = StoryPipeline(llm_client=llm_client, output_dir=output_dir, file_format=args.format)
    return pipeline.run(story_input=story_input, resume_from=resume_from, rerun_from=rerun_from)


def rerun_project_chapter(args: argparse.Namespace, output_dir: Path):
    llm_client = build_llm_client(provider=args.provider, model=args.model)
    pipeline = StoryPipeline(llm_client=llm_client, output_dir=output_dir, file_format=args.format)
    return pipeline.rerun_chapter(resume_from=output_dir, chapter_number=args.chapter_number)


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
        issue_count = sum(artifacts.continuity_report.get("issue_counts", {}).values())
        print(f"Generated short-story artifacts in: {output_dir.resolve()}")
        print(f"Selected logline: {artifacts.loglines[0]['title']}")
        print(f"Chapter count: {len(artifacts.chapter_plan)}")
        print(f"Continuity severity: {artifacts.continuity_report.get('severity', 'unknown')}")
        print(f"Continuity issues flagged: {issue_count}")
        return 0

    if args.command == "resume-project":
        project_layout, output_dir = load_project_run_context(Path(args.projects_dir), args.project_id)
        artifacts = run_pipeline(args, output_dir, resume_from=output_dir, rerun_from=args.rerun_from)
        save_project_state(project_layout, Path(args.projects_dir), args.project_id, output_dir, args.format)
        issue_count = sum(artifacts.continuity_report.get("issue_counts", {}).values())
        print(f"Generated short-story artifacts in: {output_dir.resolve()}")
        print(f"Selected logline: {artifacts.loglines[0]['title']}")
        print(f"Chapter count: {len(artifacts.chapter_plan)}")
        print(f"Continuity severity: {artifacts.continuity_report.get('severity', 'unknown')}")
        print(f"Continuity issues flagged: {issue_count}")
        return 0

    if args.command == "rerun-chapter":
        project_layout, output_dir = load_project_run_context(Path(args.projects_dir), args.project_id)
        artifacts = rerun_project_chapter(args, output_dir)
        save_project_state(project_layout, Path(args.projects_dir), args.project_id, output_dir, args.format)
        issue_count = sum(artifacts.continuity_report.get("issue_counts", {}).values())
        print(f"Generated short-story artifacts in: {output_dir.resolve()}")
        print(f"Selected logline: {artifacts.loglines[0]['title']}")
        print(f"Chapter count: {len(artifacts.chapter_plan)}")
        print(f"Continuity severity: {artifacts.continuity_report.get('severity', 'unknown')}")
        print(f"Continuity issues flagged: {issue_count}")
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
    issue_count = sum(artifacts.continuity_report.get("issue_counts", {}).values())

    print(f"Generated short-story artifacts in: {output_dir.resolve()}")
    print(f"Selected logline: {artifacts.loglines[0]['title']}")
    print(f"Chapter count: {len(artifacts.chapter_plan)}")
    print(f"Continuity severity: {artifacts.continuity_report.get('severity', 'unknown')}")
    print(f"Continuity issues flagged: {issue_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
