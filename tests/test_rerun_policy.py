import json
import tempfile
import unittest
from pathlib import Path

from novel_writer.pipeline import StoryPipeline
from novel_writer.rerun_policy import ContinuityRerunPolicy
from novel_writer.schema import StoryInput


class SequencedContinuityChecker:
    def __init__(self, reports: list[dict]) -> None:
        self.reports = reports
        self.calls = 0

    def build_report(self, artifacts, chapter_index=0) -> dict:
        report = self.reports[min(self.calls, len(self.reports) - 1)]
        self.calls += 1
        return report

    def build_quality_report(self, continuity_report) -> dict:
        issue_counts = continuity_report.get("issue_counts", {})
        overall_recommendation = "accept" if sum(issue_counts.values()) == 0 else "revise"
        return {
            "overall_recommendation": overall_recommendation,
            "severity": continuity_report.get("severity", "unknown"),
            "source_report": "continuity_report",
            "recommendations": [],
            "issue_counts": issue_counts,
            "total_issue_count": sum(issue_counts.values()),
        }

    def build_project_quality_report(self, artifacts) -> dict:
        return {
            "overall_recommendation": "accept",
            "source_report": "project_quality_report",
            "checks": {},
            "issue_count": 0,
            "issues": [],
        }


class CountingLLMClient:
    def __init__(self) -> None:
        self.chapter_plan_calls = 0
        self.chapter_briefs_calls = 0
        self.scene_cards_calls = 0
        self.chapter_draft_calls = 0
        self.revise_calls = 0

    def generate_loglines(self, story_input):
        return [{"id": "logline-1", "title": "案", "premise": "前提", "hook": "フック"}]

    def generate_characters(self, story_input, logline):
        return [{"name": "篠崎 遥", "role": "protagonist", "goal": "goal", "conflict": "conflict", "arc": "arc"}]

    def generate_three_act_plot(self, story_input, logline, characters):
        return {
            "act_1": {"setup": "setup", "inciting_incident": "incident"},
            "act_2": {"rising_action": "rising", "crisis": "crisis"},
            "act_3": {"resolution": "resolution"},
        }

    def generate_story_bible(self, story_input, logline, characters, three_act_plot):
        return {
            "schema_name": "story_bible",
            "schema_version": "1.0",
            "core_premise": logline["premise"],
            "ending_reveal": "resolution",
            "theme_statement": f"{story_input.theme} を通じて変化を描く。",
            "character_arcs": characters,
            "world_rules": ["rule-1"],
            "forbidden_facts": ["fact-1"],
            "foreshadowing_seeds": [{"id": "seed-1", "setup": "setup", "payoff_target": "resolution"}],
        }

    def generate_chapter_plan(self, story_input, logline, characters, three_act_plot, story_bible):
        self.chapter_plan_calls += 1
        return [
            {
                "chapter_number": 1,
                "title": f"第1章 導入 {self.chapter_plan_calls}",
                "purpose": f"setup {story_bible['theme_statement']}",
                "point_of_view": "篠崎 遥",
                "target_words": 1000,
            },
            {
                "chapter_number": 2,
                "title": f"第2章 対立 {self.chapter_plan_calls}",
                "purpose": f"conflict {story_bible['ending_reveal']}",
                "point_of_view": "篠崎 遥",
                "target_words": 1000,
            }
        ]

    def generate_chapter_briefs(
        self,
        story_input,
        logline,
        characters,
        three_act_plot,
        story_bible,
        chapter_plan,
    ):
        self.chapter_briefs_calls += 1
        return [
            {
                "chapter_number": chapter["chapter_number"],
                "purpose": chapter["purpose"],
                "goal": f"{chapter['title']} で物語を進める",
                "conflict": f"{three_act_plot['act_2'].get('rising_action', 'rising')} が障害になる",
                "turn": story_bible["ending_reveal"],
                "must_include": [story_bible["foreshadowing_seeds"][0]["id"]],
                "continuity_dependencies": [characters[0]["name"]],
                "foreshadowing_targets": [story_bible["foreshadowing_seeds"][0]["id"]],
                "arc_progress": characters[0]["arc"],
                "target_length_guidance": "standard",
            }
            for chapter in chapter_plan
        ]

    def generate_scene_cards(
        self,
        story_input,
        logline,
        characters,
        three_act_plot,
        story_bible,
        chapter_plan,
        chapter_briefs,
    ):
        self.scene_cards_calls += 1
        return [
            {
                "chapter_number": brief["chapter_number"],
                "scenes": [
                    {
                        "chapter_number": brief["chapter_number"],
                        "scene_number": 1,
                        "scene_goal": brief["goal"],
                        "scene_conflict": brief["conflict"],
                        "scene_turn": "前提が揺らぐ",
                        "pov_character": chapter_plan[index]["point_of_view"],
                        "participants": [characters[0]["name"]],
                        "setting": f"scene-{brief['chapter_number']}",
                        "must_include": brief["must_include"],
                        "continuity_refs": brief["continuity_dependencies"],
                        "foreshadowing_action": "seed",
                        "exit_state": "選択を先送りする",
                    },
                    {
                        "chapter_number": brief["chapter_number"],
                        "scene_number": 2,
                        "scene_goal": "対立を悪化させる",
                        "scene_conflict": brief["conflict"],
                        "scene_turn": three_act_plot["act_2"]["rising_action"],
                        "pov_character": chapter_plan[index]["point_of_view"],
                        "participants": [characters[0]["name"]],
                        "setting": f"scene-{brief['chapter_number']}-2",
                        "must_include": brief["must_include"],
                        "continuity_refs": brief["continuity_dependencies"],
                        "foreshadowing_action": "progress",
                        "exit_state": "後戻りしにくくなる",
                    },
                    {
                        "chapter_number": brief["chapter_number"],
                        "scene_number": 3,
                        "scene_goal": brief["goal"],
                        "scene_conflict": brief["conflict"],
                        "scene_turn": three_act_plot["act_3"]["resolution"],
                        "pov_character": chapter_plan[index]["point_of_view"],
                        "participants": [characters[0]["name"]],
                        "setting": f"scene-{brief['chapter_number']}-3",
                        "must_include": brief["must_include"],
                        "continuity_refs": brief["continuity_dependencies"],
                        "foreshadowing_action": "payoff_or_seed",
                        "exit_state": brief["turn"],
                    }
                ],
            }
            for index, brief in enumerate(chapter_briefs)
        ]

    def generate_chapter_draft(
        self,
        story_input,
        logline,
        characters,
        three_act_plot,
        chapter_plan,
        chapter_briefs,
        scene_cards,
        canon_ledger,
        thread_registry,
        chapter_index=0,
        chapter_handoff_packet=None,
    ):
        self.chapter_draft_calls += 1
        chapter = chapter_plan[chapter_index]
        brief = chapter_briefs[chapter_index]
        scene_packet = scene_cards[chapter_index]
        return {
            "chapter_number": chapter["chapter_number"],
            "title": chapter["title"],
            "summary": brief["goal"],
            "text": (
                f"{three_act_plot['act_1']['setup']} "
                f"{scene_packet['scenes'][0]['exit_state']} "
                f"篠崎 遥の草稿 {self.chapter_draft_calls}"
            ),
        }

    def revise_chapter_draft(
        self,
        story_input,
        chapter_plan,
        chapter_draft,
        continuity_report,
        chapter_index=0,
    ):
        self.revise_calls += 1
        return {
            "chapter_number": chapter_draft["chapter_number"],
            "title": chapter_draft["title"],
            "summary": chapter_plan[chapter_index]["purpose"],
            "chapter_index": chapter_index,
            "text": f"{chapter_draft['text']} 改稿済み",
            "source_issue_counts": continuity_report.get("issue_counts", {}),
        }

    def generate_story_summary(self, story_input, logline, chapter_plan, revised_chapter_drafts):
        return {
            "title": logline["title"],
            "synopsis": " ".join(draft["summary"] for draft in revised_chapter_drafts),
            "chapter_count": len(chapter_plan),
            "chapter_summaries": [
                {
                    "chapter_number": chapter["chapter_number"],
                    "title": chapter["title"],
                    "summary": draft["summary"],
                }
                for chapter, draft in zip(chapter_plan, revised_chapter_drafts)
            ],
        }


