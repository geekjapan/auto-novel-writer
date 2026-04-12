# Shared Story-State Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `progress_report` と `publish_ready_bundle.summary` に shared `story_state_summary` を保存し、評価系と read-only 表示系が同じ story state 要約を再利用できるようにする

**Architecture:** `src/novel_writer/schema.py` に `story_state_summary` の helper と validator を集約し、`src/novel_writer/continuity.py` と `src/novel_writer/pipeline.py` はその shape を保存するだけに留める。CLI は保存済み summary を line に整形するだけにして、legacy bundle への自動 migration や暗黙 fallback は増やさない。

**Tech Stack:** Python, pytest, unittest-style tests, JSON artifact storage, CLI

---

## File Structure

- Modify: `/Users/geekjapan/dev/auto-novel-writer/src/novel_writer/schema.py`
  - `story_state_summary` の builder、contract、validator を追加し、`progress_report` と `publish_ready_bundle.summary` の validation を広げる
- Modify: `/Users/geekjapan/dev/auto-novel-writer/src/novel_writer/continuity.py`
  - `build_progress_report()` が `canon_ledger` と `thread_registry` から `story_state_summary` を組み立てる
- Modify: `/Users/geekjapan/dev/auto-novel-writer/src/novel_writer/pipeline.py`
  - `progress_report` 保存時に `canon_ledger` を渡し、`publish_ready_bundle.summary.story_state_summary` も同じ shape で保存する
- Modify: `/Users/geekjapan/dev/auto-novel-writer/src/novel_writer/cli.py`
  - 保存済み `publish_ready_bundle.summary.story_state_summary` を read-only line として表示する
- Modify: `/Users/geekjapan/dev/auto-novel-writer/tests/test_storage.py`
  - validator が `story_state_summary` を fail-fast に検証することを確認する
- Modify: `/Users/geekjapan/dev/auto-novel-writer/tests/test_continuity.py`
  - `build_progress_report()` が summary を含むことを確認する
- Modify: `/Users/geekjapan/dev/auto-novel-writer/tests/test_pipeline.py`
  - pipeline 実行後に `progress_report.json` と `publish_ready_bundle.json` に同じ summary が入ることを確認する
- Modify: `/Users/geekjapan/dev/auto-novel-writer/tests/test_rerun_policy.py`
  - fake continuity checker の `build_progress_report()` signature と payload を新 contract に合わせる
- Modify: `/Users/geekjapan/dev/auto-novel-writer/tests/test_cli.py`
  - bundle summary line に `story_state_summary` が出ることを確認する
- Modify: `/Users/geekjapan/dev/auto-novel-writer/README.md`
  - 主な出力物に reusable story-state summary を最小限で追記する
- Modify: `/Users/geekjapan/dev/auto-novel-writer/docs/TASKS.md`
  - `M65b` を `In Progress` へ上げ、完了後に `Done` へ移す

## Shared Implementation Notes

- `story_state_summary` の field 名は spec どおり固定する
- 新 artifact は追加しない
- `publish_ready_bundle.summary.story_state_summary` は新規保存 bundle では必ず存在させる
- legacy bundle の互換読みでは、既存の `summary` backfill だけを維持し、`story_state_summary` は捏造しない
- テスト実行は `PYTHONPATH=src python -m pytest <target> -q` の形で行う
- 各 task の最後に小さくコミットする

### Task 1: Start M65b And Lock The Shared Summary Contract

**Files:**
- Modify: `/Users/geekjapan/dev/auto-novel-writer/docs/TASKS.md`
- Modify: `/Users/geekjapan/dev/auto-novel-writer/src/novel_writer/schema.py`
- Modify: `/Users/geekjapan/dev/auto-novel-writer/tests/test_storage.py`

- [ ] **Step 1: Mark `M65b` as the current task in `docs/TASKS.md`**

Replace the empty `In Progress` section with:

```markdown
## In Progress

- [ ] M65b: add shared story_state_summary to progress_report and publish bundle

## Ready
```

