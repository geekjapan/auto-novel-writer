# Development Roadmap Design

## Summary

本 spec は、`auto-novel-writer` の今後の開発・機能追加に向けて、
既存の `docs/ROADMAP.md`、`docs/TASKS.md`、新規追加する開発ガイド文書の
役割分担と記述方針を整理するための design である。

目的は、次の 3 点である。

1. 中長期のプロダクト方向と直近の実装キューを混ぜずに管理できるようにする
2. 開発者と将来の協力者が、何を優先し、どう task に落とすかを同じ基準で判断できるようにする
3. M63 以降の control layer、publish layer、story state layer の拡張を、ぶれない方針で継続できるようにする

この変更は、主に docs の責務整理と新規 docs 追加を対象とする。
artifact contract や CLI 仕様の変更は、この spec 自体の対象外である。

## Problem Statement

現状の repository には `AGENTS.md`、`docs/CODEX_WORKFLOW.md`、`docs/ROADMAP.md`、
`docs/TASKS.md` があり、直近の実装順や作業ルールはある程度明文化されている。

一方で、今後の開発・機能追加を考える際に、次の問題が残っている。

- `ROADMAP.md` が「長期の到達点」と「今どこを優先するか」の両方を背負いやすい
- `TASKS.md` は直近の安全な 1 task を管理するには適しているが、なぜその順番なのかの判断基準は十分に集約されていない
- 将来の協力者が入ったときに、「何を実装候補にしてよいか」「何を後回しにすべきか」が docs だけでは読み取りにくい
- M64 以降の未着手領域をどう分割して task 化していくかの方針が、個々の issue 起票時に暗黙知へ寄りやすい

その結果、docs が増えても「どの文書を見て何を判断するか」が曖昧になり、
ロードマップの更新と task 起票の一貫性が落ちるリスクがある。

## Goals

- `docs/ROADMAP.md` を中長期のプロダクト到達点と milestone 見取り図の正本として維持する
- `docs/TASKS.md` を直近の最小安全 task キューの正本として維持する
- 新規 docs を追加し、優先順位基準、機能追加ポリシー、長期見取り図、task 分解ルールを明文化する
- 開発者と協力者のどちらが読んでも、現在地と次の判断基準が分かる構成にする
- M63 残件、M64、その先の長期候補までを、実装順序の理由つきで説明できるようにする

## Non-Goals

- 既存 artifact schema、storage contract、CLI contract の変更
- 具体的な feature 実装や milestone 完了そのもの
- `ROADMAP.md` と `TASKS.md` を 1 つの文書へ統合すること
- すべての将来機能を細粒度 task まで先回りで起票すること

## Design

### 1. Docs Responsibility Split

docs の責務は次の 3 層へ明確に分ける。

#### `docs/ROADMAP.md`

- プロダクトの最終目標
- 現在の能力と不足能力
- milestone の順序と依存関係
- 「次にどの milestone を攻めるべきか」という中期判断

ここでは、長期の能力地図を保つことを優先する。
細かい task 粒度や日々の queue 管理は持たせない。

#### `docs/TASKS.md`

- 直近で安全に実装できる単一 task
- 完了条件
- 必要な tests
- 更新すべき docs
- `In Progress` / `Ready` / `Done` の状態管理

ここでは、実装実務の queue を保つことを優先する。
なぜその milestone が重要かという説明は、必要最小限に留める。

#### 新規 docs: `docs/DEVELOPMENT_GUIDE.md`

- 優先順位の判断基準
- 機能追加の設計原則と境界線
- milestone をどう task に分解するか
- 中長期ロードマップをどの能力軸で伸ばすか

この文書は、`ROADMAP.md` と `TASKS.md` の間をつなぐ判断基準の正本として扱う。

### 2. New Guide Structure

新規 docs は `docs/DEVELOPMENT_GUIDE.md` とし、次の章立てを持つ。

1. `Purpose`
2. `Document Roles`
3. `Current Development Stage`
4. `Priority Rules`
5. `Feature Addition Policy`
6. `Milestone Outlook`
7. `How To Turn Roadmap Into Tasks`
8. `Docs Sync Rules`

各章の役割は次のとおりである。

#### `Purpose`

この文書が、開発者と協力者の共通判断基準であることを明記する。

#### `Document Roles`

`AGENTS.md`、`docs/CODEX_WORKFLOW.md`、`docs/ROADMAP.md`、`docs/TASKS.md`、
新規 docs の役割分担を簡潔に整理する。

#### `Current Development Stage`

現時点では M63 の残件と M64 以降が主戦場であること、
導入済み artifact 群と未完了論点を短くまとめる。

#### `Priority Rules`

優先順位判断の基準を明文化する。
最低限、次を含める。

- CLI と artifact contract を先に固める
- fail-fast を優先し、暗黙 fallback を足さない
- 新機能より既存 layer の接続完成を優先する
- UI や派生機能より、long-form control / evaluation / handoff を優先する
- 1 回の変更は小さく安全に閉じる

#### `Feature Addition Policy`

機能追加時の境界線を明文化する。
最低限、次を含める。

