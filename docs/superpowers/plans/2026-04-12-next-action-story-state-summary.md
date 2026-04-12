# Next-Action Story-State Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `next_action_decision` と `replan_history` に shared `story_state_summary` を保存し、`show-project-status` が同じ snapshot を read-only に表示できるようにする

**Architecture:** `src/novel_writer/schema.py` にある shared `story_state_summary` validator をそのまま再利用し、`src/novel_writer/pipeline.py` は `progress_report` から snapshot を受け渡すだけに留める。`src/novel_writer/cli.py` は保存済み `next_action_decision` を読んで短い status line を 1 本追加するだけにして、state の再計算や暗黙 fallback は増やさない。

**Tech Stack:** Python, pytest, unittest-style tests, JSON artifact storage, CLI

---

## File Structure

- Modify: `/Users/geekjapan/dev/auto-novel-writer/src/novel_writer/schema.py`
  - `next_action_decision` と `replan_history` entry の contract に `story_state_summary` を追加し、既存の `_validate_story_state_summary()` で fail-fast に検証する
- Modify: `/Users/geekjapan/dev/auto-novel-writer/src/novel_writer/pipeline.py`
  - `progress_report.story_state_summary` を `next_action_decision` と `replan_history` entry に snapshot として保存する
- Modify: `/Users/geekjapan/dev/auto-novel-writer/src/novel_writer/cli.py`
  - 保存済み `next_action_decision.story_state_summary` を `show-project-status` の line として表示する
- Modify: `/Users/geekjapan/dev/auto-novel-writer/tests/test_storage.py`
  - validator が `story_state_summary` 欠落を reject することを確認する
- Modify: `/Users/geekjapan/dev/auto-novel-writer/tests/test_pipeline.py`
  - pipeline 実行後に `next_action_decision` と `replan_history` へ同じ summary snapshot が保存されることを確認する
- Modify: `/Users/geekjapan/dev/auto-novel-writer/tests/test_cli.py`
  - `show-project-status` が保存済み `story_state_summary` を表示することと、既存の missing path を壊さないことを確認する
- Modify: `/Users/geekjapan/dev/auto-novel-writer/README.md`
  - `show-project-status` から保存済み story-state snapshot を見られることを最小限で同期する
- Modify: `/Users/geekjapan/dev/auto-novel-writer/docs/TASKS.md`
  - `M66a` を `In Progress` に上げ、完了後に `Done` へ移す

## Shared Implementation Notes

- `story_state_summary` の field 名は既存 contract をそのまま使う
- 新しい summary helper は追加しない
- `next_action_decision` と `replan_history` 側で state を再計算しない
- `show-project-status` は保存済み `next_action_decision` を読むだけにする
- `show-run-comparison` には今回は新 line を追加しない
- テスト実行は `PYTHONPATH=src python -m pytest <target> -q` の形で行う
- 各 task の最後に小さくコミットする

### Task 1: Start M66a And Lock The Decision Artifact Contract

**Files:**
- Modify: `/Users/geekjapan/dev/auto-novel-writer/docs/TASKS.md`
- Modify: `/Users/geekjapan/dev/auto-novel-writer/src/novel_writer/schema.py`
- Modify: `/Users/geekjapan/dev/auto-novel-writer/tests/test_storage.py`

- [ ] **Step 1: Mark `M66a` as the current task in `docs/TASKS.md`**

Replace the empty queue head with:

```markdown
## In Progress

- [ ] M66a: carry shared story_state_summary into next_action_decision and replan history

## Ready
```

- [ ] **Step 2: Write failing storage tests for the new required field**

In `/Users/geekjapan/dev/auto-novel-writer/tests/test_storage.py`, update the round-trip payloads so they already match the post-change contract, and add explicit missing-field tests.

Update `test_save_next_action_decision_round_trips_valid_payload()` to include:

```python
            "story_state_summary": {
                "evaluated_through_chapter": 5,
                "canon_chapter_count": 5,
                "thread_count": 4,
                "unresolved_thread_count": 2,
                "resolved_thread_count": 1,
                "open_question_count": 3,
                "latest_timeline_event_count": 1,
            },
```

Add a new test near the existing next-action validation tests:

