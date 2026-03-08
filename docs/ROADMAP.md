# ROADMAP

## Goal

人手の往復を最小化しながら、プロット作成から全章ドラフト、検査、改稿、再開実行までを自動で回せる「全自動小説執筆システム」を段階的に育てる。

## Current State

- CLI から `story_input` を受け取り、logline から chapter 1 draft まで一連実行できる
- `mock` / `openai` の LLM クライアント切替がある
- artifact は JSON / YAML で保存できる
- continuity check、rerun policy、chapter 1 revise が入っている
- 内部データ構造は `chapter_drafts` / `revised_chapter_drafts` を持ち、複数章対応の土台がある
- 外部仕様と保存成果物はまだ chapter 1 中心

## Milestones

### M1. Multi-Chapter Generation Foundation

目的:
chapter 1 固定の実装を外し、全章を同じ生成パイプラインで扱えるようにする。

完了条件:

- chapter draft 生成が章番号ループで動く
- revise/save が任意章を対象にできる
- manifest と storage が章配列中心でも一貫する
- chapter 1 向けの既存出力は後方互換を維持する

### M2. Resume And Selective Rerun

目的:
途中成果物を再利用し、止まってもやり直しても作業を前進できるようにする。

完了条件:

- 既存 artifact を読み込んで途中再開できる
- フェーズ単位の再実行ができる
- rerun の記録が manifest で追える
- CLI から再開実行と再実行起点を指定できる

### M3. Multi-Layer Quality Checks

目的:
整合性だけでなく、文体、視点、長さ配分、章間因果、人物の一貫性も機械検査できるようにする。

完了条件:

- continuity 以外の quality check が追加される
- 問題種別ごとに regenerate / revise の推奨が分かれる
- quality report が artifact として保存される

### M4. Automated Revision Loop

目的:
単発改稿ではなく、停止条件付きの反復改稿で品質を底上げする。

完了条件:

- revise を複数回回せる
- 反復上限回数と停止条件がある
- 改稿前後の差分と判断理由が履歴に残る

### M5. Project-Level Writing Management

目的:
単発 CLI 実行から、作品単位の継続管理へ進める。

完了条件:

- 作品 ID ごとに設定、進捗、成果物、履歴を管理できる
- CLI から新規作品、再開、全体生成、章単位再生成ができる
- project manifest から現在状態を復元できる

### M6. Autonomous Agent Development Loop

目的:
システム開発自体を、Codex が GitHub と連動しながら小さく安全に前進できる状態にする。

完了条件:

- `docs/TASKS.md` と GitHub issue / PR の粒度がそろっている
- Codex が 1 タスクずつ実装、テスト、docs 更新、小コミットまで進められる
- block 時は `docs/BLOCKED.md` に停止理由が残る

### M7. Chapter-Wide Continuity And Revision

目的:
chapter 1 中心の continuity / rerun / revise を、全章へ一般化する。

完了条件:

- continuity check を任意章に適用できる
- rerun policy を章単位で実行できる
- revise を任意章へ適用できる
- manifest に章ごとの検査・再実行・改稿履歴が残る
- chapter 1 向けの既存互換を維持する

### M8. Story-Level Evaluation And Selection

目的:
作品全体の品質評価と、複数候補からの選抜を可能にする。

完了条件:

- 全章を通した summary / synopsis を生成できる
- project-wide quality report を生成できる
- 主題整合、伏線回収、視点維持、章配分を評価できる
- 複数 run を比較し best candidate を選べる
- 比較結果が manifest / project metadata に保存される

### M9. Long-Form Novel Orchestration

目的:
短編MVPから中編・長編へ拡張し、章ループで安定生成できるようにする。

完了条件:

- 全章を順に生成・改稿・評価できる
- 長編でも中断・再開できる
- 全体要約と全体再検査が自動で走る
- 長編向け retry / stop condition を持つ
- publish-ready artifact bundle を出力できる

## Sequencing Rationale

- 先に M1 と M2 を固めないと、全章生成も自動再開も不安定になる
- M3 と M4 は、基盤ができてから品質改善を安全に積み上げる段階
- M5 で「作品を継続的に育てる」運用へ進める
- M6 は開発運用そのものを半自動化する土台
- M7 で chapter 1 固定の品質制御を全章へ広げる
- M8 で作品単位の評価と候補選抜を扱えるようにする
- M9 で中編・長編向けの安定オーケストレーションへ進む

## Roadmap Notes

- 直近は M1 を最優先とする
- 広い再設計より、1 タスクずつ安全に前進する
- GitHub では `docs/TASKS.md` の項目を基準に issue / PR を対応づける
- 現在は M1〜M6 が一巡し、次の本命は M7 の全章一般化である
