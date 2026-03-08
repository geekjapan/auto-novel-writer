import json
import tempfile
import unittest
from pathlib import Path

from novel_writer.storage import save_artifact


class SaveArtifactTest(unittest.TestCase):
    def test_save_artifact_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = save_artifact(Path(tmp_dir), "sample", {"value": 1}, "json")

            self.assertTrue(target.exists())
            self.assertEqual(target.name, "sample.json")
            self.assertIn('"value": 1', target.read_text(encoding="utf-8"))

    def test_save_artifact_preserves_multi_chapter_manifest_payload(self) -> None:
        payload = {
            "summary": {"counts": {"chapters": 3}},
            "artifacts": {
                "chapter_plan": [
                    {"chapter_number": 1, "title": "第1章 導入"},
                    {"chapter_number": 2, "title": "第2章 転機"},
                    {"chapter_number": 3, "title": "第3章 対立"},
                ],
                "chapter_drafts": [
                    {"chapter_number": 1, "title": "第1章 導入"},
                    {"chapter_number": 2, "title": "第2章 転機"},
                    {"chapter_number": 3, "title": "第3章 対立"},
                ],
                "revised_chapter_drafts": [
                    {"chapter_number": 1, "title": "第1章 導入"},
                    {"chapter_number": 2, "title": "第2章 転機"},
                    {"chapter_number": 3, "title": "第3章 対立"},
                ],
                "chapter_1_draft": {"chapter_number": 1, "title": "第1章 導入"},
                "revised_chapter_1_draft": {"chapter_number": 1, "title": "第1章 導入"},
            },
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            target = save_artifact(Path(tmp_dir), "manifest", payload, "json")
            saved = json.loads(target.read_text(encoding="utf-8"))

            self.assertEqual(saved["summary"]["counts"]["chapters"], 3)
            self.assertEqual(len(saved["artifacts"]["chapter_drafts"]), 3)
            self.assertEqual(len(saved["artifacts"]["revised_chapter_drafts"]), 3)
            self.assertEqual(saved["artifacts"]["chapter_drafts"][0], saved["artifacts"]["chapter_1_draft"])
            self.assertEqual(
                saved["artifacts"]["revised_chapter_drafts"][0],
                saved["artifacts"]["revised_chapter_1_draft"],
            )


if __name__ == "__main__":
    unittest.main()
