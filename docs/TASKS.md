# TASKS

このファイルは Codex が次に着手する実装候補を決めるための単一の作業台帳とする。  
ここでは、現在のキューを先頭に置き、完了履歴は必要な粒度まで圧縮して残す。

## In Progress

- [ ] M63g: project autonomy level を next_action_decision 制御へ接続する
  - Title: autonomy level による next_action_decision の自動適用条件を 1 箇所だけ追加する
  - Milestone: M63 Autonomous Policy
  - Purpose: project-level `autonomy_level` を、`next_action_decision` の自動適用または手動確認の分岐に接続し、contract 以外の behavior / control へ最小単位で広げる
  - Target files or directories: `src/novel_writer/pipeline.py`, `src/novel_writer/cli.py`, `tests/test_pipeline.py`, `tests/test_cli.py`, `docs/TASKS.md`, `docs/ROADMAP.md`
  - Done when: `manual` / `assist` / `auto` のいずれかが `next_action_decision` の適用可否に反映され、既存 project manifest の save-load / status contract を壊さずに説明できる
  - Required tests: `./venv/bin/python -m unittest tests.test_pipeline -v`, `./venv/bin/python -m unittest tests.test_cli -v`, `./venv/bin/python -m unittest discover -s tests -v`
  - Docs to update: `docs/TASKS.md`, `docs/ROADMAP.md`

## Ready

- なし

## Done

### Recent completions

- [x] M63f: project autonomy level contract を追加する
- [x] M63e-M63a: `next_action_decision` の schema、pipeline 保存、action mapping、target chapter validation を固定した
- [x] M62f-M62a: `replan_history` と future chapter update の基盤を固めた
- [x] M61b-M60a: `progress_report` と `chapter_handoff_packet` の共有入力を固めた
- [x] M59-M58: memory layer、canon / thread registry、chapter briefs / scene cards の基礎を整えた
- [x] M57-M54: story bible の導入と OpenAI / LM Studio 応答の扱いを固めた
- [x] M53-M42: show-run-comparison と comparison summary の read-only / compact 表示を整えた
- [x] Scaffold CLI-based short-story pipeline MVP

### Archived milestones

- `M41-M1`: pipeline 基盤、resume / rerun、quality、project layout、chapter 互換出力の土台を段階的に整備した
- `M40-M30`: `show-run-comparison` の line renderer と compact summary を整理し、比較表示の read-only 挙動を固めた
- `M29-M22`: `show-run-comparison` と `project_manifest.json` の comparison context を揃え、status 表示の語彙を machine-readable artifact に寄せた
- `M21-M19`: compact summary と manual / automatic selection の理由表示を整えた
- `M18-M16`: publish bundle、policy snapshot、rerun policy の基礎を整えた
- `M15-M13`: schema validator、schema version 方針、長編向け stop condition を固定した
- `M12-M10`: best run 比較、project-level run layout、chapter 配列ベースの互換正本を固めた
- `M9-M7`: multi-chapter draft、stop condition、per-chapter history を整えた
- `M6-M4`: GitHub / blocked-task の運用補助、continuity / revise / rerun の基礎を作った
- `M3-M1`: quality report、resume / selective rerun、chapter 1 互換出力を段階的に追加した

## Task Update Rules

- `In Progress` は常に 1 件まで
- 完了したら `Done` へ移す
- `Ready` が残っている場合は、次の最上位 `Ready` を `In Progress` へ上げる
- `Ready` が空の場合は、`docs/ROADMAP.md` と現在のコードを確認し、次のマイルストーンに必要な最小子タスクを `Ready` に追加する
- 新規子タスクを追加した場合は、その先頭 1 件を `In Progress` へ上げる
- 大きすぎる項目は着手前に分割する
- docs-only タスクでも、README / tests / task 状態更新の要否を確認する
- ブロックしたら `docs/BLOCKED.md` を更新し、原因・試したこと・次に必要な判断を書く
