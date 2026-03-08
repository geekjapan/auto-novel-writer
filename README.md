# auto-novel-writer

短編小説向けの創作パイプラインMVPです。CLIからテーマを与えると、発想から第1章草稿までを5フェーズで生成し、各成果物を `JSON` または `YAML` で保存します。

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

インストール後はエントリポイント経由で実行します。既定プロバイダは `mock` です。

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
7. `manifest`

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
