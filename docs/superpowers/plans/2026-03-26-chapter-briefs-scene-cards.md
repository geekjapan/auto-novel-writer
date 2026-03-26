# Chapter Briefs / Scene Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `chapter_briefs` と `scene_cards` を pipeline の正式 artifact として追加し、`chapter_drafts` が chapter plan だけでなく章成功条件と scene 分解を必須入力として使うようにする

**Architecture:** 既存の `story_bible -> chapter_plan -> chapter_drafts` の間に、`chapter_briefs` と `scene_cards` を追加する。schema / storage / llm / pipeline の既存境界を維持し、resume / rerun 時も同じ validation を通す fail-fast 設計にする。

**Tech Stack:** Python 3、標準ライブラリ `dataclasses` / `json` / `unittest`、既存 CLI / pipeline / storage 構成

---

## File Structure

- Modify: `src/novel_writer/schema.py`
  - `chapter_briefs` / `scene_cards` の contract と validator を追加する
  - `StoryArtifacts` に新 artifact を追加する
  - `summary()` / `artifact_contract()` の出力を更新する
- Modify: `src/novel_writer/storage.py`
  - `save_chapter_briefs()` / `load_chapter_briefs()` を追加する
  - `save_scene_cards()` / `load_scene_cards()` を追加する
- Modify: `src/novel_writer/llm/base.py`
  - provider interface に `generate_chapter_briefs()` / `generate_scene_cards()` を追加する
  - `generate_chapter_draft()` の引数を新 artifact 対応へ拡張する
- Modify: `src/novel_writer/llm/mock.py`
  - mock 実装で brief / scene 生成を返す
  - chapter draft が brief / scene を参照する形に直す
- Modify: `src/novel_writer/llm/openai_client.py`
  - brief / scene 生成 prompt と response validation を追加する
  - chapter draft prompt に brief / scene を渡す
- Modify: `src/novel_writer/pipeline.py`
  - `PIPELINE_STEP_ORDER` に `chapter_briefs` / `scene_cards` を追加する
  - run / resume / rerun / reset / checkpoint / manifest 保存を更新する
  - chapter draft 前の欠落 artifact を明示的に失敗させる
- Modify: `tests/test_storage.py`
  - contract / validation / save-load round trip を追加する
- Modify: `tests/test_llm_client.py`
  - mock / OpenAI client の新 interface と validation を固定する
- Modify: `tests/test_pipeline.py`
  - 新 pipeline 順序、artifact 保存、resume、fail-fast を固定する
- Modify: `README.md`
  - pipeline 順序、artifact 一覧、resume 説明を更新する
- Modify: `docs/ROADMAP.md`
  - M58 の進捗と現状説明を同期する
- Modify: `docs/TASKS.md`
  - M57e 完了と M58 分割タスクへの遷移を反映する

## Shared Implementation Notes

- `chapter_briefs` は `list[dict]` とし、各要素は 1 章を表す
- `scene_cards` は `list[dict]` とし、各要素は 1 章分の scene packet を表す
- `scene_cards` の 1 要素は次の形にそろえる

```python
{
    "chapter_number": 1,
    "scenes": [
        {
            "scene_number": 1,
            "scene_goal": "主人公に失踪事件の異常さを悟らせる",
            "scene_conflict": "主人公は真相調査より日常維持を優先したい",
            "scene_turn": "失踪したはずの人物から留守電が届く",
            "pov_character": "篠崎 遥",
            "participants": ["篠崎 遥", "木崎 蓮"],
            "setting": "深夜の駅前",
            "must_include": ["壊れた腕時計", "偽名のメモ"],
            "continuity_refs": ["story_bible.foreshadowing_seeds[0]"],
            "foreshadowing_action": "seed-1 を張る",
            "exit_state": "主人公は失踪を偶然で片付けられなくなる",
        }
    ],
}
```

- `generate_chapter_draft()` の新 signature は次で統一する

```python
def generate_chapter_draft(
    self,
    story_input: StoryInput,
    logline: dict[str, Any],
    characters: list[dict[str, Any]],
    chapter_plan: list[dict[str, Any]],
    chapter_briefs: list[dict[str, Any]],
    scene_cards: list[dict[str, Any]],
    chapter_index: int = 0,
) -> dict[str, Any]:
    raise NotImplementedError
```