```python
    def test_save_next_action_decision_requires_story_state_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(
                ValueError,
                "Invalid next_action_decision: missing required fields: story_state_summary",
            ):
                save_next_action_decision(
                    Path(tmp_dir),
                    {
                        "schema_name": "next_action_decision",
                        "schema_version": "1.0",
                        "evaluated_through_chapter": 5,
                        "action": "replan_future",
                        "reason": "中盤停滞のため future chapter を再計画する",
                        "issue_codes": ["escalation_pace_flat"],
                        "target_chapters": [6, 7, 8],
                        "policy_budget": {
                            "max_high_severity_chapters": 10,
                            "max_total_rerun_attempts": 20,
                            "remaining_high_severity_chapter_budget": 7,
                            "remaining_rerun_attempt_budget": 14,
                        },
                        "decision_trace": [
                            {
                                "code": "escalation_pace_flat",
                                "summary": "中盤の伸びが止まっている",
                                "value": "chapter-5",
                            }
                        ],
                    },
                )
```

Update `test_save_replan_history_round_trips_valid_payload()` so its entry includes:

```python
                    "story_state_summary": {
                        "evaluated_through_chapter": 5,
                        "canon_chapter_count": 5,
                        "thread_count": 4,
                        "unresolved_thread_count": 2,
                        "resolved_thread_count": 1,
                        "open_question_count": 3,
                        "latest_timeline_event_count": 1,
                    },
```

Add a new test near the existing replan history validation tests:

```python
    def test_load_replan_history_rejects_missing_story_state_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_artifact(
                Path(tmp_dir),
                "replan_history",
                {
                    "schema_name": "replan_history",
                    "schema_version": "1.0",
                    "replans": [
                        {
                            "replan_id": "replan-001",
                            "trigger_chapter_number": 5,
                            "reason": "理由",
                            "issue_codes": ["code-1"],
                            "impact_scope": {
                                "from_chapter": 6,
                                "to_chapter": 7,
                                "chapter_numbers": [6, 7],
                            },
                            "updated_artifacts": ["chapter_briefs"],
                            "change_summary": ["差分"],
                        }
                    ],
                },
            )

            with self.assertRaisesRegex(
                ValueError,
                "Invalid replan_history: replans\\[0\\] is missing required fields: story_state_summary",
            ):
                load_replan_history(Path(tmp_dir))
```

- [ ] **Step 3: Run the targeted storage tests to verify they fail**

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_storage.py::SaveArtifactTest::test_save_next_action_decision_requires_story_state_summary \
  tests/test_storage.py::SaveArtifactTest::test_load_replan_history_rejects_missing_story_state_summary \
  -q
```

Expected:

```text
2 failed
```

- [ ] **Step 4: Implement the minimal schema changes in `schema.py`**

In `/Users/geekjapan/dev/auto-novel-writer/src/novel_writer/schema.py`, add `story_state_summary` to the contract required fields and validate it with the existing shared validator.

Update `next_action_decision_contract()` to:

```python
def next_action_decision_contract() -> dict:
    return {
        "schema_name": "next_action_decision",
        "schema_version": "1.0",
        "required_fields": [
            "schema_name",
            "schema_version",
            "evaluated_through_chapter",
            "action",
            "reason",
            "issue_codes",
            "target_chapters",
            "policy_budget",
            "decision_trace",
            "story_state_summary",
        ],
        "allowed_actions": [
            "continue",
            "revise",
            "rerun_chapter",
            "replan_future",
            "stop_for_review",
        ],
        "policy_budget_required_fields": [
            "max_high_severity_chapters",
            "max_total_rerun_attempts",
            "remaining_high_severity_chapter_budget",
            "remaining_rerun_attempt_budget",
        ],
        "decision_trace_required_fields": [
            "code",
            "summary",
            "value",
        ],
        "target_chapter_rules": {
            "continue": "empty",
            "revise": "single",
            "rerun_chapter": "single",
            "replan_future": "non_empty",
            "stop_for_review": "empty",
        },
    }
```

In `validate_next_action_decision()`, add:

```python
    _validate_story_state_summary(
        payload.get("story_state_summary"),
        "next_action_decision",
        "story_state_summary",
    )

    return payload
```

Update `replan_history_contract()` to:

```python
def replan_history_contract() -> dict:
    return {
        "schema_name": "replan_history",
        "schema_version": "1.0",
        "required_fields": [
            "schema_name",
            "schema_version",
            "replans",
        ],
        "replan_required_fields": [
            "replan_id",
            "trigger_chapter_number",
            "reason",
            "issue_codes",
            "impact_scope",
            "updated_artifacts",
            "change_summary",
            "story_state_summary",
        ],
        "impact_scope_required_fields": [
            "from_chapter",
            "to_chapter",
            "chapter_numbers",
        ],
    }
