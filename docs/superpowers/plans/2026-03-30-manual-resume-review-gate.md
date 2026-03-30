# M63g Manual Resume Review Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `manual` project が `stop_for_review` の `next_action_decision` を持つ run を `resume-project` で自動再開しない review gate を追加する。

**Architecture:** `resume-project` の CLI 入口でだけ gate を追加し、project manifest と current run の `next_action_decision` を読んで停止条件を判定する。pipeline 本体の責務は広げず、storage の既存 load 関数を再利用する。

**Tech Stack:** Python 3, unittest, CLI, JSON artifact storage

---

### Task 1: `resume-project` の manual review gate を実装する

**Files:**
- Modify: `src/novel_writer/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: CLI の失敗系・継続系テストを先に追加する**

```python
def test_resume_project_stops_for_manual_project_with_stop_for_review_decision(self) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        main(
            [
                "create-project",
                "--theme", "境界",
                "--genre", "SF",
                "--tone", "ビター",
                "--target-length", "5000",
                "--project-id", "Case 07",
                "--projects-dir", tmp_dir,
            ]
        )

        project_dir = Path(tmp_dir) / "case-07"
        run_dir = project_dir / "runs" / "latest_run"
        project_manifest = load_artifact(project_dir, "project_manifest")
        project_manifest["autonomy_level"] = "manual"
        (project_dir / "project_manifest.json").write_text(
            json.dumps(project_manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        save_artifact(
            run_dir,
            "next_action_decision",
            {
                "schema_name": "next_action_decision",
                "schema_version": "1.0",
                "evaluated_through_chapter": 3,
                "action": "stop_for_review",
                "reason": "human review required",
                "issue_codes": ["human_review_required"],
                "target_chapters": [],
                "policy_budget": {
                    "max_high_severity_chapters": 10,
                    "max_total_rerun_attempts": 20,
                    "remaining_high_severity_chapter_budget": 10,
                    "remaining_rerun_attempt_budget": 20,
                },
                "decision_trace": [{"code": "manual_gate", "summary": "stop", "value": "critical"}],
            },
            "json",
        )

        with self.assertRaisesRegex(ValueError, "resume-project.*manual.*stop_for_review"):
            main(
                [
                    "resume-project",
                    "--project-id", "Case 07",
                    "--projects-dir", tmp_dir,
                ]
            )
```

```python
def test_resume_project_allows_assist_project_with_stop_for_review_decision(self) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        create_exit_code = main(
            [
                "create-project",
                "--theme", "境界",
                "--genre", "SF",
                "--tone", "ビター",
                "--target-length", "5000",
                "--project-id", "Case 08",
                "--projects-dir", tmp_dir,
            ]
        )

        project_dir = Path(tmp_dir) / "case-08"
        run_dir = project_dir / "runs" / "latest_run"
        save_artifact(
            run_dir,
            "next_action_decision",
            {
                "schema_name": "next_action_decision",
                "schema_version": "1.0",
                "evaluated_through_chapter": 3,
                "action": "stop_for_review",
                "reason": "human review required",
                "issue_codes": ["human_review_required"],
                "target_chapters": [],
                "policy_budget": {
                    "max_high_severity_chapters": 10,
                    "max_total_rerun_attempts": 20,
                    "remaining_high_severity_chapter_budget": 10,
                    "remaining_rerun_attempt_budget": 20,
                },
                "decision_trace": [{"code": "manual_gate", "summary": "stop", "value": "critical"}],
            },
            "json",
        )

        resume_exit_code = main(
            [
                "resume-project",
                "--project-id", "Case 08",
                "--projects-dir", tmp_dir,
            ]
        )

        self.assertEqual(create_exit_code, 0)
        self.assertEqual(resume_exit_code, 0)
```

```python
def test_resume_project_allows_manual_project_without_next_action_decision(self) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        main(
            [
                "create-project",
                "--theme", "境界",
                "--genre", "SF",
                "--tone", "ビター",
                "--target-length", "5000",
                "--project-id", "Case 09",
                "--projects-dir", tmp_dir,
            ]
        )

        project_dir = Path(tmp_dir) / "case-09"
        project_manifest = load_artifact(project_dir, "project_manifest")
        project_manifest["autonomy_level"] = "manual"
        (project_dir / "project_manifest.json").write_text(
            json.dumps(project_manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (project_dir / "runs" / "latest_run" / "next_action_decision.json").unlink(missing_ok=True)

        resume_exit_code = main(
            [
                "resume-project",
                "--project-id", "Case 09",
                "--projects-dir", tmp_dir,
            ]
        )

        self.assertEqual(resume_exit_code, 0)
```

- [ ] **Step 2: 追加した CLI テストだけを実行し、失敗内容を確認する**

Run: `./venv/bin/python -m unittest tests.test_cli.CliTest.test_resume_project_stops_for_manual_project_with_stop_for_review_decision tests.test_cli.CliTest.test_resume_project_allows_assist_project_with_stop_for_review_decision tests.test_cli.CliTest.test_resume_project_allows_manual_project_without_next_action_decision -v`
Expected: manual 停止ケースが未実装で FAIL する

- [ ] **Step 3: `resume-project` の前に gate を追加する**

```python
def _enforce_manual_resume_review_gate(project_dir: Path) -> None:
    project_manifest = load_project_manifest(project_dir)
    if project_manifest.get("autonomy_level") != "manual":
        return

    current_run = project_manifest.get("current_run", {})
    output_dir = current_run.get("output_dir")
    if not output_dir:
        return

    try:
        next_action_decision = load_next_action_decision(Path(output_dir))
    except FileNotFoundError:
        return

    if next_action_decision.get("action") == "stop_for_review":
        raise ValueError(
            "resume-project is blocked for manual project because next_action_decision.action=stop_for_review."
        )
```

```python
if args.command == "resume-project":
    project_layout, output_dir = load_project_run_context(Path(args.projects_dir), args.project_id)
    _enforce_manual_resume_review_gate(project_layout["project_dir"])
    artifacts = run_pipeline(args, output_dir, resume_from=output_dir, rerun_from=args.rerun_from)
    ...
```

- [ ] **Step 4: 対象 CLI テストを再実行して通す**

Run: `./venv/bin/python -m unittest tests.test_cli.CliTest.test_resume_project_stops_for_manual_project_with_stop_for_review_decision tests.test_cli.CliTest.test_resume_project_allows_assist_project_with_stop_for_review_decision tests.test_cli.CliTest.test_resume_project_allows_manual_project_without_next_action_decision -v`
Expected: PASS

- [ ] **Step 5: CLI テスト全体を確認して Task 1 を commit する**

Run: `./venv/bin/python -m unittest tests.test_cli -v`
Expected: PASS

```bash
git add src/novel_writer/cli.py tests/test_cli.py
git commit -m "feat: gate manual resume on review decision"
```

### Task 2: README と task queue を同期する

**Files:**
- Modify: `README.md`
- Modify: `docs/TASKS.md`

- [ ] **Step 1: README と task queue の更新文面を追加する**

```md
# README.md
- `manual` project は、current run の `next_action_decision.action` が `stop_for_review` の場合、`resume-project` を自動再開しない
```

```md
# docs/TASKS.md
- `M63g` を Done へ移す
- 次の最小子タスクを 1 件だけ `In Progress` に上げる
```

- [ ] **Step 2: docs と diff 整合を確認する**

Run: `git diff --check`
Expected: no output

- [ ] **Step 3: Task 2 を commit する**

```bash
git add README.md docs/TASKS.md
git commit -m "docs: sync manual resume review gate"
```

## Self-Review

- Spec coverage:
  - `manual + stop_for_review` 停止は Task 1 で実装する
  - `assist` と `decision なし` の継続は Task 1 の CLI tests で確認する
  - README と `docs/TASKS.md` の同期は Task 2 で行う
- Placeholder scan:
  - `TODO`、`TBD`、曖昧な「適切に対応する」は残していない
- Type consistency:
  - 条件名はすべて `autonomy_level` と `next_action_decision.action` で統一した
  - 停止対象はすべて `stop_for_review` に限定した
