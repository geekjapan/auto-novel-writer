# ROADMAP

## Goal

CLI から小説プロジェクトを作成し、長編小説を
`設計 -> 分解 -> 執筆 -> 検査 -> 再計画 -> 改稿 -> 公開用成果物出力`
まで自律的に回せる制作システムへ育てる。

最終目標は「章を順番に書けること」ではなく、**長い作品を壊さずに最後まで運べること**である。

## Product Direction

このソフトウェアの中心は、単発の本文生成ではない。
必要なのは次の 5 能力を備えた長編運用基盤である。

1. **設計能力**
   作品全体の premise、登場人物、世界設定、伏線、終着点を保持する。
2. **分解能力**
   act -> chapter -> scene へ落とし、各段階に目的と制約を持たせる。
3. **記憶能力**
   長編の途中でも、既出事実・未回収要素・人物変化を再利用できる。
4. **検査能力**
   continuity だけでなく、進行停滞、伏線未回収、感情線の欠落を検知する。
5. **再計画能力**
   問題発見時に、章単位 rerun だけでなく以降の計画を更新できる。

## Current State

- CLI から `theme`、`genre`、`tone`、`target_length` を受け取り、`project_id` 単位で project/run 管理できる
- LLM provider は `mock` / `openai` / `openai-compatible` / `lmstudio` / `ollama` を切り替えられる
- `story_input -> loglines -> characters -> three_act_plot -> story_bible -> chapter_plan -> chapter_briefs -> scene_cards -> chapter_drafts` の生成フローがある
- chapter draft 生成と `rerun-from chapter_drafts` は `chapter_plan` だけでなく `chapter_briefs` / `scene_cards` も参照する
- chapter plan 全件に対して draft / revised draft を生成し、全章 artifact を保存できる
- continuity check、quality report、rerun policy、bounded revise loop、resume / rerun、history / diff metadata 保存がある
- `project_manifest.json` と comparison artifact により、current run / best run / run candidates を比較できる
- `show-run-comparison` の minimal artifact read-only coverage では compact issue / step / long-run stop 行まで tests で固定している
- `canon_ledger` の schema / storage contract は導入済みで、chapter 単位の required field と `schema_version` を save/load 時に validation できる
- `canon_ledger` には chapter 単位 upsert helper が入り、同章置換と次章追記を fail-fast 制約つきで扱える
- `thread_registry` の schema / storage contract は導入済みで、status 列挙型と chapter 参照の基本整合性を save/load 時に validation できる
- `story_summary.json`、`project_quality_report.json`、`publish_ready_bundle.json` を出力できる

## Gap To Goal

実装済みなのは、**全章生成・再開・再実行・改稿・作品単位成果物出力までの基盤**です。  
また、LLM provider 境界は openai-compatible / lmstudio / ollama まで広がっています。  
長編自律執筆に対して、現在不足している主な能力は以下である。

### 1. 長期記憶が弱い

- 既出事実、人物関係、未回収伏線、時系列イベントを検索可能な形で保持していない
- 章をまたぐ参照が summary 頼みになりやすい

### 2. Handoff Packet が未整備

- `chapter_briefs` と `scene_cards` は入ったが、章執筆入力を 1 つの packet として固定していない
- rerun / revise / 将来の replan が複数 artifact の再構成に依存している

### 3. Replanning が弱い

- rerun はできるが、「後続章計画をどう直すか」が体系化されていない
- 途中で設定変更や伏線追加が起きたときに downstream を更新しにくい

### 4. Long-form evaluation が弱い

- continuity / quality の基礎はあるが、長編特有の失敗を測りきれていない
- 例: 中盤停滞、章ごとの役割重複、感情線の停滞、伏線回収漏れ、クライマックス準備不足

## Architecture Direction

長編向けには、artifact の正本を次の 4 層へ整理する。

### 1. Project Design Layer

- `story_input`
- `loglines`
- `characters`
- `three_act_plot`
- `story_bible`

