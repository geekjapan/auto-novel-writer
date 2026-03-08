# auto-novel-writer

短編小説向けの創作パイプラインMVPです。CLIから `theme`, `genre`, `tone`, `target_length` を受け取り、logline 生成から chapter plan 全件分の draft 生成までを順に実行し、その後に chapter 1 を対象とした continuity check、rerun policy、`revise_chapter_1` を適用して成果物を保存します。

## ディレクトリ構成

```text
.
├─ data/
├─ src/
│  └─ novel_writer/
├─ tests/
├─ pyproject.toml
└─ README.md
```

## セットアップ

推奨手順:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e .
```

補助ライブラリ:

```bash
python -m pip install PyYAML
```

OpenAI プロバイダを使う場合:

```bash
python -m pip install openai
set OPENAI_API_KEY=your_api_key
```

`.env*` や API キーなどの secrets、`data/` 配下の生成成果物は push しない運用を前提にしています。

## 実行方法

### 推奨実行手順

インストール後はエントリポイント経由で実行します。既定プロバイダは `mock` で、生成完了後に continuity check、必要に応じた rerun、chapter 1 の改稿まで自動実行されます。

```bash
novel-writer ^
  --theme "喪失と再生" ^
  --genre "ミステリ" ^
  --tone "静かで切ない" ^
  --target-length 8000 ^
  --output-dir data\sample_run
```

`python -m` でも実行できます。

```bash
python -m novel_writer ^
  --theme "秘密" ^
  --genre "ファンタジー" ^
  --tone "希望を残す" ^
  --target-length 6000
```

再開実行の例:

```bash
novel-writer --resume-from-output-dir data\sample_run
```

project 単位の run layout を使う例:

```bash
novel-writer ^
  --theme "境界" ^
  --genre "SF" ^
  --tone "ビター" ^
  --target-length 5000 ^
  --project-id "my-story-01"
```

この場合、既定では `data/projects/my-story-01/runs/latest_run` に成果物を保存し、`data/projects/my-story-01/project_manifest.json` に現在の run 情報を保存します。

project コマンドの例:

```bash
novel-writer create-project --project-id "my-story-01" --theme "境界" --genre "SF" --tone "ビター" --target-length 5000
novel-writer resume-project --project-id "my-story-01"
novel-writer rerun-chapter --project-id "my-story-01" --chapter-number 1
```

`rerun-chapter` は現時点では後方互換性のため chapter 1 のみを対象にします。

指定フェーズからの再実行例:

```bash
novel-writer --resume-from-output-dir data\sample_run --rerun-from chapter_drafts
```

### モック実装と OpenAI 実装の切替

- モック実装: `--provider mock` または省略
- OpenAI 実装: `--provider openai`
- OpenAI 利用時の必須環境変数: `OPENAI_API_KEY`
- OpenAI 利用時の追加依存: `openai`
- OpenAI 応答は受信後に想定 JSON shape を検証し、必須 key や型が崩れている場合はエラーにします

OpenAI 利用例:

```bash
novel-writer ^
  --theme "約束" ^
  --genre "青春ドラマ" ^
  --tone "軽やか" ^
  --target-length 7000 ^
  --provider openai ^
  --model gpt-4.1-mini
```

モックに戻す場合:

```bash
novel-writer ^
  --theme "喪失と再生" ^
  --genre "ミステリ" ^
  --tone "静かで切ない" ^
  --target-length 8000 ^
  --provider mock
```

YAML 出力例:

```bash
novel-writer ^
  --theme "継承" ^
  --genre "SF" ^
  --tone "ビター" ^
  --target-length 10000 ^
  --format yaml
