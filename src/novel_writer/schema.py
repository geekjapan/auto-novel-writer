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
    }


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

    return payload


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
