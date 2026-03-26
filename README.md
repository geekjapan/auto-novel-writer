# auto-novel-writer

`auto-novel-writer` は、CLI ベースの小説制作パイプラインです。  
目指すのは「一発で完成原稿を出す本文生成器」ではなく、**小説制作を工程分解し、章単位・作品単位で再開可能に回せる制御基盤**です。

現在は、CLI 入力から `story_input`、`loglines`、`characters`、`three_act_plot`、`story_bible`、`chapter_plan`、`chapter_briefs`、`scene_cards`、全章 draft、全章 revised draft、quality 系 artifact、project/run 管理用 manifest、comparison artifact までを順に生成できます。加えて、次段階の story state layer に向けて `canon_ledger` と `thread_registry` の schema / storage contract、chapter draft / revised draft 結果からの最小自動反映導線も導入済みです。

## ソフトウェアの目的

- CLI から小説プロジェクトを作成する
- 章単位・作品単位で `生成 → 検査 → 再実行 → 改稿 → 要約 → 公開用成果物出力` を回す
- 途中停止しても、artifact と manifest から resume / rerun できるようにする
- 短編から長編まで、品質管理つきで安定生成できる土台をつくる

## 仕様の中心

このソフトウェアの中心は、プロンプト単体ではなくパイプラインです。  
正本となる内部状態は、`chapter_drafts` / `revised_chapter_drafts` のような**章配列ベースの状態**と、`project_manifest.json` / `manifest` のような**project/run 管理情報**です。

当面は後方互換のため chapter 1 互換 artifact も維持しますが、設計の中心は全章状態です。

## 用語対応

この README では読みやすさのため自然言語も使いますが、artifact や manifest の実フィールド名は以下で統一します。

- 作品単位管理: `project_manifest.json`
- 実行単位: `run`
- 実行候補: `run_candidates`
- 採用 run: `best_run`
- 章別状態要約: `chapter_statuses`
- 章別履歴束ね: `chapter_histories`
- 全章草稿の正本: `chapter_drafts`
- 全章改稿稿の正本: `revised_chapter_drafts`
- 長編設計の正本: `story_bible`
- 章別成功条件の正本: `chapter_briefs`
- 章内 scene 分解の正本: `scene_cards`
- 長期記憶の正本: `canon_ledger`
- thread 状態の正本: `thread_registry`
- chapter 1 互換出力: `chapter_1_draft`, `revised_chapter_1_draft`, `continuity_report`
- 配布向け成果物: `publish_ready_bundle.json`
- artifact 契約定義: `artifact_contract`
- 長編停止状態: `long_run_status`

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
5. `story_bible`
6. `chapter_plan`
7. `chapter_briefs`
8. `scene_cards`
9. `chapter_drafts`

`chapter_plan` の後に、各章の成功条件をまとめた `chapter_briefs` と scene 分解をまとめた `scene_cards` を生成し、その 2 つを使って各章の `chapter_{n}_draft` を保存します。

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
- `run_comparison_summary.json`

これらは公開、比較、選抜、後続工程での利用を想定した artifact です。

## 現在実装済みの主要機能

- `mock` / `openai` / `openai-compatible` / `lmstudio` / `ollama` の LLM プロバイダ切替
- provider ごとのモデル名選択
- `story_bible` を参照した `chapter_plan` 生成
- 全章 `chapter_briefs` / `scene_cards` 生成
- 全章 `chapter_{n}_draft` 生成
- 全章 `revised_chapter_{n}_draft` 保存
- continuity report と quality report の生成
- rerun policy による再生成制御
- bounded loop による改稿と diff metadata 保存
- `manifest` の checkpoint / history 保存
- `project_id` 単位の run layout と `project_manifest.json`
- `story_summary.json`、`project_quality_report.json`、`publish_ready_bundle.json`
- run candidates と `best_run` の記録
- `best_run` の比較根拠となる comparison metrics の保存
- current run と `best_run` の比較結果を CLI から確認
- `show-project-status` / `show-run-comparison` の read-only 表示
- `story_bible` の schema / storage contract
- `canon_ledger` の schema / storage contract
- `canon_ledger` の chapter 単位 upsert helper
- `thread_registry` の schema / storage contract
- `thread_registry` の thread 単位 upsert helper