```

In `validate_replan_entry()`, add:

```python
    _validate_story_state_summary(
        payload.get("story_state_summary"),
        "replan_history",
        f"{field_name}.story_state_summary",
    )

    impact_scope = payload.get("impact_scope")
```

- [ ] **Step 5: Run the storage tests to verify the contract is locked**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_storage.py -q -k "next_action_decision or replan_history"
```

Expected:

```text
<N> passed
```

There should be `0 failed`.

- [ ] **Step 6: Commit the contract work**

```bash
git add docs/TASKS.md src/novel_writer/schema.py tests/test_storage.py
git commit -m "feat: validate story state summary in decision artifacts"
```

### Task 2: Save The Snapshot Into Pipeline Decisions

**Files:**
- Modify: `/Users/geekjapan/dev/auto-novel-writer/src/novel_writer/pipeline.py`
- Modify: `/Users/geekjapan/dev/auto-novel-writer/tests/test_pipeline.py`

- [ ] **Step 1: Write failing pipeline assertions for saved snapshots**

In `/Users/geekjapan/dev/auto-novel-writer/tests/test_pipeline.py`, extend `test_pipeline_saves_next_action_decision_after_progress_report()`:

```python
            progress_report = load_progress_report(output_dir)
            next_action_decision = load_next_action_decision(output_dir)

            self.assertEqual(
                next_action_decision["story_state_summary"],
                progress_report["story_state_summary"],
            )
```

In `test_pipeline_records_replan_history_when_progress_report_recommends_replan()`, add:

```python
            progress_report = load_progress_report(output_dir)
            replan_history = load_replan_history(output_dir)

            self.assertEqual(
                replan_history["replans"][0]["story_state_summary"],
                progress_report["story_state_summary"],
            )
```

In `test_pipeline_maps_replan_recommended_action_to_replan_future_decision()`, add:

```python
            progress_report = load_progress_report(output_dir)
            next_action_decision = load_next_action_decision(output_dir)

            self.assertEqual(
                next_action_decision["story_state_summary"],
                progress_report["story_state_summary"],
            )
```

- [ ] **Step 2: Run the targeted pipeline tests to verify they fail**

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_pipeline.py::StoryPipelineTest::test_pipeline_saves_next_action_decision_after_progress_report \
  tests/test_pipeline.py::StoryPipelineTest::test_pipeline_records_replan_history_when_progress_report_recommends_replan \
  tests/test_pipeline.py::StoryPipelineTest::test_pipeline_maps_replan_recommended_action_to_replan_future_decision \
  -q
```

Expected:

```text
3 failed
```

- [ ] **Step 3: Write the minimal pipeline implementation**

In `/Users/geekjapan/dev/auto-novel-writer/src/novel_writer/pipeline.py`, copy the already-built snapshot from `progress_report`.

Update `_build_next_action_decision()` to return:

```python
        return {
            "schema_name": "next_action_decision",
            "schema_version": "1.0",
            "evaluated_through_chapter": int(progress_report.get("evaluated_through_chapter", 0)),
            "action": action,
            "reason": reason,
            "issue_codes": list(progress_report.get("issue_codes", [])),
            "target_chapters": target_chapters,
            "policy_budget": {
                "max_high_severity_chapters": int(self.long_run_status.get("max_high_severity_chapters", 0)),
                "max_total_rerun_attempts": int(self.long_run_status.get("max_total_rerun_attempts", 0)),
                "remaining_high_severity_chapter_budget": int(
                    self.long_run_status.get("remaining_high_severity_chapter_budget", 0)
                ),
                "remaining_rerun_attempt_budget": int(
                    self.long_run_status.get("remaining_rerun_attempt_budget", 0)
                ),
            },
            "decision_trace": self._build_next_action_decision_trace(progress_report),
            "story_state_summary": dict(progress_report.get("story_state_summary", {})),
        }
```

Update `_build_replan_payload()` to return:

```python
        return {
            "replan_id": f"replan-after-chapter-{trigger_chapter_number}",
            "trigger_chapter_number": trigger_chapter_number,
            "reason": "progress_report recommended replan",
            "issue_codes": list(progress_report.get("issue_codes", [])),
            "impact_scope": {
                "from_chapter": from_chapter,
                "to_chapter": to_chapter,
                "chapter_numbers": chapter_numbers,
            },
            "updated_artifacts": ["chapter_briefs", "scene_cards"],
            "change_summary": [
                f"chapter {trigger_chapter_number} の progress_report が replan を推奨した",
            ],
            "story_state_summary": dict(progress_report.get("story_state_summary", {})),
        }