- scene 数制約は validator で固定する
  - 章ごとに `scenes` が 3 件以上 7 件以下であること

### Task 1: Schema And Storage Contracts

**Files:**
- Modify: `src/novel_writer/schema.py`
- Modify: `src/novel_writer/storage.py`
- Test: `tests/test_storage.py`

- [ ] **Step 1: Write the failing storage and validation tests**

```python
def test_save_chapter_briefs_validates_required_fields(self) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        with self.assertRaisesRegex(ValueError, "missing required fields: conflict, turn"):
            save_chapter_briefs(
                Path(tmp_dir),
                [
                    {
                        "chapter_number": 1,
                        "purpose": "導入",
                        "goal": "主人公に異変を認識させる",
                        "must_include": ["壊れた腕時計"],
                        "continuity_dependencies": [],
                        "foreshadowing_targets": [],
                        "arc_progress": "受け身の維持",
                        "target_length_guidance": "標準",
                    }
                ],
            )


def test_load_scene_cards_rejects_scene_count_out_of_range(self) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        save_artifact(
            Path(tmp_dir),
            "scene_cards",
            [{"chapter_number": 1, "scenes": []}],
            "json",
        )

        with self.assertRaisesRegex(ValueError, "scene_cards\\[0\\] must contain between 3 and 7 scenes"):
            load_scene_cards(Path(tmp_dir))
```

- [ ] **Step 2: Run the focused storage tests and verify they fail**

Run: `./venv/bin/python -m unittest tests.test_storage.SaveArtifactTest.test_save_chapter_briefs_validates_required_fields tests.test_storage.SaveArtifactTest.test_load_scene_cards_rejects_scene_count_out_of_range -v`

Expected: `ERROR` or `FAIL` because `save_chapter_briefs` / `load_scene_cards` are not defined yet.

- [ ] **Step 3: Add contracts, validators, and storage helpers**

```python
def chapter_briefs_contract() -> dict:
    return {
        "schema_name": "chapter_briefs",
        "schema_version": "1.0",
        "required_fields": [
            "chapter_number",
            "purpose",
            "goal",
            "conflict",
            "turn",
            "must_include",
            "continuity_dependencies",
            "foreshadowing_targets",
            "arc_progress",
            "target_length_guidance",
        ],
    }


def validate_chapter_briefs(payload: list[dict]) -> list[dict]:
    if not isinstance(payload, list) or not payload:
        raise ValueError("Invalid chapter_briefs: payload must be a non-empty list.")
    for index, item in enumerate(payload):
        missing_fields = [
            field for field in chapter_briefs_contract()["required_fields"] if field not in item
        ]
        if missing_fields:
            raise ValueError(
                "Invalid chapter_briefs: "
                f"chapter_briefs[{index}] is missing required fields: {', '.join(missing_fields)}."
            )
    return payload


def validate_scene_cards(payload: list[dict]) -> list[dict]:
    if not isinstance(payload, list) or not payload:
        raise ValueError("Invalid scene_cards: payload must be a non-empty list.")
    for index, chapter_packet in enumerate(payload):
        scenes = chapter_packet.get("scenes")
        if not isinstance(scenes, list) or not 3 <= len(scenes) <= 7:
            raise ValueError(
                f"Invalid scene_cards: scene_cards[{index}] must contain between 3 and 7 scenes."
            )
    return payload
```

```python
def save_chapter_briefs(output_dir: Path, payload: Any, file_format: str = "json") -> Path:
    validate_chapter_briefs(payload)
    return save_artifact(output_dir, "chapter_briefs", payload, file_format)


def load_scene_cards(output_dir: Path, file_format: str | None = None) -> list[dict[str, Any]]:
    payload = load_artifact(output_dir, "scene_cards", file_format)
    validate_scene_cards(payload)
    return payload
```

- [ ] **Step 4: Extend `StoryArtifacts` and manifest contract output**

