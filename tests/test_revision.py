import unittest

from novel_writer.llm_client import MockLLMClient
from novel_writer.schema import StoryInput


class RevisionTest(unittest.TestCase):
    def test_mock_revision_aligns_summary_and_reduces_duplicates(self) -> None:
        client = MockLLMClient()
        story_input = StoryInput(theme="喪失", genre="ミステリ", tone="静謐", target_length=6000)
        chapter_plan = [
            {
                "chapter_number": 1,
                "title": "第1章 導入",
                "purpose": "主人公が手紙を失い、夜の電話を受ける。",
                "point_of_view": "篠崎 遥",
                "target_words": 1000,
            }
        ]
        draft = {
            "chapter_number": 1,
            "title": "第1章 導入",
            "summary": "別の要約",
            "text": "篠崎 遥は立ち尽くした。篠崎 遥は立ち尽くした。夜の着信に顔を上げた。",
        }

        revised = client.revise_chapter_draft(
            story_input,
            chapter_plan,
            draft,
            {"severity": "medium", "issue_counts": {"plan_to_draft_gaps": 1}},
        )

        self.assertEqual(revised["summary"], chapter_plan[0]["purpose"])
        self.assertEqual(revised["text"].count("篠崎 遥は立ち尽くした。"), 1)
        self.assertIn("revision_notes", revised)
