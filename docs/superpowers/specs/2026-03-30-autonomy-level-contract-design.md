# M63f Project Autonomy Level Contract Design

## Purpose

M63 の残件である「project 単位で autonomy level を切り替えられる」を、最小限の安全な変更で前進させる。今回のタスクでは `project_manifest.json` に `autonomy_level` を追加し、保存・読み込み・表示・テスト・docs までを固定する。pipeline の実行分岐や `assist` / `auto` の動作差は次段階に分離する。

## Scope

今回の変更に含めるもの:

- `project_manifest.json` の contract に `autonomy_level` を追加する
- 許容値を `manual` / `assist` / `auto` に固定する
- 新規 project では既定値 `assist` を保存する
- 既存 project manifest に値が無い場合は互換読み込みとして `assist` を補う
- 不正値は fail-fast で例外にする
- CLI の project status 系出力で現在値を確認できるようにする
- tests と docs を更新する

今回の変更に含めないもの:

- run manifest への `autonomy_level` 保存
- pipeline の実行分岐
- `next_action_decision` や rerun policy への新しい制御分岐
- `assist` と `auto` の実質的な挙動差

## Design

### Data Contract

- 保存先 artifact は `project_manifest.json` とする
- key 名は `autonomy_level` とする
- 許容値は `manual` / `assist` / `auto` の 3 値とする
- 新規 project の既定値は `assist` とする

この contract は project-level の運用方針を示すものであり、run 単位の snapshot にはまだ広げない。

### Compatibility

- 既存 `project_manifest.json` に `autonomy_level` が存在しない場合は、互換読み込みとして `assist` を補う
- 互換値の補完は「欠損時のみ」に限定する
- 値が存在する場合は `manual` / `assist` / `auto` のいずれかでなければ例外にする

この方針により、既存 artifact を壊さずに読み込める状態を維持しつつ、不正な値は早い段階で検出する。

### Responsibilities

- `src/novel_writer/schema.py`
  - `project_manifest` に関する contract または validation rule に `autonomy_level` を追加する
- `src/novel_writer/storage.py`
  - project manifest の save/load 経路で `autonomy_level` を欠損させない
  - 欠損時は互換補完し、不正値は fail-fast で止める
- `src/novel_writer/cli.py`
  - project 作成時に既定値 `assist` を保存する
  - project status 系の表示に `autonomy_level` を含める
- tests
  - 新規保存、互換読み込み、不正値エラー、status 表示を検証する
- docs
  - contract 固定まで完了し、挙動分岐は次段階で扱うことを明記する

## Error Handling

- `autonomy_level` が不正値の場合は、暗黙の補正を行わず例外にする
- project manifest の欠損補完は、既存 data との互換性維持のための限定的な処理として扱う
- 今回は pipeline 側に新しい fallback を追加しない

## Testing

最低限、次を確認する。

1. 新規 project 作成で `autonomy_level: "assist"` が保存される
2. `autonomy_level` が存在しない既存 manifest を読み込んだとき、互換値として `assist` が得られる
3. 不正な `autonomy_level` は明確に失敗する
4. project status 表示で現在の `autonomy_level` を確認できる

## Docs Impact

- `README.md`
  - project 単位 autonomy level の存在を短く追記する
- `docs/ROADMAP.md`
  - M63 の残件が contract 固定から次段階へ進んだことを反映する
- `docs/TASKS.md`
  - `M63f` の完了と次タスク起票を反映する
- `docs/DEVELOPMENT_GUIDE.md`
  - 必要に応じて「先に contract を固定する」方針を補足する

## Out Of Scope Follow-up

次の子タスクでは、`manual` / `assist` / `auto` を実際の制御分岐にどう結び付けるかを扱う。候補は、review 停止条件、resume 時の既定挙動、`next_action_decision` の自動適用範囲などである。ただし、それらは今回の contract 導入とは分離して検討する。