```

- [ ] **Step 4: Run the pipeline tests to verify the snapshot is saved**

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_pipeline.py::StoryPipelineTest::test_pipeline_saves_next_action_decision_after_progress_report \
  tests/test_pipeline.py::StoryPipelineTest::test_pipeline_records_replan_history_when_progress_report_recommends_replan \
  tests/test_pipeline.py::StoryPipelineTest::test_pipeline_maps_replan_recommended_action_to_replan_future_decision \
  -q
```

Expected:

```text
3 passed
```

- [ ] **Step 5: Commit the pipeline wiring**

```bash
git add src/novel_writer/pipeline.py tests/test_pipeline.py
git commit -m "feat: save story state summary in decision pipeline artifacts"
```

### Task 3: Surface The Saved Snapshot In Project Status

**Files:**
- Modify: `/Users/geekjapan/dev/auto-novel-writer/src/novel_writer/cli.py`
- Modify: `/Users/geekjapan/dev/auto-novel-writer/tests/test_cli.py`

- [ ] **Step 1: Write failing CLI tests for the new status line**

In `/Users/geekjapan/dev/auto-novel-writer/tests/test_cli.py`, extend `test_build_project_status_lines_surfaces_manual_stop_for_review_gate()` so the patched decision includes `story_state_summary` and the output includes the new line:

```python
        with patch(
            "novel_writer.cli.load_next_action_decision",
            return_value={
                "action": "stop_for_review",
                "story_state_summary": {
                    "evaluated_through_chapter": 3,
                    "canon_chapter_count": 3,
                    "thread_count": 4,
                    "unresolved_thread_count": 2,
                    "resolved_thread_count": 1,
                    "open_question_count": 5,
                    "latest_timeline_event_count": 2,
                },
            },
        ):
            lines = build_project_status_lines(project_manifest)

        self.assertIn(
            "  saved_story_state_summary: evaluated_through_chapter=3, canon_chapter_count=3, thread_count=4, unresolved_count=2, resolved_count=1, open_question_count=5, latest_timeline_event_count=2",
            lines,
        )
```

Add a new test near the existing project-status tests:

```python
    def test_build_project_status_lines_hides_saved_story_state_summary_when_next_action_has_no_summary(self) -> None:
        project_manifest = {
            "project_id": "Case 10",
            "project_slug": "case-10",
            "autonomy_level": "manual",
            "current_run": {
                "name": "latest_run",
                "output_dir": "data/projects/case-10/runs/latest_run",
                "current_step": "publish_ready_bundle",
                "completed_steps": ["story_input"],
                "chapter_statuses": [],
                "long_run_status": {},
                "comparison_basis": ["long_run_should_stop"],
                "comparison_reason": [],
                "comparison_metrics": {
                    "total_issue_score": 2,
                    "completed_step_count": 1,
                    "long_run_should_stop": False,
                },
                "comparison_reason_details": [
                    {"code": "long_run_should_stop", "value": False},
                    {"code": "total_issue_score", "value": 2},
                ],
                "policy_snapshot": {"long_run": {"max_high_severity_chapters": 6, "max_total_rerun_attempts": 20}},
            },
            "best_run": {},
            "run_candidates": [],
        }

        with patch(
            "novel_writer.cli.load_next_action_decision",
            return_value={"action": "continue"},
        ):
            lines = build_project_status_lines(project_manifest)

        self.assertFalse(any(line.startswith("  saved_story_state_summary: ") for line in lines))
```

- [ ] **Step 2: Run the targeted CLI tests to verify they fail**

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_cli.py::CliTest::test_build_project_status_lines_surfaces_manual_stop_for_review_gate \
  tests/test_cli.py::CliTest::test_build_project_status_lines_hides_saved_story_state_summary_when_next_action_has_no_summary \
  -q
