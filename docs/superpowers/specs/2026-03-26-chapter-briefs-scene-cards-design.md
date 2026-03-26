# Chapter Briefs / Scene Cards Design

## 概要

本 spec は、`story_bible` 導入後の次段として、長編向けの章成功条件レイヤ `chapter_briefs` と、scene 分解レイヤ `scene_cards` を追加する設計を定義する。

目的は、10 万字超の長編でも章ごとの役割と進行条件を artifact として固定し、本文生成が chapter plan だけに依存して脱線する状態を減らすことである。

この変更では、`story_bible -> chapter_plan -> chapter_briefs -> scene_cards -> chapter_drafts` の依存順を新しい正本の流れとする。

## 背景

現状の repository は `story_bible` を導入済みであり、`chapter_plan` は `story_bible` を参照して生成できる。
一方で、本文生成の直前に「各章が何を達成すべきか」「章をどの scene 群で構成するか」を固定する artifact がないため、長編で本文の成功条件が曖昧になりやすい。

`docs/ROADMAP.md` でも、M58 の目的は chapter brief と scene card の導入による chapter / scene 分解の強化とされている。

## スコープ

今回の設計対象は次の 2 artifact に限定する。

- `chapter_briefs.json`
- `scene_cards.json`

今回の設計では、以下は扱わない。

- `canon_ledger`
- `thread_registry`
- `progress_report`
- `replan_history`
- autonomy policy

これらは後続 milestone で追加する。

## 設計方針

### 1. 責務分離

- `story_bible`: 作品全体の設計正本
- `chapter_plan`: 章の大枠計画
- `chapter_briefs`: 章の成功条件の正本
- `scene_cards`: 章 brief を scene 単位へ展開した実行計画
- `chapter_drafts`: 本文生成結果

`chapter_briefs` を章単位の正本とし、`scene_cards` はその具体化とする。
この分離により、将来の rerun / replan で「章の目的を維持したまま scene だけ調整する」「章 brief から後続章を更新する」といった操作をしやすくする。

### 2. 可変 scene 数

`scene_cards` は章ごとの可変配列とする。
ただし、長編での極端な粗密を避けるため、実装時には各章あたりの scene 数に下限と上限を持たせる前提とする。
初期設計では 3 から 7 scene 程度を想定するが、厳密な定数値は実装 plan で決める。

### 3. Fail Fast

暗黙 fallback は実装しない。

- `chapter_briefs` は `story_bible` と `chapter_plan` の両方が揃っていなければ生成できない
- `scene_cards` は対応する `chapter_brief` が揃っていなければ生成できない
- `chapter_drafts` は `chapter_plan` だけでは生成せず、対応する `chapter_brief` と `scene_cards` が欠けていたら明示的に失敗する

## Artifact Design

### `chapter_briefs`

`chapter_briefs` は章ごとの成功条件を固定する artifact である。

各章は最低限次の field を持つ。

- `chapter_number`
- `purpose`
- `goal`
- `conflict`
- `turn`
- `must_include`
- `continuity_dependencies`
- `foreshadowing_targets`
- `arc_progress`
- `target_length_guidance`

field の意図:

- `purpose`: 章が長編全体の中で担う役割
- `goal`: 章で達成すべき前進
- `conflict`: 章の主衝突
- `turn`: 章内で起きる転換
- `must_include`: scene 化や本文生成で落としてはいけない要素
- `continuity_dependencies`: 既出事実や設定のうち参照必須な前提
- `foreshadowing_targets`: この章で出すべき伏線、または回収対象
- `arc_progress`: 人物や関係性の進行
- `target_length_guidance`: 章の比重や長さの目安

`target_length_guidance` は厳密な文字数固定ではなく、章の比重制御に使う。
これにより、10 万字超の長編でも「接続章は軽く、転換章は厚く」といった設計を artifact に保持できる。

### `scene_cards`

`scene_cards` は `chapter_briefs` を scene 単位へ展開した artifact である。

各 scene は最低限次の field を持つ。

