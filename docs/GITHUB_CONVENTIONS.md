# GITHUB_CONVENTIONS

## Purpose

`docs/TASKS.md` を起点に、issue / PR / branch / commit の粒度をそろえて運用するための最小ルールをまとめる。

## Mapping Rules

- `docs/TASKS.md` の 1 項目を、原則として GitHub issue 1 件に対応づける
- 1 タスクが大きすぎる場合は、`TASKS.md` 側で先に分割する
- issue / PR タイトルは `TASKS.md` の文言をできるだけそのまま使う
- `In Progress` の項目だけを「今動いている GitHub 作業」とみなす

## Issue Rules

issue 本文には少なくとも以下を書く。

- 対象 milestone
- 完了条件
- 想定変更ファイル
- 必要テスト
- docs 更新の要否

## Branch Rules

- branch は 1 タスク 1 branch を原則にする
- branch 名は `codex/<short-task-slug>` を使う
- 無関係な変更は同じ branch に載せない
- docs-only タスクでも branch を分けてよい

## PR Rules

- PR は原則 1 タスク 1 PR
- PR タイトルは `TASKS.md` と揃える
- PR 本文には少なくとも以下を書く
- 何を変えたか
- 何を変えていないか
- 実行したテスト
- docs 更新内容
- 残課題または次タスク

## Commit Rules

- 小さく説明可能な単位で commit する
- 1 commit で複数タスクをまたがない
- commit message は要約を先頭に置き、必要なら本文で補足する
- docs 更新だけの commit も許容するが、対応タスクが分かるようにする

## Status Sync

- `docs/TASKS.md` を正本とし、issue / PR の状態も同じ段階へ揃える
- `In Progress` に上げたら対応 issue も着手状態にする
- 完了して test / docs / commit が終わったら `Done` に移す
- ブロックしたら code を広げず、`docs/BLOCKED.md` と GitHub の記録を同期する

## Recommended PR Size

- 差分は 1 回でレビューできる小ささに保つ
- 「説明なしでは読めない」規模になる前にタスクを分割する
- 実装、テスト、docs が同じタスクに属するなら同一 PR でよい

## Review Checklist

- 対応する `TASKS.md` 項目が明確か
- 変更は 1 タスクに収まっているか
- テスト結果が記録されているか
- README / docs 更新が必要なら含まれているか
- 次に進むタスクが見える状態か
