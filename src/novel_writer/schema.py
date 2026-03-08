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
    chapter_1_draft: dict = field(default_factory=dict)
    continuity_report: dict = field(default_factory=dict)
    rerun_history: list[dict] = field(default_factory=list)

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
            ],
            "counts": {
                "loglines": len(self.loglines),
                "characters": len(self.characters),
                "chapters": len(self.chapter_plan),
            },
        }