- [ ] **Step 2: Add failing storage tests for the new contract**

Add this test to `/Users/geekjapan/dev/auto-novel-writer/tests/test_storage.py` near the existing `progress_report` validation tests:

```python
    def test_save_progress_report_requires_story_state_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(
                ValueError,
                "Invalid progress_report: missing required fields: story_state_summary.",
            ):
                save_progress_report(
                    Path(tmp_dir),
                    {
                        "schema_name": "progress_report",
                        "schema_version": "1.0",
                        "evaluated_through_chapter": 5,
                        "checks": {
                            "chapter_role_coverage": {"status": "ok", "summary": "ok", "evidence": []},
                            "escalation_pace": {"status": "ok", "summary": "ok", "evidence": []},
                            "emotional_progression": {"status": "ok", "summary": "ok", "evidence": []},
                            "foreshadowing_coverage": {"status": "ok", "summary": "ok", "evidence": []},
                            "unresolved_thread_load": {"status": "ok", "summary": "ok", "evidence": []},
                            "climax_readiness": {"status": "ok", "summary": "ok", "evidence": []},
                        },
                        "issue_codes": [],
                        "recommended_action": "continue",
                    },
                )
```

Add this test near the existing publish bundle summary validation tests:

```python
    def test_load_publish_ready_bundle_rejects_invalid_story_state_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_artifact(
                Path(tmp_dir),
                "publish_ready_bundle",
                {
                    "schema_version": "1.0",
                    "bundle_type": "publish_ready_bundle",
                    "title": "Case 01",
                    "synopsis": "Synopsis",
                    "chapter_count": 1,
                    "chapters": [],
                    "story_summary": {},
                    "overall_quality_report": {},
                    "selected_logline": {},
                    "source_artifacts": {},
                    "sections": {
                        "manuscript": {"field": "chapters"},
                        "story_summary": {"field": "story_summary"},
                        "quality": {"field": "overall_quality_report"},
                    },
                    "summary": {
                        "title": "Case 01",
                        "chapter_count": 1,
                        "section_names": ["manuscript", "story_summary", "quality"],
                        "source_artifact_names": [],
                        "story_state_summary": {
                            "evaluated_through_chapter": 1,
                            "canon_chapter_count": 1,
                            "thread_count": 0,
                            "unresolved_thread_count": 0,
                            "resolved_thread_count": 0,
                            "open_question_count": 0,
                            "latest_timeline_event_count": "invalid",
                        },
                    },
                },
                "json",
            )

            with self.assertRaisesRegex(
                ValueError,
                "Invalid publish_ready_bundle: summary.story_state_summary.latest_timeline_event_count must be an int.",
            ):
                load_publish_ready_bundle(Path(tmp_dir))
```

Update the round-trip payload in `test_save_progress_report_round_trips_valid_payload()` so the saved payload already matches the post-change contract:

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

- [ ] **Step 3: Run the targeted storage tests to verify they fail**

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_storage.py::SaveArtifactTest::test_save_progress_report_requires_story_state_summary \
  tests/test_storage.py::SaveArtifactTest::test_load_publish_ready_bundle_rejects_invalid_story_state_summary \
  -q
```

Expected:

```text
2 failed
```

- [ ] **Step 4: Implement the shared summary contract, builder, and validators in `schema.py`**

Add the new helper functions near the existing summary helpers in `/Users/geekjapan/dev/auto-novel-writer/src/novel_writer/schema.py`:

```python
def story_state_summary_contract() -> dict:
    return {
        "required_fields": [
            "evaluated_through_chapter",
            "canon_chapter_count",
            "thread_count",
            "unresolved_thread_count",
            "resolved_thread_count",
            "open_question_count",
            "latest_timeline_event_count",
        ],
    }


