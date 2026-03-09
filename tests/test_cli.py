import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from novel_writer.cli import (
    build_project_status_lines,
    build_project_status_summary,
    build_saved_run_comparison_lines,
    build_saved_run_comparison_summary,
    main,
)
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
            self.assertIn("current_comparison_basis_summary:", output)
            self.assertIn("current_comparison_reason_summary:", output)
            self.assertIn("current_comparison_metrics:", output)
            self.assertIn("best_selection_source: automatic", output)
            self.assertIn("best_comparison_basis_summary:", output)
            self.assertIn("best_selection_reason_summary:", output)
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
            self.assertIn("best_comparison_metrics: total_issue_score=", output)

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
            self.assertEqual(project_manifest["best_run"]["selection_reason_details"][0]["code"], "manual_selection")
            self.assertEqual(comparison_summary["best_run"]["run_name"], "candidate-b")
            self.assertEqual(comparison_summary["best_run"]["selection_source"], "manual")
            self.assertIn("manual_selection=candidate-b", comparison_summary["best_run"]["selection_reason"][0])
            self.assertEqual(comparison_summary["best_run"]["selection_reason_details"][0]["code"], "manual_selection")

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
            self.assertIn("current_comparison_reason_summary: long_run_should_stop=False", status_output)
            self.assertIn("best_selection_source: manual", status_output)
            self.assertIn("best_selection_reason_summary: manual_selection=candidate-b", status_output)

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

    def test_show_project_status_can_render_reason_detail_codes(self) -> None:
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
                    "Codes 01",
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
                    "Codes 01",
                    "--projects-dir",
                    tmp_dir,
                    "--output-dir",
                    str(Path(tmp_dir) / "candidate-b"),
                ]
            )
            main(
                [
                    "select-best-run",
                    "--project-id",
                    "Codes 01",
                    "--projects-dir",
                    tmp_dir,
                    "--run-name",
                    "candidate-a",
                ]
            )

            project_dir = Path(tmp_dir) / "codes-01"
            comparison_summary = load_artifact(project_dir, "run_comparison_summary")
            current_codes = [detail["code"] for detail in comparison_summary["current_run"]["comparison_reason_details"][:3]]
            best_codes = [detail["code"] for detail in comparison_summary["best_run"]["selection_reason_details"][:3]]

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(
                    [
                        "show-project-status",
                        "--project-id",
                        "Codes 01",
                        "--projects-dir",
                        tmp_dir,
                        "--reason-detail-mode",
                        "codes",
                    ]
                )

            output = buffer.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn(
                f"current_comparison_reason_codes: {', '.join(current_codes)}",
                output,
            )
            self.assertIn(
                f"best_selection_reason_codes: {', '.join(best_codes)}",
                output,
            )

    def test_build_project_status_lines_orders_reason_codes_by_schema_contract(self) -> None:
        project_manifest = {
            "project_id": "Case 01",
            "project_slug": "case-01",
            "current_run": {
                "name": "latest_run",
                "output_dir": "data/projects/case-01/runs/latest_run",
                "current_step": "publish_ready_bundle",
                "completed_steps": ["story_input", "publish_ready_bundle"],
                "chapter_statuses": [],
                "long_run_status": {},
                "comparison_basis": [],
                "comparison_reason": [],
                "comparison_metrics": {},
                "comparison_reason_details": [
                    {"code": "total_issue_score", "value": 3},
                    {"code": "long_run_should_stop", "value": False},
                ],
            },
            "best_run": {
                "run_name": "candidate-a",
                "output_dir": "data/projects/case-01/runs/candidate-a",
                "score": 3,
                "comparison_basis": [],
                "selection_source": "manual",
                "selection_reason": [],
                "comparison_metrics": {},
                "selection_reason_details": [
                    {"code": "completed_step_count", "value": 12},
                    {"code": "manual_selection", "value": "candidate-a"},
                ],
                "policy_snapshot": {},
            },
            "run_candidates": [],
        }

        lines = build_project_status_lines(project_manifest, reason_detail_mode="codes")

        self.assertIn("  current_comparison_reason_codes: long_run_should_stop, total_issue_score", lines)
        self.assertIn("  best_selection_reason_codes: manual_selection, completed_step_count", lines)

    def test_build_project_status_lines_prefers_machine_readable_comparison_context(self) -> None:
        project_manifest = {
            "project_id": "Case 02",
            "project_slug": "case-02",
            "current_run": {
                "name": "latest_run",
                "output_dir": "data/projects/case-02/runs/latest_run",
                "current_step": "publish_ready_bundle",
                "completed_steps": ["story_input"],
                "chapter_statuses": [],
                "long_run_status": {"should_stop": True},
                "comparison_basis": ["long_run_should_stop", "continuity_issue_total"],
                "comparison_reason": ["stale_reason=yes"],
                "comparison_metrics": {
                    "total_issue_score": 11,
                    "completed_step_count": 12,
                    "long_run_should_stop": False,
                },
                "comparison_reason_details": [
                    {"code": "long_run_should_stop", "value": False},
                    {"code": "total_issue_score", "value": 11},
                ],
                "policy_snapshot": {"long_run": {"max_high_severity_chapters": 6, "max_total_rerun_attempts": 20}},
            },
            "best_run": {
                "run_name": "candidate-a",
                "output_dir": "data/projects/case-02/runs/candidate-a",
                "score": 5,
                "comparison_basis": ["long_run_should_stop", "continuity_issue_total"],
                "selection_source": "manual",
                "selection_reason": ["stale_selection=yes"],
                "comparison_metrics": {
                    "total_issue_score": 5,
                    "completed_step_count": 7,
                    "long_run_should_stop": True,
                },
                "selection_reason_details": [
                    {"code": "manual_selection", "value": "candidate-a"},
                    {"code": "long_run_should_stop", "value": True},
                ],
                "policy_snapshot": {"long_run": {"max_high_severity_chapters": 2, "max_total_rerun_attempts": 20}},
            },
            "run_candidates": [],
        }

        lines = build_project_status_lines(project_manifest)

        self.assertIn("  completed_steps: 12", lines)
        self.assertIn("  current_comparison_reason_summary: long_run_should_stop=False; total_issue_score=11", lines)
        self.assertIn("  best_selection_reason_summary: manual_selection=candidate-a; long_run_should_stop=True", lines)
        self.assertIn(
            "  diff_summary: issue_score current=11 best=5; completed_steps current=12 best=7; stop current=False best=True",
            lines,
        )
        self.assertNotIn("  current_comparison_reason_summary: stale_reason=yes", lines)
        self.assertNotIn("  best_selection_reason_summary: stale_selection=yes", lines)

    def test_build_project_status_lines_keeps_documented_summary_field_mapping(self) -> None:
        project_manifest = {
            "project_id": "Case 03",
            "project_slug": "case-03",
            "current_run": {
                "name": "latest_run",
                "output_dir": "data/projects/case-03/runs/latest_run",
                "current_step": "publish_ready_bundle",
                "chapter_statuses": [],
                "long_run_status": {},
                "comparison_basis": ["long_run_should_stop", "continuity_issue_total", "quality_issue_total"],
                "comparison_reason": [],
                "comparison_metrics": {
                    "total_issue_score": 11,
                    "completed_step_count": 12,
                    "long_run_should_stop": False,
                },
                "comparison_reason_details": [
                    {"code": "long_run_should_stop", "value": False},
                    {"code": "total_issue_score", "value": 11},
                ],
                "policy_snapshot": {"long_run": {"max_high_severity_chapters": 6, "max_total_rerun_attempts": 20}},
            },
            "best_run": {
                "run_name": "candidate-a",
                "output_dir": "data/projects/case-03/runs/candidate-a",
                "score": 5,
                "comparison_basis": ["long_run_should_stop", "continuity_issue_total", "quality_issue_total"],
                "selection_source": "manual",
                "selection_reason": [],
                "comparison_metrics": {
                    "total_issue_score": 5,
                    "completed_step_count": 7,
                    "long_run_should_stop": True,
                },
                "selection_reason_details": [
                    {"code": "manual_selection", "value": "candidate-a"},
                    {"code": "long_run_should_stop", "value": True},
                ],
                "policy_snapshot": {"long_run": {"max_high_severity_chapters": 2, "max_total_rerun_attempts": 20}},
            },
            "run_candidates": [],
        }

        lines = build_project_status_lines(project_manifest, reason_detail_mode="codes")

        expected_lines = {
            "  completed_steps: 12",
            "  current_comparison_basis_summary: long_run_should_stop, continuity_issue_total, quality_issue_total",
            "  current_comparison_reason_summary: long_run_should_stop=False; total_issue_score=11",
            "  current_comparison_reason_codes: long_run_should_stop, total_issue_score",
            "  current_comparison_metrics: total_issue_score=11, completed_step_count=12",
            "  best_selection_source: manual",
            "  best_comparison_basis_summary: long_run_should_stop, continuity_issue_total, quality_issue_total",
            "  best_selection_reason_summary: manual_selection=candidate-a; long_run_should_stop=True",
            "  best_selection_reason_codes: manual_selection, long_run_should_stop",
            "  best_comparison_metrics: total_issue_score=5, completed_step_count=7",
            "  diff_summary: issue_score current=11 best=5; completed_steps current=12 best=7; stop current=False best=True",
            "  diff_policy: max_high_severity_chapters current=6 best=2; max_total_rerun_attempts current=20 best=20",
            "  policy_diff.max_high_severity_chapters: current=6, best=2",
        }

        self.assertTrue(expected_lines.issubset(set(lines)))

    def test_build_project_status_summary_returns_render_ready_sections(self) -> None:
        project_manifest = {
            "project_id": "Case 04",
            "project_slug": "case-04",
            "current_run": {
                "name": "latest_run",
                "output_dir": "data/projects/case-04/runs/latest_run",
                "current_step": "publish_ready_bundle",
                "chapter_statuses": [],
                "long_run_status": {"should_stop": False, "reason": "none"},
                "comparison_basis": ["long_run_should_stop", "continuity_issue_total"],
                "comparison_reason": [],
                "comparison_metrics": {
                    "total_issue_score": 11,
                    "completed_step_count": 12,
                    "long_run_should_stop": False,
                },
                "comparison_reason_details": [
                    {"code": "long_run_should_stop", "value": False},
                    {"code": "total_issue_score", "value": 11},
                ],
                "policy_snapshot": {"long_run": {"max_high_severity_chapters": 6, "max_total_rerun_attempts": 20}},
            },
            "best_run": {
                "run_name": "candidate-a",
                "output_dir": "data/projects/case-04/runs/candidate-a",
                "score": 5,
                "comparison_basis": ["long_run_should_stop", "continuity_issue_total"],
                "selection_source": "manual",
                "selection_reason": [],
                "comparison_metrics": {
                    "total_issue_score": 5,
                    "completed_step_count": 7,
                    "long_run_should_stop": True,
                },
                "selection_reason_details": [
                    {"code": "manual_selection", "value": "candidate-a"},
                    {"code": "long_run_should_stop", "value": True},
                ],
                "policy_snapshot": {"long_run": {"max_high_severity_chapters": 2, "max_total_rerun_attempts": 20}},
            },
            "run_candidates": [{"run_name": "candidate-a"}, {"run_name": "latest_run"}],
        }

        summary = build_project_status_summary(project_manifest, reason_detail_mode="codes")

        self.assertEqual(summary["project_label"], "case-04")
        self.assertEqual(summary["run_candidate_count"], 2)
        self.assertEqual(summary["current_run"]["completed_steps"], 12)
        self.assertIn(
            "  current_comparison_reason_codes: long_run_should_stop, total_issue_score",
            summary["current_run"]["comparison_lines"],
        )
        self.assertEqual(summary["best_run"]["name"], "candidate-a")
        self.assertIn("  best_selection_source: manual", summary["best_run"]["selection_lines"])
        self.assertIn(
            "  diff_summary: issue_score current=11 best=5; completed_steps current=12 best=7; stop current=False best=True",
            summary["best_run"]["diff_lines"],
        )
        self.assertEqual(
            summary["best_run"]["comparison_metrics_line"],
            "  best_comparison_metrics: total_issue_score=5, completed_step_count=7",
        )

    def test_build_run_comparison_summary_returns_render_ready_sections(self) -> None:
        summary_artifact = {
            "project_id": "Case 05",
            "project_slug": "case-05",
            "candidate_count": 2,
            "current_run": {
                "run_name": "latest_run",
                "output_dir": "data/projects/case-05/runs/latest_run",
                "comparison_basis": ["long_run_should_stop", "continuity_issue_total"],
                "comparison_metrics": {
                    "total_issue_score": 11,
                    "completed_step_count": 12,
                    "long_run_should_stop": False,
                },
                "comparison_reason_details": [
                    {"code": "long_run_should_stop", "value": False},
                    {"code": "total_issue_score", "value": 11},
                ],
            },
            "best_run": {
                "run_name": "candidate-a",
                "output_dir": "data/projects/case-05/runs/candidate-a",
                "selection_source": "manual",
                "comparison_basis": ["long_run_should_stop", "continuity_issue_total"],
                "comparison_metrics": {
                    "total_issue_score": 5,
                    "completed_step_count": 7,
                },
                "selection_reason_details": [
                    {"code": "manual_selection", "value": "candidate-a"},
                    {"code": "long_run_should_stop", "value": True},
                ],
            },
            "compact_summary": {
                "selection_source": "manual",
                "issue_score": {"current": 11, "best": 5},
                "completed_step_count": {"current": 12, "best": 7},
                "long_run_should_stop": {"current": False, "best": True},
                "policy_limits": {
                    "max_high_severity_chapters": {"current": 6, "best": 2},
                    "max_total_rerun_attempts": {"current": 20, "best": 20},
                },
            },
            "run_candidates": [
                {"run_name": "latest_run", "score": 11, "output_dir": "data/projects/case-05/runs/latest_run"},
                {"run_name": "candidate-a", "score": 5, "output_dir": "data/projects/case-05/runs/candidate-a"},
            ],
        }

        summary = build_saved_run_comparison_summary(summary_artifact, reason_detail_mode="codes")
        lines = build_saved_run_comparison_lines(summary_artifact, reason_detail_mode="codes")

        self.assertEqual(summary["project_label"], "case-05")
        self.assertEqual(summary["candidate_count"], 2)
        self.assertEqual(summary["run_candidates"]["names"], ["latest_run", "candidate-a"])
        self.assertEqual(summary["run_candidates"]["scores"], ["latest_run=11", "candidate-a=5"])
        self.assertEqual(
            summary["run_candidates"]["output_dirs"],
            [
                "latest_run=data/projects/case-05/runs/latest_run",
                "candidate-a=data/projects/case-05/runs/candidate-a",
            ],
        )
        self.assertEqual(summary["current_run"]["output_dir"], "data/projects/case-05/runs/latest_run")
        self.assertEqual(summary["best_run"]["output_dir"], "data/projects/case-05/runs/candidate-a")
        self.assertEqual(summary["current_run"]["comparison_metrics"]["total_issue_score"], 11)
        self.assertEqual(summary["best_run"]["comparison_metrics"]["total_issue_score"], 5)
        self.assertEqual(
            summary["current_run"]["comparison_metrics_line"],
            "  current_comparison_metrics: total_issue_score=11, completed_step_count=12",
        )
        self.assertEqual(
            summary["best_run"]["comparison_metrics_line"],
            "  best_comparison_metrics: total_issue_score=5, completed_step_count=7",
        )
        self.assertIn(
            "  current_comparison_reason_codes: long_run_should_stop, total_issue_score",
            summary["current_run"]["comparison_summary"]["lines"],
        )
        self.assertIn("  run_candidate_names: latest_run, candidate-a", summary["run_candidates"]["lines"])
        self.assertEqual(
            summary["current_run"]["comparison_summary"]["basis_summary"],
            "long_run_should_stop, continuity_issue_total",
        )
        self.assertEqual(
            summary["current_run"]["comparison_summary"]["reason_summary"],
            "long_run_should_stop=False; total_issue_score=11",
        )
        self.assertEqual(
            summary["current_run"]["comparison_summary"]["reason_codes"],
            ["long_run_should_stop", "total_issue_score"],
        )
        self.assertEqual(summary["best_run"]["selection_summary"]["selection_source"], "manual")
        self.assertEqual(
            summary["best_run"]["selection_summary"]["basis_summary"],
            "long_run_should_stop, continuity_issue_total",
        )
        self.assertEqual(
            summary["best_run"]["selection_summary"]["reason_summary"],
            "manual_selection=candidate-a; long_run_should_stop=True",
        )
        self.assertEqual(
            summary["best_run"]["selection_summary"]["reason_codes"],
            ["manual_selection", "long_run_should_stop"],
        )
        self.assertIn("  best_selection_source: manual", summary["best_run"]["selection_summary"]["lines"])
        self.assertEqual(summary["compact_summary"]["selection_source"], "manual")
        self.assertEqual(summary["compact_summary"]["issue_score"], {"current": 11, "best": 5})
        self.assertEqual(
            summary["compact_summary"]["policy_limits"]["max_high_severity_chapters"],
            {"current": 6, "best": 2},
        )
        self.assertEqual(
            summary["compact_summary"]["lines"][0],
            "Compact summary: selection_source=manual",
        )
        self.assertEqual(
            summary["run_candidates"]["lines"][0],
            "  run_candidate_names: latest_run, candidate-a",
        )
        self.assertIn("Compact summary: selection_source=manual", lines)
        self.assertIn("  compact.issue_score: current=11, best=5", lines)
        self.assertIn("  compact.policy_limits.max_high_severity_chapters: current=6, best=2", lines)
        self.assertIn("Run candidates: 2", lines)
        self.assertEqual(lines[0], "Project: case-05")

    def test_build_run_comparison_lines_keep_documented_field_mapping(self) -> None:
        summary_artifact = {
            "project_id": "Case 06",
            "project_slug": "case-06",
            "candidate_count": 2,
            "current_run": {
                "run_name": "latest_run",
                "output_dir": "data/projects/case-06/runs/latest_run",
                "comparison_basis": ["long_run_should_stop", "continuity_issue_total", "quality_issue_total"],
                "comparison_metrics": {
                    "total_issue_score": 11,
                    "completed_step_count": 12,
                    "long_run_should_stop": False,
                },
                "comparison_reason_details": [
                    {"code": "long_run_should_stop", "value": False},
                    {"code": "total_issue_score", "value": 11},
                ],
            },
            "best_run": {
                "run_name": "candidate-a",
                "output_dir": "data/projects/case-06/runs/candidate-a",
                "selection_source": "manual",
                "comparison_basis": ["long_run_should_stop", "continuity_issue_total", "quality_issue_total"],
                "comparison_metrics": {
                    "total_issue_score": 5,
                    "completed_step_count": 7,
                },
                "selection_reason_details": [
                    {"code": "manual_selection", "value": "candidate-a"},
                    {"code": "long_run_should_stop", "value": True},
                ],
            },
            "compact_summary": {
                "selection_source": "manual",
                "issue_score": {"current": 11, "best": 5},
                "completed_step_count": {"current": 12, "best": 7},
                "long_run_should_stop": {"current": False, "best": True},
                "policy_limits": {
                    "max_high_severity_chapters": {"current": 6, "best": 2},
                    "max_total_rerun_attempts": {"current": 20, "best": 20},
                },
            },
            "run_candidates": [
                {"run_name": "latest_run", "score": 11, "output_dir": "data/projects/case-06/runs/latest_run"},
                {"run_name": "candidate-a", "score": 5, "output_dir": "data/projects/case-06/runs/candidate-a"},
            ],
        }

        lines = build_saved_run_comparison_lines(summary_artifact, reason_detail_mode="codes")
        expected_lines = {
            "Current run: latest_run",
            "  output_dir: data/projects/case-06/runs/latest_run",
            "  current_comparison_basis_summary: long_run_should_stop, continuity_issue_total, quality_issue_total",
            "  current_comparison_reason_summary: long_run_should_stop=False; total_issue_score=11",
            "  current_comparison_reason_codes: long_run_should_stop, total_issue_score",
            "  current_comparison_metrics: total_issue_score=11, completed_step_count=12",
            "Best run: candidate-a",
            "  output_dir: data/projects/case-06/runs/candidate-a",
            "  best_selection_source: manual",
            "  best_comparison_basis_summary: long_run_should_stop, continuity_issue_total, quality_issue_total",
            "  best_selection_reason_summary: manual_selection=candidate-a; long_run_should_stop=True",
            "  best_selection_reason_codes: manual_selection, long_run_should_stop",
            "  best_comparison_metrics: total_issue_score=5, completed_step_count=7",
            "Compact summary: selection_source=manual",
            "  compact.issue_score: current=11, best=5",
            "  compact.completed_step_count: current=12, best=7",
            "  compact.long_run_should_stop: current=False, best=True",
            "  compact.policy_limits.max_high_severity_chapters: current=6, best=2",
            "  compact.policy_limits.max_total_rerun_attempts: current=20, best=20",
            "Run candidates: 2",
            "  run_candidate_names: latest_run, candidate-a",
            "  run_candidate_scores: latest_run=11, candidate-a=5",
            "  run_candidate_output_dirs: latest_run=data/projects/case-06/runs/latest_run, candidate-a=data/projects/case-06/runs/candidate-a",
        }

        self.assertTrue(expected_lines.issubset(set(lines)))

    def test_build_run_comparison_lines_keeps_section_order_contract(self) -> None:
        summary_artifact = {
            "project_id": "Case 07",
            "project_slug": "case-07",
            "candidate_count": 2,
            "current_run": {
                "run_name": "latest_run",
                "output_dir": "data/projects/case-07/runs/latest_run",
                "comparison_basis": ["long_run_should_stop", "continuity_issue_total"],
                "comparison_metrics": {
                    "total_issue_score": 11,
                    "completed_step_count": 12,
                },
                "comparison_reason_details": [
                    {"code": "long_run_should_stop", "value": False},
                ],
            },
            "best_run": {
                "run_name": "candidate-a",
                "output_dir": "data/projects/case-07/runs/candidate-a",
                "selection_source": "manual",
                "comparison_basis": ["long_run_should_stop", "continuity_issue_total"],
                "comparison_metrics": {
                    "total_issue_score": 5,
                    "completed_step_count": 7,
                },
                "selection_reason_details": [
                    {"code": "manual_selection", "value": "candidate-a"},
                ],
            },
            "compact_summary": {
                "selection_source": "manual",
                "issue_score": {"current": 11, "best": 5},
                "completed_step_count": {"current": 12, "best": 7},
                "long_run_should_stop": {"current": False, "best": True},
                "policy_limits": {
                    "max_high_severity_chapters": {"current": 6, "best": 2},
                    "max_total_rerun_attempts": {"current": 20, "best": 20},
                },
            },
            "run_candidates": [
                {"run_name": "latest_run", "score": 11, "output_dir": "data/projects/case-07/runs/latest_run"},
                {"run_name": "candidate-a", "score": 5, "output_dir": "data/projects/case-07/runs/candidate-a"},
            ],
        }

        lines = build_saved_run_comparison_lines(summary_artifact, reason_detail_mode="codes")

        project_index = lines.index("Project: case-07")
        current_index = lines.index("Current run: latest_run")
        best_index = lines.index("Best run: candidate-a")
        compact_index = lines.index("Compact summary: selection_source=manual")
        candidate_index = lines.index("Run candidates: 2")

        self.assertLess(project_index, current_index)
        self.assertLess(current_index, best_index)
        self.assertLess(best_index, compact_index)
        self.assertLess(compact_index, candidate_index)

    def test_build_run_comparison_lines_skips_missing_optional_sections(self) -> None:
        summary_artifact = {
            "project_id": "Case 08",
            "project_slug": "case-08",
            "candidate_count": 0,
            "current_run": {
                "run_name": "latest_run",
                "output_dir": "data/projects/case-08/runs/latest_run",
                "comparison_basis": ["long_run_should_stop"],
                "comparison_metrics": {
                    "total_issue_score": 3,
                    "completed_step_count": 4,
                },
                "comparison_reason_details": [
                    {"code": "total_issue_score", "value": 3},
                ],
            },
        }

        lines = build_saved_run_comparison_lines(summary_artifact, reason_detail_mode="codes")

        self.assertEqual(lines[0], "Project: case-08")
        self.assertIn("Current run: latest_run", lines)
        self.assertNotIn("Best run: candidate-a", lines)
        self.assertNotIn("Compact summary: selection_source=manual", lines)
        self.assertIn("Run candidates: 0", lines)

    def test_cli_show_run_comparison_reads_artifact_without_rerunning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            main(
                [
                    "create-project",
                    "--theme",
                    "記憶",
                    "--genre",
                    "SF",
                    "--tone",
                    "静謐",
                    "--target-length",
                    "5000",
                    "--project-id",
                    "Compare 01",
                    "--projects-dir",
                    tmp_dir,
                ]
            )

            project_dir = Path(tmp_dir) / "compare-01"
            comparison_before = load_artifact(project_dir, "run_comparison_summary")

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(
                    [
                        "show-run-comparison",
                        "--project-id",
                        "Compare 01",
                        "--projects-dir",
                        tmp_dir,
                        "--reason-detail-mode",
                        "codes",
                    ]
                )

            comparison_after = load_artifact(project_dir, "run_comparison_summary")
            output = buffer.getvalue()

            self.assertEqual(exit_code, 0)
            self.assertEqual(comparison_before, comparison_after)
            self.assertIn("Project: compare-01", output)
            self.assertIn("Current run: latest_run", output)
            self.assertIn("output_dir:", output)
            self.assertIn("Best run: latest_run", output)
            self.assertIn("current_comparison_reason_codes:", output)
            self.assertIn("best_selection_source:", output)
            self.assertIn("Compact summary: selection_source=", output)
            self.assertIn("compact.issue_score:", output)
            self.assertIn("compact.policy_limits.max_high_severity_chapters:", output)
            self.assertIn("Run candidates: 1", output)
            self.assertIn("run_candidate_names: latest_run", output)
            self.assertIn("run_candidate_scores: latest_run=11", output)
            self.assertIn("run_candidate_output_dirs: latest_run=", output)


if __name__ == "__main__":
    unittest.main()
