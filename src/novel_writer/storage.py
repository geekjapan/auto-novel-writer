from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SUPPORTED_FORMATS = ("json", "yaml")


def ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


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