def build_story_state_summary(
    canon_ledger: dict,
    thread_registry: dict,
    evaluated_through_chapter: int,
) -> dict:
    if not isinstance(canon_ledger, dict):
        canon_ledger = {}
    if not isinstance(thread_registry, dict):
        thread_registry = {}

    chapters = canon_ledger.get("chapters")
    if not isinstance(chapters, list):
        chapters = []

    threads = thread_registry.get("threads")
    if not isinstance(threads, list):
        threads = []

    latest_chapter = chapters[-1] if chapters and isinstance(chapters[-1], dict) else {}
    latest_timeline_events = latest_chapter.get("timeline_events")
    if not isinstance(latest_timeline_events, list):
        latest_timeline_events = []

    open_question_count = 0
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        open_questions = chapter.get("open_questions")
        if isinstance(open_questions, list):
            open_question_count += len(open_questions)

    unresolved_thread_count = 0
    resolved_thread_count = 0
    for thread in threads:
        if not isinstance(thread, dict):
            continue
        status = thread.get("status")
        if status in {"seeded", "progressed"}:
            unresolved_thread_count += 1
        elif status == "resolved":
            resolved_thread_count += 1

    return {
        "evaluated_through_chapter": evaluated_through_chapter,
        "canon_chapter_count": len(chapters),
        "thread_count": len(threads),
        "unresolved_thread_count": unresolved_thread_count,
        "resolved_thread_count": resolved_thread_count,
        "open_question_count": open_question_count,
        "latest_timeline_event_count": len(latest_timeline_events),
    }


def _validate_story_state_summary(payload: object, prefix: str, field_name: str) -> dict:
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid {prefix}: {field_name} must be an object.")

    contract = story_state_summary_contract()
    missing_fields = [field for field in contract["required_fields"] if field not in payload]
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(f"Invalid {prefix}: {field_name} is missing required fields: {missing}.")

    for required_field in contract["required_fields"]:
        value = payload.get(required_field)
        _validate_int_field(value, prefix, f"{field_name}.{required_field}")
        if value < 0:
            raise ValueError(
                f"Invalid {prefix}: {field_name}.{required_field} must be greater than or equal to 0."
            )

    return payload
```

Update `build_publish_ready_bundle_summary()` to preserve saved `story_state_summary` when it exists:

```python
            **(
                {"story_state_summary": summary["story_state_summary"]}
                if isinstance(summary.get("story_state_summary"), dict)
                else {}
            ),
```

Update `progress_report_contract()` to require the new field:

```python
        "required_fields": [
            "schema_name",
            "schema_version",
            "evaluated_through_chapter",
            "checks",
            "issue_codes",
            "recommended_action",
            "story_state_summary",
        ],
```

Call the validator inside `validate_progress_report()`:

```python
    _validate_story_state_summary(
        payload.get("story_state_summary"),
        "progress_report",
        "story_state_summary",
    )
```

Add the nested field list to `publish_ready_bundle_contract()["summary"]`:

```python
            "story_state_summary_fields": [
                "evaluated_through_chapter",
                "canon_chapter_count",
                "thread_count",
                "unresolved_thread_count",
                "resolved_thread_count",
                "open_question_count",
                "latest_timeline_event_count",
            ],
```

And validate the optional nested object inside `validate_publish_ready_bundle()`:

```python
    story_state_summary = summary.get("story_state_summary")
    if story_state_summary is not None:
        _validate_story_state_summary(
            story_state_summary,
            "publish_ready_bundle",
            "summary.story_state_summary",
        )
```

- [ ] **Step 5: Re-run the targeted storage tests and confirm they pass**

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_storage.py::SaveArtifactTest::test_save_progress_report_requires_story_state_summary \
  tests/test_storage.py::SaveArtifactTest::test_load_publish_ready_bundle_rejects_invalid_story_state_summary \
  tests/test_storage.py::SaveArtifactTest::test_save_progress_report_round_trips_valid_payload \
  -q
```

Expected:

```text
3 passed
```

- [ ] **Step 6: Commit the contract work**

Run:

```bash
git add \
  docs/TASKS.md \
  src/novel_writer/schema.py \
  tests/test_storage.py
git commit -m "feat: validate shared story state summary"
```