```python
@dataclass(slots=True)
class StoryArtifacts:
    story_input: StoryInput
    loglines: list[dict] = field(default_factory=list)
    characters: list[dict] = field(default_factory=list)
    three_act_plot: dict = field(default_factory=dict)
    story_bible: dict = field(default_factory=dict)
    chapter_plan: list[dict] = field(default_factory=list)
    chapter_briefs: list[dict] = field(default_factory=list)
    scene_cards: list[dict] = field(default_factory=list)
    chapter_drafts: list[dict] = field(default_factory=list)
    chapter_1_draft: dict = field(default_factory=dict)

    def artifact_contract(self) -> dict:
        return {
            "chapter_artifacts": chapter_artifact_contract(),
            "story_bible": story_bible_contract(),
            "chapter_briefs": chapter_briefs_contract(),
            "scene_cards": scene_cards_contract(),
            "publish_ready_bundle": publish_ready_bundle_contract(),
        }
```

- [ ] **Step 5: Run the focused storage tests and the broader storage suite**

Run: `./venv/bin/python -m unittest tests.test_storage -v`

Expected: all storage tests pass, including the new chapter brief / scene card validations.

- [ ] **Step 6: Commit**

```bash
git add src/novel_writer/schema.py src/novel_writer/storage.py tests/test_storage.py
git commit -m "feat: add chapter brief and scene card contracts"
```

### Task 2: LLM Interface And Provider Implementations

**Files:**
- Modify: `src/novel_writer/llm/base.py`
- Modify: `src/novel_writer/llm/mock.py`
- Modify: `src/novel_writer/llm/openai_client.py`
- Test: `tests/test_llm_client.py`

- [ ] **Step 1: Write the failing LLM tests**

```python
def test_mock_client_generates_chapter_briefs_and_scene_cards(self) -> None:
    client = MockLLMClient()
    story_input = StoryInput(theme="喪失", genre="ミステリ", tone="静謐", target_length=120000)
    loglines = client.generate_loglines(story_input)
    characters = client.generate_characters(story_input, loglines[0])
    plot = client.generate_three_act_plot(story_input, loglines[0], characters)
    story_bible = client.generate_story_bible(story_input, loglines[0], characters, plot)
    chapter_plan = client.generate_chapter_plan(story_input, loglines[0], characters, plot, story_bible)

    chapter_briefs = client.generate_chapter_briefs(
        story_input, loglines[0], characters, plot, story_bible, chapter_plan
    )
    scene_cards = client.generate_scene_cards(
        story_input, loglines[0], characters, plot, story_bible, chapter_plan, chapter_briefs
    )

    self.assertEqual(len(chapter_briefs), len(chapter_plan))
    self.assertEqual(len(scene_cards), len(chapter_plan))
    self.assertEqual(scene_cards[0]["chapter_number"], chapter_briefs[0]["chapter_number"])
    self.assertGreaterEqual(len(scene_cards[0]["scenes"]), 3)
```

```python
def test_openai_client_validates_scene_cards_shape(self) -> None:
    client = FakeOpenAIClient({"scene_cards": [{"chapter_number": 1, "scenes": "not-a-list"}]})
    story_input = StoryInput(theme="喪失", genre="ミステリ", tone="静謐", target_length=120000)

    with self.assertRaisesRegex(ValueError, "scene_cards\\[0\\].scenes must be a list"):
        client.generate_scene_cards(
            story_input,
            {"id": "logline-1", "title": "鏡", "premise": "p", "hook": "h"},
            [{"name": "篠崎 遥"}],
            {"act_1": {}, "act_2": {}, "act_3": {}},
            {"schema_name": "story_bible", "schema_version": "1.0", "core_premise": "p", "ending_reveal": "r", "theme_statement": "t", "character_arcs": [], "world_rules": [], "forbidden_facts": [], "foreshadowing_seeds": []},
            [{"chapter_number": 1, "title": "第1章", "purpose": "導入", "point_of_view": "篠崎 遥", "target_words": 5000}],
            [{"chapter_number": 1, "purpose": "導入", "goal": "g", "conflict": "c", "turn": "t", "must_include": [], "continuity_dependencies": [], "foreshadowing_targets": [], "arc_progress": "a", "target_length_guidance": "標準"}],
        )
```

- [ ] **Step 2: Run the focused LLM tests and verify they fail**

