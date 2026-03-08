from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from novel_writer.continuity import ContinuityChecker
from novel_writer.llm_client import BaseLLMClient
from novel_writer.rerun_policy import ContinuityRerunPolicy
from novel_writer.schema import StoryArtifacts, StoryInput
from novel_writer.storage import save_artifact


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
        save_artifact(self.output_dir, "story_input", story_input.to_dict(), self.file_format)

        artifacts.loglines = self.llm_client.generate_loglines(story_input)
        save_artifact(self.output_dir, "01_loglines", artifacts.loglines, self.file_format)

        selected_logline = artifacts.loglines[0]
        artifacts.characters = self.llm_client.generate_characters(story_input, selected_logline)
        save_artifact(self.output_dir, "02_characters", artifacts.characters, self.file_format)

        artifacts.three_act_plot = self.llm_client.generate_three_act_plot(
            story_input,
            selected_logline,
            artifacts.characters,
        )
        save_artifact(self.output_dir, "03_three_act_plot", artifacts.three_act_plot, self.file_format)

        artifacts.chapter_plan = self.llm_client.generate_chapter_plan(
            story_input,
            selected_logline,
            artifacts.characters,
            artifacts.three_act_plot,
        )
        save_artifact(self.output_dir, "04_chapter_plan", artifacts.chapter_plan, self.file_format)

        artifacts.chapter_1_draft = self.llm_client.generate_chapter_draft(
            story_input,
            selected_logline,
            artifacts.characters,
            artifacts.chapter_plan,
            chapter_index=0,
        )
        save_artifact(self.output_dir, "05_chapter_1_draft", artifacts.chapter_1_draft, self.file_format)

        artifacts.continuity_report = self._build_report_with_decision(artifacts)
        self._maybe_rerun_from_decision(story_input, selected_logline, artifacts)
        save_artifact(self.output_dir, "continuity_report", artifacts.continuity_report, "json")

        manifest = {
            "summary": artifacts.summary(),
            "selected_logline": selected_logline,
            "rerun_history": artifacts.rerun_history,
            "artifacts": asdict(artifacts),
        }
        save_artifact(self.output_dir, "manifest", manifest, self.file_format)
        return artifacts

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
            artifacts.chapter_1_draft = self.llm_client.generate_chapter_draft(
                story_input,
                selected_logline,
                artifacts.characters,
                artifacts.chapter_plan,
                chapter_index=0,
            )
            save_artifact(self.output_dir, "05_chapter_1_draft", artifacts.chapter_1_draft, self.file_format)
            artifacts.continuity_report = self._build_report_with_decision(artifacts)
            artifacts.rerun_history.append(
                {
                    "attempt": 2,
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

            artifacts.chapter_1_draft = self.llm_client.generate_chapter_draft(
                story_input,
                selected_logline,
                artifacts.characters,
                artifacts.chapter_plan,
                chapter_index=0,
            )
            save_artifact(self.output_dir, "05_chapter_1_draft", artifacts.chapter_1_draft, self.file_format)
            artifacts.continuity_report = self._build_report_with_decision(artifacts)
            artifacts.rerun_history.append(
                {
                    "attempt": 2,
                    "triggered_by": "high",
                    "action_taken": "reran_from_chapter_plan",
                    "resulting_severity": artifacts.continuity_report["severity"],
                    "issue_counts": artifacts.continuity_report.get("issue_counts", {}),
                }
            )