### Task 2: Save The Shared Summary Through Continuity And Pipeline

**Files:**
- Modify: `/Users/geekjapan/dev/auto-novel-writer/src/novel_writer/continuity.py`
- Modify: `/Users/geekjapan/dev/auto-novel-writer/src/novel_writer/pipeline.py`
- Modify: `/Users/geekjapan/dev/auto-novel-writer/tests/test_continuity.py`
- Modify: `/Users/geekjapan/dev/auto-novel-writer/tests/test_pipeline.py`
- Modify: `/Users/geekjapan/dev/auto-novel-writer/tests/test_rerun_policy.py`

- [ ] **Step 1: Extend the continuity and pipeline tests with the new summary expectations**

Update `/Users/geekjapan/dev/auto-novel-writer/tests/test_continuity.py` by adding a `canon_ledger` fixture and a strict assertion:

```python
        canon_ledger = {
            "schema_name": "canon_ledger",
            "schema_version": "1.0",
            "chapters": [
                {
                    "chapter_number": 1,
                    "new_facts": ["fact-1"],
                    "changed_facts": [],
                    "open_questions": ["q1", "q2"],
                    "timeline_events": ["e1"],
                },
                {
                    "chapter_number": 2,
                    "new_facts": ["fact-2"],
                    "changed_facts": [],
                    "open_questions": ["q3"],
                    "timeline_events": ["e2"],
                },
                {
                    "chapter_number": 3,
                    "new_facts": ["fact-3"],
                    "changed_facts": [],
                    "open_questions": [],
                    "timeline_events": ["e3", "e4"],
                },
            ],
        }
```

Change the call and assertion to:

```python
        progress_report = ContinuityChecker().build_progress_report(
            artifacts,
            canon_ledger,
            thread_registry,
        )

        self.assertEqual(
            progress_report["story_state_summary"],
            {
                "evaluated_through_chapter": 3,
                "canon_chapter_count": 3,
                "thread_count": 1,
                "unresolved_thread_count": 1,
                "resolved_thread_count": 0,
                "open_question_count": 3,
                "latest_timeline_event_count": 2,
            },
        )
```

Update `/Users/geekjapan/dev/auto-novel-writer/tests/test_pipeline.py` imports:

```python
from novel_writer.schema import (
    StoryInput,
    build_handoff_summary,
    build_publish_ready_bundle_summary,
    build_story_bible_summary,
    build_story_state_summary,
    build_thread_summary,
)
```

Update storage imports in the same file:

```python
from novel_writer.storage import (
    load_canon_ledger,
    load_chapter_briefs,
    load_next_action_decision,
    load_replan_history,
    load_publish_ready_bundle,
    load_scene_cards,
    save_canon_ledger,
    save_thread_registry,
)
```

Inside `test_pipeline_run_writes_expected_artifacts()`, load `canon_ledger` and assert the shared summary in both artifacts:

```python
            canon_ledger = load_canon_ledger(output_dir)
```

```python
            self.assertEqual(
                progress_report["story_state_summary"],
                build_story_state_summary(
                    canon_ledger,
                    thread_registry,
                    progress_report["evaluated_through_chapter"],
                ),
            )
```

```python
                    "story_state_summary": build_story_state_summary(
                        canon_ledger,
                        thread_registry,
                        progress_report["evaluated_through_chapter"],
                    ),
```

- [ ] **Step 2: Run the targeted integration tests and confirm they fail**

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_continuity.py::ContinuityCheckerTest::test_build_progress_report_summarizes_long_form_checks \
  tests/test_pipeline.py::StoryPipelineTest::test_pipeline_run_writes_expected_artifacts \
  -q
