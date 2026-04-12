# Next-Action Story-State Summary Design

## Summary

本 spec は、`M66 Evaluation` の次の最小 task として、
すでに `progress_report` と `publish_ready_bundle.summary` に保存されている
shared `story_state_summary` を、
判断 artifact にも広げる設計を固定する。

対象は次の 2 か所である。

- `next_action_decision.story_state_summary`
- `replan_history.replans[*].story_state_summary`

目的は次の 3 点である。

1. `M66` として、`issue_codes` だけでなく state 数値も判断根拠として残す
2. `M67` として、status / recovery 系が判断 artifact から同じ state snapshot を読めるようにする
3. `progress_report`、`next_action_decision`、`replan_history`、`publish_ready_bundle` の間で story state の語彙を共有し続ける

この task では新 artifact を追加しない。
既存 artifact contract を小さく拡張し、
pipeline、validator、CLI、tests を同期させる最小安全単位として扱う。

## Problem Statement

現状の repository では、shared `story_state_summary` は
次の 2 か所には保存されている。

- `progress_report.story_state_summary`
- `publish_ready_bundle.summary.story_state_summary`

この状態でも、評価入力と publish / handoff summary の間では
同じ state shape を再利用できる。
ただし、実際の制御判断に使う artifact である
`next_action_decision` と `replan_history` には、
まだ同じ snapshot が保存されていない。

そのため、次の問題が残っている。

- `M66` が「なぜその action を選んだか」をあとから見返すとき、`issue_codes` は残るが state 数値の根拠が残らない
- `M67` が status / recovery 表示を強化したいとき、判断 artifact から story state を直接読めない
- 今後、判断系 helper や CLI が `progress_report` を直接見に行ったり、別途 state を再計算したりすると、artifact ごとに語彙がずれる

このズレを防ぐために、次の task では
「判断 artifact も、共有済み story-state summary を snapshot として持つ」
ことを先に行う。

## Goals

- 新 artifact を増やさず、既存の判断 artifact に shared `story_state_summary` を追加する
- `next_action_decision` に、判断時点の story-state snapshot を保存する
- `replan_history` entry に、`replan` 判断時点の story-state snapshot を保存する
- validator が同じ shape を fail-fast に検証する
- `show-project-status` が保存済み `next_action_decision.story_state_summary` を read-only に表示できるようにする
- `M66` の判断根拠と `M67` の operational 表示の両方に橋をかける

## Non-Goals

- 新しい story-state field を追加すること
- `story_state_summary` を判断 artifact 側で再計算すること
- `show-run-comparison` の全面的な設計変更
- `next_action_decision` の action mapping や `replan_history` の意味を変えること
- evaluator 専用 score や複雑な derived metric を追加すること

## Recommended Next Task

次の実装 task は、次の 1 件として切る。

- Title
  - `M66a: carry shared story_state_summary into next_action_decision and replan history`
- Milestone
  - `M66`
- Purpose
  - 判断 artifact に shared story-state snapshot を保存し、評価根拠と operational 表示が同じ state shape を読めるようにする
- Target files or directories
  - `src/novel_writer/schema.py`
  - `src/novel_writer/pipeline.py`
  - `src/novel_writer/cli.py`
  - `tests/test_pipeline.py`
  - `tests/test_cli.py`
  - `tests/test_storage.py`
  - `README.md`
  - `docs/TASKS.md`
- Done when
  - `next_action_decision` と `replan_history` entry に `story_state_summary` が保存される
  - validator が新しい field を fail-fast に検証する
  - `show-project-status` が保存済み summary を read-only に表示できる
  - tests と docs が同期される

## Design

### 1. Placement And Responsibility

shared `story_state_summary` の保存先は次の 4 か所になる。

- `progress_report.story_state_summary`
- `next_action_decision.story_state_summary`
- `replan_history.replans[*].story_state_summary`
- `publish_ready_bundle.summary.story_state_summary`

責務は次のように分ける。

- `progress_report.story_state_summary`
  - 評価時点の shared state 正本
- `next_action_decision.story_state_summary`
  - その評価を受けて action を決めた時点の判断根拠
- `replan_history.replans[*].story_state_summary`
  - `replan` に至ったときの state snapshot
- `publish_ready_bundle.summary.story_state_summary`
  - read-only / handoff 向け summary

この配置にすると、
story state の正本 shape は 1 つのまま維持しつつ、
各 artifact が「その時点の state をどう使ったか」を保存できる。

### 2. Shape Reuse

今回の task では、新しい shape は定義しない。
`next_action_decision` と `replan_history` は、
既存の shared `story_state_summary` をそのまま再利用する。

shape は次の field からなる。

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

今回の task では次を行わない。

- `decision_story_state_summary` のような別名 field を作る
- `next_action_decision` 専用 field を追加する
- `replan_history` 専用の summary shape を追加する

