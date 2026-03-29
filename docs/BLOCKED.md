# BLOCKED

現在の `In Progress` タスクが、推測では安全に前進できないときだけ更新する。  
「実装を止める理由」と「次に必要な判断」を最小コストで共有するためのテンプレートとして使う。

## Task

- タスク名: M63 の次子タスク（autonomy level contract）
- milestone: M63 Autonomous Policy
- 関連 issue / PR:

## Symptoms

- 事実ベースの症状: `next_action_decision` の schema / save-load / pipeline save / action mapping / `target_chapters` validator までは固定できたが、その次の ROADMAP 完了条件にある「project 単位で autonomy level を切り替えられる」の仕様が repository 内で未定義である。
- どこで止まったか: `docs/TASKS.md` の `Ready` を空にしたあと、`docs/ROADMAP.md` を根拠に次の最小子タスクを起票する段階で停止した。
- 影響範囲: M63 の継続実装、特に project manifest / CLI / schema / docs にまたがる autonomy 設定の追加。

## Tried

- 試したこと: `README.md`、`docs/ROADMAP.md`、`docs/TASKS.md`、`src/novel_writer/schema.py`、`src/novel_writer/pipeline.py`、関連 tests を確認し、既存 docs 内に autonomy level の列挙値や保存先がないか調べた。
- 確認したファイル / artifact: `README.md`、`docs/ROADMAP.md`、`docs/TASKS.md`、`docs/CODEX_WORKFLOW.md`、`src/novel_writer/schema.py`、`src/novel_writer/pipeline.py`、`tests/test_pipeline.py`、`tests/test_storage.py`
- 分かったこと: repository 内で明示されている M63 の残件は「project 単位で autonomy level を切り替えられる」だけだが、`autonomy level` の候補値、保存場所、既定値、`next_action_decision` や pipeline への影響が定義されていない。

## Options

- 候補案 1: `project_manifest.json` に `autonomy_level` を追加し、`manual` / `assist` / `auto` のような列挙型を新設する。
- 候補案 2: run 単位 manifest に `autonomy_policy` を保存し、project 単位ではなく run 単位設定として扱う。
- 各案のトレードオフ: 候補案 1 は ROADMAP 文面の「project 単位」と整合しやすい一方で、project manifest schema の互換性判断が必要である。候補案 2 は実装範囲が狭いが、ROADMAP 文面とずれる可能性がある。

## Needed Decision

- 次に必要な判断: `autonomy level` の列挙値、保存先 artifact、既定値、CLI 露出有無を決めること。
- 必要な追加情報: 「manual / assist / auto」のような levels を採るのか、あるいは boolean / phase-based policy にするのか。
- ユーザーまたはレビューアに確認したい点: project 単位 autonomy level はどの値を持つべきか。また、その設定は `project_manifest.json` に保存する前提でよいか。

## Status Sync

- `docs/TASKS.md` を `In Progress` のまま維持するか、`Ready` に戻すか: `In Progress` は空のままにし、次タスクはユーザー判断後に再起票する。
- GitHub issue / PR に反映した内容:
- 再開条件: autonomy level の contract が決まり、最小子タスクへ分割できること。
