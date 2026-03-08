import tempfile
import unittest
from pathlib import Path

from novel_writer.cli import main


class CliTest(unittest.TestCase):
    def test_cli_main_runs_with_mock_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            exit_code = main(
                [
                    "--theme",
                    "罪と赦し",
                    "--genre",
                    "ヒューマンドラマ",
                    "--tone",
                    "切実",
                    "--target-length",
                    "5000",
                    "--output-dir",
                    tmp_dir,
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue((Path(tmp_dir) / "05_chapter_1_draft.json").exists())
            self.assertTrue((Path(tmp_dir) / "revised_chapter_1_draft.json").exists())

    def test_cli_main_can_resume_from_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            first_exit_code = main(
                [
                    "--theme",
                    "秘密",
                    "--genre",
                    "ミステリ",
                    "--tone",
                    "静謐",
                    "--target-length",
                    "5000",
                    "--output-dir",
                    tmp_dir,
                ]
            )
            second_exit_code = main(
                [
                    "--resume-from-output-dir",
                    tmp_dir,
                ]
            )

            self.assertEqual(first_exit_code, 0)
            self.assertEqual(second_exit_code, 0)
            self.assertTrue((Path(tmp_dir) / "manifest.json").exists())

    def test_cli_main_can_rerun_from_named_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            first_exit_code = main(
                [
                    "--theme",
                    "約束",
                    "--genre",
                    "青春ドラマ",
                    "--tone",
                    "軽やか",
                    "--target-length",
                    "5000",
                    "--output-dir",
                    tmp_dir,
                ]
            )
            second_exit_code = main(
                [
                    "--resume-from-output-dir",
                    tmp_dir,
                    "--rerun-from",
                    "chapter_drafts",
                ]
            )

            self.assertEqual(first_exit_code, 0)
            self.assertEqual(second_exit_code, 0)
            self.assertTrue((Path(tmp_dir) / "05_chapter_1_draft.json").exists())


if __name__ == "__main__":
    unittest.main()
