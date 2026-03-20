import json
import tempfile
import unittest
from pathlib import Path

from novel_writer.llm_client import MockLLMClient
from novel_writer.pipeline import PIPELINE_STEP_ORDER, StoryPipeline
from novel_writer.schema import StoryInput


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
            publish_ready_bundle = json.loads(
                (output_dir / "publish_ready_bundle.json").read_text(encoding="utf-8")
            )
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
            manifest["completed_steps"] = PIPELINE_STEP_ORDER[:7]
            manifest["checkpoints"] = [
                {
                    "step": step_name,
                    "status": "completed",
                    "completed_steps": PIPELINE_STEP_ORDER[: index + 1],
                }
                for index, step_name in enumerate(PIPELINE_STEP_ORDER[:7])
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
