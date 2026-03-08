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
                "04_chapter_plan.json",
                "05_chapter_1_draft.json",
                "continuity_report.json",
                "quality_report.json",
                "revised_chapter_1_draft.json",
                "manifest.json",
            ]
            for name in expected_files:
                self.assertTrue((output_dir / name).exists(), name)

            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            continuity_report = json.loads(
                (output_dir / "continuity_report.json").read_text(encoding="utf-8")
            )
            quality_report = json.loads((output_dir / "quality_report.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["selected_logline"]["id"], "logline-1")
            self.assertEqual(artifacts.chapter_1_draft["chapter_number"], 1)
            self.assertIn("length_warnings", continuity_report)
            self.assertIn("overall_recommendation", quality_report)
            self.assertIn("rerun_history", manifest)
            self.assertIn("revise_history", manifest)
            self.assertTrue(manifest["rerun_history"])
            self.assertTrue(manifest["revise_history"])
            self.assertIn("severity", continuity_report)
            self.assertEqual(artifacts.quality_report, quality_report)
            self.assertEqual(manifest["artifacts"]["quality_report"], quality_report)
            self.assertEqual(artifacts.revised_chapter_1_draft["chapter_number"], 1)
            self.assertEqual(manifest["revise_history"][0]["chapter_index"], 0)
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
            self.assertEqual(compatibility_draft, artifacts.chapter_drafts[0])
            self.assertEqual(len(artifacts.revised_chapter_drafts), len(artifacts.chapter_drafts))
            self.assertEqual(
                [draft["chapter_number"] for draft in artifacts.revised_chapter_drafts],
                [chapter["chapter_number"] for chapter in artifacts.chapter_plan],
            )
            self.assertEqual(len(manifest["revise_history"]), len(artifacts.chapter_plan))
            self.assertEqual(manifest["revise_history"][0]["target"], "revised_chapter_1_draft")
            self.assertEqual(
                manifest["revise_history"][-1]["target"],
                f"revised_chapter_drafts[{len(artifacts.chapter_plan) - 1}]",
            )
            self.assertEqual(
                [entry["chapter_index"] for entry in manifest["revise_history"]],
                list(range(len(artifacts.chapter_plan))),
            )
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



if __name__ == "__main__":
    unittest.main()
