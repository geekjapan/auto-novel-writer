# Orchestration Roadmap Wording Design

## Purpose

長編生成を「単一の大きな本文生成」ではなく、「分業された制作工程をオーケストレーションするシステム」として育てる方針を、既存 docs の役割分担を壊さずに明文化する。

## Scope

今回の変更に含めるもの:

- `docs/ROADMAP.md` に、長編生成を分業された制作工程のオーケストレーションとして育てる方向性を短く追記する
- `docs/DEVELOPMENT_GUIDE.md` に、task 分解と優先順位判断がその方向を支えることを明記する

今回の変更に含めないもの:

- 新しい docs の追加
- 具体的な agent 構成や実装方式の固定
- `README.md` への将来方針の追記
- `docs/TASKS.md` の現在キュー変更

## Design

### ROADMAP

`docs/ROADMAP.md` では、`Product Direction` の中で次を短く明記する。

- この project は 1 回の大きな本文生成を目指すのではない
- 目指すのは、設計、分解、本文生成、検査、再計画、改稿を分業できる制作システムである
- 長編化は、単一生成の長さではなく、工程を壊さず統合できることによって達成する

ここでは思想レベルに留め、具体的な agent 役割や execution model までは書かない。

### DEVELOPMENT GUIDE

`docs/DEVELOPMENT_GUIDE.md` では、判断基準として次を追記する。

- task 分解は、分業しやすい artifact 境界と control 境界を優先する
- 新機能は、設計、分解、本文生成、検査、再計画、改稿のどの責務を支えるかを明確にしてから追加する
- 長編化のためには、モデル能力そのものより state の外部化、工程ごとの検査、統合時の正本管理を優先する

追記先は `Priority Rules`、`Feature Addition Policy`、`How To Turn Roadmap Into Tasks` の範囲に留める。

## Constraints

- `ROADMAP.md` は中長期の到達点と milestone の地図のまま保つ
- `DEVELOPMENT_GUIDE.md` は判断基準に留める
- docs は思想を明確にするが、未実装の詳細仕様は固定しない

## Out Of Scope Follow-up

将来、分業オーケストレーションの具体的な execution model や agent roles を定義する場合は、別 spec として切り出す。その時点で初めて task queue や専用 docs の追加を検討する。
