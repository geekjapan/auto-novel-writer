import io
import tempfile
import unittest
from contextlib import redirect_stdout
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
            self.assertTrue((Path(tmp_dir) / "chapter_2_draft.json").exists())
            self.assertTrue((Path(tmp_dir) / "revised_chapter_1_draft.json").exists())
            self.assertTrue((Path(tmp_dir) / "revised_chapter_2_draft.json").exists())
            self.assertTrue((Path(tmp_dir) / "publish_ready_bundle.json").exists())

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
            self.assertEqual(
                len(project_manifest["current_run"]["chapter_statuses"]),
                project_manifest["current_run"]["summary"]["counts"]["chapters"],
            )
            self.assertIn("long_run_status", project_manifest["current_run"])
            self.assertIn("policy_snapshot", project_manifest["current_run"])

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

    def test_cli_rerun_chapter_command_supports_arbitrary_chapter(self) -> None:
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
                    "2",
                ]
            )

            run_dir = Path(tmp_dir) / "my-story-01" / "runs" / "latest_run"
            manifest = load_artifact(run_dir, "manifest")
            self.assertEqual(exit_code, 0)
            self.assertTrue((run_dir / "05_chapter_1_draft.json").exists())
            self.assertTrue((run_dir / "chapter_2_draft.json").exists())
            self.assertTrue((run_dir / "revised_chapter_2_draft.json").exists())
            self.assertTrue(any(entry.get("chapter_index") == 1 for entry in manifest["continuity_history"]))
            self.assertTrue(
                any(
                    entry.get("chapter_index") == 1 and entry.get("triggered_by") == "manual"
                    for entry in manifest["rerun_history"]
                )
            )
            project_manifest = load_artifact(Path(tmp_dir) / "my-story-01", "project_manifest")
            chapter_2_status = next(
                status for status in project_manifest["current_run"]["chapter_statuses"] if status["chapter_number"] == 2
            )
            self.assertEqual(chapter_2_status["chapter_index"], 1)
            self.assertEqual(chapter_2_status["latest_rerun_action"], "reran_chapter_draft")
            self.assertIsNotNone(chapter_2_status["latest_revision_attempt"])

    def test_project_manifest_tracks_run_candidates_and_best_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            first_run_dir = Path(tmp_dir) / "candidate-a"
            second_run_dir = Path(tmp_dir) / "candidate-b"

            first_exit_code = main(
                [
                    "create-project",
                    "--theme",
                    "秘密",
                    "--genre",
                    "ミステリ",
                    "--tone",
                    "静謐",
                    "--target-length",
                    "5000",
                    "--project-id",
                    "Case 02",
                    "--projects-dir",
                    tmp_dir,
                    "--output-dir",
                    str(first_run_dir),
                ]
            )
            second_exit_code = main(
                [
                    "create-project",
                    "--theme",
                    "秘密",
                    "--genre",
                    "ミステリ",
                    "--tone",
                    "静謐",
                    "--target-length",
                    "5000",
                    "--project-id",
                    "Case 02",
                    "--projects-dir",
                    tmp_dir,
                    "--output-dir",
                    str(second_run_dir),
                ]
            )

            project_dir = Path(tmp_dir) / "case-02"
            project_manifest = load_artifact(project_dir, "project_manifest")
            comparison_summary = load_artifact(project_dir, "run_comparison_summary")

            self.assertEqual(first_exit_code, 0)
            self.assertEqual(second_exit_code, 0)
            self.assertEqual(len(project_manifest["run_candidates"]), 2)
            self.assertEqual(project_manifest["current_run"]["output_dir"], str(second_run_dir))
            self.assertIn(project_manifest["best_run"]["output_dir"], {str(first_run_dir), str(second_run_dir)})
            self.assertTrue(all("chapter_statuses" in candidate for candidate in project_manifest["run_candidates"]))
            self.assertTrue(all("comparison_metrics" in candidate for candidate in project_manifest["run_candidates"]))
            self.assertTrue(all("comparison_basis" in candidate for candidate in project_manifest["run_candidates"]))
            self.assertTrue(all("comparison_reason" in candidate for candidate in project_manifest["run_candidates"]))
            self.assertTrue(all("long_run_status" in candidate for candidate in project_manifest["run_candidates"]))
            self.assertTrue(all("policy_snapshot" in candidate for candidate in project_manifest["run_candidates"]))
            self.assertIn("comparison_metrics", project_manifest["current_run"])
            self.assertIn("comparison_basis", project_manifest["current_run"])
            self.assertIn("comparison_reason", project_manifest["current_run"])
            self.assertIn("comparison_metrics", project_manifest["best_run"])
            self.assertIn("policy_snapshot", project_manifest["best_run"])
            self.assertIn("selection_reason", project_manifest["best_run"])
            self.assertIn("long_run_should_stop", project_manifest["best_run"]["comparison_metrics"])
            self.assertIn("total_issue_score=", project_manifest["best_run"]["selection_reason"][1])
            self.assertEqual(
                {candidate["output_dir"] for candidate in project_manifest["run_candidates"]},
                {str(first_run_dir), str(second_run_dir)},
            )
            self.assertEqual(comparison_summary["schema_name"], "run_comparison_summary")
            self.assertEqual(comparison_summary["schema_version"], "1.0")
            self.assertEqual(comparison_summary["candidate_count"], 2)
            self.assertEqual(comparison_summary["best_run"]["output_dir"], project_manifest["best_run"]["output_dir"])
            self.assertEqual(comparison_summary["current_run"]["output_dir"], str(second_run_dir))
            self.assertIn("comparison_metrics", comparison_summary["current_run"])
            self.assertIn("comparison_basis", comparison_summary["current_run"])
            self.assertIn("comparison_reason", comparison_summary["current_run"])
            self.assertIn("compact_summary", comparison_summary)
            self.assertIn("issue_score", comparison_summary["compact_summary"])
            self.assertIn("policy_limits", comparison_summary["compact_summary"])

    def test_cli_prints_current_vs_best_run_summary_for_project_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            main(
                [
                    "create-project",
                    "--theme",
                    "秘密",
                    "--genre",
                    "ミステリ",
                    "--tone",
                    "静謐",
                    "--target-length",
                    "5000",
                    "--project-id",
                    "Case 03",
                    "--projects-dir",
                    tmp_dir,
                    "--output-dir",
                    str(Path(tmp_dir) / "candidate-a"),
                ]
            )

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(
                    [
                        "create-project",
                        "--theme",
                        "秘密",
                        "--genre",
                        "ミステリ",
                        "--tone",
                        "静謐",
                        "--target-length",
                        "5000",
                        "--project-id",
                        "Case 03",
                        "--projects-dir",
                        tmp_dir,
                        "--output-dir",
                        str(Path(tmp_dir) / "candidate-b"),
                    ]
                )

            output = buffer.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("Long-run status:", output)
            self.assertIn("Best run:", output)
            self.assertIn("Comparison metrics:", output)

    def test_cli_show_project_status_reads_manifest_without_rerunning(self) -> None:
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
                    "Status 01",
                    "--projects-dir",
                    tmp_dir,
                ]
            )

            project_dir = Path(tmp_dir) / "status-01"
            before_manifest = load_artifact(project_dir, "project_manifest")

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(
                    [
                        "show-project-status",
                        "--project-id",
                        "Status 01",
                        "--projects-dir",
                        tmp_dir,
                    ]
                )

            after_manifest = load_artifact(project_dir, "project_manifest")
            output = buffer.getvalue()

            self.assertEqual(exit_code, 0)
            self.assertEqual(before_manifest, after_manifest)
            self.assertIn("Project: status-01", output)
            self.assertIn("Current run: latest_run", output)
            self.assertIn("Best run: latest_run", output)
            self.assertIn("comparison_reason_summary:", output)
            self.assertIn("selection_source: automatic", output)
            self.assertIn("selection_reason_summary:", output)
            self.assertIn("diff_summary:", output)
            self.assertIn("diff_policy:", output)
            self.assertIn("Run candidates: 1", output)
            self.assertIn("chapter_statuses: 3 tracked", output)
            self.assertIn("chapters_with_issues:", output)
            self.assertIn("chapter_details:", output)
            self.assertIn("chapter_1: continuity_issues=", output)
            self.assertIn("rerun_attempt=", output)
            self.assertIn("revision_attempt=", output)
            self.assertIn("long_run_status: should_stop=False, reason=none", output)
            self.assertIn("long_run_budget: remaining_rerun_attempt_budget=", output)
            self.assertIn("comparison_metrics: total_issue_score=", output)

    def test_cli_can_override_long_run_policy_limits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            exit_code = main(
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
                    "Policy 01",
                    "--projects-dir",
                    tmp_dir,
                    "--max-high-severity-chapters",
                    "2",
                    "--max-total-rerun-attempts",
                    "7",
                ]
            )

            project_manifest = load_artifact(Path(tmp_dir) / "policy-01", "project_manifest")
            policy_limits = project_manifest["current_run"]["long_run_status"]["policy_limits"]
            policy_snapshot = project_manifest["current_run"]["policy_snapshot"]

            self.assertEqual(exit_code, 0)
            self.assertEqual(policy_limits["max_high_severity_chapters"], 2)
            self.assertEqual(policy_limits["max_total_rerun_attempts"], 7)
            self.assertEqual(policy_snapshot["long_run"]["max_high_severity_chapters"], 2)
            self.assertEqual(policy_snapshot["long_run"]["max_total_rerun_attempts"], 7)

    def test_cli_can_manually_select_best_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            main(
                [
                    "create-project",
                    "--theme",
                    "秘密",
                    "--genre",
                    "ミステリ",
                    "--tone",
                    "静謐",
                    "--target-length",
                    "5000",
                    "--project-id",
                    "Manual 01",
                    "--projects-dir",
                    tmp_dir,
                    "--output-dir",
                    str(Path(tmp_dir) / "candidate-a"),
                ]
            )
            main(
                [
                    "create-project",
                    "--theme",
                    "秘密",
                    "--genre",
                    "ミステリ",
                    "--tone",
                    "静謐",
                    "--target-length",
                    "5000",
                    "--project-id",
                    "Manual 01",
                    "--projects-dir",
                    tmp_dir,
                    "--output-dir",
                    str(Path(tmp_dir) / "candidate-b"),
                ]
            )

            exit_code = main(
                [
                    "select-best-run",
                    "--project-id",
                    "Manual 01",
                    "--projects-dir",
                    tmp_dir,
                    "--run-name",
                    "candidate-b",
                ]
            )

            project_dir = Path(tmp_dir) / "manual-01"
            project_manifest = load_artifact(project_dir, "project_manifest")
            comparison_summary = load_artifact(project_dir, "run_comparison_summary")

            self.assertEqual(exit_code, 0)
            self.assertEqual(project_manifest["best_run"]["run_name"], "candidate-b")
            self.assertEqual(project_manifest["best_run"]["selection_source"], "manual")
            self.assertIn("manual_selection=candidate-b", project_manifest["best_run"]["selection_reason"][0])
            self.assertEqual(comparison_summary["best_run"]["run_name"], "candidate-b")
            self.assertEqual(comparison_summary["best_run"]["selection_source"], "manual")
            self.assertIn("manual_selection=candidate-b", comparison_summary["best_run"]["selection_reason"][0])

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                status_exit_code = main(
                    [
                        "show-project-status",
                        "--project-id",
                        "Manual 01",
                        "--projects-dir",
                        tmp_dir,
                    ]
                )

            status_output = buffer.getvalue()
            self.assertEqual(status_exit_code, 0)
            self.assertIn("comparison_reason_summary: long_run_should_stop=False", status_output)
            self.assertIn("selection_source: manual", status_output)
            self.assertIn("selection_reason_summary: manual_selection=candidate-b", status_output)

    def test_show_project_status_displays_policy_diff_against_best_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            main(
                [
                    "create-project",
                    "--theme",
                    "秘密",
                    "--genre",
                    "ミステリ",
                    "--tone",
                    "静謐",
                    "--target-length",
                    "5000",
                    "--project-id",
                    "Diff 01",
                    "--projects-dir",
                    tmp_dir,
                    "--output-dir",
                    str(Path(tmp_dir) / "candidate-a"),
                    "--max-high-severity-chapters",
                    "2",
                ]
            )
            main(
                [
                    "create-project",
                    "--theme",
                    "秘密",
                    "--genre",
                    "ミステリ",
                    "--tone",
                    "静謐",
                    "--target-length",
                    "5000",
                    "--project-id",
                    "Diff 01",
                    "--projects-dir",
                    tmp_dir,
                    "--output-dir",
                    str(Path(tmp_dir) / "candidate-b"),
                    "--max-high-severity-chapters",
                    "6",
                ]
            )
            main(
                [
                    "select-best-run",
                    "--project-id",
                    "Diff 01",
                    "--projects-dir",
                    tmp_dir,
                    "--run-name",
                    "candidate-a",
                ]
            )

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(
                    [
                        "show-project-status",
                        "--project-id",
                        "Diff 01",
                        "--projects-dir",
                        tmp_dir,
                    ]
                )

            output = buffer.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("policy_diff.max_high_severity_chapters: current=6, best=2", output)
            self.assertIn("diff_summary: issue_score current=", output)
            self.assertIn("diff_policy: max_high_severity_chapters current=6 best=2", output)


if __name__ == "__main__":
    unittest.main()
