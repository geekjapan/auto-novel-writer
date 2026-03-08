from __future__ import annotations

import re
from typing import Any

from novel_writer.schema import StoryArtifacts


class ContinuityChecker:
    def build_report(self, artifacts: StoryArtifacts) -> dict[str, Any]:
        selected_logline = artifacts.loglines[0] if artifacts.loglines else {}
        report = {
            "missing_fields": self._find_missing_fields(
                selected_logline,
                artifacts.characters,
                artifacts.three_act_plot,
                artifacts.chapter_plan,
                artifacts.chapter_1_draft,
            ),
            "character_name_mismatches": self._find_character_name_mismatches(
                artifacts.characters,
                artifacts.chapter_plan,
                artifacts.chapter_1_draft,
            ),
            "plot_to_plan_gaps": self._find_plot_to_plan_gaps(
                artifacts.three_act_plot,
                artifacts.chapter_plan,
            ),
            "plan_to_draft_gaps": self._find_plan_to_draft_gaps(
                artifacts.chapter_plan,
                artifacts.chapter_1_draft,
                artifacts.characters,
            ),
            "length_warnings": self._find_length_warnings(artifacts.chapter_plan, artifacts.chapter_1_draft),
        }
        report["issue_counts"] = {
            key: len(value)
            for key, value in report.items()
            if isinstance(value, list)
        }
        return report

    def _find_missing_fields(
        self,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
        three_act_plot: dict[str, Any],
        chapter_plan: list[dict[str, Any]],
        chapter_1_draft: dict[str, Any],
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        issues.extend(self._missing_dict_fields("logline", logline, ["id", "title", "premise", "hook"]))
        for index, character in enumerate(characters, start=1):
            issues.extend(
                self._missing_dict_fields(
                    f"characters[{index}]",
                    character,
                    ["name", "role", "goal", "conflict", "arc"],
                )
            )
        for act_name in ["act_1", "act_2", "act_3"]:
            if act_name not in three_act_plot:
                issues.append({"artifact": "three_act_plot", "field": act_name, "reason": "missing"})
        issues.extend(
            self._missing_dict_fields(
                "chapter_1_draft",
                chapter_1_draft,
                ["chapter_number", "title", "summary", "text"],
            )
        )
        if not chapter_plan:
            issues.append({"artifact": "chapter_plan", "field": "items", "reason": "missing"})
        return issues

    def _missing_dict_fields(
        self,
        artifact_name: str,
        payload: dict[str, Any],
        required_fields: list[str],
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for field_name in required_fields:
            value = payload.get(field_name)
            if value in (None, "", [], {}):
                issues.append({"artifact": artifact_name, "field": field_name, "reason": "missing"})
        return issues

    def _find_character_name_mismatches(
        self,
        characters: list[dict[str, Any]],
        chapter_plan: list[dict[str, Any]],
        chapter_1_draft: dict[str, Any],
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        names = {character.get("name", "") for character in characters if character.get("name")}
        if not names:
            return issues

        first_plan = chapter_plan[0] if chapter_plan else {}
        point_of_view = first_plan.get("point_of_view")
        if point_of_view and point_of_view not in names:
            issues.append(
                {
                    "artifact": "chapter_plan",
                    "field": "point_of_view",
                    "value": point_of_view,
                    "reason": "point_of_view_not_in_characters",
                }
            )

        draft_text = " ".join(
            [
                str(chapter_1_draft.get("title", "")),
                str(chapter_1_draft.get("summary", "")),
                str(chapter_1_draft.get("text", "")),
            ]
        )
        if point_of_view and point_of_view not in draft_text:
            issues.append(
                {
                    "artifact": "chapter_1_draft",
                    "field": "text",
                    "value": point_of_view,
                    "reason": "point_of_view_name_not_found_in_draft",
                }
            )

        draft_names = set(re.findall(r"[一-龠ぁ-んァ-ヶA-Za-z]+(?:\s?[一-龠ぁ-んァ-ヶA-Za-z]+)?", draft_text))
        unknown_names = sorted(name for name in draft_names if " " in name and name not in names)
        for name in unknown_names:
            issues.append(
                {
                    "artifact": "chapter_1_draft",
                    "field": "text",
                    "value": name,
                    "reason": "name_in_draft_not_in_characters",
                }
            )
        return issues

    def _find_plot_to_plan_gaps(
        self,
        three_act_plot: dict[str, Any],
        chapter_plan: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        plan_text = " ".join(
            f"{chapter.get('title', '')} {chapter.get('purpose', '')}"
            for chapter in chapter_plan
        )
        beat_map = [
            ("act_1", "setup"),
            ("act_1", "inciting_incident"),
            ("act_2", "rising_action"),
            ("act_2", "crisis"),
            ("act_3", "resolution"),
        ]
        for act_name, beat_name in beat_map:
            beat_text = str(three_act_plot.get(act_name, {}).get(beat_name, ""))
            if beat_text and beat_text not in plan_text:
                issues.append(
                    {
                        "plot_point": f"{act_name}.{beat_name}",
                        "reason": "plot_beat_not_reflected_in_chapter_plan",
                    }
                )
        return issues

    def _find_plan_to_draft_gaps(
        self,
        chapter_plan: list[dict[str, Any]],
        chapter_1_draft: dict[str, Any],
        characters: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        if not chapter_plan:
            return issues

        first_plan = chapter_plan[0]
        if chapter_1_draft.get("chapter_number") != first_plan.get("chapter_number"):
            issues.append(
                {
                    "field": "chapter_number",
                    "reason": "draft_chapter_number_does_not_match_plan",
                }
            )
        if chapter_1_draft.get("title") != first_plan.get("title"):
            issues.append(
                {
                    "field": "title",
                    "reason": "draft_title_does_not_match_plan",
                }
            )

        summary = str(chapter_1_draft.get("summary", ""))
        if first_plan.get("purpose") and summary != first_plan.get("purpose"):
            issues.append(
                {
                    "field": "summary",
                    "reason": "draft_summary_does_not_match_plan_purpose",
                }
            )

        point_of_view = first_plan.get("point_of_view")
        draft_text = str(chapter_1_draft.get("text", ""))
        if point_of_view and point_of_view not in draft_text:
            issues.append(
                {
                    "field": "point_of_view",
                    "reason": "planned_point_of_view_not_visible_in_draft",
                }
            )

        character_names = {character.get("name", "") for character in characters}
        if point_of_view and point_of_view not in character_names:
            issues.append(
                {
                    "field": "point_of_view",
                    "reason": "planned_point_of_view_not_defined_in_characters",
                }
            )
        return issues

    def _find_length_warnings(
        self,
        chapter_plan: list[dict[str, Any]],
        chapter_1_draft: dict[str, Any],
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        if not chapter_plan:
            return issues

        target_words = int(chapter_plan[0].get("target_words", 0) or 0)
        draft_text = str(chapter_1_draft.get("text", ""))
        actual_length = len(draft_text)
        if target_words and actual_length < max(200, int(target_words * 0.3)):
            issues.append(
                {
                    "field": "chapter_1_draft.text",
                    "target_words": target_words,
                    "actual_characters": actual_length,
                    "reason": "draft_is_significantly_shorter_than_plan_target",
                }
            )
        return issues