Run: `./venv/bin/python -m unittest tests.test_llm_client.MockLLMClientTest.test_mock_client_generates_chapter_briefs_and_scene_cards tests.test_llm_client.MockLLMClientTest.test_openai_client_validates_scene_cards_shape -v`

Expected: missing method errors for `generate_chapter_briefs()` / `generate_scene_cards()`.

- [ ] **Step 3: Extend the base interface**

```python
class BaseLLMClient(ABC):
    @abstractmethod
    def generate_chapter_briefs(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
        three_act_plot: dict[str, Any],
        story_bible: dict[str, Any],
        chapter_plan: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def generate_scene_cards(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
        three_act_plot: dict[str, Any],
        story_bible: dict[str, Any],
        chapter_plan: list[dict[str, Any]],
        chapter_briefs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        raise NotImplementedError
```

- [ ] **Step 4: Implement mock outputs and the new draft signature**

```python
def generate_chapter_briefs(
    self,
    story_input: StoryInput,
    logline: dict[str, Any],
    characters: list[dict[str, Any]],
    three_act_plot: dict[str, Any],
    story_bible: dict[str, Any],
    chapter_plan: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "chapter_number": chapter["chapter_number"],
            "purpose": chapter["purpose"],
            "goal": f"{chapter['title']} で物語を前進させる",
            "conflict": "主人公の望みと外部圧力が衝突する",
            "turn": story_bible["ending_reveal"],
            "must_include": [seed["setup"] for seed in story_bible["foreshadowing_seeds"][:1]],
            "continuity_dependencies": [characters[0]["name"]],
            "foreshadowing_targets": [seed["id"] for seed in story_bible["foreshadowing_seeds"]],
            "arc_progress": characters[0]["arc"],
            "target_length_guidance": "standard" if chapter["target_words"] < 12000 else "heavy",
        }
        for chapter in chapter_plan
    ]


def generate_scene_cards(
    self,
    story_input: StoryInput,
    logline: dict[str, Any],
    characters: list[dict[str, Any]],
    three_act_plot: dict[str, Any],
    story_bible: dict[str, Any],
    chapter_plan: list[dict[str, Any]],
    chapter_briefs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    packets = []
    for brief in chapter_briefs:
        packets.append(
            {
                "chapter_number": brief["chapter_number"],
                "scenes": [
                    {
                        "scene_number": 1,
                        "scene_goal": brief["goal"],
                        "scene_conflict": brief["conflict"],
                        "scene_turn": "前提が崩れる",
                        "pov_character": chapter_plan[brief["chapter_number"] - 1]["point_of_view"],
                        "participants": [characters[0]["name"]],
                        "setting": "導入地点",
                        "must_include": brief["must_include"],
                        "continuity_refs": brief["continuity_dependencies"],
                        "foreshadowing_action": "seed",
                        "exit_state": brief["turn"],
                    },
                    {
                        "scene_number": 2,
                        "scene_goal": "対立を表面化させる",
                        "scene_conflict": brief["conflict"],
                        "scene_turn": "関係が不安定になる",
                        "pov_character": chapter_plan[brief["chapter_number"] - 1]["point_of_view"],
                        "participants": [characters[0]["name"], characters[1]["name"]],
                        "setting": "対立地点",
                        "must_include": brief["must_include"],
                        "continuity_refs": brief["continuity_dependencies"],
                        "foreshadowing_action": "progress",
                        "exit_state": "協力関係にひびが入る",
                    },
                    {
                        "scene_number": 3,
                        "scene_goal": "章の転換を確定する",
                        "scene_conflict": brief["conflict"],
                        "scene_turn": brief["turn"],
                        "pov_character": chapter_plan[brief["chapter_number"] - 1]["point_of_view"],
                        "participants": [characters[0]["name"]],
                        "setting": "転換地点",
                        "must_include": brief["must_include"],
                        "continuity_refs": brief["continuity_dependencies"],
                        "foreshadowing_action": "payoff_or_seed",
                        "exit_state": brief["turn"],
                    },
                ],
            }
        )
    return packets
```

