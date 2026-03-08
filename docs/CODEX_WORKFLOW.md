# CODEX_WORKFLOW

## Purpose

Codex が人手の往復を最小化しつつ、小さな安全な単位で実装を前進させる。

## Standard Loop

1. `docs/ROADMAP.md` を読んで現在のマイルストーンを確認する
2. `docs/TASKS.md` を読み、`In Progress` の最上位 1 件を現在タスクとする
3. `In Progress` が空なら `Ready` の最上位を `In Progress` に上げてから着手する
4. 現在タスクの達成に必要な最小変更だけを実装する
5. 関連テストを追加または更新し、既存テストを実行する
6. 振る舞いが変わったら `README.md` と該当 docs を更新する
7. `docs/TASKS.md` の状態を更新する
8. 小さいコミットを作る
9. 未完の `Ready` が残っていれば同じループを続ける

## Guardrails

- 1 回の作業で扱う主目的は 1 つだけにする
- リファクタは現在タスク達成に必要な範囲へ限定する
- 依存追加は必要最小限にする
- OpenAI 関連コードは専用 client/module の境界内に閉じ込める
- 既存の CLI 振る舞いと成果物名を壊す変更は、互換レイヤーなしでは行わない
- 変更後は必ずテストを実行する

## GitHub Tracking

- `docs/TASKS.md` の各項目は GitHub issue 1 件に対応づける想定で扱う
- 実装は原則として 1 issue = 1 小コミット以上、1 PR = 1 タスクに寄せる
- issue / PR タイトルは `TASKS.md` の文言をできるだけそのまま使う
- 進捗の正本はコードと `docs/TASKS.md`、GitHub では同じ状態を反映する
- 詳細な運用ルールは `docs/GITHUB_CONVENTIONS.md` を参照する

## Definition of Done

- 現在タスクの受け入れ条件を満たす
- 新規または変更された振る舞いにテストがある
- テストが通る
- `docs/TASKS.md` が更新されている
- 変更理由が短いコミット単位で説明できる

## If Blocked

- 推測で広げずに停止する
- `docs/BLOCKED.md` の template を使って記録する
- `docs/TASKS.md` の状態と GitHub issue / PR の状態を同じ理由で同期する
- 記録する内容
- 詰まっているタスク名
- 事実ベースの症状
- 試したこと
- 次に必要な判断または情報
