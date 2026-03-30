# DEVELOPMENT GUIDE

## Purpose

この文書は、`auto-novel-writer` の開発者と将来の協力者が、機能追加の優先順位と task 分解を同じ基準で判断するためのガイドである。

## Document Roles

- `AGENTS.md`: repository 全体の恒久ルール
- `docs/CODEX_WORKFLOW.md`: Codex の実行手順
- `docs/ROADMAP.md`: 中長期の到達点と milestone の見取り図
- `docs/TASKS.md`: 直近の最小安全 task queue
- `docs/DEVELOPMENT_GUIDE.md`: 優先順位、設計原則、task 分解基準

## Current Development Stage

- その時点の active task は `TASKS.md` の先頭から読む
- 対応する milestone は `ROADMAP.md` で確認する
- この guide は、両者をどう解釈し、どう task 化するかの基準だけを定義する

## Priority Rules

- CLI と artifact contract を先に固める
- fail-fast を優先し、暗黙 fallback を足さない
- 新規機能より、既存 layer の接続完成を優先する
- UI や派生機能より、long-form の control、評価、publish / handoff、運用改善を優先する
- long-form の成長では、1 回の生成を大きくするより、状態を artifact として分け持ち、工程ごとに確認しやすい形を先に整える
- 1 回の変更は小さく安全に閉じ、tests と docs まで同期する

## Feature Addition Policy

- 新 artifact は、既存 artifact では責務を表現できない場合のみ追加する
- 新機能は、それが設計、分解、本文生成、検査、再計画、改稿、publish / handoff、運用確認のどの責務を支えるかを明確にしてから追加する
- 既存 contract を拡張するときは、validator / storage / pipeline / tests / docs を同時に更新する
- project-level policy は、まず contract / save-load / status 表示を固定し、その後に behavior / control を 1 gate ずつつなぐ
- long-form の成長では、モデルを強くする前に、状態を artifact に分けて持ち、各工程で確認し、あとで統合しやすい形を優先する
- LLM access は、既存 client 境界の内側に閉じ込める
- docs-only で足りるのは、振る舞いが変わらず説明だけを整える場合に限る
- 振る舞いが変わるときは、README を現状仕様として同期する
- 将来機能の詳細は README に先書きせず、`ROADMAP.md` と本 guide に寄せる

## Milestone Outlook

- 次の task は、`ROADMAP.md` にある capability axes を基準に選ぶ
- 軸の例は publish / handoff、story state、evaluation、operational である
- この guide は、どの軸を選ぶべきかを固定せず、選び方の基準だけを示す
- 未実装の方向性をこの文書で先取りして確定しない

## How To Turn Roadmap Into Tasks

- 1 task は 1 回で実装・tests・docs 更新・commit まで閉じる粒度にする
- milestone 完了条件は、schema / storage / pipeline / tests / docs のどこで満たすかを先に分けて考える
- 仕様判断が一意でない場合は、task 化を進めず、まず論点を分解する
- task は、ひとつの contract 変更で安全に閉じられる最小単位にする
- task は、将来の分業オーケストレーションを支えられる artifact と制御の境界に沿って切る
- task 名よりも、どの contract を fail-fast に固定するかを先に決める

## Docs Sync Rules

- `ROADMAP.md` は「何を目指すか」を書く
- `TASKS.md` は「次に何をやるか」を書く
- `DEVELOPMENT_GUIDE.md` は「どう判断して順序づけるか」を書く
- 実装で振る舞いが変わったときは README も同期する
- 役割が重なる場合は、最初に `ROADMAP.md` と `TASKS.md` へ寄せ、guide には判断基準だけを残す
