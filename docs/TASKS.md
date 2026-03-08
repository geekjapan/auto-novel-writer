# TASKS

このファイルは Codex が次に着手する実装候補を決めるための単一の作業台帳とする。  
ここでの task は、1 回で安全に実装・テスト・docs 更新・コミットできる粒度へ分割する。

## In Progress

- [ ] M28: `show-project-status` と `show-run-comparison` の責務差を README / ROADMAP / TASKS で整理する

## Ready



## Done

- [x] Scaffold CLI-based short-story pipeline MVP
- [x] Separate orchestration, schema, storage, and LLM access modules
- [x] Add mock provider and OpenAI provider selection
- [x] Save intermediate artifacts as JSON or YAML
- [x] Add continuity check over generated artifacts
- [x] Add rerun policy driven by continuity issue counts
- [x] Add chapter 1 revise phase
- [x] Introduce internal `chapter_drafts` and `revised_chapter_drafts` structures
- [x] M1: Generate chapter drafts in a loop while keeping `05_chapter_1_draft` as a compatibility output
- [x] M1: Generalize revise/save flow so revised drafts can be stored per chapter internally and still mirror `revised_chapter_1_draft`
- [x] M1: Add per-chapter manifest/storage tests for multi-chapter artifact consistency
- [x] M2: Add storage helpers and tests for reading existing artifacts to prepare resume / selective rerun
- [x] M2: Split pipeline phases into resumable steps with manifest-driven checkpoints
- [x] M2: Add CLI options for resuming from an output directory and rerunning from a named phase
- [x] M3: Add quality checks for POV consistency, chapter length balance, and character continuity
- [x] M3: Write a unified quality report that can recommend regenerate vs revise actions
- [x] M4: Add bounded iterative revision with stop conditions and revision history per chapter
- [x] M4: Save before/after revision diffs in artifacts or manifest metadata
- [x] M5: Introduce a project-level run layout keyed by story/project ID
- [x] M5: Add CLI commands for create-project, resume-project, and rerun-chapter workflows
- [x] M3: Tighten OpenAI response validation around schema expectations without changing the mock-first architecture
- [x] M6: Add documentation for GitHub issue / PR conventions once the autonomous loop is exercised in practice
- [x] M6: Add a lightweight blocked-task template and status sync rules for Codex-driven work
- [x] M7: Generalize continuity check so it can run per chapter using chapter_index-based artifact access
- [x] M7: Generalize rerun policy and revise flow from chapter 1 to arbitrary chapters while keeping chapter 1 compatibility outputs
- [x] M7: Save per-chapter continuity / rerun / revise histories in manifest
- [x] M8: Add story-level summary generation across all chapters
- [x] M8: Add project-wide quality report for theme coherence, POV consistency, foreshadowing coverage, and chapter balance
- [x] M8: Support multi-run candidate comparison and best-run selection metadata
- [x] M9: Orchestrate full multi-chapter draft generation from chapter_plan to final revised drafts
- [x] M9: Add long-run stop conditions and retry policy for multi-chapter generation
- [x] M9: Add final whole-story pass that generates synopsis, overall quality report, and publish-ready artifact bundle
- [x] Cover current pipeline modules with tests
- [x] Docs: Refresh README / ROADMAP / TASKS around the software-as-pipeline framing
- [x] M10: chapter 配列ベースの内部正本と chapter 1 互換 artifact の contract を manifest / tests / docs で固定する
- [x] M11: `rerun-chapter` CLI を任意章対応に一般化する
- [x] M11: 対象章だけを rerun / revise できる pipeline entry point を追加する
- [x] M11: 章単位操作の履歴を project manifest から追いやすく整理する
- [x] M12: run candidates の比較指標を issue 数以外にも広げ、`best_run` の根拠を保存する
- [x] M12: current run と best run の比較結果を CLI と project manifest で確認しやすくする
- [x] M13: 長編向け stop condition / retry policy / rerun limit を整理する
- [x] M13: `publish_ready_bundle.json` の schema を固定し、downstream 利用前提の説明と tests を追加する
- [x] Docs: README / ROADMAP / TASKS / manifest で使う用語を完全に統一する
- [x] M14: `project_manifest.json` を読み取り専用で表示する `show-project-status` CLI を追加する
- [x] M14: status 出力に `current_run` / `best_run` / `chapter_statuses` / `long_run_status` の要点を揃え、tests を追加する
- [x] M14: 章別の issue 数、rerun 回数、revise 回数を status 出力から確認できるようにする
- [x] M15: `project_manifest.json` の validator を追加し、欠落 field / version 不整合時に actionable なエラーを返す
- [x] M15: `publish_ready_bundle.json` の validator を追加し、`schema_version=1.0` contract を保存時・読込時に検証する
- [x] M15: manifest / bundle の schema version 方針を docs と tests に固定する
- [x] M16: rerun policy の主要閾値を CLI 引数または設定ファイルから与えられるようにする
- [x] M16: 実行時 policy snapshot を `manifest` / `project_manifest.json` に保存し、比較可能にする
- [x] M16: 長編向け budget 設定の差を検証する tests を追加する
- [x] M17: 機械可読な run comparison summary artifact を追加する
- [x] M17: 人間レビュー後に `best_run` を固定または昇格できる CLI を追加する
- [x] M18: `publish_ready_bundle.sections` の最小 contract を定義し、docs / tests で固定する
- [x] Docs: M16-M18 実装後に README / ROADMAP / TASKS の説明を同期する
- [x] M19: `run_comparison_summary.json` の validator と schema version を追加する
- [x] M19: `select-best-run` の manual selection reason を comparison summary に残す
- [x] M19: `show-project-status` から current run と best run の policy 差分を表示する
- [x] Docs: M16-M19 実装後に README / ROADMAP / TASKS の説明を同期する
- [x] M20: `show-project-status` に selection source と selection reason の要約を表示する
- [x] M20: current run と best run の issue / step / policy 差分を status 出力でまとめて見やすくする
- [x] M20: `run_comparison_summary.json` に status 表示用の compact summary を追加する
- [x] Docs: M16-M20 実装後に README / ROADMAP / TASKS の説明を同期する
- [x] M21: `run_comparison_summary.json` の compact summary contract を docs / tests で固定する
- [x] M21: `show-project-status` の compact diff と `run_comparison_summary.json` の compact summary の対応を docs に明記する
- [x] M21: manual / automatic selection の比較根拠を current run と best run の双方で出せるようにする
- [x] Docs: M16-M20 実装後に README / ROADMAP / TASKS の説明を同期する
- [x] M22: `run_comparison_summary.json` の `current_run` / `best_run` comparison context contract を validator / docs / tests で固定する
- [x] M22: `show-project-status` の current / best comparison summary を machine-readable artifact と同じ語彙で揃える
- [x] M22: manual selection と automatic selection の reason schema を downstream 利用向けに整理する
- [x] M23: `run_candidates` の reason details contract を `run_comparison_summary.json` と同じ粒度で固定する
- [x] M23: `show-project-status` に reason details の主要 code を簡潔に表示できる mode を追加する
- [x] Docs: M23 実装後に README / ROADMAP / TASKS の説明を同期する
- [x] M24: `show-project-status` の reason codes と `run_comparison_summary.json` の `*_reason_details.code` の対応を docs / tests で固定する
- [x] M24: `run_comparison_summary.json` の `*_reason_details.code` を列挙型として contract 化する
- [x] Docs: M23-M24 実装後に README / ROADMAP / TASKS の説明を同期する
- [x] M25: `project_manifest.json` 側の `*_reason_details.code` も同じ列挙型 contract で固定する
- [x] M25: `show-project-status` の reason code 表示順を schema の列挙順に明示的に揃える
- [x] Docs: M25 実装後に README / ROADMAP / TASKS の説明を同期する
- [x] M26: `project_manifest.json` の current / best / run_candidates comparison context contract を `run_comparison_summary.json` と同じ粒度に広げる
- [x] M26: `show-project-status` の summary 行を `project_manifest.json` の machine-readable context だけから再構成できるように整理する
- [x] M26: status 表示の summary field 名と `project_manifest.json` / `run_comparison_summary.json` の field 名の対応表を docs / tests で固定する
- [x] M27: `show-project-status` の整形関数を manifest 読込と分離し、summary builder を単体テスト可能にする
- [x] Docs: M26-M27 実装後に ROADMAP / TASKS の説明を同期する
- [x] M28: `run_comparison_summary.json` を読み取り専用で表示する `show-run-comparison` CLI を追加する
- [x] M28: `show-run-comparison` の summary field 名と `run_comparison_summary.json` の field 名の対応を docs / tests で固定する

## Task Update Rules

- `In Progress` は常に 1 件まで
- 完了したら `Done` へ移し、次の最上位 `Ready` を `In Progress` へ上げる
- 大きすぎる項目は着手前に分割する
- docs-only タスクでも、README / tests / task 状態更新の要否を確認する
- ブロックしたら `docs/BLOCKED.md` を更新し、原因・試したこと・次に必要な判断を書く
