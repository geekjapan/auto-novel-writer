from __future__ import annotations

from dataclasses import asdict, dataclass, field


def chapter_artifact_contract() -> dict:
    return {
        "canonical_story_state": {
            "chapter_drafts": {
                "primary_collection": "chapter_drafts",
                "artifact_pattern": "chapter_{n}_draft",
                "compatibility_field": "chapter_1_draft",
                "compatibility_artifact": "05_chapter_1_draft",
                "compatibility_chapter_index": 0,
            },
            "revised_chapter_drafts": {
                "primary_collection": "revised_chapter_drafts",
                "artifact_pattern": "revised_chapter_{n}_draft",
                "compatibility_field": "revised_chapter_1_draft",
                "compatibility_artifact": "revised_chapter_1_draft",
                "compatibility_chapter_index": 0,
            },
            "continuity_history": {
                "primary_collection": "continuity_history",
                "compatibility_field": "continuity_report",
                "compatibility_artifact": "continuity_report",
                "compatibility_chapter_index": 0,
            },
        }
    }


def chapter_briefs_contract() -> dict:
    return {
        "schema_name": "chapter_briefs",
        "schema_version": "1.0",
        "required_fields": [
            "chapter_number",
            "purpose",
            "goal",
            "conflict",
            "turn",
            "must_include",
            "continuity_dependencies",
            "foreshadowing_targets",
            "arc_progress",
            "target_length_guidance",
        ],
    }


def story_bible_contract() -> dict:
    return {
        "schema_name": "story_bible",
        "schema_version": "1.0",
        "required_fields": [
            "schema_name",
            "schema_version",
            "core_premise",
            "ending_reveal",
            "theme_statement",
            "character_arcs",
            "world_rules",
            "forbidden_facts",
            "foreshadowing_seeds",
        ],
        "list_fields": [
            "character_arcs",
            "world_rules",
            "forbidden_facts",
            "foreshadowing_seeds",
        ],
    }


def validate_story_bible(payload: dict) -> dict:
    contract = story_bible_contract()
    missing_fields = [field for field in contract["required_fields"] if field not in payload]
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(
            "Invalid story_bible: missing required fields: "
            f"{missing}. Regenerate the story bible from the pipeline."
        )

    if payload.get("schema_name") != contract["schema_name"]:
        raise ValueError(
            "Invalid story_bible: "
            f"schema_name={payload.get('schema_name')!r} is not supported; expected {contract['schema_name']!r}."
        )

    if payload.get("schema_version") != contract["schema_version"]:
        raise ValueError(
            "Invalid story_bible: "
            f"schema_version={payload.get('schema_version')!r} is not supported; expected {contract['schema_version']!r}."
        )

    for field_name in ["core_premise", "ending_reveal", "theme_statement"]:
        if not isinstance(payload.get(field_name), str):
            raise ValueError(f"Invalid story_bible: {field_name} must be a string.")

    for field_name in contract["list_fields"]:
        if not isinstance(payload.get(field_name), list):
            raise ValueError(f"Invalid story_bible: {field_name} must be a list.")

    return payload


def validate_chapter_briefs(payload: list[dict]) -> list[dict]:
    if not isinstance(payload, list) or not payload:
        raise ValueError("Invalid chapter_briefs: payload must be a non-empty list.")

    contract = chapter_briefs_contract()
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Invalid chapter_briefs: chapter_briefs[{index}] must be an object.")

        missing_fields = [field for field in contract["required_fields"] if field not in item]
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ValueError(
                "Invalid chapter_briefs: "
                f"chapter_briefs[{index}] is missing required fields: {missing}."
            )

    return payload


def scene_cards_contract() -> dict:
    return {
        "schema_name": "scene_cards",
        "schema_version": "1.0",
        "required_fields": [
            "chapter_number",
            "scenes",
        ],
    }