```python
def generate_chapter_draft(
    self,
    story_input: StoryInput,
    logline: dict[str, Any],
    characters: list[dict[str, Any]],
    chapter_plan: list[dict[str, Any]],
    chapter_briefs: list[dict[str, Any]],
    scene_cards: list[dict[str, Any]],
    chapter_index: int = 0,
) -> dict[str, Any]:
    brief = chapter_briefs[chapter_index]
    packet = scene_cards[chapter_index]
    return {
        "chapter_number": chapter_plan[chapter_index]["chapter_number"],
        "title": chapter_plan[chapter_index]["title"],
        "summary": brief["goal"],
        "text": f"{brief['purpose']}。{packet['scenes'][0]['exit_state']}へ向かう本文。",
    }
```

- [ ] **Step 5: Add OpenAI client parsing and validation**

```python
def generate_chapter_briefs(
    self,
    story_input: StoryInput,
    logline: dict[str, Any],
    characters: list[dict[str, Any]],
    three_act_plot: dict[str, Any],
    story_bible: dict[str, Any],
    chapter_plan: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    data = self._generate_json(
        "You generate chapter briefs in Japanese.",
        (
            "Return JSON with key 'chapter_briefs' as an array. "
            f"story={story_input.to_dict()}, "
            f"chapter_plan={json.dumps(chapter_plan, ensure_ascii=False)}, "
            f"story_bible={json.dumps(story_bible, ensure_ascii=False)}"
        ),
    )
    root = self._require_dict(data, "chapter_briefs root")
    return self._require_object_list(
        root.get("chapter_briefs"),
        "chapter_briefs",
        ("chapter_number", "purpose", "goal", "conflict", "turn", "must_include", "continuity_dependencies", "foreshadowing_targets", "arc_progress", "target_length_guidance"),
        expected_length=len(chapter_plan),
    )
```

```python
def generate_scene_cards(
    self,
    story_input: StoryInput,
    logline: dict[str, Any],
    characters: list[dict[str, Any]],
    three_act_plot: dict[str, Any],
    story_bible: dict[str, Any],
    chapter_plan: list[dict[str, Any]],
    chapter_briefs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    root = self._require_dict(data, "scene_cards root")
    packets = self._require_object_list(
        root.get("scene_cards"),
        "scene_cards",
        ("chapter_number", "scenes"),
        expected_length=len(chapter_plan),
    )
    for index, packet in enumerate(packets):
        scenes = packet.get("scenes")
        if not isinstance(scenes, list):
            raise ValueError(f"OpenAI response for scene_cards[{index}].scenes must be a list.")
    return packets
```

- [ ] **Step 6: Run the full LLM test suite**

Run: `./venv/bin/python -m unittest tests.test_llm_client -v`

Expected: all tests pass with the new provider interface and validation.

- [ ] **Step 7: Commit**

```bash
git add src/novel_writer/llm/base.py src/novel_writer/llm/mock.py src/novel_writer/llm/openai_client.py tests/test_llm_client.py
git commit -m "feat: add chapter brief and scene card llm generation"
```

### Task 3: Pipeline Integration And Fail-Fast Behavior

**Files:**
- Modify: `src/novel_writer/pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing pipeline tests**

```python
def test_pipeline_writes_chapter_briefs_and_scene_cards_before_drafts(self) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_dir = Path(tmp_dir)
        artifacts = StoryPipeline(MockLLMClient(), output_dir, "json").run(
            StoryInput(theme="記憶", genre="SF", tone="ビター", target_length=120000)
        )

        self.assertTrue((output_dir / "chapter_briefs.json").exists())
        self.assertTrue((output_dir / "scene_cards.json").exists())
        self.assertEqual(PIPELINE_STEP_ORDER[6:9], ["chapter_briefs", "scene_cards", "chapter_drafts"])
        self.assertEqual(len(artifacts.chapter_briefs), len(artifacts.chapter_plan))
        self.assertEqual(len(artifacts.scene_cards), len(artifacts.chapter_plan))
```

```python
def test_pipeline_resume_fails_fast_when_scene_cards_missing_before_chapter_drafts(self) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_dir = Path(tmp_dir)
        pipeline = StoryPipeline(MockLLMClient(), output_dir, "json")
        pipeline.run(StoryInput(theme="秘密", genre="ミステリ", tone="静謐", target_length=120000))
        (output_dir / "scene_cards.json").unlink()

        with self.assertRaisesRegex(ValueError, "scene_cards is required before chapter_drafts"):
            StoryPipeline(MockLLMClient(), output_dir, "json").run(
                resume_from=output_dir,
                rerun_from="chapter_drafts",
            )
