# M63f Autonomy Level Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `project_manifest.json` に project-level `autonomy_level` contract を追加し、新規保存、互換読み込み、不正値 fail-fast、CLI 表示、docs 更新までを完了する。

**Architecture:** 既存の `project_manifest` 検証境界を保ち、`schema.py` で許容値を固定し、`storage.py` で欠損時の互換補完を担当する。`cli.py` は project 保存時に既定値 `assist` を書き込み、status 表示で現在値を可視化するが、pipeline の制御分岐は追加しない。

**Tech Stack:** Python 3, unittest, CLI, JSON artifact storage

---

### Task 1: Project Manifest Contract と Storage 互換読み込みを固定する

**Files:**
- Modify: `src/novel_writer/schema.py`
- Modify: `src/novel_writer/storage.py`
- Test: `tests/test_storage.py`

- [ ] **Step 1: storage 側の失敗系テストを先に追加する**

```python
def test_save_project_manifest_defaults_autonomy_level_to_assist(self) -> None:
    payload = {
        "project_id": "My Story 01",
        "project_slug": "my-story-01",
        "projects_dir": "data/projects",
        "current_run": {
            "name": "latest_run",
            "output_dir": "data/projects/my-story-01/runs/latest_run",
            "comparison_metrics": {},
            "comparison_basis": [],
            "comparison_reason": [],
            "comparison_reason_details": [],
        },
        "run_candidates": [],
        "best_run": {
            "run_name": "latest_run",
            "output_dir": "data/projects/my-story-01/runs/latest_run",
            "comparison_metrics": {},
            "comparison_basis": [],
            "selection_source": "automatic",
            "selection_reason": [],
            "selection_reason_details": [],
        },
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        target = save_project_manifest(Path(tmp_dir), "My Story 01", payload, "json")
        saved = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(saved["autonomy_level"], "assist")


def test_load_project_manifest_backfills_missing_autonomy_level(self) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_dir = Path(tmp_dir) / "case-01"
        save_artifact(
            project_dir,
            "project_manifest",
            {
                "schema_name": "project_manifest",
                "schema_version": "1.0",
                "project_id": "Case 01",
                "project_slug": "case-01",
                "projects_dir": str(Path(tmp_dir)),
                "current_run": {
                    "name": "latest_run",
                    "output_dir": str(project_dir / "runs" / "latest_run"),
                    "comparison_metrics": {},
                    "comparison_basis": [],
                    "comparison_reason": [],
                    "comparison_reason_details": [],
                },
                "run_candidates": [],
                "best_run": {
                    "run_name": "latest_run",
                    "output_dir": str(project_dir / "runs" / "latest_run"),
                    "comparison_metrics": {},
                    "comparison_basis": [],
                    "selection_source": "automatic",
                    "selection_reason": [],
                    "selection_reason_details": [],
                },
            },
            "json",
        )

        loaded = load_project_manifest(project_dir)
        self.assertEqual(loaded["autonomy_level"], "assist")


def test_load_project_manifest_rejects_unknown_autonomy_level(self) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_dir = Path(tmp_dir) / "case-01"
        save_artifact(
            project_dir,
            "project_manifest",
            {
                "schema_name": "project_manifest",
                "schema_version": "1.0",
                "project_id": "Case 01",
                "project_slug": "case-01",
                "projects_dir": str(Path(tmp_dir)),
                "autonomy_level": "fully_automatic",
                "current_run": {
                    "name": "latest_run",
                    "output_dir": str(project_dir / "runs" / "latest_run"),
                    "comparison_metrics": {},
                    "comparison_basis": [],
                    "comparison_reason": [],
                    "comparison_reason_details": [],
                },
                "run_candidates": [],
                "best_run": {
                    "run_name": "latest_run",
                    "output_dir": str(project_dir / "runs" / "latest_run"),
                    "comparison_metrics": {},
                    "comparison_basis": [],
                    "selection_source": "automatic",
                    "selection_reason": [],
                    "selection_reason_details": [],
                },
            },
            "json",
        )

        with self.assertRaisesRegex(ValueError, "autonomy_level must be one of: assist, auto, manual"):
            load_project_manifest(project_dir)
```

- [ ] **Step 2: 追加した storage テストだけを実行し、失敗内容を確認する**

