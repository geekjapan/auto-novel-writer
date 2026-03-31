# Manual Review Gate Helper Design

## Summary

`resume-project` と `show-project-status` が別々に持っている `manual + next_action_decision.action == "stop_for_review"` 判定を、CLI 内の 1 つの helper にまとめる。
この task は review gate の source of truth を 1 つに揃えるための refactor であり、既存の停止条件や status 表示条件は変更しない。

## Goal

- `resume-project` と `show-project-status` が同じ review gate 判定 helper を使うようにする
- `manual + stop_for_review` の解釈を CLI 内で二重管理しないようにする
- 既存の `manual` / `assist` / decision 欠損の挙動を変えない

## Non-Goals

- review gate の条件を増やすこと
- `assist` / `auto` の新しい制御差分を追加すること
- `project_manifest.json` や `next_action_decision.json` の schema / save-load contract を変えること
- README の外向き仕様を変えること

## Source Of Truth

review gate の source of truth は次の 2 つとする。

- `project_manifest.json` の `autonomy_level`
- current run の `next_action_decision.json`

判定条件は既存どおり、以下の 2 条件が同時に成立した場合だけ gate active とする。

1. `autonomy_level == "manual"`
2. `next_action_decision.action == "stop_for_review"`

## Proposed Design

### 共通 helper

CLI 内に、review gate 判定専用の小さい helper を追加する。

想定インターフェース:

```python
def _build_manual_review_gate(project_manifest: dict[str, Any], output_dir: Path) -> dict[str, Any] | None:
    ...
```

戻り値:

- gate が active の場合:

```python
{"reason": "stop_for_review"}
```

- gate が無い場合:

```python
None
```

この helper は表示文言や例外メッセージを返さず、「gate があるか」と「理由は何か」だけを返す。

### `resume-project` 側

`_enforce_resume_project_review_gate()` は上記 helper を呼び、戻り値が `None` でなければ既存の `ValueError` を投げる。
例外メッセージ自体は現状の文言を維持する。

### `show-project-status` 側

status summary / lines も同じ helper を呼び、戻り値が `None` でなければ `Resume gate: stop_for_review` を表示する。
表示文言も現状維持とする。

## Failure Handling And Compatibility

以下の条件では helper は `None` を返す。

- `autonomy_level != "manual"`
- `next_action_decision.json` が存在しない
- `next_action_decision.action != "stop_for_review"`

`FileNotFoundError` は、現状どおり「保存済み decision が無い」として扱う。
この task は refactor なので、既存の failure behavior や user-facing behavior を変えない。

## Implementation Outline

### `src/novel_writer/cli.py`

- review gate 条件を共通 helper へ抽出する
- `resume-project` 側は helper を使うように置き換える
- status 側も helper を使うように置き換える
- 既存の表示行や例外文言は維持する

### `tests/test_cli.py`

- 既存の `resume-project` テストがそのまま通ることを確認する
- 既存の `show-project-status` review gate テストがそのまま通ることを確認する
- 必要なら helper 抽出後も branch が守られていることを分かりやすくするために最小限の補助テストを整理する

### `docs/TASKS.md`

- `M63i` 完了時に Done へ移す
- `Ready` が空なら、M63 の次の最小子タスクを起票して `In Progress` に上げる

## Tests

- `./venv/bin/python -m unittest tests.test_cli -v`
- `./venv/bin/python -m unittest discover -s tests -v`

## Open Questions

なし。

この task は既存判定の共通化であり、仕様判断は一意に決められる。
