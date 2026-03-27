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

    def test_build_report_can_target_arbitrary_chapter_by_index(self) -> None:
        artifacts = StoryArtifacts(
            story_input=StoryInput(theme="秘密", genre="ミステリ", tone="静謐", target_length=6000),
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
                    "target_words": 1200,
                },
                {
                    "chapter_number": 2,
                    "title": "第2章 対立",
                    "purpose": "疑いが深まり、旧友と対峙する。",
                    "point_of_view": "別人 視点",
                    "target_words": 1200,
                },
            ],
            chapter_drafts=[
                {
                    "chapter_number": 1,
                    "title": "第1章 導入",
                    "summary": "手紙を失う。",
                    "text": "篠崎 遥は机を探した。" * 20,
                },
                {
                    "chapter_number": 2,
                    "title": "第2章 ずれた題",
                    "summary": "別の要約",
                    "text": "木崎 蓮は廊下で立ち止まった。",
                },
            ],
        )

        report = ContinuityChecker().build_report(artifacts, chapter_index=1)

        self.assertEqual(report["chapter_index"], 1)
        self.assertEqual(report["chapter_number"], 2)
        self.assertTrue(report["character_name_mismatches"])
        self.assertTrue(any(issue["artifact"] == "chapter_plan[1]" for issue in report["character_name_mismatches"]))
        self.assertTrue(any(issue["artifact"] == "chapter_drafts[1]" for issue in report["character_name_mismatches"]))
        self.assertTrue(any(issue["field"] == "title" for issue in report["plan_to_draft_gaps"]))
        self.assertTrue(any(issue["field"] == "chapter_drafts[1].text" for issue in report["length_warnings"]))

    def test_build_quality_report_recommends_regenerate_vs_revise(self) -> None:
        continuity_report = {
            "severity": "high",
            "issue_counts": {
                "missing_fields": 1,
                "character_name_mismatches": 1,
                "plot_to_plan_gaps": 0,
                "plan_to_draft_gaps": 2,
                "length_warnings": 0,
                "pov_consistency_issues": 1,
                "chapter_length_balance_warnings": 0,
                "character_continuity_issues": 1,
            },
        }

        quality_report = ContinuityChecker().build_quality_report(continuity_report)

        self.assertEqual(quality_report["overall_recommendation"], "regenerate")
        self.assertEqual(quality_report["severity"], "high")
        self.assertEqual(quality_report["source_report"], "continuity_report")
        self.assertEqual(quality_report["total_issue_count"], 6)
        self.assertTrue(
            any(
                item["category"] == "missing_fields" and item["recommended_action"] == "regenerate"
                for item in quality_report["recommendations"]
            )
        )
        self.assertTrue(
            any(
                item["category"] == "plan_to_draft_gaps" and item["recommended_action"] == "revise"
                for item in quality_report["recommendations"]
            )
        )

    def test_build_quality_report_recommends_revise_when_no_regenerate_issue_exists(self) -> None:
        continuity_report = {
            "severity": "medium",
            "issue_counts": {
                "missing_fields": 0,
                "character_name_mismatches": 1,
                "plot_to_plan_gaps": 0,
                "plan_to_draft_gaps": 1,
                "length_warnings": 1,
                "pov_consistency_issues": 0,
                "chapter_length_balance_warnings": 0,
                "character_continuity_issues": 0,
            },
        }

        quality_report = ContinuityChecker().build_quality_report(continuity_report)

        self.assertEqual(quality_report["overall_recommendation"], "revise")

    def test_build_project_quality_report_summarizes_story_level_checks(self) -> None:
        artifacts = StoryArtifacts(
            story_input=StoryInput(theme="秘密", genre="ミステリ", tone="静謐", target_length=6000),
            chapter_plan=[
                {
                    "chapter_number": 1,
                    "title": "第1章 導入",
                    "purpose": "秘密を抱えた主人公が異変に気づく。",
                    "point_of_view": "篠崎 遥",
                    "target_words": 1000,
                },
                {
                    "chapter_number": 2,
                    "title": "第2章 対立",
                    "purpose": "秘密を追ううちに対立が深まる。",
                    "point_of_view": "木崎 蓮",
                    "target_words": 2200,
                },
                {
                    "chapter_number": 3,
                    "title": "第3章 結末",
                    "purpose": "秘密の核心が明かされる。",
                    "point_of_view": "篠崎 遥",
                    "target_words": 800,
                },
            ],
            story_summary={
                "title": "消えた手紙",
                "synopsis": "秘密を抱えた主人公が異変を追い、最後に秘密の核心へ辿り着く。",
                "chapter_summaries": [
                    {"chapter_number": 1, "title": "第1章 導入", "summary": "秘密を抱えた主人公が異変に気づく。"},
                    {"chapter_number": 2, "title": "第2章 対立", "summary": "秘密を追ううちに対立が深まる。"},
                    {"chapter_number": 3, "title": "第3章 結末", "summary": "秘密の核心が明かされる。"},
                ],
            },
        )

        project_quality_report = ContinuityChecker().build_project_quality_report(artifacts)

        self.assertEqual(project_quality_report["overall_recommendation"], "revise")
        self.assertEqual(project_quality_report["source_report"], "project_quality_report")
        self.assertIn("theme_coherence", project_quality_report["checks"])
        self.assertEqual(project_quality_report["checks"]["theme_coherence"]["status"], "pass")
        self.assertEqual(project_quality_report["checks"]["pov_consistency"]["status"], "warn")
        self.assertEqual(project_quality_report["checks"]["chapter_balance"]["status"], "warn")

    def test_build_progress_report_summarizes_long_form_checks(self) -> None:
        artifacts = StoryArtifacts(
            story_input=StoryInput(theme="秘密", genre="ミステリ", tone="静謐", target_length=120000),
            chapter_plan=[
                {
                    "chapter_number": 1,
                    "title": "第1章 導入",
                    "purpose": "秘密を抱えた主人公が異変に気づく。",
                    "point_of_view": "篠崎 遥",
                    "target_words": 1000,
                },
                {
                    "chapter_number": 2,
                    "title": "第2章 対立",
                    "purpose": "主人公の疑いが深まり、対立が悪化する。",
                    "point_of_view": "篠崎 遥",
                    "target_words": 1100,
                },
                {
                    "chapter_number": 3,
                    "title": "第3章 転換",
                    "purpose": "伏線が反転し、終盤への道筋が見える。",
                    "point_of_view": "篠崎 遥",
                    "target_words": 1200,
                },
            ],
            chapter_briefs=[
                {
                    "chapter_number": 1,
                    "purpose": "導入",
                    "goal": "異変に気づく",
                    "conflict": "状況が見えない",
                    "turn": "不吉な違和感が残る",
                    "must_include": ["seed-1"],
                    "continuity_dependencies": ["篠崎 遥"],
                    "foreshadowing_targets": ["seed-1"],
                    "arc_progress": "不安が芽生える",
                    "target_length_guidance": "standard",
                },
                {
                    "chapter_number": 2,
                    "purpose": "対立",
                    "goal": "疑いを深める",
                    "conflict": "味方を信じ切れない",
                    "turn": "後戻りできない",
                    "must_include": ["seed-1"],
                    "continuity_dependencies": ["篠崎 遥"],
                    "foreshadowing_targets": ["seed-1"],
                    "arc_progress": "疑念が強まる",
                    "target_length_guidance": "standard",
                },
                {
                    "chapter_number": 3,
                    "purpose": "転換",
                    "goal": "終盤準備を整える",
                    "conflict": "真相に届かない",
                    "turn": "核心へ近づく",
                    "must_include": ["seed-1"],
                    "continuity_dependencies": ["篠崎 遥"],
                    "foreshadowing_targets": ["seed-1"],
                    "arc_progress": "決意が固まる",
                    "target_length_guidance": "standard",
                },
            ],
            revised_chapter_drafts=[
                {"chapter_number": 1, "title": "第1章 導入", "summary": "異変が始まり、seed-1 が提示される。", "text": "本文1"},
                {"chapter_number": 2, "title": "第2章 対立", "summary": "対立が悪化し、seed-1 が進展する。", "text": "本文2"},
                {"chapter_number": 3, "title": "第3章 転換", "summary": "核心へ近づき、climax 準備が見える。", "text": "本文3"},
            ],
        )
        thread_registry = {
            "schema_name": "thread_registry",
            "schema_version": "1.0",
            "threads": [
                {
                    "thread_id": "seed-1",
                    "label": "seed-1",
                    "status": "progressed",
                    "introduced_in_chapter": 1,
                    "last_updated_in_chapter": 3,
                    "related_characters": ["篠崎 遥"],
                    "notes": ["第3章まで進展した"],
                }
            ],
        }

        progress_report = ContinuityChecker().build_progress_report(artifacts, thread_registry)

        self.assertEqual(progress_report["schema_name"], "progress_report")
        self.assertEqual(progress_report["schema_version"], "1.0")
        self.assertEqual(progress_report["evaluated_through_chapter"], 3)
        self.assertIn("chapter_role_coverage", progress_report["checks"])
        self.assertIn("climax_readiness", progress_report["checks"])
        self.assertIn(progress_report["recommended_action"], {"continue", "revise", "rerun", "replan", "stop_for_review"})


if __name__ == "__main__":
    unittest.main()
