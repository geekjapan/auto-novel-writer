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


if __name__ == "__main__":
    unittest.main()

