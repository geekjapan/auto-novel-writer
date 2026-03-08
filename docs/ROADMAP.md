# ROADMAP

## Goal

CLI から小説プロジェクトを作成し、章単位・作品単位で  
`生成 → 検査 → 再実行 → 改稿 → 要約 → 公開用成果物出力`  
までを再開可能に回せる、小説執筆パイプラインを育てる。

このソフトウェアの目標は「高性能な本文生成器」ではなく、**作品制作の制御基盤**をつくることにある。

## Current State

- CLI から `theme`、`genre`、`tone`、`target_length` を受け取り、`project_id` つきの project/run 管理ができる
- `story_input → loglines → characters → three_act_plot → chapter_plan → chapter_drafts` の生成フローがある
- chapter plan 全件に対して draft / revised draft を生成し、全章 artifact を保存できる
- continuity check と quality report により、構造不整合、POV 一貫性、章長バランス、キャラクター継続性を評価できる
- rerun policy、bounded revise loop、resume / rerun、history / diff metadata 保存がある
- `project_manifest.json` と `manifest` により、project/run の状態復元と run 比較ができる
- `story_summary.json`、`project_quality_report.json`、`publish_ready_bundle.json` を生成できる
- `rerun-chapter` は任意章で動く
- `best_run` には comparison metrics、selection reason、long-run status が保存される
- `publish_ready_bundle.json` は `schema_version=1.0` の固定 contract を持つ

## 現在地の整理

実装済みなのは、**全章生成・再開・再実行・改稿・作品単位成果物出力までの基盤**です。  
次に必要なのは新しい生成段を増やすことではなく、**運用時に状態を見やすくし、contract を検証し、長編運用の制御を外から扱えるようにすること**です。

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

### M10. 仕様語彙と artifact contract の固定

chapter 配列ベースの内部正本、chapter 1 互換 artifact、publish-ready bundle contract の用語と責務は docs / manifest / tests で固定済み。

### M11. 章単位制御の外部仕様一般化

`rerun-chapter` は任意章に対応し、対象章の rerun / revise / summary 系 artifact を更新できる。

### M12. 作品単位評価と選抜の強化

`run_candidates` と `best_run` に comparison metrics と selection reason を保存し、CLI でも current run と best run の差分を確認できる。

### M13. 長編安定化の初期整備

`long_run_status` に停止理由、予算、resume guidance を保存し、`publish_ready_bundle.json` の contract も固定済み。

## 現在の本命

### M14. 運用観測性の強化

目的:
生成を回す前に、project と run の状態を**読み取り専用で確認できる**ようにする。

完了条件:

- `project_manifest.json` を読むだけの status 系 CLI がある
- `current_run` / `best_run` / `chapter_statuses` / `long_run_status` を再実行なしで確認できる
- 章別の issue 数、rerun 回数、revise 回数を人間が追いやすい

## 次のマイルストーン

### M15. artifact schema 検証

目的:
manifest と publish bundle の contract を docs 上の説明だけでなく、保存時・読込時の検証として扱えるようにする。

完了条件:

- `project_manifest.json` と `publish_ready_bundle.json` の validator がある
- schema/version 不整合を actionable なエラーとして出せる
- compatibility layer と canonical state の境界が validator 上でも明確になる

### M16. 長編運用ポリシーの外部化

目的:
長編向け stop condition / retry policy / rerun budget をコード内固定値から運用設定へ寄せる。

完了条件:

- rerun policy の主要閾値を CLI または設定ファイルから与えられる
- 実行時に使った policy snapshot を manifest に保存できる
- 予算切れや停止条件を project 単位で比較できる

### M17. run 比較と採用フローの強化

目的:
複数 run の比較と `best_run` 採用を、CLI 出力だけでなく downstream 利用できる成果物として扱う。

完了条件:

- 機械可読な run comparison summary を保存できる
- 人間レビュー後に `best_run` を明示的に採用または固定できる
- 自動選抜と人間選抜の境界が docs / manifest で明確になる

### M18. 公開成果物 bundle の強化

目的:
`publish_ready_bundle.json` を比較・公開・変換の起点として扱えるようにする。

完了条件:

- `sections` の内容契約が固定される
- bundle の downstream 利用前提が docs / tests で説明される
- 将来の Markdown / EPUB 変換に繋がる最小 contract が整う

## Sequencing Rationale

- まず M14 で「今どの run がどういう状態か」を安全に読めるようにする
- 次に M15 で artifact contract を validator と versioning で守る
- その後 M16 で長編運用ポリシーを外から調整できるようにする
- さらに M17 で run 比較と採用フローを成果物として扱う
- 最後に M18 で publish-ready bundle を downstream 前提で固める

## Roadmap Notes

- README は「現状できること」
- ROADMAP は「どこへ進むか」
- TASKS は「次に何を実装するか」
- 実装順序の正本は `docs/TASKS.md`
- docs では `run_candidates` / `best_run` / `chapter_statuses` / `chapter_histories` / `artifact_contract` / `long_run_status` の語を固定する

この3つは役割を分けて保守する。
