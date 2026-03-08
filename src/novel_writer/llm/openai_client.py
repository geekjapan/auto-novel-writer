from __future__ import annotations

import json
import os
from typing import Any

from novel_writer.llm.base import BaseLLMClient
from novel_writer.schema import StoryInput


class OpenAIClient(BaseLLMClient):
    def __init__(self, model: str = "gpt-4.1-mini") -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("OpenAI provider requires the openai package to be installed.") from exc

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def _generate_json(self, system_prompt: str, user_prompt: str) -> Any:
        response = self._client.chat.completions.create(
            model=self._model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    def _story_context(self, story_input: StoryInput) -> str:
        return (
            f"theme={story_input.theme}, genre={story_input.genre}, "
            f"tone={story_input.tone}, target_length={story_input.target_length}"
        )

    def generate_loglines(self, story_input: StoryInput) -> list[dict[str, Any]]:
        data = self._generate_json(
            "You generate concise short-story planning assets in Japanese.",
            "Return JSON with key 'loglines' as an array of 3 items. " + self._story_context(story_input),
        )
        return data["loglines"]

    def generate_characters(self, story_input: StoryInput, logline: dict[str, Any]) -> list[dict[str, Any]]:
        data = self._generate_json(
            "You generate concise character sheets in Japanese.",
            (
                "Return JSON with key 'characters' as an array of 3 items. "
                f"story={story_input.to_dict()}, logline={json.dumps(logline, ensure_ascii=False)}"
            ),
        )
        return data["characters"]

    def generate_three_act_plot(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
    ) -> dict[str, Any]:
        data = self._generate_json(
            "You generate a three-act plot in Japanese.",
            (
                "Return JSON with key 'three_act_plot'. "
                f"story={story_input.to_dict()}, logline={json.dumps(logline, ensure_ascii=False)}, "
                f"characters={json.dumps(characters, ensure_ascii=False)}"
            ),
        )
        return data["three_act_plot"]

    def generate_chapter_plan(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
        three_act_plot: dict[str, Any],
    ) -> list[dict[str, Any]]:
        data = self._generate_json(
            "You generate a short chapter plan in Japanese.",
            (
                "Return JSON with key 'chapter_plan' as an array. "
                f"story={story_input.to_dict()}, logline={json.dumps(logline, ensure_ascii=False)}, "
                f"characters={json.dumps(characters, ensure_ascii=False)}, "
                f"plot={json.dumps(three_act_plot, ensure_ascii=False)}"
            ),
        )
        return data["chapter_plan"]

    def generate_chapter_draft(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
        chapter_plan: list[dict[str, Any]],
        chapter_index: int = 0,
    ) -> dict[str, Any]:
        data = self._generate_json(
            "You generate a first chapter draft in Japanese.",
            (
                "Return JSON with key 'chapter_1_draft'. "
                f"story={story_input.to_dict()}, logline={json.dumps(logline, ensure_ascii=False)}, "
                f"characters={json.dumps(characters, ensure_ascii=False)}, "
                f"chapter_plan={json.dumps(chapter_plan, ensure_ascii=False)}, "
                f"chapter_index={chapter_index}"
            ),
        )
        return data["chapter_1_draft"]

