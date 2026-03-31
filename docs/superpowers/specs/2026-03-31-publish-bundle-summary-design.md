# Publish Bundle Summary Design

## Summary

`publish_ready_bundle.json` に machine-readable な `summary` object を追加し、CLI の read-only 表示はその保存済み summary を source of truth として使う。
この task は publish bundle の保存内容と表示内容を 1 つの正本へ寄せ、後続の M64 で bundle を強化するときに保存と表示の差分が広がりにくい土台を作る。

## Goal

- `publish_ready_bundle.json` に軽量な `summary` object を保存する
- CLI の publish bundle 要約表示が、その保存済み `summary` を参照するようにする
- publish bundle の本体本文や quality report 詳細は増やさず、read-only summary だけを追加する

## Non-Goals

- `publish_ready_bundle` を別 artifact に分割すること
- CLI 向けの整形済み文字列配列を artifact に保存すること
- synopsis や chapter 本文の追加要約を新たに生成すること
- publish bundle の大規模拡張や M64 全体を一気に完了させること

## Summary Shape

`publish_ready_bundle.json` の top-level に `summary` を追加する。

```json
{
  "summary": {
    "title": "Example Title",
    "chapter_count": 3,
    "section_names": ["manuscript", "story_summary", "quality"],
    "source_artifact_names": [
      "story_summary.json",
      "project_quality_report.json",
      "revised_chapter_{n}_draft.json"
    ]
  }
}
```

### `summary` に含める項目

- `title`
  - bundle タイトル
- `chapter_count`
  - 含まれる章数
- `section_names`
  - bundle の `sections` に含まれる名前の配列
- `source_artifact_names`
  - `source_artifacts` の値一覧

### 今回は入れない項目

- synopsis 本文
- chapter 本文
- chapter 見出し一覧
- quality report の詳細
- CLI 表示専用の lines

## Source Of Truth

- 保存正本: `publish_ready_bundle.json.summary`
- CLI 表示: 保存済み `summary` から line を組み立てる helper

pipeline は `summary` を保存する責務を持ち、CLI はその保存済み data を read-only で整形するだけに留める。

## Compatibility

既存の `publish_ready_bundle.json` には `summary` が無い可能性がある。

そのため挙動は次のようにする。

- 新規 pipeline 実行で保存される bundle
  - `summary` を必ず含む
- 既存 bundle を CLI が読む場合
  - `summary` があればそれを使う
  - `summary` が無ければ、既存 top-level fields (`title`, `chapter_count`, `sections`, `source_artifacts`) から互換的に組み立てる

この互換読みは CLI の read-only 表示に限定し、既存 bundle を自動で書き換えない。

## Implementation Outline

### `src/novel_writer/pipeline.py`

- `publish_ready_bundle` を保存するときに `summary` を同時に作る
- `summary` は bundle 本体の top-level fields から構成する

### `src/novel_writer/schema.py`

- `publish_ready_bundle` contract / validator に `summary` を追加する
- `summary` の中身は object として validate する

### `src/novel_writer/cli.py`

- publish bundle 向けの read-only summary helper を追加する
- 可能なら `summary` を優先し、無ければ top-level fields から互換的に組み立てる
- CLI は保存済み machine-readable summary を line に落とすだけに留める

### `tests/test_pipeline.py`

- `publish_ready_bundle.json` に `summary` が保存されることを確認する

### `tests/test_cli.py`

- CLI の bundle 系要約が保存済み `summary` を使って出ることを確認する
- `summary` 欠損 bundle でも表示が壊れないことを確認する

### `docs/TASKS.md`

- `M64a` 完了時に Done へ移す

## Tests

- `./venv/bin/python -m unittest tests.test_cli -v`
- `./venv/bin/python -m unittest discover -s tests -v`

## Open Questions

なし。

この task は `publish_ready_bundle` の read-only summary を固定する最小単位として一意に仕様を決められる。
