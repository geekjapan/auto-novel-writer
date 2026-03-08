import unittest

from novel_writer.llm import OpenAIClient
from novel_writer.llm_client import MockLLMClient
from novel_writer.schema import StoryInput


class FakeOpenAIClient(OpenAIClient):
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def _generate_json(self, system_prompt: str, user_prompt: str):
        return self.payload


class MockLLMClientTest(unittest.TestCase):
    def test_mock_client_generates_expected_shapes(self) -> None:
        client = MockLLMClient()
        story_input = StoryInput(theme="喪失", genre="ミステリ", tone="静謐", target_length=6000)

        loglines = client.generate_loglines(story_input)
        characters = client.generate_characters(story_input, loglines[0])
        plot = client.generate_three_act_plot(story_input, loglines[0], characters)
        chapter_plan = client.generate_chapter_plan(story_input, loglines[0], characters, plot)
        draft = client.generate_chapter_draft(story_input, loglines[0], characters, chapter_plan)
        revised = client.revise_chapter_draft(
            story_input,
            chapter_plan,
            draft,
            {"issue_counts": {"length_warnings": 1}, "severity": "medium"},
            chapter_index=0,
        )

        self.assertEqual(len(loglines), 3)
        self.assertEqual(len(characters), 3)
        self.assertIn("act_1", plot)
        self.assertEqual(chapter_plan[0]["chapter_number"], 1)
        self.assertEqual(draft["chapter_number"], 1)
        self.assertEqual(revised["chapter_number"], 1)
        self.assertEqual(revised["chapter_index"], 0)
        self.assertIn("revision_notes", revised)

    def test_openai_client_validates_logline_schema(self) -> None:
        client = FakeOpenAIClient({"loglines": [{"id": "1", "title": "t"}]})
        story_input = StoryInput(theme="喪失", genre="ミステリ", tone="静謐", target_length=6000)

        with self.assertRaises(ValueError):
            client.generate_loglines(story_input)

    def test_openai_client_accepts_chapter_draft_compatibility_key(self) -> None:
        client = FakeOpenAIClient(
            {
                "chapter_1_draft": {
                    "chapter_number": 1,
                    "title": "第1章 導入",
                    "summary": "導入",
                    "text": "本文",
                }
            }
        )
        story_input = StoryInput(theme="喪失", genre="ミステリ", tone="静謐", target_length=6000)

        chapter_draft = client.generate_chapter_draft(
            story_input,
            {"id": "logline-1", "title": "鏡", "premise": "p", "hook": "h"},
            [{"name": "篠崎 遥"}],
            [{"chapter_number": 1, "title": "第1章 導入", "purpose": "導入", "point_of_view": "篠崎 遥", "target_words": 1000}],
            chapter_index=0,
        )

        self.assertEqual(chapter_draft["chapter_number"], 1)
        self.assertEqual(chapter_draft["title"], "第1章 導入")

    def test_openai_client_validates_revised_draft_notes_type(self) -> None:
        client = FakeOpenAIClient(
            {
                "revised_chapter_draft": {
                    "chapter_number": 1,
                    "title": "第1章 導入",
                    "summary": "導入",
                    "text": "本文",
                    "revision_notes": "not-a-list",
                }
            }
        )
        story_input = StoryInput(theme="喪失", genre="ミステリ", tone="静謐", target_length=6000)

        with self.assertRaises(ValueError):
            client.revise_chapter_draft(
                story_input,
                [{"chapter_number": 1, "title": "第1章 導入", "purpose": "導入", "point_of_view": "篠崎 遥", "target_words": 1000}],
                {"chapter_number": 1, "title": "第1章 導入", "summary": "導入", "text": "本文"},
                {"severity": "low"},
                chapter_index=0,
            )


if __name__ == "__main__":
    unittest.main()