- `scene_number`
- `chapter_number`
- `scene_goal`
- `scene_conflict`
- `scene_turn`
- `pov_character`
- `participants`
- `setting`
- `must_include`
- `continuity_refs`
- `foreshadowing_action`
- `exit_state`

field の意図:

- `scene_goal`: scene 単位の前進目標
- `scene_conflict`: その scene での障害や摩擦
- `scene_turn`: scene の終端で起きる変化
- `pov_character`: 視点人物
- `participants`: 主な関与人物
- `setting`: 場所や時間帯などの舞台情報
- `must_include`: その scene で必ず触れる要素
- `continuity_refs`: 参照すべき既出情報
- `foreshadowing_action`: 伏線を張る、進める、回収するなどの操作
- `exit_state`: scene 終了時点で成立しているべき新状態

`exit_state` を必須にすることで、scene 列が単なる箇条書きではなく、因果を持った進行計画になる。

## Pipeline Design

新しい pipeline 順序は次のとおりとする。

1. `story_input`
2. `loglines`
3. `characters`
4. `three_act_plot`
5. `story_bible`
6. `chapter_plan`
7. `chapter_briefs`
8. `scene_cards`
9. `chapter_drafts`
10. `continuity_report`
11. `quality_report`
12. `revised_chapter_drafts`
13. `story_summary`
14. `project_quality_report`
15. `publish_ready_bundle`

`chapter_drafts` 生成は、従来の `chapter_plan` 依存から次へ広げる。

- 対応する `chapter_plan`
- 対応する `chapter_brief`
- 対応する `scene_cards`
- 必要に応じて `story_bible`

これにより、本文生成前に章目的と scene の出口状態が固定される。

## Storage / Validation Design

- `chapter_briefs.json` は章順を保持して保存する
- `scene_cards.json` は章番号と scene 番号の対応が崩れない形で保存する
- validation は必須 field、章番号整合、scene 番号整合を検証する
- chapter ごとの対応が崩れた場合は recover せず例外を返す

resume / rerun では、既存 artifact を再利用する際にも同じ validation を通す。

## Error Handling

失敗は早く、明確に検出する。

最低限、次の異常系を明示的に扱う。

- `chapter_plan` はあるが `chapter_briefs` がない
- `chapter_briefs` はあるが `scene_cards` がない
- `chapter_briefs` の章数と `chapter_plan` の章数が一致しない
- `scene_cards` の `chapter_number` が対応する brief と一致しない
- scene が 0 件の章が含まれる
- 本文生成時に対象章の brief または scene cards が欠落している

これらは暗黙補完せず、actionable なエラーメッセージで止める。

## Testing Strategy

最低限必要な tests は次のとおりとする。

- schema test: `chapter_briefs` / `scene_cards` の required field と validation を固定する
- storage test: 保存と再読込で章順、章番号、scene 番号対応が崩れないことを確認する
- pipeline test: 正常系で `chapter_briefs` と `scene_cards` が生成され、`chapter_drafts` が両方を受け取ることを確認する
- fail-fast test: 欠落 artifact、章番号不整合、scene 欠落で明確に失敗することを確認する
- docs sync test: pipeline 順序と artifact 一覧が docs / tests で一致していることを確認する

テスト名や fixture は、初学者でも意図が追える具体名にする。

## 期待される効果

- 章の成功条件が artifact として固定される
- scene ごとの出口状態が定義され、本文生成の drift を減らせる
- 10 万字超の長編で、章の比重と転換密度を章単位で制御しやすくなる
- 後続の `canon_ledger`、`progress_report`、`replan_history` を自然に接続できる

## 非目標

- この段階では長期記憶そのものは導入しない
- この段階では自律判断 policy までは導入しない
- この段階では既存の quality system を大規模に置き換えない

## 実装時の注意

- 既存の `story_bible` 導入済み boundary を壊さない
- `chapter_plan` に brief / scene の責務を混ぜ込まない
- README、ROADMAP、TASKS の pipeline 順序と artifact 一覧を同期する
- 既存の chapter 1 互換 artifact を壊さない