## 長編設計 artifact の現状

`story_bible` は、長編向け設計情報を保持するための正本 artifact として導入済みです。
現在は pipeline で `three_act_plot` の後に生成し、storage / validation を通して保存します。最低限以下の field を固定しています。

- `core_premise`
- `ending_reveal`
- `theme_statement`
- `character_arcs`
- `world_rules`
- `forbidden_facts`
- `foreshadowing_seeds`

現在は `chapter_plan` 生成も `story_bible` を参照し、テーマ命題や終盤の真相、伏線情報を planning に反映します。

`chapter_briefs` と `scene_cards` も導入済みです。現在は `chapter_plan` の後に順に生成し、resume / rerun でも chapter draft 生成の前提として扱います。

- `chapter_briefs` は章ごとの `goal`, `conflict`, `turn`, `must_include`, `continuity_dependencies` などを保持します
- `scene_cards` は章ごとの scene 配列として、`scene_goal`, `scene_conflict`, `scene_turn`, `must_include`, `continuity_refs` などを保持します

`canon_ledger` は、story state layer に入る前の長期記憶 artifact として save/load helper と validator まで導入済みです。現在の contract は top-level に `schema_name`, `schema_version`, `chapters` を持ち、各 chapter entry に最低限次を要求します。

- `chapter_number`
- `new_facts`
- `changed_facts`
- `open_questions`
- `timeline_events`

`canon_ledger.json` は保存時と読込時の両方で validation され、required field 欠落や `schema_version` 不整合は fail fast で停止します。storage helper では chapter 単位 upsert もでき、同じ `chapter_number` は置換、連番の次章は追記、番号が飛ぶ append は fail fast で停止します。chapter draft 生成と `rerun-chapter` の文脈入力でも参照し、artifact が存在しない場合は空の `canon_ledger` を互換用 default として渡します。さらに chapter draft 保存直後と revised draft 保存直後には最小の決め打ちルールで自動更新し、`new_facts` にはその時点の draft `summary`、`open_questions` には `chapter_briefs.foreshadowing_targets`、`timeline_events` には scene 1 の `exit_state` を保存します。full pipeline を最後まで進めた場合、各 chapter entry は revised draft の `summary` で上書きされます。

`thread_registry` も save/load helper と validator まで導入済みです。現在の contract は top-level に `schema_name`, `schema_version`, `threads` を持ち、各 thread entry に最低限次を要求します。

- `thread_id`
- `label`
- `status`
- `introduced_in_chapter`
- `last_updated_in_chapter`
- `related_characters`
- `notes`

`status` は `seeded`, `progressed`, `resolved`, `dropped` の列挙型に固定しています。`thread_registry.json` も保存時と読込時の両方で validation され、required field 欠落、unsupported `schema_version`、不正な status、`last_updated_in_chapter < introduced_in_chapter` は fail fast で停止します。storage helper では thread 単位 upsert もでき、同じ `thread_id` は置換、未登録の `thread_id` は追加します。chapter draft 生成と `rerun-chapter` の文脈入力でも参照し、artifact が存在しない場合は空の `thread_registry` を互換用 default として渡します。さらに chapter draft 保存直後と revised draft 保存直後には `chapter_briefs.foreshadowing_targets` から thread entry を自動反映し、`last_updated_in_chapter` は当該章、`introduced_in_chapter` は既存 thread があれば最初の導入章を保持します。full pipeline を最後まで進めた場合、各 thread の `notes` は最後に更新した章の revised draft `summary` になります。

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

既定の接続先は `http://127.0.0.1:1234/v1` です。`--base-url` または `LMSTUDIO_BASE_URL` で上書きできます。
LM Studio では `response_format.type=json_object` が通らないため、現在実装は `text` 応答として JSON を返す前提で接続します。
LM Studio が JSON を Markdown の ```json fenced block``` で返した場合は、その外側だけを明示的に取り除いて parse します。JSON 本体でない文章が返った場合は fail fast でエラーにします。
text mode の provider には、CLI 側からも「JSON 以外を書かない」「Markdown fence を付けない」指示を明示的に付与します。

