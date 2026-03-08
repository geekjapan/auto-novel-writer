import unittest

from novel_writer.continuity import ContinuityChecker
from novel_writer.schema import StoryArtifacts, StoryInput


class ContinuityCheckerTest(unittest.TestCase):
    def test_build_report_detects_structural_gaps(self) -> None:
        artifacts = StoryArtifacts(
            story_input=StoryInput(theme="秘密", genre="ミステリ", tone="静謐", target_length=6000),
            loglines=[
                {
                    "id": "logline-1",
                    "title": "消えた手紙",
                    "premise": "消えた手紙を追う短編。",
                    "hook": "真相は身近な場所にある。",
                }
            ],
            characters=[
                {
                    "name": "篠崎 遥",
                    "role": "protagonist",
                    "goal": "真相解明",
                    "conflict": "過去と向き合えない",
                    "arc": "受動から能動へ",
                }
            ],
            three_act_plot={
                "act_1": {"setup": "主人公は手紙を失う。", "inciting_incident": "謎の電話が来る。"},
                "act_2": {"rising_action": "旧友を疑う。", "crisis": "親友が姿を消す。"},
                "act_3": {"resolution": "手紙は自宅にあったと判明する。"},
            },
            chapter_plan=[
                {
                    "chapter_number": 1,
                    "title": "第1章 導入",
                    "purpose": "主人公は手紙を失う。",
                    "point_of_view": "別人 視点",
                    "target_words": 1200,
                }
            ],
            chapter_1_draft={
                "chapter_number": 1,
                "title": "第1章 導入",
                "summary": "主人公は手紙を失う。",
                "text": "篠崎 遥は机の引き出しを見つめた。",
            },
        )

        report = ContinuityChecker().build_report(artifacts)

        self.assertEqual(report["missing_fields"], [])
        self.assertTrue(report["character_name_mismatches"])
        self.assertTrue(report["plot_to_plan_gaps"])
        self.assertTrue(report["plan_to_draft_gaps"])
        self.assertTrue(report["length_warnings"])


if __name__ == "__main__":
    unittest.main()
