# TASKS

このファイルは Codex が次に着手する実装候補を決めるための単一の作業台帳とする。
GitHub では各項目を小さな issue または PR に対応づけ、同じ文言で追跡する。

## In Progress

- [ ] M6: Add documentation for GitHub issue / PR conventions once the autonomous loop is exercised in practice

## Ready

- [ ] M6: Add a lightweight blocked-task template and status sync rules for Codex-driven work

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
- [x] Cover current pipeline modules with tests

## Task Update Rules

- `In Progress` は常に 1 件まで
- 完了したら `Done` へ移し、次の最上位 `Ready` を `In Progress` へ上げる
- 大きすぎる項目は着手前に分割する
- ブロックしたら `docs/BLOCKED.md` を追加し、原因・試したこと・次に必要な判断を書く
