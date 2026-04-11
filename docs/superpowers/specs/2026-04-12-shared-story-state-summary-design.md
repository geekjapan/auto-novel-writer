# Shared Story-State Summary Design

## Summary

本 spec は、`M65 Story State` の次の最小 task として、
既存の `canon_ledger` と `thread_registry` をもとにした
小さな machine-readable summary を定義し、
それを `progress_report` と `publish_ready_bundle.summary` の両方で共有する設計を固定する。

目的は次の 3 点である。

1. `M65` として story state の再利用しやすい要約 shape を 1 つに固定する
2. `M66 Evaluation` が参照できる評価根拠を、既存 artifact の内側に増やす
3. `M67 Operational` の read-only 表示や handoff が読める state を、同じ要約から再利用できるようにする

この task では新 artifact を追加しない。
既存 artifact の contract を小さく拡張し、
pipeline、validator、CLI、tests を同期させる最小安全単位として扱う。

## Problem Statement

現状の repository では、story state に関わる主な情報は次のように分散している。

- `canon_ledger`
  - 章ごとの新事実、変化、未解決事項、timeline event を持つ
- `thread_registry`
  - thread の status、導入章、更新章、関連人物、notes を持つ
- `progress_report`
  - 長編向け評価の checks と `recommended_action` を持つ
- `publish_ready_bundle.summary`
  - publish / handoff / read-only 表示向けの軽量 summary を持つ

ただし、`thread_registry` 側の read-only summary はある一方で、
`canon_ledger` を含めた story state 全体の要約は保存正本として存在していない。

そのため、次の問題が残っている。

- `M66` が story state を評価根拠として広げたいとき、`progress_report` 側に共通の machine-readable state summary が無い
- `M67` が status / comparison / handoff 表示を強化したいとき、read-only 表示が参照できる state summary が thread 側に偏る
- `canon_ledger` と `thread_registry` をまたぐ同じ数字や状態を、将来別々の helper や CLI 表示で組み立て始めると、表示と評価の語彙がずれる

このズレを防ぐために、次の task では
「story state の正規要約を小さく固定し、評価系と read-only 系の両方で共有する」
ことを先に行う。

## Goals

- 新 artifact を増やさず、既存 artifact の中に shared story-state summary を追加する
- `progress_report` に、今後の evaluator が参照できる `story_state_summary` を保存する
- `publish_ready_bundle.summary` に、read-only / handoff が参照できる同じ `story_state_summary` を保存する
- summary の shape を helper と validator で固定し、pipeline と CLI はその shape を再利用するだけにする
- `M65` の次 task として閉じつつ、`M66` / `M67` の後続 task が同じ summary を前提にできるようにする

## Non-Goals

- `character_state` のような新 artifact を追加すること
- thread ごとの詳細一覧や canon fact の全文一覧を新たに保存すること
- evaluator 専用の複雑な score や derived metric をこの task で導入すること
- `show-project-status` や `show-run-comparison` の全面的な設計変更
- `M65`、`M66`、`M67` 全体をこの 1 task で一気に完了させること

## Recommended Next Task

次の実装 task は、次の 1 件として切る。

- Title
  - `M65b: add shared story_state_summary to progress_report and publish bundle`
- Purpose
  - story state の正規要約を小さく固定し、`M66 Evaluation` と `M67 Operational` の両方が同じ artifact shape を読める土台を作る
- Target files or directories
  - `src/novel_writer/schema.py`
  - `src/novel_writer/pipeline.py`
  - `src/novel_writer/cli.py`
  - `tests/test_continuity.py`
  - `tests/test_pipeline.py`
  - `tests/test_cli.py`
  - `tests/test_storage.py`
  - `docs/TASKS.md`
- Done when
  - `progress_report` と `publish_ready_bundle.summary` に同じ `story_state_summary` が保存される
  - validator が新しい shape を fail-fast に検証する
  - CLI が保存済み summary を read-only に表示できる
  - tests と docs が同期される

## Design

### 1. Summary Name And Placement

shared summary の名前は `story_state_summary` とする。

保存場所は次の 2 か所に限定する。

- `progress_report.story_state_summary`
- `publish_ready_bundle.summary.story_state_summary`

この 2 か所に同じ意味の summary を置くことで、
評価系と read-only 系が別々の summary shape を持たずに済むようにする。

新しい top-level artifact は追加しない。
今回の summary は既存 artifact に寄生させ、保存正本の数を増やしすぎない。