def validate_scene_cards(payload: list[dict]) -> list[dict]:
    if not isinstance(payload, list) or not payload:
        raise ValueError("Invalid scene_cards: payload must be a non-empty list.")

    contract = scene_cards_contract()
    for index, chapter_packet in enumerate(payload):
        if not isinstance(chapter_packet, dict):
            raise ValueError(f"Invalid scene_cards: scene_cards[{index}] must be an object.")

        missing_fields = [field for field in contract["required_fields"] if field not in chapter_packet]
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ValueError(
                "Invalid scene_cards: "
                f"scene_cards[{index}] is missing required fields: {missing}."
            )

        scenes = chapter_packet.get("scenes")
        if not isinstance(scenes, list) or not 3 <= len(scenes) <= 7:
            raise ValueError(
                f"Invalid scene_cards: scene_cards[{index}] must contain between 3 and 7 scenes."
            )

    return payload


def publish_ready_bundle_contract() -> dict:
    return {
        "schema_name": "publish_ready_bundle",
        "schema_version": "1.0",
        "required_fields": [
            "schema_version",
            "bundle_type",
            "title",
            "synopsis",
            "chapter_count",
            "chapters",
            "story_summary",
            "overall_quality_report",
            "selected_logline",
            "source_artifacts",
            "sections",
        ],
        "sections": {
            "manuscript": {
                "field": "chapters",
                "description": "Revised chapter draft collection for downstream publishing or export.",
            },
            "story_summary": {
                "field": "story_summary",
                "description": "Whole-story summary and chapter summaries.",
            },
            "quality": {
                "field": "overall_quality_report",
                "description": "Project-level quality evaluation for downstream review.",
            },
        },
    }


def validate_publish_ready_bundle(payload: dict) -> dict:
    contract = publish_ready_bundle_contract()
    missing_fields = [field for field in contract["required_fields"] if field not in payload]
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(
            "Invalid publish_ready_bundle: missing required fields: "
            f"{missing}. Regenerate the publish bundle from the pipeline."
        )

    schema_version = payload.get("schema_version")
    if schema_version != contract["schema_version"]:
        raise ValueError(
            "Invalid publish_ready_bundle: "
            f"schema_version={schema_version!r} is not supported; expected {contract['schema_version']!r}."
        )

    bundle_type = payload.get("bundle_type")
    if bundle_type != contract["schema_name"]:
        raise ValueError(
            "Invalid publish_ready_bundle: "
            f"bundle_type={bundle_type!r} is not supported; expected {contract['schema_name']!r}."
        )

    sections = payload.get("sections", {})
    for section_name, section_contract in contract["sections"].items():
        section_payload = sections.get(section_name)
        if not isinstance(section_payload, dict):
            raise ValueError(
                "Invalid publish_ready_bundle: "
                f"sections.{section_name!s} must be an object with field metadata."
            )
        if section_payload.get("field") != section_contract["field"]:
            raise ValueError(
                "Invalid publish_ready_bundle: "
                f"sections.{section_name}.field={section_payload.get('field')!r} "
                f"is not supported; expected {section_contract['field']!r}."
            )

    return payload


def project_manifest_contract() -> dict:
    return {
        "schema_name": "project_manifest",
        "schema_version": "1.0",
        "required_fields": [
            "project_id",
            "project_slug",
            "projects_dir",
            "current_run",
            "run_candidates",
            "best_run",
        ],
        "current_run": {
            "required_fields": [
                "name",
                "output_dir",
                "comparison_metrics",
                "comparison_basis",
                "comparison_reason",
                "comparison_reason_details",
            ],
        },
        "best_run": {
            "required_fields": [
                "run_name",
                "output_dir",
                "comparison_metrics",
                "comparison_basis",
                "selection_source",
                "selection_reason",
                "selection_reason_details",
            ],
        },
        "run_candidate": {
            "required_fields": [
                "run_name",
                "output_dir",
                "comparison_metrics",
                "comparison_basis",
                "comparison_reason",
                "comparison_reason_details",
            ],
        },
        "reason_detail_codes": comparison_reason_detail_codes(),
    }


