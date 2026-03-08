# ROADMAP

## Goal

CLI から小説プロジェクトを作成し、章単位・作品単位で  
`生成 → 検査 → 再実行 → 改稿 → 要約 → 公開用成果物出力`  
までを再開可能に回せる、小説執筆パイプラインを育てる。

このソフトウェアの目標は「高性能な本文生成器」ではなく、**作品制作の制御基盤**をつくることにある。

## Current State

- CLI から `theme`、`genre`、`tone`、`target_length` を受け取り、`project_id` つきの run 管理もできる
- `story_input → loglines → characters → three_act_plot → chapter_plan → chapter_drafts` の生成フローがある
- chapter plan 全件に対して draft / revised draft を生成し、全章 artifact を保存できる
- continuity check と quality report により、構造不整合、POV 一貫性、章長バランス、キャラクター継続性を評価できる
- rerun policy、bounded revise loop、resume / rerun、history / diff metadata 保存がある
- `project_manifest.json` と `manifest` により、project/run の状態復元ができる
- `story_summary.json`、`project_quality_report.json`、`publish_ready_bundle.json` を生成できる
- 一方で、CLI や互換 artifact には chapter 1 前提の外部仕様がまだ残っている

## 仕様上の柱

### 1. 入力と project 管理

- project 単位で run を継続管理できること
- CLI から最小入力で開始できること
- manifest から再開できること

### 2. 全章生成

- chapter plan 全件をループして草稿を生成できること
- 章ごとの内部状態が正本であること
- chapter 1 互換 artifact は補助層として維持すること

### 3. 品質管理と制御

- 章別 continuity / quality 検査
- rerun policy による再生成制御
- bounded revise loop
- 履歴と diff の保存

### 4. 作品単位成果物

- story summary / synopsis
- project-wide quality report
- publish-ready bundle
- run 比較と best candidate selection

## 完了済みの段階

### M1. 全章草稿生成の基盤

全章 `chapter_plan` と `chapter_{n}_draft` / `revised_chapter_{n}_draft` を扱う土台は実装済み。

### M2. resume / rerun の基盤

checkpoint と manifest を使った resume、phase rerun は実装済み。

### M3. 品質検査の基盤

continuity check、quality report、POV / 章長 / キャラクター継続性の評価は実装済み。

### M4. 改稿制御の基盤

bounded revise loop、停止条件、diff metadata 保存は実装済み。

### M5. project / run 管理の基盤

`project_id`、project manifest、run candidate、best run の基盤は実装済み。

### M6. 最終成果物の基盤

`story_summary.json`、`project_quality_report.json`、`publish_ready_bundle.json` の生成は実装済み。

## 現在の本命

### M10. 仕様語彙と artifact contract の固定

目的:
README / ROADMAP / TASKS / manifest / テストの間で、何が正本で何が互換層かをぶらさずに固定する。

完了条件:

- 「制作パイプライン」であることが docs 全体で一貫する
- chapter 配列ベースの内部状態が正本だと明記される
- chapter 1 互換 artifact の位置づけが文書とテストで一致する
- publish-ready bundle と project/run manifest の責務が説明できる

### M11. 章単位制御の外部仕様一般化

目的:
内部で全章対応している rerun / revise / history を、CLI と外部仕様でも任意章へ広げる。

完了条件:

- `rerun-chapter` が任意章に対応する
- 対象章だけを安全に再実行できる
- 章単位操作が manifest と project manifest で追える

### M12. 作品単位評価と選抜の強化

目的:
複数 run の比較と best candidate 選抜を、運用可能な精度へ強化する。

完了条件:

- best run の根拠を説明できる
- comparison 用 metadata が整理される
- project-level quality report が比較運用に耐える

### M13. 長編安定化

目的:
中編・長編でも途中停止 / 再開しながら安定生成できるようにする。

完了条件:

- stop condition と retry policy が長編向けに整理される
- rerun コストを制御できる
- 長編時でも chapter / project の状態追跡が崩れない

## Sequencing Rationale

- まず M10 で仕様語彙と artifact contract を固定し、docs と実装のぶれを止める
- 次に M11 で chapter 単位制御を外部仕様でも完成させる
- その後 M12 で run 比較と選抜を強める
- 最後に M13 で長編安定化へ進む

## Roadmap Notes

- README は「現状できること」
- ROADMAP は「どこへ進むか」
- TASKS は「次に何を実装するか」

この3つは役割を分けて保守する。
