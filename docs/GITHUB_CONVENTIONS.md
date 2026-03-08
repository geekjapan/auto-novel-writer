# GITHUB_CONVENTIONS

## Purpose

`docs/TASKS.md` を起点に、GitHub issue / PR / branch の粒度を揃えて運用するための最小ルールをまとめる。

## Issue Rules

- `docs/TASKS.md` の 1 項目を GitHub issue 1 件に対応づける
- issue タイトルは `TASKS.md` の文言をできるだけそのまま使う
- issue 本文には少なくとも以下を書く
- 対象 milestone
- 完了条件
- 変更対象の想定ファイル
- 必要テスト
- `In Progress` に上げたタイミングで issue も着手状態にする

## Branch Rules

- branch は 1 タスク 1 branch を原則にする
- branch 名は `codex/<short-task-slug>` を使う
- 無関係な変更は同じ branch に載せない

## Pull Request Rules

- PR は原則 1 タスク 1 PR に寄せる
- PR タイトルも `TASKS.md` の文言に近づける
- PR 本文には少なくとも以下を書く
- 何を変えたか
- 何を変えていないか
- 実行したテスト
- 残課題または既知の制約

## Status Sync

- `docs/TASKS.md` を実装順の正本とする
- issue / PR の状態は `docs/TASKS.md` と同じ段階に揃える
- 1 件を `In Progress` に上げたら、対応 issue も着手状態にする
- 完了して commit / test / docs 更新が終わったら `Done` に移し、対応 PR も closing できる状態にする
- ブロックしたら code を広げず、`docs/BLOCKED.md` を追加して issue / PR に同じ内容を反映する
- ブロック解除後は `docs/BLOCKED.md` の更新有無と `TASKS.md` の状態変更理由を PR に残す

## Recommended PR Size

- 差分は 1 回でレビュー可能な小ささに保つ
- 目安として「説明なしでは読み切れない変更」になる前にタスクを分割する
- docs のみ、テストのみ、実装のみの小分けは許容するが、無関係な抱き合わせは避ける
