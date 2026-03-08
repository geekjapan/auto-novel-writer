from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from novel_writer.continuity import ContinuityChecker
from novel_writer.llm_client import BaseLLMClient
from novel_writer.rerun_policy import ContinuityRerunPolicy
from novel_writer.schema import StoryArtifacts, StoryInput
from novel_writer.storage import save_artifact


PIPELINE_STEP_ORDER = [
    "story_input",
    "loglines",
    "characters",
    "three_act_plot",
    "chapter_plan",
    "chapter_drafts",
    "continuity_report",
    "revised_chapter_drafts",
]


class StoryPipeline:
    def __init__(
        self,
        llm_client: BaseLLMClient,
        output_dir: Path,
        file_format: str = "json",
        continuity_checker: ContinuityChecker | None = None,
        rerun_policy: ContinuityRerunPolicy | None = None,
    ) -> None:
        self.llm_client = llm_client
        self.output_dir = output_dir
        self.file_format = file_format
        self.continuity_checker = continuity_checker or ContinuityChecker()
        self.rerun_policy = rerun_policy or ContinuityRerunPolicy()

    def run(self, story_input: StoryInput) -> StoryArtifacts:
        artifacts = StoryArtifacts(story_input=story_input)
        checkpoints: list[dict] = []
        selected_logline: dict = {}

        self._run_story_input_step(artifacts, checkpoints)

        selected_logline = self._run_loglines_step(artifacts, checkpoints)
        self._run_characters_step(story_input, selected_logline, artifacts, checkpoints)
        self._run_three_act_plot_step(story_input, selected_logline, artifacts, checkpoints)
        self._run_chapter_plan_step(story_input, selected_logline, artifacts, checkpoints)
        self._run_chapter_drafts_step(story_input, selected_logline, artifacts, checkpoints)

        artifacts.continuity_report = self._build_report_with_decision(artifacts)
        self._maybe_rerun_from_decision(story_input, selected_logline, artifacts)
        save_artifact(self.output_dir, "continuity_report", artifacts.continuity_report, "json")
        self._mark_checkpoint("continuity_report", checkpoints, artifacts, selected_logline)
        for chapter_index, _chapter_draft in enumerate(artifacts.chapter_drafts):
            self._revise_chapter(story_input, artifacts, chapter_index=chapter_index)
        save_artifact(self.output_dir, "revised_chapter_1_draft", artifacts.revised_chapter_1_draft, self.file_format)
        self._mark_checkpoint("revised_chapter_drafts", checkpoints, artifacts, selected_logline)
        return artifacts

    def _run_story_input_step(self, artifacts: StoryArtifacts, checkpoints: list[dict]) -> None:
        save_artifact(self.output_dir, "story_input", artifacts.story_input.to_dict(), self.file_format)
        self._mark_checkpoint("story_input", checkpoints, artifacts, {})

    def _run_loglines_step(self, artifacts: StoryArtifacts, checkpoints: list[dict]) -> dict:
        artifacts.loglines = self.llm_client.generate_loglines(artifacts.story_input)
        save_artifact(self.output_dir, "01_loglines", artifacts.loglines, self.file_format)
        selected_logline = artifacts.loglines[0]
        self._mark_checkpoint("loglines", checkpoints, artifacts, selected_logline)
        return selected_logline

    def _run_characters_step(
        self,
        story_input: StoryInput,
        selected_logline: dict,
        artifacts: StoryArtifacts,
        checkpoints: list[dict],
    ) -> None:
        artifacts.characters = self.llm_client.generate_characters(story_input, selected_logline)
        save_artifact(self.output_dir, "02_characters", artifacts.characters, self.file_format)
        self._mark_checkpoint("characters", checkpoints, artifacts, selected_logline)

    def _run_three_act_plot_step(
        self,
        story_input: StoryInput,
        selected_logline: dict,
        artifacts: StoryArtifacts,
        checkpoints: list[dict],
    ) -> None:
        artifacts.three_act_plot = self.llm_client.generate_three_act_plot(
            story_input,
            selected_logline,
            artifacts.characters,
        )
        save_artifact(self.output_dir, "03_three_act_plot", artifacts.three_act_plot, self.file_format)
        self._mark_checkpoint("three_act_plot", checkpoints, artifacts, selected_logline)

    def _run_chapter_plan_step(
        self,
        story_input: StoryInput,
        selected_logline: dict,
        artifacts: StoryArtifacts,
        checkpoints: list[dict],
    ) -> None:
        artifacts.chapter_plan = self.llm_client.generate_chapter_plan(
            story_input,
            selected_logline,
            artifacts.characters,
            artifacts.three_act_plot,
        )
        save_artifact(self.output_dir, "04_chapter_plan", artifacts.chapter_plan, self.file_format)
        self._mark_checkpoint("chapter_plan", checkpoints, artifacts, selected_logline)

    def _run_chapter_drafts_step(
        self,
        story_input: StoryInput,
        selected_logline: dict,
        artifacts: StoryArtifacts,
        checkpoints: list[dict],
    ) -> None:
        for chapter_index, _chapter in enumerate(artifacts.chapter_plan):
            chapter_draft = self.llm_client.generate_chapter_draft(
                story_input,
                selected_logline,
                artifacts.characters,
                artifacts.chapter_plan,
                chapter_index=chapter_index,
            )
            artifacts.set_chapter_draft(chapter_index, chapter_draft)
        save_artifact(self.output_dir, "05_chapter_1_draft", artifacts.get_chapter_draft(0), self.file_format)
        self._mark_checkpoint("chapter_drafts", checkpoints, artifacts, selected_logline)

    def _mark_checkpoint(
        self,
        step_name: str,
        checkpoints: list[dict],
        artifacts: StoryArtifacts,
        selected_logline: dict,
    ) -> None:
        completed_steps = [entry["step"] for entry in checkpoints]
        checkpoints.append(
            {
                "step": step_name,
                "status": "completed",
                "completed_steps": completed_steps + [step_name],
            }
        )
        self._save_manifest(artifacts, selected_logline, checkpoints)

    def _save_manifest(
        self,
        artifacts: StoryArtifacts,
        selected_logline: dict,
        checkpoints: list[dict],
    ) -> None:
        manifest = {
            "summary": artifacts.summary(),
            "selected_logline": selected_logline,
            "rerun_history": artifacts.rerun_history,
            "revise_history": artifacts.revise_history,
            "checkpoints": checkpoints,
            "current_step": checkpoints[-1]["step"] if checkpoints else None,
            "completed_steps": checkpoints[-1]["completed_steps"] if checkpoints else [],
            "artifacts": asdict(artifacts),
        }
        save_artifact(self.output_dir, "manifest", manifest, self.file_format)

    def _build_report_with_decision(self, artifacts: StoryArtifacts) -> dict:
        report = self.continuity_checker.build_report(artifacts)
        decision = self.rerun_policy.decide(report.get("issue_counts", {}))
        report["severity"] = decision.severity
        report["recommended_action"] = decision.action
        report["weighted_score"] = decision.weighted_score
        return report

    def _maybe_rerun_from_decision(
        self,
        story_input: StoryInput,
        selected_logline: dict,
        artifacts: StoryArtifacts,
    ) -> None:
        decision = self.rerun_policy.decide(artifacts.continuity_report.get("issue_counts", {}))
        artifacts.rerun_history.append(
            {
                "attempt": 1,
                **decision.to_dict(),
            }
        )

        if decision.severity == "medium":
            chapter_draft = self.llm_client.generate_chapter_draft(
                story_input,
                selected_logline,
                artifacts.characters,
                artifacts.chapter_plan,
                chapter_index=0,
            )
            artifacts.set_chapter_draft(0, chapter_draft)
            save_artifact(self.output_dir, "05_chapter_1_draft", artifacts.get_chapter_draft(0), self.file_format)
            artifacts.continuity_report = self._build_report_with_decision(artifacts)
            artifacts.rerun_history.append(
                {
                    "attempt": 2,
                    "chapter_index": 0,
                    "triggered_by": "medium",
                    "action_taken": "reran_chapter_1_draft",
                    "resulting_severity": artifacts.continuity_report["severity"],
                    "issue_counts": artifacts.continuity_report.get("issue_counts", {}),
                }
            )
            return

        if decision.severity == "high":
            artifacts.chapter_plan = self.llm_client.generate_chapter_plan(
                story_input,
                selected_logline,
                artifacts.characters,
                artifacts.three_act_plot,
            )
            save_artifact(self.output_dir, "04_chapter_plan", artifacts.chapter_plan, self.file_format)

            chapter_draft = self.llm_client.generate_chapter_draft(
                story_input,
                selected_logline,
                artifacts.characters,
                artifacts.chapter_plan,
                chapter_index=0,
            )
            artifacts.set_chapter_draft(0, chapter_draft)
            save_artifact(self.output_dir, "05_chapter_1_draft", artifacts.get_chapter_draft(0), self.file_format)
            artifacts.continuity_report = self._build_report_with_decision(artifacts)
            artifacts.rerun_history.append(
                {
                    "attempt": 2,
                    "chapter_index": 0,
                    "triggered_by": "high",
                    "action_taken": "reran_from_chapter_plan",
                    "resulting_severity": artifacts.continuity_report["severity"],
                    "issue_counts": artifacts.continuity_report.get("issue_counts", {}),
                }
            )

    def _revise_chapter(self, story_input: StoryInput, artifacts: StoryArtifacts, chapter_index: int) -> None:
        revised_chapter_draft = self.llm_client.revise_chapter_draft(
            story_input,
            artifacts.chapter_plan,
            artifacts.get_chapter_draft(chapter_index),
            artifacts.continuity_report,
            chapter_index=chapter_index,
        )
        artifacts.set_revised_chapter_draft(chapter_index, revised_chapter_draft)
        artifacts.revise_history.append(
            {
                "attempt": 1,
                "chapter_index": chapter_index,
                "source": "chapter_1_draft" if chapter_index == 0 else f"chapter_drafts[{chapter_index}]",
                "target": "revised_chapter_1_draft" if chapter_index == 0 else f"revised_chapter_drafts[{chapter_index}]",
                "continuity_severity": artifacts.continuity_report.get("severity"),
                "applied_rules": [
                    "style_adjustment",
                    "redundancy_reduction",
                    "summary_alignment",
                ],
            }
        )
