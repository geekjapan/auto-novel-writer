import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from novel_writer.cli import (
    _build_resume_gate_status_line,
    _build_saved_story_state_summary_line,
    _build_publish_bundle_summary_lines,
    _build_saved_publish_bundle_summary_lines,
    build_project_status_lines,
    build_project_status_summary,
    build_saved_run_comparison_lines,
    build_saved_run_comparison_summary,
    main,
    print_run_summary,
)
from novel_writer.storage import (
    load_artifact,
    load_publish_ready_bundle,
    save_artifact,
    save_next_action_decision,
    save_publish_ready_bundle,
    save_run_comparison_summary,
)


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

    def test_cli_rerun_chapter_keeps_show_run_comparison_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            create_exit_code = main(
                [
                    "create-project",
                    "--theme",
                    "約束",
                    "--genre",
                    "青春ドラマ",
                    "--tone",
                    "軽やか",
                    "--target-length",
                    "5000",
                    "--project-id",
                    "Compare Rerun 01",
                    "--projects-dir",
                    tmp_dir,
                ]
            )
            rerun_exit_code = main(
                [
                    "rerun-chapter",
                    "--project-id",
                    "Compare Rerun 01",
                    "--projects-dir",
                    tmp_dir,
                    "--chapter-number",
                    "2",
                ]
            )

            project_dir = Path(tmp_dir) / "compare-rerun-01"
            run_dir = project_dir / "runs" / "latest_run"
            publish_ready_bundle = load_publish_ready_bundle(run_dir)
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                comparison_exit_code = main(
                    [
                        "show-run-comparison",
                        "--project-id",
                        "Compare Rerun 01",
                        "--projects-dir",
                        tmp_dir,
                        "--reason-detail-mode",
                        "codes",
                    ]
                )

            output = buffer.getvalue()

            self.assertEqual(create_exit_code, 0)
            self.assertEqual(rerun_exit_code, 0)
            self.assertEqual(comparison_exit_code, 0)
            self.assertIn("publish_bundle.title:", output)
            self.assertIn(
                "publish_bundle.section_names: manuscript, story_summary, quality",
                output,
            )
            self.assertEqual(
                load_publish_ready_bundle(run_dir)["summary"],
                publish_ready_bundle["summary"],
            )

    def test_cli_main_resume_from_output_dir_blocks_manual_stop_for_review_for_project(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            create_exit_code = main(
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
                    "Case 08",
                    "--projects-dir",
                    tmp_dir,
                ]
            )

            project_dir = Path(tmp_dir) / "case-08"
            run_dir = project_dir / "runs" / "latest_run"
            project_manifest_path = project_dir / "project_manifest.json"
            project_manifest = load_artifact(project_dir, "project_manifest")
            project_manifest["autonomy_level"] = "manual"
            project_manifest_path.write_text(
                json.dumps(project_manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            save_next_action_decision(
                run_dir,
                {
                    "schema_name": "next_action_decision",
                    "schema_version": "1.0",
                    "evaluated_through_chapter": 5,
                    "story_state_summary": {
                        "evaluated_through_chapter": 5,
                        "canon_chapter_count": 5,
                        "thread_count": 0,
                        "unresolved_thread_count": 0,
                        "resolved_thread_count": 0,
                        "open_question_count": 0,
                        "latest_timeline_event_count": 0,
                    },
                    "action": "stop_for_review",
                    "reason": "manual review required",
                    "issue_codes": ["manual_review"],
                    "target_chapters": [],
                    "policy_budget": {
                        "max_high_severity_chapters": 0,
                        "max_total_rerun_attempts": 0,
                        "remaining_high_severity_chapter_budget": 0,
                        "remaining_rerun_attempt_budget": 0,
                    },
                    "decision_trace": [
                        {
                            "code": "manual_review",
                            "summary": "Manual review is required before continuing.",
                            "value": "chapter-5",
                        }
                    ],
                },
            )

            with self.assertRaisesRegex(
                ValueError,
                "resume-project.*manual.*stop_for_review",
            ):
                main(
                    [
                        "--resume-from-output-dir",
                        str(run_dir),
                        "--project-id",
                        "Case 08",
                        "--projects-dir",
                        tmp_dir,
                    ]
                )

            self.assertEqual(create_exit_code, 0)

    def test_cli_main_resume_from_output_dir_can_attach_to_new_project_without_manifest(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            standalone_exit_code = main(
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
            resume_exit_code = main(
                [
                    "--resume-from-output-dir",
                    tmp_dir,
                    "--project-id",
                    "Case 09",
                    "--projects-dir",
                    tmp_dir,
                ]
            )

            project_dir = Path(tmp_dir) / "case-09"

            self.assertEqual(standalone_exit_code, 0)
            self.assertEqual(resume_exit_code, 0)
            self.assertTrue((Path(tmp_dir) / "manifest.json").exists())
            self.assertTrue((project_dir / "project_manifest.json").exists())

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
            self.assertEqual(
                project_manifest["current_run"]["output_dir"], str(run_dir)
            )
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

    def test_cli_resume_project_blocks_manual_stop_for_review_before_pipeline(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir) / "case-05"
            run_dir = project_dir / "runs" / "latest_run"

            with (
                patch(
                    "novel_writer.cli.load_project_run_context",
                    return_value=({"project_dir": project_dir}, run_dir),
                ),
                patch(
                    "novel_writer.cli.load_project_manifest",
                    return_value={"autonomy_level": "manual"},
                ),
                patch(
                    "novel_writer.cli.load_next_action_decision",
                    return_value={"action": "stop_for_review"},
                ),
                patch("novel_writer.cli.run_pipeline") as run_pipeline,
                patch("novel_writer.cli.save_project_state"),
                patch("novel_writer.cli.print_run_summary"),
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    "resume-project.*manual.*stop_for_review",
                ):
                    main(
                        [
                            "resume-project",
                            "--project-id",
                            "Case 05",
                            "--projects-dir",
                            tmp_dir,
                        ]
                    )

            run_pipeline.assert_not_called()

    def test_cli_resume_project_allows_missing_next_action_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir) / "case-06"
            run_dir = project_dir / "runs" / "latest_run"
            calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

            def fake_run_pipeline(*args: object, **kwargs: object) -> dict[str, object]:
                calls.append((args, kwargs))
                return {"artifacts": []}

            with (
                patch(
                    "novel_writer.cli.load_project_run_context",
                    return_value=({"project_dir": project_dir}, run_dir),
                ),
                patch(
                    "novel_writer.cli.load_project_manifest",
                    return_value={"autonomy_level": "manual"},
                ),
                patch(
                    "novel_writer.cli.load_next_action_decision",
                    side_effect=FileNotFoundError,
                ),
                patch("novel_writer.cli.run_pipeline", side_effect=fake_run_pipeline),
                patch("novel_writer.cli.save_project_state"),
                patch("novel_writer.cli.print_run_summary"),
            ):
                exit_code = main(
                    [
                        "resume-project",
                        "--project-id",
                        "Case 06",
                        "--projects-dir",
                        tmp_dir,
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][1]["resume_from"], run_dir)

    def test_cli_resume_project_allows_assist_stop_for_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir) / "case-07"
            run_dir = project_dir / "runs" / "latest_run"
            calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

            def fake_run_pipeline(*args: object, **kwargs: object) -> dict[str, object]:
                calls.append((args, kwargs))
                return {"artifacts": []}

            with (
                patch(
                    "novel_writer.cli.load_project_run_context",
                    return_value=({"project_dir": project_dir}, run_dir),
                ),
                patch(
                    "novel_writer.cli.load_project_manifest",
                    return_value={"autonomy_level": "assist"},
                ),
                patch(
                    "novel_writer.cli.load_next_action_decision",
                    return_value={"action": "stop_for_review"},
                ),
                patch("novel_writer.cli.run_pipeline", side_effect=fake_run_pipeline),
                patch("novel_writer.cli.save_project_state"),
                patch("novel_writer.cli.print_run_summary"),
            ):
                exit_code = main(
                    [
                        "resume-project",
                        "--project-id",
                        "Case 07",
                        "--projects-dir",
                        tmp_dir,
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][1]["resume_from"], run_dir)

    def test_build_publish_bundle_summary_lines_prefers_saved_summary(self) -> None:
        publish_ready_bundle = {
            "title": "Case Bundle",
            "chapter_count": 2,
            "sections": {
                "manuscript": {"field": "chapters"},
                "story_summary": {"field": "story_summary"},
            },
            "source_artifacts": {
                "story_summary": "story_summary.json",
                "chapters": "revised_chapter_{n}_draft.json",
            },
            "summary": {
                "title": "Saved Bundle Title",
                "chapter_count": 2,
                "section_names": ["manuscript", "story_summary"],
                "source_artifact_names": [
                    "story_summary.json",
                    "revised_chapter_{n}_draft.json",
                ],
                "story_bible_summary": {
                    "core_premise": "Saved premise",
                    "theme_statement": "Saved theme",
                    "ending_reveal": "Saved reveal",
                },
                "thread_summary": {
                    "thread_count": 3,
                    "resolved_thread_count": 0,
                    "unresolved_thread_count": 2,
                    "seeded_thread_count": 1,
                    "progressed_thread_count": 1,
                },
                "story_state_summary": {
                    "evaluated_through_chapter": 4,
                    "canon_chapter_count": 2,
                    "thread_count": 3,
                    "unresolved_thread_count": 2,
                    "resolved_thread_count": 1,
                    "open_question_count": 5,
                    "latest_timeline_event_count": 7,
                },
                "handoff_summary": {
                    "title": "Saved Bundle Title",
                    "selected_logline_title": "",
                    "chapter_count": 2,
                    "quality_recommendation": "unknown",
                    "issue_count": 0,
                    "synopsis": "",
                },
            },
        }

        lines = _build_publish_bundle_summary_lines(publish_ready_bundle)

        self.assertEqual(
            lines,
            [
                "publish_bundle.title: Saved Bundle Title",
                "publish_bundle.chapter_count: 2",
                "publish_bundle.section_names: manuscript, story_summary",
                "publish_bundle.source_artifact_names: story_summary.json, revised_chapter_{n}_draft.json",
                "publish_bundle.story_bible_summary: core_premise=Saved premise, theme_statement=Saved theme, ending_reveal=Saved reveal",
                "publish_bundle.thread_summary: thread_count=3, unresolved_count=2, resolved_count=0, seeded_count=1, progressed_count=1",
                "publish_bundle.story_state_summary: evaluated_through_chapter=4, canon_chapter_count=2, thread_count=3, unresolved_count=2, resolved_count=1, open_question_count=5, latest_timeline_event_count=7",
                "publish_bundle.handoff_summary: title=Saved Bundle Title, logline=, recommendation=unknown, issue_count=0, chapter_count=2",
            ],
        )

    def test_build_publish_bundle_summary_lines_backfills_missing_summary(self) -> None:
        publish_ready_bundle = {
            "title": "Fallback Bundle",
            "chapter_count": 3,
            "sections": {
                "manuscript": {"field": "chapters"},
                "quality": {"field": "overall_quality_report"},
            },
            "source_artifacts": {
                "story_summary": "story_summary.json",
                "overall_quality_report": "project_quality_report.json",
            },
        }

        lines = _build_publish_bundle_summary_lines(publish_ready_bundle)

        self.assertEqual(
            lines,
            [
                "publish_bundle.title: Fallback Bundle",
                "publish_bundle.chapter_count: 3",
                "publish_bundle.section_names: manuscript, quality",
                "publish_bundle.source_artifact_names: story_summary.json, project_quality_report.json",
            ],
        )

    def test_build_saved_publish_bundle_summary_lines_surfaces_post_backfill_validation_error(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            save_artifact(
                output_dir,
                "publish_ready_bundle",
                {
                    "schema_version": "1.0",
                    "bundle_type": "publish_ready_bundle",
                    "title": "Legacy Bundle",
                    "synopsis": "Legacy synopsis",
                    "chapter_count": 2,
                    "chapters": [],
                    "story_summary": {},
                    "overall_quality_report": {},
                    "selected_logline": {},
                    "source_artifacts": {},
                    "sections": {
                        "manuscript": {"field": "chapters"},
                        "story_summary": {"field": "story_summary"},
                        "quality": {"field": "wrong_field"},
                    },
                },
            )

            with self.assertRaisesRegex(
                ValueError,
                r"Invalid publish_ready_bundle: sections\.quality\.field='wrong_field' is not supported; expected 'overall_quality_report'\.",
            ):
                _build_saved_publish_bundle_summary_lines(output_dir)

    def test_print_run_summary_uses_saved_publish_bundle_summary(self) -> None:
        artifacts = SimpleNamespace(
            loglines=[{"title": "Selected Logline"}],
            chapter_plan=[{"chapter_number": 1}, {"chapter_number": 2}],
            continuity_report={"issue_counts": {}, "severity": "low"},
            publish_ready_bundle={
                "title": "Legacy Bundle Title",
                "chapter_count": 2,
                "sections": {
                    "manuscript": {"field": "chapters"},
                    "quality": {"field": "overall_quality_report"},
                },
                "source_artifacts": {
                    "story_summary": "story_summary.json",
                    "overall_quality_report": "project_quality_report.json",
                },
                "summary": {
                    "title": "Saved Bundle Title",
                    "chapter_count": 2,
                    "section_names": ["manuscript", "quality"],
                    "source_artifact_names": [
                        "story_summary.json",
                        "project_quality_report.json",
                    ],
                    "story_bible_summary": {
                        "core_premise": "Summary premise",
                        "ending_reveal": "Summary reveal",
                        "theme_statement": "Summary theme",
                    },
                    "thread_summary": {
                        "thread_count": 2,
                        "resolved_thread_count": 1,
                        "unresolved_thread_count": 1,
                        "seeded_thread_count": 0,
                        "progressed_thread_count": 1,
                    },
                    "story_state_summary": {
                        "evaluated_through_chapter": 3,
                        "canon_chapter_count": 2,
                        "thread_count": 2,
                        "unresolved_thread_count": 1,
                        "resolved_thread_count": 1,
                        "open_question_count": 1,
                        "latest_timeline_event_count": 4,
                    },
                    "handoff_summary": {
                        "title": "Saved Bundle Title",
                        "selected_logline_title": "Selected Logline",
                        "chapter_count": 2,
                        "quality_recommendation": "accept",
                        "issue_count": 0,
                        "synopsis": "Summary synopsis",
                    },
                },
            },
        )

        buffer = io.StringIO()
        with (
            patch("novel_writer.cli.build_run_comparison_lines", return_value=[]),
            redirect_stdout(buffer),
        ):
            print_run_summary(artifacts, Path("/tmp/publish-ready-bundle"), {})

        output = buffer.getvalue()

        self.assertIn("publish_bundle.title: Saved Bundle Title", output)
        self.assertIn("publish_bundle.section_names: manuscript, quality", output)
        self.assertIn(
            "publish_bundle.source_artifact_names: story_summary.json, project_quality_report.json",
            output,
        )
        self.assertIn(
            "publish_bundle.story_bible_summary: core_premise=Summary premise, theme_statement=Summary theme, ending_reveal=Summary reveal",
            output,
        )
        self.assertIn(
            "publish_bundle.thread_summary: thread_count=2, unresolved_count=1, resolved_count=1, seeded_count=0, progressed_count=1",
            output,
        )
        self.assertIn(
            "publish_bundle.story_state_summary: evaluated_through_chapter=3, canon_chapter_count=2, thread_count=2, unresolved_count=1, resolved_count=1, open_question_count=1, latest_timeline_event_count=4",
            output,
        )
        self.assertIn(
            "publish_bundle.handoff_summary: title=Saved Bundle Title, logline=Selected Logline, recommendation=accept, issue_count=0, chapter_count=2",
            output,
        )

    def test_cli_create_project_sets_default_autonomy_level_and_preserves_existing_value(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            first_exit_code = main(
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
                    "Case 04",
                    "--projects-dir",
                    tmp_dir,
                ]
            )

            project_dir = Path(tmp_dir) / "case-04"
            project_manifest_path = project_dir / "project_manifest.json"
            first_manifest = load_artifact(project_dir, "project_manifest")
            self.assertEqual(first_manifest["autonomy_level"], "assist")
            first_manifest["autonomy_level"] = "manual"
            project_manifest_path.write_text(
                json.dumps(first_manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            second_exit_code = main(
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
                    "Case 04",
                    "--projects-dir",
                    tmp_dir,
                    "--output-dir",
                    str(Path(tmp_dir) / "candidate-b"),
                ]
            )

            updated_manifest = load_artifact(project_dir, "project_manifest")

            self.assertEqual(first_exit_code, 0)
            self.assertEqual(second_exit_code, 0)
            self.assertEqual(updated_manifest["autonomy_level"], "manual")

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
            self.assertTrue(
                any(
                    entry.get("chapter_index") == 1
                    for entry in manifest["continuity_history"]
                )
            )
            self.assertTrue(
                any(
                    entry.get("chapter_index") == 1
                    and entry.get("triggered_by") == "manual"
                    for entry in manifest["rerun_history"]
                )
            )
            project_manifest = load_artifact(
                Path(tmp_dir) / "my-story-01", "project_manifest"
            )
            chapter_2_status = next(
                status
                for status in project_manifest["current_run"]["chapter_statuses"]
                if status["chapter_number"] == 2
            )
            self.assertEqual(chapter_2_status["chapter_index"], 1)
            self.assertEqual(
                chapter_2_status["latest_rerun_action"], "reran_chapter_draft"
            )
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
            self.assertEqual(
                project_manifest["current_run"]["output_dir"], str(second_run_dir)
            )
            self.assertIn(
                project_manifest["best_run"]["output_dir"],
                {str(first_run_dir), str(second_run_dir)},
            )
            self.assertTrue(
                all(
                    "chapter_statuses" in candidate
                    for candidate in project_manifest["run_candidates"]
                )
            )
            self.assertTrue(
                all(
                    "comparison_metrics" in candidate
                    for candidate in project_manifest["run_candidates"]
                )
            )
            self.assertTrue(
                all(
                    "comparison_basis" in candidate
                    for candidate in project_manifest["run_candidates"]
                )
            )
            self.assertTrue(
                all(
                    "comparison_reason" in candidate
                    for candidate in project_manifest["run_candidates"]
                )
            )
            self.assertTrue(
                all(
                    "long_run_status" in candidate
                    for candidate in project_manifest["run_candidates"]
                )
            )
            self.assertTrue(
                all(
                    "policy_snapshot" in candidate
                    for candidate in project_manifest["run_candidates"]
                )
            )
            self.assertIn("comparison_metrics", project_manifest["current_run"])
            self.assertIn("comparison_basis", project_manifest["current_run"])
            self.assertIn("comparison_reason", project_manifest["current_run"])
            self.assertIn("comparison_metrics", project_manifest["best_run"])
            self.assertIn("policy_snapshot", project_manifest["best_run"])
            self.assertIn("selection_reason", project_manifest["best_run"])
            self.assertIn(
                "long_run_should_stop",
                project_manifest["best_run"]["comparison_metrics"],
            )
            self.assertIn(
                "total_issue_score=",
                project_manifest["best_run"]["selection_reason"][1],
            )
            self.assertEqual(
                {
                    candidate["output_dir"]
                    for candidate in project_manifest["run_candidates"]
                },
                {str(first_run_dir), str(second_run_dir)},
            )
            self.assertEqual(
                comparison_summary["schema_name"], "run_comparison_summary"
            )
            self.assertEqual(comparison_summary["schema_version"], "1.0")
            self.assertEqual(comparison_summary["candidate_count"], 2)
            self.assertEqual(
                comparison_summary["best_run"]["output_dir"],
                project_manifest["best_run"]["output_dir"],
            )
            self.assertEqual(
                comparison_summary["current_run"]["output_dir"], str(second_run_dir)
            )
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

    def test_cli_show_project_status_surfaces_manual_review_gate_from_saved_next_action_decision(
        self,
    ) -> None:
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
                    "Manual Gate 01",
                    "--projects-dir",
                    tmp_dir,
                ]
            )

            project_dir = Path(tmp_dir) / "manual-gate-01"
            run_dir = project_dir / "runs" / "latest_run"
            project_manifest_path = project_dir / "project_manifest.json"
            project_manifest = load_artifact(project_dir, "project_manifest")
            project_manifest["autonomy_level"] = "manual"
            project_manifest_path.write_text(
                json.dumps(project_manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            save_next_action_decision(
                run_dir,
                {
                    "schema_name": "next_action_decision",
                    "schema_version": "1.0",
                    "evaluated_through_chapter": 5,
                    "story_state_summary": {
                        "evaluated_through_chapter": 5,
                        "canon_chapter_count": 5,
                        "thread_count": 0,
                        "unresolved_thread_count": 0,
                        "resolved_thread_count": 0,
                        "open_question_count": 0,
                        "latest_timeline_event_count": 0,
                    },
                    "action": "stop_for_review",
                    "reason": "manual review required",
                    "issue_codes": ["manual_review"],
                    "target_chapters": [],
                    "policy_budget": {
                        "max_high_severity_chapters": 0,
                        "max_total_rerun_attempts": 0,
                        "remaining_high_severity_chapter_budget": 0,
                        "remaining_rerun_attempt_budget": 0,
                    },
                    "decision_trace": [
                        {
                            "code": "manual_review",
                            "summary": "Manual review is required before continuing.",
                            "value": "chapter-5",
                        }
                    ],
                },
            )

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(
                    [
                        "show-project-status",
                        "--project-id",
                        "Manual Gate 01",
                        "--projects-dir",
                        tmp_dir,
                    ]
                )

            output = buffer.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("Autonomy level: manual", output)
            self.assertIn(
                "Resume gate: blocked_by_review (saved next_action_decision.action=stop_for_review)",
                output,
            )

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

            project_manifest = load_artifact(
                Path(tmp_dir) / "policy-01", "project_manifest"
            )
            policy_limits = project_manifest["current_run"]["long_run_status"][
                "policy_limits"
            ]
            policy_snapshot = project_manifest["current_run"]["policy_snapshot"]

            self.assertEqual(exit_code, 0)
            self.assertEqual(policy_limits["max_high_severity_chapters"], 2)
            self.assertEqual(policy_limits["max_total_rerun_attempts"], 7)
            self.assertEqual(
                policy_snapshot["long_run"]["max_high_severity_chapters"], 2
            )
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
            self.assertIn(
                "manual_selection=candidate-b",
                project_manifest["best_run"]["selection_reason"][0],
            )
            self.assertEqual(
                project_manifest["best_run"]["selection_reason_details"][0]["code"],
                "manual_selection",
            )
            self.assertEqual(comparison_summary["best_run"]["run_name"], "candidate-b")
            self.assertEqual(
                comparison_summary["best_run"]["selection_source"], "manual"
            )
            self.assertIn(
                "manual_selection=candidate-b",
                comparison_summary["best_run"]["selection_reason"][0],
            )
            self.assertEqual(
                comparison_summary["best_run"]["selection_reason_details"][0]["code"],
                "manual_selection",
            )

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
            self.assertIn(
                "current_comparison_reason_summary: long_run_should_stop=False",
                status_output,
            )
            self.assertIn("best_selection_source: manual", status_output)
            self.assertIn(
                "best_selection_reason_summary: manual_selection=candidate-b",
                status_output,
            )

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
            self.assertIn(
                "policy_diff.max_high_severity_chapters: current=6, best=2", output
            )
            self.assertIn("diff_summary: issue_score current=", output)
            self.assertIn(
                "diff_policy: max_high_severity_chapters current=6 best=2", output
            )

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
            current_codes = [
                detail["code"]
                for detail in comparison_summary["current_run"][
                    "comparison_reason_details"
                ][:3]
            ]
            best_codes = [
                detail["code"]
                for detail in comparison_summary["best_run"][
                    "selection_reason_details"
                ][:3]
            ]

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

    def test_build_project_status_lines_orders_reason_codes_by_schema_contract(
        self,
    ) -> None:
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

        self.assertIn(
            "  current_comparison_reason_codes: long_run_should_stop, total_issue_score",
            lines,
        )
        self.assertIn(
            "  best_selection_reason_codes: manual_selection, completed_step_count",
            lines,
        )

    def test_build_project_status_lines_prefers_machine_readable_comparison_context(
        self,
    ) -> None:
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
                "policy_snapshot": {
                    "long_run": {
                        "max_high_severity_chapters": 6,
                        "max_total_rerun_attempts": 20,
                    }
                },
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
                "policy_snapshot": {
                    "long_run": {
                        "max_high_severity_chapters": 2,
                        "max_total_rerun_attempts": 20,
                    }
                },
            },
            "run_candidates": [],
        }

        lines = build_project_status_lines(project_manifest)

        self.assertIn("  completed_steps: 12", lines)
        self.assertIn(
            "  current_comparison_reason_summary: long_run_should_stop=False; total_issue_score=11",
            lines,
        )
        self.assertIn(
            "  best_selection_reason_summary: manual_selection=candidate-a; long_run_should_stop=True",
            lines,
        )
        self.assertIn(
            "  diff_summary: issue_score current=11 best=5; completed_steps current=12 best=7; stop current=False best=True",
            lines,
        )
        self.assertNotIn("  current_comparison_reason_summary: stale_reason=yes", lines)
        self.assertNotIn("  best_selection_reason_summary: stale_selection=yes", lines)

    def test_build_project_status_lines_keeps_documented_summary_field_mapping(
        self,
    ) -> None:
        project_manifest = {
            "project_id": "Case 03",
            "project_slug": "case-03",
            "current_run": {
                "name": "latest_run",
                "output_dir": "data/projects/case-03/runs/latest_run",
                "current_step": "publish_ready_bundle",
                "chapter_statuses": [],
                "long_run_status": {},
                "comparison_basis": [
                    "long_run_should_stop",
                    "continuity_issue_total",
                    "quality_issue_total",
                ],
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
                "policy_snapshot": {
                    "long_run": {
                        "max_high_severity_chapters": 6,
                        "max_total_rerun_attempts": 20,
                    }
                },
            },
            "best_run": {
                "run_name": "candidate-a",
                "output_dir": "data/projects/case-03/runs/candidate-a",
                "score": 5,
                "comparison_basis": [
                    "long_run_should_stop",
                    "continuity_issue_total",
                    "quality_issue_total",
                ],
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
                "policy_snapshot": {
                    "long_run": {
                        "max_high_severity_chapters": 2,
                        "max_total_rerun_attempts": 20,
                    }
                },
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
            "autonomy_level": "assist",
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
                "policy_snapshot": {
                    "long_run": {
                        "max_high_severity_chapters": 6,
                        "max_total_rerun_attempts": 20,
                    }
                },
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
                "policy_snapshot": {
                    "long_run": {
                        "max_high_severity_chapters": 2,
                        "max_total_rerun_attempts": 20,
                    }
                },
            },
            "run_candidates": [{"run_name": "candidate-a"}, {"run_name": "latest_run"}],
        }

        summary = build_project_status_summary(
            project_manifest, reason_detail_mode="codes"
        )

        self.assertEqual(summary["project_label"], "case-04")
        self.assertEqual(summary["run_candidate_count"], 2)
        self.assertEqual(summary["autonomy_level"], "assist")
        self.assertEqual(summary["current_run"]["completed_steps"], 12)
        self.assertIn(
            "  current_comparison_reason_codes: long_run_should_stop, total_issue_score",
            summary["current_run"]["comparison_lines"],
        )
        self.assertEqual(summary["best_run"]["name"], "candidate-a")
        self.assertIn(
            "  best_selection_source: manual", summary["best_run"]["selection_lines"]
        )
        self.assertIn(
            "  diff_summary: issue_score current=11 best=5; completed_steps current=12 best=7; stop current=False best=True",
            summary["best_run"]["diff_lines"],
        )
        self.assertEqual(
            summary["best_run"]["comparison_metrics_line"],
            "  best_comparison_metrics: total_issue_score=5, completed_step_count=7",
        )

    def test_build_project_status_summary_defaults_missing_autonomy_level_to_assist(
        self,
    ) -> None:
        project_manifest = {
            "project_id": "Legacy 01",
            "project_slug": "legacy-01",
            "current_run": {
                "name": "latest_run",
                "output_dir": "data/projects/legacy-01/runs/latest_run",
                "current_step": "publish_ready_bundle",
                "completed_steps": ["story_input"],
                "chapter_statuses": [],
                "long_run_status": {},
                "comparison_basis": ["long_run_should_stop"],
                "comparison_reason": [],
                "comparison_metrics": {
                    "total_issue_score": 2,
                    "completed_step_count": 1,
                    "long_run_should_stop": False,
                },
                "comparison_reason_details": [
                    {"code": "long_run_should_stop", "value": False},
                    {"code": "total_issue_score", "value": 2},
                ],
                "policy_snapshot": {
                    "long_run": {
                        "max_high_severity_chapters": 6,
                        "max_total_rerun_attempts": 20,
                    }
                },
            },
            "best_run": {
                "run_name": "latest_run",
                "output_dir": "data/projects/legacy-01/runs/latest_run",
                "score": 2,
                "comparison_basis": ["long_run_should_stop"],
                "selection_source": "automatic",
                "selection_reason": [],
                "comparison_metrics": {
                    "total_issue_score": 2,
                    "completed_step_count": 1,
                    "long_run_should_stop": False,
                },
                "selection_reason_details": [
                    {"code": "long_run_should_stop", "value": False},
                    {"code": "total_issue_score", "value": 2},
                ],
                "policy_snapshot": {
                    "long_run": {
                        "max_high_severity_chapters": 6,
                        "max_total_rerun_attempts": 20,
                    }
                },
            },
            "run_candidates": [],
        }

        summary = build_project_status_summary(project_manifest)
        lines = build_project_status_lines(project_manifest)

        self.assertEqual(summary["autonomy_level"], "assist")
        self.assertIn("Autonomy level: assist", lines)

    def test_build_project_status_lines_surfaces_autonomy_level(self) -> None:
        project_manifest = {
            "project_id": "Case 06",
            "project_slug": "case-06",
            "autonomy_level": "manual",
            "current_run": {
                "name": "latest_run",
                "output_dir": "data/projects/case-06/runs/latest_run",
                "current_step": "publish_ready_bundle",
                "completed_steps": ["story_input"],
                "chapter_statuses": [],
                "long_run_status": {},
                "comparison_basis": ["long_run_should_stop"],
                "comparison_reason": [],
                "comparison_metrics": {
                    "total_issue_score": 2,
                    "completed_step_count": 1,
                    "long_run_should_stop": False,
                },
                "comparison_reason_details": [
                    {"code": "long_run_should_stop", "value": False},
                    {"code": "total_issue_score", "value": 2},
                ],
                "policy_snapshot": {
                    "long_run": {
                        "max_high_severity_chapters": 6,
                        "max_total_rerun_attempts": 20,
                    }
                },
            },
            "best_run": {
                "run_name": "latest_run",
                "output_dir": "data/projects/case-06/runs/latest_run",
                "score": 2,
                "comparison_basis": ["long_run_should_stop"],
                "selection_source": "automatic",
                "selection_reason": [],
                "comparison_metrics": {
                    "total_issue_score": 2,
                    "completed_step_count": 1,
                    "long_run_should_stop": False,
                },
                "selection_reason_details": [
                    {"code": "long_run_should_stop", "value": False},
                    {"code": "total_issue_score", "value": 2},
                ],
                "policy_snapshot": {
                    "long_run": {
                        "max_high_severity_chapters": 6,
                        "max_total_rerun_attempts": 20,
                    }
                },
            },
            "run_candidates": [],
        }

        lines = build_project_status_lines(project_manifest)

        self.assertIn("Autonomy level: manual", lines)

    def test_build_project_status_lines_surfaces_manual_stop_for_review_gate(
        self,
    ) -> None:
        project_manifest = {
            "project_id": "Case 07",
            "project_slug": "case-07",
            "autonomy_level": "manual",
            "current_run": {
                "name": "latest_run",
                "output_dir": "data/projects/case-07/runs/latest_run",
                "current_step": "publish_ready_bundle",
                "completed_steps": ["story_input"],
                "chapter_statuses": [],
                "long_run_status": {},
                "comparison_basis": ["long_run_should_stop"],
                "comparison_reason": [],
                "comparison_metrics": {
                    "total_issue_score": 2,
                    "completed_step_count": 1,
                    "long_run_should_stop": False,
                },
                "comparison_reason_details": [
                    {"code": "long_run_should_stop", "value": False},
                    {"code": "total_issue_score", "value": 2},
                ],
                "policy_snapshot": {
                    "long_run": {
                        "max_high_severity_chapters": 6,
                        "max_total_rerun_attempts": 20,
                    }
                },
            },
            "best_run": {},
            "run_candidates": [],
        }

        with patch(
            "novel_writer.cli.load_next_action_decision",
            return_value={
                "action": "stop_for_review",
                "story_state_summary": {
                    "evaluated_through_chapter": 3,
                    "canon_chapter_count": 3,
                    "thread_count": 4,
                    "unresolved_thread_count": 2,
                    "resolved_thread_count": 1,
                    "open_question_count": 5,
                    "latest_timeline_event_count": 2,
                },
            },
        ):
            lines = build_project_status_lines(project_manifest)

        self.assertIn("Resume gate: stop_for_review", lines)
        self.assertIn(
            "  saved_story_state_summary: "
            "evaluated_through_chapter=3, canon_chapter_count=3, thread_count=4, "
            "unresolved_count=2, resolved_count=1, open_question_count=5, latest_timeline_event_count=2",
            lines,
        )

    def test_build_project_status_lines_hides_gate_for_manual_non_blocking_next_action(
        self,
    ) -> None:
        project_manifest = {
            "project_id": "Case 07",
            "project_slug": "case-07",
            "autonomy_level": "manual",
            "current_run": {
                "name": "latest_run",
                "output_dir": "data/projects/case-07/runs/latest_run",
                "current_step": "publish_ready_bundle",
                "completed_steps": ["story_input"],
                "chapter_statuses": [],
                "long_run_status": {},
                "comparison_basis": ["long_run_should_stop"],
                "comparison_reason": [],
                "comparison_metrics": {
                    "total_issue_score": 2,
                    "completed_step_count": 1,
                    "long_run_should_stop": False,
                },
                "comparison_reason_details": [
                    {"code": "long_run_should_stop", "value": False},
                    {"code": "total_issue_score", "value": 2},
                ],
                "policy_snapshot": {
                    "long_run": {
                        "max_high_severity_chapters": 6,
                        "max_total_rerun_attempts": 20,
                    }
                },
            },
            "best_run": {},
            "run_candidates": [],
        }

        with patch(
            "novel_writer.cli.load_next_action_decision",
            return_value={"action": "continue"},
        ):
            lines = build_project_status_lines(project_manifest)

        self.assertNotIn("Resume gate: stop_for_review", lines)

    def test_build_project_status_lines_hides_saved_story_state_summary_when_next_action_has_no_summary(
        self,
    ) -> None:
        project_manifest = {
            "project_id": "Case 07",
            "project_slug": "case-07",
            "autonomy_level": "manual",
            "current_run": {
                "name": "latest_run",
                "output_dir": "data/projects/case-07/runs/latest_run",
                "current_step": "publish_ready_bundle",
                "completed_steps": ["story_input"],
                "chapter_statuses": [],
                "long_run_status": {},
                "comparison_basis": ["long_run_should_stop"],
                "comparison_reason": [],
                "comparison_metrics": {
                    "total_issue_score": 2,
                    "completed_step_count": 1,
                    "long_run_should_stop": False,
                },
                "comparison_reason_details": [
                    {"code": "long_run_should_stop", "value": False},
                    {"code": "total_issue_score", "value": 2},
                ],
                "policy_snapshot": {
                    "long_run": {
                        "max_high_severity_chapters": 6,
                        "max_total_rerun_attempts": 20,
                    }
                },
            },
            "best_run": {},
            "run_candidates": [],
        }

        with patch(
            "novel_writer.cli.load_next_action_decision",
            return_value={"action": "continue"},
        ):
            lines = build_project_status_lines(project_manifest)

        self.assertFalse(
            any(line.startswith("  saved_story_state_summary: ") for line in lines)
        )

    def test_build_project_status_lines_hides_gate_for_assist_projects(self) -> None:
        project_manifest = {
            "project_id": "Case 08",
            "project_slug": "case-08",
            "autonomy_level": "assist",
            "current_run": {
                "name": "latest_run",
                "output_dir": "data/projects/case-08/runs/latest_run",
                "current_step": "publish_ready_bundle",
                "completed_steps": ["story_input"],
                "chapter_statuses": [],
                "long_run_status": {},
                "comparison_basis": ["long_run_should_stop"],
                "comparison_reason": [],
                "comparison_metrics": {
                    "total_issue_score": 2,
                    "completed_step_count": 1,
                    "long_run_should_stop": False,
                },
                "comparison_reason_details": [
                    {"code": "long_run_should_stop", "value": False},
                    {"code": "total_issue_score", "value": 2},
                ],
                "policy_snapshot": {
                    "long_run": {
                        "max_high_severity_chapters": 6,
                        "max_total_rerun_attempts": 20,
                    }
                },
            },
            "best_run": {},
            "run_candidates": [],
        }

        with patch(
            "novel_writer.cli.load_next_action_decision",
            return_value={"action": "stop_for_review"},
        ):
            lines = build_project_status_lines(project_manifest)

        self.assertNotIn("Resume gate: stop_for_review", lines)

    def test_build_project_status_lines_hides_gate_when_next_action_decision_is_missing(
        self,
    ) -> None:
        project_manifest = {
            "project_id": "Case 09",
            "project_slug": "case-09",
            "autonomy_level": "manual",
            "current_run": {
                "name": "latest_run",
                "output_dir": "data/projects/case-09/runs/latest_run",
                "current_step": "publish_ready_bundle",
                "completed_steps": ["story_input"],
                "chapter_statuses": [],
                "long_run_status": {},
                "comparison_basis": ["long_run_should_stop"],
                "comparison_reason": [],
                "comparison_metrics": {
                    "total_issue_score": 2,
                    "completed_step_count": 1,
                    "long_run_should_stop": False,
                },
                "comparison_reason_details": [
                    {"code": "long_run_should_stop", "value": False},
                    {"code": "total_issue_score", "value": 2},
                ],
                "policy_snapshot": {
                    "long_run": {
                        "max_high_severity_chapters": 6,
                        "max_total_rerun_attempts": 20,
                    }
                },
            },
            "best_run": {},
            "run_candidates": [],
        }

        with patch(
            "novel_writer.cli.load_next_action_decision",
            side_effect=FileNotFoundError("missing next_action_decision"),
        ):
            lines = build_project_status_lines(project_manifest)

        self.assertNotIn("Resume gate: stop_for_review", lines)

    def test_build_resume_gate_status_line_uses_legacy_next_action_decision_without_story_state_summary(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            save_artifact(
                output_dir,
                "next_action_decision",
                {
                    "schema_name": "next_action_decision",
                    "schema_version": "1.0",
                    "evaluated_through_chapter": 3,
                    "action": "stop_for_review",
                    "reason": "manual review required",
                    "issue_codes": ["manual_review"],
                    "target_chapters": [],
                    "policy_budget": {
                        "max_high_severity_chapters": 0,
                        "max_total_rerun_attempts": 0,
                        "remaining_high_severity_chapter_budget": 0,
                        "remaining_rerun_attempt_budget": 0,
                    },
                    "decision_trace": [
                        {
                            "code": "manual_review",
                            "summary": "Manual review is required before continuing.",
                            "value": "chapter-3",
                        }
                    ],
                },
            )

            line = _build_resume_gate_status_line("manual", output_dir)

        self.assertEqual(
            line,
            "  Resume gate: blocked_by_review (saved next_action_decision.action=stop_for_review)",
        )

    def test_build_saved_story_state_summary_line_uses_legacy_next_action_decision_without_story_state_summary(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            save_artifact(
                output_dir,
                "next_action_decision",
                {
                    "schema_name": "next_action_decision",
                    "schema_version": "1.0",
                    "evaluated_through_chapter": 3,
                    "action": "stop_for_review",
                    "reason": "manual review required",
                    "issue_codes": ["manual_review"],
                    "target_chapters": [],
                    "policy_budget": {
                        "max_high_severity_chapters": 0,
                        "max_total_rerun_attempts": 0,
                        "remaining_high_severity_chapter_budget": 0,
                        "remaining_rerun_attempt_budget": 0,
                    },
                    "decision_trace": [
                        {
                            "code": "manual_review",
                            "summary": "Manual review is required before continuing.",
                            "value": "chapter-3",
                        }
                    ],
                },
            )

            line = _build_saved_story_state_summary_line(output_dir)

        self.assertIsNone(line)

    def test_build_resume_gate_status_line_raises_for_invalid_legacy_next_action_decision(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            save_artifact(
                output_dir,
                "next_action_decision",
                {
                    "schema_name": "next_action_decision",
                    "schema_version": "1.0",
                    "evaluated_through_chapter": 3,
                    "action": "invalid-action",
                    "reason": "manual review required",
                    "issue_codes": ["manual_review"],
                    "target_chapters": [],
                    "policy_budget": {
                        "max_high_severity_chapters": 0,
                        "max_total_rerun_attempts": 0,
                        "remaining_high_severity_chapter_budget": 0,
                        "remaining_rerun_attempt_budget": 0,
                    },
                    "decision_trace": [
                        {
                            "code": "manual_review",
                            "summary": "Manual review is required before continuing.",
                            "value": "chapter-3",
                        }
                    ],
                },
            )

            with self.assertRaisesRegex(ValueError, "action must be one of"):
                _build_resume_gate_status_line("manual", output_dir)

    def test_build_resume_gate_status_line_surfaces_non_summary_validation_error_for_legacy_next_action(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            save_artifact(
                output_dir,
                "next_action_decision",
                {
                    "schema_name": "next_action_decision",
                    "schema_version": "1.0",
                    "evaluated_through_chapter": 3,
                    "action": "invalid-action",
                    "reason": "manual review required",
                    "issue_codes": ["manual_review"],
                    "target_chapters": [],
                    "policy_budget": {
                        "max_high_severity_chapters": 0,
                        "max_total_rerun_attempts": 0,
                        "remaining_high_severity_chapter_budget": 0,
                        "remaining_rerun_attempt_budget": 0,
                    },
                    "decision_trace": [
                        {
                            "code": "manual_review",
                            "summary": "Manual review is required before continuing.",
                            "value": "chapter-3",
                        }
                    ],
                },
            )

            with self.assertRaisesRegex(
                ValueError,
                "Invalid next_action_decision: action must be one of: continue, revise, rerun_chapter, replan_future, stop_for_review",
            ):
                _build_resume_gate_status_line("manual", output_dir)

    def test_cli_resume_project_blocks_manual_legacy_stop_for_review_before_pipeline(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir) / "case-legacy"
            run_dir = project_dir / "runs" / "latest_run"
            run_dir.mkdir(parents=True)

            save_artifact(
                run_dir,
                "next_action_decision",
                {
                    "schema_name": "next_action_decision",
                    "schema_version": "1.0",
                    "evaluated_through_chapter": 3,
                    "action": "stop_for_review",
                    "reason": "manual review required",
                    "issue_codes": ["manual_review"],
                    "target_chapters": [],
                    "policy_budget": {
                        "max_high_severity_chapters": 0,
                        "max_total_rerun_attempts": 0,
                        "remaining_high_severity_chapter_budget": 0,
                        "remaining_rerun_attempt_budget": 0,
                    },
                    "decision_trace": [
                        {
                            "code": "manual_review",
                            "summary": "Manual review is required before continuing.",
                            "value": "chapter-3",
                        }
                    ],
                },
            )

            with (
                patch(
                    "novel_writer.cli.load_project_run_context",
                    return_value=({"project_dir": project_dir}, run_dir),
                ),
                patch(
                    "novel_writer.cli.load_project_manifest",
                    return_value={"autonomy_level": "manual"},
                ),
                patch("novel_writer.cli.run_pipeline") as run_pipeline,
                patch("novel_writer.cli.save_project_state"),
                patch("novel_writer.cli.print_run_summary"),
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    "resume-project.*manual.*stop_for_review",
                ):
                    main(
                        [
                            "resume-project",
                            "--project-id",
                            "Case Legacy",
                            "--projects-dir",
                            tmp_dir,
                        ]
                    )

            run_pipeline.assert_not_called()

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
                {
                    "run_name": "latest_run",
                    "score": 11,
                    "output_dir": "data/projects/case-05/runs/latest_run",
                },
                {
                    "run_name": "candidate-a",
                    "score": 5,
                    "output_dir": "data/projects/case-05/runs/candidate-a",
                },
            ],
        }

        summary = build_saved_run_comparison_summary(
            summary_artifact, reason_detail_mode="codes"
        )
        lines = build_saved_run_comparison_lines(
            summary_artifact, reason_detail_mode="codes"
        )

        self.assertEqual(summary["project_label"], "case-05")
        self.assertEqual(summary["candidate_count"], 2)
        self.assertEqual(
            summary["run_candidates"]["names"], ["latest_run", "candidate-a"]
        )
        self.assertEqual(
            summary["run_candidates"]["scores"], ["latest_run=11", "candidate-a=5"]
        )
        self.assertEqual(
            summary["run_candidates"]["output_dirs"],
            [
                "latest_run=data/projects/case-05/runs/latest_run",
                "candidate-a=data/projects/case-05/runs/candidate-a",
            ],
        )
        self.assertEqual(
            summary["current_run"]["output_dir"],
            "data/projects/case-05/runs/latest_run",
        )
        self.assertEqual(
            summary["best_run"]["output_dir"], "data/projects/case-05/runs/candidate-a"
        )
        self.assertEqual(
            summary["current_run"]["comparison_metrics"]["total_issue_score"], 11
        )
        self.assertEqual(
            summary["best_run"]["comparison_metrics"]["total_issue_score"], 5
        )
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
        self.assertIn(
            "  run_candidate_names: latest_run, candidate-a",
            summary["run_candidates"]["lines"],
        )
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
        self.assertEqual(
            summary["best_run"]["selection_summary"]["selection_source"], "manual"
        )
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
        self.assertIn(
            "  best_selection_source: manual",
            summary["best_run"]["selection_summary"]["lines"],
        )
        self.assertEqual(summary["compact_summary"]["selection_source"], "manual")
        self.assertEqual(
            summary["compact_summary"]["issue_score"], {"current": 11, "best": 5}
        )
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
        self.assertIn(
            "  compact.policy_limits.max_high_severity_chapters: current=6, best=2",
            lines,
        )
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
                "comparison_basis": [
                    "long_run_should_stop",
                    "continuity_issue_total",
                    "quality_issue_total",
                ],
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
                "comparison_basis": [
                    "long_run_should_stop",
                    "continuity_issue_total",
                    "quality_issue_total",
                ],
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
                {
                    "run_name": "latest_run",
                    "score": 11,
                    "output_dir": "data/projects/case-06/runs/latest_run",
                },
                {
                    "run_name": "candidate-a",
                    "score": 5,
                    "output_dir": "data/projects/case-06/runs/candidate-a",
                },
            ],
        }

        lines = build_saved_run_comparison_lines(
            summary_artifact, reason_detail_mode="codes"
        )
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
                {
                    "run_name": "latest_run",
                    "score": 11,
                    "output_dir": "data/projects/case-07/runs/latest_run",
                },
                {
                    "run_name": "candidate-a",
                    "score": 5,
                    "output_dir": "data/projects/case-07/runs/candidate-a",
                },
            ],
        }

        lines = build_saved_run_comparison_lines(
            summary_artifact, reason_detail_mode="codes"
        )

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

        lines = build_saved_run_comparison_lines(
            summary_artifact, reason_detail_mode="codes"
        )

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
            publish_ready_bundle = {
                "schema_name": "publish_ready_bundle",
                "schema_version": "1.0",
                "bundle_type": "publish_ready_bundle",
                "title": "Saved Publish Bundle Title",
                "synopsis": "Saved synopsis for the read-only CLI path.",
                "chapter_count": 2,
                "chapters": [
                    {"chapter_number": 1, "title": "Chapter 1"},
                    {"chapter_number": 2, "title": "Chapter 2"},
                ],
                "sections": {
                    "manuscript": {"field": "chapters"},
                    "story_summary": {"field": "story_summary"},
                    "quality": {"field": "overall_quality_report"},
                },
                "source_artifacts": {
                    "story_summary": "story_summary.json",
                    "overall_quality_report": "project_quality_report.json",
                    "chapters": "revised_chapter_{n}_draft.json",
                },
                "story_summary": {
                    "schema_name": "story_summary",
                    "schema_version": "1.0",
                    "chapter_count": 2,
                },
                "overall_quality_report": {
                    "schema_name": "project_quality_report",
                    "schema_version": "1.0",
                },
                "selected_logline": {"id": "logline-1", "title": "Selected logline"},
                "summary": {
                    "title": "Saved Publish Bundle Title",
                    "chapter_count": 2,
                    "section_names": ["manuscript", "story_summary"],
                    "source_artifact_names": [
                        "story_summary.json",
                        "revised_chapter_{n}_draft.json",
                    ],
                },
            }
            save_publish_ready_bundle(
                project_dir / "runs" / "latest_run", publish_ready_bundle
            )
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
            self.assertIn("run_candidate_scores: latest_run=13", output)
            self.assertIn("run_candidate_output_dirs: latest_run=", output)
            self.assertIn("publish_bundle.title: Saved Publish Bundle Title", output)
            self.assertIn(
                "publish_bundle.section_names: manuscript, story_summary", output
            )
            self.assertIn(
                "publish_bundle.source_artifact_names: story_summary.json, revised_chapter_{n}_draft.json",
                output,
            )
            self.assertNotIn("publish_bundle.title: Case Bundle", output)

    def test_cli_show_run_comparison_backfills_legacy_publish_bundle_without_summary(
        self,
    ) -> None:
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
                    "Compare Legacy 01",
                    "--projects-dir",
                    tmp_dir,
                ]
            )

            project_dir = Path(tmp_dir) / "compare-legacy-01"
            run_dir = project_dir / "runs" / "latest_run"
            save_artifact(
                run_dir,
                "publish_ready_bundle",
                {
                    "schema_name": "publish_ready_bundle",
                    "schema_version": "1.0",
                    "bundle_type": "publish_ready_bundle",
                    "title": "Legacy Publish Bundle Title",
                    "synopsis": "Saved synopsis for the read-only CLI path.",
                    "chapter_count": 2,
                    "chapters": [
                        {"chapter_number": 1, "title": "Chapter 1"},
                        {"chapter_number": 2, "title": "Chapter 2"},
                    ],
                    "sections": {
                        "manuscript": {"field": "chapters"},
                        "story_summary": {"field": "story_summary"},
                        "quality": {"field": "overall_quality_report"},
                    },
                    "source_artifacts": {
                        "story_summary": "story_summary.json",
                        "overall_quality_report": "project_quality_report.json",
                        "chapters": "revised_chapter_{n}_draft.json",
                    },
                    "story_summary": {
                        "schema_name": "story_summary",
                        "schema_version": "1.0",
                        "chapter_count": 2,
                    },
                    "overall_quality_report": {
                        "schema_name": "project_quality_report",
                        "schema_version": "1.0",
                    },
                    "selected_logline": {
                        "id": "logline-1",
                        "title": "Selected logline",
                    },
                },
            )
            comparison_before = load_artifact(project_dir, "run_comparison_summary")

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(
                    [
                        "show-run-comparison",
                        "--project-id",
                        "Compare Legacy 01",
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
            self.assertIn("publish_bundle.title: Legacy Publish Bundle Title", output)
            self.assertIn("publish_bundle.chapter_count: 2", output)
            self.assertIn(
                "publish_bundle.section_names: manuscript, story_summary, quality",
                output,
            )
            self.assertIn(
                "publish_bundle.source_artifact_names: story_summary.json, project_quality_report.json, revised_chapter_{n}_draft.json",
                output,
            )
            self.assertIn(
                "publish_bundle.story_state_summary: evaluated_through_chapter=3, canon_chapter_count=3, thread_count=2, unresolved_count=2, resolved_count=0, open_question_count=6, latest_timeline_event_count=1",
                output,
            )
            self.assertNotIn("publish_bundle.summary:", output)

    def test_cli_show_run_comparison_fails_fast_for_invalid_schema_version(
        self,
    ) -> None:
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
                    "Compare Invalid Schema 01",
                    "--projects-dir",
                    tmp_dir,
                ]
            )

            project_dir = Path(tmp_dir) / "compare-invalid-schema-01"
            run_dir = project_dir / "runs" / "latest_run"
            save_artifact(
                run_dir,
                "publish_ready_bundle",
                {
                    "schema_name": "publish_ready_bundle",
                    "schema_version": "2.0",
                    "bundle_type": "publish_ready_bundle",
                    "title": "Broken Publish Bundle Title",
                    "synopsis": "Saved synopsis for the read-only CLI path.",
                    "chapter_count": 2,
                    "chapters": [
                        {"chapter_number": 1, "title": "Chapter 1"},
                        {"chapter_number": 2, "title": "Chapter 2"},
                    ],
                    "sections": {
                        "manuscript": {"field": "chapters"},
                        "story_summary": {"field": "story_summary"},
                        "quality": {"field": "overall_quality_report"},
                    },
                    "source_artifacts": {
                        "story_summary": "story_summary.json",
                        "overall_quality_report": "project_quality_report.json",
                        "chapters": "revised_chapter_{n}_draft.json",
                    },
                    "story_summary": {
                        "schema_name": "story_summary",
                        "schema_version": "1.0",
                        "chapter_count": 2,
                    },
                    "overall_quality_report": {
                        "schema_name": "project_quality_report",
                        "schema_version": "1.0",
                    },
                    "selected_logline": {
                        "id": "logline-1",
                        "title": "Selected logline",
                    },
                },
            )

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                with self.assertRaisesRegex(
                    ValueError, r"schema_version='2\.0' is not supported"
                ):
                    main(
                        [
                            "show-run-comparison",
                            "--project-id",
                            "Compare Invalid Schema 01",
                            "--projects-dir",
                            tmp_dir,
                            "--reason-detail-mode",
                            "codes",
                        ]
                    )

            self.assertEqual(buffer.getvalue(), "")

    def test_cli_show_run_comparison_fails_fast_for_invalid_sections_shape(
        self,
    ) -> None:
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
                    "Compare Invalid Sections 01",
                    "--projects-dir",
                    tmp_dir,
                ]
            )

            project_dir = Path(tmp_dir) / "compare-invalid-sections-01"
            run_dir = project_dir / "runs" / "latest_run"
            save_artifact(
                run_dir,
                "publish_ready_bundle",
                {
                    "schema_name": "publish_ready_bundle",
                    "schema_version": "1.0",
                    "bundle_type": "publish_ready_bundle",
                    "title": "Broken Publish Bundle Title",
                    "synopsis": "Saved synopsis for the read-only CLI path.",
                    "chapter_count": 2,
                    "chapters": [
                        {"chapter_number": 1, "title": "Chapter 1"},
                        {"chapter_number": 2, "title": "Chapter 2"},
                    ],
                    "sections": {
                        "manuscript": "broken",
                        "story_summary": {"field": "story_summary"},
                        "quality": {"field": "overall_quality_report"},
                    },
                    "source_artifacts": {
                        "story_summary": "story_summary.json",
                        "overall_quality_report": "project_quality_report.json",
                        "chapters": "revised_chapter_{n}_draft.json",
                    },
                    "story_summary": {
                        "schema_name": "story_summary",
                        "schema_version": "1.0",
                        "chapter_count": 2,
                    },
                    "overall_quality_report": {
                        "schema_name": "project_quality_report",
                        "schema_version": "1.0",
                    },
                    "selected_logline": {
                        "id": "logline-1",
                        "title": "Selected logline",
                    },
                },
            )

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                with self.assertRaisesRegex(
                    ValueError, r"sections\.manuscript must be an object"
                ):
                    main(
                        [
                            "show-run-comparison",
                            "--project-id",
                            "Compare Invalid Sections 01",
                            "--projects-dir",
                            tmp_dir,
                            "--reason-detail-mode",
                            "codes",
                        ]
                    )

            self.assertEqual(buffer.getvalue(), "")

    def test_cli_show_run_comparison_reads_minimal_valid_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir) / "compare-optional-01"
            run_dir = project_dir / "runs" / "latest_run"
            project_dir.mkdir(parents=True, exist_ok=True)
            comparison_payload = {
                "schema_name": "run_comparison_summary",
                "schema_version": "1.0",
                "project_id": "Compare Optional 01",
                "project_slug": "compare-optional-01",
                "current_run": {
                    "run_name": "latest_run",
                    "output_dir": str(run_dir),
                    "comparison_basis": ["long_run_should_stop"],
                    "comparison_metrics": {
                        "total_issue_score": 3,
                        "completed_step_count": 4,
                    },
                    "comparison_reason": [],
                    "comparison_reason_details": [
                        {"code": "total_issue_score", "value": 3},
                    ],
                },
                "best_run": {
                    "run_name": "latest_run",
                    "output_dir": str(run_dir),
                    "selection_source": "automatic",
                    "comparison_basis": ["long_run_should_stop"],
                    "comparison_metrics": {
                        "total_issue_score": 3,
                        "completed_step_count": 4,
                    },
                    "selection_reason": [],
                    "selection_reason_details": [
                        {"code": "total_issue_score", "value": 3},
                    ],
                },
                "candidate_count": 0,
                "compact_summary": {
                    "selection_source": "automatic",
                    "issue_score": {"current": 3, "best": 3},
                    "completed_step_count": {"current": 4, "best": 4},
                    "long_run_should_stop": {"current": False, "best": False},
                    "policy_limits": {
                        "max_high_severity_chapters": {"current": 10, "best": 10},
                        "max_total_rerun_attempts": {"current": 20, "best": 20},
                    },
                },
                "run_candidates": [],
            }
            save_publish_ready_bundle(
                run_dir,
                {
                    "schema_version": "1.0",
                    "bundle_type": "publish_ready_bundle",
                    "title": "Compare Optional 01 Bundle",
                    "synopsis": "Saved synopsis for the read-only CLI path.",
                    "chapter_count": 1,
                    "chapters": [{"chapter_number": 1, "title": "Chapter 1"}],
                    "sections": {
                        "manuscript": {"field": "chapters"},
                        "story_summary": {"field": "story_summary"},
                        "quality": {"field": "overall_quality_report"},
                    },
                    "source_artifacts": {
                        "story_summary": "story_summary.json",
                        "overall_quality_report": "project_quality_report.json",
                        "chapters": "revised_chapter_{n}_draft.json",
                    },
                    "story_summary": {},
                    "overall_quality_report": {},
                    "selected_logline": {
                        "id": "logline-1",
                        "title": "Selected logline",
                    },
                    "summary": {
                        "title": "Compare Optional 01 Bundle",
                        "chapter_count": 1,
                        "section_names": ["manuscript", "story_summary", "quality"],
                        "source_artifact_names": [
                            "story_summary.json",
                            "project_quality_report.json",
                            "revised_chapter_{n}_draft.json",
                        ],
                    },
                },
            )
            save_run_comparison_summary(project_dir, comparison_payload)
            comparison_before = load_artifact(project_dir, "run_comparison_summary")

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = main(
                    [
                        "show-run-comparison",
                        "--project-id",
                        "Compare Optional 01",
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
            self.assertIn("Project: compare-optional-01", output)
            self.assertIn("Current run: latest_run", output)
            self.assertIn("current_comparison_reason_codes: total_issue_score", output)
            self.assertIn(
                "current_comparison_metrics: total_issue_score=3, completed_step_count=4",
                output,
            )
            self.assertIn("Best run: latest_run", output)
            self.assertIn("best_selection_source: automatic", output)
            self.assertIn("best_selection_reason_codes: total_issue_score", output)
            self.assertIn(
                "best_comparison_metrics: total_issue_score=3, completed_step_count=4",
                output,
            )
            self.assertIn("Compact summary: selection_source=automatic", output)
            self.assertIn("compact.issue_score: current=3, best=3", output)
            self.assertIn("compact.completed_step_count: current=4, best=4", output)
            self.assertIn(
                "compact.long_run_should_stop: current=False, best=False", output
            )
            self.assertIn("Run candidates: 0", output)
            self.assertNotIn("run_candidate_names:", output)
            self.assertNotIn("run_candidate_scores:", output)
            self.assertNotIn("run_candidate_output_dirs:", output)
            self.assertIn("publish_bundle.title: Compare Optional 01 Bundle", output)

    def test_cli_show_run_comparison_fails_when_publish_bundle_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir) / "compare-missing-bundle-01"
            run_dir = project_dir / "runs" / "latest_run"
            run_dir.mkdir(parents=True, exist_ok=True)
            comparison_payload = {
                "schema_name": "run_comparison_summary",
                "schema_version": "1.0",
                "project_id": "Compare Missing Bundle 01",
                "project_slug": "compare-missing-bundle-01",
                "current_run": {
                    "run_name": "latest_run",
                    "output_dir": str(run_dir),
                    "comparison_basis": ["long_run_should_stop"],
                    "comparison_metrics": {
                        "total_issue_score": 3,
                        "completed_step_count": 4,
                    },
                    "comparison_reason": [],
                    "comparison_reason_details": [
                        {"code": "total_issue_score", "value": 3},
                    ],
                },
                "best_run": {
                    "run_name": "latest_run",
                    "output_dir": str(run_dir),
                    "selection_source": "automatic",
                    "comparison_basis": ["long_run_should_stop"],
                    "comparison_metrics": {
                        "total_issue_score": 3,
                        "completed_step_count": 4,
                    },
                    "selection_reason": [],
                    "selection_reason_details": [
                        {"code": "total_issue_score", "value": 3},
                    ],
                },
                "candidate_count": 0,
                "compact_summary": {
                    "selection_source": "automatic",
                    "issue_score": {"current": 3, "best": 3},
                    "completed_step_count": {"current": 4, "best": 4},
                    "long_run_should_stop": {"current": False, "best": False},
                    "policy_limits": {
                        "max_high_severity_chapters": {"current": 10, "best": 10},
                        "max_total_rerun_attempts": {"current": 20, "best": 20},
                    },
                },
                "run_candidates": [],
            }
            save_run_comparison_summary(project_dir, comparison_payload)

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                with self.assertRaisesRegex(
                    FileNotFoundError,
                    r"Artifact not found for phase 'publish_ready_bundle'",
                ):
                    main(
                        [
                            "show-run-comparison",
                            "--project-id",
                            "Compare Missing Bundle 01",
                            "--projects-dir",
                            tmp_dir,
                            "--reason-detail-mode",
                            "codes",
                        ]
                    )

            self.assertEqual(buffer.getvalue(), "")

    def test_cli_show_project_status_surfaces_saved_story_state_summary_from_best_run(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir) / "best-run-status-01"
            current_run_dir = project_dir / "runs" / "latest_run"
            best_run_dir = project_dir / "runs" / "candidate-a"
            current_run_dir.mkdir(parents=True)
            best_run_dir.mkdir(parents=True)
            save_next_action_decision(
                best_run_dir,
                {
                    "schema_name": "next_action_decision",
                    "schema_version": "1.0",
                    "evaluated_through_chapter": 9,
                    "story_state_summary": {
                        "evaluated_through_chapter": 9,
                        "canon_chapter_count": 9,
                        "thread_count": 4,
                        "unresolved_thread_count": 2,
                        "resolved_thread_count": 2,
                        "open_question_count": 1,
                        "latest_timeline_event_count": 8,
                    },
                    "action": "continue",
                    "reason": "best run snapshot",
                    "issue_codes": [],
                    "target_chapters": [],
                    "policy_budget": {
                        "max_high_severity_chapters": 0,
                        "max_total_rerun_attempts": 0,
                        "remaining_high_severity_chapter_budget": 0,
                        "remaining_rerun_attempt_budget": 0,
                    },
                    "decision_trace": [],
                },
            )

            lines = build_project_status_lines(
                {
                    "project_id": "Best Run Status 01",
                    "project_slug": "best-run-status-01",
                    "autonomy_level": "manual",
                    "current_run": {
                        "name": "latest_run",
                        "output_dir": str(current_run_dir),
                        "current_step": "publish_ready_bundle",
                        "completed_steps": ["story_input"],
                        "chapter_statuses": [],
                        "long_run_status": {},
                        "comparison_basis": ["long_run_should_stop"],
                        "comparison_reason": [],
                        "comparison_metrics": {
                            "total_issue_score": 2,
                            "completed_step_count": 1,
                            "long_run_should_stop": False,
                        },
                        "comparison_reason_details": [
                            {"code": "long_run_should_stop", "value": False}
                        ],
                        "policy_snapshot": {
                            "long_run": {
                                "max_high_severity_chapters": 6,
                                "max_total_rerun_attempts": 20,
                            }
                        },
                    },
                    "best_run": {
                        "run_name": "candidate-a",
                        "output_dir": str(best_run_dir),
                    },
                    "run_candidates": [],
                }
            )

        self.assertIn("Best run: candidate-a", lines)
        self.assertIn(
            "  saved_story_state_summary: evaluated_through_chapter=9, canon_chapter_count=9, thread_count=4, unresolved_count=2, resolved_count=2, open_question_count=1, latest_timeline_event_count=8",
            lines,
        )

    def test_build_saved_story_state_summary_line_uses_best_run_next_action_decision_summary(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            best_run_dir = Path(tmp_dir) / "candidate-a"
            save_next_action_decision(
                best_run_dir,
                {
                    "schema_name": "next_action_decision",
                    "schema_version": "1.0",
                    "evaluated_through_chapter": 4,
                    "story_state_summary": {
                        "evaluated_through_chapter": 4,
                        "canon_chapter_count": 4,
                        "thread_count": 1,
                        "unresolved_thread_count": 0,
                        "resolved_thread_count": 1,
                        "open_question_count": 0,
                        "latest_timeline_event_count": 3,
                    },
                    "action": "continue",
                    "reason": "best run snapshot",
                    "issue_codes": [],
                    "target_chapters": [],
                    "policy_budget": {
                        "max_high_severity_chapters": 0,
                        "max_total_rerun_attempts": 0,
                        "remaining_high_severity_chapter_budget": 0,
                        "remaining_rerun_attempt_budget": 0,
                    },
                    "decision_trace": [],
                },
            )

            line = _build_saved_story_state_summary_line(best_run_dir)

        self.assertEqual(
            line,
            "  saved_story_state_summary: evaluated_through_chapter=4, canon_chapter_count=4, thread_count=1, unresolved_count=0, resolved_count=1, open_question_count=0, latest_timeline_event_count=3",
        )

    def test_build_project_status_lines_omits_saved_story_state_summary_when_next_action_decision_is_missing(
        self,
    ) -> None:
        project_manifest = {
            "project_id": "Case 09",
            "project_slug": "case-09",
            "autonomy_level": "manual",
            "current_run": {
                "name": "latest_run",
                "output_dir": "data/projects/case-09/runs/latest_run",
                "current_step": "publish_ready_bundle",
                "completed_steps": ["story_input"],
                "chapter_statuses": [],
                "long_run_status": {},
                "comparison_basis": ["long_run_should_stop"],
                "comparison_reason": [],
                "comparison_metrics": {
                    "total_issue_score": 2,
                    "completed_step_count": 1,
                    "long_run_should_stop": False,
                },
                "comparison_reason_details": [
                    {"code": "long_run_should_stop", "value": False}
                ],
                "policy_snapshot": {
                    "long_run": {
                        "max_high_severity_chapters": 6,
                        "max_total_rerun_attempts": 20,
                    }
                },
            },
            "best_run": {},
            "run_candidates": [],
        }

        with patch(
            "novel_writer.cli.load_next_action_decision",
            side_effect=FileNotFoundError("missing next_action_decision"),
        ):
            lines = build_project_status_lines(project_manifest)

        self.assertFalse(
            any(line.startswith("  saved_story_state_summary: ") for line in lines)
        )

    def test_build_saved_story_state_summary_line_omits_legacy_next_action_decision_without_story_state_summary(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            save_artifact(
                output_dir,
                "next_action_decision",
                {
                    "schema_name": "next_action_decision",
                    "schema_version": "1.0",
                    "evaluated_through_chapter": 3,
                    "action": "stop_for_review",
                    "reason": "manual review required",
                    "issue_codes": ["manual_review"],
                    "target_chapters": [],
                    "policy_budget": {
                        "max_high_severity_chapters": 0,
                        "max_total_rerun_attempts": 0,
                        "remaining_high_severity_chapter_budget": 0,
                        "remaining_rerun_attempt_budget": 0,
                    },
                    "decision_trace": [],
                },
            )

            line = _build_saved_story_state_summary_line(output_dir)

        self.assertIsNone(line)

    def test_build_run_comparison_lines_surfaces_saved_story_state_snapshots_for_current_and_best_runs(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir) / "compare-snapshot-01"
            current_run_dir = project_dir / "runs" / "latest_run"
            best_run_dir = project_dir / "runs" / "candidate-a"
            current_run_dir.mkdir(parents=True)
            best_run_dir.mkdir(parents=True)
            save_next_action_decision(
                current_run_dir,
                {
                    "schema_name": "next_action_decision",
                    "schema_version": "1.0",
                    "evaluated_through_chapter": 8,
                    "story_state_summary": {
                        "evaluated_through_chapter": 8,
                        "canon_chapter_count": 8,
                        "thread_count": 3,
                        "unresolved_thread_count": 1,
                        "resolved_thread_count": 2,
                        "open_question_count": 4,
                        "latest_timeline_event_count": 6,
                    },
                    "action": "continue",
                    "reason": "current snapshot",
                    "issue_codes": [],
                    "target_chapters": [],
                    "policy_budget": {
                        "max_high_severity_chapters": 0,
                        "max_total_rerun_attempts": 0,
                        "remaining_high_severity_chapter_budget": 0,
                        "remaining_rerun_attempt_budget": 0,
                    },
                    "decision_trace": [],
                },
            )
            save_next_action_decision(
                best_run_dir,
                {
                    "schema_name": "next_action_decision",
                    "schema_version": "1.0",
                    "evaluated_through_chapter": 9,
                    "story_state_summary": {
                        "evaluated_through_chapter": 9,
                        "canon_chapter_count": 9,
                        "thread_count": 4,
                        "unresolved_thread_count": 2,
                        "resolved_thread_count": 2,
                        "open_question_count": 1,
                        "latest_timeline_event_count": 8,
                    },
                    "action": "continue",
                    "reason": "best snapshot",
                    "issue_codes": [],
                    "target_chapters": [],
                    "policy_budget": {
                        "max_high_severity_chapters": 0,
                        "max_total_rerun_attempts": 0,
                        "remaining_high_severity_chapter_budget": 0,
                        "remaining_rerun_attempt_budget": 0,
                    },
                    "decision_trace": [],
                },
            )

            summary_artifact = {
                "project_id": "Compare Snapshot 01",
                "project_slug": "compare-snapshot-01",
                "candidate_count": 2,
                "current_run": {
                    "run_name": "latest_run",
                    "output_dir": str(current_run_dir),
                    "comparison_basis": [],
                    "comparison_metrics": {},
                    "comparison_reason_details": [],
                },
                "best_run": {
                    "run_name": "candidate-a",
                    "output_dir": str(best_run_dir),
                    "selection_source": "manual",
                    "comparison_basis": [],
                    "comparison_metrics": {},
                    "selection_reason_details": [],
                },
                "compact_summary": {
                    "selection_source": "manual",
                    "issue_score": {"current": 0, "best": 0},
                    "completed_step_count": {"current": 0, "best": 0},
                    "long_run_should_stop": {"current": False, "best": False},
                    "policy_limits": {
                        "max_high_severity_chapters": {"current": 0, "best": 0},
                        "max_total_rerun_attempts": {"current": 0, "best": 0},
                    },
                },
                "run_candidates": [],
            }

            lines = build_saved_run_comparison_lines(
                summary_artifact, reason_detail_mode="codes"
            )

        self.assertIn(
            "  saved_story_state_summary: evaluated_through_chapter=8, canon_chapter_count=8, thread_count=3, unresolved_count=1, resolved_count=2, open_question_count=4, latest_timeline_event_count=6",
            lines,
        )
        self.assertIn(
            "  saved_story_state_summary: evaluated_through_chapter=9, canon_chapter_count=9, thread_count=4, unresolved_count=2, resolved_count=2, open_question_count=1, latest_timeline_event_count=8",
            lines,
        )

    def test_build_run_comparison_lines_omits_saved_story_state_snapshots_when_next_action_decision_is_missing(
        self,
    ) -> None:
        summary_artifact = {
            "project_id": "Compare Snapshot 02",
            "project_slug": "compare-snapshot-02",
            "candidate_count": 2,
            "current_run": {
                "run_name": "latest_run",
                "output_dir": "data/projects/compare-snapshot-02/runs/latest_run",
                "comparison_basis": [],
                "comparison_metrics": {},
                "comparison_reason_details": [],
            },
            "best_run": {
                "run_name": "candidate-a",
                "output_dir": "data/projects/compare-snapshot-02/runs/candidate-a",
                "selection_source": "manual",
                "comparison_basis": [],
                "comparison_metrics": {},
                "selection_reason_details": [],
            },
            "compact_summary": {
                "selection_source": "manual",
                "issue_score": {"current": 0, "best": 0},
                "completed_step_count": {"current": 0, "best": 0},
                "long_run_should_stop": {"current": False, "best": False},
                "policy_limits": {
                    "max_high_severity_chapters": {"current": 0, "best": 0},
                    "max_total_rerun_attempts": {"current": 0, "best": 0},
                },
            },
            "run_candidates": [],
        }

        with patch(
            "novel_writer.cli.load_next_action_decision",
            side_effect=FileNotFoundError("missing next_action_decision"),
        ):
            lines = build_saved_run_comparison_lines(
                summary_artifact, reason_detail_mode="codes"
            )

        self.assertFalse(any("saved_story_state_summary:" in line for line in lines))

    def test_build_run_comparison_lines_fails_fast_for_invalid_non_summary_next_action_decision(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            current_run_dir = Path(tmp_dir) / "current"
            best_run_dir = Path(tmp_dir) / "best"
            current_run_dir.mkdir()
            best_run_dir.mkdir()
            save_artifact(
                best_run_dir,
                "next_action_decision",
                {
                    "schema_name": "next_action_decision",
                    "schema_version": "1.0",
                    "evaluated_through_chapter": 3,
                    "action": "invalid-action",
                    "reason": "manual review required",
                    "issue_codes": ["manual_review"],
                    "target_chapters": [],
                    "policy_budget": {
                        "max_high_severity_chapters": 0,
                        "max_total_rerun_attempts": 0,
                        "remaining_high_severity_chapter_budget": 0,
                        "remaining_rerun_attempt_budget": 0,
                    },
                    "decision_trace": [],
                },
            )

            summary_artifact = {
                "project_id": "Compare Snapshot 03",
                "project_slug": "compare-snapshot-03",
                "candidate_count": 2,
                "current_run": {
                    "run_name": "latest_run",
                    "output_dir": str(current_run_dir),
                    "comparison_basis": [],
                    "comparison_metrics": {},
                    "comparison_reason_details": [],
                },
                "best_run": {
                    "run_name": "candidate-a",
                    "output_dir": str(best_run_dir),
                    "selection_source": "manual",
                    "comparison_basis": [],
                    "comparison_metrics": {},
                    "selection_reason_details": [],
                },
                "compact_summary": {
                    "selection_source": "manual",
                    "issue_score": {"current": 0, "best": 0},
                    "completed_step_count": {"current": 0, "best": 0},
                    "long_run_should_stop": {"current": False, "best": False},
                    "policy_limits": {
                        "max_high_severity_chapters": {"current": 0, "best": 0},
                        "max_total_rerun_attempts": {"current": 0, "best": 0},
                    },
                },
                "run_candidates": [],
            }

            with self.assertRaisesRegex(ValueError, "action must be one of"):
                build_saved_run_comparison_lines(
                    summary_artifact, reason_detail_mode="codes"
                )


if __name__ == "__main__":
    unittest.main()
