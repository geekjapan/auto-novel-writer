from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


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

