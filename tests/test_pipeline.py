import json
import tempfile
import unittest
from pathlib import Path

from novel_writer.llm_client import MockLLMClient
from novel_writer.pipeline import StoryPipeline
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
                "manifest.json",
            ]
            for name in expected_files:
                self.assertTrue((output_dir / name).exists(), name)

            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            continuity_report = json.loads(
                (output_dir / "continuity_report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["selected_logline"]["id"], "logline-1")
            self.assertEqual(artifacts.chapter_1_draft["chapter_number"], 1)
            self.assertIn("length_warnings", continuity_report)


if __name__ == "__main__":
    unittest.main()
