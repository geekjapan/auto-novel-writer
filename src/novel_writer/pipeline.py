from __future__ import annotations

from dataclasses import asdict
from difflib import unified_diff
from pathlib import Path

from novel_writer.continuity import ContinuityChecker
from novel_writer.llm_client import BaseLLMClient
from novel_writer.rerun_policy import ContinuityRerunPolicy
from novel_writer.schema import StoryArtifacts, StoryInput
from novel_writer.storage import load_artifact, save_artifact


PIPELINE_STEP_ORDER = [
    "story_input",
    "loglines",
    "characters",
    "three_act_plot",
    "chapter_plan",
    "chapter_drafts",
    "continuity_report",
    "quality_report",
    "revised_chapter_drafts",
    "story_summary",
    "project_quality_report",
    "publish_ready_bundle",
]

REVISION_MAX_ATTEMPTS = 2


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
        self.long_run_status = self._default_long_run_status()

    def run(
        self,
        story_input: StoryInput | None = None,
        resume_from: Path | None = None,
        rerun_from: str | None = None,
    ) -> StoryArtifacts:
        if resume_from is None and story_input is None:
            raise ValueError("story_input is required unless resume_from is provided.")

        if rerun_from is not None and rerun_from not in PIPELINE_STEP_ORDER:
            raise ValueError(f"Unsupported rerun step: {rerun_from}")

        if resume_from is not None:
            artifacts, selected_logline, checkpoints, self.long_run_status = self._load_resume_state(resume_from)
            if story_input is not None:
                artifacts.story_input = story_input
        else:
            artifacts = StoryArtifacts(story_input=story_input)
            selected_logline = {}
            checkpoints = []
            self.long_run_status = self._default_long_run_status()
        artifacts.normalize_chapter_artifacts()

        if rerun_from is not None:
            checkpoints = self._truncate_checkpoints(checkpoints, rerun_from)
            self._reset_for_step(artifacts, rerun_from)
            start_index = PIPELINE_STEP_ORDER.index(rerun_from)
        elif checkpoints:
            completed_steps = checkpoints[-1]["completed_steps"]
            if self.long_run_status.get("should_stop"):
                return artifacts
            if completed_steps == PIPELINE_STEP_ORDER:
                return artifacts
            start_index = len(completed_steps)
        else:
            start_index = 0

        for step_name in PIPELINE_STEP_ORDER[start_index:]:
            selected_logline = self._run_step(step_name, artifacts.story_input, selected_logline, artifacts, checkpoints)
            if step_name == "continuity_report" and self.long_run_status.get("should_stop"):
                return artifacts

        return artifacts

    def rerun_chapter(self, resume_from: Path, chapter_number: int) -> StoryArtifacts:
        artifacts, selected_logline, checkpoints, self.long_run_status = self._load_resume_state(resume_from)
        chapter_index = chapter_number - 1
        if chapter_number <= 0:
            raise ValueError("chapter_number must be greater than 0.")
        if chapter_index >= len(artifacts.chapter_plan):
            raise ValueError(f"chapter_number {chapter_number} is out of range.")

        artifacts.normalize_chapter_artifacts()
        chapter_draft = self.llm_client.generate_chapter_draft(
            artifacts.story_input,
            selected_logline,
            artifacts.characters,
            artifacts.chapter_plan,
            chapter_index=chapter_index,
        )
        artifacts.set_chapter_draft(chapter_index, chapter_draft)
        self._save_chapter_draft_artifact(chapter_index, chapter_draft)
        if chapter_index == 0:
            save_artifact(self.output_dir, "05_chapter_1_draft", artifacts.get_chapter_draft(0), self.file_format)

        chapter_report = self._build_report_with_decision(artifacts, chapter_index=chapter_index)
        self._replace_chapter_history_entry(artifacts.continuity_history, chapter_index, chapter_report)
        if chapter_index == 0:
            artifacts.continuity_report = chapter_report
            artifacts.quality_report = self.continuity_checker.build_quality_report(chapter_report)
            save_artifact(self.output_dir, "continuity_report", artifacts.continuity_report, "json")
            save_artifact(self.output_dir, "quality_report", artifacts.quality_report, "json")

        artifacts.rerun_history.append(
            {
                "attempt": self._next_rerun_attempt(artifacts.rerun_history, chapter_index),
                "chapter_index": chapter_index,
                "triggered_by": "manual",
                "action_taken": "reran_chapter_1_draft" if chapter_index == 0 else "reran_chapter_draft",
                "severity": chapter_report["severity"],
                "recommended_action": chapter_report["recommended_action"],
                "weighted_score": chapter_report["weighted_score"],
                "issue_counts": chapter_report.get("issue_counts", {}),
            }
        )

        chapter_quality_report = self.continuity_checker.build_quality_report(chapter_report)
        self._run_revision_loop(
            artifacts.story_input,
            artifacts,
            chapter_index=chapter_index,
            continuity_report=chapter_report,
            quality_report=chapter_quality_report,
        )
        revised_chapter_draft = artifacts.get_revised_chapter_draft(chapter_index)
        self._save_revised_chapter_draft_artifact(chapter_index, revised_chapter_draft)
        if chapter_index == 0:
            save_artifact(self.output_dir, "revised_chapter_1_draft", revised_chapter_draft, self.file_format)

        artifacts.story_summary = self.llm_client.generate_story_summary(
            artifacts.story_input,
            selected_logline,
            artifacts.chapter_plan,
            artifacts.revised_chapter_drafts,
        )
        save_artifact(self.output_dir, "story_summary", artifacts.story_summary, "json")

        artifacts.project_quality_report = self.continuity_checker.build_project_quality_report(artifacts)
        save_artifact(self.output_dir, "project_quality_report", artifacts.project_quality_report, "json")

        artifacts.publish_ready_bundle = {
            "title": artifacts.story_summary.get("title") or selected_logline.get("title"),
            "synopsis": artifacts.story_summary.get("synopsis", ""),
            "chapter_count": len(artifacts.revised_chapter_drafts),
            "chapters": artifacts.revised_chapter_drafts,
            "story_summary": artifacts.story_summary,
            "overall_quality_report": artifacts.project_quality_report,
            "selected_logline": selected_logline,
        }
        save_artifact(self.output_dir, "publish_ready_bundle", artifacts.publish_ready_bundle, "json")

        completed_steps = checkpoints[-1]["completed_steps"] if checkpoints else []
        rerun_checkpoints = list(checkpoints)
        if completed_steps != PIPELINE_STEP_ORDER:
            rerun_checkpoints = [
                {
                    "step": step_name,
                    "status": "completed",
                    "completed_steps": PIPELINE_STEP_ORDER[: index + 1],
                }
                for index, step_name in enumerate(PIPELINE_STEP_ORDER)
            ]
        self._save_manifest(artifacts, selected_logline, rerun_checkpoints)
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
            self._save_chapter_draft_artifact(chapter_index, chapter_draft)
        save_artifact(self.output_dir, "05_chapter_1_draft", artifacts.get_chapter_draft(0), self.file_format)
        self._mark_checkpoint("chapter_drafts", checkpoints, artifacts, selected_logline)

    def _run_continuity_report_step(
        self,
        story_input: StoryInput,
        selected_logline: dict,
        artifacts: StoryArtifacts,
        checkpoints: list[dict],
    ) -> None:
        compatibility_report = {}
        artifacts.continuity_history = []
        for chapter_index, _chapter_draft in enumerate(artifacts.chapter_drafts):
            chapter_report = self._build_report_with_decision(artifacts, chapter_index=chapter_index)
            chapter_report = self._maybe_rerun_from_decision(
                story_input,
                selected_logline,
                artifacts,
                chapter_index=chapter_index,
                chapter_report=chapter_report,
            )
            artifacts.continuity_history.append(chapter_report)
            if chapter_index == 0:
                compatibility_report = chapter_report
        artifacts.continuity_report = compatibility_report
        self.long_run_status = self.rerun_policy.decide_long_run(
            artifacts.continuity_history,
            artifacts.rerun_history,
        )
        save_artifact(self.output_dir, "continuity_report", artifacts.continuity_report, "json")
        self._mark_checkpoint("continuity_report", checkpoints, artifacts, selected_logline)

    def _run_quality_report_step(
        self,
        artifacts: StoryArtifacts,
        checkpoints: list[dict],
        selected_logline: dict,
    ) -> None:
        artifacts.quality_report = self.continuity_checker.build_quality_report(artifacts.continuity_report)
        save_artifact(self.output_dir, "quality_report", artifacts.quality_report, "json")
        self._mark_checkpoint("quality_report", checkpoints, artifacts, selected_logline)

    def _run_revised_chapter_drafts_step(
        self,
        story_input: StoryInput,
        selected_logline: dict,
        artifacts: StoryArtifacts,
        checkpoints: list[dict],
    ) -> None:
        for chapter_index, _chapter_draft in enumerate(artifacts.chapter_drafts):
            chapter_report = self._build_report_with_decision(artifacts, chapter_index=chapter_index)
            chapter_quality_report = self.continuity_checker.build_quality_report(chapter_report)
            self._run_revision_loop(
                story_input,
                artifacts,
                chapter_index=chapter_index,
                continuity_report=chapter_report,
                quality_report=chapter_quality_report,
            )
            self._save_revised_chapter_draft_artifact(chapter_index, artifacts.get_revised_chapter_draft(chapter_index))
        save_artifact(self.output_dir, "revised_chapter_1_draft", artifacts.revised_chapter_1_draft, self.file_format)
        self._mark_checkpoint("revised_chapter_drafts", checkpoints, artifacts, selected_logline)

    def _run_step(
        self,
        step_name: str,
        story_input: StoryInput,
        selected_logline: dict,
        artifacts: StoryArtifacts,
        checkpoints: list[dict],
    ) -> dict:
        if step_name == "story_input":
            self._run_story_input_step(artifacts, checkpoints)
            return selected_logline
        if step_name == "loglines":
            return self._run_loglines_step(artifacts, checkpoints)
        if step_name == "characters":
            self._run_characters_step(story_input, selected_logline, artifacts, checkpoints)
            return selected_logline
        if step_name == "three_act_plot":
            self._run_three_act_plot_step(story_input, selected_logline, artifacts, checkpoints)
            return selected_logline
        if step_name == "chapter_plan":
            self._run_chapter_plan_step(story_input, selected_logline, artifacts, checkpoints)
            return selected_logline
        if step_name == "chapter_drafts":
            self._run_chapter_drafts_step(story_input, selected_logline, artifacts, checkpoints)
            return selected_logline
        if step_name == "continuity_report":
            self._run_continuity_report_step(story_input, selected_logline, artifacts, checkpoints)
            return selected_logline
        if step_name == "quality_report":
            self._run_quality_report_step(artifacts, checkpoints, selected_logline)
            return selected_logline
        if step_name == "revised_chapter_drafts":
            self._run_revised_chapter_drafts_step(story_input, selected_logline, artifacts, checkpoints)
            return selected_logline
        if step_name == "story_summary":
            self._run_story_summary_step(story_input, selected_logline, artifacts, checkpoints)
            return selected_logline
        if step_name == "project_quality_report":
            self._run_project_quality_report_step(artifacts, checkpoints, selected_logline)
            return selected_logline
        if step_name == "publish_ready_bundle":
            self._run_publish_ready_bundle_step(artifacts, checkpoints, selected_logline)
            return selected_logline
        raise ValueError(f"Unsupported step: {step_name}")

    def _load_resume_state(self, resume_from: Path) -> tuple[StoryArtifacts, dict, list[dict], dict]:
        manifest = load_artifact(resume_from, "manifest")
        artifacts_data = manifest.get("artifacts", {})
        story_input_data = artifacts_data.get("story_input") or load_artifact(resume_from, "story_input")
        artifacts = StoryArtifacts(story_input=StoryInput(**story_input_data))
        for field_name in [
            "loglines",
            "characters",
            "three_act_plot",
            "chapter_plan",
            "chapter_drafts",
            "chapter_1_draft",
            "continuity_report",
            "continuity_history",
            "quality_report",
            "revised_chapter_drafts",
            "revised_chapter_1_draft",
            "story_summary",
            "project_quality_report",
            "publish_ready_bundle",
            "rerun_history",
            "revise_history",
        ]:
            if field_name in artifacts_data:
                setattr(artifacts, field_name, artifacts_data[field_name])
        artifacts.normalize_chapter_artifacts()
        return (
            artifacts,
            manifest.get("selected_logline", {}),
            list(manifest.get("checkpoints", [])),
            dict(manifest.get("long_run_status", self._default_long_run_status())),
        )

    def _truncate_checkpoints(self, checkpoints: list[dict], rerun_from: str) -> list[dict]:
        rerun_index = PIPELINE_STEP_ORDER.index(rerun_from)
        kept_steps = set(PIPELINE_STEP_ORDER[:rerun_index])
        return [checkpoint for checkpoint in checkpoints if checkpoint.get("step") in kept_steps]

    def _reset_for_step(self, artifacts: StoryArtifacts, rerun_from: str) -> None:
        if rerun_from == "story_input":
            self._reset_from_loglines(artifacts)
            return
        if rerun_from == "loglines":
            self._reset_from_loglines(artifacts)
            return
        if rerun_from == "characters":
            self._reset_from_characters(artifacts)
            return
        if rerun_from == "three_act_plot":
            self._reset_from_three_act_plot(artifacts)
            return
        if rerun_from == "chapter_plan":
            self._reset_from_chapter_plan(artifacts)
            return
        if rerun_from == "chapter_drafts":
            self._reset_from_chapter_drafts(artifacts)
            return
        if rerun_from == "continuity_report":
            self._reset_from_continuity_report(artifacts)
            return
        if rerun_from == "quality_report":
            self._reset_from_quality_report(artifacts)
            return
        if rerun_from == "revised_chapter_drafts":
            self._reset_from_revised_chapter_drafts(artifacts)
            return
        if rerun_from == "story_summary":
            self._reset_from_story_summary(artifacts)
            return
        if rerun_from == "project_quality_report":
            self._reset_from_project_quality_report(artifacts)
            return
        if rerun_from == "publish_ready_bundle":
            self._reset_from_publish_ready_bundle(artifacts)

    def _reset_from_loglines(self, artifacts: StoryArtifacts) -> None:
        artifacts.loglines = []
        self._reset_from_characters(artifacts)

    def _reset_from_characters(self, artifacts: StoryArtifacts) -> None:
        artifacts.characters = []
        self._reset_from_three_act_plot(artifacts)

    def _reset_from_three_act_plot(self, artifacts: StoryArtifacts) -> None:
        artifacts.three_act_plot = {}
        self._reset_from_chapter_plan(artifacts)

    def _reset_from_chapter_plan(self, artifacts: StoryArtifacts) -> None:
        artifacts.chapter_plan = []
        self._reset_from_chapter_drafts(artifacts)

    def _reset_from_chapter_drafts(self, artifacts: StoryArtifacts) -> None:
        artifacts.chapter_drafts = []
        artifacts.chapter_1_draft = {}
        self._reset_from_continuity_report(artifacts)

    def _reset_from_continuity_report(self, artifacts: StoryArtifacts) -> None:
        artifacts.continuity_report = {}
        artifacts.continuity_history = []
        artifacts.rerun_history = []
        self.long_run_status = self._default_long_run_status()
        self._reset_from_quality_report(artifacts)

    def _reset_from_quality_report(self, artifacts: StoryArtifacts) -> None:
        artifacts.quality_report = {}
        self._reset_from_revised_chapter_drafts(artifacts)

    def _reset_from_revised_chapter_drafts(self, artifacts: StoryArtifacts) -> None:
        artifacts.revised_chapter_drafts = []
        artifacts.revised_chapter_1_draft = {}
        artifacts.revise_history = []
        self._reset_from_story_summary(artifacts)

    def _reset_from_story_summary(self, artifacts: StoryArtifacts) -> None:
        artifacts.story_summary = {}
        self._reset_from_project_quality_report(artifacts)

    def _reset_from_project_quality_report(self, artifacts: StoryArtifacts) -> None:
        artifacts.project_quality_report = {}
        self._reset_from_publish_ready_bundle(artifacts)

    def _reset_from_publish_ready_bundle(self, artifacts: StoryArtifacts) -> None:
        artifacts.publish_ready_bundle = {}

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
        artifacts.normalize_chapter_artifacts()
        manifest = {
            "summary": artifacts.summary(),
            "artifact_contract": artifacts.artifact_contract(),
            "selected_logline": selected_logline,
            "continuity_history": artifacts.continuity_history,
            "rerun_history": artifacts.rerun_history,
            "revise_history": artifacts.revise_history,
            "chapter_histories": self._build_chapter_histories(artifacts),
            "long_run_status": self.long_run_status,
            "checkpoints": checkpoints,
            "current_step": checkpoints[-1]["step"] if checkpoints else None,
            "completed_steps": checkpoints[-1]["completed_steps"] if checkpoints else [],
            "artifacts": asdict(artifacts),
        }
        save_artifact(self.output_dir, "manifest", manifest, self.file_format)

    def _default_long_run_status(self) -> dict:
        return self.rerun_policy.decide_long_run([], [])

    def _build_chapter_histories(self, artifacts: StoryArtifacts) -> list[dict]:
        chapter_histories: list[dict] = []
        for chapter_index, chapter in enumerate(artifacts.chapter_plan):
            chapter_histories.append(
                {
                    "chapter_index": chapter_index,
                    "chapter_number": chapter.get("chapter_number"),
                    "continuity": [
                        entry for entry in artifacts.continuity_history if entry.get("chapter_index") == chapter_index
                    ],
                    "reruns": [
                        entry for entry in artifacts.rerun_history if entry.get("chapter_index") == chapter_index
                    ],
                    "revisions": [
                        entry for entry in artifacts.revise_history if entry.get("chapter_index") == chapter_index
                    ],
                }
            )
        return chapter_histories

    def _replace_chapter_history_entry(
        self,
        chapter_history: list[dict],
        chapter_index: int,
        payload: dict,
    ) -> None:
        for index, entry in enumerate(chapter_history):
            if entry.get("chapter_index") == chapter_index:
                chapter_history[index] = payload
                return
        chapter_history.append(payload)
        chapter_history.sort(key=lambda entry: entry.get("chapter_index", 0))

    def _next_rerun_attempt(self, rerun_history: list[dict], chapter_index: int) -> int:
        matching_attempts = [
            int(entry.get("attempt", 0))
            for entry in rerun_history
            if entry.get("chapter_index") == chapter_index
        ]
        return max(matching_attempts, default=0) + 1

    def _build_report_with_decision(self, artifacts: StoryArtifacts, chapter_index: int = 0) -> dict:
        report = self.continuity_checker.build_report(artifacts, chapter_index=chapter_index)
        decision = self.rerun_policy.decide(report.get("issue_counts", {}))
        report["severity"] = decision.severity
        report["recommended_action"] = decision.action
        report["weighted_score"] = decision.weighted_score
        return report

    def _save_chapter_draft_artifact(self, chapter_index: int, chapter_draft: dict) -> None:
        save_artifact(self.output_dir, f"chapter_{chapter_index + 1}_draft", chapter_draft, self.file_format)

    def _save_revised_chapter_draft_artifact(self, chapter_index: int, revised_chapter_draft: dict) -> None:
        save_artifact(
            self.output_dir,
            f"revised_chapter_{chapter_index + 1}_draft",
            revised_chapter_draft,
            self.file_format,
        )

    def _run_story_summary_step(
        self,
        story_input: StoryInput,
        selected_logline: dict,
        artifacts: StoryArtifacts,
        checkpoints: list[dict],
    ) -> None:
        artifacts.story_summary = self.llm_client.generate_story_summary(
            story_input,
            selected_logline,
            artifacts.chapter_plan,
            artifacts.revised_chapter_drafts,
        )
        save_artifact(self.output_dir, "story_summary", artifacts.story_summary, "json")
        self._mark_checkpoint("story_summary", checkpoints, artifacts, selected_logline)

    def _run_project_quality_report_step(
        self,
        artifacts: StoryArtifacts,
        checkpoints: list[dict],
        selected_logline: dict,
    ) -> None:
        artifacts.project_quality_report = self.continuity_checker.build_project_quality_report(artifacts)
        save_artifact(self.output_dir, "project_quality_report", artifacts.project_quality_report, "json")
        self._mark_checkpoint("project_quality_report", checkpoints, artifacts, selected_logline)

    def _run_publish_ready_bundle_step(
        self,
        artifacts: StoryArtifacts,
        checkpoints: list[dict],
        selected_logline: dict,
    ) -> None:
        artifacts.publish_ready_bundle = {
            "title": artifacts.story_summary.get("title") or selected_logline.get("title"),
            "synopsis": artifacts.story_summary.get("synopsis", ""),
            "chapter_count": len(artifacts.revised_chapter_drafts),
            "chapters": artifacts.revised_chapter_drafts,
            "story_summary": artifacts.story_summary,
            "overall_quality_report": artifacts.project_quality_report,
            "selected_logline": selected_logline,
        }
        save_artifact(self.output_dir, "publish_ready_bundle", artifacts.publish_ready_bundle, "json")
        self._mark_checkpoint("publish_ready_bundle", checkpoints, artifacts, selected_logline)

    def _maybe_rerun_from_decision(
        self,
        story_input: StoryInput,
        selected_logline: dict,
        artifacts: StoryArtifacts,
        chapter_index: int,
        chapter_report: dict,
    ) -> dict:
        decision = self.rerun_policy.decide(chapter_report.get("issue_counts", {}))
        artifacts.rerun_history.append(
            {
                "attempt": 1,
                "chapter_index": chapter_index,
                **decision.to_dict(),
            }
        )

        if decision.severity == "medium":
            chapter_draft = self.llm_client.generate_chapter_draft(
                story_input,
                selected_logline,
                artifacts.characters,
                artifacts.chapter_plan,
                chapter_index=chapter_index,
            )
            artifacts.set_chapter_draft(chapter_index, chapter_draft)
            self._save_chapter_draft_artifact(chapter_index, chapter_draft)
            if chapter_index == 0:
                save_artifact(self.output_dir, "05_chapter_1_draft", artifacts.get_chapter_draft(0), self.file_format)
            chapter_report = self._build_report_with_decision(artifacts, chapter_index=chapter_index)
            artifacts.rerun_history.append(
                {
                    "attempt": 2,
                    "chapter_index": chapter_index,
                    "triggered_by": "medium",
                    "action_taken": "reran_chapter_1_draft" if chapter_index == 0 else "reran_chapter_draft",
                    "resulting_severity": chapter_report["severity"],
                    "issue_counts": chapter_report.get("issue_counts", {}),
                }
            )
            return chapter_report

        if decision.severity == "high":
            artifacts.chapter_plan = self.llm_client.generate_chapter_plan(
                story_input,
                selected_logline,
                artifacts.characters,
                artifacts.three_act_plot,
            )
            save_artifact(self.output_dir, "04_chapter_plan", artifacts.chapter_plan, self.file_format)

            for rerun_chapter_index, _chapter in enumerate(artifacts.chapter_plan):
                chapter_draft = self.llm_client.generate_chapter_draft(
                    story_input,
                    selected_logline,
                    artifacts.characters,
                    artifacts.chapter_plan,
                    chapter_index=rerun_chapter_index,
                )
                artifacts.set_chapter_draft(rerun_chapter_index, chapter_draft)
                self._save_chapter_draft_artifact(rerun_chapter_index, chapter_draft)
            save_artifact(self.output_dir, "05_chapter_1_draft", artifacts.get_chapter_draft(0), self.file_format)
            chapter_report = self._build_report_with_decision(artifacts, chapter_index=chapter_index)
            artifacts.rerun_history.append(
                {
                    "attempt": 2,
                    "chapter_index": chapter_index,
                    "triggered_by": "high",
                    "action_taken": "reran_from_chapter_plan",
                    "resulting_severity": chapter_report["severity"],
                    "issue_counts": chapter_report.get("issue_counts", {}),
                }
            )
            return chapter_report

        return chapter_report

    def _run_revision_loop(
        self,
        story_input: StoryInput,
        artifacts: StoryArtifacts,
        chapter_index: int,
        continuity_report: dict,
        quality_report: dict,
    ) -> None:
        max_attempts = 1 if quality_report.get("overall_recommendation") == "accept" else REVISION_MAX_ATTEMPTS
        current_source = artifacts.get_chapter_draft(chapter_index)

        for attempt in range(1, max_attempts + 1):
            revised_chapter_draft = self._revise_chapter(
                story_input,
                artifacts,
                chapter_index=chapter_index,
                source_draft=current_source,
                continuity_report=continuity_report,
            )
            artifacts.set_revised_chapter_draft(chapter_index, revised_chapter_draft)
            changed = revised_chapter_draft != current_source
            stop_reason = None
            if not changed:
                stop_reason = "no_changes_detected"
            elif attempt >= max_attempts:
                stop_reason = "max_attempts_reached"

            artifacts.revise_history.append(
                {
                    "attempt": attempt,
                    "chapter_index": chapter_index,
                    "source": "chapter_1_draft" if chapter_index == 0 and attempt == 1 else f"revised_chapter_drafts[{chapter_index}]",
                    "target": "revised_chapter_1_draft" if chapter_index == 0 else f"revised_chapter_drafts[{chapter_index}]",
                    "continuity_severity": continuity_report.get("severity"),
                    "quality_recommendation": quality_report.get("overall_recommendation"),
                    "applied_rules": [
                        "style_adjustment",
                        "redundancy_reduction",
                        "summary_alignment",
                    ],
                    "diff": self._build_revision_diff(current_source, revised_chapter_draft),
                    "stop_reason": stop_reason,
                }
            )
            if stop_reason is not None:
                break
            current_source = revised_chapter_draft

    def _revise_chapter(
        self,
        story_input: StoryInput,
        artifacts: StoryArtifacts,
        chapter_index: int,
        source_draft: dict,
        continuity_report: dict,
    ) -> dict:
        revised_chapter_draft = self.llm_client.revise_chapter_draft(
            story_input,
            artifacts.chapter_plan,
            source_draft,
            continuity_report,
            chapter_index=chapter_index,
        )
        return revised_chapter_draft

    def _build_revision_diff(self, before_draft: dict, after_draft: dict) -> dict:
        changed_fields = sorted(
            key
            for key in set(before_draft) | set(after_draft)
            if before_draft.get(key) != after_draft.get(key)
        )
        before_summary = str(before_draft.get("summary", ""))
        after_summary = str(after_draft.get("summary", ""))
        before_text = str(before_draft.get("text", ""))
        after_text = str(after_draft.get("text", ""))
        text_diff = "".join(
            unified_diff(
                before_text.splitlines(keepends=True),
                after_text.splitlines(keepends=True),
                fromfile="before",
                tofile="after",
            )
        )
        return {
            "changed": bool(changed_fields),
            "changed_fields": changed_fields,
            "summary_before": before_summary,
            "summary_after": after_summary,
            "text_diff": text_diff,
        }
