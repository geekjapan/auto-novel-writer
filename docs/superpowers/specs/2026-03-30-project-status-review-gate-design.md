# Project Status Review Gate Design

## Summary

`show-project-status` に、`manual` project で保存済み `next_action_decision.action == "stop_for_review"` が current run に存在する場合の resume gate 状態を表示する。
この変更は、すでに実装済みの `resume-project` review gate を status 画面から確認できるようにし、現在の制御と利用者の見え方を一致させるためのものである。

## Goal

- `manual` project の current run が review-required で自動再開できない状態なら、その理由を `show-project-status` で確認できるようにする
- 既存の `autonomy_level` 表示と project status の summary / lines 構造を壊さない
- 新しい保存 contract を増やさず、既存 artifact から gate 状態を導出する

## Non-Goals

- `resume-project` の制御条件を増やすこと
- `project_manifest.json` に新しい gate 用キーを保存すること
- `next_action_decision` の詳細全文や `decision_trace` を status へ展開すること
- `assist` / `auto` の新しい制御差分を追加すること

## Source Of Truth

- project-level policy: `project_manifest.json` の `autonomy_level`
- review-required state: current run の `next_action_decision.json`
- status 表示: `show-project-status`

status に出す gate 情報は、新しい保存値ではなく、上記 2 つの既存 artifact から毎回組み立てる。

## Proposed Behavior

### Gate が active になる条件

以下の 2 条件が同時に成立した場合だけ、status に review gate を表示する。

1. project の `autonomy_level` が `manual`
2. current run の保存済み `next_action_decision.action` が `stop_for_review`

### Gate が非表示のままになる条件

以下のケースでは、resume gate 行は出さない。

- `autonomy_level` が `assist` または `auto`
- current run に `next_action_decision.json` が存在しない
- `next_action_decision.action` が `stop_for_review` ではない

### 表示粒度

`show-project-status` には「resume が止まる理由」を 1 行で出せれば十分とする。
この task では detailed trace や policy budget の表示までは広げない。

表示例:

```text
Project: case-06
Autonomy level: manual
Resume gate: stop_for_review
Current run: latest_run
...
```

文言は多少調整してよいが、少なくとも `manual` project に review gate がかかっていることと、理由が `stop_for_review` 由来であることが読み取れる必要がある。

## Implementation Outline

### `src/novel_writer/cli.py`

- `build_project_status_summary()` で current run 向けの resume gate 要約を追加する
- current run の `output_dir` がある場合にだけ `next_action_decision` を確認する
- `FileNotFoundError` は「保存済み decision が無い」として扱い、gate 非表示にする
- `build_project_status_lines()` では、summary に gate 情報があるときだけ 1 行追加する

### `tests/test_cli.py`

- `manual + stop_for_review` で status に gate が出ることを確認する
- `assist` または `action != stop_for_review` では gate が出ないことを確認する
- `next_action_decision` 欠損時に gate が出ないことを確認する

### `README.md`

- `show-project-status` で review gate 状態も確認できることを短く追記する

### `docs/TASKS.md`

- `M63h` 完了時に反映する

## Compatibility And Failure Handling

- 既存の `project_manifest.json` schema は変更しない
- save/load contract は変更しない
- `next_action_decision.json` が無いこと自体はエラーにしない
- `show-project-status` は表示のために current run artifact を読むが、artifact を更新しない

この task は read-only status の改善であり、新しい migration や互換層は不要である。

## Tests

- `./venv/bin/python -m unittest tests.test_cli -v`
- `./venv/bin/python -m unittest discover -s tests -v`

## Open Questions

なし。

この task は、現在の resume gate と同じ条件を status へ可視化するだけで、一意に仕様を決められる。
