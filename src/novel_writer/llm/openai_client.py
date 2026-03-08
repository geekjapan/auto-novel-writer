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

    def _require_dict(self, payload: Any, label: str) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError(f"OpenAI response for {label} must be an object.")
        return payload

    def _require_list(self, payload: Any, label: str) -> list[Any]:
        if not isinstance(payload, list):
            raise ValueError(f"OpenAI response for {label} must be a list.")
        return payload

    def _require_object_list(
        self,
        payload: Any,
        label: str,
        required_keys: tuple[str, ...],
        expected_length: int | None = None,
    ) -> list[dict[str, Any]]:
        items = self._require_list(payload, label)
        if expected_length is not None and len(items) != expected_length:
            raise ValueError(f"OpenAI response for {label} must contain {expected_length} items.")
        for index, item in enumerate(items):
            self._require_required_keys(
                self._require_dict(item, f"{label}[{index}]"),
                f"{label}[{index}]",
                required_keys,
            )
        return items

    def _require_required_keys(
        self,
        payload: dict[str, Any],
        label: str,
        required_keys: tuple[str, ...],
    ) -> dict[str, Any]:
        missing_keys = [key for key in required_keys if key not in payload]
        if missing_keys:
            raise ValueError(f"OpenAI response for {label} is missing keys: {', '.join(missing_keys)}")
        return payload

    def generate_loglines(self, story_input: StoryInput) -> list[dict[str, Any]]:
        data = self._generate_json(
            "You generate concise short-story planning assets in Japanese.",
            "Return JSON with key 'loglines' as an array of 3 items. " + self._story_context(story_input),
        )
        root = self._require_dict(data, "loglines root")
        return self._require_object_list(
            root.get("loglines"),
            "loglines",
            ("id", "title", "premise", "hook"),
            expected_length=3,
        )

    def generate_characters(self, story_input: StoryInput, logline: dict[str, Any]) -> list[dict[str, Any]]:
        data = self._generate_json(
            "You generate concise character sheets in Japanese.",
            (
                "Return JSON with key 'characters' as an array of 3 items. "
                f"story={story_input.to_dict()}, logline={json.dumps(logline, ensure_ascii=False)}"
            ),
        )
        root = self._require_dict(data, "characters root")
        return self._require_object_list(
            root.get("characters"),
            "characters",
            ("name", "role", "goal", "conflict", "arc"),
            expected_length=3,
        )

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
        root = self._require_dict(data, "three_act_plot root")
        plot = self._require_required_keys(
            self._require_dict(root.get("three_act_plot"), "three_act_plot"),
            "three_act_plot",
            ("act_1", "act_2", "act_3"),
        )
        for act_name in ("act_1", "act_2", "act_3"):
            self._require_dict(plot.get(act_name), f"three_act_plot.{act_name}")
        return plot

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
        root = self._require_dict(data, "chapter_plan root")
        return self._require_object_list(
            root.get("chapter_plan"),
            "chapter_plan",
            ("chapter_number", "title", "purpose", "point_of_view", "target_words"),
        )

    def generate_chapter_draft(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
        chapter_plan: list[dict[str, Any]],
        chapter_index: int = 0,
    ) -> dict[str, Any]:
        data = self._generate_json(
            "You generate a chapter draft in Japanese.",
            (
                "Return JSON with key 'chapter_draft' or 'chapter_1_draft'. "
                f"story={story_input.to_dict()}, logline={json.dumps(logline, ensure_ascii=False)}, "
                f"characters={json.dumps(characters, ensure_ascii=False)}, "
                f"chapter_plan={json.dumps(chapter_plan, ensure_ascii=False)}, "
                f"chapter_index={chapter_index}"
            ),
        )
        root = self._require_dict(data, "chapter_draft root")
        draft = root.get("chapter_draft") or root.get("chapter_1_draft")
        return self._require_required_keys(
            self._require_dict(draft, "chapter_draft"),
            "chapter_draft",
            ("chapter_number", "title", "summary", "text"),
        )

    def revise_chapter_draft(
        self,
        story_input: StoryInput,
        chapter_plan: list[dict[str, Any]],
        chapter_draft: dict[str, Any],
        continuity_report: dict[str, Any],
        chapter_index: int = 0,
    ) -> dict[str, Any]:
        data = self._generate_json(
            "You revise a Japanese chapter draft for consistency, concision, and tone.",
            (
                "Return JSON with key 'revised_chapter_draft'. "
                f"story={story_input.to_dict()}, "
                f"chapter_plan={json.dumps(chapter_plan, ensure_ascii=False)}, "
                f"chapter_draft={json.dumps(chapter_draft, ensure_ascii=False)}, "
                f"continuity_report={json.dumps(continuity_report, ensure_ascii=False)}, "
                f"chapter_index={chapter_index}. "
                "Keep the same chapter number and title, improve style, remove redundancy, and align summary to the selected chapter plan."
            ),
        )
        root = self._require_dict(data, "revised_chapter_draft root")
        revised = self._require_required_keys(
            self._require_dict(root.get("revised_chapter_draft"), "revised_chapter_draft"),
            "revised_chapter_draft",
            ("chapter_number", "title", "summary", "text"),
        )
        if "revision_notes" in revised and not isinstance(revised["revision_notes"], list):
            raise ValueError("OpenAI response for revised_chapter_draft.revision_notes must be a list when present.")
        return revised
