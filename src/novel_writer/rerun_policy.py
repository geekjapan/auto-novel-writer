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
    "long_run": {
        "max_high_severity_chapters": 10,
        "max_total_rerun_attempts": 20,
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

    def decide_long_run(self, continuity_history: list[dict[str, Any]], rerun_history: list[dict[str, Any]]) -> dict[str, Any]:
        long_run_config = self.config.get("long_run", {})
        max_high_severity_chapters = long_run_config.get("max_high_severity_chapters", 10)
        max_total_rerun_attempts = long_run_config.get("max_total_rerun_attempts", 20)
        high_severity_chapters = sum(1 for report in continuity_history if report.get("severity") == "high")
        total_rerun_attempts = sum(1 for entry in rerun_history if entry.get("attempt", 0) > 1)
        should_stop = False
        reason = None
        stop_after_step = None

        if high_severity_chapters >= max_high_severity_chapters:
            should_stop = True
            reason = "high_severity_chapter_limit_reached"
            stop_after_step = "continuity_report"
        elif total_rerun_attempts >= max_total_rerun_attempts:
            should_stop = True
            reason = "total_rerun_limit_reached"
            stop_after_step = "continuity_report"

        return {
            "should_stop": should_stop,
            "reason": reason,
            "stop_after_step": stop_after_step,
            "high_severity_chapters": high_severity_chapters,
            "max_high_severity_chapters": max_high_severity_chapters,
            "remaining_high_severity_chapter_budget": max(0, max_high_severity_chapters - high_severity_chapters),
            "total_rerun_attempts": total_rerun_attempts,
            "max_total_rerun_attempts": max_total_rerun_attempts,
            "remaining_rerun_attempt_budget": max(0, max_total_rerun_attempts - total_rerun_attempts),
            "resume_requires_explicit_rerun": should_stop,
            "resume_guidance": (
                "resume will preserve the stopped state until an explicit rerun is requested"
                if should_stop
                else "resume can continue automatically"
            ),
            "policy_limits": {
                "max_high_severity_chapters": max_high_severity_chapters,
                "max_total_rerun_attempts": max_total_rerun_attempts,
            },
        }

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
