# ROADMAP

## Goal

短編小説向けの CLI パイプライン MVP を、段階的に安全拡張できる状態で育てる。

## Current State

- CLI から `story_input` を受け取り、logline から chapter 1 draft まで一連実行できる
- `mock` / `openai` の LLM クライアント切替がある
- artifact は JSON / YAML で保存できる
- continuity check、rerun policy、chapter 1 revise が入っている
- 内部データ構造は `chapter_drafts` / `revised_chapter_drafts` を持ち、複数章対応の土台がある
- 外部仕様と保存成果物はまだ chapter 1 中心

## Milestones

### M1. Internal multi-chapter foundation

目的:
chapter 1 固定の内部実装を、複数章へ無理なく広げられる形にそろえる。

完了条件:

- chapter draft 生成が章番号ループで動く
- revise 処理が任意章を対象にできる
- storage と manifest が章配列中心でも一貫する
- chapter 1 向けの既存出力は後方互換を維持する

### M2. Resume and selective rerun

目的:
失敗や試行錯誤を前提に、途中成果物から安全に再開できるようにする。

完了条件:

- 既存 artifact を読み込んで途中再開できる
- フェーズ単位の再実行ができる
- rerun の記録が manifest で追える

### M3. Stronger provider boundary

目的:
Mock 実装と OpenAI 実装を同じ契約で保ち、検証しやすくする。

完了条件:

- provider ごとの入出力契約が明文化されている
- OpenAI 応答の構造検証が強化されている
- provider 依存テストと provider 非依存テストが分離されている

### M4. Story quality loop

目的:
生成するだけでなく、評価と改善の反復を導入する。

完了条件:

- quality check フェーズが追加される
- revise が continuity 以外の観点も扱える
- 改善前後の差分が成果物として残る

## Roadmap Notes

- 直近は M1 を最優先とする
- 広い再設計より、1 タスクずつ安全に前進する
- GitHub では `docs/TASKS.md` の項目を基準に issue / PR を対応づける
