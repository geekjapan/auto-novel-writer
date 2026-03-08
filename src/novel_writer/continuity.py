from __future__ import annotations

import re
from typing import Any

from novel_writer.schema import StoryArtifacts

STOPWORDS = {
    "こと",
    "もの",
    "ため",
    "よう",
    "それ",
    "これ",
    "そして",
    "しかし",
    "主人公",
    "短編",
}

NON_NAME_TOKENS = {
    "導入",
    "転機",
    "対立",
    "危機",
    "結末",
    "余韻",
    "主人公",
    "手紙",
    "電話",
    "親友",
    "旧友",
    "自宅",
    "机",
    "封筒",
    "部屋",
    "真相",
}

PARTICLE_SPLIT_PATTERN = r"[、。・,\s\n\r\t]|(?:では|には|へは|から|まで|より)|[はがをにへのともでやか]"

REGENERATE_CATEGORIES = {
    "missing_fields",
    "plot_to_plan_gaps",
}

REVISE_CATEGORIES = {
    "character_name_mismatches",
    "plan_to_draft_gaps",
    "length_warnings",
    "pov_consistency_issues",
    "chapter_length_balance_warnings",
    "character_continuity_issues",
}


class ContinuityChecker:
    def build_report(self, artifacts: StoryArtifacts, chapter_index: int = 0) -> dict[str, Any]:
        selected_logline = artifacts.loglines[0] if artifacts.loglines else {}
        chapter_draft = artifacts.get_chapter_draft(chapter_index)
        chapter = artifacts.chapter_plan[chapter_index] if 0 <= chapter_index < len(artifacts.chapter_plan) else {}
        report = {
            "missing_fields": self._find_missing_fields(
                selected_logline,
                artifacts.characters,
                artifacts.three_act_plot,
                artifacts.chapter_plan,
                chapter_draft,
                chapter_index,
            ),
            "character_name_mismatches": self._find_character_name_mismatches(
                artifacts.characters,
                chapter,
                chapter_draft,
                chapter_index,
            ),
            "plot_to_plan_gaps": self._find_plot_to_plan_gaps(
                artifacts.three_act_plot,
                artifacts.chapter_plan,
            ),
            "plan_to_draft_gaps": self._find_plan_to_draft_gaps(
                chapter,
                chapter_draft,
                artifacts.characters,
                chapter_index,
            ),
            "length_warnings": self._find_length_warnings(chapter, chapter_draft, chapter_index),
            "pov_consistency_issues": self._find_pov_consistency_issues(
                artifacts.chapter_plan,
                artifacts.characters,
            ),
            "chapter_length_balance_warnings": self._find_chapter_length_balance_warnings(artifacts.chapter_plan),
            "character_continuity_issues": self._find_character_continuity_issues(
                artifacts.characters,
                artifacts.chapter_plan,
                chapter_draft,
                chapter_index,
            ),
        }
        report["chapter_index"] = chapter_index
        report["chapter_number"] = chapter.get("chapter_number")
        report["issue_counts"] = {
            key: len(value)
            for key, value in report.items()
            if isinstance(value, list)
        }
        return report

    def build_quality_report(self, continuity_report: dict[str, Any]) -> dict[str, Any]:
        issue_counts = continuity_report.get("issue_counts", {})
        recommendations: list[dict[str, Any]] = []
        for category, count in issue_counts.items():
            if count <= 0:
                continue
            recommendations.append(
                {
                    "category": category,
                    "issue_count": count,
                    "recommended_action": self._recommend_action_for_category(category),
                }
            )

        overall_recommendation = "accept"
        if any(item["recommended_action"] == "regenerate" for item in recommendations):
            overall_recommendation = "regenerate"
        elif any(item["recommended_action"] == "revise" for item in recommendations):
            overall_recommendation = "revise"

        return {
            "overall_recommendation": overall_recommendation,
            "total_issue_count": sum(issue_counts.values()),
            "severity": continuity_report.get("severity", "unknown"),
            "source_report": "continuity_report",
            "recommendations": recommendations,
            "issue_counts": dict(issue_counts),
        }

    def _recommend_action_for_category(self, category: str) -> str:
        if category in REGENERATE_CATEGORIES:
            return "regenerate"
        if category in REVISE_CATEGORIES:
            return "revise"
        return "inspect"

    def _find_missing_fields(
        self,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
        three_act_plot: dict[str, Any],
        chapter_plan: list[dict[str, Any]],
        chapter_draft: dict[str, Any],
        chapter_index: int,
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
                self._chapter_draft_artifact_name(chapter_index),
                chapter_draft,
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
        chapter: dict[str, Any],
        chapter_draft: dict[str, Any],
        chapter_index: int,
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        names = {character.get("name", "") for character in characters if character.get("name")}
        if not names:
            return issues

        point_of_view = chapter.get("point_of_view")
        if point_of_view and point_of_view not in names:
            issues.append(
                {
                    "artifact": self._chapter_plan_artifact_name(chapter_index),
                    "field": "point_of_view",
                    "value": point_of_view,
                    "reason": "point_of_view_not_in_characters",
                }
            )

        draft_text = " ".join(
            [
                str(chapter_draft.get("title", "")),
                str(chapter_draft.get("summary", "")),
                str(chapter_draft.get("text", "")),
            ]
        )
        if point_of_view and point_of_view not in draft_text:
            issues.append(
                {
                    "artifact": self._chapter_draft_artifact_name(chapter_index),
                    "field": "text",
                    "value": point_of_view,
                    "reason": "point_of_view_name_not_found_in_draft",
                }
            )

        draft_names = self._extract_probable_names(draft_text)
        unknown_names = sorted(name for name in draft_names if name not in names)
        for name in unknown_names:
            issues.append(
                {
                    "artifact": self._chapter_draft_artifact_name(chapter_index),
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
        plan_keywords = self._extract_keywords(
            " ".join(
                f"{chapter.get('title', '')} {chapter.get('purpose', '')}"
                for chapter in chapter_plan
            )
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
            beat_keywords = self._extract_keywords(beat_text)
            if beat_keywords and not self._has_keyword_overlap(beat_keywords, plan_keywords, minimum_ratio=0.4):
                issues.append(
                    {
                        "plot_point": f"{act_name}.{beat_name}",
                        "reason": "plot_beat_not_reflected_in_chapter_plan",
                        "keywords": beat_keywords,
                    }
                )
        return issues

    def _find_plan_to_draft_gaps(
        self,
        chapter: dict[str, Any],
        chapter_draft: dict[str, Any],
        characters: list[dict[str, Any]],
        chapter_index: int,
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        if not chapter:
            return issues

        if chapter_draft.get("chapter_number") != chapter.get("chapter_number"):
            issues.append(
                {
                    "field": "chapter_number",
                    "reason": "draft_chapter_number_does_not_match_plan",
                }
            )
        if chapter_draft.get("title") != chapter.get("title"):
            issues.append(
                {
                    "field": "title",
                    "reason": "draft_title_does_not_match_plan",
                }
            )

        purpose = str(chapter.get("purpose", ""))
        summary = str(chapter_draft.get("summary", ""))
        purpose_keywords = self._extract_keywords(purpose)
        summary_keywords = self._extract_keywords(summary)
        if purpose_keywords and not self._has_keyword_overlap(
            purpose_keywords,
            summary_keywords,
            minimum_ratio=0.5,
        ):
            issues.append(
                {
                    "field": "summary",
                    "reason": "draft_summary_does_not_reflect_plan_keywords",
                    "expected_keywords": purpose_keywords,
                    "observed_keywords": summary_keywords,
                }
            )

        point_of_view = chapter.get("point_of_view")
        draft_text = str(chapter_draft.get("text", ""))
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
        chapter: dict[str, Any],
        chapter_draft: dict[str, Any],
        chapter_index: int,
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        if not chapter:
            return issues

        target_words = int(chapter.get("target_words", 0) or 0)
        draft_text = str(chapter_draft.get("text", ""))
        actual_length = len(draft_text)
        if target_words and actual_length < max(200, int(target_words * 0.3)):
            issues.append(
                {
                    "field": f"{self._chapter_draft_artifact_name(chapter_index)}.text",
                    "target_words": target_words,
                    "actual_characters": actual_length,
                    "reason": "draft_is_significantly_shorter_than_plan_target",
                }
            )
        return issues

    def _find_pov_consistency_issues(
        self,
        chapter_plan: list[dict[str, Any]],
        characters: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        if not chapter_plan:
            return issues

        character_names = {character.get("name", "") for character in characters if character.get("name")}
        pov_entries = [
            (index, str(chapter.get("point_of_view", "")).strip())
            for index, chapter in enumerate(chapter_plan)
        ]
        invalid_entries = [
            {
                "chapter_index": index,
                "chapter_number": chapter_plan[index].get("chapter_number"),
                "value": point_of_view,
                "reason": "point_of_view_not_in_characters",
            }
            for index, point_of_view in pov_entries
            if point_of_view and point_of_view not in character_names
        ]
        issues.extend(invalid_entries)

        unique_povs = []
        for _index, point_of_view in pov_entries:
            if point_of_view and point_of_view not in unique_povs:
                unique_povs.append(point_of_view)
        if len(unique_povs) > 1:
            issues.append(
                {
                    "reason": "multiple_point_of_view_values_across_chapter_plan",
                    "values": unique_povs,
                }
            )
        return issues

    def _find_chapter_length_balance_warnings(
        self,
        chapter_plan: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        target_words = [
            int(chapter.get("target_words", 0) or 0)
            for chapter in chapter_plan
            if int(chapter.get("target_words", 0) or 0) > 0
        ]
        if len(target_words) < 2:
            return issues

        average = sum(target_words) / len(target_words)
        min_target = min(target_words)
        max_target = max(target_words)
        if min_target and (max_target / min_target) >= 1.8:
            issues.append(
                {
                    "reason": "chapter_target_words_are_unbalanced",
                    "min_target_words": min_target,
                    "max_target_words": max_target,
                }
            )

        for index, chapter in enumerate(chapter_plan):
            target = int(chapter.get("target_words", 0) or 0)
            if target <= 0:
                continue
            if target < average * 0.6 or target > average * 1.4:
                issues.append(
                    {
                        "chapter_index": index,
                        "chapter_number": chapter.get("chapter_number"),
                        "target_words": target,
                        "average_target_words": round(average, 2),
                        "reason": "chapter_target_words_deviate_from_plan_average",
                    }
                )
        return issues

    def _find_character_continuity_issues(
        self,
        characters: list[dict[str, Any]],
        chapter_plan: list[dict[str, Any]],
        chapter_draft: dict[str, Any],
        chapter_index: int,
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        combined_text = " ".join(
            [
                " ".join(
                    f"{chapter.get('title', '')} {chapter.get('purpose', '')} {chapter.get('point_of_view', '')}"
                    for chapter in chapter_plan
                ),
                str(chapter_draft.get("title", "")),
                str(chapter_draft.get("summary", "")),
                str(chapter_draft.get("text", "")),
            ]
        )
        for character in characters:
            name = str(character.get("name", "")).strip()
            if not name:
                continue
            if name not in combined_text:
                issues.append(
                    {
                        "character": name,
                        "role": character.get("role"),
                        "chapter_index": chapter_index,
                        "reason": "character_defined_but_not_referenced_in_plan_or_draft",
                    }
                )
        return issues

    def _chapter_draft_artifact_name(self, chapter_index: int) -> str:
        if chapter_index == 0:
            return "chapter_1_draft"
        return f"chapter_drafts[{chapter_index}]"

    def _chapter_plan_artifact_name(self, chapter_index: int) -> str:
        return f"chapter_plan[{chapter_index}]"

    def _extract_keywords(self, text: str) -> list[str]:
        normalized_text = re.sub(PARTICLE_SPLIT_PATTERN, " ", text)
        raw_chunks = [chunk for chunk in normalized_text.split(" ") if chunk]
        keywords: list[str] = []
        for chunk in raw_chunks:
            for token in self._expand_keyword_chunk(chunk):
                normalized = token.strip().lower()
                if normalized in STOPWORDS:
                    continue
                if re.fullmatch(r"[ぁ-ん]{2,}", normalized):
                    continue
                keywords.append(normalized)
        deduped: list[str] = []
        for keyword in keywords:
            if keyword not in deduped:
                deduped.append(keyword)
        return deduped

    def _expand_keyword_chunk(self, chunk: str) -> list[str]:
        tokens: list[str] = []
        if len(chunk) >= 2:
            tokens.append(chunk)
        tokens.extend(re.findall(r"[一-龠]{2,}", chunk))
        tokens.extend(re.findall(r"[ァ-ヶー]{2,}", chunk))
        tokens.extend(re.findall(r"[A-Za-z0-9]{2,}", chunk))
        return tokens

    def _has_keyword_overlap(
        self,
        source_keywords: list[str],
        target_keywords: list[str],
        minimum_ratio: float,
    ) -> bool:
        if not source_keywords:
            return True
        matches = 0
        for keyword in source_keywords:
            if any(keyword in target or target in keyword for target in target_keywords):
                matches += 1
        return (matches / len(source_keywords)) >= minimum_ratio

    def _extract_probable_names(self, text: str) -> set[str]:
        matches = set()
        for pattern in [
            r"[一-龠]{2,3}\s[一-龠]{1,3}",
            r"[ァ-ヶー]{2,}\s[ァ-ヶー]{2,}",
            r"[A-Z][a-zA-Z]{1,20}\s[A-Z][a-zA-Z]{1,20}",
        ]:
            matches.update(re.findall(pattern, text))
        filtered = set()
        for match in matches:
            parts = match.split(" ")
            if any(part in NON_NAME_TOKENS for part in parts):
                continue
            filtered.add(match)
        return filtered
