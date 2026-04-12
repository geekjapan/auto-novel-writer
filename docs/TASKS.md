# TASKS

このファイルは Codex が次に着手する実装候補を決めるための単一の作業台帳とする。  
ここでは、現在のキューを先頭に置き、完了履歴は必要な粒度まで圧縮して残す。

## In Progress

- [ ] M71a: Story State 共有断面の docs 参照面を comparison / status / publish で整理する

## Ready

- [ ] M71b: Story State 共有断面の source-of-truth を ROADMAP / guide / README で揃える


## Done

### Recent completions

- [x] M70c: action / reason / decision_trace と comparison reason_detail の docs 用語を分離する
- [x] M70b: saved next_action_decision の read-only view と docs wording を揃える
- [x] M70a: next_action_decision の action reason と autonomy policy の docs 棚卸しを始める
- [x] M69e: story_state_summary の docs 用語を publish bundle summary label と照合する
- [x] M69d: story_state_summary の docs 用語を status / comparison helper 名と照合する
- [x] M69c: status / comparison / publish で参照する story_state_summary の docs 用語を揃える
- [x] M69b: story_state_summary の source of truth と read-only consumer の wording を README / guide で揃える
- [x] M69a: story_state_summary の保存タイミングと参照面を docs 上で棚卸しする
- [x] M68f: README / AGENTS / workflow の read order と docs roles を微調整する
- [x] M68e: AGENTS / workflow / guide の docs 参照差分を整理する
- [x] M68d: DEVELOPMENT_GUIDE に long-running autonomy の再計画基準と既定実行方式を同期する
- [x] M68c: `ROADMAP.md` に M68〜M90 の wording を反映する
- [x] M68b: `BLOCKED.md` を long-running autonomy 向けテンプレートへ更新する
- [x] M68a: long-running autonomy workflow の replan / stop ルールを docs で固定する

- [x] M67b: lock legacy publish bundle story_state_summary backfill in read-only CLI tests
- [x] M67a: surface saved decision snapshot in best-run and run comparison views
- [x] M66a: carry shared story_state_summary into next_action_decision and replan history
- [x] M65b: add shared story_state_summary to progress_report and publish bundle
- [x] M65a: add unresolved thread snapshots to chapter_handoff_packet

- [x] M64d: publish bundle に handoff summary を追加する
- [x] M64c: publish bundle に thread summary を追加する
- [x] M64b: publish bundle に story bible summary を追加する
- [x] M64a: publish bundle の status 要約を保存済み summary と揃える
- [x] M63i: manual review gate 判定を status と resume で共通化する
- [x] M63h: manual project の review gate を status から見えるようにする
- [x] M63g: manual project は review-required decision で resume-project を停止する
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