def run_comparison_summary_contract() -> dict:
    return {
        "schema_name": "run_comparison_summary",
        "schema_version": "1.0",
        "required_fields": [
            "schema_name",
            "schema_version",
            "project_id",
            "project_slug",
            "current_run",
            "best_run",
            "candidate_count",
            "compact_summary",
            "run_candidates",
        ],
        "current_run": {
            "required_fields": [
                "run_name",
                "output_dir",
                "comparison_metrics",
                "comparison_basis",
                "comparison_reason",
                "comparison_reason_details",
            ],
        },
        "best_run": {
            "required_fields": [
                "run_name",
                "output_dir",
                "comparison_metrics",
                "comparison_basis",
                "selection_source",
                "selection_reason",
                "selection_reason_details",
            ],
        },
        "run_candidate": {
            "required_fields": [
                "run_name",
                "output_dir",
                "comparison_metrics",
                "comparison_basis",
                "comparison_reason",
                "comparison_reason_details",
            ],
        },
        "reason_detail_codes": comparison_reason_detail_codes(),
        "compact_summary": {
            "selection_source": "string",
            "issue_score": ["current", "best"],
            "completed_step_count": ["current", "best"],
            "long_run_should_stop": ["current", "best"],
            "policy_limits": {
                "max_high_severity_chapters": ["current", "best"],
                "max_total_rerun_attempts": ["current", "best"],
            },
        },
    }


def validate_run_comparison_summary(payload: dict) -> dict:
    contract = run_comparison_summary_contract()
    missing_fields = [field for field in contract["required_fields"] if field not in payload]
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(
            "Invalid run_comparison_summary: missing required fields: "
            f"{missing}. Regenerate the project comparison summary."
        )

    if payload.get("schema_name") != contract["schema_name"]:
        raise ValueError(
            "Invalid run_comparison_summary: "
            f"schema_name={payload.get('schema_name')!r} is not supported; expected {contract['schema_name']!r}."
        )

    if payload.get("schema_version") != contract["schema_version"]:
        raise ValueError(
            "Invalid run_comparison_summary: "
            f"schema_version={payload.get('schema_version')!r} is not supported; expected {contract['schema_version']!r}."
        )

    _validate_run_comparison_context(
        payload.get("current_run"),
        "current_run",
        contract["current_run"]["required_fields"],
    )
    _validate_run_comparison_context(
        payload.get("best_run"),
        "best_run",
        contract["best_run"]["required_fields"],
    )
    run_candidates = payload.get("run_candidates")
    if not isinstance(run_candidates, list):
        raise ValueError("Invalid run_comparison_summary: run_candidates must be a list.")
    for index, candidate in enumerate(run_candidates):
        _validate_run_comparison_context(
            candidate,
            f"run_candidates[{index}]",
            contract["run_candidate"]["required_fields"],
        )

    compact_summary = payload.get("compact_summary")
    if not isinstance(compact_summary, dict):
        raise ValueError("Invalid run_comparison_summary: compact_summary must be an object.")

    compact_contract = contract["compact_summary"]
    if not isinstance(compact_summary.get("selection_source"), str):
        raise ValueError("Invalid run_comparison_summary: compact_summary.selection_source must be a string.")

    for key in ["issue_score", "completed_step_count", "long_run_should_stop"]:
        _validate_current_best_pair(
            compact_summary.get(key),
            f"compact_summary.{key}",
        )

    policy_limits = compact_summary.get("policy_limits")
    if not isinstance(policy_limits, dict):
        raise ValueError("Invalid run_comparison_summary: compact_summary.policy_limits must be an object.")
    for key in compact_contract["policy_limits"]:
        _validate_current_best_pair(
            policy_limits.get(key),
            f"compact_summary.policy_limits.{key}",
        )

    return payload


def _validate_current_best_pair(payload: dict | None, field_name: str) -> None:
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid run_comparison_summary: {field_name} must be an object.")
    missing_fields = [key for key in ["current", "best"] if key not in payload]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Invalid run_comparison_summary: {field_name} is missing fields: {missing}.")


