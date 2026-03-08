import tempfile
import unittest
from pathlib import Path

from novel_writer.cli import main
from novel_writer.storage import load_artifact


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

    def test_cli_main_can_use_project_scoped_run_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            exit_code = main(
                [
                    "--theme",
                    "境界",
                    "--genre",
                    "SF",
                    "--tone",
                    "ビター",
                    "--target-length",
                    "5000",
                    "--project-id",
                    "My Story 01",
                    "--projects-dir",
                    tmp_dir,
                ]
            )

            project_dir = Path(tmp_dir) / "my-story-01"
            run_dir = project_dir / "runs" / "latest_run"
            project_manifest = load_artifact(project_dir, "project_manifest")

            self.assertEqual(exit_code, 0)
            self.assertTrue((run_dir / "manifest.json").exists())
            self.assertTrue((run_dir / "revised_chapter_1_draft.json").exists())
            self.assertEqual(project_manifest["project_slug"], "my-story-01")
            self.assertEqual(project_manifest["current_run"]["output_dir"], str(run_dir))
            self.assertEqual(project_manifest["current_run"]["name"], "latest_run")

    def test_cli_create_and_resume_project_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            create_exit_code = main(
                [
                    "create-project",
                    "--theme",
                    "遺書",
                    "--genre",
                    "ミステリ",
                    "--tone",
                    "静謐",
                    "--target-length",
                    "5000",
                    "--project-id",
                    "Case 01",
                    "--projects-dir",
                    tmp_dir,
                ]
            )
            resume_exit_code = main(
                [
                    "resume-project",
                    "--project-id",
                    "Case 01",
                    "--projects-dir",
                    tmp_dir,
                ]
            )

            run_dir = Path(tmp_dir) / "case-01" / "runs" / "latest_run"
            self.assertEqual(create_exit_code, 0)
            self.assertEqual(resume_exit_code, 0)
            self.assertTrue((run_dir / "manifest.json").exists())

    def test_cli_rerun_chapter_command_supports_chapter_1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            main(
                [
                    "create-project",
                    "--theme",
                    "境界",
                    "--genre",
                    "SF",
                    "--tone",
                    "ビター",
                    "--target-length",
                    "5000",
                    "--project-id",
                    "My Story 01",
                    "--projects-dir",
                    tmp_dir,
                ]
            )

            exit_code = main(
                [
                    "rerun-chapter",
                    "--project-id",
                    "My Story 01",
                    "--projects-dir",
                    tmp_dir,
                    "--chapter-number",
                    "1",
                ]
            )

            run_dir = Path(tmp_dir) / "my-story-01" / "runs" / "latest_run"
            self.assertEqual(exit_code, 0)
            self.assertTrue((run_dir / "05_chapter_1_draft.json").exists())


if __name__ == "__main__":
    unittest.main()
