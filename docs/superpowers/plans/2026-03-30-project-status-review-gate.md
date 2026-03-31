# Project Status Review Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `show-project-status` から、`manual` project の `stop_for_review` 由来 resume gate を確認できるようにする

**Architecture:** `project_manifest.json` に新しい保存値は追加せず、current run の `output_dir` から `next_action_decision.json` を読んで gate 状態を summary と lines に反映する。表示条件は既存の `resume-project` review gate と同じに揃え、status は read-only のまま保つ。

**Tech Stack:** Python, unittest, CLI, JSON artifact storage

---

### Task 1: Show Project Status に review gate 状態を追加する

**Files:**
- Modify: `/home/geekjapan/dev/auto-novel-writer/src/novel_writer/cli.py`
- Modify: `/home/geekjapan/dev/auto-novel-writer/tests/test_cli.py`
- Modify: `/home/geekjapan/dev/auto-novel-writer/README.md`
- Modify: `/home/geekjapan/dev/auto-novel-writer/docs/TASKS.md`

- [ ] **Step 1: status summary / lines の既存責務を確認する**

確認対象:

```text
/home/geekjapan/dev/auto-novel-writer/src/novel_writer/cli.py
- _enforce_resume_project_review_gate()
- build_project_status_summary()
- build_project_status_lines()
```

確認ポイント:

```text
- 既存の resume gate 条件が manual + stop_for_review で固定されていること
- status summary が current_run セクションを返していること
- status lines が summary を描画していること
```

- [ ] **Step 2: review gate 表示の failing test を追加する**

`/home/geekjapan/dev/auto-novel-writer/tests/test_cli.py` に、status 表示用の 3 ケースを追加する。

```python
    def test_build_project_status_lines_surfaces_manual_stop_for_review_gate(self) -> None:
        project_manifest = {
            "project_id": "Case 07",
            "project_slug": "case-07",
            "autonomy_level": "manual",
            "current_run": {
                "name": "latest_run",
                "output_dir": "data/projects/case-07/runs/latest_run",
                "current_step": "publish_ready_bundle",
                "comparison_metrics": {"completed_step_count": 1},
                "comparison_reason": [],
                "comparison_reason_details": [],
                "chapter_statuses": [],
                "long_run_status": {},
                "policy_snapshot": {},
            },
            "best_run": {},
            "run_candidates": [],
        }

        with patch(
            "novel_writer.cli.load_next_action_decision",
            return_value={"action": "stop_for_review"},
        ):
            lines = build_project_status_lines(project_manifest)

        self.assertIn("Resume gate: stop_for_review", lines)

    def test_build_project_status_lines_hides_gate_for_assist_projects(self) -> None:
        project_manifest = {
            "project_id": "Case 08",
            "project_slug": "case-08",
            "autonomy_level": "assist",
            "current_run": {
                "name": "latest_run",
                "output_dir": "data/projects/case-08/runs/latest_run",
                "current_step": "publish_ready_bundle",
                "comparison_metrics": {"completed_step_count": 1},
                "comparison_reason": [],
                "comparison_reason_details": [],
                "chapter_statuses": [],
                "long_run_status": {},
                "policy_snapshot": {},
            },
            "best_run": {},
            "run_candidates": [],
        }

        with patch(
            "novel_writer.cli.load_next_action_decision",
            return_value={"action": "stop_for_review"},
        ):
            lines = build_project_status_lines(project_manifest)

        self.assertNotIn("Resume gate: stop_for_review", lines)

    def test_build_project_status_lines_hides_gate_when_next_action_decision_is_missing(self) -> None:
        project_manifest = {
            "project_id": "Case 09",
            "project_slug": "case-09",
            "autonomy_level": "manual",
            "current_run": {
                "name": "latest_run",
                "output_dir": "data/projects/case-09/runs/latest_run",
                "current_step": "publish_ready_bundle",
                "comparison_metrics": {"completed_step_count": 1},
                "comparison_reason": [],
                "comparison_reason_details": [],
                "chapter_statuses": [],
                "long_run_status": {},
                "policy_snapshot": {},
            },
            "best_run": {},
            "run_candidates": [],
        }

        with patch(
            "novel_writer.cli.load_next_action_decision",
            side_effect=FileNotFoundError("missing next_action_decision"),
        ):
            lines = build_project_status_lines(project_manifest)

        self.assertNotIn("Resume gate: stop_for_review", lines)
```