```

Expected:

```text
2 failed
```

- [ ] **Step 3: Implement the continuity and pipeline wiring**

Update the import in `/Users/geekjapan/dev/auto-novel-writer/src/novel_writer/continuity.py`:

```python
from novel_writer.schema import StoryArtifacts, build_story_state_summary
```

Change `build_progress_report()` to accept `canon_ledger` and attach the shared summary:

```python
    def build_progress_report(
        self,
        artifacts: StoryArtifacts,
        canon_ledger: dict[str, Any],
        thread_registry: dict[str, Any],
    ) -> dict[str, Any]:
        evaluated_through_chapter = len(artifacts.revised_chapter_drafts) or len(artifacts.chapter_plan)
        checks = {
            "chapter_role_coverage": self._evaluate_chapter_role_coverage(artifacts),
            "escalation_pace": self._evaluate_escalation_pace(artifacts),
            "emotional_progression": self._evaluate_emotional_progression(artifacts),
            "foreshadowing_coverage": self._evaluate_progress_foreshadowing_coverage(artifacts, thread_registry),
            "unresolved_thread_load": self._evaluate_unresolved_thread_load(artifacts, thread_registry),
            "climax_readiness": self._evaluate_climax_readiness(artifacts),
        }
        issue_codes = [
            payload["code"]
            for payload in checks.values()
            if payload.get("status") != "ok" and payload.get("code")
        ]
        return {
            "schema_name": "progress_report",
            "schema_version": "1.0",
            "evaluated_through_chapter": evaluated_through_chapter,
            "checks": checks,
            "issue_codes": issue_codes,
            "recommended_action": self._recommend_progress_action(issue_codes, checks),
            "story_state_summary": build_story_state_summary(
                canon_ledger,
                thread_registry,
                evaluated_through_chapter,
            ),
        }
```

Update `/Users/geekjapan/dev/auto-novel-writer/src/novel_writer/pipeline.py` imports:

```python
from novel_writer.schema import (
    StoryArtifacts,
    StoryInput,
    build_handoff_summary,
    build_publish_ready_bundle_summary,
    build_story_bible_summary,
    build_story_state_summary,
    build_thread_summary,
)
```

Pass `canon_ledger` into the progress report build:

```python
        canon_ledger, thread_registry = self._load_memory_context(self.output_dir)
        artifacts.progress_report = self.continuity_checker.build_progress_report(
            artifacts,
            canon_ledger,
            thread_registry,
        )
```

Expand `_build_publish_ready_bundle()` so it can reuse the same summary:

```python
    def _build_publish_ready_bundle(
        self,
        artifacts: StoryArtifacts,
        selected_logline: dict,
        canon_ledger: dict | None = None,
        thread_registry: dict | None = None,
    ) -> dict:
        if canon_ledger is None or thread_registry is None:
            canon_ledger, thread_registry = self._load_memory_context(self.output_dir)

        bundle_contract = artifacts.artifact_contract()["publish_ready_bundle"]
        publish_ready_bundle = {
            "schema_version": bundle_contract["schema_version"],
            "bundle_type": bundle_contract["schema_name"],
            "title": artifacts.story_summary.get("title") or selected_logline.get("title"),
            "synopsis": artifacts.story_summary.get("synopsis", ""),
            "chapter_count": len(artifacts.revised_chapter_drafts),
            "chapters": artifacts.revised_chapter_drafts,
            "story_summary": artifacts.story_summary,
            "overall_quality_report": artifacts.project_quality_report,
            "selected_logline": selected_logline,
            "source_artifacts": {
                "story_summary": "story_summary.json",
                "overall_quality_report": "project_quality_report.json",
                "chapters": "revised_chapter_{n}_draft.json",
            },
            "sections": bundle_contract["sections"],
        }
        publish_ready_bundle["summary"] = build_publish_ready_bundle_summary(publish_ready_bundle)
        publish_ready_bundle["summary"]["story_bible_summary"] = build_story_bible_summary(
            artifacts.story_bible,
        )
        publish_ready_bundle["summary"]["thread_summary"] = build_thread_summary(thread_registry)
        publish_ready_bundle["summary"]["story_state_summary"] = build_story_state_summary(
            canon_ledger,
            thread_registry,
            artifacts.progress_report.get(
                "evaluated_through_chapter",
                len(artifacts.revised_chapter_drafts),
            ),
        )
        publish_ready_bundle["summary"]["handoff_summary"] = build_handoff_summary(publish_ready_bundle)
        return publish_ready_bundle
