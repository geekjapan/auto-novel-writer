from __future__ import annotations

import argparse
from pathlib import Path

from novel_writer.llm_client import build_llm_client
from novel_writer.pipeline import PIPELINE_STEP_ORDER, StoryPipeline
from novel_writer.schema import StoryInput


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Short-story generation support pipeline MVP")
    parser.add_argument("--theme", help="Story theme")
    parser.add_argument("--genre", help="Story genre")
    parser.add_argument("--tone", help="Story tone")
    parser.add_argument("--target-length", type=int, help="Target length in words or characters")
    parser.add_argument("--output-dir", default="data/latest_run", help="Directory for generated artifacts")
    parser.add_argument(
        "--resume-from-output-dir",
        help="Read existing artifacts and manifest from this directory before continuing",
    )
    parser.add_argument(
        "--rerun-from",
        choices=PIPELINE_STEP_ORDER,
        help="When resuming, rerun from the named pipeline step",
    )
    parser.add_argument("--provider", default="mock", choices=["mock", "openai"], help="LLM provider")
    parser.add_argument("--model", default="gpt-4.1-mini", help="Model name for provider=openai")
    parser.add_argument("--format", default="json", choices=["json", "yaml"], help="Artifact serialization format")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    resume_from = Path(args.resume_from_output_dir) if args.resume_from_output_dir else None
    if args.rerun_from and resume_from is None:
        parser.error("--rerun-from requires --resume-from-output-dir.")

    if resume_from is None and not all([args.theme, args.genre, args.tone, args.target_length is not None]):
        parser.error("--theme, --genre, --tone, and --target-length are required unless resuming.")

    story_input = None
    if resume_from is None:
        story_input = StoryInput(
            theme=args.theme,
            genre=args.genre,
            tone=args.tone,
            target_length=args.target_length,
        )

    output_dir = Path(args.output_dir)
    if resume_from is not None and args.output_dir == "data/latest_run":
        output_dir = resume_from
    llm_client = build_llm_client(provider=args.provider, model=args.model)
    pipeline = StoryPipeline(llm_client=llm_client, output_dir=output_dir, file_format=args.format)
    artifacts = pipeline.run(story_input=story_input, resume_from=resume_from, rerun_from=args.rerun_from)
    issue_count = sum(
        artifacts.continuity_report.get("issue_counts", {}).values()
    )

    print(f"Generated short-story artifacts in: {output_dir.resolve()}")
    print(f"Selected logline: {artifacts.loglines[0]['title']}")
    print(f"Chapter count: {len(artifacts.chapter_plan)}")
    print(f"Continuity severity: {artifacts.continuity_report.get('severity', 'unknown')}")
    print(f"Continuity issues flagged: {issue_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