def _validate_run_comparison_context(
    payload: dict | None,
    field_name: str,
    required_fields: list[str],
) -> None:
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid run_comparison_summary: {field_name} must be an object.")

    missing_fields = [key for key in required_fields if key not in payload]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Invalid run_comparison_summary: {field_name} is missing fields: {missing}.")

    if not isinstance(payload.get("comparison_metrics"), dict):
        raise ValueError(f"Invalid run_comparison_summary: {field_name}.comparison_metrics must be an object.")
    if not isinstance(payload.get("comparison_basis"), list):
        raise ValueError(f"Invalid run_comparison_summary: {field_name}.comparison_basis must be a list.")

    uses_selection_reason = field_name == "best_run"
    reason_field = "selection_reason" if uses_selection_reason else "comparison_reason"
    if not isinstance(payload.get(reason_field), list):
        raise ValueError(f"Invalid run_comparison_summary: {field_name}.{reason_field} must be a list.")

    detail_field = "selection_reason_details" if uses_selection_reason else "comparison_reason_details"
    details = payload.get(detail_field)
    if not isinstance(details, list):
        raise ValueError(f"Invalid run_comparison_summary: {field_name}.{detail_field} must be a list.")
    allowed_codes = set(run_comparison_summary_contract()["reason_detail_codes"])
    for index, detail in enumerate(details):
        if not isinstance(detail, dict):
            raise ValueError(f"Invalid run_comparison_summary: {field_name}.{detail_field}[{index}] must be an object.")
        missing_detail_fields = [key for key in ["code", "value"] if key not in detail]
        if missing_detail_fields:
            missing = ", ".join(missing_detail_fields)
            raise ValueError(
                f"Invalid run_comparison_summary: {field_name}.{detail_field}[{index}] is missing fields: {missing}."
            )
        if not isinstance(detail.get("code"), str):
            raise ValueError(
                f"Invalid run_comparison_summary: {field_name}.{detail_field}[{index}].code must be a string."
            )
        if detail.get("code") not in allowed_codes:
            allowed = ", ".join(sorted(allowed_codes))
            raise ValueError(
                "Invalid run_comparison_summary: "
                f"{field_name}.{detail_field}[{index}].code={detail.get('code')!r} is not supported; "
                f"expected one of: {allowed}."
            )

    if uses_selection_reason and not isinstance(payload.get("selection_source"), str):
        raise ValueError("Invalid run_comparison_summary: best_run.selection_source must be a string.")


def comparison_reason_detail_codes() -> list[str]:
    return [
        "manual_selection",
        "long_run_should_stop",
        "total_issue_score",
        "high_severity_chapter_count",
        "rerun_attempt_total",
        "revision_attempt_total",
        "completed_step_count",
    ]


def validate_project_manifest(payload: dict) -> dict:
    contract = project_manifest_contract()
    missing_fields = [field for field in contract["required_fields"] if field not in payload]
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(
            "Invalid project_manifest: missing required fields: "
            f"{missing}. Recreate the manifest or rerun create-project."
        )

    schema_name = payload.get("schema_name")
    if schema_name is not None and schema_name != contract["schema_name"]:
        raise ValueError(
            "Invalid project_manifest: "
            f"schema_name={schema_name!r} is not supported; expected {contract['schema_name']!r}."
        )

    schema_version = payload.get("schema_version")
    if schema_version is not None and schema_version != contract["schema_version"]:
        raise ValueError(
            "Invalid project_manifest: "
            f"schema_version={schema_version!r} is not supported; expected {contract['schema_version']!r}."
        )

    _validate_project_manifest_reason_context(
        payload.get("current_run"),
        "current_run",
        contract["current_run"]["required_fields"],
        "comparison_reason_details",
        contract["reason_detail_codes"],
    )
    _validate_project_manifest_reason_context(
        payload.get("best_run"),
        "best_run",
        contract["best_run"]["required_fields"],
        "selection_reason_details",
        contract["reason_detail_codes"],
    )

    run_candidates = payload.get("run_candidates")
    if not isinstance(run_candidates, list):
        raise ValueError("Invalid project_manifest: run_candidates must be a list.")
    for index, candidate in enumerate(run_candidates):
        _validate_project_manifest_reason_context(
            candidate,
            f"run_candidates[{index}]",
            contract["run_candidate"]["required_fields"],
            "comparison_reason_details",
            contract["reason_detail_codes"],
        )

    return payload


