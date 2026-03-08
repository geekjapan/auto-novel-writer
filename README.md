# auto-novel-writer

`auto-novel-writer` は、CLI ベースの小説制作パイプラインです。  
目指すのは「一発で完成原稿を出す本文生成器」ではなく、**小説制作を工程分解し、章単位・作品単位で再開可能に回せる制御基盤**です。

現在は、CLI 入力から `story_input`、`loglines`、`characters`、`three_act_plot`、`chapter_plan`、全章 draft、全章 revised draft、quality 系 artifact、project/run 管理用 manifest までを順に生成できます。

## ソフトウェアの目的

- CLI から小説プロジェクトを作成する
- 章単位・作品単位で `生成 → 検査 → 再実行 → 改稿 → 要約 → 公開用成果物出力` を回す
- 途中停止しても、artifact と manifest から resume / rerun できるようにする
- 短編から長編まで、品質管理つきで安定生成できる土台をつくる

## 仕様の中心

このソフトウェアの中心は、プロンプト単体ではなくパイプラインです。  
正本となる内部状態は、`chapter_drafts` / `revised_chapter_drafts` のような**章配列ベースの状態**と、`project_manifest.json` / `manifest` のような**project/run 管理情報**です。

当面は後方互換のため chapter 1 互換 artifact も維持しますが、設計の中心は全章状態です。

## 仕様の6層

### 1. 入力仕様

最低限、CLI から以下を受け取ります。

- `theme`
- `genre`
- `tone`
- `target_length`

継続管理が必要な場合は `project_id` を指定し、project 単位の run layout を使います。

### 2. 生成仕様

最低限、以下の順で生成します。

1. `story_input`
2. `loglines`
3. `characters`
4. `three_act_plot`
5. `chapter_plan`
6. `chapter_drafts`

`chapter_plan` は全件ループで処理し、各章の `chapter_{n}_draft` を保存します。

### 3. 品質管理仕様

生成後は continuity check と quality report を走らせます。  
構造不整合だけでなく、少なくとも以下を扱います。

- POV 一貫性
- 章長バランス
- キャラクター継続性
- plan と draft の対応

### 4. 再実行・改稿仕様

問題があれば rerun policy に従って再生成し、その後 bounded loop で改稿します。  
停止条件、再実行履歴、改稿履歴、diff metadata を manifest に残します。

### 5. project/run 管理仕様

単発実行だけでなく、`project_id` ごとに run を管理します。

- resume
- rerun
- chapter 単位操作
- `project_manifest.json` と `manifest` からの状態復元

を前提にしています。

### 6. 最終成果物仕様

本文だけでなく、以下を最終成果物として出力します。

- `story_summary.json`
- `project_quality_report.json`
- `publish_ready_bundle.json`

これらは公開、比較、選抜、後続工程での利用を想定した artifact です。

## 現在実装済みの主要機能

- `mock` / `openai` の LLM プロバイダ切替
- 全章 `chapter_plan` と全章 `chapter_{n}_draft` 生成
- 全章 `revised_chapter_{n}_draft` 保存
- continuity report と quality report の生成
- rerun policy による再生成制御
- bounded loop による改稿と diff metadata 保存
- `manifest` の checkpoint / history 保存
- `project_id` 単位の run layout と `project_manifest.json`
- `story_summary.json`、`project_quality_report.json`、`publish_ready_bundle.json`
- run candidates と `best_run` の記録

## chapter 1 互換 artifact と全章状態

内部処理は全章対応ですが、既存利用者向けに chapter 1 互換 artifact を残しています。

- `05_chapter_1_draft.json|yaml`
- `revised_chapter_1_draft.json|yaml`
- `continuity_report.json`

`chapter_1_draft` と `revised_chapter_1_draft` は内部配列先頭要素の互換ミラーです。  
章ごとの履歴や検査結果は `manifest` の以下を参照します。

- `continuity_history`
- `rerun_history`
- `revise_history`
- `chapter_histories`

