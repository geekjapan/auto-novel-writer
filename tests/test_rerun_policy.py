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

    def build_report(self, artifacts) -> dict:
        report = self.reports[min(self.calls, len(self.reports) - 1)]
        self.calls += 1
        return report


class CountingLLMClient:
    def __init__(self) -> None:
        self.chapter_plan_calls = 0
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

    def generate_chapter_plan(self, story_input, logline, characters, three_act_plot):
        self.chapter_plan_calls += 1
        return [
            {
                "chapter_number": 1,
                "title": f"第1章 導入 {self.chapter_plan_calls}",
                "purpose": "setup",
                "point_of_view": "篠崎 遥",
                "target_words": 1000,
            }
        ]

    def generate_chapter_draft(self, story_input, logline, characters, chapter_plan, chapter_index=0):
        self.chapter_draft_calls += 1
        return {
            "chapter_number": 1,
            "title": chapter_plan[0]["title"],
            "summary": chapter_plan[0]["purpose"],
            "text": f"篠崎 遥の草稿 {self.chapter_draft_calls}",
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
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            pipeline = StoryPipeline(client, Path(tmp_dir), continuity_checker=checker)
            artifacts = pipeline.run(StoryInput(theme="記憶", genre="SF", tone="静謐", target_length=5000))

        self.assertEqual(client.chapter_plan_calls, 1)
        self.assertEqual(client.chapter_draft_calls, 2)
        self.assertEqual(client.revise_calls, 1)
        self.assertEqual(artifacts.continuity_report["severity"], "low")
        self.assertEqual(artifacts.rerun_history[0]["severity"], "medium")
        self.assertEqual(artifacts.rerun_history[1]["action_taken"], "reran_chapter_1_draft")
        self.assertEqual(artifacts.revised_chapter_1_draft["summary"], "setup")
        self.assertEqual(artifacts.revised_chapter_1_draft["chapter_index"], 0)

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
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            pipeline = StoryPipeline(client, Path(tmp_dir), continuity_checker=checker)
            artifacts = pipeline.run(StoryInput(theme="記憶", genre="SF", tone="静謐", target_length=5000))

        self.assertEqual(client.chapter_plan_calls, 2)
        self.assertEqual(client.chapter_draft_calls, 2)
        self.assertEqual(client.revise_calls, 1)
        self.assertEqual(artifacts.rerun_history[0]["severity"], "high")
        self.assertEqual(artifacts.rerun_history[1]["action_taken"], "reran_from_chapter_plan")


if __name__ == "__main__":
    unittest.main()
