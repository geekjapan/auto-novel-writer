# auto-novel-writer

短編小説向けの創作パイプラインMVPです。CLIからテーマを与えると、発想から第1章草稿までを5フェーズで生成し、その後に continuity check を実行して、各成果物を保存します。

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

## 実行方法

### 推奨実行手順

インストール後はエントリポイント経由で実行します。既定プロバイダは `mock` で、生成完了後に continuity check も自動実行されます。

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

### モック実装と OpenAI 実装の切替

- モック実装: `--provider mock` または省略
- OpenAI 実装: `--provider openai`
- OpenAI 利用時の必須環境変数: `OPENAI_API_KEY`
- OpenAI 利用時の追加依存: `openai`

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
8. `manifest`

## Continuity Check

continuity check はルールベースで成果物間の構造的不整合候補を洗い出します。面白さ評価ではなく、最低限の整合性確認が目的です。

参照する成果物:

- `logline`
- `characters`
- `three_act_plot`
- `chapter_plan`
- `chapter_1_draft`

出力ファイル:

- `continuity_report.json`

主なチェック項目:

- `missing_fields`
- `character_name_mismatches`
- `plot_to_plan_gaps`
- `plan_to_draft_gaps`
- `length_warnings`

実行方法:

- 通常の `novel-writer ...` 実行に continuity check が含まれます
- 追加オプションなしで `continuity_report.json` が出力されます

## Re-run Policy

continuity check 後は `issue_counts` を見て重大度を判定し、必要なら生成を 1 回だけ再実行します。判定ルールは [rerun_policy.py](D:/dev/auto-novel-writer/src/novel_writer/rerun_policy.py) の定数として分離しています。

制御フロー:

- `low`: 警告のみ。生成結果をそのまま採用
- `medium`: `chapter_1_draft` を再生成
- `high`: `chapter_plan` から `chapter_1_draft` まで再生成

記録:

- 最終判定は `continuity_report.json` の `severity`, `recommended_action`, `weighted_score` に保存
- 再実行履歴は `manifest` の `rerun_history` に保存

## 既知の限界

- continuity check はルールベースのため、比喩や長い因果関係の理解にはまだ弱いです
- plot と summary の判定は主要語の反映率を見るため、短すぎる文や抽象度の高い文では揺れます
- 名前検出は一般的なフルネーム表記を優先して誤検知を抑えていますが、あだ名、単名、特殊な表記には弱いです

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

## 次の改善候補

- OpenAI レスポンスを JSON schema ベースでより厳密に検証する
- 生成対象を第1章だけでなく全章草稿まで拡張する
- フェーズごとの再実行や途中再開をサポートする
- 生成物の評価・リライトフェーズを追加する
