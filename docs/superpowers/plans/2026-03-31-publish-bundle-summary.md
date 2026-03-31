# Publish Bundle Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `publish_ready_bundle.json` に保存済み `summary` を追加し、CLI の read-only 表示をその summary に揃える

**Architecture:** pipeline が `publish_ready_bundle.summary` を保存の正本として書き、schema がその shape を validate し、CLI は保存済み summary を line に整形するだけに留める。既存 bundle に `summary` が無い場合は CLI でだけ互換的に組み立て、artifact の自動書換えはしない。

**Tech Stack:** Python, unittest, CLI, JSON artifact storage

---

### Task 1: publish bundle の保存済み summary を導入する

**Files:**
- Modify: `/home/geekjapan/dev/auto-novel-writer/src/novel_writer/pipeline.py`
- Modify: `/home/geekjapan/dev/auto-novel-writer/src/novel_writer/schema.py`
- Modify: `/home/geekjapan/dev/auto-novel-writer/src/novel_writer/cli.py`
- Modify: `/home/geekjapan/dev/auto-novel-writer/tests/test_pipeline.py`
- Modify: `/home/geekjapan/dev/auto-novel-writer/tests/test_cli.py`
- Modify: `/home/geekjapan/dev/auto-novel-writer/docs/TASKS.md`

- [ ] **Step 1: pipeline と CLI の publish bundle 参照箇所を確認する**

確認対象:

```text
/home/geekjapan/dev/auto-novel-writer/src/novel_writer/pipeline.py
- _run_publish_ready_bundle_step()

/home/geekjapan/dev/auto-novel-writer/src/novel_writer/schema.py
- publish_ready_bundle_contract()
- validate_publish_ready_bundle()

/home/geekjapan/dev/auto-novel-writer/src/novel_writer/cli.py
- show-run-comparison と saved summary 表示系 helper
```

確認ポイント:

```text
- publish_ready_bundle が現在は top-level fields のみを持つこと
- CLI 側に publish bundle summary の保存正本がまだ無いこと
- M64a では新 artifact を増やさず bundle 本体に summary を足すこと
```

- [ ] **Step 2: publish bundle summary 保存の failing test を追加する**

`/home/geekjapan/dev/auto-novel-writer/tests/test_pipeline.py` に、bundle 保存時の `summary` を確認する assertion を追加する。

追加内容:

```python
            self.assertEqual(
                publish_ready_bundle["summary"],
                {
                    "title": publish_ready_bundle["title"],
                    "chapter_count": len(artifacts.revised_chapter_drafts),
                    "section_names": publish_ready_bundle["sections"],
                    "source_artifact_names": [
                        "story_summary.json",
                        "project_quality_report.json",
                        "revised_chapter_{n}_draft.json",
                    ],
                },
            )
```

`/home/geekjapan/dev/auto-novel-writer/tests/test_cli.py` に、保存済み `summary` を読む CLI 側のテストを追加する。

追加候補:

```python
    def test_build_publish_bundle_summary_lines_prefers_saved_summary(self) -> None:
        publish_ready_bundle = {
            "title": "Case Bundle",
            "chapter_count": 2,
            "sections": ["manuscript", "story_summary"],
            "source_artifacts": {
                "story_summary": "story_summary.json",
                "chapters": "revised_chapter_{n}_draft.json",
            },
            "summary": {
                "title": "Saved Bundle Title",
                "chapter_count": 2,
                "section_names": ["manuscript", "story_summary"],
                "source_artifact_names": [
                    "story_summary.json",
                    "revised_chapter_{n}_draft.json",
                ],
            },
        }

        lines = _build_publish_bundle_summary_lines(publish_ready_bundle)

        self.assertIn("publish_bundle.title: Saved Bundle Title", lines)
        self.assertIn("publish_bundle.chapter_count: 2", lines)
        self.assertIn("publish_bundle.section_names: manuscript, story_summary", lines)
        self.assertIn(
            "publish_bundle.source_artifact_names: story_summary.json, revised_chapter_{n}_draft.json",
            lines,
        )

    def test_build_publish_bundle_summary_lines_backfills_missing_summary(self) -> None:
        publish_ready_bundle = {
            "title": "Fallback Bundle",
            "chapter_count": 3,
            "sections": ["manuscript", "quality"],
            "source_artifacts": {
                "story_summary": "story_summary.json",
                "overall_quality_report": "project_quality_report.json",
            },
        }

        lines = _build_publish_bundle_summary_lines(publish_ready_bundle)

        self.assertIn("publish_bundle.title: Fallback Bundle", lines)
        self.assertIn("publish_bundle.chapter_count: 3", lines)
        self.assertIn("publish_bundle.section_names: manuscript, quality", lines)
        self.assertIn(
            "publish_bundle.source_artifact_names: story_summary.json, project_quality_report.json",
            lines,
        )
```

- [ ] **Step 3: 対象テストを実行して失敗を確認する**

Run:

```bash
./venv/bin/python -m unittest \
  tests.test_pipeline.TestPipeline.test_pipeline_run_writes_expected_artifacts \
  tests.test_cli.TestCLI.test_build_publish_bundle_summary_lines_prefers_saved_summary \
  tests.test_cli.TestCLI.test_build_publish_bundle_summary_lines_backfills_missing_summary \
  -v
```

Expected:

```text
FAIL
- publish_ready_bundle["summary"] is missing
- _build_publish_bundle_summary_lines is missing
```

- [ ] **Step 4: schema と pipeline に summary を追加する**

`/home/geekjapan/dev/auto-novel-writer/src/novel_writer/schema.py` で `publish_ready_bundle` contract / validator に `summary` を追加する。

追加イメージ:

```python
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
            "summary",
        ],
```

```python
        "summary": {
            "required_fields": [
                "title",
                "chapter_count",
                "section_names",
                "source_artifact_names",
            ],
        },
```

validator では `summary` が object で、required fields が揃っていることを確認する。

`/home/geekjapan/dev/auto-novel-writer/src/novel_writer/pipeline.py` では保存 payload に `summary` を追加する。

```python
        artifacts.publish_ready_bundle = {
            "schema_version": bundle_contract["schema_version"],
            "bundle_type": bundle_contract["schema_name"],
            "title": ...,
            "synopsis": ...,
            "chapter_count": ...,
            "chapters": ...,
            "story_summary": ...,
            "overall_quality_report": ...,
            "selected_logline": ...,
            "source_artifacts": {...},
            "sections": bundle_contract["sections"],
            "summary": {
                "title": artifacts.story_summary.get("title") or selected_logline.get("title"),
                "chapter_count": len(artifacts.revised_chapter_drafts),
                "section_names": bundle_contract["sections"],
                "source_artifact_names": [
                    "story_summary.json",
                    "project_quality_report.json",
                    "revised_chapter_{n}_draft.json",
                ],
            },
        }
```

- [ ] **Step 5: CLI に publish bundle summary helper を追加する**

`/home/geekjapan/dev/auto-novel-writer/src/novel_writer/cli.py` に、保存済み `summary` を優先して line を作る helper を追加する。

```python
def _build_publish_bundle_summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary")
    if isinstance(summary, dict):
        return {
            "title": summary.get("title", payload.get("title", "unknown")),
            "chapter_count": summary.get("chapter_count", payload.get("chapter_count", 0)),
            "section_names": list(summary.get("section_names", [])),
            "source_artifact_names": list(summary.get("source_artifact_names", [])),
        }

    source_artifacts = payload.get("source_artifacts", {})
    return {
        "title": payload.get("title", "unknown"),
        "chapter_count": payload.get("chapter_count", 0),
        "section_names": list(payload.get("sections", [])),
        "source_artifact_names": list(source_artifacts.values()) if isinstance(source_artifacts, dict) else [],
    }
```

```python
def _build_publish_bundle_summary_lines(payload: dict[str, Any]) -> list[str]:
    summary = _build_publish_bundle_summary(payload)
    return [
        f"publish_bundle.title: {summary['title']}",
        f"publish_bundle.chapter_count: {summary['chapter_count']}",
        f"publish_bundle.section_names: {', '.join(summary['section_names']) or 'none'}",
        f"publish_bundle.source_artifact_names: {', '.join(summary['source_artifact_names']) or 'none'}",
    ]
```

この helper を、publish bundle を扱う既存の status / comparison 要約経路へ最小限で接続する。
表示箇所では、保存済み bundle が存在する場合にだけ追加 line を出す。

- [ ] **Step 6: 対象テストを再実行して通過を確認する**

Run:

```bash
./venv/bin/python -m unittest \
  tests.test_pipeline.TestPipeline.test_pipeline_run_writes_expected_artifacts \
  tests.test_cli.TestCLI.test_build_publish_bundle_summary_lines_prefers_saved_summary \
  tests.test_cli.TestCLI.test_build_publish_bundle_summary_lines_backfills_missing_summary \
  -v
```

Expected:

```text
OK
```

- [ ] **Step 7: タスク台帳を更新する**

`/home/geekjapan/dev/auto-novel-writer/docs/TASKS.md` を更新する。

更新内容:

```text
- M64a を Done へ移す
- Ready が空なら、M64 の次の最小子タスクを 1 件起票し、In Progress に上げる
```

次タスク候補の方向:

```text
publish bundle に story bible summary / thread summary / handoff summary を 1 つずつ追加する最小子タスク
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
git add /home/geekjapan/dev/auto-novel-writer/src/novel_writer/pipeline.py \
        /home/geekjapan/dev/auto-novel-writer/src/novel_writer/schema.py \
        /home/geekjapan/dev/auto-novel-writer/src/novel_writer/cli.py \
        /home/geekjapan/dev/auto-novel-writer/tests/test_pipeline.py \
        /home/geekjapan/dev/auto-novel-writer/tests/test_cli.py \
        /home/geekjapan/dev/auto-novel-writer/docs/TASKS.md
git commit -m "feat: add publish bundle summary"
```

