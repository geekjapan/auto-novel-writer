# M63g Manual Resume Review Gate Design

## Purpose

M63 の次子タスクとして、project-level `autonomy_level` を最初の実際の control に結び付ける。今回のタスクでは `resume-project` に 1 箇所だけ review gate を追加し、`manual` project が review-required な decision を持つ run を自動再開しないようにする。

## Scope

今回の変更に含めるもの:

- `resume-project` 実行前に project manifest の `autonomy_level` を確認する
- current run に保存済みの `next_action_decision.json` を確認する
- `autonomy_level == "manual"` かつ `next_action_decision.action == "stop_for_review"` のとき、pipeline を呼ばず fail-fast で停止する
- CLI tests と docs を更新する

今回の変更に含めないもの:

- pipeline 本体への project-level policy 注入
- `assist` / `auto` の新しい自動分岐
- `stop_for_review` 以外の `next_action_decision.action` を使った停止条件
- `create-project`、`rerun-chapter`、`show-project-status` など他の CLI command の制御変更

## Design

### Gate Placement

gate は `cli.py` の `resume-project` 分岐にだけ追加する。`main()` の `resume-project` 経路で、`run_pipeline()` を呼ぶ前に current project の policy と current run の `next_action_decision` を確認する。

このタスクでは control の接続点を 1 箇所に限定し、pipeline 本体の責務は増やさない。

### Stop Condition

停止条件は次の 2 つが同時に成立した場合のみとする。

- project manifest の `autonomy_level` が `manual`
- current run の `next_action_decision.action` が `stop_for_review`

条件を満たす場合、`resume-project` は明示的なエラーで停止する。エラーメッセージには少なくとも `resume-project`、`manual`、`stop_for_review` が分かる情報を含める。

### Compatibility

- 既存 project manifest に `autonomy_level` が無い場合は、既存 contract どおり `assist` として扱う
- `next_action_decision.json` が存在しない場合は gate を適用しない
- `assist` / `auto` は今回のタスクでは挙動を変えない
- `manual` でも `action != "stop_for_review"` の場合は止めない

この方針により、既存 resume 経路を広く壊さずに、`manual` policy の最初の control だけを足せる。

## Responsibilities

- `src/novel_writer/cli.py`
  - `resume-project` 前の review gate を追加する
  - 停止条件に当たるときは pipeline 実行前に止める
- `src/novel_writer/storage.py`
  - 既存の `load_project_manifest()` / `load_next_action_decision()` をそのまま利用する
- `tests/test_cli.py`
  - `manual + stop_for_review` 停止
  - `assist + stop_for_review` 継続
  - `manual + decision なし` または `manual + action != stop_for_review` 継続
- `README.md`
  - `manual` project の resume gate を現状仕様として短く追記する
- `docs/TASKS.md`
  - `M63g` の完了と次タスク起票を反映する

## Error Handling

- 停止条件に当たるときは、暗黙 continuation を行わず例外で停止する
- `next_action_decision.json` が無い場合に新規 fallback artifact は作らない
- `manual` 以外の level に対する補正や推測分岐は追加しない

## Testing

最低限、次を確認する。

1. `manual` project が `stop_for_review` decision を持つ run を `resume-project` すると、pipeline 実行前に失敗する
2. `assist` project が同じ decision を持っていても、`resume-project` は従来どおり進む
3. `manual` project でも `next_action_decision` が無い、または `action != "stop_for_review"` なら止まらない

## Docs Impact

- `README.md`
  - `manual` project の review-required resume gate を現状仕様として追記する
- `docs/TASKS.md`
  - `M63g` の完了と次 task の反映を行う

## Out Of Scope Follow-up

次の子タスクでは、`assist` / `auto` の差分や、`stop_for_review` 以外の `next_action_decision.action` を control にどう結び付けるかを扱う。今回の task は `manual` の review gate を 1 箇所だけ導入するところで止める。