def _validate_project_manifest_reason_context(
    payload: dict | None,
    field_name: str,
    required_fields: list[str],
    detail_field: str,
    allowed_codes: list[str],
) -> None:
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid project_manifest: {field_name} must be an object.")

    missing_fields = [key for key in required_fields if key not in payload]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Invalid project_manifest: {field_name} is missing fields: {missing}.")

    if not isinstance(payload.get("comparison_metrics"), dict):
        raise ValueError(f"Invalid project_manifest: {field_name}.comparison_metrics must be an object.")
    if not isinstance(payload.get("comparison_basis"), list):
        raise ValueError(f"Invalid project_manifest: {field_name}.comparison_basis must be a list.")

    reason_field = "selection_reason" if detail_field == "selection_reason_details" else "comparison_reason"
    if not isinstance(payload.get(reason_field), list):
        raise ValueError(f"Invalid project_manifest: {field_name}.{reason_field} must be a list.")
    if detail_field == "selection_reason_details" and not isinstance(payload.get("selection_source"), str):
        raise ValueError(f"Invalid project_manifest: {field_name}.selection_source must be a string.")

    details = payload.get(detail_field)
    if not isinstance(details, list):
        raise ValueError(f"Invalid project_manifest: {field_name}.{detail_field} must be a list.")

    allowed = set(allowed_codes)
    for index, detail in enumerate(details):
        if not isinstance(detail, dict):
            raise ValueError(f"Invalid project_manifest: {field_name}.{detail_field}[{index}] must be an object.")
        missing_detail_fields = [key for key in ["code", "value"] if key not in detail]
        if missing_detail_fields:
            missing = ", ".join(missing_detail_fields)
            raise ValueError(
                f"Invalid project_manifest: {field_name}.{detail_field}[{index}] is missing fields: {missing}."
            )
        if not isinstance(detail.get("code"), str):
            raise ValueError(f"Invalid project_manifest: {field_name}.{detail_field}[{index}].code must be a string.")
        if detail.get("code") not in allowed:
            expected = ", ".join(sorted(allowed))
            raise ValueError(
                "Invalid project_manifest: "
                f"{field_name}.{detail_field}[{index}].code={detail.get('code')!r} is not supported; "
                f"expected one of: {expected}."
            )


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
    story_bible: dict = field(default_factory=dict)
    chapter_plan: list[dict] = field(default_factory=list)
    chapter_briefs: list[dict] = field(default_factory=list)
    scene_cards: list[dict] = field(default_factory=list)
    chapter_drafts: list[dict] = field(default_factory=list)
    chapter_1_draft: dict = field(default_factory=dict)
    continuity_report: dict = field(default_factory=dict)
    continuity_history: list[dict] = field(default_factory=list)
    quality_report: dict = field(default_factory=dict)
    revised_chapter_drafts: list[dict] = field(default_factory=list)
    revised_chapter_1_draft: dict = field(default_factory=dict)
    story_summary: dict = field(default_factory=dict)
    project_quality_report: dict = field(default_factory=dict)
    publish_ready_bundle: dict = field(default_factory=dict)
    rerun_history: list[dict] = field(default_factory=list)
    revise_history: list[dict] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "story_input": self.story_input.to_dict(),
            "phases": [
                "story_input",
                "loglines",
                "characters",
                "three_act_plot",
                "story_bible",
                "chapter_plan",
                "chapter_drafts",
                "continuity_report",
                "quality_report",
                "revised_chapter_drafts",
                "story_summary",
                "project_quality_report",
                "publish_ready_bundle",
            ],
            "counts": {
                "loglines": len(self.loglines),
                "characters": len(self.characters),
                "chapters": len(self.chapter_plan),
                "chapter_drafts": len(self.chapter_drafts),
                "revised_chapter_drafts": len(self.revised_chapter_drafts),
            },
        }

    def normalize_chapter_artifacts(self) -> None:
        if self.chapter_drafts:
            self.chapter_1_draft = self.chapter_drafts[0]
        elif self.chapter_1_draft:
            self.set_chapter_draft(0, dict(self.chapter_1_draft))

        if self.revised_chapter_drafts:
            self.revised_chapter_1_draft = self.revised_chapter_drafts[0]
        elif self.revised_chapter_1_draft:
            self.set_revised_chapter_draft(0, dict(self.revised_chapter_1_draft))

        if self.continuity_history:
            self.continuity_report = self.continuity_history[0]
        elif self.continuity_report:
            self.continuity_history = [dict(self.continuity_report)]

    def artifact_contract(self) -> dict:
        return {
            "chapter_artifacts": chapter_artifact_contract(),
            "chapter_briefs": chapter_briefs_contract(),
            "scene_cards": scene_cards_contract(),
            "story_bible": story_bible_contract(),
            "publish_ready_bundle": publish_ready_bundle_contract(),
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
