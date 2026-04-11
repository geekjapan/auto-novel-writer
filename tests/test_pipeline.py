import json
import tempfile
import unittest
from pathlib import Path

from novel_writer.llm_client import MockLLMClient
from novel_writer.pipeline import PIPELINE_STEP_ORDER, StoryPipeline
from novel_writer.rerun_policy import ContinuityRerunPolicy
from novel_writer.schema import (
    StoryInput,
    build_handoff_summary,
    build_publish_ready_bundle_summary,
    build_story_state_summary,
    build_story_bible_summary,
    build_thread_summary,
)
from novel_writer.storage import (
    load_chapter_briefs,
    load_canon_ledger,
    load_next_action_decision,
    load_replan_history,
    load_publish_ready_bundle,
    load_scene_cards,
    save_canon_ledger,
    save_thread_registry,
)


class RecordingDraftContextLLMClient(MockLLMClient):
    def __init__(self) -> None:
        self.draft_calls: list[dict] = []
        self.revise_calls: list[dict] = []

    def generate_chapter_draft(
        self,
        story_input,
        logline,
        characters,
        three_act_plot,
        chapter_plan,
        chapter_briefs,
        scene_cards,
        canon_ledger,
        thread_registry,
        chapter_index=0,
        chapter_handoff_packet=None,
    ):
        self.draft_calls.append(
            {
                "three_act_plot": three_act_plot,
                "chapter_handoff_packet": chapter_handoff_packet,
                "chapter_plan": chapter_plan,
                "chapter_briefs": chapter_briefs,
                "scene_cards": scene_cards,
                "canon_ledger": canon_ledger,
                "thread_registry": thread_registry,
                "chapter_index": chapter_index,
            }
        )
        return super().generate_chapter_draft(
            story_input,
            logline,
            characters,
            three_act_plot,
            chapter_plan,
            chapter_briefs,
            scene_cards,
            canon_ledger,
            thread_registry,
            chapter_index=chapter_index,
            chapter_handoff_packet=chapter_handoff_packet,
        )

    def revise_chapter_draft(
        self,
        story_input,
        chapter_plan,
        chapter_draft,
        continuity_report,
        chapter_index=0,
        chapter_handoff_packet=None,
    ):
        self.revise_calls.append(
            {
                "chapter_plan": chapter_plan,
                "chapter_draft": chapter_draft,
                "continuity_report": continuity_report,
                "chapter_index": chapter_index,
                "chapter_handoff_packet": chapter_handoff_packet,
            }
        )
        return super().revise_chapter_draft(
            story_input,
            chapter_plan,
            chapter_draft,
            continuity_report,
            chapter_index=chapter_index,
            chapter_handoff_packet=chapter_handoff_packet,
        )


class NoRerunContinuityChecker:
    def build_report(self, artifacts, chapter_index=0):
        return {
            "chapter_index": chapter_index,
            "missing_fields": [],
            "character_name_mismatches": [],
            "plot_to_plan_gaps": [],
            "plan_to_draft_gaps": [],
            "length_warnings": [],
            "issue_counts": {
                "missing_fields": 0,
                "character_name_mismatches": 0,
                "plot_to_plan_gaps": 0,
                "plan_to_draft_gaps": 0,
                "length_warnings": 0,
            },
        }

    def build_quality_report(self, continuity_report):
        return {
            "overall_recommendation": "accept",
            "severity": continuity_report.get("severity", "low"),
            "source_report": "continuity_report",
            "recommendations": [],
            "issue_counts": continuity_report.get("issue_counts", {}),
            "total_issue_count": 0,
        }

    def build_project_quality_report(self, artifacts):
        return {
            "overall_recommendation": "accept",
            "source_report": "project_quality_report",
            "checks": {},
            "issue_count": 0,
            "issues": [],
        }

    def build_progress_report(self, artifacts, canon_ledger, thread_registry):
        return {
            "schema_name": "progress_report",
            "schema_version": "1.0",
            "evaluated_through_chapter": len(artifacts.chapter_plan),
            "story_state_summary": build_story_state_summary(
                canon_ledger,
                thread_registry,
                len(artifacts.chapter_plan),
            ),
            "checks": {
                "chapter_role_coverage": {"status": "ok", "summary": "ok", "evidence": []},
                "escalation_pace": {"status": "ok", "summary": "ok", "evidence": []},
                "emotional_progression": {"status": "ok", "summary": "ok", "evidence": []},
                "foreshadowing_coverage": {"status": "ok", "summary": "ok", "evidence": []},
                "unresolved_thread_load": {"status": "ok", "summary": "ok", "evidence": []},
                "climax_readiness": {"status": "ok", "summary": "ok", "evidence": []},
            },
            "issue_codes": [],
            "recommended_action": "continue",
        }


class StopBeforeRevisionContinuityChecker(NoRerunContinuityChecker):
    def build_report(self, artifacts, chapter_index=0):
        return {
            "chapter_index": chapter_index,
            "severity": "high",
            "missing_fields": [{"reason": "missing"}],
            "character_name_mismatches": [],
            "plot_to_plan_gaps": [],
            "plan_to_draft_gaps": [],
            "length_warnings": [],
            "issue_counts": {
                "missing_fields": 1,
                "character_name_mismatches": 0,
                "plot_to_plan_gaps": 0,
                "plan_to_draft_gaps": 0,
                "length_warnings": 0,
            },
        }


class ReplanTriggerContinuityChecker(NoRerunContinuityChecker):
    def build_progress_report(self, artifacts, canon_ledger, thread_registry):
        report = super().build_progress_report(artifacts, canon_ledger, thread_registry)
        report["issue_codes"] = ["climax_readiness_low"]
        report["recommended_action"] = "replan"
        report["checks"]["climax_readiness"] = {
            "status": "warning",
            "summary": "終盤準備が不足している",
            "evidence": ["chapter-3"],
        }
        return report


