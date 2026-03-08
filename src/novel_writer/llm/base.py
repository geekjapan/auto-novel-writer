from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from novel_writer.schema import StoryInput


class BaseLLMClient(ABC):
    @abstractmethod
    def generate_loglines(self, story_input: StoryInput) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def generate_characters(self, story_input: StoryInput, logline: dict[str, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def generate_three_act_plot(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def generate_chapter_plan(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
        three_act_plot: dict[str, Any],
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def generate_chapter_draft(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
        chapter_plan: list[dict[str, Any]],
        chapter_index: int = 0,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def revise_chapter_draft(
        self,
        story_input: StoryInput,
        chapter_plan: list[dict[str, Any]],
        chapter_draft: dict[str, Any],
        continuity_report: dict[str, Any],
        chapter_index: int = 0,
    ) -> dict[str, Any]:
        raise NotImplementedError
