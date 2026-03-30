# Orchestration Roadmap Wording Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 長編生成を分業された制作工程のオーケストレーションとして育てる方針を、`ROADMAP.md` と `DEVELOPMENT_GUIDE.md` に役割分担を崩さず反映する。

**Architecture:** `ROADMAP.md` には思想レベルの短い追記だけを入れ、`DEVELOPMENT_GUIDE.md` には task 分解と優先順位判断の基準として具体化する。`README.md` や `TASKS.md` には触れず、将来仕様の固定も行わない。

**Tech Stack:** Markdown documentation

---

### Task 1: `ROADMAP.md` にオーケストレーション指向を追記する

**Files:**
- Modify: `docs/ROADMAP.md`

- [ ] **Step 1: `Product Direction` に追記する文章を追加する**

```md
この project は、1 回の大きな本文生成を強くすること自体を目的にしない。
目指すのは、設計、分解、本文生成、検査、再計画、改稿を分業できる制作システムであり、
長編化は単一生成の長さではなく、その工程を壊さず統合できることによって達成する。
```

- [ ] **Step 2: diff を確認して、`ROADMAP.md` の役割が変わっていないことを確かめる**

Run: `git diff -- docs/ROADMAP.md`
Expected: milestone や task の詳細ではなく、思想レベルの追記だけが入っている

- [ ] **Step 3: Task 1 を commit する**

```bash
git add docs/ROADMAP.md
git commit -m "docs: frame roadmap around orchestration"
```

### Task 2: `DEVELOPMENT_GUIDE.md` に判断基準を追記する

**Files:**
- Modify: `docs/DEVELOPMENT_GUIDE.md`

- [ ] **Step 1: `Priority Rules`、`Feature Addition Policy`、`How To Turn Roadmap Into Tasks` に判断基準を追記する**

```md
# Priority Rules
- 長編化では、単一生成の拡大より、分業しやすい artifact 境界と control 境界を優先する
```

```md
# Feature Addition Policy
- 新機能は、設計、分解、本文生成、検査、再計画、改稿のどの責務を支えるかを明確にしてから追加する
- 長編化のためには、モデル能力そのものより state の外部化、工程ごとの検査、統合時の正本管理を優先する
```

```md
# How To Turn Roadmap Into Tasks
- task は、将来の分業オーケストレーションに耐える artifact 境界と control 境界で切る
```

- [ ] **Step 2: docs-only 変更の整合を確認する**

Run: `git diff --check`
Expected: no output

- [ ] **Step 3: Task 2 を commit する**

```bash
git add docs/DEVELOPMENT_GUIDE.md
git commit -m "docs: add orchestration tasking guidance"
```

## Self-Review

- Spec coverage:
  - `ROADMAP.md` への思想レベル追記は Task 1 で実装する
  - `DEVELOPMENT_GUIDE.md` への判断基準追記は Task 2 で実装する
  - `README.md` や `TASKS.md` を触らない制約は plan 全体で守っている
- Placeholder scan:
  - `TODO`、`TBD`、曖昧な「適切に追記する」は残していない
- Type consistency:
  - `分業`, `オーケストレーション`, `artifact 境界`, `control 境界` の語彙を統一した