- [ ] **Step 3: failing test を実行して失敗を確認する**

Run:

```bash
./venv/bin/python -m unittest \
  tests.test_cli.TestCLI.test_build_project_status_lines_surfaces_manual_stop_for_review_gate \
  tests.test_cli.TestCLI.test_build_project_status_lines_hides_gate_for_assist_projects \
  tests.test_cli.TestCLI.test_build_project_status_lines_hides_gate_when_next_action_decision_is_missing \
  -v
```

Expected:

```text
FAIL
AssertionError: 'Resume gate: stop_for_review' not found in ...
```

- [ ] **Step 4: status summary に review gate 要約を追加する**

`/home/geekjapan/dev/auto-novel-writer/src/novel_writer/cli.py` を最小変更で更新する。

```python
def _build_project_resume_gate_summary(project_manifest: dict[str, Any]) -> dict[str, Any] | None:
    if project_manifest.get("autonomy_level") != "manual":
        return None

    current_run = project_manifest.get("current_run", {})
    output_dir = current_run.get("output_dir")
    if not output_dir:
        return None

    try:
        next_action_decision = load_next_action_decision(Path(output_dir))
    except FileNotFoundError:
        return None

    if next_action_decision.get("action") != "stop_for_review":
        return None

    return {
        "status": "blocked",
        "reason": "stop_for_review",
    }
```

`build_project_status_summary()` では current run セクションに追加する。

```python
    resume_gate = _build_project_resume_gate_summary(project_manifest)

    if current_run:
        summary["current_run"] = {
            "name": current_run.get("name", "unknown"),
            "output_dir": current_run.get("output_dir", "unknown"),
            "current_step": current_run.get("current_step", "unknown"),
            "completed_steps": comparison_metrics.get("completed_step_count", "n/a"),
            "comparison_lines": _build_current_comparison_summary_lines(current_run, reason_detail_mode),
            "chapter_status_lines": _build_chapter_status_summary_lines(chapter_statuses),
            "long_run_status_lines": _build_long_run_status_lines(long_run_status),
            "resume_gate": resume_gate,
        }
```

`build_project_status_lines()` では gate 情報があるときだけ 1 行追加する。

```python
    current_run = summary.get("current_run")
    if current_run:
        resume_gate = current_run.get("resume_gate")
        if resume_gate:
            lines.append(f"Resume gate: {resume_gate['reason']}")
        lines.append(f"Current run: {current_run['name']}")
```

- [ ] **Step 5: 対象テストを再実行して通過を確認する**

Run:

```bash
./venv/bin/python -m unittest \
  tests.test_cli.TestCLI.test_build_project_status_lines_surfaces_manual_stop_for_review_gate \
  tests.test_cli.TestCLI.test_build_project_status_lines_hides_gate_for_assist_projects \
  tests.test_cli.TestCLI.test_build_project_status_lines_hides_gate_when_next_action_decision_is_missing \
  -v
```

Expected:

```text
OK
```

- [ ] **Step 6: README に status で gate が見えることを追記する**

`/home/geekjapan/dev/auto-novel-writer/README.md` の project status 説明を更新する。

追記例:

```md
`manual` project では、今回の run に保存された判定が「レビューしてから続けるべき」と示している場合、`resume-project` は自動再開せず停止します。
`show-project-status` では、その review gate が `stop_for_review` 由来で active かどうかも確認できます。
```

- [ ] **Step 7: タスク台帳を完了状態へ更新する**

`/home/geekjapan/dev/auto-novel-writer/docs/TASKS.md` を更新する。

更新内容:

```text
- M63h を Done へ移す
- Ready が空なら、docs/ROADMAP.md を根拠に次の最小子タスクを 1 件起票し、In Progress へ上げる
```

次タスク候補の方向:

```text
manual / assist / auto の control 差分を status 以外でも段階的に可視化・適用する最小子タスク
```

- [ ] **Step 8: 必須テストを実行する**

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

- [ ] **Step 9: コミットする**

Run:

```bash
git add /home/geekjapan/dev/auto-novel-writer/src/novel_writer/cli.py \
        /home/geekjapan/dev/auto-novel-writer/tests/test_cli.py \
        /home/geekjapan/dev/auto-novel-writer/README.md \
        /home/geekjapan/dev/auto-novel-writer/docs/TASKS.md
git commit -m "feat: show manual review gate in project status"
```