Run: `pytest tests/test_storage.py -k "autonomy_level or project_manifest" -v`
Expected: `autonomy_level` 関連の新規テストが失敗し、既存 `project_manifest` テストは現状維持

- [ ] **Step 3: schema と storage に最小実装を追加する**

```python
def project_manifest_contract() -> dict:
    return {
        "schema_name": "project_manifest",
        "schema_version": "1.0",
        "required_fields": [
            "project_id",
            "project_slug",
            "projects_dir",
            "autonomy_level",
            "current_run",
            "run_candidates",
            "best_run",
        ],
        "allowed_autonomy_levels": ["manual", "assist", "auto"],
        ...
    }


def validate_project_manifest(payload: dict) -> dict:
    contract = project_manifest_contract()
    ...
    _validate_str_field(payload.get("autonomy_level"), "project_manifest", "autonomy_level")
    if payload.get("autonomy_level") not in contract["allowed_autonomy_levels"]:
        allowed = ", ".join(sorted(contract["allowed_autonomy_levels"]))
        raise ValueError(
            f"Invalid project_manifest: autonomy_level must be one of: {allowed}."
        )
    ...
    return payload
```

```python
def _normalize_project_manifest_autonomy_level(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    normalized.setdefault("autonomy_level", "assist")
    return normalized


def save_project_manifest(
    projects_dir: Path,
    project_id: str,
    payload: Any,
    file_format: str = "json",
) -> Path:
    ...
    manifest_payload = _normalize_project_manifest_autonomy_level(dict(payload))
    manifest_payload.setdefault("schema_name", contract["schema_name"])
    manifest_payload.setdefault("schema_version", contract["schema_version"])
    validate_project_manifest(manifest_payload)
    return save_artifact(project_layout["project_dir"], "project_manifest", manifest_payload, file_format)


def load_project_manifest(project_dir: Path, file_format: str | None = None) -> dict[str, Any]:
    payload = load_artifact(project_dir, "project_manifest", file_format)
    normalized = _normalize_project_manifest_autonomy_level(payload)
    validate_project_manifest(normalized)
    return normalized
```

- [ ] **Step 4: storage テストを再実行して通す**

Run: `pytest tests/test_storage.py -k "autonomy_level or project_manifest" -v`
Expected: PASS

- [ ] **Step 5: Task 1 を commit する**

```bash
git add src/novel_writer/schema.py src/novel_writer/storage.py tests/test_storage.py
git commit -m "feat: add project autonomy level contract"
```

### Task 2: CLI で autonomy level を保存し、status 表示へ出す

**Files:**
- Modify: `src/novel_writer/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: CLI の作成・表示テストを先に追加する**

```python
def test_create_project_persists_default_autonomy_level(self) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        exit_code = main(
            [
                "create-project",
                "--theme", "境界",
                "--genre", "SF",
                "--tone", "ビター",
                "--target-length", "5000",
                "--project-id", "My Story 01",
                "--projects-dir", tmp_dir,
            ]
        )

        project_manifest = load_artifact(Path(tmp_dir) / "my-story-01", "project_manifest")
        self.assertEqual(exit_code, 0)
        self.assertEqual(project_manifest["autonomy_level"], "assist")


def test_build_project_status_lines_includes_autonomy_level(self) -> None:
    project_manifest = {
        "project_id": "Case 01",
        "project_slug": "case-01",
        "projects_dir": "data/projects",
        "autonomy_level": "manual",
        "current_run": {
            "name": "latest_run",
            "output_dir": "data/projects/case-01/runs/latest_run",
            "current_step": "done",
            "comparison_metrics": {},
            "comparison_basis": [],
            "comparison_reason": [],
            "comparison_reason_details": [],
        },
        "run_candidates": [],
        "best_run": {
            "run_name": "latest_run",
            "output_dir": "data/projects/case-01/runs/latest_run",
            "score": 0,
            "comparison_metrics": {},
            "comparison_basis": [],
            "selection_source": "automatic",
            "selection_reason": [],
            "selection_reason_details": [],
        },
    }

    lines = build_project_status_lines(project_manifest)
    self.assertIn("Autonomy level: manual", lines)
