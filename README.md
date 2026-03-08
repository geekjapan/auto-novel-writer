# auto-novel-writer

短編小説向けの創作パイプラインMVPです。CLIからテーマを与えると、発想から第1章草稿までを5フェーズで生成し、各成果物を `JSON` または `YAML` で保存します。

## 実装計画

1. `src/novel_writer` に CLI、パイプライン、保存層、スキーマ、LLMクライアントを分離して実装する
2. まずは `mock` プロバイダで全フローを動かし、OpenAI クライアントは任意利用の形で分離する
3. `tests/` に最低限の自動テストを追加し、README にセットアップ・実行例・改善候補をまとめる

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

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

YAML出力を使いたい場合だけ、追加で `PyYAML` を入れてください。

```bash
pip install PyYAML
```

OpenAI プロバイダを使う場合は、さらに `openai` パッケージを入れて環境変数を設定します。

```bash
pip install openai
set OPENAI_API_KEY=your_api_key
```

## 実行方法

既定ではモック実装で動作します。

```bash
novel-writer ^
  --theme "喪失と再生" ^
  --genre "ミステリ" ^
  --tone "静かで切ない" ^
  --target-length 8000 ^
  --output-dir data\sample_run
```

モジュール実行でも同じです。

```bash
python -m novel_writer ^
  --theme "秘密" ^
  --genre "ファンタジー" ^
  --tone "希望を残す" ^
  --target-length 6000
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

追加依存なしで標準ライブラリの `unittest` で実行できます。

```bash
python -m unittest discover -s tests -v
```

## 次の改善候補

- OpenAI レスポンスを JSON schema ベースでより厳密に検証する
- 生成対象を第1章だけでなく全章草稿まで拡張する
- フェーズごとの再実行や途中再開をサポートする
- 生成物の評価・リライトフェーズを追加する