```

Update the fake continuity checkers in `/Users/geekjapan/dev/auto-novel-writer/tests/test_pipeline.py` and `/Users/geekjapan/dev/auto-novel-writer/tests/test_rerun_policy.py` to use the new signature and return a valid summary:

```python
from novel_writer.schema import StoryInput, build_story_state_summary
```

```python
    def build_progress_report(self, artifacts, canon_ledger, thread_registry):
        return {
            "schema_name": "progress_report",
            "schema_version": "1.0",
            "evaluated_through_chapter": len(artifacts.chapter_plan),
            "checks": {
                "chapter_role_coverage": {"status": "ok", "summary": "ok", "evidence": []},
                "escalation_pace": {"status": "ok", "summary": "ok", "evidence": []},
                "emotional_progression": {"status": "ok", "summary": "ok", "evidence": []},
                "foreshadowing_coverage": {"status": "ok", "summary": "ok", "evidence": []},
                "unresolved_thread_load": {"status": "ok", "summary": "ok", "evidence": []},
                "climax_readiness": {"status": "ok", "summary": "ok", "evidence": []},
            },
            "issue_codes": [],
            "recommended_action": "continue",
            "story_state_summary": build_story_state_summary(
                canon_ledger,
                thread_registry,
                len(artifacts.chapter_plan),
            ),
        }
```

Update every derived fake in `/Users/geekjapan/dev/auto-novel-writer/tests/test_pipeline.py` so `super()` receives the new argument list:

```python
class ReplanTriggerContinuityChecker(NoRerunContinuityChecker):
    def build_progress_report(self, artifacts, canon_ledger, thread_registry):
        report = super().build_progress_report(artifacts, canon_ledger, thread_registry)
        report["issue_codes"] = ["climax_readiness_low"]
        report["recommended_action"] = "replan"
        report["checks"]["climax_readiness"] = {
            "status": "warning",
            "summary": "終盤準備が不足している",
            "evidence": ["chapter-3"],
        }
        return report
```

Apply the same signature change to:

```python
class EarlyReplanTriggerContinuityChecker(NoRerunContinuityChecker):
    def build_progress_report(self, artifacts, canon_ledger, thread_registry):
        report = super().build_progress_report(artifacts, canon_ledger, thread_registry)
        report["evaluated_through_chapter"] = 1
        report["issue_codes"] = ["escalation_pace_flat"]
        report["recommended_action"] = "replan"
        report["checks"]["escalation_pace"] = {
            "status": "warning",
            "summary": "第2章以降の役割を組み替える必要がある",
            "evidence": ["chapter-1"],
        }
        return report


class ReviseTriggerContinuityChecker(NoRerunContinuityChecker):
    def build_progress_report(self, artifacts, canon_ledger, thread_registry):
        report = super().build_progress_report(artifacts, canon_ledger, thread_registry)
        report["evaluated_through_chapter"] = 2
        report["issue_codes"] = ["emotional_progression_stall"]
        report["recommended_action"] = "revise"
        report["checks"]["emotional_progression"] = {
            "status": "warning",
            "summary": "感情変化が弱く改稿が必要である",
            "evidence": ["chapter-2"],
        }
        return report


class RerunTriggerContinuityChecker(NoRerunContinuityChecker):
    def build_progress_report(self, artifacts, canon_ledger, thread_registry):
        report = super().build_progress_report(artifacts, canon_ledger, thread_registry)
        report["evaluated_through_chapter"] = 2
        report["issue_codes"] = ["chapter_role_coverage_gap"]
        report["recommended_action"] = "rerun"
        report["checks"]["chapter_role_coverage"] = {
            "status": "warning",
            "summary": "章役割が崩れており再実行が必要である",
            "evidence": ["chapter-2"],
        }
        return report