class ContinuityRerunPolicyTest(unittest.TestCase):
    def test_policy_classifies_levels(self) -> None:
        policy = ContinuityRerunPolicy()

        low = policy.decide(
            {
                "missing_fields": 0,
                "character_name_mismatches": 0,
                "plot_to_plan_gaps": 0,
                "plan_to_draft_gaps": 0,
                "length_warnings": 1,
            }
        )
        medium = policy.decide(
            {
                "missing_fields": 0,
                "character_name_mismatches": 1,
                "plot_to_plan_gaps": 0,
                "plan_to_draft_gaps": 1,
                "length_warnings": 0,
            }
        )
        high = policy.decide(
            {
                "missing_fields": 1,
                "character_name_mismatches": 0,
                "plot_to_plan_gaps": 0,
                "plan_to_draft_gaps": 0,
                "length_warnings": 0,
            }
        )

        self.assertEqual(low.severity, "low")
        self.assertEqual(medium.severity, "medium")
        self.assertEqual(high.severity, "high")

    def test_policy_can_stop_long_run_when_high_severity_chapters_accumulate(self) -> None:
        policy = ContinuityRerunPolicy(
            {
                **ContinuityRerunPolicy().config,
                "long_run": {
                    "max_high_severity_chapters": 2,
                    "max_total_rerun_attempts": 99,
                },
            }
        )

        decision = policy.decide_long_run(
            [
                {"severity": "high"},
                {"severity": "low"},
                {"severity": "high"},
            ],
            [{"attempt": 1}, {"attempt": 2}],
        )

        self.assertTrue(decision["should_stop"])
        self.assertEqual(decision["reason"], "high_severity_chapter_limit_reached")
        self.assertEqual(decision["high_severity_chapters"], 2)
        self.assertEqual(decision["stop_after_step"], "continuity_report")
        self.assertEqual(decision["remaining_high_severity_chapter_budget"], 0)
        self.assertTrue(decision["resume_requires_explicit_rerun"])
        self.assertIn("explicit rerun", decision["resume_guidance"])

    def test_medium_reruns_only_chapter_draft(self) -> None:
        client = CountingLLMClient()
        checker = SequencedContinuityChecker(
            [
                {
                    "missing_fields": [],
                    "character_name_mismatches": [{"reason": "x"}],
                    "plot_to_plan_gaps": [],
                    "plan_to_draft_gaps": [{"reason": "y"}],
                    "length_warnings": [],
                    "issue_counts": {
                        "missing_fields": 0,
                        "character_name_mismatches": 0,
                        "plot_to_plan_gaps": 0,
                        "plan_to_draft_gaps": 0,
                        "length_warnings": 0,
                    },
                },
                {
                    "missing_fields": [],
                    "character_name_mismatches": [{"reason": "x"}],
                    "plot_to_plan_gaps": [],
                    "plan_to_draft_gaps": [{"reason": "y"}],
                    "length_warnings": [],
                    "issue_counts": {
                        "missing_fields": 0,
                        "character_name_mismatches": 1,
                        "plot_to_plan_gaps": 0,
                        "plan_to_draft_gaps": 1,
                        "length_warnings": 0,
                    },
                },
                {
                    "missing_fields": [],
                    "character_name_mismatches": [],
                    "plot_to_plan_gaps": [],
                    "plan_to_draft_gaps": [],
                    "length_warnings": [],
                    "issue_counts": {
                        "missing_fields": 0,
                        "character_name_mismatches": 0,
                        "plot_to_plan_gaps": 0,
                        "plan_to_draft_gaps": 0,
                        "length_warnings": 0,
                    },
                },
                {
                    "missing_fields": [],
                    "character_name_mismatches": [],
                    "plot_to_plan_gaps": [],
                    "plan_to_draft_gaps": [],
                    "length_warnings": [],
                    "issue_counts": {
                        "missing_fields": 0,
                        "character_name_mismatches": 0,
                        "plot_to_plan_gaps": 0,
                        "plan_to_draft_gaps": 0,
                        "length_warnings": 0,
                    },
                },
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            pipeline = StoryPipeline(client, Path(tmp_dir), continuity_checker=checker)
            artifacts = pipeline.run(StoryInput(theme="記憶", genre="SF", tone="静謐", target_length=5000))
            canon_ledger = json.loads((Path(tmp_dir) / "canon_ledger.json").read_text(encoding="utf-8"))
            thread_registry = json.loads((Path(tmp_dir) / "thread_registry.json").read_text(encoding="utf-8"))

        self.assertEqual(client.chapter_plan_calls, 1)
        self.assertEqual(client.chapter_draft_calls, 3)
        self.assertEqual(client.revise_calls, 2)
        self.assertEqual(artifacts.continuity_report["severity"], "low")
        self.assertEqual(artifacts.rerun_history[0]["severity"], "low")
        self.assertEqual(artifacts.rerun_history[1]["severity"], "medium")
        self.assertEqual(artifacts.rerun_history[2]["action_taken"], "reran_chapter_draft")
        self.assertEqual(artifacts.rerun_history[2]["chapter_index"], 1)
        self.assertEqual(artifacts.revised_chapter_1_draft["summary"], "setup 記憶 を通じて変化を描く。")
        self.assertEqual(artifacts.revised_chapter_1_draft["chapter_index"], 0)
        self.assertEqual(artifacts.revised_chapter_drafts[1]["chapter_index"], 1)
        self.assertEqual(
            canon_ledger["chapters"][1]["new_facts"],
            [artifacts.revised_chapter_drafts[1]["summary"]],
        )
        self.assertEqual(thread_registry["threads"][0]["last_updated_in_chapter"], 2)

    def test_high_reruns_from_chapter_plan(self) -> None:
        client = CountingLLMClient()
        checker = SequencedContinuityChecker(
            [
                {
                    "missing_fields": [{"reason": "missing"}],
                    "character_name_mismatches": [],
                    "plot_to_plan_gaps": [],
                    "plan_to_draft_gaps": [],
                    "length_warnings": [],
                    "issue_counts": {
                        "missing_fields": 1,
                        "character_name_mismatches": 0,
                        "plot_to_plan_gaps": 0,
                        "plan_to_draft_gaps": 0,
                        "length_warnings": 0,
                    },
                },
                {
                    "missing_fields": [],
                    "character_name_mismatches": [],
                    "plot_to_plan_gaps": [],
                    "plan_to_draft_gaps": [],
                    "length_warnings": [],
                    "issue_counts": {
                        "missing_fields": 0,
                        "character_name_mismatches": 0,
                        "plot_to_plan_gaps": 0,
                        "plan_to_draft_gaps": 0,
                        "length_warnings": 0,
                    },
                },
                {
                    "missing_fields": [],
                    "character_name_mismatches": [],
                    "plot_to_plan_gaps": [],
                    "plan_to_draft_gaps": [],
                    "length_warnings": [],
                    "issue_counts": {
                        "missing_fields": 0,
                        "character_name_mismatches": 0,
                        "plot_to_plan_gaps": 0,
                        "plan_to_draft_gaps": 0,
                        "length_warnings": 0,
                    },
                },
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            pipeline = StoryPipeline(client, Path(tmp_dir), continuity_checker=checker)
            artifacts = pipeline.run(StoryInput(theme="記憶", genre="SF", tone="静謐", target_length=5000))
            canon_ledger = json.loads((Path(tmp_dir) / "canon_ledger.json").read_text(encoding="utf-8"))
            thread_registry = json.loads((Path(tmp_dir) / "thread_registry.json").read_text(encoding="utf-8"))

        self.assertEqual(client.chapter_plan_calls, 2)
        self.assertEqual(client.chapter_draft_calls, 4)
        self.assertEqual(client.revise_calls, 2)
        self.assertEqual(artifacts.rerun_history[0]["severity"], "high")
        self.assertEqual(artifacts.rerun_history[1]["action_taken"], "reran_from_chapter_plan")
        self.assertEqual(artifacts.rerun_history[1]["chapter_index"], 0)
        self.assertEqual(
            canon_ledger["chapters"][0]["new_facts"],
            [artifacts.revised_chapter_drafts[0]["summary"]],
        )
        self.assertEqual(thread_registry["threads"][0]["introduced_in_chapter"], 1)

    def test_revision_loop_uses_per_chapter_quality_reports(self) -> None:
        client = CountingLLMClient()
        checker = SequencedContinuityChecker(
            [
                {
                    "missing_fields": [],
                    "character_name_mismatches": [],
                    "plot_to_plan_gaps": [],
                    "plan_to_draft_gaps": [],
                    "length_warnings": [],
                    "chapter_length_balance_warnings": [],
                    "issue_counts": {
                        "missing_fields": 0,
                        "character_name_mismatches": 0,
                        "plot_to_plan_gaps": 0,
                        "plan_to_draft_gaps": 0,
                        "length_warnings": 0,
                        "chapter_length_balance_warnings": 0,
                    },
                },
                {
                    "missing_fields": [],
                    "character_name_mismatches": [],
                    "plot_to_plan_gaps": [],
                    "plan_to_draft_gaps": [],
                    "length_warnings": [],
                    "chapter_length_balance_warnings": [{"reason": "balance"}],
                    "issue_counts": {
                        "missing_fields": 0,
                        "character_name_mismatches": 0,
                        "plot_to_plan_gaps": 0,
                        "plan_to_draft_gaps": 0,
                        "length_warnings": 0,
                        "chapter_length_balance_warnings": 1,
                    },
                },
                {
                    "missing_fields": [],
                    "character_name_mismatches": [],
                    "plot_to_plan_gaps": [],
                    "plan_to_draft_gaps": [],
                    "length_warnings": [],
                    "chapter_length_balance_warnings": [],
                    "issue_counts": {
                        "missing_fields": 0,
                        "character_name_mismatches": 0,
                        "plot_to_plan_gaps": 0,
                        "plan_to_draft_gaps": 0,
                        "length_warnings": 0,
                        "chapter_length_balance_warnings": 0,
                    },
                },
                {
                    "missing_fields": [],
                    "character_name_mismatches": [],
                    "plot_to_plan_gaps": [],
                    "plan_to_draft_gaps": [],
                    "length_warnings": [],
                    "chapter_length_balance_warnings": [{"reason": "balance"}],
                    "issue_counts": {
                        "missing_fields": 0,
                        "character_name_mismatches": 0,
                        "plot_to_plan_gaps": 0,
                        "plan_to_draft_gaps": 0,
                        "length_warnings": 0,
                        "chapter_length_balance_warnings": 1,
                    },
                },
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            pipeline = StoryPipeline(client, Path(tmp_dir), continuity_checker=checker)
            artifacts = pipeline.run(StoryInput(theme="記憶", genre="SF", tone="静謐", target_length=5000))

        self.assertEqual(client.revise_calls, 3)
        chapter_0_attempts = [entry for entry in artifacts.revise_history if entry["chapter_index"] == 0]
        chapter_1_attempts = [entry for entry in artifacts.revise_history if entry["chapter_index"] == 1]
        self.assertEqual(len(chapter_0_attempts), 1)
        self.assertEqual(len(chapter_1_attempts), 2)
        self.assertEqual(artifacts.revised_chapter_drafts[1]["source_issue_counts"]["chapter_length_balance_warnings"], 1)

    def test_pipeline_stops_before_revision_when_long_run_limit_is_reached(self) -> None:
        client = CountingLLMClient()
        checker = SequencedContinuityChecker(
            [
                {
                    "missing_fields": [{"reason": "missing"}],
                    "character_name_mismatches": [],
                    "plot_to_plan_gaps": [],
                    "plan_to_draft_gaps": [],
                    "length_warnings": [],
                    "issue_counts": {
                        "missing_fields": 1,
                        "character_name_mismatches": 0,
                        "plot_to_plan_gaps": 0,
                        "plan_to_draft_gaps": 0,
                        "length_warnings": 0,
                    },
                },
                {
                    "missing_fields": [{"reason": "missing"}],
                    "character_name_mismatches": [],
                    "plot_to_plan_gaps": [],
                    "plan_to_draft_gaps": [],
                    "length_warnings": [],
                    "issue_counts": {
                        "missing_fields": 1,
                        "character_name_mismatches": 0,
                        "plot_to_plan_gaps": 0,
                        "plan_to_draft_gaps": 0,
                        "length_warnings": 0,
                    },
                },
                {
                    "missing_fields": [{"reason": "missing"}],
                    "character_name_mismatches": [],
                    "plot_to_plan_gaps": [],
                    "plan_to_draft_gaps": [],
                    "length_warnings": [],
                    "issue_counts": {
                        "missing_fields": 1,
                        "character_name_mismatches": 0,
                        "plot_to_plan_gaps": 0,
                        "plan_to_draft_gaps": 0,
                        "length_warnings": 0,
                    },
                },
                {
                    "missing_fields": [{"reason": "missing"}],
                    "character_name_mismatches": [],
                    "plot_to_plan_gaps": [],
                    "plan_to_draft_gaps": [],
                    "length_warnings": [],
                    "issue_counts": {
                        "missing_fields": 1,
                        "character_name_mismatches": 0,
                        "plot_to_plan_gaps": 0,
                        "plan_to_draft_gaps": 0,
                        "length_warnings": 0,
                    },
                },
            ]
        )
        policy = ContinuityRerunPolicy(
            {
                **ContinuityRerunPolicy().config,
                "long_run": {
                    "max_high_severity_chapters": 2,
                    "max_total_rerun_attempts": 99,
                },
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            pipeline = StoryPipeline(client, Path(tmp_dir), continuity_checker=checker, rerun_policy=policy)
            artifacts = pipeline.run(StoryInput(theme="記憶", genre="SF", tone="静謐", target_length=5000))
            manifest = Path(tmp_dir) / "manifest.json"
            canon_ledger = json.loads((Path(tmp_dir) / "canon_ledger.json").read_text(encoding="utf-8"))
            thread_registry = json.loads((Path(tmp_dir) / "thread_registry.json").read_text(encoding="utf-8"))

            self.assertTrue(manifest.exists())
            self.assertEqual(client.revise_calls, 0)
            self.assertFalse(artifacts.revised_chapter_drafts)
            self.assertFalse(artifacts.story_summary)
            self.assertFalse(artifacts.project_quality_report)
            self.assertEqual(
                canon_ledger["chapters"][0]["new_facts"],
                [artifacts.chapter_drafts[0]["summary"]],
            )
            self.assertEqual(thread_registry["threads"][0]["introduced_in_chapter"], 1)
            self.assertIn('"should_stop": true', manifest.read_text(encoding="utf-8").lower())
            self.assertIn('"stop_after_step": "continuity_report"', manifest.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