理由は、shared summary の語彙を増やさずに
artifact 間で同じ意味を保つためである。

### 3. Source Of Truth

`story_state_summary` の source of truth は引き続き
`src/novel_writer/schema.py` の helper と validator に置く。

想定データフローは次のとおりである。

1. `continuity` が `progress_report.story_state_summary` を作る
2. pipeline が `next_action_decision` を作るとき、`progress_report.story_state_summary` を同梱する
3. pipeline が `replan_history` entry を作るとき、同じ `progress_report.story_state_summary` を snapshot として同梱する
4. `show-project-status` は保存済み `next_action_decision.story_state_summary` を line 化して表示する
5. 将来の status / recovery / comparison 系は、必要に応じて `next_action_decision` や `replan_history` から同じ summary を読む

重要なのは、`next_action_decision` や `replan_history` 側で
state を再計算しないことである。
再計算を始めると、`progress_report` と意味がズレる。
今回は snapshot として保存することで、
「その時点で何を根拠に判断したか」を artifact に残す。

### 4. Contract Changes

#### `next_action_decision`

`next_action_decision_contract()` に
`story_state_summary` を必須 field として追加する。

validator は次を fail-fast に検証する。

- `story_state_summary` が object であること
- field 名が shared `story_state_summary` と一致すること
- 各 field が int であること
- count 系が負値でないこと

`next_action_decision` は
`show-project-status` の resume gate 表示や、今後の operational 表示の基盤なので、
ここでは optional にしない。

#### `replan_history`

`replan_history` entry contract に
`story_state_summary` を必須 field として追加する。

validator は次を fail-fast に検証する。

- `replans[*].story_state_summary` が object であること
- field 名と型が shared `story_state_summary` と一致すること
- 負値が無いこと

これにより、`replan` になった run は
「どの state で判断したか」を履歴として残せる。

### 5. CLI Read-Only Display

今回の task では、表示面は `show-project-status` に限定して最小追加する。

想定 line 例:

```text
  saved_story_state_summary: evaluated_through_chapter=3, canon_chapter_count=3, thread_count=4, unresolved_count=2, resolved_count=1, open_question_count=5, latest_timeline_event_count=2
```

表示ポリシーは次のとおりである。

- CLI は保存済み `next_action_decision.story_state_summary` を優先して表示する
- `next_action_decision` が無い既存 run には、現在の表示方針を壊さない
- `show-run-comparison` には今回は新 line を追加しない

この境界にする理由は、
`show-run-comparison` はすでに `publish_ready_bundle.summary.story_state_summary` を通じて state を見られる一方、
今回の新規価値は「判断 artifact にも同じ snapshot が残ること」にあるためである。

### 6. Error Handling

この task でも fail-fast を維持する。

- `next_action_decision` の保存・読込時に `story_state_summary` 欠落を reject する
- `replan_history` entry の保存・読込時に `story_state_summary` 欠落を reject する
- 型不一致や負値は validator が明示的に reject する
- CLI は validation 済みの保存 artifact を表示するだけに留める

暗黙 fallback や自動補完は増やさない。
既存 run に `next_action_decision` が無い場合は、これまでどおり gate 非表示のまま扱う。

### 7. Tests

最小で必要な test は次のとおりである。

- `tests/test_storage.py`
  - `next_action_decision` が `story_state_summary` を必須化したことを確認する
  - `replan_history` entry が `story_state_summary` を必須化したことを確認する
- `tests/test_pipeline.py`
  - pipeline 実行後に `next_action_decision.story_state_summary` が保存されることを確認する
  - `replan` 発生時に `replan_history.replans[0].story_state_summary` が保存されることを確認する
- `tests/test_cli.py`
  - `show-project-status` が保存済み `next_action_decision.story_state_summary` を表示することを確認する
  - `next_action_decision` が無い既存 run の表示が壊れないことを確認する

### 8. Docs Impact

この task で更新対象になる docs は次のとおりである。

- `README.md`
  - project / run の管理情報や status 表示の説明を、必要最小限で同期する
- `docs/TASKS.md`
  - `M66a` を `In Progress` / `Done` として更新する

`ROADMAP.md` と `DEVELOPMENT_GUIDE.md` は、
今回の task では方針変更が無いため更新しない。

## Why This Is The Right Next Slice

この task は、`M65b` で固定した shared summary を
そのまま `M66` と `M67` の接続面へ持ち込む最小単位である。

- `M66` には、判断根拠の artifact 化という形で直接効く
- `M67` には、status / recovery 表示が同じ snapshot を読める基盤として効く
- 新 artifact を増やさず、既存の pipeline 制御 artifact を厚くするだけで閉じる
- `show-run-comparison` の全面改修や evaluator score の導入に比べて、変更境界が小さく安全である

この task を先に入れることで、
次の evaluation 強化や operational 表示強化は
新しい state helper を増やさず、
保存済み artifact を読む task として分割しやすくなる。
