import json
import importlib.util
import tempfile
import unittest
from pathlib import Path

from novel_writer.storage import (
    build_project_layout,
    load_artifact,
    load_project_manifest,
    load_publish_ready_bundle,
    load_run_comparison_summary,
    normalize_project_id,
    resolve_artifact_path,
    save_artifact,
    save_publish_ready_bundle,
    save_project_manifest,
    save_run_comparison_summary,
)


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
            "artifact_contract": {
                "chapter_artifacts": {
                    "canonical_story_state": {
                        "chapter_drafts": {
                            "primary_collection": "chapter_drafts",
                            "compatibility_artifact": "05_chapter_1_draft",
                        }
                    }
                },
                "publish_ready_bundle": {"schema_version": "1.0"},
            },
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
            self.assertEqual(
                saved["artifact_contract"]["chapter_artifacts"]["canonical_story_state"]["chapter_drafts"]["compatibility_artifact"],
                "05_chapter_1_draft",
            )
            self.assertEqual(saved["artifact_contract"]["publish_ready_bundle"]["schema_version"], "1.0")
            self.assertEqual(len(saved["artifacts"]["chapter_drafts"]), 3)
            self.assertEqual(len(saved["artifacts"]["revised_chapter_drafts"]), 3)
            self.assertEqual(saved["artifacts"]["chapter_drafts"][0], saved["artifacts"]["chapter_1_draft"])
            self.assertEqual(
                saved["artifacts"]["revised_chapter_drafts"][0],
                saved["artifacts"]["revised_chapter_1_draft"],
            )

    def test_load_artifact_reads_json_without_explicit_format(self) -> None:
        payload = {"phase": "chapter_plan", "items": [{"chapter_number": 1}, {"chapter_number": 2}]}

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_artifact(Path(tmp_dir), "04_chapter_plan", payload, "json")

            loaded = load_artifact(Path(tmp_dir), "04_chapter_plan")

            self.assertEqual(loaded, payload)

    @unittest.skipUnless(importlib.util.find_spec("yaml"), "PyYAML is not installed")
    def test_load_artifact_reads_yaml_with_explicit_format(self) -> None:
        payload = {"severity": "medium", "issue_counts": {"plan_to_draft_gaps": 1}}

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_artifact(Path(tmp_dir), "continuity_report", payload, "yaml")

            loaded = load_artifact(Path(tmp_dir), "continuity_report", "yaml")

            self.assertEqual(loaded, payload)

    def test_resolve_artifact_path_prefers_existing_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_artifact(Path(tmp_dir), "manifest", {"ok": True}, "json")

            resolved = resolve_artifact_path(Path(tmp_dir), "manifest")

            self.assertEqual(resolved.name, "manifest.json")

    def test_load_artifact_raises_for_missing_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaises(FileNotFoundError):
                load_artifact(Path(tmp_dir), "missing_phase")

    def test_normalize_project_id_slugifies_input(self) -> None:
        self.assertEqual(normalize_project_id("My Story 01"), "my-story-01")

    def test_build_project_layout_returns_project_scoped_paths(self) -> None:
        layout = build_project_layout(Path("data/projects"), "My Story 01")

        self.assertEqual(layout["project_slug"], "my-story-01")
        self.assertEqual(layout["project_dir"], Path("data/projects") / "my-story-01")
        self.assertEqual(layout["run_dir"], Path("data/projects") / "my-story-01" / "runs" / "latest_run")

    def test_save_project_manifest_uses_project_directory(self) -> None:
        payload = {
            "project_id": "My Story 01",
            "project_slug": "my-story-01",
            "projects_dir": "data/projects",
            "current_run": {"name": "latest_run"},
            "run_candidates": [{"run_name": "latest_run", "output_dir": "data/projects/my-story-01/runs/latest_run"}],
            "best_run": {"run_name": "latest_run", "output_dir": "data/projects/my-story-01/runs/latest_run", "score": 0},
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            target = save_project_manifest(Path(tmp_dir), "My Story 01", payload, "json")
            saved = json.loads(target.read_text(encoding="utf-8"))

            self.assertEqual(target, Path(tmp_dir) / "my-story-01" / "project_manifest.json")
            self.assertEqual(saved["project_id"], payload["project_id"])
            self.assertEqual(saved["schema_name"], "project_manifest")
            self.assertEqual(saved["schema_version"], "1.0")

    def test_load_project_manifest_validates_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir) / "case-01"
            save_artifact(
                project_dir,
                "project_manifest",
                {
                    "schema_name": "project_manifest",
                    "schema_version": "1.0",
                    "project_id": "Case 01",
                    "project_slug": "case-01",
                    "projects_dir": str(Path(tmp_dir)),
                    "best_run": {},
                },
                "json",
            )

            with self.assertRaisesRegex(ValueError, "missing required fields: current_run, run_candidates"):
                load_project_manifest(project_dir)

    def test_load_project_manifest_rejects_unsupported_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir) / "case-01"
            save_artifact(
                project_dir,
                "project_manifest",
                {
                    "schema_name": "project_manifest",
                    "schema_version": "9.9",
                    "project_id": "Case 01",
                    "project_slug": "case-01",
                    "projects_dir": str(Path(tmp_dir)),
                    "current_run": {"name": "latest_run"},
                    "run_candidates": [],
                    "best_run": {},
                },
                "json",
            )

            with self.assertRaisesRegex(ValueError, "schema_version='9.9' is not supported; expected '1.0'"):
                load_project_manifest(project_dir)

    def test_save_publish_ready_bundle_validates_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(ValueError, "missing required fields: chapters, sections"):
                save_publish_ready_bundle(
                    Path(tmp_dir),
                    {
                        "schema_version": "1.0",
                        "bundle_type": "publish_ready_bundle",
                        "title": "Case 01",
                        "synopsis": "Synopsis",
                        "chapter_count": 1,
                        "story_summary": {},
                        "overall_quality_report": {},
                        "selected_logline": {},
                        "source_artifacts": {},
                    },
                )

    def test_load_publish_ready_bundle_rejects_unsupported_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_artifact(
                Path(tmp_dir),
                "publish_ready_bundle",
                {
                    "schema_version": "9.9",
                    "bundle_type": "publish_ready_bundle",
                    "title": "Case 01",
                    "synopsis": "Synopsis",
                    "chapter_count": 1,
                    "chapters": [],
                    "story_summary": {},
                    "overall_quality_report": {},
                    "selected_logline": {},
                    "source_artifacts": {},
                    "sections": {},
                },
                "json",
            )

            with self.assertRaisesRegex(ValueError, "schema_version='9.9' is not supported; expected '1.0'"):
                load_publish_ready_bundle(Path(tmp_dir))

    def test_load_publish_ready_bundle_rejects_invalid_sections_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_artifact(
                Path(tmp_dir),
                "publish_ready_bundle",
                {
                    "schema_version": "1.0",
                    "bundle_type": "publish_ready_bundle",
                    "title": "Case 01",
                    "synopsis": "Synopsis",
                    "chapter_count": 1,
                    "chapters": [],
                    "story_summary": {},
                    "overall_quality_report": {},
                    "selected_logline": {},
                    "source_artifacts": {},
                    "sections": {
                        "manuscript": {"field": "wrong_field"},
                        "story_summary": {"field": "story_summary"},
                        "quality": {"field": "overall_quality_report"},
                    },
                },
                "json",
            )

            with self.assertRaisesRegex(ValueError, "sections.manuscript.field='wrong_field' is not supported"):
                load_publish_ready_bundle(Path(tmp_dir))

    def test_save_run_comparison_summary_validates_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(ValueError, "missing required fields: best_run, candidate_count"):
                save_run_comparison_summary(
                    Path(tmp_dir),
                    {
                        "schema_name": "run_comparison_summary",
                        "schema_version": "1.0",
                        "project_id": "Case 01",
                        "project_slug": "case-01",
                        "current_run": {"run_name": "latest_run"},
                        "run_candidates": [],
                    },
                )

    def test_load_run_comparison_summary_rejects_unsupported_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_artifact(
                Path(tmp_dir),
                "run_comparison_summary",
                {
                    "schema_name": "run_comparison_summary",
                    "schema_version": "9.9",
                    "project_id": "Case 01",
                    "project_slug": "case-01",
                    "current_run": {"run_name": "latest_run"},
                    "best_run": {"run_name": "latest_run"},
                    "candidate_count": 1,
                    "compact_summary": {
                        "selection_source": "automatic",
                        "issue_score": {"current": 1, "best": 1},
                        "completed_step_count": {"current": 1, "best": 1},
                        "long_run_should_stop": {"current": False, "best": False},
                        "policy_limits": {
                            "max_high_severity_chapters": {"current": 10, "best": 10},
                            "max_total_rerun_attempts": {"current": 20, "best": 20},
                        },
                    },
                    "run_candidates": [],
                },
                "json",
            )

            with self.assertRaisesRegex(ValueError, "schema_version='9.9' is not supported; expected '1.0'"):
                load_run_comparison_summary(Path(tmp_dir))

    def test_load_run_comparison_summary_rejects_invalid_compact_summary_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_artifact(
                Path(tmp_dir),
                "run_comparison_summary",
                {
                    "schema_name": "run_comparison_summary",
                    "schema_version": "1.0",
                    "project_id": "Case 01",
                    "project_slug": "case-01",
                    "current_run": {
                        "run_name": "latest_run",
                        "output_dir": str(Path(tmp_dir) / "latest_run"),
                        "comparison_metrics": {},
                        "comparison_basis": [],
                        "comparison_reason": [],
                        "comparison_reason_details": [],
                    },
                    "best_run": {
                        "run_name": "latest_run",
                        "output_dir": str(Path(tmp_dir) / "latest_run"),
                        "comparison_metrics": {},
                        "comparison_basis": [],
                        "selection_source": "automatic",
                        "selection_reason": [],
                        "selection_reason_details": [],
                    },
                    "candidate_count": 1,
                    "compact_summary": {
                        "selection_source": "automatic",
                        "issue_score": {"current": 1},
                        "completed_step_count": {"current": 1, "best": 1},
                        "long_run_should_stop": {"current": False, "best": False},
                        "policy_limits": {
                            "max_high_severity_chapters": {"current": 10, "best": 10},
                            "max_total_rerun_attempts": {"current": 20, "best": 20},
                        },
                    },
                    "run_candidates": [],
                },
                "json",
            )

            with self.assertRaisesRegex(
                ValueError,
                r"compact_summary\.issue_score is missing fields: best",
            ):
                load_run_comparison_summary(Path(tmp_dir))

    def test_load_run_comparison_summary_rejects_missing_current_run_comparison_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_artifact(
                Path(tmp_dir),
                "run_comparison_summary",
                {
                    "schema_name": "run_comparison_summary",
                    "schema_version": "1.0",
                    "project_id": "Case 01",
                    "project_slug": "case-01",
                    "current_run": {
                        "run_name": "latest_run",
                        "output_dir": str(Path(tmp_dir) / "latest_run"),
                        "comparison_metrics": {},
                        "comparison_basis": [],
                    },
                    "best_run": {
                        "run_name": "latest_run",
                        "output_dir": str(Path(tmp_dir) / "latest_run"),
                        "comparison_metrics": {},
                        "comparison_basis": [],
                        "selection_source": "automatic",
                        "selection_reason": [],
                        "selection_reason_details": [],
                    },
                    "candidate_count": 1,
                    "compact_summary": {
                        "selection_source": "automatic",
                        "issue_score": {"current": 1, "best": 1},
                        "completed_step_count": {"current": 1, "best": 1},
                        "long_run_should_stop": {"current": False, "best": False},
                        "policy_limits": {
                            "max_high_severity_chapters": {"current": 10, "best": 10},
                            "max_total_rerun_attempts": {"current": 20, "best": 20},
                        },
                    },
                    "run_candidates": [],
                },
                "json",
            )

            with self.assertRaisesRegex(
                ValueError,
                r"current_run is missing fields: comparison_reason",
            ):
                load_run_comparison_summary(Path(tmp_dir))

    def test_load_run_comparison_summary_rejects_missing_best_run_selection_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_artifact(
                Path(tmp_dir),
                "run_comparison_summary",
                {
                    "schema_name": "run_comparison_summary",
                    "schema_version": "1.0",
                    "project_id": "Case 01",
                    "project_slug": "case-01",
                    "current_run": {
                        "run_name": "latest_run",
                        "output_dir": str(Path(tmp_dir) / "latest_run"),
                        "comparison_metrics": {},
                        "comparison_basis": [],
                        "comparison_reason": [],
                        "comparison_reason_details": [],
                    },
                    "best_run": {
                        "run_name": "latest_run",
                        "output_dir": str(Path(tmp_dir) / "latest_run"),
                        "comparison_metrics": {},
                        "comparison_basis": [],
                        "selection_reason": [],
                    },
                    "candidate_count": 1,
                    "compact_summary": {
                        "selection_source": "automatic",
                        "issue_score": {"current": 1, "best": 1},
                        "completed_step_count": {"current": 1, "best": 1},
                        "long_run_should_stop": {"current": False, "best": False},
                        "policy_limits": {
                            "max_high_severity_chapters": {"current": 10, "best": 10},
                            "max_total_rerun_attempts": {"current": 20, "best": 20},
                        },
                    },
                    "run_candidates": [],
                },
                "json",
            )

            with self.assertRaisesRegex(
                ValueError,
                r"best_run is missing fields: selection_source",
            ):
                load_run_comparison_summary(Path(tmp_dir))

    def test_load_run_comparison_summary_rejects_invalid_reason_detail_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_artifact(
                Path(tmp_dir),
                "run_comparison_summary",
                {
                    "schema_name": "run_comparison_summary",
                    "schema_version": "1.0",
                    "project_id": "Case 01",
                    "project_slug": "case-01",
                    "current_run": {
                        "run_name": "latest_run",
                        "output_dir": str(Path(tmp_dir) / "latest_run"),
                        "comparison_metrics": {},
                        "comparison_basis": [],
                        "comparison_reason": [],
                        "comparison_reason_details": [{"value": 1}],
                    },
                    "best_run": {
                        "run_name": "latest_run",
                        "output_dir": str(Path(tmp_dir) / "latest_run"),
                        "comparison_metrics": {},
                        "comparison_basis": [],
                        "selection_source": "automatic",
                        "selection_reason": [],
                        "selection_reason_details": [],
                    },
                    "candidate_count": 1,
                    "compact_summary": {
                        "selection_source": "automatic",
                        "issue_score": {"current": 1, "best": 1},
                        "completed_step_count": {"current": 1, "best": 1},
                        "long_run_should_stop": {"current": False, "best": False},
                        "policy_limits": {
                            "max_high_severity_chapters": {"current": 10, "best": 10},
                            "max_total_rerun_attempts": {"current": 20, "best": 20},
                        },
                    },
                    "run_candidates": [],
                },
                "json",
            )

            with self.assertRaisesRegex(
                ValueError,
                r"current_run\.comparison_reason_details\[0\] is missing fields: code",
            ):
                load_run_comparison_summary(Path(tmp_dir))

    def test_load_run_comparison_summary_rejects_invalid_run_candidate_reason_details(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_artifact(
                Path(tmp_dir),
                "run_comparison_summary",
                {
                    "schema_name": "run_comparison_summary",
                    "schema_version": "1.0",
                    "project_id": "Case 01",
                    "project_slug": "case-01",
                    "current_run": {
                        "run_name": "latest_run",
                        "output_dir": str(Path(tmp_dir) / "latest_run"),
                        "comparison_metrics": {},
                        "comparison_basis": [],
                        "comparison_reason": [],
                        "comparison_reason_details": [],
                    },
                    "best_run": {
                        "run_name": "latest_run",
                        "output_dir": str(Path(tmp_dir) / "latest_run"),
                        "comparison_metrics": {},
                        "comparison_basis": [],
                        "selection_source": "automatic",
                        "selection_reason": [],
                        "selection_reason_details": [],
                    },
                    "candidate_count": 1,
                    "compact_summary": {
                        "selection_source": "automatic",
                        "issue_score": {"current": 1, "best": 1},
                        "completed_step_count": {"current": 1, "best": 1},
                        "long_run_should_stop": {"current": False, "best": False},
                        "policy_limits": {
                            "max_high_severity_chapters": {"current": 10, "best": 10},
                            "max_total_rerun_attempts": {"current": 20, "best": 20},
                        },
                    },
                    "run_candidates": [
                        {
                            "run_name": "latest_run",
                            "output_dir": str(Path(tmp_dir) / "latest_run"),
                            "comparison_metrics": {},
                            "comparison_basis": [],
                            "comparison_reason": [],
                        }
                    ],
                },
                "json",
            )

            with self.assertRaisesRegex(
                ValueError,
                r"run_candidates\[0\] is missing fields: comparison_reason_details",
            ):
                load_run_comparison_summary(Path(tmp_dir))

    def test_load_run_comparison_summary_rejects_unknown_reason_detail_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_artifact(
                Path(tmp_dir),
                "run_comparison_summary",
                {
                    "schema_name": "run_comparison_summary",
                    "schema_version": "1.0",
                    "project_id": "Case 01",
                    "project_slug": "case-01",
                    "current_run": {
                        "run_name": "latest_run",
                        "output_dir": str(Path(tmp_dir) / "latest_run"),
                        "comparison_metrics": {},
                        "comparison_basis": [],
                        "comparison_reason": [],
                        "comparison_reason_details": [{"code": "unknown_reason", "value": 1}],
                    },
                    "best_run": {
                        "run_name": "latest_run",
                        "output_dir": str(Path(tmp_dir) / "latest_run"),
                        "comparison_metrics": {},
                        "comparison_basis": [],
                        "selection_source": "automatic",
                        "selection_reason": [],
                        "selection_reason_details": [],
                    },
                    "candidate_count": 1,
                    "compact_summary": {
                        "selection_source": "automatic",
                        "issue_score": {"current": 1, "best": 1},
                        "completed_step_count": {"current": 1, "best": 1},
                        "long_run_should_stop": {"current": False, "best": False},
                        "policy_limits": {
                            "max_high_severity_chapters": {"current": 10, "best": 10},
                            "max_total_rerun_attempts": {"current": 20, "best": 20},
                        },
                    },
                    "run_candidates": [],
                },
                "json",
            )

            with self.assertRaisesRegex(
                ValueError,
                r"current_run\.comparison_reason_details\[0\]\.code='unknown_reason' is not supported",
            ):
                load_run_comparison_summary(Path(tmp_dir))


if __name__ == "__main__":
    unittest.main()
