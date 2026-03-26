from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any

from novel_writer.llm.base import BaseLLMClient
from novel_writer.schema import (
    StoryInput,
    validate_chapter_briefs,
    validate_scene_cards,
    validate_story_bible,
)


class OpenAIClient(BaseLLMClient):
    def __init__(
        self,
        model: str = "gpt-4.1-mini",
        api_key: str | None = None,
        base_url: str | None = None,
        provider_label: str = "OpenAI",
        response_format_type: str = "json_object",
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(f"{provider_label} provider requires the openai package to be installed.") from exc

        if not api_key:
            raise RuntimeError(f"{provider_label} provider requires an API key.")

        client_kwargs: dict[str, str] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        self._client = OpenAI(**client_kwargs)
        self._model = model
        self._provider_label = provider_label
        self._response_format_type = response_format_type

    def _generate_json(self, system_prompt: str, user_prompt: str) -> Any:
        system_message = system_prompt
        user_message = user_prompt
        if self._response_format_type == "text":
            json_only_instruction = (
                "Output only valid JSON. "
                "Do not wrap the response in markdown fences. "
                "Do not add explanations before or after the JSON."
            )
            system_message = f"{system_prompt} {json_only_instruction}"
            user_message = f"{json_only_instruction} {user_prompt}"

        response = self._client.chat.completions.create(
            model=self._model,
            response_format={"type": self._response_format_type},
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
        )
        content = response.choices[0].message.content or ""
        normalized_content = self._normalize_json_content(content)
        try:
            return json.loads(normalized_content)
        except JSONDecodeError as exc:
            preview = normalized_content[:160].replace("\n", "\\n")
            raise ValueError(
                f"{self._provider_label} response was not valid JSON. content_preview={preview}"
            ) from exc

    def _normalize_json_content(self, content: str) -> str:
        normalized = content.strip()
        if not normalized:
            raise ValueError(f"{self._provider_label} response content was empty.")

        if normalized.startswith("```"):
            lines = normalized.splitlines()
            if len(lines) >= 3 and lines[0].startswith("```") and lines[-1] == "```":
                normalized = "\n".join(lines[1:-1]).strip()
                if normalized.lower().startswith("json\n"):
                    normalized = normalized[5:].strip()

        return normalized

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
        story_bible: dict[str, Any],
    ) -> list[dict[str, Any]]:
        data = self._generate_json(
            "You generate a short chapter plan in Japanese.",
            (
                "Return JSON with key 'chapter_plan' as an array. "
                f"story={story_input.to_dict()}, logline={json.dumps(logline, ensure_ascii=False)}, "
                f"characters={json.dumps(characters, ensure_ascii=False)}, "
                f"plot={json.dumps(three_act_plot, ensure_ascii=False)}, "
                f"story_bible={json.dumps(story_bible, ensure_ascii=False)}"
            ),
        )
        root = self._require_dict(data, "chapter_plan root")
        return self._require_object_list(
            root.get("chapter_plan"),
            "chapter_plan",
            ("chapter_number", "title", "purpose", "point_of_view", "target_words"),
        )

    def generate_story_bible(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
        three_act_plot: dict[str, Any],
    ) -> dict[str, Any]:
        data = self._generate_json(
            "You generate a long-form story bible in Japanese.",
            (
                "Return JSON with key 'story_bible'. "
                f"story={story_input.to_dict()}, logline={json.dumps(logline, ensure_ascii=False)}, "
                f"characters={json.dumps(characters, ensure_ascii=False)}, "
                f"plot={json.dumps(three_act_plot, ensure_ascii=False)}"
            ),
        )
        root = self._require_dict(data, "story_bible root")
        story_bible = self._require_dict(root.get("story_bible"), "story_bible")
        return validate_story_bible(story_bible)

    def generate_chapter_briefs(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
        three_act_plot: dict[str, Any],
        story_bible: dict[str, Any],
        chapter_plan: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        data = self._generate_json(
            "You generate chapter briefs in Japanese.",
            (
                "Return JSON with key 'chapter_briefs' as an array. "
                f"story={story_input.to_dict()}, "
                f"logline={json.dumps(logline, ensure_ascii=False)}, "
                f"characters={json.dumps(characters, ensure_ascii=False)}, "
                f"three_act_plot={json.dumps(three_act_plot, ensure_ascii=False)}, "
                f"chapter_plan={json.dumps(chapter_plan, ensure_ascii=False)}, "
                f"story_bible={json.dumps(story_bible, ensure_ascii=False)}"
            ),
        )
        root = self._require_dict(data, "chapter_briefs root")
        chapter_briefs = self._require_list(root.get("chapter_briefs"), "chapter_briefs")
        if len(chapter_briefs) != len(chapter_plan):
            raise ValueError(f"OpenAI response for chapter_briefs must contain {len(chapter_plan)} items.")
        return validate_chapter_briefs(chapter_briefs)

    def generate_scene_cards(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
        three_act_plot: dict[str, Any],
        story_bible: dict[str, Any],
        chapter_plan: list[dict[str, Any]],
        chapter_briefs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        data = self._generate_json(
            "You generate scene cards in Japanese.",
            (
                "Return JSON with key 'scene_cards' as an array. "
                f"story={story_input.to_dict()}, "
                f"logline={json.dumps(logline, ensure_ascii=False)}, "
                f"characters={json.dumps(characters, ensure_ascii=False)}, "
                f"three_act_plot={json.dumps(three_act_plot, ensure_ascii=False)}, "
                f"chapter_plan={json.dumps(chapter_plan, ensure_ascii=False)}, "
                f"chapter_briefs={json.dumps(chapter_briefs, ensure_ascii=False)}, "
                f"story_bible={json.dumps(story_bible, ensure_ascii=False)}"
            ),
        )
        root = self._require_dict(data, "scene_cards root")
        packets = self._require_object_list(
            root.get("scene_cards"),
            "scene_cards",
            ("chapter_number", "scenes"),
            expected_length=len(chapter_plan),
        )
        for index, packet in enumerate(packets):
            scenes = packet.get("scenes")
            if not isinstance(scenes, list):
                raise ValueError(f"OpenAI response for scene_cards[{index}].scenes must be a list.")
        return validate_scene_cards(packets)

    def generate_chapter_draft(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
        three_act_plot: dict[str, Any],
        chapter_plan: list[dict[str, Any]],
        chapter_briefs: list[dict[str, Any]],
        scene_cards: list[dict[str, Any]],
        canon_ledger: dict[str, Any],
        thread_registry: dict[str, Any],
        chapter_index: int = 0,
        chapter_handoff_packet: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if chapter_index < 0 or chapter_index >= len(chapter_plan):
            raise ValueError(f"chapter_plan must contain an entry for chapter_index={chapter_index}.")
        if chapter_index >= len(chapter_briefs):
            raise ValueError(f"chapter_briefs must contain an entry for chapter_index={chapter_index}.")
        if chapter_index >= len(scene_cards):
            raise ValueError(f"scene_cards must contain an entry for chapter_index={chapter_index}.")

        data = self._generate_json(
            "You generate a chapter draft in Japanese.",
            (
                "Return JSON with key 'chapter_draft' or 'chapter_1_draft'. "
                f"story={story_input.to_dict()}, logline={json.dumps(logline, ensure_ascii=False)}, "
                f"characters={json.dumps(characters, ensure_ascii=False)}, "
                f"three_act_plot={json.dumps(three_act_plot, ensure_ascii=False)}, "
                f"chapter_plan={json.dumps(chapter_plan, ensure_ascii=False)}, "
                f"chapter_briefs={json.dumps(chapter_briefs, ensure_ascii=False)}, "
                f"scene_cards={json.dumps(scene_cards, ensure_ascii=False)}, "
                f"chapter_handoff_packet={json.dumps(chapter_handoff_packet or {}, ensure_ascii=False)}, "
                f"canon_ledger={json.dumps(canon_ledger, ensure_ascii=False)}, "
                f"thread_registry={json.dumps(thread_registry, ensure_ascii=False)}, "
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
        chapter_handoff_packet: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = self._generate_json(
            "You revise a Japanese chapter draft for consistency, concision, and tone.",
            (
                "Return JSON with key 'revised_chapter_draft'. "
                f"story={story_input.to_dict()}, "
                f"chapter_plan={json.dumps(chapter_plan, ensure_ascii=False)}, "
                f"chapter_draft={json.dumps(chapter_draft, ensure_ascii=False)}, "
                f"continuity_report={json.dumps(continuity_report, ensure_ascii=False)}, "
                f"chapter_handoff_packet={json.dumps(chapter_handoff_packet or {}, ensure_ascii=False)}, "
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

    def generate_story_summary(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        chapter_plan: list[dict[str, Any]],
        revised_chapter_drafts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        data = self._generate_json(
            "You generate a whole-story summary in Japanese.",
            (
                "Return JSON with key 'story_summary'. "
                f"story={story_input.to_dict()}, "
                f"logline={json.dumps(logline, ensure_ascii=False)}, "
                f"chapter_plan={json.dumps(chapter_plan, ensure_ascii=False)}, "
                f"revised_chapter_drafts={json.dumps(revised_chapter_drafts, ensure_ascii=False)}. "
                "Include a concise synopsis and chapter_summaries across the full story."
            ),
        )
        root = self._require_dict(data, "story_summary root")
        story_summary = self._require_required_keys(
            self._require_dict(root.get("story_summary"), "story_summary"),
            "story_summary",
            ("title", "synopsis", "chapter_count", "chapter_summaries"),
        )
        story_summary["chapter_summaries"] = self._require_object_list(
            story_summary.get("chapter_summaries"),
            "story_summary.chapter_summaries",
            ("chapter_number", "title", "summary"),
        )
        return story_summary
