import unittest

from novel_writer.llm_client import MockLLMClient
from novel_writer.schema import StoryInput


class MockLLMClientTest(unittest.TestCase):
    def test_mock_client_generates_expected_shapes(self) -> None:
        client = MockLLMClient()
        story_input = StoryInput(theme="喪失", genre="ミステリ", tone="静謐", target_length=6000)

        loglines = client.generate_loglines(story_input)
        characters = client.generate_characters(story_input, loglines[0])
        plot = client.generate_three_act_plot(story_input, loglines[0], characters)
        chapter_plan = client.generate_chapter_plan(story_input, loglines[0], characters, plot)
        draft = client.generate_chapter_draft(story_input, loglines[0], characters, chapter_plan)

        self.assertEqual(len(loglines), 3)
        self.assertEqual(len(characters), 3)
        self.assertIn("act_1", plot)
        self.assertEqual(chapter_plan[0]["chapter_number"], 1)
        self.assertEqual(draft["chapter_number"], 1)


if __name__ == "__main__":
    unittest.main()

