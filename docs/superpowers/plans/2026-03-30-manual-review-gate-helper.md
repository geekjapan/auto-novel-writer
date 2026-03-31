# Manual Review Gate Helper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `resume-project` と `show-project-status` の manual review gate 判定を 1 helper に共通化する

**Architecture:** `cli.py` に review gate 判定専用の小さい helper を追加し、resume 側と status 側はその helper の戻り値だけを見るように整理する。user-facing behavior は変えず、既存テストで manual / assist / decision 欠損の条件を固定したまま refactor を閉じる。

**Tech Stack:** Python, unittest, CLI, JSON artifact storage

---

### Task 1: manual review gate 判定を helper に共通化する

**Files:**
- Modify: `/home/geekjapan/dev/auto-novel-writer/src/novel_writer/cli.py`
- Modify: `/home/geekjapan/dev/auto-novel-writer/tests/test_cli.py`
- Modify: `/home/geekjapan/dev/auto-novel-writer/docs/TASKS.md`

- [ ] **Step 1: 既存の重複判定と関連テストを確認する**

確認対象:

```text
/home/geekjapan/dev/auto-novel-writer/src/novel_writer/cli.py
- _enforce_resume_project_review_gate()
- _build_project_resume_gate_summary() または同等の status 用 helper

/home/geekjapan/dev/auto-novel-writer/tests/test_cli.py
- resume-project の manual / assist / missing decision テスト
- show-project-status の manual stop_for_review / assist / missing / non-blocking action テスト
```

確認ポイント:

```text
- 両側が manual + stop_for_review を別々に判定していること
- README ではなく tests を behavior の正本として扱うこと
- 今回の task では README 更新が不要なこと
```

- [ ] **Step 2: helper 共通化後も branch が守られる failing test を追加または整理する**

`/home/geekjapan/dev/auto-novel-writer/tests/test_cli.py` に、helper 共通化後も resume と status の両方が同じ条件で動くことを示す最小テストを用意する。

追加候補:

```python
    def test_build_manual_review_gate_returns_reason_for_manual_stop_for_review(self) -> None:
        project_manifest = {"autonomy_level": "manual"}

        with patch(
            "novel_writer.cli.load_next_action_decision",
            return_value={"action": "stop_for_review"},
        ):
            gate = _build_manual_review_gate(project_manifest, Path("runs/latest_run"))

        self.assertEqual(gate, {"reason": "stop_for_review"})

    def test_build_manual_review_gate_returns_none_for_assist_project(self) -> None:
        project_manifest = {"autonomy_level": "assist"}

        gate = _build_manual_review_gate(project_manifest, Path("runs/latest_run"))

        self.assertIsNone(gate)

    def test_build_manual_review_gate_returns_none_when_decision_is_missing(self) -> None:
        project_manifest = {"autonomy_level": "manual"}

        with patch(
            "novel_writer.cli.load_next_action_decision",
            side_effect=FileNotFoundError("missing next_action_decision"),
        ):
            gate = _build_manual_review_gate(project_manifest, Path("runs/latest_run"))

        self.assertIsNone(gate)
```

既存テストとの重複が強すぎる場合は、新規 helper テストを 1-2 本に絞ってもよい。
ただし、manual / assist / missing decision の branch が helper 単位で読めるようにする。

- [ ] **Step 3: 対象テストを実行して失敗を確認する**

Run:

```bash
./venv/bin/python -m unittest \
  tests.test_cli.TestCLI.test_build_manual_review_gate_returns_reason_for_manual_stop_for_review \
  tests.test_cli.TestCLI.test_build_manual_review_gate_returns_none_for_assist_project \
  tests.test_cli.TestCLI.test_build_manual_review_gate_returns_none_when_decision_is_missing \
  -v
```

Expected:

```text
ERROR
ImportError or AttributeError for _build_manual_review_gate
```