```

Expected:

```text
1 failed, 1 passed
```

The first test should fail because the new line does not exist yet.

- [ ] **Step 3: Write the minimal CLI implementation**

In `/Users/geekjapan/dev/auto-novel-writer/src/novel_writer/cli.py`, add a helper near `_build_resume_gate_status_line()`:

```python
def _build_saved_story_state_summary_line(output_dir: Any) -> str | None:
    if not output_dir:
        return None

    try:
        next_action_decision = load_next_action_decision(Path(output_dir))
    except FileNotFoundError:
        return None

    story_state_summary = next_action_decision.get("story_state_summary")
    if not isinstance(story_state_summary, dict) or not story_state_summary:
        return None

    return (
        "  saved_story_state_summary: "
        f"evaluated_through_chapter={story_state_summary.get('evaluated_through_chapter', 0)}, "
        f"canon_chapter_count={story_state_summary.get('canon_chapter_count', 0)}, "
        f"thread_count={story_state_summary.get('thread_count', 0)}, "
        f"unresolved_count={story_state_summary.get('unresolved_thread_count', 0)}, "
        f"resolved_count={story_state_summary.get('resolved_thread_count', 0)}, "
        f"open_question_count={story_state_summary.get('open_question_count', 0)}, "
        f"latest_timeline_event_count={story_state_summary.get('latest_timeline_event_count', 0)}"
    )
```

Update `build_project_status_summary()` so `summary["current_run"]` also carries:

```python
            "saved_story_state_summary_line": _build_saved_story_state_summary_line(current_output_dir),
```

Update `build_project_status_lines()` so it prints the line right after `resume_gate_line`:

```python
        if current_run["resume_gate_line"]:
            lines.append(current_run["resume_gate_line"])
        if current_run["saved_story_state_summary_line"]:
            lines.append(current_run["saved_story_state_summary_line"])
        lines.append(f"  current_step: {current_run['current_step']}")
```

- [ ] **Step 4: Run the CLI tests to verify the line is rendered**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_cli.py -q -k "saved_story_state_summary or manual_stop_for_review_gate or hides_gate_when_next_action_decision_is_missing"
```

Expected:

```text
<N> passed
```

There should be `0 failed`.

- [ ] **Step 5: Commit the CLI status work**

```bash
git add src/novel_writer/cli.py tests/test_cli.py
git commit -m "feat: show saved story state summary in project status"
```

### Task 4: Sync Docs And Run Full Regression

**Files:**
- Modify: `/Users/geekjapan/dev/auto-novel-writer/README.md`
- Modify: `/Users/geekjapan/dev/auto-novel-writer/docs/TASKS.md`

- [ ] **Step 1: Update README to reflect the new status surface**

In `/Users/geekjapan/dev/auto-novel-writer/README.md`, extend the project management section after the manual review gate paragraph with:

```md
`show-project-status` では、保存済み `next_action_decision` に `story_state_summary` が含まれる場合、その判断時点の story state snapshot も確認できます。
```

- [ ] **Step 2: Mark `M66a` complete in `docs/TASKS.md`**

Move the task from `In Progress` to the top of `Recent completions`:

```markdown
## In Progress

## Ready

## Done

### Recent completions

- [x] M66a: carry shared story_state_summary into next_action_decision and replan history
- [x] M65b: add shared story_state_summary to progress_report and publish bundle
```

- [ ] **Step 3: Run the focused regression suite**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_storage.py tests/test_pipeline.py tests/test_cli.py -q
```

Expected:

```text
<N> passed
```

There should be `0 failed`.

- [ ] **Step 4: Run the full test suite**

Run:

```bash
PYTHONPATH=src python -m pytest -q
```

Expected:

```text
184 passed, 1 skipped, 4 subtests passed
```

If the exact pass count changes because new tests were added, the important condition is still:

```text
0 failed
```

- [ ] **Step 5: Commit the docs and task completion**

```bash
git add README.md docs/TASKS.md
git commit -m "docs: finish M66a next-action story state summary"
```

## Self-Review

### Spec Coverage

- `next_action_decision.story_state_summary` を必須化する要件は Task 1 と Task 2 でカバーした
- `replan_history.replans[*].story_state_summary` を必須化する要件は Task 1 と Task 2 でカバーした
- `show-project-status` に保存済み summary line を出す要件は Task 3 でカバーした
- `README.md` と `docs/TASKS.md` の同期要件は Task 4 でカバーした
- `show-run-comparison` を広げないというスコープ境界は Task 3 の実装範囲で維持した

### Placeholder Scan

- `TBD`、`TODO`、曖昧な「適切に対応する」は入れていない
- すべての code-edit step に具体的な code block を入れた
- すべての test step に exact command を入れた

### Type Consistency

- field 名はすべて `story_state_summary` で統一した
- summary の中身は既存 shared shape の field 名に合わせた
- pipeline では `progress_report["story_state_summary"]` をコピーし、CLI でも同じ field 名を読む前提で揃えた