### 2. Summary Shape

`story_state_summary` の最小 shape は次のとおりとする。

```json
{
  "evaluated_through_chapter": 3,
  "canon_chapter_count": 3,
  "thread_count": 4,
  "unresolved_thread_count": 2,
  "resolved_thread_count": 1,
  "open_question_count": 5,
  "latest_timeline_event_count": 2
}
```

各 field の意味は次のとおりである。

- `evaluated_through_chapter`
  - この summary がどの章までを対象にしているか
  - `progress_report` と `publish_ready_bundle.summary` の両方で同じ章境界を共有する
- `canon_chapter_count`
  - `canon_ledger.chapters` に存在する章 entry 数
- `thread_count`
  - `thread_registry.threads` の総数
- `unresolved_thread_count`
  - `status` が `seeded` または `progressed` の thread 数
- `resolved_thread_count`
  - `status` が `resolved` の thread 数
- `open_question_count`
  - `canon_ledger.chapters[*].open_questions` の総数
- `latest_timeline_event_count`
  - `canon_ledger` の最新章 entry にある `timeline_events` 数

### 3. What This Task Intentionally Leaves Out

今回は次を `story_state_summary` に入れない。

- 章ごとの詳細 `open_questions` 一覧
- thread ごとの `label` や `notes`
- `changed_facts` や `new_facts` の本文一覧
- character arc 単位の状態
- future chapter に対する予測値
- 自由文の総評

理由は次のとおりである。

- `M65` の次 task としては shape を小さく固定する方が安全である
- 詳細一覧を混ぜると read-only summary と evaluator input の責務が曖昧になる
- `M66` / `M67` で必要になったときに、同じ summary を拡張する余地を残せる

### 4. Source Of Truth

summary の生成 helper は `src/novel_writer/schema.py` に置く。

想定 helper:

- `build_story_state_summary(canon_ledger, thread_registry, evaluated_through_chapter)`

この helper の責務は次のとおりである。

- `canon_ledger` と `thread_registry` から summary 数値を導出する
- 入力が空または欠落していても、既存 contract と矛盾しない最小値を返す
- pipeline、CLI、tests の間で summary の shape を 1 か所に集約する

pipeline は helper を呼んで保存するだけに留める。
CLI は保存済み summary を line に整形するだけに留める。
summary の意味や数え方は helper と validator を正本とする。

### 5. Architecture And Data Flow

データフローは次のようにする。

1. pipeline が memory context として `canon_ledger` / `thread_registry` を読む
2. `progress_report` 生成時に `build_story_state_summary(...)` を呼び、`progress_report.story_state_summary` へ保存する
3. `publish_ready_bundle` 生成時に同じ helper を呼び、`publish_ready_bundle.summary.story_state_summary` へ保存する
4. CLI の publish bundle summary 表示は、保存済み `story_state_summary` を line 化して表示する
5. 後続の `M66` は `progress_report.story_state_summary` を評価根拠として再利用する
6. 後続の `M67` は `publish_ready_bundle.summary.story_state_summary` を status / comparison / handoff へ展開する

この構成では、summary の source of truth は helper と保存済み artifact にあり、
表示専用 helper や evaluator 側で独自に story state を再計算しない。

### 6. Contract Changes

#### `progress_report`

`progress_report_contract()` に `story_state_summary` を optional ではなく
保存後 artifact の正規 field として追加する。

validator は次を fail-fast に検証する。

- `story_state_summary` が object であること
- required field が全て存在すること
- 各 field が int であること
- count 系が負値でないこと

`progress_report` は今後 `M66` の入力として広がるため、
ここでは shape を曖昧にしない。

#### `publish_ready_bundle.summary`

`publish_ready_bundle_contract()["summary"]` に
`story_state_summary` を optional summary field として追加する。

validator は次を検証する。

- `summary.story_state_summary` が存在する場合は object であること
- field 名と型が `progress_report.story_state_summary` と一致すること

`publish_ready_bundle` は既存 summary backfill 互換を持っているため、
legacy artifact の読みでは今回の追加 field を必須化しない。
ただし、新しい pipeline で保存された bundle は `story_state_summary` を含むことを正とする。

### 7. CLI Read-Only Display

今回の task では、CLI 表示は `publish_ready_bundle.summary.story_state_summary` に限定して追加する。

想定 line 例:

```text
publish_bundle.story_state_summary: evaluated_through_chapter=3, canon_chapter_count=3, thread_count=4, unresolved_count=2, resolved_count=1, open_question_count=5, latest_timeline_event_count=2
```

表示ポリシーは次のとおりである。

- CLI は保存済み summary を優先して表示する
- `publish_ready_bundle.summary` 自体が無い legacy artifact には、既存の backfill 方針を維持する
- 今回は `show-project-status` や `show-run-comparison` へ新 line を広げない

理由は、次 task のスコープを
「summary shape を保存して publish bundle read-only から見える」
ところで閉じるためである。

### 8. Error Handling

この task でも fail-fast を維持する。

- validator は field 欠落、型不一致、負値を明示的に reject する
- pipeline は silent fallback を追加しない
- legacy publish bundle に対する互換読みは、既存の `summary` backfill 範囲を超えて artifact 自動書換えを行わない

summary helper では空の `canon_ledger` や `thread_registry` を許容するが、
それは「入力不足でも 0 件として summary を作れる」範囲に限る。
未定義 shape や曖昧な field は導入しない。

## Testing Strategy

次の 4 層で tests を追加または更新する。

### `tests/test_continuity.py`

- `build_progress_report()` が `story_state_summary` を含むことを確認する
- `evaluated_through_chapter` と summary 数値が期待どおりに入ることを確認する

### `tests/test_pipeline.py`

- pipeline 実行後の `progress_report.json` に `story_state_summary` が保存されること
- `publish_ready_bundle.json.summary.story_state_summary` に同じ数値が保存されること
- manifest 経由でも同じ payload が見えること

### `tests/test_cli.py`

- 保存済み `publish_ready_bundle.summary.story_state_summary` が summary lines に反映されること
- 既存 summary backfill case では新 field がなくても既存表示が壊れないこと

### `tests/test_storage.py`

- `progress_report` validator が `story_state_summary` の shape を検証すること
- `publish_ready_bundle` validator が `summary.story_state_summary` の shape を検証すること

## Rollout And Follow-On Roadmap

この task 自体は `M65` の最小 task であり、次のロードマップへの橋として扱う。

### Immediate follow-on inside `M65`

- `story_state_summary` の利用先を増やす前に、summary shape を 1 つに固定する
- 必要であれば次 task で `canon_ledger` 由来の別要約や character-oriented summary を検討する

### `M66 Evaluation` follow-on

この task の後は、`progress_report.story_state_summary` を用いて次の評価強化へ進みやすくなる。

- `open_question_count` と `unresolved_thread_count` を使った停滞検知の改善
- `canon_chapter_count` と `evaluated_through_chapter` の差分を使った評価境界の明示
- 長編の失速や未回収負荷に関する evidence の強化

### `M67 Operational` follow-on

この task の後は、`publish_ready_bundle.summary.story_state_summary` を用いて次の運用改善へ進みやすくなる。

- `show-project-status` への story state line 追加
- `show-run-comparison` の compact summary への story state 指標追加
- review / handoff 時に story state の負荷を把握しやすくする表示整理

## Risks And Mitigations

### Risk: `progress_report` と `publish_ready_bundle.summary` の shape が将来ずれる

Mitigation:
summary の生成 helper を 1 つにし、tests で両 artifact の値一致を確認する。

### Risk: summary が大きくなりすぎて read-only と evaluator input の責務が混ざる

Mitigation:
今回は count 系と章境界だけに限定し、詳細一覧や自由文を入れない。

### Risk: legacy bundle 互換と新 validator の整合が崩れる

Mitigation:
既存の `summary` backfill 方針は維持し、新 field は新規保存 artifact の正規 shape として扱う。
互換読みの責務は CLI に限定し、自動 migration は行わない。

## Open Decisions Resolved In This Spec

本 spec では次を確定する。

- 新 artifact は追加しない
- shared summary 名は `story_state_summary` とする
- summary の最初の利用先は `progress_report` と `publish_ready_bundle.summary` に限定する
- summary helper は `schema.py` に置く
- 次 task は `M65` を進めつつ、`M66` / `M67` に再利用しやすい contract を先に固める方向で切る

## Acceptance Snapshot

この spec に基づく次 task の完了条件は次のとおりである。

- `progress_report` に `story_state_summary` が保存される
- `publish_ready_bundle.summary` に同じ `story_state_summary` が保存される
- validator が shape を strict に検証する
- CLI が保存済み summary を read-only に表示できる
- tests と `docs/TASKS.md` が同期される
