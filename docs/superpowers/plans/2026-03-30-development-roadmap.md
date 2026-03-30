# Development Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 開発優先順位、機能追加方針、中長期マイルストーン見取り図を docs として整理し、`ROADMAP.md` と `TASKS.md` の役割分担を保ったまま今後の開発判断をしやすくする

**Architecture:** 新規 `docs/DEVELOPMENT_GUIDE.md` を追加して、`docs/ROADMAP.md` は中長期の到達点、`docs/TASKS.md` は直近のキュー、`DEVELOPMENT_GUIDE.md` はその間をつなぐ判断基準として役割を固定する。README は現状仕様に限定し、必要な参照だけを同期する。

**Tech Stack:** Markdown、git、既存 docs 運用ルール、`rg`、`sed`

---

## File Structure

- Create: `docs/DEVELOPMENT_GUIDE.md`
  - 優先順位基準、機能追加ポリシー、長期見取り図、task 分解ルールを書く
- Modify: `docs/ROADMAP.md`
  - 新 guide と矛盾しないように current focus と長期見取り図を整理する
- Modify: `docs/TASKS.md`
  - 直近 task が新しい優先順位基準と整合することを確認し、必要なら wording を調整する
- Modify: `README.md`
  - 現状仕様文書としての役割を守りつつ、新 guide への参照か docs 役割説明を最小追加する
- Create/Modify: `docs/superpowers/plans/2026-03-30-development-roadmap.md`
  - この plan 自体を保存する

## Shared Implementation Notes

- `README.md` には未実装の将来機能を書き足さない
- `docs/ROADMAP.md` では task 粒度へ落とし込みすぎない
- `docs/TASKS.md` は常に単一の `In Progress` を維持する
- 新 guide では、M63 残件、M64、その先の長期候補を能力軸で整理する
- docs 間の役割説明は、表現を変えても意味を揃える

### Task 1: Create The Development Guide

**Files:**
- Create: `docs/DEVELOPMENT_GUIDE.md`
- Reference: `AGENTS.md`
- Reference: `docs/CODEX_WORKFLOW.md`
- Reference: `docs/ROADMAP.md`
- Reference: `docs/TASKS.md`

- [ ] **Step 1: Re-read the source docs that define responsibilities**

Run:

```bash
sed -n '1,220p' AGENTS.md
sed -n '1,220p' docs/CODEX_WORKFLOW.md
sed -n '1,260p' docs/ROADMAP.md
sed -n '1,120p' docs/TASKS.md
```

Expected: 4 つの文書から、作業ルール、現在の focus、現在 task を再確認できる。

- [ ] **Step 2: Draft the new guide with the agreed section structure**

```markdown
# DEVELOPMENT GUIDE

## Purpose

この文書は、`auto-novel-writer` の開発者と将来の協力者が、
今後の機能追加と task 分解を同じ判断基準で進めるためのガイドである。

## Document Roles

- `AGENTS.md`: repository 全体の恒久ルール
- `docs/CODEX_WORKFLOW.md`: Codex の実行手順
- `docs/ROADMAP.md`: 中長期の到達点と milestone
- `docs/TASKS.md`: 直近の最小 task queue
- `docs/DEVELOPMENT_GUIDE.md`: 優先順位、設計原則、task 分解基準

## Current Development Stage

- 現在の主戦場は M63 の残件と M64 以降である
- `next_action_decision` まで導入済みで、M63 の残件は `autonomy level` の project 単位 contract である
- 次段階では publish / handoff と長期評価強化を整理して進める

## Priority Rules

- CLI と artifact contract を先に固める
- fail-fast を優先し、暗黙 fallback を入れない
- 既存 layer の接続完成を、新規派生機能より優先する
- UI より long-form control / evaluation / handoff を優先する
- 1 回の変更は tests、docs、commit まで閉じる

## Feature Addition Policy

- 新 artifact は、既存 artifact では責務を表現できないときだけ追加する
- 既存 contract 拡張時は validator / storage / docs / tests を同時に更新する
- LLM access は既存 client 境界の内側に閉じ込める
- docs-only で済まない変更は README と tests の更新要否も確認する
- 将来機能は README ではなく `ROADMAP.md` と本 guide に書く

## Milestone Outlook

### Control Layer の完成
- M63 残件の `autonomy level`
- project 単位の制御方針

### Publish / Handoff Layer の強化
- M64 の publish bundle 強化
- editor / review handoff summary

### Story State Layer の深化
- `canon_ledger` / `thread_registry` の参照性向上
- 将来候補の `character_state`

### Evaluation Layer の深化
- `progress_report` の評価精度改善
- rerun / revise / replan 境界の改善

### Operational Layer の強化
- status / comparison / resume / rerun の運用性向上
- block 時の診断性強化

## How To Turn Roadmap Into Tasks

- 1 task は 1 回で実装・tests・docs 更新・commit まで閉じる粒度にする
- milestone を schema / storage / pipeline / tests / docs へ分解して考える
- 仕様判断が一意でないときは `docs/BLOCKED.md` を更新して止まる
- `Ready` が空のときだけ次の子 task を起票する

## Docs Sync Rules

- `ROADMAP.md` は「何を目指すか」
- `TASKS.md` は「次に何をやるか」
- `DEVELOPMENT_GUIDE.md` は「どう判断して順序づけるか」
- 振る舞い変更時は README も同期する
```