```

- [ ] **Step 2: Run the focused pipeline tests and verify they fail**

Run: `./venv/bin/python -m unittest tests.test_pipeline.StoryPipelineTest.test_pipeline_writes_chapter_briefs_and_scene_cards_before_drafts tests.test_pipeline.StoryPipelineTest.test_pipeline_resume_fails_fast_when_scene_cards_missing_before_chapter_drafts -v`

Expected: `FAIL` because the new step names and saved files do not exist yet.

- [ ] **Step 3: Insert new pipeline steps and save/load paths**

```python
PIPELINE_STEP_ORDER = [
    "story_input",
    "loglines",
    "characters",
    "three_act_plot",
    "story_bible",
    "chapter_plan",
    "chapter_briefs",
    "scene_cards",
    "chapter_drafts",
    "continuity_report",
    "quality_report",
    "revised_chapter_drafts",
    "story_summary",
    "project_quality_report",
    "publish_ready_bundle",
]
```

```python
def _run_chapter_briefs_step(
    self,
    story_input: StoryInput,
    selected_logline: dict,
    artifacts: StoryArtifacts,
    checkpoints: list[dict],
) -> None:
    artifacts.chapter_briefs = self.llm_client.generate_chapter_briefs(
        story_input,
        selected_logline,
        artifacts.characters,
        artifacts.three_act_plot,
        artifacts.story_bible,
        artifacts.chapter_plan,
    )
    save_chapter_briefs(self.output_dir, artifacts.chapter_briefs, self.file_format)
    self._mark_checkpoint("chapter_briefs", checkpoints, artifacts, selected_logline)


def _run_scene_cards_step(
    self,
    story_input: StoryInput,
    selected_logline: dict,
    artifacts: StoryArtifacts,
    checkpoints: list[dict],
) -> None:
    artifacts.scene_cards = self.llm_client.generate_scene_cards(
        story_input,
        selected_logline,
        artifacts.characters,
        artifacts.three_act_plot,
        artifacts.story_bible,
        artifacts.chapter_plan,
        artifacts.chapter_briefs,
    )
    save_scene_cards(self.output_dir, artifacts.scene_cards, self.file_format)
    self._mark_checkpoint("scene_cards", checkpoints, artifacts, selected_logline)
```

- [ ] **Step 4: Make draft generation require briefs and scene cards**

```python
def _require_chapter_generation_inputs(self, artifacts: StoryArtifacts, chapter_index: int) -> None:
    if not artifacts.chapter_briefs:
        raise ValueError("chapter_briefs is required before chapter_drafts. Resume from chapter_briefs or regenerate it.")
    if not artifacts.scene_cards:
        raise ValueError("scene_cards is required before chapter_drafts. Resume from scene_cards or regenerate it.")
    if chapter_index >= len(artifacts.chapter_briefs):
        raise ValueError(f"chapter_briefs is missing chapter_index={chapter_index}.")
    if chapter_index >= len(artifacts.scene_cards):
        raise ValueError(f"scene_cards is missing chapter_index={chapter_index}.")
```

```python
chapter_draft = self.llm_client.generate_chapter_draft(
    story_input,
    selected_logline,
    artifacts.characters,
    artifacts.chapter_plan,
    artifacts.chapter_briefs,
    artifacts.scene_cards,
    chapter_index=chapter_index,
)
```

- [ ] **Step 5: Update resume/reset behavior**

```python
for field_name in [
    "loglines",
    "characters",
    "three_act_plot",
    "story_bible",
    "chapter_plan",
    "chapter_briefs",
    "scene_cards",
    "chapter_drafts",
    "chapter_1_draft",
    "continuity_report",
    "continuity_history",
    "quality_report",
    "revised_chapter_drafts",
    "revised_chapter_1_draft",
    "story_summary",
    "project_quality_report",
    "publish_ready_bundle",
    "rerun_history",
    "revise_history",
]:
    if field_name in artifacts_data:
        setattr(artifacts, field_name, artifacts_data[field_name])