```

- [ ] **Step 2: CLI テストを実行し、保存・表示の失敗を確認する**

Run: `pytest tests/test_cli.py -k "autonomy_level or project_status_lines" -v`
Expected: 新規テストが FAIL し、`autonomy_level` 未保存または未表示が原因になる

- [ ] **Step 3: save_project_state と status summary/lines を最小修正する**

```python
def save_project_state(...):
    ...
    save_project_manifest(
        projects_dir,
        project_id,
        {
            "project_id": project_layout["project_id"],
            "project_slug": project_layout["project_slug"],
            "projects_dir": str(projects_dir),
            "autonomy_level": existing_project_manifest.get("autonomy_level", "assist"),
            "current_run": {...},
            "run_candidates": run_candidates,
            "best_run": best_run,
        },
        file_format,
    )
```

```python
def build_project_status_summary(project_manifest: dict[str, Any], reason_detail_mode: str = "summary") -> dict[str, Any]:
    ...
    summary: dict[str, Any] = {
        "project_label": project_manifest.get("project_slug") or project_manifest.get("project_id", "unknown"),
        "autonomy_level": project_manifest.get("autonomy_level", "assist"),
        "run_candidate_count": len(project_manifest.get("run_candidates", [])),
    }
    ...


def build_project_status_lines(project_manifest: dict[str, Any], reason_detail_mode: str = "summary") -> list[str]:
    ...
    lines.append(f"Autonomy level: {summary['autonomy_level']}")
    ...
```

- [ ] **Step 4: CLI テストを再実行して通す**

Run: `pytest tests/test_cli.py -k "autonomy_level or project_status_lines" -v`
Expected: PASS

- [ ] **Step 5: Task 2 を commit する**

```bash
git add src/novel_writer/cli.py tests/test_cli.py
git commit -m "feat: surface project autonomy level in cli"
```

### Task 3: docs と task queue を同期し、回帰確認を行う

**Files:**
- Modify: `README.md`
- Modify: `docs/ROADMAP.md`
- Modify: `docs/TASKS.md`
- Modify: `docs/DEVELOPMENT_GUIDE.md`

- [ ] **Step 1: docs 更新の先に必要な回帰確認コマンドを固定する**

Run: `pytest tests/test_storage.py tests/test_cli.py -k "project_manifest or autonomy_level or project_status" -v`
Expected: Task 1 と Task 2 で追加したケースを含めて PASS

- [ ] **Step 2: README と docs を更新する**

```md
# README.md
- `project_manifest.json` には project 単位の `autonomy_level` (`manual` / `assist` / `auto`) を保存します。
- 現在は contract 固定まで完了しており、実際の制御分岐は次段階で追加します。
```

```md
# docs/ROADMAP.md
- M63: `autonomy_level` contract の project 保存と表示は完了
- 次の子タスク: `manual` / `assist` / `auto` を制御分岐へ結び付ける
```

```md
# docs/TASKS.md
- `M63f` を Done へ移動する
- 次の最小子タスクを `Ready` または `In Progress` に 1 件だけ起票する
```

```md
# docs/DEVELOPMENT_GUIDE.md
- autonomy policy は、まず contract を固定し、その後に制御分岐を追加する
```

- [ ] **Step 3: docs と対象テストをまとめて確認する**

Run: `pytest tests/test_storage.py tests/test_cli.py -k "project_manifest or autonomy_level or project_status" -v`
Expected: PASS

Run: `git diff --check`
Expected: no output

- [ ] **Step 4: Task 3 を commit する**

```bash
git add README.md docs/ROADMAP.md docs/TASKS.md docs/DEVELOPMENT_GUIDE.md
git commit -m "docs: update autonomy level roadmap status"
```

## Self-Review

- Spec coverage:
  - `project_manifest.json` への `autonomy_level` 追加は Task 1 で実装する
  - 既定値 `assist` の保存は Task 1 と Task 2 で実装する
  - 既存 manifest の互換読み込みは Task 1 で実装する
  - 不正値 fail-fast は Task 1 で実装する
  - CLI status 表示は Task 2 で実装する
  - docs 更新は Task 3 で実装する
- Placeholder scan:
  - `TODO`、`TBD`、曖昧な「適切に対応する」は残していない
- Type consistency:
  - 追加する key 名はすべて `autonomy_level` で統一した
  - 許容値はすべて `manual` / `assist` / `auto` で統一した
