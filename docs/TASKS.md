# TASKS

このファイルは Codex が次に着手する実装候補を決めるための単一の作業台帳とする。  
ここでの task は、1 回で安全に実装・テスト・docs 更新・コミットできる粒度へ分割する。

## In Progress

- [ ] Docs: README / ROADMAP / TASKS / manifest で使う用語を完全に統一する

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

## Task Update Rules

- `In Progress` は常に 1 件まで
- 完了したら `Done` へ移し、次の最上位 `Ready` を `In Progress` へ上げる
- 大きすぎる項目は着手前に分割する
- docs-only タスクでも、README / tests / task 状態更新の要否を確認する
- ブロックしたら `docs/BLOCKED.md` を更新し、原因・試したこと・次に必要な判断を書く
