import json
import importlib.util
import tempfile
import unittest
from pathlib import Path

from novel_writer.schema import StoryArtifacts, StoryInput
from novel_writer.storage import (
    build_project_layout,
    load_artifact,
    load_canon_ledger,
    load_chapter_briefs,
    load_scene_cards,
    load_project_manifest,
    load_publish_ready_bundle,
    load_run_comparison_summary,
    load_story_bible,
    load_thread_registry,
    normalize_project_id,
    resolve_artifact_path,
    save_artifact,
    save_canon_ledger,
    save_chapter_briefs,
    save_scene_cards,
    save_publish_ready_bundle,
    save_project_manifest,
    save_run_comparison_summary,
    save_story_bible,
    save_thread_registry,
    upsert_canon_ledger_chapter,
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
        self.assertEqual(contract["thread_registry"]["schema_name"], "thread_registry")
        self.assertEqual(contract["thread_registry"]["schema_version"], "1.0")

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
