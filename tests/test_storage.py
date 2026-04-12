import json
import importlib.util
import tempfile
import unittest
from pathlib import Path

from novel_writer.schema import StoryArtifacts, StoryInput
from novel_writer.storage import (
    apply_replan_updates,
    build_project_layout,
    load_artifact,
    load_canon_ledger,
    load_chapter_handoff_packet,
    load_chapter_briefs,
    load_progress_report,
    load_replan_history,
    load_scene_cards,
    load_project_manifest,
    load_publish_ready_bundle,
    load_next_action_decision,
    load_run_comparison_summary,
    load_story_bible,
    load_thread_registry,
    normalize_project_id,
    resolve_artifact_path,
    save_artifact,
    save_canon_ledger,
    save_chapter_handoff_packet,
    save_chapter_briefs,
    save_progress_report,
    save_replan_history,
    save_scene_cards,
    save_publish_ready_bundle,
    save_project_manifest,
    save_run_comparison_summary,
    save_story_bible,
    save_next_action_decision,
    save_thread_registry,
    upsert_canon_ledger_chapter,
    upsert_replan_history_entry,
    upsert_thread_registry_entry,
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
            "current_run": {
                "name": "latest_run",
                "output_dir": "data/projects/my-story-01/runs/latest_run",
                "comparison_metrics": {},
                "comparison_basis": [],
                "comparison_reason": [],
                "comparison_reason_details": [],
            },
            "run_candidates": [
                {
                    "run_name": "latest_run",
                    "output_dir": "data/projects/my-story-01/runs/latest_run",
                    "comparison_metrics": {},
                    "comparison_basis": [],
                    "comparison_reason": [],
                    "comparison_reason_details": [],
                }
            ],
            "best_run": {
                "run_name": "latest_run",
                "output_dir": "data/projects/my-story-01/runs/latest_run",
                "score": 0,
                "comparison_metrics": {},
                "comparison_basis": [],
                "selection_source": "automatic",
                "selection_reason": [],
                "selection_reason_details": [],
            },
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            target = save_project_manifest(Path(tmp_dir), "My Story 01", payload, "json")
            saved = json.loads(target.read_text(encoding="utf-8"))

            self.assertEqual(target, Path(tmp_dir) / "my-story-01" / "project_manifest.json")
            self.assertEqual(saved["project_id"], payload["project_id"])
            self.assertEqual(saved["schema_name"], "project_manifest")
            self.assertEqual(saved["schema_version"], "1.0")
            self.assertEqual(saved["autonomy_level"], "assist")

    def test_save_project_manifest_defaults_autonomy_level_to_assist(self) -> None:
        payload = {
            "project_id": "My Story 01",
            "project_slug": "my-story-01",
            "projects_dir": "data/projects",
            "current_run": {
                "name": "latest_run",
                "output_dir": "data/projects/my-story-01/runs/latest_run",
                "comparison_metrics": {},
                "comparison_basis": [],
                "comparison_reason": [],
                "comparison_reason_details": [],
            },
            "run_candidates": [
                {
                    "run_name": "latest_run",
                    "output_dir": "data/projects/my-story-01/runs/latest_run",
                    "comparison_metrics": {},
                    "comparison_basis": [],
                    "comparison_reason": [],
                    "comparison_reason_details": [],
                }
            ],
            "best_run": {
                "run_name": "latest_run",
                "output_dir": "data/projects/my-story-01/runs/latest_run",
                "score": 0,
                "comparison_metrics": {},
                "comparison_basis": [],
                "selection_source": "automatic",
                "selection_reason": [],
                "selection_reason_details": [],
            },
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            target = save_project_manifest(Path(tmp_dir), "My Story 01", payload, "json")
            saved = json.loads(target.read_text(encoding="utf-8"))

            self.assertEqual(saved["autonomy_level"], "assist")

    def test_save_project_manifest_preserves_existing_autonomy_level_when_omitted(self) -> None:
        base_payload = {
            "project_id": "My Story 01",
            "project_slug": "my-story-01",
            "projects_dir": "data/projects",
            "current_run": {
                "name": "latest_run",
                "output_dir": "data/projects/my-story-01/runs/latest_run",
                "comparison_metrics": {},
                "comparison_basis": [],
                "comparison_reason": [],
                "comparison_reason_details": [],
            },
            "run_candidates": [
                {
                    "run_name": "latest_run",
                    "output_dir": "data/projects/my-story-01/runs/latest_run",
                    "comparison_metrics": {},
                    "comparison_basis": [],
                    "comparison_reason": [],
                    "comparison_reason_details": [],
                }
            ],
            "best_run": {
                "run_name": "latest_run",
                "output_dir": "data/projects/my-story-01/runs/latest_run",
                "score": 0,
                "comparison_metrics": {},
                "comparison_basis": [],
                "selection_source": "automatic",
                "selection_reason": [],
                "selection_reason_details": [],
            },
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            project_dir = Path(tmp_dir)
            initial_payload = dict(base_payload)
            initial_payload["autonomy_level"] = "manual"
            save_project_manifest(project_dir, "My Story 01", initial_payload, "json")

            updated_payload = dict(base_payload)
            target = save_project_manifest(project_dir, "My Story 01", updated_payload, "json")
            saved = json.loads(target.read_text(encoding="utf-8"))

            self.assertEqual(saved["autonomy_level"], "manual")

    def test_save_story_bible_validates_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(ValueError, "missing required fields: ending_reveal, forbidden_facts"):
                save_story_bible(
                    Path(tmp_dir),
                    {
                        "schema_name": "story_bible",
                        "schema_version": "1.0",
                        "core_premise": "記憶を失うたびに未来が書き換わる。",
                        "theme_statement": "喪失の先でも選び直せる。",
                        "character_arcs": [],
                        "world_rules": [],
                        "foreshadowing_seeds": [],
                    },
                )

    def test_save_chapter_briefs_validates_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(ValueError, "missing required fields: conflict, turn"):
                save_chapter_briefs(
                    Path(tmp_dir),
                    [
                        {
                            "chapter_number": 1,
                            "purpose": "導入",
                            "goal": "主人公に異変を認識させる",
                            "must_include": ["壊れた腕時計"],
                            "continuity_dependencies": [],
                            "foreshadowing_targets": [],
                            "arc_progress": "受け身の維持",
                            "target_length_guidance": "標準",
                        }
                    ],
                )

    def test_save_chapter_briefs_round_trips_valid_payload(self) -> None:
        payload = [
            {
                "chapter_number": 1,
                "purpose": "導入",
                "goal": "主人公に異変を認識させる",
                "conflict": "記憶の欠落が広がる",
                "turn": "壊れた腕時計が異常反応する",
                "must_include": ["壊れた腕時計"],
                "continuity_dependencies": ["第1話の違和感"],
                "foreshadowing_targets": ["黒幕の手がかり"],
                "arc_progress": "受け身の維持",
                "target_length_guidance": "標準",
            }
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            target = save_chapter_briefs(Path(tmp_dir), payload, "json")
            loaded = load_chapter_briefs(Path(tmp_dir))

            self.assertEqual(target.name, "chapter_briefs.json")
            self.assertEqual(loaded, payload)

    def test_save_canon_ledger_validates_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(ValueError, "chapters\\[0\\] is missing required fields: timeline_events"):
                save_canon_ledger(
                    Path(tmp_dir),
                    {
                        "schema_name": "canon_ledger",
                        "schema_version": "1.0",
                        "chapters": [
                            {
                                "chapter_number": 1,
                                "new_facts": ["主人公は腕時計の逆回転を見た。"],
                                "changed_facts": [],
                                "open_questions": ["なぜ時計が逆回転したのか。"],
                            }
                        ],
                    },
                )

    def test_save_canon_ledger_round_trips_valid_payload(self) -> None:
        payload = {
            "schema_name": "canon_ledger",
            "schema_version": "1.0",
            "chapters": [
                {
                    "chapter_number": 1,
                    "new_facts": ["主人公は腕時計の逆回転を見た。"],
                    "changed_facts": ["相棒への不信感が芽生えた。"],
                    "open_questions": ["なぜ時計が逆回転したのか。"],
                    "timeline_events": ["放課後の駅前で異変が発生した。"],
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            target = save_canon_ledger(Path(tmp_dir), payload, "json")
            loaded = load_canon_ledger(Path(tmp_dir))

            self.assertEqual(target.name, "canon_ledger.json")
            self.assertEqual(loaded, payload)

    def test_save_thread_registry_validates_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(ValueError, "threads\\[0\\] is missing required fields: notes"):
                save_thread_registry(
                    Path(tmp_dir),
                    {
                        "schema_name": "thread_registry",
                        "schema_version": "1.0",
                        "threads": [
                            {
                                "thread_id": "watch-mystery",
                                "label": "壊れた腕時計の謎",
                                "status": "seeded",
                                "introduced_in_chapter": 1,
                                "last_updated_in_chapter": 1,
                                "related_characters": ["ミナト"],
                            }
                        ],
                    },
                )

    def test_save_thread_registry_round_trips_valid_payload(self) -> None:
        payload = {
            "schema_name": "thread_registry",
            "schema_version": "1.0",
            "threads": [
                {
                    "thread_id": "watch-mystery",
                    "label": "壊れた腕時計の謎",
                    "status": "seeded",
                    "introduced_in_chapter": 1,
                    "last_updated_in_chapter": 1,
                    "related_characters": ["ミナト"],
                    "notes": ["駅前で逆回転が初登場した。"],
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            target = save_thread_registry(Path(tmp_dir), payload, "json")
            loaded = load_thread_registry(Path(tmp_dir))

            self.assertEqual(target.name, "thread_registry.json")
            self.assertEqual(loaded, payload)

    def test_upsert_thread_registry_entry_creates_new_registry_when_missing(self) -> None:
        thread_payload = {
            "thread_id": "watch-mystery",
            "label": "壊れた腕時計の謎",
            "status": "seeded",
            "introduced_in_chapter": 1,
            "last_updated_in_chapter": 1,
            "related_characters": ["ミナト"],
            "notes": ["駅前で逆回転が初登場した。"],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            target = upsert_thread_registry_entry(Path(tmp_dir), thread_payload)
            loaded = load_thread_registry(Path(tmp_dir))

            self.assertEqual(target.name, "thread_registry.json")
            self.assertEqual(
                loaded,
                {
                    "schema_name": "thread_registry",
                    "schema_version": "1.0",
                    "threads": [thread_payload],
                },
            )

    def test_upsert_thread_registry_entry_appends_new_thread(self) -> None:
        first_thread = {
            "thread_id": "watch-mystery",
            "label": "壊れた腕時計の謎",
            "status": "seeded",
            "introduced_in_chapter": 1,
            "last_updated_in_chapter": 1,
            "related_characters": ["ミナト"],
            "notes": ["駅前で逆回転が初登場した。"],
        }
        second_thread = {
            "thread_id": "partner-secret",
            "label": "相棒の沈黙",
            "status": "progressed",
            "introduced_in_chapter": 2,
            "last_updated_in_chapter": 2,
            "related_characters": ["ミナト", "相棒"],
            "notes": ["教室で証言が食い違った。"],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_thread_registry(
                Path(tmp_dir),
                {
                    "schema_name": "thread_registry",
                    "schema_version": "1.0",
                    "threads": [first_thread],
                },
            )

            upsert_thread_registry_entry(Path(tmp_dir), second_thread)
            loaded = load_thread_registry(Path(tmp_dir))

            self.assertEqual(loaded["threads"], [first_thread, second_thread])

    def test_upsert_thread_registry_entry_replaces_existing_thread(self) -> None:
        original_thread = {
            "thread_id": "watch-mystery",
            "label": "壊れた腕時計の謎",
            "status": "seeded",
            "introduced_in_chapter": 1,
            "last_updated_in_chapter": 1,
            "related_characters": ["ミナト"],
            "notes": ["駅前で逆回転が初登場した。"],
        }
        updated_thread = {
            "thread_id": "watch-mystery",
            "label": "壊れた腕時計の謎",
            "status": "progressed",
            "introduced_in_chapter": 1,
            "last_updated_in_chapter": 3,
            "related_characters": ["ミナト", "相棒"],
            "notes": ["教室の会話で矛盾が増えた。"],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_thread_registry(
                Path(tmp_dir),
                {
                    "schema_name": "thread_registry",
                    "schema_version": "1.0",
                    "threads": [original_thread],
                },
            )

            upsert_thread_registry_entry(Path(tmp_dir), updated_thread)
            loaded = load_thread_registry(Path(tmp_dir))

            self.assertEqual(loaded["threads"], [updated_thread])

    def test_upsert_thread_registry_entry_rejects_invalid_chapter_order(self) -> None:
        original_thread = {
            "thread_id": "watch-mystery",
            "label": "壊れた腕時計の謎",
            "status": "progressed",
            "introduced_in_chapter": 1,
            "last_updated_in_chapter": 3,
            "related_characters": ["ミナト", "相棒"],
            "notes": ["教室の会話で矛盾が増えた。"],
        }
        invalid_update = {
            "thread_id": "watch-mystery",
            "label": "壊れた腕時計の謎",
            "status": "resolved",
            "introduced_in_chapter": 1,
            "last_updated_in_chapter": 0,
            "related_characters": ["ミナト"],
            "notes": ["真相が明かされた。"],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_thread_registry(
                Path(tmp_dir),
                {
                    "schema_name": "thread_registry",
                    "schema_version": "1.0",
                    "threads": [original_thread],
                },
            )

            with self.assertRaisesRegex(
                ValueError,
                "thread_payload\\.last_updated_in_chapter must be greater than or equal to introduced_in_chapter",
            ):
                upsert_thread_registry_entry(Path(tmp_dir), invalid_update)

    def test_upsert_canon_ledger_chapter_creates_new_ledger_when_missing(self) -> None:
        chapter_payload = {
            "chapter_number": 1,
            "new_facts": ["主人公は腕時計の逆回転を見た。"],
            "changed_facts": [],
            "open_questions": ["なぜ時計が逆回転したのか。"],
            "timeline_events": ["放課後の駅前で異変が発生した。"],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            target = upsert_canon_ledger_chapter(Path(tmp_dir), chapter_payload)
            loaded = load_canon_ledger(Path(tmp_dir))

            self.assertEqual(target.name, "canon_ledger.json")
            self.assertEqual(
                loaded,
                {
                    "schema_name": "canon_ledger",
                    "schema_version": "1.0",
                    "chapters": [chapter_payload],
                },
            )

    def test_upsert_canon_ledger_chapter_appends_next_chapter(self) -> None:
        first_chapter = {
            "chapter_number": 1,
            "new_facts": ["主人公は腕時計の逆回転を見た。"],
            "changed_facts": [],
            "open_questions": ["なぜ時計が逆回転したのか。"],
            "timeline_events": ["放課後の駅前で異変が発生した。"],
        }
        second_chapter = {
            "chapter_number": 2,
            "new_facts": ["相棒が逆回転を目撃していないと判明した。"],
            "changed_facts": ["主人公は相棒を疑い始めた。"],
            "open_questions": ["相棒は何を隠しているのか。"],
            "timeline_events": ["翌朝の教室で食い違いが表面化した。"],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_canon_ledger(
                Path(tmp_dir),
                {
                    "schema_name": "canon_ledger",
                    "schema_version": "1.0",
                    "chapters": [first_chapter],
                },
            )

            upsert_canon_ledger_chapter(Path(tmp_dir), second_chapter)
            loaded = load_canon_ledger(Path(tmp_dir))

            self.assertEqual(loaded["chapters"], [first_chapter, second_chapter])

    def test_upsert_canon_ledger_chapter_replaces_existing_chapter(self) -> None:
        original_chapter = {
            "chapter_number": 1,
            "new_facts": ["主人公は腕時計の逆回転を見た。"],
            "changed_facts": [],
            "open_questions": ["なぜ時計が逆回転したのか。"],
            "timeline_events": ["放課後の駅前で異変が発生した。"],
        }
        updated_chapter = {
            "chapter_number": 1,
            "new_facts": ["主人公は腕時計の逆回転と停止を見た。"],
            "changed_facts": ["主人公は異変を偶然ではないと判断した。"],
            "open_questions": ["誰が時計を止めたのか。"],
            "timeline_events": ["放課後の駅前で時計が一度停止した。"],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_canon_ledger(
                Path(tmp_dir),
                {
                    "schema_name": "canon_ledger",
                    "schema_version": "1.0",
                    "chapters": [original_chapter],
                },
            )

            upsert_canon_ledger_chapter(Path(tmp_dir), updated_chapter)
            loaded = load_canon_ledger(Path(tmp_dir))

            self.assertEqual(loaded["chapters"], [updated_chapter])

    def test_upsert_canon_ledger_chapter_rejects_non_sequential_append(self) -> None:
        first_chapter = {
            "chapter_number": 1,
            "new_facts": ["主人公は腕時計の逆回転を見た。"],
            "changed_facts": [],
            "open_questions": ["なぜ時計が逆回転したのか。"],
            "timeline_events": ["放課後の駅前で異変が発生した。"],
        }
        skipped_chapter = {
            "chapter_number": 3,
            "new_facts": ["相棒が沈黙した。"],
            "changed_facts": [],
            "open_questions": ["第2章で何が起きたのか。"],
            "timeline_events": ["深夜の屋上で対話が途切れた。"],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_canon_ledger(
                Path(tmp_dir),
                {
                    "schema_name": "canon_ledger",
                    "schema_version": "1.0",
                    "chapters": [first_chapter],
                },
            )

            with self.assertRaisesRegex(ValueError, "chapter_number 3 cannot be appended after existing chapter 1"):
                upsert_canon_ledger_chapter(Path(tmp_dir), skipped_chapter)

    def test_story_artifacts_summary_includes_chapter_briefs_and_scene_cards(self) -> None:
        artifacts = StoryArtifacts(
            story_input=StoryInput(theme="記憶", genre="SF", tone="静か", target_length=120),
            chapter_plan=[{"chapter_number": 1}, {"chapter_number": 2}],
            chapter_briefs=[{"chapter_number": 1}, {"chapter_number": 2}],
            scene_cards=[{"chapter_number": 1, "scenes": []}, {"chapter_number": 2, "scenes": []}],
            chapter_drafts=[{"chapter_number": 1}, {"chapter_number": 2}],
            revised_chapter_drafts=[{"chapter_number": 1}],
        )

        summary = artifacts.summary()

        self.assertEqual(
            summary["phases"],
            [
                "story_input",
                "loglines",
                "characters",
                "three_act_plot",
                "story_bible",
                "chapter_plan",
                "chapter_briefs",
                "scene_cards",
                "chapter_drafts",
                "continuity_report",
                "quality_report",
                "revised_chapter_drafts",
                "story_summary",
                "project_quality_report",
                "progress_report",
                "publish_ready_bundle",
            ],
        )
        self.assertEqual(summary["counts"]["chapters"], 2)
        self.assertEqual(summary["counts"]["chapter_briefs"], 2)
        self.assertEqual(summary["counts"]["scene_cards"], 2)
        self.assertEqual(summary["counts"]["chapter_drafts"], 2)
        self.assertEqual(summary["counts"]["revised_chapter_drafts"], 1)

    def test_story_artifacts_contract_includes_canon_ledger(self) -> None:
        artifacts = StoryArtifacts(
            story_input=StoryInput(theme="記憶", genre="SF", tone="静か", target_length=120),
        )

        contract = artifacts.artifact_contract()

        self.assertEqual(contract["canon_ledger"]["schema_name"], "canon_ledger")
        self.assertEqual(contract["canon_ledger"]["schema_version"], "1.0")
        self.assertEqual(contract["chapter_handoff_packet"]["schema_name"], "chapter_handoff_packet")
        self.assertEqual(contract["chapter_handoff_packet"]["schema_version"], "1.0")
        self.assertEqual(contract["next_action_decision"]["schema_name"], "next_action_decision")
        self.assertEqual(contract["next_action_decision"]["schema_version"], "1.0")
        self.assertEqual(contract["progress_report"]["schema_name"], "progress_report")
        self.assertEqual(contract["progress_report"]["schema_version"], "1.0")
        self.assertEqual(contract["replan_history"]["schema_name"], "replan_history")
        self.assertEqual(contract["replan_history"]["schema_version"], "1.0")
        self.assertEqual(contract["thread_registry"]["schema_name"], "thread_registry")
        self.assertEqual(contract["thread_registry"]["schema_version"], "1.0")

    def test_save_progress_report_round_trips_valid_payload(self) -> None:
        payload = {
            "schema_name": "progress_report",
            "schema_version": "1.0",
            "evaluated_through_chapter": 5,
            "checks": {
                "chapter_role_coverage": {"status": "ok", "summary": "役割分担は維持されている", "evidence": []},
                "escalation_pace": {"status": "warning", "summary": "中盤で伸びが鈍い", "evidence": ["chapter-4"]},
                "emotional_progression": {"status": "ok", "summary": "感情線は前進している", "evidence": []},
                "foreshadowing_coverage": {"status": "warning", "summary": "伏線回収が遅れている", "evidence": ["seed-1"]},
                "unresolved_thread_load": {"status": "ok", "summary": "未解決 thread は許容範囲", "evidence": []},
                "climax_readiness": {"status": "warning", "summary": "終盤準備がまだ弱い", "evidence": ["chapter-5"]},
            },
            "issue_codes": ["foreshadowing_coverage_gap", "climax_readiness_low"],
            "recommended_action": "replan",
            "story_state_summary": {
                "evaluated_through_chapter": 5,
                "canon_chapter_count": 5,
                "thread_count": 4,
                "unresolved_thread_count": 2,
                "resolved_thread_count": 2,
                "open_question_count": 3,
                "latest_timeline_event_count": 1,
            },
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            target = save_progress_report(Path(tmp_dir), payload, "json")
            loaded = load_progress_report(Path(tmp_dir))

            self.assertEqual(target.name, "progress_report.json")
            self.assertEqual(loaded, payload)

    def test_save_progress_report_requires_story_state_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(
                ValueError,
                "Invalid progress_report: missing required fields: story_state_summary",
            ):
                save_progress_report(
                    Path(tmp_dir),
                    {
                        "schema_name": "progress_report",
                        "schema_version": "1.0",
                        "evaluated_through_chapter": 5,
                        "checks": {
                            "chapter_role_coverage": {
                                "status": "ok",
                                "summary": "役割分担は維持されている",
                                "evidence": [],
                            },
                            "escalation_pace": {
                                "status": "warning",
                                "summary": "中盤で伸びが鈍い",
                                "evidence": ["chapter-4"],
                            },
                            "emotional_progression": {
                                "status": "ok",
                                "summary": "感情線は前進している",
                                "evidence": [],
                            },
                            "foreshadowing_coverage": {
                                "status": "warning",
                                "summary": "伏線回収が遅れている",
                                "evidence": ["seed-1"],
                            },
                            "unresolved_thread_load": {
                                "status": "ok",
                                "summary": "未解決 thread は許容範囲",
                                "evidence": [],
                            },
                            "climax_readiness": {
                                "status": "warning",
                                "summary": "終盤準備がまだ弱い",
                                "evidence": ["chapter-5"],
                            },
                        },
                        "issue_codes": ["foreshadowing_coverage_gap", "climax_readiness_low"],
                        "recommended_action": "replan",
                    },
                )

    def test_save_next_action_decision_round_trips_valid_payload(self) -> None:
        payload = {
            "schema_name": "next_action_decision",
            "schema_version": "1.0",
            "evaluated_through_chapter": 5,
            "story_state_summary": {
                "evaluated_through_chapter": 5,
                "canon_chapter_count": 5,
                "thread_count": 4,
                "unresolved_thread_count": 2,
                "resolved_thread_count": 1,
                "open_question_count": 3,
                "latest_timeline_event_count": 1,
            },
            "action": "replan_future",
            "reason": "中盤停滞のため future chapter を再計画する",
            "issue_codes": ["escalation_pace_flat", "climax_readiness_low"],
            "target_chapters": [6, 7, 8],
            "policy_budget": {
                "max_high_severity_chapters": 10,
                "max_total_rerun_attempts": 20,
                "remaining_high_severity_chapter_budget": 7,
                "remaining_rerun_attempt_budget": 14,
            },
            "decision_trace": [
                {
                    "code": "escalation_pace_flat",
                    "summary": "中盤の伸びが止まっている",
                    "value": "chapter-5",
                },
                {
                    "code": "climax_readiness_low",
                    "summary": "終盤準備が不足している",
                    "value": "chapter-5",
                },
            ],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            target = save_next_action_decision(Path(tmp_dir), payload, "json")
            loaded = load_next_action_decision(Path(tmp_dir))

            self.assertEqual(target.name, "next_action_decision.json")
            self.assertEqual(loaded, payload)

    def test_save_next_action_decision_requires_story_state_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(
                ValueError,
                "Invalid next_action_decision: missing required fields: story_state_summary",
            ):
                save_next_action_decision(
                    Path(tmp_dir),
                    {
                        "schema_name": "next_action_decision",
                        "schema_version": "1.0",
                        "evaluated_through_chapter": 5,
                        "action": "replan_future",
                        "reason": "story_state_summary が未設定",
                        "issue_codes": ["escalation_pace_flat"],
                        "target_chapters": [6, 7, 8],
                        "policy_budget": {
                            "max_high_severity_chapters": 10,
                            "max_total_rerun_attempts": 20,
                            "remaining_high_severity_chapter_budget": 7,
                            "remaining_rerun_attempt_budget": 14,
                        },
                        "decision_trace": [],
                    },
                )

    def test_save_next_action_decision_validates_allowed_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(
                ValueError,
                "Invalid next_action_decision: action must be one of: continue, revise, rerun_chapter, replan_future, stop_for_review",
            ):
                save_next_action_decision(
                    Path(tmp_dir),
                    {
                        "schema_name": "next_action_decision",
                        "schema_version": "1.0",
                        "evaluated_through_chapter": 5,
                        "story_state_summary": {
                            "evaluated_through_chapter": 5,
                            "canon_chapter_count": 5,
                            "thread_count": 4,
                            "unresolved_thread_count": 2,
                            "resolved_thread_count": 1,
                            "open_question_count": 3,
                            "latest_timeline_event_count": 1,
                        },
                        "action": "rerun",
                        "reason": "旧 action 名を使っている",
                        "issue_codes": [],
                        "target_chapters": [5],
                        "policy_budget": {
                            "max_high_severity_chapters": 10,
                            "max_total_rerun_attempts": 20,
                            "remaining_high_severity_chapter_budget": 7,
                            "remaining_rerun_attempt_budget": 14,
                        },
                        "decision_trace": [],
                    },
                )

    def test_save_next_action_decision_validates_trace_entry_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(
                ValueError,
                "Invalid next_action_decision: decision_trace\\[0\\] is missing required fields: summary",
            ):
                save_next_action_decision(
                    Path(tmp_dir),
                    {
                        "schema_name": "next_action_decision",
                        "schema_version": "1.0",
                        "evaluated_through_chapter": 5,
                        "story_state_summary": {
                            "evaluated_through_chapter": 5,
                            "canon_chapter_count": 5,
                            "thread_count": 4,
                            "unresolved_thread_count": 2,
                            "resolved_thread_count": 1,
                            "open_question_count": 3,
                            "latest_timeline_event_count": 1,
                        },
                        "action": "replan_future",
                        "reason": "根拠を保存する",
                        "issue_codes": ["escalation_pace_flat"],
                        "target_chapters": [6, 7, 8],
                        "policy_budget": {
                            "max_high_severity_chapters": 10,
                            "max_total_rerun_attempts": 20,
                            "remaining_high_severity_chapter_budget": 7,
                            "remaining_rerun_attempt_budget": 14,
                        },
                        "decision_trace": [
                            {
                                "code": "escalation_pace_flat",
                                "value": "chapter-5",
                            }
                        ],
                    },
                )

    def test_save_next_action_decision_rejects_target_chapters_for_continue_and_stop(self) -> None:
        invalid_cases = [
            ("continue", "continue must not have target_chapters"),
            ("stop_for_review", "stop_for_review must not have target_chapters"),
        ]

        for action, expected_message in invalid_cases:
            with self.subTest(action=action):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    with self.assertRaisesRegex(
                        ValueError,
                        expected_message,
                    ):
                        save_next_action_decision(
                            Path(tmp_dir),
                            {
                                "schema_name": "next_action_decision",
                                "schema_version": "1.0",
                                "evaluated_through_chapter": 5,
                                "story_state_summary": {
                                    "evaluated_through_chapter": 5,
                                    "canon_chapter_count": 5,
                                    "thread_count": 4,
                                    "unresolved_thread_count": 2,
                                    "resolved_thread_count": 1,
                                    "open_question_count": 3,
                                    "latest_timeline_event_count": 1,
                                },
                                "action": action,
                                "reason": "不要な target_chapters が入っている",
                                "issue_codes": [],
                                "target_chapters": [5],
                                "policy_budget": {
                                    "max_high_severity_chapters": 10,
                                    "max_total_rerun_attempts": 20,
                                    "remaining_high_severity_chapter_budget": 7,
                                    "remaining_rerun_attempt_budget": 14,
                                },
                                "decision_trace": [],
                            },
                        )

    def test_save_next_action_decision_requires_single_target_for_revise_and_rerun(self) -> None:
        invalid_cases = [
            ("revise", [], "revise must have exactly one target chapter"),
            ("rerun_chapter", [4, 5], "rerun_chapter must have exactly one target chapter"),
        ]

        for action, target_chapters, expected_message in invalid_cases:
            with self.subTest(action=action):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    with self.assertRaisesRegex(
                        ValueError,
                        expected_message,
                    ):
                        save_next_action_decision(
                            Path(tmp_dir),
                            {
                                "schema_name": "next_action_decision",
                                "schema_version": "1.0",
                                "evaluated_through_chapter": 5,
                                "story_state_summary": {
                                    "evaluated_through_chapter": 5,
                                    "canon_chapter_count": 5,
                                    "thread_count": 4,
                                    "unresolved_thread_count": 2,
                                    "resolved_thread_count": 1,
                                    "open_question_count": 3,
                                    "latest_timeline_event_count": 1,
                                },
                                "action": action,
                                "reason": "target chapter 数が不正である",
                                "issue_codes": ["needs_followup"],
                                "target_chapters": target_chapters,
                                "policy_budget": {
                                    "max_high_severity_chapters": 10,
                                    "max_total_rerun_attempts": 20,
                                    "remaining_high_severity_chapter_budget": 7,
                                    "remaining_rerun_attempt_budget": 14,
                                },
                                "decision_trace": [],
                            },
                        )

    def test_save_next_action_decision_requires_future_targets_for_replan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(
                ValueError,
                "replan_future must have at least one target chapter",
            ):
                save_next_action_decision(
                    Path(tmp_dir),
                    {
                        "schema_name": "next_action_decision",
                        "schema_version": "1.0",
                        "evaluated_through_chapter": 5,
                        "story_state_summary": {
                            "evaluated_through_chapter": 5,
                            "canon_chapter_count": 5,
                            "thread_count": 4,
                            "unresolved_thread_count": 2,
                            "resolved_thread_count": 1,
                            "open_question_count": 3,
                            "latest_timeline_event_count": 1,
                        },
                        "action": "replan_future",
                        "reason": "future chapter が指定されていない",
                        "issue_codes": ["escalation_pace_flat"],
                        "target_chapters": [],
                        "policy_budget": {
                            "max_high_severity_chapters": 10,
                            "max_total_rerun_attempts": 20,
                            "remaining_high_severity_chapter_budget": 7,
                            "remaining_rerun_attempt_budget": 14,
                        },
                        "decision_trace": [],
                    },
                )

    def test_save_progress_report_validates_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(
                ValueError,
                "Invalid progress_report: missing required fields: checks",
            ):
                save_progress_report(
                    Path(tmp_dir),
                    {
                        "schema_name": "progress_report",
                        "schema_version": "1.0",
                        "evaluated_through_chapter": 5,
                        "issue_codes": [],
                        "recommended_action": "continue",
                    },
                )

    def test_load_progress_report_rejects_missing_named_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_artifact(
                Path(tmp_dir),
                "progress_report",
                {
                    "schema_name": "progress_report",
                    "schema_version": "1.0",
                    "evaluated_through_chapter": 5,
                    "checks": {
                        "chapter_role_coverage": {"status": "ok", "summary": "ok", "evidence": []},
                        "escalation_pace": {"status": "ok", "summary": "ok", "evidence": []},
                        "emotional_progression": {"status": "ok", "summary": "ok", "evidence": []},
                        "foreshadowing_coverage": {"status": "ok", "summary": "ok", "evidence": []},
                        "unresolved_thread_load": {"status": "ok", "summary": "ok", "evidence": []},
                    },
                    "issue_codes": [],
                    "recommended_action": "continue",
                    "story_state_summary": {
                        "evaluated_through_chapter": 5,
                        "canon_chapter_count": 5,
                        "thread_count": 0,
                        "unresolved_thread_count": 0,
                        "resolved_thread_count": 0,
                        "open_question_count": 0,
                        "latest_timeline_event_count": 0,
                    },
                },
            )

            with self.assertRaisesRegex(
                ValueError,
                "Invalid progress_report: checks is missing required fields: climax_readiness",
            ):
                load_progress_report(Path(tmp_dir))

    def test_save_replan_history_round_trips_valid_payload(self) -> None:
        payload = {
            "schema_name": "replan_history",
            "schema_version": "1.0",
            "replans": [
                {
                    "replan_id": "replan-001",
                    "trigger_chapter_number": 5,
                    "reason": "progress_report が中盤停滞を示したため",
                    "issue_codes": ["escalation_pace_flat", "climax_readiness_low"],
                    "story_state_summary": {
                        "evaluated_through_chapter": 5,
                        "canon_chapter_count": 5,
                        "thread_count": 4,
                        "unresolved_thread_count": 2,
                        "resolved_thread_count": 1,
                        "open_question_count": 3,
                        "latest_timeline_event_count": 1,
                    },
                    "impact_scope": {
                        "from_chapter": 6,
                        "to_chapter": 8,
                        "chapter_numbers": [6, 7, 8],
                    },
                    "updated_artifacts": ["chapter_briefs", "scene_cards"],
                    "change_summary": ["第6章の役割を再定義した", "第7章の伏線回収を前倒しした"],
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            target = save_replan_history(Path(tmp_dir), payload, "json")
            loaded = load_replan_history(Path(tmp_dir))

            self.assertEqual(target.name, "replan_history.json")
            self.assertEqual(loaded, payload)

    def test_save_replan_history_validates_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(
                ValueError,
                "Invalid replan_history: missing required fields: replans",
            ):
                save_replan_history(
                    Path(tmp_dir),
                    {
                        "schema_name": "replan_history",
                        "schema_version": "1.0",
                    },
                )

    def test_load_replan_history_rejects_missing_impact_scope_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_artifact(
                Path(tmp_dir),
                "replan_history",
                {
                    "schema_name": "replan_history",
                    "schema_version": "1.0",
                    "replans": [
                        {
                            "replan_id": "replan-001",
                            "trigger_chapter_number": 5,
                            "reason": "理由",
                            "issue_codes": ["code-1"],
                            "story_state_summary": {
                                "evaluated_through_chapter": 5,
                                "canon_chapter_count": 5,
                                "thread_count": 4,
                                "unresolved_thread_count": 2,
                                "resolved_thread_count": 1,
                                "open_question_count": 3,
                                "latest_timeline_event_count": 1,
                            },
                            "impact_scope": {
                                "from_chapter": 6,
                                "chapter_numbers": [6, 7],
                            },
                            "updated_artifacts": ["chapter_briefs"],
                            "change_summary": ["差分"],
                        }
                    ],
                },
            )

            with self.assertRaisesRegex(
                ValueError,
                "Invalid replan_history: replans\\[0\\].impact_scope is missing required fields: to_chapter",
            ):
                load_replan_history(Path(tmp_dir))

    def test_load_replan_history_rejects_missing_story_state_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_artifact(
                Path(tmp_dir),
                "replan_history",
                {
                    "schema_name": "replan_history",
                    "schema_version": "1.0",
                    "replans": [
                        {
                            "replan_id": "replan-001",
                            "trigger_chapter_number": 5,
                            "reason": "理由",
                            "issue_codes": ["code-1"],
                            "impact_scope": {
                                "from_chapter": 6,
                                "to_chapter": 7,
                                "chapter_numbers": [6, 7],
                            },
                            "updated_artifacts": ["chapter_briefs"],
                            "change_summary": ["差分"],
                        }
                    ],
                },
            )

            with self.assertRaisesRegex(
                ValueError,
                "Invalid replan_history: replans\\[0\\] is missing required fields: story_state_summary",
            ):
                load_replan_history(Path(tmp_dir))

    def test_upsert_replan_history_entry_creates_new_history_when_missing(self) -> None:
        entry = {
            "replan_id": "replan-001",
            "trigger_chapter_number": 5,
            "reason": "理由",
            "issue_codes": ["code-1"],
            "story_state_summary": {
                "evaluated_through_chapter": 5,
                "canon_chapter_count": 5,
                "thread_count": 4,
                "unresolved_thread_count": 2,
                "resolved_thread_count": 1,
                "open_question_count": 3,
                "latest_timeline_event_count": 1,
            },
            "impact_scope": {"from_chapter": 6, "to_chapter": 7, "chapter_numbers": [6, 7]},
            "updated_artifacts": ["chapter_briefs"],
            "change_summary": ["差分"],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            upsert_replan_history_entry(Path(tmp_dir), entry)
            loaded = load_replan_history(Path(tmp_dir))

            self.assertEqual(len(loaded["replans"]), 1)
            self.assertEqual(loaded["replans"][0]["replan_id"], "replan-001")

    def test_upsert_replan_history_entry_appends_new_replan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_replan_history(
                Path(tmp_dir),
                {
                    "schema_name": "replan_history",
                    "schema_version": "1.0",
                    "replans": [
                        {
                            "replan_id": "replan-001",
                            "trigger_chapter_number": 5,
                            "reason": "理由1",
                            "issue_codes": ["code-1"],
                            "story_state_summary": {
                                "evaluated_through_chapter": 5,
                                "canon_chapter_count": 5,
                                "thread_count": 4,
                                "unresolved_thread_count": 2,
                                "resolved_thread_count": 1,
                                "open_question_count": 3,
                                "latest_timeline_event_count": 1,
                            },
                            "impact_scope": {"from_chapter": 6, "to_chapter": 7, "chapter_numbers": [6, 7]},
                            "updated_artifacts": ["chapter_briefs"],
                            "change_summary": ["差分1"],
                        }
                    ],
                },
            )

            upsert_replan_history_entry(
                Path(tmp_dir),
                {
                    "replan_id": "replan-002",
                    "trigger_chapter_number": 7,
                    "reason": "理由2",
                    "issue_codes": ["code-2"],
                    "story_state_summary": {
                        "evaluated_through_chapter": 7,
                        "canon_chapter_count": 7,
                        "thread_count": 4,
                        "unresolved_thread_count": 2,
                        "resolved_thread_count": 1,
                        "open_question_count": 3,
                        "latest_timeline_event_count": 1,
                    },
                    "impact_scope": {"from_chapter": 8, "to_chapter": 9, "chapter_numbers": [8, 9]},
                    "updated_artifacts": ["scene_cards"],
                    "change_summary": ["差分2"],
                },
            )
            loaded = load_replan_history(Path(tmp_dir))

            self.assertEqual([entry["replan_id"] for entry in loaded["replans"]], ["replan-001", "replan-002"])

    def test_upsert_replan_history_entry_replaces_existing_replan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_replan_history(
                Path(tmp_dir),
                {
                    "schema_name": "replan_history",
                    "schema_version": "1.0",
                    "replans": [
                        {
                            "replan_id": "replan-001",
                            "trigger_chapter_number": 5,
                            "reason": "古い理由",
                            "issue_codes": ["code-1"],
                            "story_state_summary": {
                                "evaluated_through_chapter": 5,
                                "canon_chapter_count": 5,
                                "thread_count": 4,
                                "unresolved_thread_count": 2,
                                "resolved_thread_count": 1,
                                "open_question_count": 3,
                                "latest_timeline_event_count": 1,
                            },
                            "impact_scope": {"from_chapter": 6, "to_chapter": 7, "chapter_numbers": [6, 7]},
                            "updated_artifacts": ["chapter_briefs"],
                            "change_summary": ["古い差分"],
                        }
                    ],
                },
            )

            upsert_replan_history_entry(
                Path(tmp_dir),
                {
                    "replan_id": "replan-001",
                    "trigger_chapter_number": 5,
                    "reason": "新しい理由",
                    "issue_codes": ["code-1", "code-2"],
                    "story_state_summary": {
                        "evaluated_through_chapter": 5,
                        "canon_chapter_count": 5,
                        "thread_count": 4,
                        "unresolved_thread_count": 2,
                        "resolved_thread_count": 1,
                        "open_question_count": 3,
                        "latest_timeline_event_count": 1,
                    },
                    "impact_scope": {"from_chapter": 6, "to_chapter": 8, "chapter_numbers": [6, 7, 8]},
                    "updated_artifacts": ["chapter_briefs", "scene_cards"],
                    "change_summary": ["新しい差分"],
                },
            )
            loaded = load_replan_history(Path(tmp_dir))

            self.assertEqual(len(loaded["replans"]), 1)
            self.assertEqual(loaded["replans"][0]["reason"], "新しい理由")
            self.assertEqual(loaded["replans"][0]["impact_scope"]["to_chapter"], 8)

    def test_apply_replan_updates_replaces_only_future_chapters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_chapter_briefs(
                Path(tmp_dir),
                [
                    {
                        "chapter_number": 1,
                        "purpose": "導入",
                        "goal": "異変に気づく",
                        "conflict": "記憶が曖昧になる",
                        "turn": "腕時計が逆回転する",
                        "must_include": ["壊れた腕時計"],
                        "continuity_dependencies": [],
                        "foreshadowing_targets": ["seed-1"],
                        "arc_progress": "受け身",
                        "target_length_guidance": "短め",
                    },
                    {
                        "chapter_number": 2,
                        "purpose": "探索",
                        "goal": "手がかりを集める",
                        "conflict": "相棒を信じ切れない",
                        "turn": "古い記録が見つかる",
                        "must_include": ["古い記録"],
                        "continuity_dependencies": ["chapter-1"],
                        "foreshadowing_targets": ["seed-2"],
                        "arc_progress": "疑いが強まる",
                        "target_length_guidance": "標準",
                    },
                    {
                        "chapter_number": 3,
                        "purpose": "対立",
                        "goal": "敵の正体へ迫る",
                        "conflict": "情報が食い違う",
                        "turn": "味方の裏切りが示唆される",
                        "must_include": ["地下書庫"],
                        "continuity_dependencies": ["chapter-2"],
                        "foreshadowing_targets": ["seed-3"],
                        "arc_progress": "受け身から決意へ",
                        "target_length_guidance": "長め",
                    },
                ],
            )
            save_scene_cards(
                Path(tmp_dir),
                [
                    {
                        "chapter_number": 1,
                        "scenes": [
                            {
                                "chapter_number": 1,
                                "scene_number": 1,
                                "scene_goal": "異変に気づく",
                                "scene_conflict": "記憶が揺らぐ",
                                "scene_turn": "腕時計が震える",
                                "pov_character": "ミナト",
                                "participants": ["ミナト"],
                                "setting": "駅前",
                                "must_include": ["腕時計"],
                                "continuity_refs": [],
                                "foreshadowing_action": "時計を見る",
                                "exit_state": "違和感を抱える",
                            },
                            {
                                "chapter_number": 1,
                                "scene_number": 2,
                                "scene_goal": "相談相手を探す",
                                "scene_conflict": "誰も信じられない",
                                "scene_turn": "古い噂を聞く",
                                "pov_character": "ミナト",
                                "participants": ["ミナト", "店主"],
                                "setting": "喫茶店",
                                "must_include": ["古い噂"],
                                "continuity_refs": ["scene 1"],
                                "foreshadowing_action": "メモを取る",
                                "exit_state": "次の目的地が決まる",
                            },
                            {
                                "chapter_number": 1,
                                "scene_number": 3,
                                "scene_goal": "次章へつなぐ",
                                "scene_conflict": "尾行に気づく",
                                "scene_turn": "誰かが主人公を見ている",
                                "pov_character": "ミナト",
                                "participants": ["ミナト", "尾行者"],
                                "setting": "高架下",
                                "must_include": ["足音"],
                                "continuity_refs": ["scene 2"],
                                "foreshadowing_action": "振り返る",
                                "exit_state": "危機が近づく",
                            },
                        ],
                    },
                    {
                        "chapter_number": 2,
                        "scenes": [
                            {
                                "chapter_number": 2,
                                "scene_number": 1,
                                "scene_goal": "旧計画を実行する",
                                "scene_conflict": "警戒が強い",
                                "scene_turn": "想定外の警報が鳴る",
                                "pov_character": "ミナト",
                                "participants": ["ミナト", "相棒"],
                                "setting": "旧研究棟",
                                "must_include": ["警報"],
                                "continuity_refs": ["chapter-1"],
                                "foreshadowing_action": "資料棚を見る",
                                "exit_state": "退路が閉ざされる",
                            },
                            {
                                "chapter_number": 2,
                                "scene_number": 2,
                                "scene_goal": "資料を持ち出す",
                                "scene_conflict": "時間が足りない",
                                "scene_turn": "偽装文書を見抜く",
                                "pov_character": "ミナト",
                                "participants": ["ミナト"],
                                "setting": "保管室",
                                "must_include": ["偽装文書"],
                                "continuity_refs": ["scene 1"],
                                "foreshadowing_action": "印を見る",
                                "exit_state": "本命の手がかりが残る",
                            },
                            {
                                "chapter_number": 2,
                                "scene_number": 3,
                                "scene_goal": "脱出する",
                                "scene_conflict": "出口が封鎖される",
                                "scene_turn": "地下通路を見つける",
                                "pov_character": "ミナト",
                                "participants": ["ミナト", "相棒"],
                                "setting": "旧研究棟",
                                "must_include": ["地下通路"],
                                "continuity_refs": ["scene 2"],
                                "foreshadowing_action": "床を調べる",
                                "exit_state": "地下へ向かう",
                            },
                        ],
                    },
                    {
                        "chapter_number": 3,
                        "scenes": [
                            {
                                "chapter_number": 3,
                                "scene_number": 1,
                                "scene_goal": "地下で情報を探す",
                                "scene_conflict": "停電で進めない",
                                "scene_turn": "非常灯が点く",
                                "pov_character": "ミナト",
                                "participants": ["ミナト"],
                                "setting": "地下通路",
                                "must_include": ["非常灯"],
                                "continuity_refs": ["chapter-2"],
                                "foreshadowing_action": "壁を見る",
                                "exit_state": "先へ進む",
                            },
                            {
                                "chapter_number": 3,
                                "scene_number": 2,
                                "scene_goal": "真相へ近づく",
                                "scene_conflict": "証言が食い違う",
                                "scene_turn": "録音が見つかる",
                                "pov_character": "ミナト",
                                "participants": ["ミナト", "案内人"],
                                "setting": "制御室",
                                "must_include": ["録音"],
                                "continuity_refs": ["scene 1"],
                                "foreshadowing_action": "再生する",
                                "exit_state": "疑いが深まる",
                            },
                            {
                                "chapter_number": 3,
                                "scene_number": 3,
                                "scene_goal": "対立を深める",
                                "scene_conflict": "味方を疑う",
                                "scene_turn": "裏切りの証拠が出る",
                                "pov_character": "ミナト",
                                "participants": ["ミナト", "相棒"],
                                "setting": "制御室前",
                                "must_include": ["証拠写真"],
                                "continuity_refs": ["scene 2"],
                                "foreshadowing_action": "写真を確かめる",
                                "exit_state": "次章へ不信感を持ち越す",
                            },
                        ],
                    },
                ],
            )

            result = apply_replan_updates(
                Path(tmp_dir),
                {
                    "replan_id": "replan-001",
                    "trigger_chapter_number": 1,
                    "reason": "中盤の役割を前倒しで組み替える",
                    "issue_codes": ["escalation_pace_flat"],
                    "story_state_summary": {
                        "evaluated_through_chapter": 1,
                        "canon_chapter_count": 1,
                        "thread_count": 0,
                        "unresolved_thread_count": 0,
                        "resolved_thread_count": 0,
                        "open_question_count": 0,
                        "latest_timeline_event_count": 0,
                    },
                    "impact_scope": {"from_chapter": 2, "to_chapter": 3, "chapter_numbers": [2, 3]},
                    "updated_artifacts": ["chapter_briefs", "scene_cards"],
                    "change_summary": ["第2章と第3章の役割を再構成する"],
                },
                chapter_brief_updates=[
                    {
                        "chapter_number": 2,
                        "purpose": "再計画後の探索",
                        "goal": "伏線を前倒しで回収する",
                        "conflict": "相棒との不信が露呈する",
                        "turn": "録音の一部が先に見つかる",
                        "must_include": ["録音の断片"],
                        "continuity_dependencies": ["chapter-1"],
                        "foreshadowing_targets": ["seed-2", "seed-3"],
                        "arc_progress": "疑いを言語化する",
                        "target_length_guidance": "標準",
                    },
                    {
                        "chapter_number": 3,
                        "purpose": "対立の加速",
                        "goal": "裏切りの核心へ近づく",
                        "conflict": "証拠が相棒を指す",
                        "turn": "証拠の出所に矛盾が見つかる",
                        "must_include": ["証拠写真", "録音"],
                        "continuity_dependencies": ["chapter-2"],
                        "foreshadowing_targets": ["seed-4"],
                        "arc_progress": "決意へ踏み込む",
                        "target_length_guidance": "長め",
                    },
                ],
                scene_card_updates=[
                    {
                        "chapter_number": 2,
                        "scenes": [
                            {
                                "chapter_number": 2,
                                "scene_number": 1,
                                "scene_goal": "録音の断片を追う",
                                "scene_conflict": "相棒が行き先を隠す",
                                "scene_turn": "断片が旧研究棟を示す",
                                "pov_character": "ミナト",
                                "participants": ["ミナト", "相棒"],
                                "setting": "商店街",
                                "must_include": ["録音の断片"],
                                "continuity_refs": ["chapter-1"],
                                "foreshadowing_action": "波形を確認する",
                                "exit_state": "旧研究棟へ向かう",
                            },
                            {
                                "chapter_number": 2,
                                "scene_number": 2,
                                "scene_goal": "相棒を問い詰める",
                                "scene_conflict": "言い訳が二転三転する",
                                "scene_turn": "証拠写真の存在が示唆される",
                                "pov_character": "ミナト",
                                "participants": ["ミナト", "相棒"],
                                "setting": "歩道橋",
                                "must_include": ["証拠写真"],
                                "continuity_refs": ["scene 1"],
                                "foreshadowing_action": "写真の話を聞き返す",
                                "exit_state": "不信感が確信へ変わる",
                            },
                            {
                                "chapter_number": 2,
                                "scene_number": 3,
                                "scene_goal": "次章の対立へつなぐ",
                                "scene_conflict": "別勢力が介入する",
                                "scene_turn": "黒幕側の監視を知る",
                                "pov_character": "ミナト",
                                "participants": ["ミナト", "監視者"],
                                "setting": "旧研究棟前",
                                "must_include": ["監視メモ"],
                                "continuity_refs": ["scene 2"],
                                "foreshadowing_action": "監視記録を拾う",
                                "exit_state": "三者対立の兆候が生まれる",
                            },
                        ],
                    },
                    {
                        "chapter_number": 3,
                        "scenes": [
                            {
                                "chapter_number": 3,
                                "scene_number": 1,
                                "scene_goal": "証拠の出所を追う",
                                "scene_conflict": "記録が改ざんされている",
                                "scene_turn": "録音の欠落箇所が見つかる",
                                "pov_character": "ミナト",
                                "participants": ["ミナト"],
                                "setting": "資料室",
                                "must_include": ["改ざん記録"],
                                "continuity_refs": ["chapter-2"],
                                "foreshadowing_action": "改ざん時刻を見る",
                                "exit_state": "黒幕候補が絞られる",
                            },
                            {
                                "chapter_number": 3,
                                "scene_number": 2,
                                "scene_goal": "相棒と再対峙する",
                                "scene_conflict": "相棒が沈黙する",
                                "scene_turn": "別の犯人像が浮かぶ",
                                "pov_character": "ミナト",
                                "participants": ["ミナト", "相棒"],
                                "setting": "屋上",
                                "must_include": ["録音"],
                                "continuity_refs": ["scene 1"],
                                "foreshadowing_action": "録音を再生する",
                                "exit_state": "疑い先が揺らぐ",
                            },
                            {
                                "chapter_number": 3,
                                "scene_number": 3,
                                "scene_goal": "次の山場を準備する",
                                "scene_conflict": "真相がまだ届かない",
                                "scene_turn": "監視者の正体に手がかりが出る",
                                "pov_character": "ミナト",
                                "participants": ["ミナト", "監視者"],
                                "setting": "非常階段",
                                "must_include": ["監視メモ"],
                                "continuity_refs": ["scene 2"],
                                "foreshadowing_action": "メモを照合する",
                                "exit_state": "次章の追跡目標が定まる",
                            },
                        ],
                    },
                ],
            )

            briefs = load_chapter_briefs(Path(tmp_dir))
            scenes = load_scene_cards(Path(tmp_dir))

            self.assertEqual(result["chapter_briefs"].name, "chapter_briefs.json")
            self.assertEqual(result["scene_cards"].name, "scene_cards.json")
            self.assertEqual(briefs[0]["purpose"], "導入")
            self.assertEqual(briefs[1]["purpose"], "再計画後の探索")
            self.assertEqual(briefs[2]["purpose"], "対立の加速")
            self.assertEqual(scenes[0]["scenes"][0]["scene_goal"], "異変に気づく")
            self.assertEqual(scenes[1]["scenes"][0]["scene_goal"], "録音の断片を追う")
            self.assertEqual(scenes[2]["scenes"][1]["scene_turn"], "別の犯人像が浮かぶ")

    def test_apply_replan_updates_rejects_non_future_chapter_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_chapter_briefs(
                Path(tmp_dir),
                [
                    {
                        "chapter_number": 1,
                        "purpose": "導入",
                        "goal": "異変に気づく",
                        "conflict": "記憶が揺らぐ",
                        "turn": "腕時計が逆回転する",
                        "must_include": ["腕時計"],
                        "continuity_dependencies": [],
                        "foreshadowing_targets": ["seed-1"],
                        "arc_progress": "受け身",
                        "target_length_guidance": "短め",
                    }
                ],
            )
            save_scene_cards(
                Path(tmp_dir),
                [
                    {
                        "chapter_number": 1,
                        "scenes": [
                            {
                                "chapter_number": 1,
                                "scene_number": 1,
                                "scene_goal": "異変に気づく",
                                "scene_conflict": "記憶が揺らぐ",
                                "scene_turn": "腕時計が逆回転する",
                                "pov_character": "ミナト",
                                "participants": ["ミナト"],
                                "setting": "駅前",
                                "must_include": ["腕時計"],
                                "continuity_refs": [],
                                "foreshadowing_action": "時計を見る",
                                "exit_state": "違和感を抱える",
                            },
                            {
                                "chapter_number": 1,
                                "scene_number": 2,
                                "scene_goal": "相談相手を探す",
                                "scene_conflict": "誰も信じられない",
                                "scene_turn": "古い噂を聞く",
                                "pov_character": "ミナト",
                                "participants": ["ミナト", "店主"],
                                "setting": "喫茶店",
                                "must_include": ["噂"],
                                "continuity_refs": ["scene 1"],
                                "foreshadowing_action": "メモを取る",
                                "exit_state": "次の目的地が決まる",
                            },
                            {
                                "chapter_number": 1,
                                "scene_number": 3,
                                "scene_goal": "次章へつなぐ",
                                "scene_conflict": "尾行に気づく",
                                "scene_turn": "誰かが主人公を見ている",
                                "pov_character": "ミナト",
                                "participants": ["ミナト", "尾行者"],
                                "setting": "高架下",
                                "must_include": ["足音"],
                                "continuity_refs": ["scene 2"],
                                "foreshadowing_action": "振り返る",
                                "exit_state": "危機が近づく",
                            },
                        ],
                    }
                ],
            )

            with self.assertRaisesRegex(
                ValueError,
                "impact_scope.from_chapter must be greater than trigger_chapter_number",
            ):
                apply_replan_updates(
                    Path(tmp_dir),
                {
                    "replan_id": "replan-001",
                    "trigger_chapter_number": 1,
                    "reason": "過去章まで巻き戻そうとしている",
                    "issue_codes": ["bad-scope"],
                    "story_state_summary": {
                        "evaluated_through_chapter": 1,
                        "canon_chapter_count": 1,
                        "thread_count": 0,
                        "unresolved_thread_count": 0,
                        "resolved_thread_count": 0,
                        "open_question_count": 0,
                        "latest_timeline_event_count": 0,
                    },
                    "impact_scope": {"from_chapter": 1, "to_chapter": 1, "chapter_numbers": [1]},
                    "updated_artifacts": ["chapter_briefs", "scene_cards"],
                    "change_summary": ["第1章を書き換える"],
                },
                    chapter_brief_updates=[],
                    scene_card_updates=[],
                )

    def test_apply_replan_updates_rejects_scope_and_payload_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_chapter_briefs(
                Path(tmp_dir),
                [
                    {
                        "chapter_number": 1,
                        "purpose": "導入",
                        "goal": "異変に気づく",
                        "conflict": "記憶が揺らぐ",
                        "turn": "腕時計が逆回転する",
                        "must_include": ["腕時計"],
                        "continuity_dependencies": [],
                        "foreshadowing_targets": ["seed-1"],
                        "arc_progress": "受け身",
                        "target_length_guidance": "短め",
                    },
                    {
                        "chapter_number": 2,
                        "purpose": "探索",
                        "goal": "手がかりを集める",
                        "conflict": "相棒を信じ切れない",
                        "turn": "古い記録が見つかる",
                        "must_include": ["古い記録"],
                        "continuity_dependencies": ["chapter-1"],
                        "foreshadowing_targets": ["seed-2"],
                        "arc_progress": "疑いが強まる",
                        "target_length_guidance": "標準",
                    },
                ],
            )
            save_scene_cards(
                Path(tmp_dir),
                [
                    {
                        "chapter_number": 1,
                        "scenes": [
                            {
                                "chapter_number": 1,
                                "scene_number": 1,
                                "scene_goal": "異変に気づく",
                                "scene_conflict": "記憶が揺らぐ",
                                "scene_turn": "腕時計が逆回転する",
                                "pov_character": "ミナト",
                                "participants": ["ミナト"],
                                "setting": "駅前",
                                "must_include": ["腕時計"],
                                "continuity_refs": [],
                                "foreshadowing_action": "時計を見る",
                                "exit_state": "違和感を抱える",
                            },
                            {
                                "chapter_number": 1,
                                "scene_number": 2,
                                "scene_goal": "相談相手を探す",
                                "scene_conflict": "誰も信じられない",
                                "scene_turn": "古い噂を聞く",
                                "pov_character": "ミナト",
                                "participants": ["ミナト", "店主"],
                                "setting": "喫茶店",
                                "must_include": ["噂"],
                                "continuity_refs": ["scene 1"],
                                "foreshadowing_action": "メモを取る",
                                "exit_state": "次の目的地が決まる",
                            },
                            {
                                "chapter_number": 1,
                                "scene_number": 3,
                                "scene_goal": "次章へつなぐ",
                                "scene_conflict": "尾行に気づく",
                                "scene_turn": "誰かが主人公を見ている",
                                "pov_character": "ミナト",
                                "participants": ["ミナト", "尾行者"],
                                "setting": "高架下",
                                "must_include": ["足音"],
                                "continuity_refs": ["scene 2"],
                                "foreshadowing_action": "振り返る",
                                "exit_state": "危機が近づく",
                            },
                        ],
                    },
                    {
                        "chapter_number": 2,
                        "scenes": [
                            {
                                "chapter_number": 2,
                                "scene_number": 1,
                                "scene_goal": "旧計画を実行する",
                                "scene_conflict": "警戒が強い",
                                "scene_turn": "想定外の警報が鳴る",
                                "pov_character": "ミナト",
                                "participants": ["ミナト", "相棒"],
                                "setting": "旧研究棟",
                                "must_include": ["警報"],
                                "continuity_refs": ["chapter-1"],
                                "foreshadowing_action": "資料棚を見る",
                                "exit_state": "退路が閉ざされる",
                            },
                            {
                                "chapter_number": 2,
                                "scene_number": 2,
                                "scene_goal": "資料を持ち出す",
                                "scene_conflict": "時間が足りない",
                                "scene_turn": "偽装文書を見抜く",
                                "pov_character": "ミナト",
                                "participants": ["ミナト"],
                                "setting": "保管室",
                                "must_include": ["偽装文書"],
                                "continuity_refs": ["scene 1"],
                                "foreshadowing_action": "印を見る",
                                "exit_state": "本命の手がかりが残る",
                            },
                            {
                                "chapter_number": 2,
                                "scene_number": 3,
                                "scene_goal": "脱出する",
                                "scene_conflict": "出口が封鎖される",
                                "scene_turn": "地下通路を見つける",
                                "pov_character": "ミナト",
                                "participants": ["ミナト", "相棒"],
                                "setting": "旧研究棟",
                                "must_include": ["地下通路"],
                                "continuity_refs": ["scene 2"],
                                "foreshadowing_action": "床を調べる",
                                "exit_state": "地下へ向かう",
                            },
                        ],
                    },
                ],
            )

            with self.assertRaisesRegex(
                ValueError,
                "chapter_brief_updates chapter numbers must match impact_scope.chapter_numbers",
            ):
                apply_replan_updates(
                    Path(tmp_dir),
                {
                    "replan_id": "replan-002",
                    "trigger_chapter_number": 1,
                    "reason": "対象章の差し替えが足りない",
                    "issue_codes": ["scope-mismatch"],
                    "story_state_summary": {
                        "evaluated_through_chapter": 1,
                        "canon_chapter_count": 2,
                        "thread_count": 0,
                        "unresolved_thread_count": 0,
                        "resolved_thread_count": 0,
                        "open_question_count": 0,
                        "latest_timeline_event_count": 0,
                    },
                    "impact_scope": {"from_chapter": 2, "to_chapter": 2, "chapter_numbers": [2]},
                    "updated_artifacts": ["chapter_briefs", "scene_cards"],
                    "change_summary": ["第2章だけ差し替える"],
                },
                    chapter_brief_updates=[
                        {
                            "chapter_number": 1,
                            "purpose": "誤った章番号",
                            "goal": "誤更新",
                            "conflict": "誤更新",
                            "turn": "誤更新",
                            "must_include": [],
                            "continuity_dependencies": [],
                            "foreshadowing_targets": [],
                            "arc_progress": "誤更新",
                            "target_length_guidance": "短め",
                        }
                    ],
                    scene_card_updates=[
                        {
                            "chapter_number": 2,
                            "scenes": [
                                {
                                    "chapter_number": 2,
                                    "scene_number": 1,
                                    "scene_goal": "再計画",
                                    "scene_conflict": "再計画",
                                    "scene_turn": "再計画",
                                    "pov_character": "ミナト",
                                    "participants": ["ミナト"],
                                    "setting": "駅前",
                                    "must_include": [],
                                    "continuity_refs": [],
                                    "foreshadowing_action": "見る",
                                    "exit_state": "進む",
                                },
                                {
                                    "chapter_number": 2,
                                    "scene_number": 2,
                                    "scene_goal": "再計画",
                                    "scene_conflict": "再計画",
                                    "scene_turn": "再計画",
                                    "pov_character": "ミナト",
                                    "participants": ["ミナト"],
                                    "setting": "喫茶店",
                                    "must_include": [],
                                    "continuity_refs": ["scene 1"],
                                    "foreshadowing_action": "話す",
                                    "exit_state": "進む",
                                },
                                {
                                    "chapter_number": 2,
                                    "scene_number": 3,
                                    "scene_goal": "再計画",
                                    "scene_conflict": "再計画",
                                    "scene_turn": "再計画",
                                    "pov_character": "ミナト",
                                    "participants": ["ミナト"],
                                    "setting": "高架下",
                                    "must_include": [],
                                    "continuity_refs": ["scene 2"],
                                    "foreshadowing_action": "進む",
                                    "exit_state": "終える",
                                },
                            ],
                        }
                    ],
                )

    def test_save_chapter_handoff_packet_round_trips_valid_payload(self) -> None:
        payload = {
            "schema_name": "chapter_handoff_packet",
            "schema_version": "1.0",
            "chapter_number": 2,
            "current_chapter_brief": {
                "chapter_number": 2,
                "purpose": "転機",
                "goal": "秘密の扉を開く",
                "conflict": "仲間を信じ切れない",
                "turn": "鍵の正体に気づく",
                "must_include": ["壊れた鍵"],
                "continuity_dependencies": ["ミナト"],
                "foreshadowing_targets": ["seed-1"],
                "arc_progress": "疑いから決意へ進む",
                "target_length_guidance": "standard",
            },
            "relevant_scene_cards": [
                {
                    "chapter_number": 2,
                    "scene_number": 1,
                    "scene_goal": "地下書庫へ入る",
                    "scene_conflict": "警報が鳴る",
                    "scene_turn": "鍵が反応する",
                    "pov_character": "ミナト",
                    "participants": ["ミナト", "相棒"],
                    "setting": "地下書庫",
                    "must_include": ["壊れた鍵"],
                    "continuity_refs": ["chapter_briefs[1]"],
                    "foreshadowing_action": "鍵穴を調べる",
                    "exit_state": "真相に一歩近づく",
                }
            ],
            "relevant_canon_facts": ["第1章で鍵を拾っている"],
            "unresolved_threads": ["seed-1"],
            "unresolved_thread_entries": [
                {
                    "thread_id": "seed-1",
                    "label": "壊れた鍵の出自",
                    "status": "seeded",
                    "introduced_in_chapter": 1,
                    "last_updated_in_chapter": 1,
                    "related_characters": ["ミナト"],
                    "notes": ["第1章で鍵が反応した理由は未回収。"],
                }
            ],
            "previous_chapter_summary": "主人公は鍵を拾い、異変の始まりを知った。",
            "style_constraints": {
                "tone": "静謐",
                "point_of_view": "ミナト",
                "tense": "past",
            },
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            target = save_chapter_handoff_packet(Path(tmp_dir), payload, "json")
            loaded = load_chapter_handoff_packet(Path(tmp_dir))

            self.assertEqual(target.name, "chapter_handoff_packet.json")
            self.assertEqual(loaded, payload)

    def test_save_chapter_handoff_packet_rejects_invalid_unresolved_thread_entry(self) -> None:
        payload = {
            "schema_name": "chapter_handoff_packet",
            "schema_version": "1.0",
            "chapter_number": 2,
            "current_chapter_brief": {
                "chapter_number": 2,
                "purpose": "転機",
                "goal": "秘密の扉を開く",
                "conflict": "仲間を信じ切れない",
                "turn": "鍵の正体に気づく",
                "must_include": ["壊れた鍵"],
                "continuity_dependencies": ["ミナト"],
                "foreshadowing_targets": ["seed-1"],
                "arc_progress": "疑いから決意へ進む",
                "target_length_guidance": "standard",
            },
            "relevant_scene_cards": [],
            "relevant_canon_facts": ["第1章で鍵を拾っている"],
            "unresolved_threads": ["seed-1"],
            "unresolved_thread_entries": [
                {
                    "label": "壊れた鍵の出自",
                    "status": "seeded",
                    "introduced_in_chapter": 1,
                    "last_updated_in_chapter": 1,
                    "related_characters": ["ミナト"],
                    "notes": ["第1章で鍵が反応した理由は未回収。"],
                }
            ],
            "previous_chapter_summary": "主人公は鍵を拾い、異変の始まりを知った。",
            "style_constraints": {
                "tone": "静謐",
                "point_of_view": "ミナト",
                "tense": "past",
            },
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(
                ValueError,
                "Invalid thread_registry: unresolved_thread_entries\\[0\\] is missing required fields: thread_id",
            ):
                save_chapter_handoff_packet(Path(tmp_dir), payload, "json")

    def test_save_chapter_handoff_packet_validates_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(
                ValueError,
                "Invalid chapter_handoff_packet: missing required fields: style_constraints",
            ):
                save_chapter_handoff_packet(
                    Path(tmp_dir),
                    {
                        "schema_name": "chapter_handoff_packet",
                        "schema_version": "1.0",
                        "chapter_number": 1,
                        "current_chapter_brief": {},
                        "relevant_scene_cards": [],
                        "relevant_canon_facts": [],
                        "unresolved_threads": [],
                        "previous_chapter_summary": "",
                    },
                    "json",
                )

    def test_load_chapter_handoff_packet_rejects_missing_style_constraint_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_artifact(
                Path(tmp_dir),
                "chapter_handoff_packet",
                {
                    "schema_name": "chapter_handoff_packet",
                    "schema_version": "1.0",
                    "chapter_number": 1,
                    "current_chapter_brief": {
                        "chapter_number": 1,
                        "purpose": "導入",
                        "goal": "異変に気づく",
                        "conflict": "状況が飲み込めない",
                        "turn": "時計が逆回転する",
                        "must_include": ["壊れた時計"],
                        "continuity_dependencies": ["ミナト"],
                        "foreshadowing_targets": ["seed-1"],
                        "arc_progress": "平穏から不安へ移る",
                        "target_length_guidance": "standard",
                    },
                    "relevant_scene_cards": [],
                    "relevant_canon_facts": [],
                    "unresolved_threads": [],
                    "previous_chapter_summary": "",
                    "style_constraints": {
                        "tone": "静謐",
                        "point_of_view": "ミナト",
                    },
                },
                "json",
            )

            with self.assertRaisesRegex(
                ValueError,
                "Invalid chapter_handoff_packet: style_constraints is missing required fields: tense",
            ):
                load_chapter_handoff_packet(Path(tmp_dir))

    def test_save_story_bible_writes_story_design_contract(self) -> None:
        payload = {
            "schema_name": "story_bible",
            "schema_version": "1.0",
            "core_premise": "記憶を失うたびに未来が書き換わる。",
            "ending_reveal": "喪失の原因は主人公自身の選択だった。",
            "theme_statement": "喪失の先でも選び直せる。",
            "character_arcs": [{"name": "ミナト", "want": "過去の回復", "need": "罪を認めること"}],
            "world_rules": ["記憶改変は一日一度だけ起きる"],
            "forbidden_facts": ["第1章では黒幕の正体を明かさない"],
            "foreshadowing_seeds": [{"id": "seed-1", "setup": "壊れた腕時計", "payoff_target": "終盤の真相"}],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            target = save_story_bible(Path(tmp_dir), payload, "json")
            saved = json.loads(target.read_text(encoding="utf-8"))

            self.assertEqual(target.name, "story_bible.json")
            self.assertEqual(saved, payload)

    def test_load_scene_cards_rejects_scene_count_out_of_range(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_artifact(
                Path(tmp_dir),
                "scene_cards",
                [{"chapter_number": 1, "scenes": []}],
                "json",
            )

            with self.assertRaisesRegex(ValueError, "scene_cards\\[0\\] must contain between 3 and 7 scenes"):
                load_scene_cards(Path(tmp_dir))

    def test_load_scene_cards_reads_valid_payload(self) -> None:
        payload = [
            {
                "chapter_number": 1,
                "scenes": [
                    {
                        "chapter_number": 1,
                        "scene_number": 1,
                        "scene_goal": "異変に気づく",
                        "scene_conflict": "記憶が曖昧になる",
                        "scene_turn": "腕時計が逆回転する",
                        "pov_character": "ミナト",
                        "participants": ["ミナト", "相棒"],
                        "setting": "駅前の路地",
                        "must_include": ["壊れた腕時計"],
                        "continuity_refs": ["chapter_briefs[0]"],
                        "foreshadowing_action": "周囲を見回す",
                        "exit_state": "違和感を抱えたまま移動する",
                    },
                    {
                        "chapter_number": 1,
                        "scene_number": 2,
                        "scene_goal": "手がかりを探す",
                        "scene_conflict": "手がかりが見つからない",
                        "scene_turn": "古いメモが見つかる",
                        "pov_character": "ミナト",
                        "participants": ["ミナト"],
                        "setting": "喫茶店",
                        "must_include": ["古いメモ"],
                        "continuity_refs": ["scene 1"],
                        "foreshadowing_action": "メモを読む",
                        "exit_state": "次の場所へ向かう",
                    },
                    {
                        "chapter_number": 1,
                        "scene_number": 3,
                        "scene_goal": "次章へつなぐ",
                        "scene_conflict": "敵の気配が近づく",
                        "scene_turn": "誰かに尾行されていると気づく",
                        "pov_character": "ミナト",
                        "participants": ["ミナト", "尾行者"],
                        "setting": "高架下",
                        "must_include": ["足音"],
                        "continuity_refs": ["scene 2"],
                        "foreshadowing_action": "走り出す",
                        "exit_state": "危機が迫る",
                    },
                ],
            }
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_scene_cards(Path(tmp_dir), payload)

            loaded = load_scene_cards(Path(tmp_dir))

            self.assertEqual(loaded, payload)

    def test_save_scene_cards_rejects_missing_scene_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(ValueError, "scene_cards\\[0\\]\\.scenes\\[0\\] is missing required fields: exit_state"):
                save_scene_cards(
                    Path(tmp_dir),
                    [
                        {
                            "chapter_number": 1,
                            "scenes": [
                                {
                                    "chapter_number": 1,
                                    "scene_number": 1,
                                    "scene_goal": "異変に気づく",
                                    "scene_conflict": "記憶が曖昧になる",
                                    "scene_turn": "腕時計が逆回転する",
                                    "pov_character": "ミナト",
                                    "participants": ["ミナト", "相棒"],
                                    "setting": "駅前の路地",
                                    "must_include": ["壊れた腕時計"],
                                    "continuity_refs": ["chapter_briefs[0]"],
                                    "foreshadowing_action": "周囲を見回す",
                                },
                                {
                                    "chapter_number": 1,
                                    "scene_number": 2,
                                    "scene_goal": "手がかりを探す",
                                    "scene_conflict": "手がかりが見つからない",
                                    "scene_turn": "古いメモが見つかる",
                                    "pov_character": "ミナト",
                                    "participants": ["ミナト"],
                                    "setting": "喫茶店",
                                    "must_include": ["古いメモ"],
                                    "continuity_refs": ["scene 1"],
                                    "foreshadowing_action": "メモを読む",
                                    "exit_state": "次の場所へ向かう",
                                },
                                {
                                    "chapter_number": 1,
                                    "scene_number": 3,
                                    "scene_goal": "次章へつなぐ",
                                    "scene_conflict": "敵の気配が近づく",
                                    "scene_turn": "誰かに尾行されていると気づく",
                                    "pov_character": "ミナト",
                                    "participants": ["ミナト", "尾行者"],
                                    "setting": "高架下",
                                    "must_include": ["足音"],
                                    "continuity_refs": ["scene 2"],
                                    "foreshadowing_action": "走り出す",
                                    "exit_state": "危機が迫る",
                                },
                            ],
                        }
                    ],
                )

    def test_save_chapter_briefs_rejects_non_sequential_numbering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(ValueError, "chapter_number sequence must be 1..len\\(payload\\)"):
                save_chapter_briefs(
                    Path(tmp_dir),
                    [
                        {
                            "chapter_number": 2,
                            "purpose": "導入",
                            "goal": "主人公に異変を認識させる",
                            "conflict": "記憶の欠落が広がる",
                            "turn": "壊れた腕時計が異常反応する",
                            "must_include": ["壊れた腕時計"],
                            "continuity_dependencies": ["第1話の違和感"],
                            "foreshadowing_targets": ["黒幕の手がかり"],
                            "arc_progress": "受け身の維持",
                            "target_length_guidance": "標準",
                        }
                    ],
                )

    def test_save_scene_cards_rejects_non_sequential_packet_numbering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(ValueError, "scene_cards\\[0\\] chapter_number sequence must be 1..len\\(payload\\)"):
                save_scene_cards(
                    Path(tmp_dir),
                    [
                        {
                            "chapter_number": 2,
                            "scenes": [
                                {
                                    "chapter_number": 2,
                                    "scene_number": 1,
                                    "scene_goal": "異変に気づく",
                                    "scene_conflict": "記憶が曖昧になる",
                                    "scene_turn": "腕時計が逆回転する",
                                    "pov_character": "ミナト",
                                    "participants": ["ミナト", "相棒"],
                                    "setting": "駅前の路地",
                                    "must_include": ["壊れた腕時計"],
                                    "continuity_refs": ["chapter_briefs[0]"],
                                    "foreshadowing_action": "周囲を見回す",
                                    "exit_state": "違和感を抱えたまま移動する",
                                },
                                {
                                    "chapter_number": 2,
                                    "scene_number": 2,
                                    "scene_goal": "手がかりを探す",
                                    "scene_conflict": "手がかりが見つからない",
                                    "scene_turn": "古いメモが見つかる",
                                    "pov_character": "ミナト",
                                    "participants": ["ミナト"],
                                    "setting": "喫茶店",
                                    "must_include": ["古いメモ"],
                                    "continuity_refs": ["scene 1"],
                                    "foreshadowing_action": "メモを読む",
                                    "exit_state": "次の場所へ向かう",
                                },
                                {
                                    "chapter_number": 2,
                                    "scene_number": 3,
                                    "scene_goal": "次章へつなぐ",
                                    "scene_conflict": "敵の気配が近づく",
                                    "scene_turn": "誰かに尾行されていると気づく",
                                    "pov_character": "ミナト",
                                    "participants": ["ミナト", "尾行者"],
                                    "setting": "高架下",
                                    "must_include": ["足音"],
                                    "continuity_refs": ["scene 2"],
                                    "foreshadowing_action": "走り出す",
                                    "exit_state": "危機が迫る",
                                },
                            ],
                        }
                    ],
                )

    def test_save_scene_cards_rejects_mismatched_scene_chapter_number(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(ValueError, "scene_cards\\[0\\]\\.scenes\\[0\\]\\.chapter_number must match parent chapter_number"):
                save_scene_cards(
                    Path(tmp_dir),
                    [
                        {
                            "chapter_number": 1,
                            "scenes": [
                                {
                                    "chapter_number": 2,
                                    "scene_number": 1,
                                    "scene_goal": "異変に気づく",
                                    "scene_conflict": "記憶が曖昧になる",
                                    "scene_turn": "腕時計が逆回転する",
                                    "pov_character": "ミナト",
                                    "participants": ["ミナト", "相棒"],
                                    "setting": "駅前の路地",
                                    "must_include": ["壊れた腕時計"],
                                    "continuity_refs": ["chapter_briefs[0]"],
                                    "foreshadowing_action": "周囲を見回す",
                                    "exit_state": "違和感を抱えたまま移動する",
                                },
                                {
                                    "chapter_number": 1,
                                    "scene_number": 2,
                                    "scene_goal": "手がかりを探す",
                                    "scene_conflict": "手がかりが見つからない",
                                    "scene_turn": "古いメモが見つかる",
                                    "pov_character": "ミナト",
                                    "participants": ["ミナト"],
                                    "setting": "喫茶店",
                                    "must_include": ["古いメモ"],
                                    "continuity_refs": ["scene 1"],
                                    "foreshadowing_action": "メモを読む",
                                    "exit_state": "次の場所へ向かう",
                                },
                                {
                                    "chapter_number": 1,
                                    "scene_number": 3,
                                    "scene_goal": "次章へつなぐ",
                                    "scene_conflict": "敵の気配が近づく",
                                    "scene_turn": "誰かに尾行されていると気づく",
                                    "pov_character": "ミナト",
                                    "participants": ["ミナト", "尾行者"],
                                    "setting": "高架下",
                                    "must_include": ["足音"],
                                    "continuity_refs": ["scene 2"],
                                    "foreshadowing_action": "走り出す",
                                    "exit_state": "危機が迫る",
                                },
                            ],
                        }
                    ],
                )

    def test_save_scene_cards_rejects_non_sequential_scene_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(ValueError, "scene_cards\\[0\\]\\.scenes sequence must be 1..len\\(scenes\\)"):
                save_scene_cards(
                    Path(tmp_dir),
                    [
                        {
                            "chapter_number": 1,
                            "scenes": [
                                {
                                    "chapter_number": 1,
                                    "scene_number": 2,
                                    "scene_goal": "異変に気づく",
                                    "scene_conflict": "記憶が曖昧になる",
                                    "scene_turn": "腕時計が逆回転する",
                                    "pov_character": "ミナト",
                                    "participants": ["ミナト", "相棒"],
                                    "setting": "駅前の路地",
                                    "must_include": ["壊れた腕時計"],
                                    "continuity_refs": ["chapter_briefs[0]"],
                                    "foreshadowing_action": "周囲を見回す",
                                    "exit_state": "違和感を抱えたまま移動する",
                                },
                                {
                                    "chapter_number": 1,
                                    "scene_number": 3,
                                    "scene_goal": "手がかりを探す",
                                    "scene_conflict": "手がかりが見つからない",
                                    "scene_turn": "古いメモが見つかる",
                                    "pov_character": "ミナト",
                                    "participants": ["ミナト"],
                                    "setting": "喫茶店",
                                    "must_include": ["古いメモ"],
                                    "continuity_refs": ["scene 1"],
                                    "foreshadowing_action": "メモを読む",
                                    "exit_state": "次の場所へ向かう",
                                },
                                {
                                    "chapter_number": 1,
                                    "scene_number": 4,
                                    "scene_goal": "次章へつなぐ",
                                    "scene_conflict": "敵の気配が近づく",
                                    "scene_turn": "誰かに尾行されていると気づく",
                                    "pov_character": "ミナト",
                                    "participants": ["ミナト", "尾行者"],
                                    "setting": "高架下",
                                    "must_include": ["足音"],
                                    "continuity_refs": ["scene 2"],
                                    "foreshadowing_action": "走り出す",
                                    "exit_state": "危機が迫る",
                                },
                            ],
                        }
                    ],
                )

    def test_load_story_bible_rejects_unsupported_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_artifact(
                Path(tmp_dir),
                "story_bible",
                {
                    "schema_name": "story_bible",
                    "schema_version": "9.9",
                    "core_premise": "記憶を失うたびに未来が書き換わる。",
                    "ending_reveal": "喪失の原因は主人公自身の選択だった。",
                    "theme_statement": "喪失の先でも選び直せる。",
                    "character_arcs": [],
                    "world_rules": [],
                    "forbidden_facts": [],
                    "foreshadowing_seeds": [],
                },
                "json",
            )

            with self.assertRaisesRegex(ValueError, "schema_version='9.9' is not supported; expected '1.0'"):
                load_story_bible(Path(tmp_dir))

    def test_load_story_bible_rejects_invalid_list_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_artifact(
                Path(tmp_dir),
                "story_bible",
                {
                    "schema_name": "story_bible",
                    "schema_version": "1.0",
                    "core_premise": "記憶を失うたびに未来が書き換わる。",
                    "ending_reveal": "喪失の原因は主人公自身の選択だった。",
                    "theme_statement": "喪失の先でも選び直せる。",
                    "character_arcs": [],
                    "world_rules": {"law": "time memory conservation"},
                    "forbidden_facts": [],
                    "foreshadowing_seeds": [],
                },
                "json",
            )

            with self.assertRaisesRegex(ValueError, "world_rules must be a list"):
                load_story_bible(Path(tmp_dir))

    def test_load_canon_ledger_rejects_unsupported_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_artifact(
                Path(tmp_dir),
                "canon_ledger",
                {
                    "schema_name": "canon_ledger",
                    "schema_version": "9.9",
                    "chapters": [
                        {
                            "chapter_number": 1,
                            "new_facts": [],
                            "changed_facts": [],
                            "open_questions": [],
                            "timeline_events": [],
                        }
                    ],
                },
                "json",
            )

            with self.assertRaisesRegex(ValueError, "schema_version='9.9' is not supported; expected '1.0'"):
                load_canon_ledger(Path(tmp_dir))

    def test_load_thread_registry_rejects_invalid_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_artifact(
                Path(tmp_dir),
                "thread_registry",
                {
                    "schema_name": "thread_registry",
                    "schema_version": "1.0",
                    "threads": [
                        {
                            "thread_id": "watch-mystery",
                            "label": "壊れた腕時計の謎",
                            "status": "paused",
                            "introduced_in_chapter": 1,
                            "last_updated_in_chapter": 1,
                            "related_characters": ["ミナト"],
                            "notes": ["駅前で逆回転が初登場した。"],
                        }
                    ],
                },
                "json",
            )

            with self.assertRaisesRegex(ValueError, "threads\\[0\\]\\.status must be one of: seeded, progressed, resolved, dropped"):
                load_thread_registry(Path(tmp_dir))

    def test_load_thread_registry_rejects_unsupported_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_artifact(
                Path(tmp_dir),
                "thread_registry",
                {
                    "schema_name": "thread_registry",
                    "schema_version": "9.9",
                    "threads": [
                        {
                            "thread_id": "watch-mystery",
                            "label": "壊れた腕時計の謎",
                            "status": "seeded",
                            "introduced_in_chapter": 1,
                            "last_updated_in_chapter": 1,
                            "related_characters": ["ミナト"],
                            "notes": ["駅前で逆回転が初登場した。"],
                        }
                    ],
                },
                "json",
            )

            with self.assertRaisesRegex(ValueError, "schema_version='9.9' is not supported; expected '1.0'"):
                load_thread_registry(Path(tmp_dir))

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
                        "best_run": {
                            "run_name": "latest_run",
                            "output_dir": str(Path(tmp_dir) / "latest_run"),
                            "comparison_metrics": {},
                            "comparison_basis": [],
                            "selection_source": "automatic",
                            "selection_reason": [],
                            "selection_reason_details": [],
                        },
                    },
                    "json",
                )

            with self.assertRaisesRegex(ValueError, "missing required fields: current_run, run_candidates"):
                load_project_manifest(project_dir)

    def test_load_project_manifest_backfills_missing_autonomy_level_to_assist(self) -> None:
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
                    "current_run": {
                        "name": "latest_run",
                        "output_dir": str(project_dir / "runs" / "latest_run"),
                        "comparison_metrics": {},
                        "comparison_basis": [],
                        "comparison_reason": [],
                        "comparison_reason_details": [],
                    },
                    "run_candidates": [],
                    "best_run": {
                        "run_name": "latest_run",
                        "output_dir": str(project_dir / "runs" / "latest_run"),
                        "comparison_metrics": {},
                        "comparison_basis": [],
                        "selection_source": "automatic",
                        "selection_reason": [],
                        "selection_reason_details": [],
                    },
                },
                "json",
            )

            loaded = load_project_manifest(project_dir)

            self.assertEqual(loaded["autonomy_level"], "assist")

    def test_load_project_manifest_rejects_invalid_autonomy_level(self) -> None:
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
                    "autonomy_level": "chaos",
                    "current_run": {
                        "name": "latest_run",
                        "output_dir": str(project_dir / "runs" / "latest_run"),
                        "comparison_metrics": {},
                        "comparison_basis": [],
                        "comparison_reason": [],
                        "comparison_reason_details": [],
                    },
                    "run_candidates": [],
                    "best_run": {
                        "run_name": "latest_run",
                        "output_dir": str(project_dir / "runs" / "latest_run"),
                        "comparison_metrics": {},
                        "comparison_basis": [],
                        "selection_source": "automatic",
                        "selection_reason": [],
                        "selection_reason_details": [],
                    },
                },
                "json",
            )

            with self.assertRaisesRegex(ValueError, r"autonomy_level=.*is not supported"):
                load_project_manifest(project_dir)

    def test_load_project_manifest_rejects_null_autonomy_level(self) -> None:
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
                    "autonomy_level": None,
                    "current_run": {
                        "name": "latest_run",
                        "output_dir": str(project_dir / "runs" / "latest_run"),
                        "comparison_metrics": {},
                        "comparison_basis": [],
                        "comparison_reason": [],
                        "comparison_reason_details": [],
                    },
                    "run_candidates": [],
                    "best_run": {
                        "run_name": "latest_run",
                        "output_dir": str(project_dir / "runs" / "latest_run"),
                        "comparison_metrics": {},
                        "comparison_basis": [],
                        "selection_source": "automatic",
                        "selection_reason": [],
                        "selection_reason_details": [],
                    },
                },
                "json",
            )

            with self.assertRaisesRegex(ValueError, r"autonomy_level=None is not supported"):
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
                        "current_run": {
                            "name": "latest_run",
                            "output_dir": str(Path(tmp_dir) / "latest_run"),
                            "comparison_metrics": {},
                            "comparison_basis": [],
                            "comparison_reason": [],
                            "comparison_reason_details": [],
                        },
                        "run_candidates": [],
                        "best_run": {
                            "run_name": "latest_run",
                            "output_dir": str(Path(tmp_dir) / "latest_run"),
                            "comparison_metrics": {},
                            "comparison_basis": [],
                            "selection_source": "automatic",
                            "selection_reason": [],
                            "selection_reason_details": [],
                        },
                    },
                    "json",
                )

            with self.assertRaisesRegex(ValueError, "schema_version='9.9' is not supported; expected '1.0'"):
                load_project_manifest(project_dir)

    def test_load_project_manifest_rejects_unknown_reason_detail_code(self) -> None:
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
                    "current_run": {
                        "name": "latest_run",
                        "output_dir": str(project_dir / "runs" / "latest_run"),
                        "comparison_metrics": {},
                        "comparison_basis": [],
                        "comparison_reason": [],
                        "comparison_reason_details": [{"code": "unknown_reason", "value": 1}],
                    },
                    "run_candidates": [
                        {
                            "run_name": "latest_run",
                            "output_dir": str(project_dir / "runs" / "latest_run"),
                            "comparison_metrics": {},
                            "comparison_basis": [],
                            "comparison_reason": [],
                            "comparison_reason_details": [],
                        }
                    ],
                    "best_run": {
                        "run_name": "latest_run",
                        "output_dir": str(project_dir / "runs" / "latest_run"),
                        "comparison_metrics": {},
                        "comparison_basis": [],
                        "selection_source": "automatic",
                        "selection_reason": [],
                        "selection_reason_details": [],
                    },
                },
                "json",
            )

            with self.assertRaisesRegex(
                ValueError,
                r"current_run\.comparison_reason_details\[0\]\.code='unknown_reason' is not supported",
            ):
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

    def test_load_publish_ready_bundle_rejects_missing_or_invalid_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_payload = {
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
                    "manuscript": {"field": "chapters"},
                    "story_summary": {"field": "story_summary"},
                    "quality": {"field": "overall_quality_report"},
                },
            }

            save_artifact(Path(tmp_dir), "publish_ready_bundle", base_payload, "json")
            with self.assertRaisesRegex(ValueError, "Invalid publish_ready_bundle: summary must be an object."):
                load_publish_ready_bundle(Path(tmp_dir))

            save_artifact(Path(tmp_dir), "publish_ready_bundle", {**base_payload, "summary": "not-a-dict"}, "json")
            with self.assertRaisesRegex(ValueError, "Invalid publish_ready_bundle: summary must be an object."):
                load_publish_ready_bundle(Path(tmp_dir))

    def test_load_publish_ready_bundle_rejects_invalid_story_state_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            payload = {
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
                    "manuscript": {"field": "chapters"},
                    "story_summary": {"field": "story_summary"},
                    "quality": {"field": "overall_quality_report"},
                },
                    "summary": {
                        "title": "Case 01",
                        "chapter_count": 1,
                        "section_names": ["manuscript", "story_summary", "quality"],
                        "source_artifact_names": ["chapter_1_draft"],
                        "story_state_summary": {
                            "evaluated_through_chapter": 1,
                            "canon_chapter_count": 1,
                            "thread_count": 2,
                            "unresolved_thread_count": 1,
                            "resolved_thread_count": 1,
                            "open_question_count": 3,
                            "latest_timeline_event_count": "invalid",
                        },
                    },
                }

            save_artifact(Path(tmp_dir), "publish_ready_bundle", payload, "json")
            with self.assertRaisesRegex(
                ValueError,
                "Invalid publish_ready_bundle: summary.story_state_summary.latest_timeline_event_count must be an int.",
            ):
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
