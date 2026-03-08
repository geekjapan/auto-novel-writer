from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class StoryInput:
    theme: str
    genre: str
    tone: str
    target_length: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class StoryArtifacts:
    story_input: StoryInput
    loglines: list[dict] = field(default_factory=list)
    characters: list[dict] = field(default_factory=list)
    three_act_plot: dict = field(default_factory=dict)
    chapter_plan: list[dict] = field(default_factory=list)
    chapter_drafts: list[dict] = field(default_factory=list)
    chapter_1_draft: dict = field(default_factory=dict)
    continuity_report: dict = field(default_factory=dict)
    quality_report: dict = field(default_factory=dict)
    revised_chapter_drafts: list[dict] = field(default_factory=list)
    revised_chapter_1_draft: dict = field(default_factory=dict)
    rerun_history: list[dict] = field(default_factory=list)
    revise_history: list[dict] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "story_input": self.story_input.to_dict(),
            "phases": [
                "logline",
                "characters",
                "three_act_plot",
                "chapter_plan",
                "chapter_1_draft",
                "continuity_check",
                "revise_chapter_1",
            ],
            "counts": {
                "loglines": len(self.loglines),
                "characters": len(self.characters),
                "chapters": len(self.chapter_plan),
            },
        }

    def set_chapter_draft(self, chapter_index: int, payload: dict) -> None:
        self._ensure_slot(self.chapter_drafts, chapter_index)
        self.chapter_drafts[chapter_index] = payload
        if chapter_index == 0:
            self.chapter_1_draft = payload

    def get_chapter_draft(self, chapter_index: int) -> dict:
        if 0 <= chapter_index < len(self.chapter_drafts):
            return self.chapter_drafts[chapter_index]
        if chapter_index == 0:
            return self.chapter_1_draft
        return {}

    def set_revised_chapter_draft(self, chapter_index: int, payload: dict) -> None:
        self._ensure_slot(self.revised_chapter_drafts, chapter_index)
        self.revised_chapter_drafts[chapter_index] = payload
        if chapter_index == 0:
            self.revised_chapter_1_draft = payload

    def get_revised_chapter_draft(self, chapter_index: int) -> dict:
        if 0 <= chapter_index < len(self.revised_chapter_drafts):
            return self.revised_chapter_drafts[chapter_index]
        if chapter_index == 0:
            return self.revised_chapter_1_draft
        return {}

    @staticmethod
    def _ensure_slot(items: list[dict], chapter_index: int) -> None:
        while len(items) <= chapter_index:
            items.append({})