```

```python
def _reset_from_chapter_plan(self, artifacts: StoryArtifacts) -> None:
    artifacts.chapter_plan = []
    artifacts.chapter_briefs = []
    artifacts.scene_cards = []
    self._reset_from_chapter_drafts(artifacts)
```

- [ ] **Step 6: Run the pipeline suite**

Run: `./venv/bin/python -m unittest tests.test_pipeline -v`

Expected: pipeline tests pass with the new step order, manifest contents, and fail-fast behavior.

- [ ] **Step 7: Commit**

```bash
git add src/novel_writer/pipeline.py tests/test_pipeline.py
git commit -m "feat: integrate chapter briefs and scene cards into pipeline"
```

### Task 4: Docs And Task Ledger Sync

**Files:**
- Modify: `README.md`
- Modify: `docs/ROADMAP.md`
- Modify: `docs/TASKS.md`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Add or update a docs-oriented regression test**

```python
def test_pipeline_step_order_matches_documented_story_bible_expansion(self) -> None:
    self.assertEqual(
        PIPELINE_STEP_ORDER[:9],
        [
            "story_input",
            "loglines",
            "characters",
            "three_act_plot",
            "story_bible",
            "chapter_plan",
            "chapter_briefs",
            "scene_cards",
            "chapter_drafts",
        ],
    )
```

- [ ] **Step 2: Run the focused test and verify it passes before editing docs**

Run: `./venv/bin/python -m unittest tests.test_pipeline.StoryPipelineTest.test_pipeline_step_order_matches_documented_story_bible_expansion -v`

Expected: `PASS`.

- [ ] **Step 3: Update README to describe the new artifacts and ordering**

```md
現在は、CLI 入力から `story_input`、`loglines`、`characters`、`three_act_plot`、`story_bible`、`chapter_plan`、`chapter_briefs`、`scene_cards`、全章 draft、全章 revised draft、quality 系 artifact、project/run 管理用 manifest、comparison artifact までを順に生成できます。
```

```md
現在の step 順序:

1. `story_input`
2. `loglines`
3. `characters`
4. `three_act_plot`
5. `story_bible`
6. `chapter_plan`
7. `chapter_briefs`
8. `scene_cards`
9. `chapter_drafts`
```

- [ ] **Step 4: Update ROADMAP and TASKS to reflect M58 progress**

```md
- `chapter_briefs.json` を生成・保存できる
- `scene_cards.json` を章ごとに生成・保存できる
- chapter draft 生成は `chapter_plan` だけでなく `chapter_briefs` / `scene_cards` を受け取る
```

```md
## In Progress
- [ ] M58a: `chapter_briefs` の schema / storage / pipeline contract を固定する
  - Done when: `chapter_briefs.json` が validation 付きで保存され、manifest / resume から読める
## Ready
- [ ] M58b: `scene_cards` を正式 artifact にする
```

- [ ] **Step 5: Run the project verification set for this milestone**

Run: `./venv/bin/python -m unittest tests.test_storage -v`

Expected: `OK`

Run: `./venv/bin/python -m unittest tests.test_llm_client -v`

Expected: `OK`

Run: `./venv/bin/python -m unittest tests.test_pipeline -v`

Expected: `OK`

Run: `./venv/bin/python -m unittest discover -s tests -v`

Expected: full suite passes.

- [ ] **Step 6: Commit**

```bash
git add README.md docs/ROADMAP.md docs/TASKS.md tests/test_pipeline.py
git commit -m "docs: sync pipeline docs for chapter briefs and scene cards"
```

## Self-Review Checklist

- Spec coverage:
  - artifact 追加: Task 1
  - LLM interface / mock / OpenAI: Task 2
  - pipeline 順序と fail-fast: Task 3
  - docs / TASKS / ROADMAP 同期: Task 4
- Placeholder scan:
  - 禁止 placeholder token は plan step に含めていない
  - すべての code step にコード断片を入れている
  - すべての test / run step に具体コマンドを入れている
- Type consistency:
  - `chapter_briefs` は `list[dict[str, Any]]`
  - `scene_cards` は `list[dict[str, Any]]` で各要素に `chapter_number` と `scenes` を持つ
  - `generate_chapter_draft()` の追加引数は全 task で同じ順序に統一した