class StopForReviewContinuityChecker(NoRerunContinuityChecker):
    def build_progress_report(self, artifacts, canon_ledger, thread_registry):
        report = super().build_progress_report(artifacts, canon_ledger, thread_registry)
        report["issue_codes"] = ["human_review_required"]
        report["recommended_action"] = "stop_for_review"
        report["checks"]["unresolved_thread_load"] = {
            "status": "warning",
            "summary": "保留案件が多く人手確認が必要である",
            "evidence": ["chapter-3"],
        }
        return report
```

- [ ] **Step 4: Re-run the targeted integration tests and confirm they pass**

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_continuity.py::ContinuityCheckerTest::test_build_progress_report_summarizes_long_form_checks \
  tests/test_pipeline.py::StoryPipelineTest::test_pipeline_run_writes_expected_artifacts \
  tests/test_rerun_policy.py \
  -q
```

Expected:

```text
all selected tests pass
```

- [ ] **Step 5: Commit the continuity and pipeline wiring**

Run:

```bash
git add \
  src/novel_writer/continuity.py \
  src/novel_writer/pipeline.py \
  tests/test_continuity.py \
  tests/test_pipeline.py \
  tests/test_rerun_policy.py
git commit -m "feat: save shared story state summary"
```

### Task 3: Expose The Shared Summary In CLI Output

**Files:**
- Modify: `/Users/geekjapan/dev/auto-novel-writer/src/novel_writer/cli.py`
- Modify: `/Users/geekjapan/dev/auto-novel-writer/tests/test_cli.py`

- [ ] **Step 1: Add failing CLI expectations for the new line**

In `test_build_publish_bundle_summary_lines_prefers_saved_summary()`, extend the saved summary fixture:

```python
                "story_state_summary": {
                    "evaluated_through_chapter": 2,
                    "canon_chapter_count": 2,
                    "thread_count": 3,
                    "unresolved_thread_count": 2,
                    "resolved_thread_count": 1,
                    "open_question_count": 4,
                    "latest_timeline_event_count": 1,
                },
```

And extend the expected lines with:

```python
                "publish_bundle.story_state_summary: evaluated_through_chapter=2, canon_chapter_count=2, thread_count=3, unresolved_count=2, resolved_count=1, open_question_count=4, latest_timeline_event_count=1",
```

Do the same in `test_print_run_summary_uses_saved_publish_bundle_summary()`:

```python
                    "story_state_summary": {
                        "evaluated_through_chapter": 2,
                        "canon_chapter_count": 2,
                        "thread_count": 2,
                        "unresolved_thread_count": 1,
                        "resolved_thread_count": 1,
                        "open_question_count": 3,
                        "latest_timeline_event_count": 1,
                    },
```

And assert the printed line:

```python
        self.assertIn(
            "publish_bundle.story_state_summary: evaluated_through_chapter=2, canon_chapter_count=2, thread_count=2, unresolved_count=1, resolved_count=1, open_question_count=3, latest_timeline_event_count=1",
            output,
        )
```

- [ ] **Step 2: Run the targeted CLI tests and confirm they fail**

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_cli.py::CliTest::test_build_publish_bundle_summary_lines_prefers_saved_summary \
  tests/test_cli.py::CliTest::test_print_run_summary_uses_saved_publish_bundle_summary \
  -q
```

Expected:

```text
2 failed
```

- [ ] **Step 3: Render the new line in `_build_publish_bundle_summary_lines()`**

Update `/Users/geekjapan/dev/auto-novel-writer/src/novel_writer/cli.py`:

```python
    story_state_summary = summary.get("story_state_summary", {})
    if isinstance(story_state_summary, dict) and story_state_summary:
        lines.append(
            "publish_bundle.story_state_summary: "
            f"evaluated_through_chapter={story_state_summary.get('evaluated_through_chapter', 0)}, "
            f"canon_chapter_count={story_state_summary.get('canon_chapter_count', 0)}, "
            f"thread_count={story_state_summary.get('thread_count', 0)}, "
            f"unresolved_count={story_state_summary.get('unresolved_thread_count', 0)}, "
            f"resolved_count={story_state_summary.get('resolved_thread_count', 0)}, "
            f"open_question_count={story_state_summary.get('open_question_count', 0)}, "
            f"latest_timeline_event_count={story_state_summary.get('latest_timeline_event_count', 0)}"
        )