class EarlyReplanTriggerContinuityChecker(NoRerunContinuityChecker):
    def build_progress_report(self, artifacts, canon_ledger, thread_registry):
        report = super().build_progress_report(artifacts, canon_ledger, thread_registry)
        report["evaluated_through_chapter"] = 1
        report["story_state_summary"]["evaluated_through_chapter"] = 1
        report["issue_codes"] = ["escalation_pace_flat"]
        report["recommended_action"] = "replan"
        report["checks"]["escalation_pace"] = {
            "status": "warning",
            "summary": "第2章以降の役割を組み替える必要がある",
            "evidence": ["chapter-1"],
        }
        return report


class ReviseTriggerContinuityChecker(NoRerunContinuityChecker):
    def build_progress_report(self, artifacts, canon_ledger, thread_registry):
        report = super().build_progress_report(artifacts, canon_ledger, thread_registry)
        report["evaluated_through_chapter"] = 2
        report["story_state_summary"]["evaluated_through_chapter"] = 2
        report["issue_codes"] = ["emotional_progression_stall"]
        report["recommended_action"] = "revise"
        report["checks"]["emotional_progression"] = {
            "status": "warning",
            "summary": "感情変化が弱く改稿が必要である",
            "evidence": ["chapter-2"],
        }
        return report


class RerunTriggerContinuityChecker(NoRerunContinuityChecker):
    def build_progress_report(self, artifacts, canon_ledger, thread_registry):
        report = super().build_progress_report(artifacts, canon_ledger, thread_registry)
        report["evaluated_through_chapter"] = 2
        report["story_state_summary"]["evaluated_through_chapter"] = 2
        report["issue_codes"] = ["chapter_role_coverage_gap"]
        report["recommended_action"] = "rerun"
        report["checks"]["chapter_role_coverage"] = {
            "status": "warning",
            "summary": "章役割が崩れており再実行が必要である",
            "evidence": ["chapter-2"],
        }
        return report


class StopForReviewContinuityChecker(NoRerunContinuityChecker):
    def build_progress_report(self, artifacts, canon_ledger, thread_registry):
        report = super().build_progress_report(artifacts, canon_ledger, thread_registry)
        report["issue_codes"] = ["human_review_required"]
        report["recommended_action"] = "stop_for_review"
        report["checks"]["unresolved_thread_load"] = {
            "status": "warning",
            "summary": "保留案件が多く人手確認が必要である",
            "evidence": ["chapter-3"],
        }
        return report


class ReplanningMockLLMClient(MockLLMClient):
    def __init__(self) -> None:
        super().__init__()
        self.chapter_briefs_calls = 0
        self.scene_cards_calls = 0

    def generate_chapter_briefs(
        self,
        story_input,
        logline,
        characters,
        three_act_plot,
        story_bible,
        chapter_plan,
    ):
        briefs = super().generate_chapter_briefs(
            story_input,
            logline,
            characters,
            three_act_plot,
            story_bible,
            chapter_plan,
        )
        self.chapter_briefs_calls += 1
        if self.chapter_briefs_calls >= 2:
            for brief in briefs[1:]:
                brief["purpose"] = f"REPLAN {brief['purpose']}"
                brief["goal"] = f"REPLAN {brief['goal']}"
                brief["turn"] = f"REPLAN {brief['turn']}"
        return briefs

    def generate_scene_cards(
        self,
        story_input,
        logline,
        characters,
        three_act_plot,
        story_bible,
        chapter_plan,
        chapter_briefs,
    ):
        packets = super().generate_scene_cards(
            story_input,
            logline,
            characters,
            three_act_plot,
            story_bible,
            chapter_plan,
            chapter_briefs,
        )
        self.scene_cards_calls += 1
        if self.scene_cards_calls >= 2:
            for packet in packets[1:]:
                packet["scenes"][0]["scene_goal"] = f"REPLAN {packet['scenes'][0]['scene_goal']}"
                packet["scenes"][0]["exit_state"] = f"REPLAN {packet['scenes'][0]['exit_state']}"
        return packets


