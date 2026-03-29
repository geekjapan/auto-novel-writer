# CODEX_WORKFLOW

## Purpose

Codex がこのリポジトリで、停止条件に該当するまで 1 タスクずつ安全に実装を前進させ続けるための標準手順を定義する。

## Source Of Truth

優先順は以下とする。

1. `AGENTS.md`
2. `docs/TASKS.md`
3. `docs/ROADMAP.md`
4. `README.md`

使い分け:

- `AGENTS.md`: リポジトリ全体の恒久ルール
- `TASKS.md`: 今まさに着手すべき作業単位
- `ROADMAP.md`: 現在地と次段階
- `README.md`: 利用者向け現状仕様

## Standard Loop

1. `AGENTS.md`、`docs/TASKS.md`、`docs/CODEX_WORKFLOW.md`、必要に応じて `docs/ROADMAP.md` を読む
2. `docs/TASKS.md` の `In Progress` 先頭 1 件を現在タスクとして扱う
3. `In Progress` が空なら `Ready` の先頭を `In Progress` に上げてから着手する
4. 現在タスクの完了条件を確認し、必要最小限の変更だけを入れる
5. 新規・変更された振る舞いに対応するテストを追加または更新する
6. 振る舞い、CLI、artifact contract、運用ルールが変わったら `README.md` と該当 docs を更新する
7. テストを実行する
8. `docs/TASKS.md` の状態を更新する
9. 小さなコミットを作る
10. 停止条件に該当しない限り、ユーザーの追加指示を待たずに次のループへ進む
11. `Ready` が残っていれば、次の最上位 `Ready` を `In Progress` に上げ、同じ手順で次タスクへ進む
12. `Ready` が空なら、`docs/ROADMAP.md` と repository の現状から次の最小子タスクを起票し、その先頭 1 件を `In Progress` に上げて続行する
13. 停止条件に該当する場合だけ停止し、`docs/BLOCKED.md` を更新する

補足:

- docs 更新タスクでも、対応する code / tests / artifact contract を実際に読んでから書く
- tests だけで完了する小タスクでも、`docs/TASKS.md` は同じターンで更新する
- read-only CLI のタスクでは、可能なら「出力内容」だけでなく「artifact を変更しないこと」も確認する
- Standard Loop は 1 回の実行で終わらせず、停止条件に該当するまで同一セッション内で繰り返す
- 停止条件に該当しない場合、Codex はユーザーの追加指示待ちを標準動作にしない

## Guardrails

- 1 回の主目的は 1 タスクだけにする
- リファクタは現在タスク達成に必要な範囲に限定する
- 依存追加は必要最小限にする
- OpenAI 関連の変更は `src/novel_writer/llm/` 境界の中に閉じ込める
- 既存の artifact 名や CLI を壊す変更は、互換層か docs での明示なしに行わない
- `README` に未来機能を書かない

## When To Stop

以下では推測で広げずに停止する。

- 現在タスクの受け入れ条件が docs だけでは解決できず、コード仕様の判断が必要
- 既存ユーザーの利用方法を大きく変える可能性がある
- どの挙動を正とするか、実装と docs のどちらを基準にすべきか判断できない
- 作業中にユーザー変更と衝突する差分を見つけた
- 既存 validator / schema contract が task 文面と矛盾し、どちらを正とするか docs だけでは決められない

停止時は `docs/BLOCKED.md` を更新し、必要ならユーザーに判断を求める。

## When To Ask For Human Direction

- 外部仕様を破るかもしれない rename / remove が必要
- 互換維持より整理を優先すべきか決められない
- タスクが大きすぎて分割方針に複数の妥当案がある
- OpenAI API 利用方針や評価軸のように、プロダクト判断が必要

## Definition Of Done

- 現在タスクの完了条件を満たす
- 必要なコード、テスト、docs がそろっている
- テスト結果を確認している
- `docs/TASKS.md` が更新されている
- 変更理由を短いコミット単位で説明できる

## Status Sync

- `docs/TASKS.md` を実装順の正本とする
- GitHub issue / PR / branch は `TASKS.md` と同じ粒度へ寄せる
- ブロック時は `docs/BLOCKED.md` と GitHub 側の状態を同期する

## Notes For Docs Work

- docs-only のタスクでも、実装とずれていないかコードを確認する
- README は「現状仕様」、ROADMAP は「次段階」、TASKS は「直近キュー」に役割を分ける
- docs 間で同じ説明を重複させすぎず、参照関係を明確にする