- 新 artifact を追加してよい条件
- 既存 artifact contract を拡張するときの条件
- LLM access は既存 client 境界へ閉じ込めること
- docs-only 変更で済ませてよいケースと、code / tests 同期が必要なケース
- 将来機能を README へ先書きしないこと

#### `Milestone Outlook`

今後のロードマップを、個別機能ではなく能力軸で並べる。
最低限、次の 5 軸を扱う。

1. `Control Layer の完成`
2. `Publish / Handoff Layer の強化`
3. `Story State Layer の深化`
4. `Evaluation Layer の深化`
5. `Operational Layer の強化`

M63 残件、M64、その先の長期候補はこの軸に沿って整理する。

#### `How To Turn Roadmap Into Tasks`

長期項目を `TASKS.md` へ落とすルールを記す。
最低限、次を含める。

- 1 task は 1 回で実装・tests・docs 更新・commit まで閉じる粒度にする
- milestone 完了条件を、schema / storage / pipeline / tests / docs のどこに分けるかを先に考える
- 仕様判断が一意でない場合は `docs/BLOCKED.md` を更新して止まる
- `Ready` が空のときだけ、次の子 task を起票する

#### `Docs Sync Rules`

docs 間の同期ルールを簡潔にまとめる。

- `ROADMAP.md` は「何を目指すか」
- `TASKS.md` は「次に何をやるか」
- `DEVELOPMENT_GUIDE.md` は「どう判断して順序づけるか」
- 実装で振る舞いが変わったときは README も更新する

### 3. Long-Term Roadmap Framing

今後の機能追加は、「機能名の羅列」ではなく「能力層」で整理する。

理由は次のとおりである。

- 現在の repository は artifact 中心の設計であり、個別機能より layer 単位で依存関係を見たほうが分割しやすい
- M63 以降は control、publish、evaluation のように複数 artifact / CLI / docs を跨ぐ変更が増える
- 将来の協力者にとっても、「どの能力を伸ばす変更か」が分かったほうが参加しやすい

能力軸ごとの見取り図は次のように置く。

#### Control Layer の完成

- M63 残件の `autonomy level`
- project 単位の自律制御方針
- 将来的な自動 rerun / revise / replan の制御範囲整理

#### Publish / Handoff Layer の強化

- M64 の publish bundle 強化
- editor handoff、review handoff、summary artifact の整備
- best run 比較時の long-form progress 指標取り込み

#### Story State Layer の深化

- `canon_ledger` / `thread_registry` の検索性や参照性の強化
- 将来候補の `character_state`
- 長編途中での state 再利用精度向上

#### Evaluation Layer の深化

- `progress_report` の評価精度改善
- 中盤停滞、章役割、感情線、伏線回収などの検査強化
- rerun / revise / replan / stop の境界判断の改善

#### Operational Layer の強化

- status / comparison / resume / rerun の運用性向上
- block 時の診断性向上
- read-only CLI と artifact 表示の整理

### 4. Recommended Rollout

docs 整備の実施順は次のとおりとする。

1. `docs/DEVELOPMENT_GUIDE.md` を新規追加する
2. `docs/ROADMAP.md` を、新しい判断基準との整合が取れるように見直す
3. `docs/TASKS.md` の直近 task が、新しい優先順位方針と矛盾しないことを確認する
4. 必要に応じて `README.md` の現状説明を同期する

## Risks And Mitigations

### Risk: docs が増えて、どれを見ればよいか逆に分かりにくくなる

Mitigation:
新規 docs 冒頭に文書ごとの役割分担を書く。
また、`ROADMAP.md` と `TASKS.md` にも新規 docs への参照を追加する。

### Risk: 新しい guide が抽象論に寄り、実運用で使われない

Mitigation:
優先順位基準と task 分解ルールを具体的に書き、
M63 残件と M64 を例として直接言及する。

### Risk: 長期候補を書きすぎて、README と混線する

Mitigation:
README は現状仕様に限定し、
未実装の方向性は `ROADMAP.md` と `DEVELOPMENT_GUIDE.md` へ寄せる。

## Testing And Verification

この変更は docs 中心のため、最低限次を確認する。

- 新規 docs の役割が `ROADMAP.md`、`TASKS.md`、`AGENTS.md` と矛盾しない
- `ROADMAP.md` の中期 focus と `TASKS.md` の `In Progress` が整合する
- 長期見取り図が、現在の実装済み能力と矛盾しない
- placeholder、曖昧表現、未定義の略語を残さない

## Open Decisions Resolved In This Spec

本 spec では次の判断を確定する。

- 新しい docs は追加する
- 読み手は開発者と将来の協力者の両方とする
- 新しい docs は優先順位基準、設計原則、マイルストーン見取り図をまとめて持つ
- ロードマップ整備の時間軸は、直近だけでなく長期の未着手領域まで含める
- docs の責務は統合せず、役割分離を維持する

## Rollout

1. 新規 docs を追加する
2. `ROADMAP.md` の immediate focus と long-term outlook を再点検する
3. `TASKS.md` の current task と新しい guide の優先順位基準を揃える
4. docs 全体を自己点検し、矛盾や曖昧さを除去する
5. spec を commit し、ユーザー確認後に implementation plan へ進む
