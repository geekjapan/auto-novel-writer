# BLOCKED

現在の `In Progress` タスクが、推測では安全に前進できないときだけ更新する。  
「実装を止める理由」と「次に必要な判断」を最小コストで共有するためのテンプレートとして使う。

## Task

- タスク名: M60a: `chapter_handoff_packet` の schema を固定する
- milestone: M60 Chapter Handoff Packet
- 関連 issue / PR: なし

## Symptoms

- 事実ベースの症状: `docs/ROADMAP.md` には `chapter_handoff_packet` へ含める概念として `style / POV / tense constraints` があるが、repository 内の既存 schema / tests / docs には `tense` の正本 field 名や packet 内 object の shape が存在しない。
- どこで止まったか: `src/novel_writer/schema.py` に contract を追加する前の field 設計段階で停止した。
- 影響範囲: `chapter_handoff_packet` の validator、storage helper、後続の packet 生成・LLM 利用のすべてに影響する。

## Tried

- 試したこと: `README.md`、`docs/ROADMAP.md`、`docs/TASKS.md`、`src/novel_writer/schema.py`、`src/novel_writer/pipeline.py`、`tests/` 全体を検索し、`handoff`、`POV`、`pov`、`tense`、`style constraints`、`previous chapter summary`、`unresolved threads` の既存語彙を確認した。
- 確認したファイル / artifact: `docs/ROADMAP.md`, `docs/TASKS.md`, `README.md`, `src/novel_writer/schema.py`, `src/novel_writer/pipeline.py`, `tests/test_storage.py`, `tests/test_pipeline.py`, `tests/test_rerun_policy.py`
- 分かったこと: `point_of_view` / `pov_character` は既存語彙がある一方で、`tense` と `style constraints` の field 名、top-level shape、object 名は repository 内で未定義である。

## Options

- 候補案 1: `style_constraints` object を新設し、`tone`, `point_of_view`, `tense` を持たせる
- 候補案 2: `narrative_constraints` object を新設し、`tone`, `point_of_view`, `tense`, `style_notes` を持たせる
- 各案のトレードオフ: 候補案 1 は最小だが将来拡張時に再編の可能性がある。候補案 2 は拡張しやすいが、現時点の docs だけでは過剰設計になる。

## Needed Decision

- 次に必要な判断: `chapter_handoff_packet` における constraints object の正本名と required field をどれにするか。
- 必要な追加情報: `tense` を first contract に入れるか、いったん TODO 扱いで除外するかの判断。
- ユーザーまたはレビューアに確認したい点: `style / POV / tense constraints` を `style_constraints` として固定してよいか。よい場合、required field は `tone`, `point_of_view`, `tense` の 3 つでよいか。

## Status Sync

- `docs/TASKS.md` を `In Progress` のまま維持するか、`Ready` に戻すか: `In Progress` のまま維持
- GitHub issue / PR に反映した内容: なし
- 再開条件: constraints object の正本名と required field が 1 つに決まること