```

Keep the existing `story_bible_summary`, `thread_summary`, and `handoff_summary` rendering order intact.

- [ ] **Step 4: Re-run the targeted CLI tests and confirm they pass**

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_cli.py::CliTest::test_build_publish_bundle_summary_lines_prefers_saved_summary \
  tests/test_cli.py::CliTest::test_print_run_summary_uses_saved_publish_bundle_summary \
  tests/test_cli.py::CliTest::test_build_publish_bundle_summary_lines_backfills_missing_summary \
  -q
```

Expected:

```text
3 passed
```

- [ ] **Step 5: Commit the CLI output change**

Run:

```bash
git add \
  src/novel_writer/cli.py \
  tests/test_cli.py
git commit -m "feat: show shared story state summary in cli"
```

### Task 4: Finish The Task, Sync Docs, And Run Regression

**Files:**
- Modify: `/Users/geekjapan/dev/auto-novel-writer/docs/TASKS.md`
- Modify: `/Users/geekjapan/dev/auto-novel-writer/README.md`

- [ ] **Step 1: Mark `M65b` as done and update the README output summary**

Update `/Users/geekjapan/dev/auto-novel-writer/docs/TASKS.md` so the task moves from `In Progress` to the top of `Recent completions`:

```markdown
## In Progress

## Ready

## Done

### Recent completions

- [x] M65b: add shared story_state_summary to progress_report and publish bundle
- [x] M65a: add unresolved thread snapshots to chapter_handoff_packet
```

Update `/Users/geekjapan/dev/auto-novel-writer/README.md` under `## 主な出力物`:

```markdown
- 草稿と改稿稿
- continuity / quality 系の確認結果
- 評価と handoff に再利用できる story state summary
- project / run の管理情報
- 比較・選抜用の run summary
- 公開用の bundle
```

- [ ] **Step 2: Run the focused regression suite for all touched areas**

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_storage.py \
  tests/test_continuity.py \
  tests/test_pipeline.py \
  tests/test_cli.py \
  tests/test_rerun_policy.py \
  -q
```

Expected:

```text
all selected test files pass
```

- [ ] **Step 3: Run the full regression suite**

Run:

```bash
PYTHONPATH=src python -m pytest -q
```

Expected:

```text
all tests pass
```

- [ ] **Step 4: Commit the docs sync and completed task state**

Run:

```bash
git add \
  README.md \
  docs/TASKS.md
git commit -m "docs: finish M65b shared story state summary"
```

## Self-Review

### Spec Coverage

- `story_state_summary` の shape 固定
  - Task 1 で contract / helper / validator を追加する
- `progress_report.story_state_summary` の保存
  - Task 2 で `ContinuityChecker` と pipeline を更新する
- `publish_ready_bundle.summary.story_state_summary` の保存
  - Task 2 で publish bundle 生成を更新する
- CLI read-only line の追加
  - Task 3 で `_build_publish_bundle_summary_lines()` を更新する
- tests / docs 同期
  - Task 1 から Task 4 で storage / continuity / pipeline / CLI / README / TASKS を順に更新する

### Placeholder Scan

- 未記入の保留語や後回し前提の文言は含めていない
- 各 code step に actual code を入れている
- 各 test step に exact command と expected result を入れている

### Type Consistency

- summary 名は全 task で `story_state_summary`
- field 名は全 task で
  - `evaluated_through_chapter`
  - `canon_chapter_count`
  - `thread_count`
  - `unresolved_thread_count`
  - `resolved_thread_count`
  - `open_question_count`
  - `latest_timeline_event_count`
- `ContinuityChecker.build_progress_report()` の新 signature は全 task で
  - `(artifacts, canon_ledger, thread_registry)`
