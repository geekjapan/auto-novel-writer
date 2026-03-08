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

    def test_keyword_overlap_reduces_false_positive_for_plot_and_summary(self) -> None:
        artifacts = StoryArtifacts(
            story_input=StoryInput(theme="秘密", genre="ミステリ", tone="静謐", target_length=3000),
            loglines=[{"id": "logline-1", "title": "消えた手紙", "premise": "前提", "hook": "フック"}],
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
                "act_1": {"setup": "主人公は古い手紙を失う。", "inciting_incident": "謎の電話が夜に来る。"},
                "act_2": {"rising_action": "旧友への疑いが深まる。", "crisis": "親友が姿を消す。"},
                "act_3": {"resolution": "手紙は自宅の机で見つかる。"},
            },
            chapter_plan=[
                {
                    "chapter_number": 1,
                    "title": "第1章 導入",
                    "purpose": "古い手紙をなくした主人公が夜の電話を受ける。",
                    "point_of_view": "篠崎 遥",
                    "target_words": 250,
                },
                {
                    "chapter_number": 2,
                    "title": "第2章 対立",
                    "purpose": "旧友への疑いが深まり、親友が姿を消す。",
                    "point_of_view": "篠崎 遥",
                    "target_words": 250,
                },
                {
                    "chapter_number": 3,
                    "title": "第3章 結末",
                    "purpose": "自宅の机から手紙が見つかる。",
                    "point_of_view": "篠崎 遥",
                    "target_words": 250,
                }
            ],
            chapter_1_draft={
                "chapter_number": 1,
                "title": "第1章 導入",
                "summary": "主人公は手紙をなくし、夜更けに電話を受けて動き出す。",
                "text": "篠崎 遥は机の上の封筒を探し、夜の着信音に顔を上げた。" * 20,
            },
        )

        report = ContinuityChecker().build_report(artifacts)

        self.assertEqual(report["plot_to_plan_gaps"], [])
        self.assertFalse(any(issue["field"] == "summary" for issue in report["plan_to_draft_gaps"]))

    def test_name_detection_avoids_general_phrase_false_positive(self) -> None:
        artifacts = StoryArtifacts(
            story_input=StoryInput(theme="秘密", genre="ミステリ", tone="静謐", target_length=3000),
            loglines=[{"id": "logline-1", "title": "消えた手紙", "premise": "前提", "hook": "フック"}],
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
                "act_1": {"setup": "手紙を失う。", "inciting_incident": "電話が来る。"},
                "act_2": {"rising_action": "旧友を疑う。", "crisis": "親友が消える。"},
                "act_3": {"resolution": "手紙が見つかる。"},
            },
            chapter_plan=[
                {
                    "chapter_number": 1,
                    "title": "第1章 導入",
                    "purpose": "手紙を失う。",
                    "point_of_view": "篠崎 遥",
                    "target_words": 200,
                }
            ],
            chapter_1_draft={
                "chapter_number": 1,
                "title": "第1章 導入",
                "summary": "手紙を失う。",
                "text": "篠崎 遥は静かな部屋で手紙を探した。青い封筒と古い机だけが残っていた。" * 20,
            },
        )

        report = ContinuityChecker().build_report(artifacts)

        self.assertFalse(
            any(issue.get("reason") == "name_in_draft_not_in_characters" for issue in report["character_name_mismatches"])
        )

    def test_quality_checks_flag_pov_length_balance_and_character_continuity(self) -> None:
        artifacts = StoryArtifacts(
            story_input=StoryInput(theme="秘密", genre="ミステリ", tone="静謐", target_length=9000),
            loglines=[{"id": "logline-1", "title": "消えた手紙", "premise": "前提", "hook": "フック"}],
            characters=[
                {
                    "name": "篠崎 遥",
                    "role": "protagonist",
                    "goal": "真相解明",
                    "conflict": "過去と向き合えない",
                    "arc": "受動から能動へ",
                },
                {
                    "name": "木崎 蓮",
                    "role": "foil",
                    "goal": "状況収束",
                    "conflict": "感情を読めない",
                    "arc": "合理性を見直す",
                },
                {
                    "name": "水守 透子",
                    "role": "catalyst",
                    "goal": "秘密を明かす",
                    "conflict": "真実を恐れる",
                    "arc": "沈黙から告白へ",
                },
            ],
            three_act_plot={
                "act_1": {"setup": "手紙を失う。", "inciting_incident": "電話が来る。"},
                "act_2": {"rising_action": "旧友を疑う。", "crisis": "親友が消える。"},
                "act_3": {"resolution": "手紙が見つかる。"},
            },
            chapter_plan=[
                {
                    "chapter_number": 1,
                    "title": "第1章 導入",
                    "purpose": "篠崎 遥が手紙を失う。",
                    "point_of_view": "篠崎 遥",
                    "target_words": 300,
                },
                {
                    "chapter_number": 2,
                    "title": "第2章 対立",
                    "purpose": "木崎 蓮が疑念を深める。",
                    "point_of_view": "木崎 蓮",
                    "target_words": 2200,
                },
                {
                    "chapter_number": 3,
                    "title": "第3章 危機",
                    "purpose": "主人公が真相に近づく。",
                    "point_of_view": "篠崎 遥",
                    "target_words": 250,
                },
            ],
            chapter_1_draft={
                "chapter_number": 1,
                "title": "第1章 導入",
                "summary": "篠崎 遥が手紙を失う。",
                "text": "篠崎 遥は机を見つめ、失くした手紙の行方を探した。" * 20,
            },
        )

        report = ContinuityChecker().build_report(artifacts)

        self.assertTrue(report["pov_consistency_issues"])
        self.assertTrue(report["chapter_length_balance_warnings"])
        self.assertTrue(report["character_continuity_issues"])
        self.assertTrue(
            any(issue["reason"] == "multiple_point_of_view_values_across_chapter_plan" for issue in report["pov_consistency_issues"])
        )
        self.assertTrue(
            any(issue["reason"] == "chapter_target_words_are_unbalanced" for issue in report["chapter_length_balance_warnings"])
        )
        self.assertTrue(
            any(issue["character"] == "水守 透子" for issue in report["character_continuity_issues"])
        )


if __name__ == "__main__":
    unittest.main()