class StoryPipelineTest(unittest.TestCase):
    def test_pipeline_writes_all_phases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            pipeline = StoryPipeline(MockLLMClient(), output_dir, "json")

            artifacts = pipeline.run(
                StoryInput(theme="記憶", genre="SF", tone="ビター", target_length=8000)
            )

            expected_files = [
                "story_input.json",
                "01_loglines.json",
                "02_characters.json",
                "03_three_act_plot.json",
                "story_bible.json",
                "04_chapter_plan.json",
                "chapter_briefs.json",
                "scene_cards.json",
                "chapter_1_handoff_packet.json",
                "chapter_2_handoff_packet.json",
                "chapter_3_handoff_packet.json",
                "05_chapter_1_draft.json",
                "chapter_1_draft.json",
                "chapter_2_draft.json",
                "chapter_3_draft.json",
                "continuity_report.json",
                "quality_report.json",
                "revised_chapter_1_draft.json",
                "revised_chapter_2_draft.json",
                "revised_chapter_3_draft.json",
                "story_summary.json",
                "project_quality_report.json",
                "progress_report.json",
                "next_action_decision.json",
                "publish_ready_bundle.json",
                "manifest.json",
            ]
            for name in expected_files:
                self.assertTrue((output_dir / name).exists(), name)

            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            continuity_report = json.loads(
                (output_dir / "continuity_report.json").read_text(encoding="utf-8")
            )
            quality_report = json.loads((output_dir / "quality_report.json").read_text(encoding="utf-8"))
            story_bible = json.loads((output_dir / "story_bible.json").read_text(encoding="utf-8"))
            story_summary = json.loads((output_dir / "story_summary.json").read_text(encoding="utf-8"))
            project_quality_report = json.loads(
                (output_dir / "project_quality_report.json").read_text(encoding="utf-8")
            )
            progress_report = json.loads((output_dir / "progress_report.json").read_text(encoding="utf-8"))
            next_action_decision = json.loads(
                (output_dir / "next_action_decision.json").read_text(encoding="utf-8")
            )
            publish_ready_bundle = json.loads(
                (output_dir / "publish_ready_bundle.json").read_text(encoding="utf-8")
            )
            canon_ledger = load_canon_ledger(output_dir)
            try:
                thread_registry = json.loads(
                    (output_dir / "thread_registry.json").read_text(encoding="utf-8")
                )
            except FileNotFoundError:
                thread_registry = {"schema_name": "thread_registry", "schema_version": "1.0", "threads": []}
            expected_story_state_summary = {
                "evaluated_through_chapter": 4,
                "canon_chapter_count": len(canon_ledger["chapters"]),
                "thread_count": len(thread_registry["threads"]),
                "unresolved_thread_count": 2,
                "resolved_thread_count": 0,
                "open_question_count": sum(len(chapter["open_questions"]) for chapter in canon_ledger["chapters"]),
                "latest_timeline_event_count": len(canon_ledger["chapters"][-1]["timeline_events"]),
            }
            self.assertEqual(manifest["selected_logline"]["id"], "logline-1")
            self.assertEqual(
                manifest["artifact_contract"]["chapter_artifacts"]["canonical_story_state"]["chapter_drafts"]["primary_collection"],
                "chapter_drafts",
            )
            self.assertEqual(
                manifest["artifact_contract"]["chapter_artifacts"]["canonical_story_state"]["chapter_drafts"]["compatibility_field"],
                "chapter_1_draft",
            )
            self.assertEqual(
                manifest["artifact_contract"]["chapter_artifacts"]["canonical_story_state"]["continuity_history"]["compatibility_field"],
                "continuity_report",
            )
            self.assertEqual(manifest["artifact_contract"]["publish_ready_bundle"]["schema_version"], "1.0")
            self.assertEqual(manifest["artifact_contract"]["story_bible"]["schema_version"], "1.0")
            self.assertEqual(manifest["policy_snapshot"]["long_run"]["max_high_severity_chapters"], 10)
            self.assertEqual(manifest["policy_snapshot"]["long_run"]["max_total_rerun_attempts"], 20)
            self.assertEqual(artifacts.story_bible, story_bible)
            self.assertEqual(manifest["artifacts"]["story_bible"], story_bible)
            self.assertEqual(story_bible["schema_name"], "story_bible")
            self.assertIn("core_premise", story_bible)
            self.assertTrue(story_bible["character_arcs"])
            self.assertIn(story_bible["theme_statement"], artifacts.chapter_plan[0]["purpose"])
            self.assertEqual(artifacts.chapter_1_draft["chapter_number"], 1)
            self.assertIn("length_warnings", continuity_report)
            self.assertIn("overall_recommendation", quality_report)
            self.assertIn("rerun_history", manifest)
            self.assertIn("revise_history", manifest)
            self.assertIn("continuity_history", manifest)
            self.assertIn("chapter_histories", manifest)
            self.assertTrue(manifest["rerun_history"])
            self.assertTrue(manifest["revise_history"])
            self.assertEqual(len(manifest["continuity_history"]), len(artifacts.chapter_plan))
            self.assertEqual(len(manifest["chapter_histories"]), len(artifacts.chapter_plan))
            self.assertIn("severity", continuity_report)
            self.assertEqual(artifacts.quality_report, quality_report)
            self.assertEqual(manifest["artifacts"]["quality_report"], quality_report)
            self.assertEqual(artifacts.story_summary, story_summary)
            self.assertEqual(manifest["artifacts"]["story_summary"], story_summary)
            self.assertEqual(story_summary["chapter_count"], len(artifacts.chapter_plan))
            self.assertEqual(len(story_summary["chapter_summaries"]), len(artifacts.chapter_plan))
            self.assertEqual(artifacts.project_quality_report, project_quality_report)
            self.assertEqual(manifest["artifacts"]["project_quality_report"], project_quality_report)
            self.assertIn("checks", project_quality_report)
            self.assertEqual(progress_report["schema_name"], "progress_report")
            self.assertEqual(progress_report["story_state_summary"], expected_story_state_summary)
            self.assertEqual(manifest["artifacts"]["progress_report"], progress_report)
            self.assertEqual(next_action_decision["schema_name"], "next_action_decision")
            self.assertEqual(artifacts.next_action_decision, next_action_decision)
            self.assertEqual(manifest["artifacts"]["next_action_decision"], next_action_decision)
            self.assertEqual(artifacts.publish_ready_bundle, publish_ready_bundle)
            self.assertEqual(manifest["artifacts"]["publish_ready_bundle"], publish_ready_bundle)
            self.assertEqual(publish_ready_bundle["schema_version"], "1.0")
            self.assertEqual(publish_ready_bundle["bundle_type"], "publish_ready_bundle")
            self.assertEqual(publish_ready_bundle["story_summary"], story_summary)
            self.assertEqual(publish_ready_bundle["overall_quality_report"], project_quality_report)
            self.assertEqual(len(publish_ready_bundle["chapters"]), len(artifacts.chapter_plan))
            self.assertEqual(
                publish_ready_bundle["source_artifacts"]["overall_quality_report"],
                "project_quality_report.json",
            )
            self.assertIn("manuscript", publish_ready_bundle["sections"])
            self.assertEqual(
                publish_ready_bundle["summary"],
                {
                    "title": publish_ready_bundle["title"],
                    "chapter_count": len(artifacts.revised_chapter_drafts),
                    "section_names": list(publish_ready_bundle["sections"].keys()),
                    "source_artifact_names": [
                        "story_summary.json",
                        "project_quality_report.json",
                        "revised_chapter_{n}_draft.json",
                    ],
                    "story_bible_summary": build_story_bible_summary(story_bible),
                    "thread_summary": build_thread_summary(thread_registry),
                    "story_state_summary": expected_story_state_summary,
                    "handoff_summary": build_handoff_summary(publish_ready_bundle),
                },
            )
            self.assertEqual(manifest["artifacts"]["continuity_history"], manifest["continuity_history"])
            self.assertEqual(artifacts.revised_chapter_1_draft["chapter_number"], 1)
            self.assertEqual(manifest["revise_history"][0]["chapter_index"], 0)
            self.assertEqual(manifest["continuity_history"][0]["chapter_index"], 0)
            self.assertTrue(artifacts.chapter_drafts)
            self.assertTrue(artifacts.revised_chapter_drafts)
            self.assertEqual(artifacts.chapter_drafts[0], artifacts.chapter_1_draft)
            self.assertEqual(artifacts.revised_chapter_drafts[0], artifacts.revised_chapter_1_draft)
            self.assertEqual(manifest["artifacts"]["chapter_drafts"][0], manifest["artifacts"]["chapter_1_draft"])
            self.assertEqual(
                manifest["artifacts"]["revised_chapter_drafts"][0],
                manifest["artifacts"]["revised_chapter_1_draft"],
            )
            self.assertEqual(len(artifacts.chapter_drafts), len(artifacts.chapter_plan))
            self.assertEqual(
                [draft["chapter_number"] for draft in artifacts.chapter_drafts],
                [chapter["chapter_number"] for chapter in artifacts.chapter_plan],
            )
            compatibility_draft = json.loads(
                (output_dir / "05_chapter_1_draft.json").read_text(encoding="utf-8")
            )
            chapter_2_draft = json.loads((output_dir / "chapter_2_draft.json").read_text(encoding="utf-8"))
            chapter_3_draft = json.loads((output_dir / "chapter_3_draft.json").read_text(encoding="utf-8"))
            self.assertEqual(compatibility_draft, artifacts.chapter_drafts[0])
            self.assertEqual(chapter_2_draft, artifacts.chapter_drafts[1])
            self.assertEqual(chapter_3_draft, artifacts.chapter_drafts[2])
            self.assertEqual(len(artifacts.revised_chapter_drafts), len(artifacts.chapter_drafts))
            self.assertEqual(
                [draft["chapter_number"] for draft in artifacts.revised_chapter_drafts],
                [chapter["chapter_number"] for chapter in artifacts.chapter_plan],
            )
            revised_chapter_2_draft = json.loads(
                (output_dir / "revised_chapter_2_draft.json").read_text(encoding="utf-8")
            )
            revised_chapter_3_draft = json.loads(
                (output_dir / "revised_chapter_3_draft.json").read_text(encoding="utf-8")
            )
            self.assertEqual(revised_chapter_2_draft, artifacts.revised_chapter_drafts[1])
            self.assertEqual(revised_chapter_3_draft, artifacts.revised_chapter_drafts[2])
            self.assertGreaterEqual(len(manifest["revise_history"]), len(artifacts.chapter_plan))
            self.assertEqual(manifest["revise_history"][0]["target"], "revised_chapter_1_draft")
            self.assertEqual(
                manifest["revise_history"][-1]["target"],
                f"revised_chapter_drafts[{len(artifacts.chapter_plan) - 1}]",
            )
            self.assertIn("diff", manifest["revise_history"][0])
            self.assertTrue(manifest["revise_history"][0]["diff"]["changed"])
            self.assertIn("text", manifest["revise_history"][0]["diff"]["changed_fields"])
            self.assertIn("summary_before", manifest["revise_history"][0]["diff"])
            self.assertIn("summary_after", manifest["revise_history"][0]["diff"])
            self.assertTrue(manifest["revise_history"][0]["diff"]["text_diff"])
            no_change_entries = [
                entry for entry in manifest["revise_history"] if entry["stop_reason"] == "no_changes_detected"
            ]
            self.assertTrue(all(not entry["diff"]["changed"] for entry in no_change_entries))
            self.assertEqual(
                sorted(set(entry["chapter_index"] for entry in manifest["revise_history"])),
                list(range(len(artifacts.chapter_plan))),
            )
            self.assertTrue(any(entry["stop_reason"] for entry in manifest["revise_history"]))
            self.assertEqual(
                [entry["chapter_index"] for entry in manifest["continuity_history"]],
                list(range(len(artifacts.chapter_plan))),
            )
            self.assertEqual(
                [entry["chapter_index"] for entry in manifest["chapter_histories"]],
                list(range(len(artifacts.chapter_plan))),
            )
            self.assertTrue(all(history["continuity"] for history in manifest["chapter_histories"]))
            self.assertTrue(all(isinstance(history["reruns"], list) for history in manifest["chapter_histories"]))
            self.assertTrue(all(isinstance(history["revisions"], list) for history in manifest["chapter_histories"]))
            self.assertEqual(
                [draft["chapter_number"] for draft in manifest["artifacts"]["chapter_drafts"]],
                [chapter["chapter_number"] for chapter in manifest["artifacts"]["chapter_plan"]],
            )
            self.assertEqual(
                [draft["chapter_number"] for draft in manifest["artifacts"]["revised_chapter_drafts"]],
                [chapter["chapter_number"] for chapter in manifest["artifacts"]["chapter_plan"]],
            )
            self.assertEqual(
                manifest["summary"]["counts"]["chapters"],
                len(manifest["artifacts"]["chapter_drafts"]),
            )
            self.assertEqual(
                manifest["summary"]["counts"]["chapters"],
                len(manifest["artifacts"]["revised_chapter_drafts"]),
            )
            self.assertEqual(manifest["current_step"], PIPELINE_STEP_ORDER[-1])
            self.assertEqual(manifest["completed_steps"], PIPELINE_STEP_ORDER)
            self.assertEqual(
                [checkpoint["step"] for checkpoint in manifest["checkpoints"]],
                PIPELINE_STEP_ORDER,
            )
            self.assertTrue(all(checkpoint["status"] == "completed" for checkpoint in manifest["checkpoints"]))
            self.assertEqual(
                manifest["checkpoints"][-1]["completed_steps"],
                PIPELINE_STEP_ORDER,
            )
            self.assertFalse(manifest["long_run_status"]["should_stop"])

    def test_pipeline_keeps_documented_story_flow_order(self) -> None:
        expected_step_order = [
            "story_input",
            "loglines",
            "characters",
            "three_act_plot",
            "story_bible",
            "chapter_plan",
            "chapter_briefs",
            "scene_cards",
            "chapter_drafts",
            "continuity_report",
            "quality_report",
            "revised_chapter_drafts",
            "story_summary",
            "project_quality_report",
            "progress_report",
            "publish_ready_bundle",
        ]

        self.assertEqual(PIPELINE_STEP_ORDER, expected_step_order)

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            artifacts = StoryPipeline(MockLLMClient(), output_dir, "json").run(
                StoryInput(theme="記憶", genre="SF", tone="ビター", target_length=120000)
            )
            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))

            self.assertTrue((output_dir / "chapter_briefs.json").exists())
            self.assertTrue((output_dir / "scene_cards.json").exists())
            self.assertEqual(manifest["completed_steps"], expected_step_order)
            self.assertEqual([checkpoint["step"] for checkpoint in manifest["checkpoints"]], expected_step_order)
            self.assertEqual(len(artifacts.chapter_briefs), len(artifacts.chapter_plan))
            self.assertEqual(len(artifacts.scene_cards), len(artifacts.chapter_plan))

    def test_pipeline_builds_chapter_handoff_packets_before_drafts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)

            artifacts = StoryPipeline(
                MockLLMClient(),
                output_dir,
                "json",
                continuity_checker=StopBeforeRevisionContinuityChecker(),
                rerun_policy=ContinuityRerunPolicy(
                    {
                        **ContinuityRerunPolicy().config,
                        "long_run": {
                            "max_high_severity_chapters": 1,
                            "max_total_rerun_attempts": 99,
                        },
                    }
                ),
            ).run(
                StoryInput(theme="記憶", genre="SF", tone="ビター", target_length=8000)
            )

            chapter_1_packet = json.loads((output_dir / "chapter_1_handoff_packet.json").read_text(encoding="utf-8"))
            chapter_2_packet = json.loads((output_dir / "chapter_2_handoff_packet.json").read_text(encoding="utf-8"))

            self.assertEqual(chapter_1_packet["schema_name"], "chapter_handoff_packet")
            self.assertEqual(chapter_1_packet["chapter_number"], 1)
            self.assertEqual(chapter_1_packet["current_chapter_brief"], artifacts.chapter_briefs[0])
            self.assertEqual(chapter_1_packet["relevant_scene_cards"], artifacts.scene_cards[0]["scenes"])
            self.assertEqual(chapter_1_packet["previous_chapter_summary"], "")
            self.assertEqual(chapter_1_packet["style_constraints"]["tone"], "ビター")
            self.assertEqual(
                chapter_1_packet["style_constraints"]["point_of_view"],
                artifacts.chapter_plan[0]["point_of_view"],
            )
            self.assertEqual(chapter_1_packet["style_constraints"]["tense"], "past")

            self.assertEqual(chapter_2_packet["chapter_number"], 2)
            self.assertEqual(
                chapter_2_packet["previous_chapter_summary"],
                artifacts.chapter_drafts[0]["summary"],
            )
            self.assertEqual(
                [entry["thread_id"] for entry in chapter_2_packet["unresolved_thread_entries"]],
                chapter_2_packet["unresolved_threads"],
            )
            self.assertTrue(chapter_2_packet["unresolved_thread_entries"])
            self.assertTrue(
                all(
                    entry["status"] not in {"resolved", "dropped"}
                    for entry in chapter_2_packet["unresolved_thread_entries"]
                )
            )

    def test_pipeline_resume_fails_fast_when_scene_cards_missing_before_chapter_drafts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            pipeline = StoryPipeline(MockLLMClient(), output_dir, "json")
            pipeline.run(StoryInput(theme="秘密", genre="ミステリ", tone="静謐", target_length=120000))
            (output_dir / "scene_cards.json").unlink()

            with self.assertRaisesRegex(
                ValueError,
                "scene_cards is required before chapter_drafts",
            ):
                StoryPipeline(MockLLMClient(), output_dir, "json").run(
                    resume_from=output_dir,
                    rerun_from="chapter_drafts",
                )

    def test_pipeline_passes_three_act_plot_and_planning_context_to_chapter_drafts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            client = RecordingDraftContextLLMClient()

            artifacts = StoryPipeline(
                client,
                output_dir,
                "json",
                continuity_checker=NoRerunContinuityChecker(),
            ).run(
                StoryInput(theme="記憶", genre="SF", tone="ビター", target_length=8000)
            )

            self.assertEqual(len(client.draft_calls), len(artifacts.chapter_plan))
            for chapter_index, call in enumerate(client.draft_calls):
                self.assertEqual(call["three_act_plot"], artifacts.three_act_plot)
                self.assertEqual(
                    call["chapter_handoff_packet"]["chapter_number"],
                    chapter_index + 1,
                )
                self.assertEqual(call["chapter_plan"], artifacts.chapter_plan)
                self.assertEqual(call["chapter_briefs"], artifacts.chapter_briefs)
                self.assertEqual(call["scene_cards"], artifacts.scene_cards)
                self.assertEqual(
                    call["canon_ledger"],
                    {"schema_name": "canon_ledger", "schema_version": "1.0", "chapters": []},
                )
                self.assertEqual(
                    call["thread_registry"],
                    {"schema_name": "thread_registry", "schema_version": "1.0", "threads": []},
                )
                self.assertEqual(call["chapter_index"], chapter_index)

    def test_pipeline_passes_saved_memory_artifacts_to_chapter_drafts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            client = RecordingDraftContextLLMClient()
            save_canon_ledger(
                output_dir,
                {
                    "schema_name": "canon_ledger",
                    "schema_version": "1.0",
                    "chapters": [
                        {
                            "chapter_number": 1,
                            "new_facts": ["主人公は腕時計の逆回転を見た。"],
                            "changed_facts": [],
                            "open_questions": ["なぜ時計が逆回転したのか。"],
                            "timeline_events": ["駅前で異変が起きた。"],
                        }
                    ],
                },
            )
            save_thread_registry(
                output_dir,
                {
                    "schema_name": "thread_registry",
                    "schema_version": "1.0",
                    "threads": [
                        {
                            "thread_id": "watch-mystery",
                            "label": "壊れた腕時計の謎",
                            "status": "seeded",
                            "introduced_in_chapter": 1,
                            "last_updated_in_chapter": 1,
                            "related_characters": ["篠崎 遥"],
                            "notes": ["駅前で逆回転が初登場した。"],
                        }
                    ],
                },
            )

            StoryPipeline(
                client,
                output_dir,
                "json",
                continuity_checker=NoRerunContinuityChecker(),
            ).run(
                StoryInput(theme="記憶", genre="SF", tone="ビター", target_length=8000)
            )

            self.assertTrue(client.draft_calls)
            for call in client.draft_calls:
                self.assertEqual(call["canon_ledger"]["chapters"][0]["chapter_number"], 1)
                self.assertEqual(call["thread_registry"]["threads"][0]["thread_id"], "watch-mystery")

    def test_pipeline_passes_chapter_handoff_packet_to_revision_loop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            client = RecordingDraftContextLLMClient()

            artifacts = StoryPipeline(
                client,
                output_dir,
                "json",
                continuity_checker=NoRerunContinuityChecker(),
            ).run(
                StoryInput(theme="記憶", genre="SF", tone="ビター", target_length=8000)
            )

            self.assertEqual(len(client.revise_calls), len(artifacts.chapter_plan))
            for chapter_index, call in enumerate(client.revise_calls):
                self.assertEqual(call["chapter_plan"], artifacts.chapter_plan)
                self.assertEqual(call["chapter_index"], chapter_index)
                self.assertEqual(
                    call["chapter_handoff_packet"]["chapter_number"],
                    chapter_index + 1,
                )
                self.assertEqual(
                    call["chapter_handoff_packet"]["current_chapter_brief"],
                    artifacts.chapter_briefs[chapter_index],
                )

    def test_pipeline_updates_memory_artifacts_after_chapter_drafts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)

            artifacts = StoryPipeline(
                MockLLMClient(),
                output_dir,
                "json",
                continuity_checker=StopBeforeRevisionContinuityChecker(),
                rerun_policy=ContinuityRerunPolicy(
                    {
                        **ContinuityRerunPolicy().config,
                        "long_run": {
                            "max_high_severity_chapters": 1,
                            "max_total_rerun_attempts": 99,
                        },
                    }
                ),
            ).run(
                StoryInput(theme="記憶", genre="SF", tone="ビター", target_length=8000)
            )

            canon_ledger = json.loads((output_dir / "canon_ledger.json").read_text(encoding="utf-8"))
            thread_registry = json.loads((output_dir / "thread_registry.json").read_text(encoding="utf-8"))

            self.assertEqual(canon_ledger["schema_name"], "canon_ledger")
            self.assertEqual(len(canon_ledger["chapters"]), len(artifacts.chapter_plan))
            self.assertEqual(canon_ledger["chapters"][0]["chapter_number"], 1)
            self.assertEqual(canon_ledger["chapters"][0]["new_facts"], [artifacts.chapter_drafts[0]["summary"]])
            self.assertEqual(
                canon_ledger["chapters"][0]["timeline_events"],
                [artifacts.scene_cards[0]["scenes"][0]["exit_state"]],
            )
            self.assertFalse(artifacts.revised_chapter_drafts)

            self.assertEqual(thread_registry["schema_name"], "thread_registry")
            self.assertTrue(thread_registry["threads"])
            self.assertEqual(
                thread_registry["threads"][0]["thread_id"],
                artifacts.chapter_briefs[0]["foreshadowing_targets"][0],
            )
            self.assertEqual(thread_registry["threads"][0]["status"], "seeded")
            self.assertEqual(thread_registry["threads"][0]["introduced_in_chapter"], 1)

    def test_pipeline_updates_memory_artifacts_after_revised_chapter_drafts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)

            artifacts = StoryPipeline(
                MockLLMClient(),
                output_dir,
                "json",
                continuity_checker=NoRerunContinuityChecker(),
            ).run(
                StoryInput(theme="記憶", genre="SF", tone="ビター", target_length=8000)
            )

            canon_ledger = json.loads((output_dir / "canon_ledger.json").read_text(encoding="utf-8"))
            thread_registry = json.loads((output_dir / "thread_registry.json").read_text(encoding="utf-8"))

            self.assertEqual(
                canon_ledger["chapters"][0]["new_facts"],
                [artifacts.revised_chapter_drafts[0]["summary"]],
            )
            self.assertEqual(
                thread_registry["threads"][0]["notes"],
                [artifacts.revised_chapter_drafts[-1]["summary"]],
            )
            self.assertEqual(thread_registry["threads"][0]["introduced_in_chapter"], 1)
            self.assertEqual(
                thread_registry["threads"][0]["last_updated_in_chapter"],
                len(artifacts.chapter_plan),
            )

    def test_pipeline_records_replan_history_when_progress_report_recommends_replan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)

            artifacts = StoryPipeline(
                MockLLMClient(),
                output_dir,
                "json",
                continuity_checker=ReplanTriggerContinuityChecker(),
            ).run(
                StoryInput(theme="記憶", genre="SF", tone="ビター", target_length=8000)
            )

            replan_history = load_replan_history(output_dir)
            next_action_decision = load_next_action_decision(output_dir)

            self.assertEqual(replan_history["schema_name"], "replan_history")
            self.assertEqual(len(replan_history["replans"]), 1)
            self.assertEqual(
                replan_history["replans"][0]["trigger_chapter_number"],
                len(artifacts.chapter_plan),
            )
            self.assertEqual(
                replan_history["replans"][0]["updated_artifacts"],
                ["chapter_briefs", "scene_cards"],
            )
            self.assertEqual(next_action_decision["action"], "stop_for_review")
            self.assertEqual(next_action_decision["target_chapters"], [])
            self.assertEqual(
                next_action_decision["reason"],
                "progress_report recommended replan but no future chapters remain",
            )

    def test_pipeline_applies_replan_updates_to_future_planning_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)

            artifacts = StoryPipeline(
                ReplanningMockLLMClient(),
                output_dir,
                "json",
                continuity_checker=EarlyReplanTriggerContinuityChecker(),
            ).run(
                StoryInput(theme="記憶", genre="SF", tone="ビター", target_length=8000)
            )

            replan_history = load_replan_history(output_dir)
            chapter_briefs = load_chapter_briefs(output_dir)
            scene_cards = load_scene_cards(output_dir)

            self.assertEqual(replan_history["replans"][0]["trigger_chapter_number"], 1)
            self.assertEqual(
                replan_history["replans"][0]["impact_scope"]["chapter_numbers"],
                list(range(2, len(artifacts.chapter_plan) + 1)),
            )
            self.assertIn(
                "chapter_briefs updated for chapters: 2, 3, 4",
                replan_history["replans"][0]["change_summary"],
            )
            self.assertIn(
                "scene_cards updated for chapters: 2, 3, 4",
                replan_history["replans"][0]["change_summary"],
            )
            self.assertEqual(chapter_briefs[0]["purpose"], artifacts.chapter_plan[0]["purpose"])
            self.assertTrue(chapter_briefs[1]["purpose"].startswith("REPLAN "))
            self.assertTrue(chapter_briefs[2]["purpose"].startswith("REPLAN "))
            self.assertFalse(scene_cards[0]["scenes"][0]["scene_goal"].startswith("REPLAN "))
            self.assertTrue(scene_cards[1]["scenes"][0]["scene_goal"].startswith("REPLAN "))
            self.assertTrue(scene_cards[2]["scenes"][0]["exit_state"].startswith("REPLAN "))

    def test_pipeline_saves_next_action_decision_after_progress_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)

            artifacts = StoryPipeline(
                MockLLMClient(),
                output_dir,
                "json",
                continuity_checker=NoRerunContinuityChecker(),
            ).run(
                StoryInput(theme="記憶", genre="SF", tone="ビター", target_length=8000)
            )

            next_action_decision = load_next_action_decision(output_dir)

            self.assertTrue((output_dir / "next_action_decision.json").exists())
            self.assertEqual(next_action_decision["evaluated_through_chapter"], len(artifacts.chapter_plan))
            self.assertEqual(next_action_decision["action"], "continue")
            self.assertEqual(next_action_decision["reason"], "progress_report recommended continue")
            self.assertEqual(next_action_decision["issue_codes"], [])
            self.assertEqual(next_action_decision["target_chapters"], [])
            self.assertEqual(next_action_decision["policy_budget"]["max_high_severity_chapters"], 10)
            self.assertEqual(next_action_decision["policy_budget"]["max_total_rerun_attempts"], 20)
            self.assertEqual(next_action_decision["decision_trace"][0]["code"], "chapter_role_coverage")
            self.assertEqual(next_action_decision["decision_trace"][0]["summary"], "ok")
            self.assertEqual(next_action_decision["decision_trace"][0]["value"], "ok")

    def test_pipeline_maps_replan_recommended_action_to_replan_future_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)

            artifacts = StoryPipeline(
                MockLLMClient(),
                output_dir,
                "json",
                continuity_checker=EarlyReplanTriggerContinuityChecker(),
            ).run(
                StoryInput(theme="記憶", genre="SF", tone="ビター", target_length=8000)
            )

            next_action_decision = load_next_action_decision(output_dir)

            self.assertEqual(next_action_decision["action"], "replan_future")
            self.assertEqual(next_action_decision["issue_codes"], ["escalation_pace_flat"])
            self.assertEqual(
                next_action_decision["target_chapters"],
                list(range(2, len(artifacts.chapter_plan) + 1)),
            )
            self.assertEqual(
                next_action_decision["reason"],
                "progress_report recommended replan",
            )
            self.assertIn(
                {
                    "code": "escalation_pace",
                    "summary": "第2章以降の役割を組み替える必要がある",
                    "value": "warning",
                },
                next_action_decision["decision_trace"],
            )

    def test_pipeline_maps_revise_recommended_action_to_revise_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)

            StoryPipeline(
                MockLLMClient(),
                output_dir,
                "json",
                continuity_checker=ReviseTriggerContinuityChecker(),
            ).run(
                StoryInput(theme="記憶", genre="SF", tone="ビター", target_length=8000)
            )

            next_action_decision = load_next_action_decision(output_dir)

            self.assertEqual(next_action_decision["action"], "revise")
            self.assertEqual(next_action_decision["target_chapters"], [2])
            self.assertEqual(next_action_decision["issue_codes"], ["emotional_progression_stall"])

    def test_pipeline_maps_rerun_recommended_action_to_rerun_chapter_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)

            StoryPipeline(
                MockLLMClient(),
                output_dir,
                "json",
                continuity_checker=RerunTriggerContinuityChecker(),
            ).run(
                StoryInput(theme="記憶", genre="SF", tone="ビター", target_length=8000)
            )

            next_action_decision = load_next_action_decision(output_dir)

            self.assertEqual(next_action_decision["action"], "rerun_chapter")
            self.assertEqual(next_action_decision["target_chapters"], [2])
            self.assertEqual(next_action_decision["issue_codes"], ["chapter_role_coverage_gap"])

    def test_pipeline_maps_stop_for_review_recommended_action_to_same_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)

            StoryPipeline(
                MockLLMClient(),
                output_dir,
                "json",
                continuity_checker=StopForReviewContinuityChecker(),
            ).run(
                StoryInput(theme="記憶", genre="SF", tone="ビター", target_length=8000)
            )

            next_action_decision = load_next_action_decision(output_dir)

            self.assertEqual(next_action_decision["action"], "stop_for_review")
            self.assertEqual(next_action_decision["target_chapters"], [])
            self.assertEqual(next_action_decision["issue_codes"], ["human_review_required"])

    def test_rerun_chapter_updates_memory_artifacts_for_target_chapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            pipeline = StoryPipeline(
                MockLLMClient(),
                output_dir,
                "json",
                continuity_checker=NoRerunContinuityChecker(),
            )
            pipeline.run(StoryInput(theme="記憶", genre="SF", tone="ビター", target_length=8000))

            save_canon_ledger(
                output_dir,
                {
                    "schema_name": "canon_ledger",
                    "schema_version": "1.0",
                    "chapters": [
                        {
                            "chapter_number": 1,
                            "new_facts": ["古い要約 1"],
                            "changed_facts": [],
                            "open_questions": ["seed-1"],
                            "timeline_events": ["古いイベント 1"],
                        },
                        {
                            "chapter_number": 2,
                            "new_facts": ["古い要約 2"],
                            "changed_facts": [],
                            "open_questions": ["seed-1"],
                            "timeline_events": ["古いイベント 2"],
                        },
                        {
                            "chapter_number": 3,
                            "new_facts": ["古い要約 3"],
                            "changed_facts": [],
                            "open_questions": ["seed-1"],
                            "timeline_events": ["古いイベント 3"],
                        },
                    ],
                },
            )
            save_thread_registry(
                output_dir,
                {
                    "schema_name": "thread_registry",
                    "schema_version": "1.0",
                    "threads": [
                        {
                            "thread_id": "seed-1",
                            "label": "seed-1",
                            "status": "seeded",
                            "introduced_in_chapter": 1,
                            "last_updated_in_chapter": 3,
                            "related_characters": ["篠崎 遥"],
                            "notes": ["古い thread note"],
                        }
                    ],
                },
            )

            rerun_artifacts = pipeline.rerun_chapter(output_dir, 2)
            canon_ledger = json.loads((output_dir / "canon_ledger.json").read_text(encoding="utf-8"))
            thread_registry = json.loads((output_dir / "thread_registry.json").read_text(encoding="utf-8"))
            progress_report = json.loads((output_dir / "progress_report.json").read_text(encoding="utf-8"))
            expected_story_state_summary = build_story_state_summary(
                canon_ledger,
                thread_registry,
                progress_report["evaluated_through_chapter"],
            )

            self.assertEqual(
                canon_ledger["chapters"][1]["new_facts"],
                [rerun_artifacts.revised_chapter_drafts[1]["summary"]],
            )
            self.assertEqual(
                thread_registry["threads"][0]["notes"],
                [rerun_artifacts.revised_chapter_drafts[1]["summary"]],
            )
            self.assertEqual(thread_registry["threads"][0]["introduced_in_chapter"], 1)
            self.assertEqual(thread_registry["threads"][0]["last_updated_in_chapter"], 2)

            publish_ready_bundle = load_publish_ready_bundle(output_dir)
            self.assertEqual(publish_ready_bundle["schema_version"], "1.0")
            self.assertEqual(publish_ready_bundle["bundle_type"], "publish_ready_bundle")
            self.assertEqual(
                publish_ready_bundle["summary"],
                build_publish_ready_bundle_summary(publish_ready_bundle),
            )
            self.assertEqual(progress_report["story_state_summary"], expected_story_state_summary)
            self.assertEqual(
                publish_ready_bundle["summary"]["story_state_summary"],
                expected_story_state_summary,
            )
            self.assertIn("story_summary", publish_ready_bundle["sections"])
            self.assertIn("source_artifacts", publish_ready_bundle)

    def test_resume_normalizes_compatibility_only_manifest_to_chapter_arrays(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            pipeline = StoryPipeline(MockLLMClient(), output_dir, "json")
            pipeline.run(StoryInput(theme="秘密", genre="ミステリ", tone="静謐", target_length=6000))

            manifest_path = output_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["artifacts"].pop("chapter_drafts", None)
            manifest["artifacts"].pop("revised_chapter_drafts", None)
            manifest["artifacts"]["continuity_history"] = []
            manifest["artifacts"]["quality_report"] = {}
            manifest["artifacts"]["story_summary"] = {}
            manifest["artifacts"]["project_quality_report"] = {}
            manifest["artifacts"]["publish_ready_bundle"] = {}
            manifest["continuity_history"] = []
            manifest["rerun_history"] = []
            manifest["revise_history"] = []
            manifest["chapter_histories"] = []
            manifest["current_step"] = "chapter_drafts"
            manifest["completed_steps"] = PIPELINE_STEP_ORDER[:9]
            manifest["checkpoints"] = [
                {
                    "step": step_name,
                    "status": "completed",
                    "completed_steps": PIPELINE_STEP_ORDER[: index + 1],
                }
                for index, step_name in enumerate(PIPELINE_STEP_ORDER[:9])
            ]
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

            resumed = StoryPipeline(MockLLMClient(), output_dir, "json").run(resume_from=output_dir)
            resumed_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertTrue(resumed.chapter_drafts)
            self.assertEqual(resumed.chapter_drafts[0], resumed.chapter_1_draft)
            self.assertTrue(resumed.revised_chapter_drafts)
            self.assertEqual(resumed.revised_chapter_drafts[0], resumed.revised_chapter_1_draft)
            self.assertEqual(
                resumed_manifest["artifacts"]["chapter_drafts"][0],
                resumed_manifest["artifacts"]["chapter_1_draft"],
            )
            self.assertEqual(
                resumed_manifest["artifacts"]["revised_chapter_drafts"][0],
                resumed_manifest["artifacts"]["revised_chapter_1_draft"],
            )
            self.assertEqual(
                resumed_manifest["artifacts"]["continuity_history"][0],
                resumed_manifest["artifacts"]["continuity_report"],
            )
            self.assertEqual(resumed_manifest["current_step"], PIPELINE_STEP_ORDER[-1])



if __name__ == "__main__":
    unittest.main()