- [ ] **Step 3: Save the guide and verify the file exists**

Run:

```bash
test -f docs/DEVELOPMENT_GUIDE.md && sed -n '1,260p' docs/DEVELOPMENT_GUIDE.md
```

Expected: `docs/DEVELOPMENT_GUIDE.md` の全セクションが表示される。

- [ ] **Step 4: Commit the new guide**

```bash
git add docs/DEVELOPMENT_GUIDE.md
git commit -m "docs: add development guide"
```

### Task 2: Sync The Roadmap With The Guide

**Files:**
- Modify: `docs/ROADMAP.md`
- Reference: `docs/DEVELOPMENT_GUIDE.md`

- [ ] **Step 1: Identify roadmap sections that still mix long-term goals and immediate rules**

Run:

```bash
rg -n "Immediate Focus|Current State|Gap To Goal|Milestones|Sequencing Rationale" docs/ROADMAP.md
sed -n '1,260p' docs/ROADMAP.md
```

Expected: 中長期の milestone 記述と immediate focus 記述の位置が確認できる。

- [ ] **Step 2: Rewrite roadmap wording so it stays milestone-focused**

```markdown
## Immediate Focus

現在の本命は M63 の残件である。

理由:

- `progress_report`、`replan_history`、`next_action_decision` まで入り、control layer の artifact はそろっている
- M63 の未完了条件は project 単位の `autonomy level` 切替だけである
- M64 へ進む前に、project-level control policy を先に固定したほうが順序が明確である

次に詰めるべき最小論点は次のとおりである。

1. `autonomy level` の列挙値
2. project 単位の保存先
3. validation と docs の同期
```

- [ ] **Step 3: Verify roadmap still describes milestones rather than task-level implementation**

Run:

```bash
sed -n '279,360p' docs/ROADMAP.md
```

Expected: `ROADMAP.md` の focus が M63 と M64 の関係を説明しており、細かい task 手順へ崩れていない。

- [ ] **Step 4: Commit the roadmap sync**

```bash
git add docs/ROADMAP.md
git commit -m "docs: sync roadmap with development guide"
```

### Task 3: Sync The Task Ledger And README

**Files:**
- Modify: `docs/TASKS.md`
- Modify: `README.md`
- Reference: `docs/DEVELOPMENT_GUIDE.md`
- Reference: `docs/ROADMAP.md`

- [ ] **Step 1: Confirm the current task matches the new priority rules**

Run:

```bash
sed -n '1,40p' docs/TASKS.md
sed -n '1,220p' README.md
```

Expected: `In Progress` が M63 残件であり、README が現状仕様中心であることを確認できる。

- [ ] **Step 2: Adjust wording only where docs-role clarity is missing**

```markdown
## In Progress

- [ ] M63f: project autonomy level contract を追加する
  - Purpose: M63 の未完了条件である project 単位の `autonomy level` 切替を、schema / storage / pipeline / docs / tests で fail-fast に固定する
```

```markdown
## ソフトウェアの目的

この repository では、現状仕様は `README.md`、
中長期の到達点は `docs/ROADMAP.md`、
直近 task は `docs/TASKS.md` で管理する。
開発優先順位と task 分解基準は `docs/DEVELOPMENT_GUIDE.md` を参照する。
```

- [ ] **Step 3: Verify there is no future-only functionality added to the README**

Run:

```bash
rg -n "autonomy level|character_state|future|予定" README.md docs/TASKS.md docs/ROADMAP.md docs/DEVELOPMENT_GUIDE.md
```

Expected: README には未実装の説明が増えず、将来方向は `ROADMAP.md` と `DEVELOPMENT_GUIDE.md` に寄っている。

- [ ] **Step 4: Commit the task and README sync**

```bash
git add docs/TASKS.md README.md
git commit -m "docs: align task ledger and readme roles"
```

### Task 4: Final Docs Review And Wrap-Up

**Files:**
- Modify: `docs/DEVELOPMENT_GUIDE.md`
- Modify: `docs/ROADMAP.md`
- Modify: `docs/TASKS.md`
- Modify: `README.md`

- [ ] **Step 1: Run the docs consistency review**

Run:

```bash
rg -n "DEVELOPMENT_GUIDE|Immediate Focus|autonomy level|next_action_decision" README.md docs/ROADMAP.md docs/TASKS.md docs/DEVELOPMENT_GUIDE.md
```

Expected: 各 docs の役割分担と現在 focus が一貫して参照されている。

- [ ] **Step 2: Read the final docs set in one pass**

Run:

```bash
sed -n '1,220p' docs/DEVELOPMENT_GUIDE.md
sed -n '1,120p' docs/TASKS.md
sed -n '279,360p' docs/ROADMAP.md
sed -n '1,220p' README.md
```

Expected: 役割分担、現在地、直近 task が矛盾なく読める。

- [ ] **Step 3: Confirm git status only contains the intended docs changes**

Run:

```bash
git status --short
```

Expected: `README.md`、`docs/ROADMAP.md`、`docs/TASKS.md`、`docs/DEVELOPMENT_GUIDE.md` だけが変更対象として並ぶ。

- [ ] **Step 4: Commit the final docs pass**

```bash
git add README.md docs/ROADMAP.md docs/TASKS.md docs/DEVELOPMENT_GUIDE.md
git commit -m "docs: finalize development roadmap docs"
```