ここでは「何を書く作品か」を固定する。

### 2. Execution Plan Layer

- `chapter_plan`
- `chapter_briefs`
- `scene_cards`

ここでは「次に何を書くか」を、章と scene の両方で固定する。

### 3. Story State Layer

- `chapter_drafts`
- `revised_chapter_drafts`
- 新規: `canon_ledger`
- 新規: `thread_registry`
- 新規: `character_state`

ここでは「すでに何が起きたか」を更新する。

### 4. Evaluation And Control Layer

- `continuity_history`
- `rerun_history`
- `revise_history`
- `chapter_histories`
- `project_quality_report`
- 新規: `progress_report`
- 新規: `replan_history`

ここでは「何が壊れていて、どう直すか」を記録する。

## Milestones

### M57. Story Bible を正本 artifact として導入する

目的:
長編の土台になる作品設計を、後続工程が参照できる contract に落とす。

進捗:

- `story_bible` の schema / storage contract は導入済み
- 最低限の required field と validation は tests で固定済み
- pipeline は `three_act_plot` の後に `story_bible.json` を生成・保存できる
- provider interface は `generate_story_bible()` を持ち、mock / OpenAI client から同じ contract を返せる
- `chapter_plan` は `story_bible` を参照し、theme statement / ending reveal / foreshadowing seed を planning に反映できる
- `chapter_briefs` / `scene_cards` 生成も `story_bible` を参照する形まで広がっている

完了条件:

- `story_bible.json` を生成・保存できる
- 以下を最低限持つ
  - core premise
  - ending / reveal / truth
  - theme statement
  - character arcs
  - world rules
  - forbidden facts / non-negotiables
  - foreshadowing seeds
- chapter plan 以降の工程が `story_bible` を参照する

### M58. Chapter Brief と Scene Card を導入する

目的:
章をさらに scene 単位へ分解し、本文生成の成功条件を明確にする。

進捗:

- `chapter_briefs.json` と `scene_cards.json` の schema / storage contract は導入済み
- pipeline は `chapter_plan` の後に `chapter_briefs` と `scene_cards` を生成・保存できる
- chapter draft 生成と `rerun-from chapter_drafts` は `chapter_briefs` / `scene_cards` を必須入力として使う
- tests は pipeline 順序と fail-fast resume 条件を固定している
- 次の本命は M59 の長期記憶層である

完了条件:

- `chapter_briefs.json` を生成できる
- 章ごとに `goal`, `conflict`, `turn`, `must_include`, `continuity_dependencies` を持つ
- `scene_cards` を章ごとに生成できる
- chapter draft 生成は `chapter_plan` だけでなく `chapter_briefs` / `scene_cards` を使う

### M59. Canon Ledger と Thread Registry を導入する

目的:
既出事実と未回収要素を、長編用の運用メモリとして保持する。

進捗:

- `canon_ledger.json` の schema / storage contract は導入済み
- `thread_registry.json` の schema / storage contract は導入済み
- top-level は `schema_name` / `schema_version` / `chapters` で固定した
- 各 chapter entry は `chapter_number`, `new_facts`, `changed_facts`, `open_questions`, `timeline_events` を required field として validation する
- save/load helper は required field 欠落と `schema_version` 不整合で fail fast に停止する
- chapter 単位 upsert helper により、同章置換と次章追記ができる
- `thread_registry` は top-level を `schema_name` / `schema_version` / `threads` に固定し、各 thread entry は `thread_id`, `label`, `status`, `introduced_in_chapter`, `last_updated_in_chapter`, `related_characters`, `notes` を required field として validation する
- 次は thread 単位更新 helper を足し、その後 draft / revise / rerun から memory layer へ配線する段階である

完了条件:

- `canon_ledger.json` を保存できる
- 章ごとの新事実、変更された関係、未解決事項、時系列イベントを追記できる
- `thread_registry.json` を保存できる
- 伏線や約束の状態を `seeded / progressed / resolved / dropped` で追跡できる
- 後続章生成で関連 ledger を抽出してプロンプトへ渡せる

