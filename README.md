# auto-novel-writer

`auto-novel-writer` は、CLI ベースで小説制作を進めるためのパイプラインです。
現在は、作品の入力から章構成、草稿、改稿、品質確認、再実行、公開用成果物までを順番に扱えます。

## いま使えること

- CLI から新しい小説プロジェクトを作成する
- 途中まで作った成果物から resume する
- 章単位で rerun する
- project 単位の status と run 比較を見る
- project 単位の `autonomy_level` (`manual` / `assist` / `auto`) の contract / save / status 表示は実装済みで、値に応じた behavior / control 分岐は次のステップで進める
- LLM プロバイダを `mock` / `openai` / `openai-compatible` / `lmstudio` / `ollama` から選ぶ

## 主な CLI フロー

### 1. 新規作成

```bash
novel-writer --theme "喪失と再生" --genre "ミステリ" --tone "静かで切ない" --target-length 8000 --output-dir data/sample_run
```

`python -m novel_writer` でも実行できます。

### 2. project 単位で管理する

```bash
novel-writer create-project --project-id "my-story-01" --theme "境界" --genre "SF" --tone "ビター" --target-length 5000
novel-writer resume-project --project-id "my-story-01"
novel-writer show-project-status --project-id "my-story-01"
novel-writer show-run-comparison --project-id "my-story-01"
novel-writer select-best-run --project-id "my-story-01" --run-name "latest_run"
novel-writer rerun-chapter --project-id "my-story-01" --chapter-number 2
```

`project_manifest.json` には project 単位の `autonomy_level` が保存され、`show-project-status` で現在値を確認できます。値に応じた制御分岐はまだ次段階の作業です。

### 3. 途中再開と rerun

```bash
novel-writer --resume-from-output-dir data/sample_run
novel-writer --resume-from-output-dir data/sample_run --rerun-from chapter_drafts
```

`--rerun-from chapter_drafts` は、保存済みの章向け素材を前提に chapter draft 以降をやり直します。必要な成果物が欠けている場合は fail fast で停止します。

## いまの制作フロー

現在のパイプラインは、次の流れで進みます。

1. 入力を受け取る
2. 作品全体の設計を作る
3. 章ごとの計画と執筆用素材を作る
4. 草稿を生成する
5. continuity と quality を確認する
6. 必要に応じて rerun / revise する
7. 作品要約や公開用成果物を出力する

## 主な出力物

- 草稿と改稿稿
- continuity / quality 系の確認結果
- project / run の管理情報
- 比較・選抜用の run summary
- 公開用の bundle

## セットアップ

```bash
python3 -m venv venv
source venv/bin/activate
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

OpenAI 互換 endpoint を使う場合:

```bash
python -m pip install openai
novel-writer --provider openai-compatible --base-url http://127.0.0.1:8080/v1 --api-key local-key --model your-model-name
```

LM Studio を使う場合:

```bash
python -m pip install openai
novel-writer --provider lmstudio --model local-model-name
```

LM Studio の既定接続先は `http://127.0.0.1:1234/v1` です。`--base-url` または `LMSTUDIO_BASE_URL` で上書きできます。

Ollama を使う場合:

```bash
python -m pip install openai
novel-writer --provider ollama --model llama3.1
```

Ollama の既定接続先は `http://127.0.0.1:11434/v1` です。`--base-url` または `OLLAMA_BASE_URL` で上書きできます。

## 参考ドキュメント

- `docs/DEVELOPMENT_GUIDE.md`: 判断基準と設計ルール
- `docs/ROADMAP.md`: これから育てたい能力の地図
- `docs/TASKS.md`: 直近の作業キュー

README は「いま使えること」を先に置き、内部契約の詳細は深掘り用ドキュメントへ寄せています。