- [ ] **Step 4: `cli.py` に共通 helper を追加して、resume と status を置き換える**

`/home/geekjapan/dev/auto-novel-writer/src/novel_writer/cli.py` に小さい helper を追加する。

```python
def _build_manual_review_gate(project_manifest: dict[str, Any], output_dir: Path) -> dict[str, Any] | None:
    if project_manifest.get("autonomy_level") != "manual":
        return None

    try:
        next_action_decision = load_next_action_decision(output_dir)
    except FileNotFoundError:
        return None

    if next_action_decision.get("action") != "stop_for_review":
        return None

    return {"reason": "stop_for_review"}
```

`_enforce_resume_project_review_gate()` は helper を使うように置き換える。

```python
def _enforce_resume_project_review_gate(project_manifest: dict[str, Any], output_dir: Path) -> None:
    review_gate = _build_manual_review_gate(project_manifest, output_dir)
    if review_gate is None:
        return

    raise ValueError(
        "resume-project is blocked for manual projects when next_action_decision.action is stop_for_review."
    )
```

status 側の helper / summary も、同じ `_build_manual_review_gate()` を使うように整理する。

```python
def _build_project_resume_gate_summary(project_manifest: dict[str, Any]) -> dict[str, Any] | None:
    current_run = project_manifest.get("current_run", {})
    output_dir = current_run.get("output_dir")
    if not output_dir:
        return None

    return _build_manual_review_gate(project_manifest, Path(output_dir))
```

- [ ] **Step 5: helper テストと既存の関連テストを実行して通過を確認する**

Run:

```bash
./venv/bin/python -m unittest \
  tests.test_cli.TestCLI.test_build_manual_review_gate_returns_reason_for_manual_stop_for_review \
  tests.test_cli.TestCLI.test_build_manual_review_gate_returns_none_for_assist_project \
  tests.test_cli.TestCLI.test_build_manual_review_gate_returns_none_when_decision_is_missing \
  tests.test_cli.TestCLI.test_cli_resume_project_blocks_manual_stop_for_review_before_pipeline \
  tests.test_cli.TestCLI.test_cli_resume_project_allows_missing_next_action_decision \
  tests.test_cli.TestCLI.test_cli_resume_project_allows_assist_stop_for_review \
  tests.test_cli.TestCLI.test_build_project_status_lines_surfaces_manual_stop_for_review_gate \
  tests.test_cli.TestCLI.test_build_project_status_lines_hides_gate_for_manual_non_blocking_next_action \
  tests.test_cli.TestCLI.test_build_project_status_lines_hides_gate_for_assist_projects \
  tests.test_cli.TestCLI.test_build_project_status_lines_hides_gate_when_next_action_decision_is_missing \
  -v
```

Expected:

```text
OK
```

- [ ] **Step 6: タスク台帳を更新する**

`/home/geekjapan/dev/auto-novel-writer/docs/TASKS.md` を更新する。

更新内容:

```text
- M63i を Done へ移す
- Ready が空なら、M63 の次の最小子タスクを 1 件起票し、In Progress に上げる
```

次タスク候補の方向:

```text
manual / assist / auto の差分を次にどの public control へつなぐかを、1 gate 単位で追加する小タスク
```

- [ ] **Step 7: 必須テストを実行する**

Run:

```bash
./venv/bin/python -m unittest tests.test_cli -v
./venv/bin/python -m unittest discover -s tests -v
git diff --check
```

Expected:

```text
- tests.test_cli が OK
- discover が OK
- git diff --check が無出力
```

- [ ] **Step 8: コミットする**

Run:

```bash
git add /home/geekjapan/dev/auto-novel-writer/src/novel_writer/cli.py \
        /home/geekjapan/dev/auto-novel-writer/tests/test_cli.py \
        /home/geekjapan/dev/auto-novel-writer/docs/TASKS.md
git commit -m "refactor: share manual review gate helper"
```

