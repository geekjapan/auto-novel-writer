from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from novel_writer.schema import project_manifest_contract, validate_project_manifest


SUPPORTED_FORMATS = ("json", "yaml")
DEFAULT_PROJECT_RUN_NAME = "latest_run"


def ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def normalize_project_id(project_id: str) -> str:
    normalized = re.sub(r"[^a-z0-9_-]+", "-", project_id.strip().lower()).strip("-_")
    if not normalized:
        raise ValueError("project_id must contain at least one alphanumeric character.")
    return normalized


def build_project_layout(
    projects_dir: Path,
    project_id: str,
    run_name: str = DEFAULT_PROJECT_RUN_NAME,
) -> dict[str, Any]:
    project_slug = normalize_project_id(project_id)
    project_dir = projects_dir / project_slug
    return {
        "project_id": project_id,
        "project_slug": project_slug,
        "project_dir": project_dir,
        "run_dir": project_dir / "runs" / run_name,
        "run_name": run_name,
        "project_manifest_path": project_dir / "project_manifest.json",
    }


def resolve_artifact_path(output_dir: Path, phase_name: str, file_format: str | None = None) -> Path:
    formats = (file_format.lower(),) if file_format else SUPPORTED_FORMATS
    for candidate_format in formats:
        candidate = output_dir / f"{phase_name}.{candidate_format}"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Artifact not found for phase '{phase_name}' in {output_dir}")


def save_artifact(output_dir: Path, phase_name: str, payload: Any, file_format: str = "json") -> Path:
    ensure_output_dir(output_dir)
    normalized = file_format.lower()
    target = output_dir / f"{phase_name}.{normalized}"

    if normalized == "json":
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return target

    if normalized == "yaml":
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError("YAML output requires PyYAML. Install it or use --format json.") from exc

        target.write_text(
            yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return target

    raise ValueError(f"Unsupported format: {file_format}")


def save_project_manifest(
    projects_dir: Path,
    project_id: str,
    payload: Any,
    file_format: str = "json",
) -> Path:
    project_layout = build_project_layout(projects_dir, project_id)
    contract = project_manifest_contract()
    manifest_payload = dict(payload)
    manifest_payload.setdefault("schema_name", contract["schema_name"])
    manifest_payload.setdefault("schema_version", contract["schema_version"])
    validate_project_manifest(manifest_payload)
    return save_artifact(project_layout["project_dir"], "project_manifest", manifest_payload, file_format)


def load_project_manifest(project_dir: Path, file_format: str | None = None) -> dict[str, Any]:
    payload = load_artifact(project_dir, "project_manifest", file_format)
    validate_project_manifest(payload)
    return payload


def load_artifact(output_dir: Path, phase_name: str, file_format: str | None = None) -> Any:
    target = resolve_artifact_path(output_dir, phase_name, file_format)
    normalized = target.suffix.lstrip(".").lower()
    content = target.read_text(encoding="utf-8")

    if normalized == "json":
        return json.loads(content)

    if normalized == "yaml":
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError("YAML input requires PyYAML. Install it or use JSON artifacts.") from exc

        return yaml.safe_load(content)

    raise ValueError(f"Unsupported format: {normalized}")
