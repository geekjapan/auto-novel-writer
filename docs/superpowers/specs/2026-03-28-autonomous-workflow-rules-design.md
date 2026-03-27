# Autonomous Workflow Rules Design

## Summary

本 spec は、`AGENTS.md` と `docs/CODEX_WORKFLOW.md` を正本として見直し、
Codex がこの repository で数時間単位の連続稼働を行いやすくするための
運用ルール変更を定義する。

狙いは次の 3 点である。

1. ユーザー確認を必要最小限に寄せる
2. 独立作業ではサブエージェント活用を標準化する
3. fail-fast と停止条件は維持しつつ、自律継続を強める

この変更は、既存の artifact contract や CLI 仕様を変えるものではなく、
Codex の作業手順と判断基準を明確化する docs 更新である。

## Problem Statement

現状の `AGENTS.md` と `docs/CODEX_WORKFLOW.md` には、自律継続の方向性はあるが、
長時間の連続稼働を前提にした運用基準が十分に明文化されていない。

特に不足しているのは次の点である。

- どの場面でユーザー確認を省略してよいか
- どの場面でサブエージェントを積極利用すべきか
- task 完了後にどの粒度で checkpoint を切り、どこまで自動継続するか
- 「おすすめを選ぶ」と明示された場合の扱い

この不足により、実装可能な task でも不要に停止したり、
並列化できる作業を主 agent が直列処理して効率を落とす余地がある。

## Goals

- `TASKS.md` 駆動の実装ループを、停止条件に当たるまで継続する前提に寄せる
- 独立した読み取り、実装、検証、docs 同期をサブエージェントへ委譲しやすくする
- ユーザー確認は、仕様判断、互換性破壊、外部方針判断などの高リスク時に限定する
- 1 task ごとに tests、docs、task 状態更新、commit までを完了させる checkpoint を明示する

## Non-Goals

- artifact schema や CLI contract の変更
- 停止条件そのものの撤廃
- すべての task を強制的に並列化すること
- ユーザーの明示指示を無視して自律実行を優先すること

## Design

### 1. Autonomous Execution Baseline

`AGENTS.md` と `docs/CODEX_WORKFLOW.md` の両方で、
Codex は通常 task の実装においてユーザー確認を待たずに前進することを明記する。

基準は次のとおりである。

- `In Progress` の task は、停止条件に該当しない限り完了まで進める
- task 完了後は `Ready` 先頭へ自動で進む
- `Ready` が空なら、自律起票ルールに従って次の最小子タスクを追加して続行する
- ユーザーが `おすすめで`, `続けて`, `可能な限り止まらずに` と指示した場合、
  推奨案を採用して継続してよい

### 2. User Confirmation Policy

ユーザー確認を求める条件を、既存の停止条件へより強く寄せる。

確認が必要なのは、次のような場面に限定する。

- docs / code / tests を見ても仕様判断が一意に決まらない
- 既存 CLI、artifact contract、schema version、保存形式の互換性を壊す可能性がある
- rename / remove / migration のような広範囲変更が必要
- 外部 API 利用方針、品質評価軸、生成仕様のようなプロダクト判断が必要
- 既存不具合と今回変更のどちらに起因するか切り分けできない失敗がある

逆に、次のような場面では確認なしに進める。

- `TASKS.md` に明確な受け入れ条件がある通常 task
- docs 同期、tests 追加、validator 追加などの低リスクな継続作業
- 既存方針に沿った小さなリファクタ
- ユーザーが推奨案の自動採用を許可している場合の分岐選択

### 3. Subagent-First Parallelism

2 件以上の独立した作業が見えた時点で、サブエージェント活用を優先検討する。

対象例:

- 実装と docs 同期が別ファイル群に分かれる場合
- schema / storage / tests のように責務が分離されている場合
- 読み取り調査を並列で進められる場合
- 検証を裏で走らせながら主 agent が実装できる場合

主 agent は次を担う。

- task の切り分け
- サブエージェントへの ownership 指定
- 競合のない統合
- 最終的な検証、docs 整合、commit

無理に分割しない条件も明記する。

- 同一ファイルの狭い変更で競合しやすい場合
- 次の 1 手が前段の結果に強く依存する場合
- task 自体が小さく、並列化コストが上回る場合

### 4. Long-Running Checkpoint Model

数時間の連続稼働を前提に、停止ではなく checkpoint を標準化する。

checkpoint は task 完了単位とし、最低限次をそろえる。

- 実装
- 必要な tests
- 必要な docs 更新
- `docs/TASKS.md` の状態更新
- 小さな commit

この checkpoint が終わったら、次 task へ継続する。
ユーザー応答待ちを既定の停止点にしない。

### 5. Reporting Style

途中報告は、作業を止めるためではなく進捗共有のために行う。

報告方針は次のとおりである。

- 短く、現在 task と次の行動が分かる内容にする
- サブエージェントへ委譲した場合は、何を並列化したかを簡潔に示す
- 停止条件に該当しない限り、報告後も作業は継続する

## Required Doc Changes

### `AGENTS.md`

追加または強化する内容:

- 作業ルールに「通常 task ではユーザー確認を待たずに続行する」旨を追加する
- 推奨案の自動採用条件を明記する
- サブエージェント運用の専用節を追加する
- 停止条件に該当しない限り停止しないことを、自律継続ルールとして強化する

### `docs/CODEX_WORKFLOW.md`

追加または強化する内容:

- `Standard Loop` にサブエージェント活用と長時間連続実行の流れを組み込む
- `Long-Running Execution` 節を追加し、checkpoint 単位を定義する
- `When To Use Subagents` 節を追加し、並列化判断基準を明記する
- `When To Ask For Human Direction` を、実質的な高リスク判断へ限定する形で明確化する

## Risks And Mitigations

### Risk: 不要な自律進行で互換性事故を起こす

Mitigation:
停止条件は維持し、互換性破壊や仕様不確定時は従来どおり停止する。

### Risk: サブエージェント乱用で競合や手戻りが増える

Mitigation:
独立性が高い task に限定し、同一ファイルへの競合しやすい編集は主 agent が持つ。

### Risk: ユーザーが途中で確認したい内容が見えにくくなる

Mitigation:
途中報告は継続しつつ、停止ではなく進捗共有として短く行う。

## Testing And Verification

この変更は docs 中心のため、最低限次を確認する。

- `AGENTS.md` と `docs/CODEX_WORKFLOW.md` の記述が相互に矛盾しない
- `AGENTS.md` の停止条件と、新しい自律実行ルールが両立している
- `docs/TASKS.md` の task 駆動ルールと、新しい workflow 記述が整合している

## Rollout

1. `AGENTS.md` を更新する
2. `docs/CODEX_WORKFLOW.md` を更新する
3. 必要なら `README.md` ではなく `docs` 間参照だけを調整する
4. docs の整合性を確認して commit する
