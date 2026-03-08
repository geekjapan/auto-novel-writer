from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DEFAULT_SEVERITY_POLICY = {
    "weights": {
        "missing_fields": 5,
        "character_name_mismatches": 2,
        "plot_to_plan_gaps": 4,
        "plan_to_draft_gaps": 3,
        "length_warnings": 1,
    },
    "thresholds": {
        "high": 8,
        "medium": 3,
    },
    "forced_high": {
        "missing_fields": 1,
        "plot_to_plan_gaps": 2,
    },
}


@dataclass(slots=True)
class RerunDecision:
    severity: str
    action: str
    weighted_score: int
    issue_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "action": self.action,
            "weighted_score": self.weighted_score,
            "issue_counts": self.issue_counts,
        }


class ContinuityRerunPolicy:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or DEFAULT_SEVERITY_POLICY

    def decide(self, issue_counts: dict[str, int]) -> RerunDecision:
        score = self._weighted_score(issue_counts)
        severity = self._classify(issue_counts, score)
        action = self._action_for(severity)
        return RerunDecision(
            severity=severity,
            action=action,
            weighted_score=score,
            issue_counts=dict(issue_counts),
        )

    def _weighted_score(self, issue_counts: dict[str, int]) -> int:
        weights = self.config["weights"]
        return sum(issue_counts.get(key, 0) * weights.get(key, 0) for key in issue_counts)

    def _classify(self, issue_counts: dict[str, int], score: int) -> str:
        for key, threshold in self.config["forced_high"].items():
            if issue_counts.get(key, 0) >= threshold:
                return "high"

        thresholds = self.config["thresholds"]
        if score >= thresholds["high"]:
            return "high"
        if score >= thresholds["medium"]:
            return "medium"
        return "low"

    def _action_for(self, severity: str) -> str:
        if severity == "high":
            return "rerun_from_chapter_plan"
        if severity == "medium":
            return "rerun_chapter_1_draft"
        return "continue"

