import unittest
from unittest.mock import patch

from novel_writer.llm import OpenAIClient
from novel_writer.llm.factory import build_llm_client, resolve_openai_provider_settings
from novel_writer.cli import build_parser
from novel_writer.llm_client import MockLLMClient
from novel_writer.schema import StoryInput


class FakeOpenAIClient(OpenAIClient):
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def _generate_json(self, system_prompt: str, user_prompt: str):
        return self.payload


class RecordingCompletions:
    def __init__(self, content: str) -> None:
        self.content = content
        self.last_kwargs: dict | None = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return type(
            "Response",
            (),
            {
                "choices": [
                    type(
                        "Choice",
                        (),
                        {"message": type("Message", (), {"content": self.content})()},
                    )()
                ]
            },
        )()


class RecordingChat:
    def __init__(self, completions: RecordingCompletions) -> None:
        self.completions = completions


class RecordingOpenAIBackend:
    def __init__(self, completions: RecordingCompletions) -> None:
        self.chat = RecordingChat(completions)


class MockLLMClientTest(unittest.TestCase):
    def test_cli_parser_accepts_lmstudio_provider_and_model(self) -> None:
        parser = build_parser()

        args = parser.parse_args(
            [
                "--theme",
                "境界",
                "--genre",
                "SF",
                "--tone",
                "ビター",
                "--target-length",
                "5000",
                "--provider",
                "lmstudio",
                "--model",
                "local-model",
            ]
        )

        self.assertEqual(args.provider, "lmstudio")
        self.assertEqual(args.model, "local-model")

    def test_resolve_lmstudio_provider_settings_uses_documented_defaults(self) -> None:
        settings = resolve_openai_provider_settings("lmstudio", model="local-model")

        self.assertEqual(settings["provider_label"], "LM Studio")
        self.assertEqual(settings["model"], "local-model")
        self.assertEqual(settings["base_url"], "http://127.0.0.1:1234/v1")
        self.assertEqual(settings["api_key"], "lm-studio")

    def test_resolve_ollama_provider_settings_uses_documented_defaults(self) -> None:
        settings = resolve_openai_provider_settings("ollama", model="llama3.1")

        self.assertEqual(settings["provider_label"], "Ollama")
        self.assertEqual(settings["model"], "llama3.1")
        self.assertEqual(settings["base_url"], "http://127.0.0.1:11434/v1")
        self.assertEqual(settings["api_key"], "ollama")

    def test_resolve_openai_compatible_settings_require_base_url(self) -> None:
        with self.assertRaises(RuntimeError):
            resolve_openai_provider_settings("openai-compatible", model="local-model")

    def test_build_llm_client_passes_openai_compatible_settings_to_client(self) -> None:
        with patch("novel_writer.llm.factory.OpenAIClient") as openai_client_class:
            build_llm_client(
                provider="openai-compatible",
                model="mistral-nemo",
                base_url="http://127.0.0.1:9000/v1",
                api_key="compat-key",
            )

        openai_client_class.assert_called_once_with(
            model="mistral-nemo",
            base_url="http://127.0.0.1:9000/v1",
            api_key="compat-key",
            provider_label="OpenAI-compatible",
            response_format_type="text",
        )

    def test_build_llm_client_passes_openai_response_format_defaults(self) -> None:
        with patch("novel_writer.llm.factory.OpenAIClient") as openai_client_class:
            build_llm_client(
                provider="openai",
                model="gpt-4.1-mini",
                api_key="openai-key",
            )

        openai_client_class.assert_called_once_with(
            model="gpt-4.1-mini",
            api_key="openai-key",
            provider_label="OpenAI",
            response_format_type="json_object",
        )

    def test_openai_client_uses_text_response_format_for_lmstudio(self) -> None:
        completions = RecordingCompletions('{"loglines": []}')
        client = object.__new__(OpenAIClient)
        client._client = RecordingOpenAIBackend(completions)
        client._model = "local-model"
        client._provider_label = "LM Studio"
        client._response_format_type = "text"

        payload = client._generate_json("system", "user")

        self.assertEqual(payload, {"loglines": []})
        self.assertEqual(completions.last_kwargs["response_format"], {"type": "text"})
        self.assertIn("Output only valid JSON.", completions.last_kwargs["messages"][0]["content"])
        self.assertIn("Do not wrap the response in markdown fences.", completions.last_kwargs["messages"][1]["content"])

    def test_openai_client_accepts_markdown_fenced_json_from_lmstudio(self) -> None:
        completions = RecordingCompletions('```json\n{"loglines": []}\n```')
        client = object.__new__(OpenAIClient)
        client._client = RecordingOpenAIBackend(completions)
        client._model = "local-model"
        client._provider_label = "LM Studio"
        client._response_format_type = "text"

        payload = client._generate_json("system", "user")

        self.assertEqual(payload, {"loglines": []})

    def test_openai_client_raises_clear_error_for_non_json_text(self) -> None:
        completions = RecordingCompletions("JSONではなく普通の文章です。")
        client = object.__new__(OpenAIClient)
        client._client = RecordingOpenAIBackend(completions)
        client._model = "local-model"
        client._provider_label = "LM Studio"
        client._response_format_type = "text"

        with self.assertRaisesRegex(ValueError, "LM Studio response was not valid JSON"):
            client._generate_json("system", "user")

    def test_openai_client_accepts_markdown_fenced_json_from_lmstudio(self) -> None:
        completions = RecordingCompletions('```json\n{"loglines": []}\n```')
        client = object.__new__(OpenAIClient)
        client._client = RecordingOpenAIBackend(completions)
        client._model = "local-model"
        client._provider_label = "LM Studio"
        client._response_format_type = "text"

        payload = client._generate_json("system", "user")

        self.assertEqual(payload, {"loglines": []})

    def test_openai_client_raises_clear_error_for_non_json_text(self) -> None:
        completions = RecordingCompletions("JSONではなく普通の文章です。")
        client = object.__new__(OpenAIClient)
        client._client = RecordingOpenAIBackend(completions)
        client._model = "local-model"
        client._provider_label = "LM Studio"
        client._response_format_type = "text"

        with self.assertRaisesRegex(ValueError, "LM Studio response was not valid JSON"):
            client._generate_json("system", "user")

    def test_mock_client_generates_expected_shapes(self) -> None:
        client = MockLLMClient()
        story_input = StoryInput(theme="喪失", genre="ミステリ", tone="静謐", target_length=6000)

        loglines = client.generate_loglines(story_input)
        characters = client.generate_characters(story_input, loglines[0])
        plot = client.generate_three_act_plot(story_input, loglines[0], characters)
        story_bible = client.generate_story_bible(story_input, loglines[0], characters, plot)
        chapter_plan = client.generate_chapter_plan(story_input, loglines[0], characters, plot, story_bible)
        chapter_briefs = client.generate_chapter_briefs(
            story_input, loglines[0], characters, plot, story_bible, chapter_plan
        )
        scene_cards = client.generate_scene_cards(
            story_input, loglines[0], characters, plot, story_bible, chapter_plan, chapter_briefs
        )
        draft = client.generate_chapter_draft(
            story_input,
            loglines[0],
            characters,
            chapter_plan,
            chapter_briefs,
            scene_cards,
        )
        revised = client.revise_chapter_draft(
            story_input,
            chapter_plan,
            draft,
            {"issue_counts": {"length_warnings": 1}, "severity": "medium"},
            chapter_index=0,
        )
        story_summary = client.generate_story_summary(story_input, loglines[0], chapter_plan, [revised])

        self.assertEqual(len(loglines), 3)
        self.assertEqual(len(characters), 3)
        self.assertIn("act_1", plot)
        self.assertEqual(story_bible["schema_name"], "story_bible")
        self.assertIn("ending_reveal", story_bible)
        self.assertEqual(chapter_plan[0]["chapter_number"], 1)
        self.assertIn(story_bible["theme_statement"], chapter_plan[0]["purpose"])
        self.assertEqual(draft["chapter_number"], 1)
        self.assertEqual(revised["chapter_number"], 1)
        self.assertEqual(revised["chapter_index"], 0)
        self.assertIn("revision_notes", revised)
        self.assertEqual(story_summary["chapter_count"], len(chapter_plan))
        self.assertIn("synopsis", story_summary)

    def test_mock_client_generates_chapter_briefs_and_scene_cards(self) -> None:
        client = MockLLMClient()
        story_input = StoryInput(theme="喪失", genre="ミステリ", tone="静謐", target_length=120000)
        loglines = client.generate_loglines(story_input)
        characters = client.generate_characters(story_input, loglines[0])
        plot = client.generate_three_act_plot(story_input, loglines[0], characters)
        story_bible = client.generate_story_bible(story_input, loglines[0], characters, plot)
        chapter_plan = client.generate_chapter_plan(story_input, loglines[0], characters, plot, story_bible)

        chapter_briefs = client.generate_chapter_briefs(
            story_input, loglines[0], characters, plot, story_bible, chapter_plan
        )
        scene_cards = client.generate_scene_cards(
            story_input, loglines[0], characters, plot, story_bible, chapter_plan, chapter_briefs
        )

        self.assertEqual(len(chapter_briefs), len(chapter_plan))
        self.assertEqual(len(scene_cards), len(chapter_plan))
        self.assertEqual(scene_cards[0]["chapter_number"], chapter_briefs[0]["chapter_number"])
        self.assertGreaterEqual(len(scene_cards[0]["scenes"]), 3)

    def test_mock_client_generate_chapter_draft_raises_when_chapter_briefs_are_empty(self) -> None:
        client = MockLLMClient()
        story_input = StoryInput(theme="喪失", genre="ミステリ", tone="静謐", target_length=120000)
        loglines = client.generate_loglines(story_input)
        characters = client.generate_characters(story_input, loglines[0])
        plot = client.generate_three_act_plot(story_input, loglines[0], characters)
        story_bible = client.generate_story_bible(story_input, loglines[0], characters, plot)
        chapter_plan = client.generate_chapter_plan(story_input, loglines[0], characters, plot, story_bible)
        scene_cards = client.generate_scene_cards(
            story_input,
            loglines[0],
            characters,
            plot,
            story_bible,
            chapter_plan,
            client.generate_chapter_briefs(story_input, loglines[0], characters, plot, story_bible, chapter_plan),
        )

        with self.assertRaisesRegex(ValueError, "chapter_briefs must contain an entry for chapter_index=0"):
            client.generate_chapter_draft(
                story_input,
                loglines[0],
                characters,
                chapter_plan,
                [],
                scene_cards,
                chapter_index=0,
            )

    def test_mock_client_generate_chapter_draft_raises_when_scene_cards_are_missing_or_index_is_invalid(self) -> None:
        client = MockLLMClient()
        story_input = StoryInput(theme="喪失", genre="ミステリ", tone="静謐", target_length=120000)
        loglines = client.generate_loglines(story_input)
        characters = client.generate_characters(story_input, loglines[0])
        plot = client.generate_three_act_plot(story_input, loglines[0], characters)
        story_bible = client.generate_story_bible(story_input, loglines[0], characters, plot)
        chapter_plan = client.generate_chapter_plan(story_input, loglines[0], characters, plot, story_bible)
        chapter_briefs = client.generate_chapter_briefs(
            story_input, loglines[0], characters, plot, story_bible, chapter_plan
        )
        scene_cards = client.generate_scene_cards(
            story_input, loglines[0], characters, plot, story_bible, chapter_plan, chapter_briefs
        )

        with self.assertRaisesRegex(ValueError, "scene_cards must contain an entry for chapter_index=0"):
            client.generate_chapter_draft(
                story_input,
                loglines[0],
                characters,
                chapter_plan,
                chapter_briefs,
                [],
                chapter_index=0,
            )

        with self.assertRaisesRegex(ValueError, "scene_cards must contain an entry for chapter_index=1"):
            client.generate_chapter_draft(
                story_input,
                loglines[0],
                characters,
                chapter_plan,
                chapter_briefs,
                scene_cards[:1],
                chapter_index=1,
            )

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
            [{
                "chapter_number": 1,
                "purpose": "導入",
                "goal": "g",
                "conflict": "c",
                "turn": "t",
                "must_include": [],
                "continuity_dependencies": [],
                "foreshadowing_targets": [],
                "arc_progress": "a",
                "target_length_guidance": "標準",
            }],
            [{
                "chapter_number": 1,
                "scenes": [
                    {
                        "chapter_number": 1,
                        "scene_number": 1,
                        "scene_goal": "g1",
                        "scene_conflict": "c1",
                        "scene_turn": "t1",
                        "pov_character": "篠崎 遥",
                        "participants": ["篠崎 遥"],
                        "setting": "s1",
                        "must_include": [],
                        "continuity_refs": [],
                        "foreshadowing_action": "seed",
                        "exit_state": "e1",
                    },
                    {
                        "chapter_number": 1,
                        "scene_number": 2,
                        "scene_goal": "g2",
                        "scene_conflict": "c2",
                        "scene_turn": "t2",
                        "pov_character": "篠崎 遥",
                        "participants": ["篠崎 遥"],
                        "setting": "s2",
                        "must_include": [],
                        "continuity_refs": [],
                        "foreshadowing_action": "progress",
                        "exit_state": "e2",
                    },
                    {
                        "chapter_number": 1,
                        "scene_number": 3,
                        "scene_goal": "g3",
                        "scene_conflict": "c3",
                        "scene_turn": "t3",
                        "pov_character": "篠崎 遥",
                        "participants": ["篠崎 遥"],
                        "setting": "s3",
                        "must_include": [],
                        "continuity_refs": [],
                        "foreshadowing_action": "payoff_or_seed",
                        "exit_state": "e3",
                    },
                ],
            }],
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

    def test_openai_client_validates_story_summary_schema(self) -> None:
        client = FakeOpenAIClient({"story_summary": {"title": "鏡", "chapter_count": 3}})
        story_input = StoryInput(theme="喪失", genre="ミステリ", tone="静謐", target_length=6000)

        with self.assertRaises(ValueError):
            client.generate_story_summary(
                story_input,
                {"id": "logline-1", "title": "鏡", "premise": "p", "hook": "h"},
                [{"chapter_number": 1, "title": "第1章 導入", "purpose": "導入", "point_of_view": "篠崎 遥", "target_words": 1000}],
                [{"chapter_number": 1, "title": "第1章 導入", "summary": "導入", "text": "本文"}],
            )

    def test_openai_client_validates_story_bible_schema(self) -> None:
        client = FakeOpenAIClient(
            {
                "story_bible": {
                    "schema_name": "story_bible",
                    "schema_version": "1.0",
                    "core_premise": "premise",
                    "theme_statement": "theme",
                    "character_arcs": [],
                    "world_rules": [],
                    "forbidden_facts": [],
                    "foreshadowing_seeds": [],
                }
            }
        )
        story_input = StoryInput(theme="喪失", genre="ミステリ", tone="静謐", target_length=6000)

        with self.assertRaises(ValueError):
            client.generate_story_bible(
                story_input,
                {"id": "logline-1", "title": "鏡", "premise": "p", "hook": "h"},
                [{"name": "篠崎 遥", "role": "protagonist", "goal": "g", "conflict": "c", "arc": "a"}],
                {"act_1": {}, "act_2": {}, "act_3": {}},
            )

    def test_openai_client_validates_scene_cards_shape(self) -> None:
        client = FakeOpenAIClient({"scene_cards": [{"chapter_number": 1, "scenes": "not-a-list"}]})
        story_input = StoryInput(theme="喪失", genre="ミステリ", tone="静謐", target_length=120000)

        with self.assertRaisesRegex(ValueError, "scene_cards\\[0\\].scenes must be a list"):
            client.generate_scene_cards(
                story_input,
                {"id": "logline-1", "title": "鏡", "premise": "p", "hook": "h"},
                [{"name": "篠崎 遥"}],
                {"act_1": {}, "act_2": {}, "act_3": {}},
                {
                    "schema_name": "story_bible",
                    "schema_version": "1.0",
                    "core_premise": "p",
                    "ending_reveal": "r",
                    "theme_statement": "t",
                    "character_arcs": [],
                    "world_rules": [],
                    "forbidden_facts": [],
                    "foreshadowing_seeds": [],
                },
                [{"chapter_number": 1, "title": "第1章", "purpose": "導入", "point_of_view": "篠崎 遥", "target_words": 5000}],
                [{
                    "chapter_number": 1,
                    "purpose": "導入",
                    "goal": "g",
                    "conflict": "c",
                    "turn": "t",
                    "must_include": [],
                    "continuity_dependencies": [],
                    "foreshadowing_targets": [],
                    "arc_progress": "a",
                    "target_length_guidance": "標準",
                }],
            )

    def test_openai_client_validates_chapter_briefs_schema(self) -> None:
        client = FakeOpenAIClient(
            {
                "chapter_briefs": [
                    {
                        "chapter_number": 1,
                        "purpose": "導入",
                        "goal": "g",
                        "conflict": "c",
                        "turn": "t",
                        "must_include": [],
                        "continuity_dependencies": [],
                        "foreshadowing_targets": [],
                        "target_length_guidance": "標準",
                    }
                ]
            }
        )
        story_input = StoryInput(theme="喪失", genre="ミステリ", tone="静謐", target_length=120000)

        with self.assertRaisesRegex(ValueError, "chapter_briefs\\[0\\] is missing required fields: arc_progress"):
            client.generate_chapter_briefs(
                story_input,
                {"id": "logline-1", "title": "鏡", "premise": "p", "hook": "h"},
                [{"name": "篠崎 遥", "role": "protagonist", "goal": "g", "conflict": "c", "arc": "a"}],
                {"act_1": {}, "act_2": {}, "act_3": {}},
                {
                    "schema_name": "story_bible",
                    "schema_version": "1.0",
                    "core_premise": "p",
                    "ending_reveal": "r",
                    "theme_statement": "t",
                    "character_arcs": [],
                    "world_rules": [],
                    "forbidden_facts": [],
                    "foreshadowing_seeds": [],
                },
                [{"chapter_number": 1, "title": "第1章", "purpose": "導入", "point_of_view": "篠崎 遥", "target_words": 5000}],
            )


if __name__ == "__main__":
    unittest.main()