```

## 出力フェーズ

以下の成果物を順番に保存します。

1. `story_input`
2. `01_loglines`
3. `02_characters`
4. `03_three_act_plot`
5. `04_chapter_plan`
6. `05_chapter_1_draft`
7. `continuity_report.json`
8. `quality_report.json`
9. `revised_chapter_1_draft`
10. `manifest`

`manifest` には、再開実行の土台として `checkpoints`, `current_step`, `completed_steps` も保存されます。

## Continuity Check

continuity check はルールベースで成果物間の構造的不整合候補を洗い出します。面白さ評価ではなく、最低限の整合性確認が目的です。

参照する成果物:

- `logline`
- `characters`
- `three_act_plot`
- `chapter_plan`
- `chapter_1_draft`

内部実装の continuity checker は `chapter_index` 指定で任意章を検査できる形に寄せていますが、現時点の pipeline 出力と互換 artifact は chapter 1 中心のままです。

出力ファイル:

- `continuity_report.json`

主なチェック項目:

- `missing_fields`
- `character_name_mismatches`
- `plot_to_plan_gaps`
- `plan_to_draft_gaps`
- `length_warnings`
- `pov_consistency_issues`
- `chapter_length_balance_warnings`
- `character_continuity_issues`
- `quality_report.json` には各問題種別ごとの `regenerate` / `revise` 推奨と全体推奨が保存されます

実行方法:

- 通常の `novel-writer ...` 実行に continuity check が含まれます
- 追加オプションなしで `continuity_report.json` が出力されます

## Re-run Policy

continuity check 後は `issue_counts` を見て重大度を判定し、必要なら生成を 1 回だけ再実行します。判定ルールは [rerun_policy.py](src/novel_writer/rerun_policy.py) の定数として分離しています。

制御フロー:

- `low`: 警告のみ。生成結果をそのまま採用
- `medium`: `chapter_1_draft` を再生成
- `high`: `chapter_plan` から `chapter_1_draft` まで再生成

内部実装では rerun 判定を章ごとに適用できる形に寄せていますが、互換 artifact と説明は chapter 1 を基準に維持しています。

記録:

- 最終判定は `continuity_report.json` の `severity`, `recommended_action`, `weighted_score` に保存
- 再実行履歴は `manifest` の `rerun_history` に保存

## Revise Chapter 1

continuity check と rerun の後に、`chapter_1_draft` を最小限の改稿ルールで整えます。入力として `story_input`, `chapter_plan`, `chapter_1_draft`, `continuity_report` を使い、`revised_chapter_1_draft` を保存します。

内部実装では改稿メソッドを `chapter_index` ベースに一般化してあり、将来は任意の章へ同じ改稿処理を広げられる構造です。現時点の CLI と保存成果物は後方互換性のため chapter 1 中心のまま維持しています。

また、内部データ構造として `chapter_drafts` と `revised_chapter_drafts` を導入しており、将来の複数章対応ではこの章番号付き保持構造を中心に拡張する想定です。現時点では chapter draft と revised draft は全章分を内部保持し、改稿判定も章ごとに行いますが、compatibility output は chapter index `0` を中心に維持しています。

改稿は最大 2 回までの bounded loop で実行します。改稿結果に変化がなくなった場合、または上限回数に達した場合にその章の改稿を停止します。

改稿ルール:

- `chapter_plan[0].purpose` に `summary` を寄せる
- 草稿本文の重複文を削減する
- 冗長な言い回しを短くし、文体を軽く整える

記録:

- 改稿結果は `revised_chapter_1_draft(.json|.yaml)` に保存
- 改稿履歴は `manifest` の `revise_history` に attempt 単位で保存し、各 attempt の before/after diff metadata も含みます

## 既知の限界

- continuity check はルールベースのため、比喩や長い因果関係の理解にはまだ弱いです
- plot と summary の判定は主要語の反映率を見るため、短すぎる文や抽象度の高い文では揺れます
- 名前検出は一般的なフルネーム表記を優先して誤検知を抑えていますが、あだ名、単名、特殊な表記には弱いです
- 改稿フェーズは局所的な整文に留まり、構成の大きな改善や高品質なリライトまでは行いません

## テスト

推奨手順:

```bash
python -m unittest discover -s tests -v
```

開発中に未インストール状態で直接ソースを試したい場合だけ、補助的に `PYTHONPATH=src` 相当を使えます。

```bash
$env:PYTHONPATH="src"
python -m unittest discover -s tests -v
```

## 開発フロー

Codex に継続実装を任せる前提の運用ドキュメントを `docs/` に置いています。

- [docs/ROADMAP.md](docs/ROADMAP.md): 現在のマイルストーンと到達順
- [docs/TASKS.md](docs/TASKS.md): 実装キュー。`In Progress / Ready / Done` で管理
- [docs/CODEX_WORKFLOW.md](docs/CODEX_WORKFLOW.md): Codex が 1 タスクずつ自律的に進める標準手順
- [docs/GITHUB_CONVENTIONS.md](docs/GITHUB_CONVENTIONS.md): issue / PR / branch の運用ルール

基本ルールは、`In Progress` の先頭 1 件だけを実装し、テスト後に `TASKS.md` を更新して小さくコミットすることです。GitHub ではこのタスク文言をそのまま issue / PR に対応づける想定です。

## 次の改善候補

- OpenAI レスポンスを JSON schema ベースでより厳密に検証する
- 生成対象を第1章だけでなく全章草稿まで拡張する
- フェーズごとの再実行や途中再開をサポートする
- 生成物の評価・リライトフェーズを追加する