## セットアップ

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e .
```

YAML artifact を使う場合:

```bash
python -m pip install PyYAML
```

OpenAI プロバイダを使う場合:

```bash
python -m pip install openai
set OPENAI_API_KEY=your_api_key
```

## 基本実行

```bash
novel-writer ^
  --theme "喪失と再生" ^
  --genre "ミステリ" ^
  --tone "静かで切ない" ^
  --target-length 8000 ^
  --output-dir data\sample_run
```

`python -m novel_writer` でも実行できます。

## resume / rerun

既存成果物を使って途中から再開できます。

```bash
novel-writer --resume-from-output-dir data\sample_run
novel-writer --resume-from-output-dir data\sample_run --rerun-from chapter_drafts
```

現在の step 順序:

1. `story_input`
2. `loglines`
3. `characters`
4. `three_act_plot`
5. `chapter_plan`
6. `chapter_drafts`
7. `continuity_report`
8. `quality_report`
9. `revised_chapter_drafts`
10. `story_summary`
11. `project_quality_report`
12. `publish_ready_bundle`

## project-level run

`--project-id` を指定すると、作品単位の run layout を使います。

```bash
novel-writer ^
  --theme "境界" ^
  --genre "SF" ^
  --tone "ビター" ^
  --target-length 5000 ^
  --project-id "my-story-01"
```

既定では成果物を `data/projects/my-story-01/runs/latest_run` に保存し、  
`data/projects/my-story-01/project_manifest.json` に current run、run candidates、best run を保存します。

専用コマンド:

```bash
novel-writer create-project --project-id "my-story-01" --theme "境界" --genre "SF" --tone "ビター" --target-length 5000
novel-writer resume-project --project-id "my-story-01"
novel-writer rerun-chapter --project-id "my-story-01" --chapter-number 1
```

`rerun-chapter` は現状では chapter 1 互換運用のため `--chapter-number 1` のみ対応です。

## 主な出力物

- `story_input`
- `01_loglines`
- `02_characters`
- `03_three_act_plot`
- `04_chapter_plan`
- `05_chapter_1_draft`
- `chapter_{n}_draft`
- `continuity_report.json`
- `quality_report.json`
- `revised_chapter_1_draft`
- `revised_chapter_{n}_draft`
- `story_summary.json`
- `project_quality_report.json`
- `publish_ready_bundle.json`
- `manifest`

`manifest` には以下も保存します。

- `checkpoints`
- `current_step`
- `completed_steps`
- `continuity_history`
- `rerun_history`
- `revise_history`
- `chapter_histories`
- `long_run_status`

## 現時点でできること

- 章計画に基づく全章 draft 生成
- 章別 continuity / quality 検査
- rerun policy による再実行
- bounded revise loop
- 作品全体 summary / synopsis 生成
- project 単位の resume / rerun
- publish-ready bundle 出力

## 既知の限界

- chapter 単位 rerun の CLI はまだ完全一般化されていません
- continuity report は互換上 chapter 1 基準の artifact を維持しています
- quality report は構造評価中心で、文学的評価は限定的です
- 長編向け stop condition はあるものの、長編運用はまだ安定化段階です
- publish-ready bundle の schema は今後さらに明文化する余地があります

## 内部設計原則

- 正本は chapter 配列ベースの内部状態
- chapter 1 互換 artifact は当面維持
- manifest に履歴を残す
- `mock` / `openai` を切替可能
- artifact は JSON / YAML で保存する
- secrets と生成成果物は repo に push しない運用を前提にする

## 最終到達像

- 中編・長編でも途中停止 / 再開できる
- 全章を順に生成・検査・改稿できる
- 複数 run を比較し best candidate を選べる
- publish-ready bundle まで一括出力できる

## テスト

```bash
python -m unittest discover -s tests -v
```

## 開発ドキュメント

- `docs/ROADMAP.md`: 現在地と次のマイルストーン
- `docs/TASKS.md`: 直近の実装キュー
- `docs/CODEX_WORKFLOW.md`: 1 タスクずつ進める標準手順
- `docs/GITHUB_CONVENTIONS.md`: issue / PR / branch / commit の運用
- `docs/BLOCKED.md`: ブロック時の記録テンプレート