Ollama を使う場合:

```bash
python -m pip install openai
novel-writer --provider ollama --model llama3.1
```

既定の接続先は `http://127.0.0.1:11434/v1` です。`--base-url` または `OLLAMA_BASE_URL` で上書きできます。
Python SDK が API key 文字列を要求するため、LM Studio と Ollama では既定のダミー key を使います。`--api-key` で明示値に差し替えられます。
Ollama などの OpenAI 互換 endpoint でも、現在実装は `text` 応答として JSON を返す前提で接続します。

長編向け stop condition を試験的に調整したい場合:

```bash
novel-writer --theme "境界" --genre "SF" --tone "ビター" --target-length 5000 --max-high-severity-chapters 6 --max-total-rerun-attempts 12
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

`--rerun-from chapter_drafts` は、保存済みの `chapter_briefs` と `scene_cards` を前提に chapter draft 以降をやり直します。これらの artifact が欠けている場合は fail fast で停止します。

現在の step 順序:

1. `story_input`
2. `loglines`
3. `characters`
4. `three_act_plot`
5. `story_bible`
6. `chapter_plan`
7. `chapter_briefs`
8. `scene_cards`
9. `chapter_drafts`
10. `continuity_report`
11. `quality_report`
12. `revised_chapter_drafts`
13. `story_summary`
14. `project_quality_report`
15. `publish_ready_bundle`

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
`data/projects/my-story-01/project_manifest.json` に current run、run candidates、best run、章別 status 要約を保存します。

専用コマンド:

```bash
novel-writer create-project --project-id "my-story-01" --theme "境界" --genre "SF" --tone "ビター" --target-length 5000
novel-writer resume-project --project-id "my-story-01"
novel-writer show-project-status --project-id "my-story-01"
novel-writer show-run-comparison --project-id "my-story-01"
novel-writer select-best-run --project-id "my-story-01" --run-name "latest_run"
novel-writer rerun-chapter --project-id "my-story-01" --chapter-number 2
```

`rerun-chapter` は任意章の draft / continuity / revise / summary 系 artifact を再計算します。  
ただし互換 artifact の `continuity_report.json` と `quality_report.json` は、引き続き chapter 1 基準です。
`show-project-status` は `project_manifest.json` を読み取り専用で表示し、run を再実行しません。  
現在は current run、best run、chapter status の要約、章ごとの issue / rerun / revise 回数、long-run status の要点、issue / step / policy の差分、current run の comparison reason 要約、best run の selection source / reason 要約を確認できます。
`show-run-comparison` は `run_comparison_summary.json` を読み取り専用で表示し、comparison artifact 側の current / best / compact summary を確認できます。
`select-best-run` は `run_candidates` から 1 つを手動で `best_run` に昇格します。

読み分けの基準:

- `show-project-status` は project manifest 中心の運用確認に使う
- 確認対象: current run、best run、chapter status、long-run status、policy diff
- 向いている用途: 途中再開前の状況確認、章ごとの rerun / revise 状態確認、project 単位の停止判断
- `show-run-comparison` は comparison artifact 中心の比較確認に使う
- 確認対象: current / best comparison context、selection source、compact summary
- 向いている用途: run 候補比較、best_run 採用理由確認、downstream 向け comparison artifact の目視確認
- 内部実装では `show-run-comparison` も `run_comparison_summary.json -> structured summary -> lines` の順で整形する
- `show-run-comparison` の read-only テストでは、minimal valid artifact と zero-candidate artifact の表示境界も固定している

## 主な出力物

- `story_input`
- `01_loglines`
- `02_characters`
- `03_three_act_plot`
- `story_bible`
- `04_chapter_plan`
- `chapter_briefs`
- `scene_cards`
- `canon_ledger`
- `thread_registry`
- `05_chapter_1_draft`
- `chapter_{n}_draft`
- `continuity_report.json`
- `quality_report.json`
- `revised_chapter_1_draft`
- `revised_chapter_{n}_draft`
- `story_summary.json`
- `project_quality_report.json`
- `publish_ready_bundle.json`
- `run_comparison_summary.json`
- `manifest`

`manifest` には以下も保存します。

- `artifact_contract`
- `checkpoints`
- `current_step`
- `completed_steps`
- `continuity_history`
- `rerun_history`
- `revise_history`
- `chapter_histories`
- `long_run_status`

`artifact_contract` は、chapter 配列ベースの正本と chapter 1 互換 artifact の対応を明示するための metadata です。
`long_run_status` は、長編向け stop condition、残り rerun 余地、resume guidance を記録する metadata です。
`policy_snapshot` は、その run がどの rerun policy 設定で動いたかを保存する metadata です。
`publish_ready_bundle.json` は `schema_version=1.0` の固定 schema を持ち、downstream 利用向けに `source_artifacts` と `sections` を含みます。
`project_manifest.json` も `schema_name=project_manifest` と `schema_version=1.0` を持ち、保存時・読込時に validation されます。
`run_comparison_summary.json` には status 表示向けの `compact_summary` も保存されます。

`run_comparison_summary.compact_summary` の固定 field:

- `selection_source`
- `issue_score.current|best`
- `completed_step_count.current|best`
- `long_run_should_stop.current|best`
- `policy_limits.max_high_severity_chapters.current|best`
- `policy_limits.max_total_rerun_attempts.current|best`

`show-project-status` の compact diff との対応:

- `diff_summary.issue_score` 相当は `compact_summary.issue_score.current|best`
- `diff_summary.completed_steps` 相当は `compact_summary.completed_step_count.current|best`
- `diff_summary.stop` 相当は `compact_summary.long_run_should_stop.current|best`
- `diff_policy.max_high_severity_chapters` 相当は `compact_summary.policy_limits.max_high_severity_chapters.current|best`
- `diff_policy.max_total_rerun_attempts` 相当は `compact_summary.policy_limits.max_total_rerun_attempts.current|best`
- `selection_source` は status と `compact_summary` の両方で同じ語彙を使う

責務分担:

- `show-project-status` は `project_manifest.json` を読む運用ビュー
- `show-run-comparison` は `run_comparison_summary.json` を読む比較ビュー
- status 表示は人間向けの project 運用要約、`run_comparison_summary.json` は比較・選抜・下流処理向けの機械可読 artifact

`current_run` / `best_run` の比較根拠:

- `current_run` には `comparison_metrics`, `comparison_basis`, `comparison_reason` を保存する
- `current_run` には machine-readable な `comparison_reason_details` も保存する
- `best_run` には `comparison_metrics`, `comparison_basis`, `selection_source`, `selection_reason` を保存する
- `best_run` には machine-readable な `selection_reason_details` も保存する
- automatic selection でも manual selection でも、`comparison_metrics` は current / best の双方で追える
- `show-project-status` では current 側は `current_comparison_reason_summary`、best 側は `best_selection_reason_summary` として表示する
- `run_comparison_summary.json` では `current_run` / `best_run` のこの comparison context を validator で検証する
- `show-project-status` の summary 行は `current_comparison_*` / `best_selection_*` / `best_comparison_*` の語彙で表示する
- `show-project-status` の comparison 系 summary 行は、`project_manifest.json` の machine-readable context をそのまま要約して再構成する
- `*_reason_details` の各要素は `code` と `value` を持つ object とする
- `run_candidates` も `comparison_reason_details` を持ち、`run_comparison_summary.json` 読込時に同じ contract で検証する
- `show-project-status --reason-detail-mode codes` を使うと、`*_reason_details` の主要 `code` を簡潔に表示できる
- `project_manifest.json` の `current_run` / `best_run` / `run_candidates` も、`run_comparison_summary.json` と同じ粒度の comparison context を持つ
- `project_manifest.json` 側の `comparison_reason_details` / `selection_reason_details` も同じ列挙型 contract で検証する
- `show-project-status` の reason code 表示順は schema の列挙順に揃える

reason code の対応:

- `current_comparison_reason_codes` は `run_comparison_summary.json.current_run.comparison_reason_details[*].code` の先頭要素に対応する
- `best_selection_reason_codes` は `run_comparison_summary.json.best_run.selection_reason_details[*].code` の先頭要素に対応する
- 現状の代表 code は `manual_selection`, `long_run_should_stop`, `total_issue_score`, `high_severity_chapter_count`, `rerun_attempt_total`, `revision_attempt_total`, `completed_step_count`
- 上記の code 一覧は `run_comparison_summary.json` validator の列挙型 contract として固定される
- `project_manifest.json` の `current_run` / `best_run` / `run_candidates` でも同じ code 一覧を使う
- status の codes mode もこの列挙順に従って表示する

status summary field と artifact field の対応:

- `completed_steps` は `project_manifest.json.current_run.comparison_metrics.completed_step_count` を表示する
- `current_comparison_basis_summary` は `project_manifest.json.current_run.comparison_basis[:3]` を表示する
- `current_comparison_reason_summary` は `project_manifest.json.current_run.comparison_reason_details[:2]` を `code=value` へ整形して表示する
- `current_comparison_reason_codes` は `project_manifest.json.current_run.comparison_reason_details[:3].code` を schema 順へ整列して表示する
- `current_comparison_metrics` は `project_manifest.json.current_run.comparison_metrics.total_issue_score` と `completed_step_count` を表示する
- `best_selection_source` は `project_manifest.json.best_run.selection_source` を表示する
- `best_comparison_basis_summary` は `project_manifest.json.best_run.comparison_basis[:3]` を表示する
- `best_selection_reason_summary` は `project_manifest.json.best_run.selection_reason_details[:2]` を `code=value` へ整形して表示する
- `best_selection_reason_codes` は `project_manifest.json.best_run.selection_reason_details[:3].code` を schema 順へ整列して表示する
- `best_comparison_metrics` は `project_manifest.json.best_run.comparison_metrics.total_issue_score` と `completed_step_count` を表示する
- `diff_summary` は `project_manifest.json.current_run.comparison_metrics` と `project_manifest.json.best_run.comparison_metrics` の比較要約を表示する
- `diff_policy` は `project_manifest.json.current_run.policy_snapshot.long_run` と `project_manifest.json.best_run.policy_snapshot.long_run` の比較要約を表示する
- `policy_diff.max_high_severity_chapters` などの個別差分行も `project_manifest.json.*.policy_snapshot.long_run` から出す
- `run_comparison_summary.json` 側では同じ comparison field 名を `current_run` / `best_run` に保ち、status 表示はその project manifest 版を読む

run comparison summary field と artifact field の対応:

- `Current run` は `run_comparison_summary.json.current_run.run_name` を表示する
- `output_dir` は `run_comparison_summary.json.current_run.output_dir` または `run_comparison_summary.json.best_run.output_dir` を表示する
- `current_comparison_basis_summary` は `run_comparison_summary.json.current_run.comparison_basis[:3]` を表示する
- `current_comparison_reason_summary` は `run_comparison_summary.json.current_run.comparison_reason_details[:2]` を `code=value` へ整形して表示する
- `current_comparison_reason_codes` は `run_comparison_summary.json.current_run.comparison_reason_details[:3].code` を schema 順へ整列して表示する
- `current_comparison_metrics` は `run_comparison_summary.json.current_run.comparison_metrics.total_issue_score` と `completed_step_count` を表示する
- `Best run` は `run_comparison_summary.json.best_run.run_name` を表示する
- `best_selection_source` は `run_comparison_summary.json.best_run.selection_source` を表示する
- `best_comparison_basis_summary` は `run_comparison_summary.json.best_run.comparison_basis[:3]` を表示する
- `best_selection_reason_summary` は `run_comparison_summary.json.best_run.selection_reason_details[:2]` を `code=value` へ整形して表示する
- `best_selection_reason_codes` は `run_comparison_summary.json.best_run.selection_reason_details[:3].code` を schema 順へ整列して表示する
- `best_comparison_metrics` は `run_comparison_summary.json.best_run.comparison_metrics.total_issue_score` と `completed_step_count` を表示する
- `Compact summary: selection_source=...` は `run_comparison_summary.json.compact_summary.selection_source` を表示する
- `compact.issue_score` は `run_comparison_summary.json.compact_summary.issue_score.current|best` を表示する
- `compact.completed_step_count` は `run_comparison_summary.json.compact_summary.completed_step_count.current|best` を表示する
- `compact.long_run_should_stop` は `run_comparison_summary.json.compact_summary.long_run_should_stop.current|best` を表示する
- `compact.policy_limits.max_high_severity_chapters` は `run_comparison_summary.json.compact_summary.policy_limits.max_high_severity_chapters.current|best` を表示する
- `compact.policy_limits.max_total_rerun_attempts` は `run_comparison_summary.json.compact_summary.policy_limits.max_total_rerun_attempts.current|best` を表示する
- `Run candidates` は `run_comparison_summary.json.candidate_count` を表示する
- `run_candidate_names` は `run_comparison_summary.json.run_candidates[*].run_name` を表示する
- `run_candidate_scores` は `run_comparison_summary.json.run_candidates[*].score` を `run_name=score` へ整形して表示する
- `run_candidate_output_dirs` は `run_comparison_summary.json.run_candidates[*].output_dir` を `run_name=output_dir` へ整形して表示する

minimal valid comparison artifact の read-only 境界:

- `show-run-comparison` は `run_comparison_summary.json` の validator を通る最小 shape に対しても表示できる
- 現在は `current_comparison_reason_codes`, `current_comparison_metrics`, `best_selection_source`, `best_selection_reason_codes`, `best_comparison_metrics`, `compact.issue_score`, `compact.completed_step_count`, `compact.long_run_should_stop`, `Run candidates: 0` まで tests で固定している
- `run_candidates=[]` の場合でも count 行は表示するが、`run_candidate_names` / `run_candidate_scores` / `run_candidate_output_dirs` は表示しない

schema version の現方針:

- `project_manifest.json` は `schema_name=project_manifest`, `schema_version=1.0`
- `publish_ready_bundle.json` は `bundle_type=publish_ready_bundle`, `schema_version=1.0`
- `run_comparison_summary.json` は `schema_name=run_comparison_summary`, `schema_version=1.0`
- `publish_ready_bundle.sections` は `manuscript`, `story_summary`, `quality` の 3 section を持つ
- 不正な version や必須 field 欠落は fail fast で弾く
- 将来 version を上げる場合は、互換維持または明示的な migration を伴わせる

## 現時点でできること

- 章計画に基づく全章 draft 生成
- 章別 continuity / quality 検査
- rerun policy による再実行
- bounded revise loop
- 作品全体 summary / synopsis 生成
- project 単位の resume / rerun
- publish-ready bundle 出力

## 既知の限界

- continuity report は互換上 chapter 1 基準の artifact を維持しています
- quality report は構造評価中心で、文学的評価は限定的です
- 長編向け stop condition はあるものの、長編運用はまだ安定化段階です
- 長編向け stop condition は見える化されたが、閾値設計そのものは今後さらに調整が必要です

## 内部設計原則

- 正本は chapter 配列ベースの内部状態
- chapter 1 互換 artifact は当面維持
- manifest に履歴を残す
- manifest に artifact contract も残す
- `mock` / `openai` / `openai-compatible` / `lmstudio` / `ollama` を切替可能
- artifact は JSON / YAML で保存する
- secrets と生成成果物は repo に push しない運用を前提にする

## 最終到達像

- 中編・長編でも途中停止 / 再開できる
- 全章を順に生成・検査・改稿できる
- 複数 run を比較し best candidate を選べる
- publish-ready bundle まで一括出力できる

## テスト

```bash
./venv/bin/python -m unittest tests.test_cli -v
./venv/bin/python -m unittest discover -s tests -v
```

## 開発ドキュメント

- `docs/ROADMAP.md`: 現在地と次のマイルストーン
- `docs/TASKS.md`: 直近の実装キュー
- `docs/CODEX_WORKFLOW.md`: 1 タスクずつ進める標準手順
- `docs/GITHUB_CONVENTIONS.md`: issue / PR / branch / commit の運用
- `docs/BLOCKED.md`: ブロック時の記録テンプレート