### M60. 章生成を Handoff Packet 駆動にする

目的:
各章執筆の入力を固定し、再現性と検査性を上げる。

完了条件:

- `chapter_handoff_packet` を章ごとに構築できる
- packet には以下が含まれる
  - current chapter brief
  - relevant scene cards
  - relevant canon facts
  - unresolved threads
  - previous chapter summary
  - style / POV / tense constraints
- draft / revise / rerun が同じ packet contract を共有する

### M61. Long-form 評価を強化する

目的:
長編で崩れやすい点を検出し、rerun と replan の判断材料にする。

完了条件:

- `progress_report.json` を生成できる
- 少なくとも以下を評価できる
  - chapter role coverage
  - escalation pace
  - emotional progression
  - foreshadowing coverage
  - unresolved thread load
  - climax readiness
- issue code が rerun / revise / replan の推奨行動に結びつく

### M62. Replan Loop を導入する

目的:
途中で見つかった問題に応じて、将来章の計画を更新できるようにする。

完了条件:

- `replan_history` を保存できる
- ある章の結果を受けて、未来の `chapter_briefs` / `scene_cards` を更新できる
- replan の理由、影響範囲、変更差分を manifest から追える
- rerun と replan の境界が docs / tests で明確になる

### M63. 自律実行ポリシーを導入する

目的:
人手なしで「続行 / 改稿 / 再実行 / 再計画 / 停止」を判断できる制御層を作る。

完了条件:

- 章完了ごとに next action decision を出せる
- decision は `continue`, `revise`, `rerun_chapter`, `replan_future`, `stop_for_review` を持つ
- policy budget と decision trace を保存できる
- project 単位で autonomy level を切り替えられる

### M64. 長編 publish bundle を強化する

目的:
完成原稿だけでなく、編集・レビュー・再生成に使える成果物束を出す。

完了条件:

- publish bundle に manuscript だけでなく
  - story bible summary
  - thread resolution summary
  - character arc summary
  - editor handoff notes
  を含められる
- best run 選抜時に long-form progress metrics も比較できる

## Sequencing Rationale

- まず M57 で設計正本を作る。長編ではここがないと後続の一貫性が弱い
- 次に M58 で chapter を scene まで分解する。これで本文生成の成功条件が明確になる
- その後 M59 で story state の長期記憶を導入する
- M60 で章生成入力を packet 化し、再現性と運用性を上げる
- M61 と M62 で評価と再計画をつなぐ
- 最後に M63 で autonomy policy を載せ、M64 で成果物を整える

## Immediate Focus

次の本命は引き続き M59 である。

理由:

- `story_bible`、`chapter_briefs`、`scene_cards` までそろったため、次は長期記憶の正本 artifact を増やす段階に入っている
- memory や replan は、導入済みの設計 / 分解 layer の上に乗せるほうが安定する
- comparison / status 系の改善は重要だが、長編自律執筆のボトルネックではない

M59 の実装順は次のとおりに進める。

1. `canon_ledger` schema と storage contract を先に固定する
2. chapter ごとの新事実・変更事実・未解決事項・時系列イベントを `canon_ledger` へ追記できるようにする
3. `thread_registry` schema と storage contract を追加する
4. draft / revise / rerun で関連 ledger / thread を参照する導線を用意する
5. README / tests / TASKS を memory layer 前提へ同期する

現在は 1 から 3 が完了し、次は 4 に進む。

## Roadmap Notes

- README は「現状できること」を書く
- ROADMAP は「最終目標までに必要な能力」を書く
- TASKS は「次に安全に実装できる最小単位」を書く
- docs では既存の `run_candidates` / `best_run` / `chapter_statuses` / `chapter_histories` / `artifact_contract` / `long_run_status` を維持しつつ、今後は `story_bible` / `chapter_briefs` / `scene_cards` / `canon_ledger` / `thread_registry` / `replan_history` を追加の正本語彙として育てる
