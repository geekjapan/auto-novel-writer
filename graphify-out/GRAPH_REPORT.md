# Graph Report - auto-novel-writer  (2026-10-23)

## Corpus Check
- 29 semantic source files; AST status: extracted. Exclusions and reuse evidence: build-audit.json.

## Summary
- 790 nodes · 2262 edges · 68 communities (38 shown, 30 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 74 edges (avg confidence: 0.88)
- Token usage: per-project usage unavailable (native Codex semantic extraction).

## Graph Freshness
- Built from commit: `547bccd1`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- StoryPipeline
- StoryInput
- cli.py
- schema.py
- ContinuityChecker
- SaveArtifactTest
- storage.py
- main
- Any
- CliTest
- OpenAIClient
- NoRerunContinuityChecker
- ContinuityRerunPolicy
- StoryPipelineTest
- pipeline.py
- load_thread_registry
- save_next_action_decision
- CountingLLMClient
- three_act_plot
- load_canon_ledger
- load_replan_history
- continuity_report
- build_saved_run_comparison_lines
- manifest.json
- artifacts
- revised_chapter_1_draft
- story_input
- issue_counts
- summary
- source_issue_counts
- save_chapter_handoff_packet
- chapter_1_draft
- Chapter success conditions
- next_action_decision and replan_history snapshots
- Validated seven-count story-state summary
- save_run_comparison_summary
- .test_cli_resume_project_allows_assist_stop_for_review
- ReplanningMockLLMClient
- Development prioritization guide
- Long-form production roadmap
- Project autonomy contract implementation plan
- Pipeline-owned publish_ready_bundle.summary
- story_bible → chapter_plan → chapter_briefs → scene_cards → drafts
- Task-completion checkpoints and continued queue processing
- Project autonomy contract design
- manual and stop_for_review conjunction
- Shared gate reason helper
- Shared story-state summary design
- TASKS single work ledger
- Auto-novel-writer CLI
- build_project_layout
- Auto-novel-writer repository agreement
- Codex single-task implementation loop
- GitHub task mapping conventions
- Development docs responsibility split plan
- manual plus stop_for_review blocks before pipeline
- One condition shared by resume and status
- Artifact and control boundaries support divided production
- Project status review gate plan
- Separate goals, queue and prioritization guidance
- Externalized state and verifiable production stages
- Project status review gate design
- Publish bundle summary design
- Next-action story-state snapshot design
- Blocked task report template
- auto-novel-writer

## God Nodes (most connected - your core abstractions)
1. `StoryInput` - 115 edges
2. `StoryPipeline` - 98 edges
3. `StoryArtifacts` - 88 edges
4. `SaveArtifactTest` - 88 edges
5. `save_artifact()` - 78 edges
6. `CliTest` - 59 edges
7. `ContinuityChecker` - 46 edges
8. `main()` - 44 edges
9. `load_artifact()` - 40 edges
10. `OpenAIClient` - 27 edges

## Surprising Connections (you probably didn't know these)
- `StoryPipelineTest` --uses--> `StoryPipeline`  [INFERRED]
  tests/test_pipeline.py → src/novel_writer/pipeline.py
- `StoryPipelineTest` --uses--> `ContinuityRerunPolicy`  [INFERRED]
  tests/test_pipeline.py → src/novel_writer/rerun_policy.py
- `ContinuityRerunPolicyTest` --uses--> `ContinuityRerunPolicy`  [INFERRED]
  tests/test_rerun_policy.py → src/novel_writer/rerun_policy.py
- `ContinuityCheckerTest` --uses--> `StoryArtifacts`  [INFERRED]
  tests/test_continuity.py → src/novel_writer/schema.py
- `SaveArtifactTest` --uses--> `StoryArtifacts`  [INFERRED]
  tests/test_storage.py → src/novel_writer/schema.py

## Import Cycles
- None detected.

## Communities (68 total, 30 thin omitted)

### Community 0 - "StoryPipeline"
Cohesion: 0.07
Nodes (4): StoryPipeline, StoryArtifacts, ContinuityRerunPolicyTest, SequencedContinuityChecker

### Community 1 - "StoryInput"
Cohesion: 0.07
Nodes (11): BaseLLMClient, build_llm_client(), resolve_openai_provider_settings(), MockLLMClient, StoryInput, FakeOpenAIClient, MockLLMClientTest, RecordingChat (+3 more)

### Community 2 - "cli.py"
Cohesion: 0.08
Nodes (64): add_generation_arguments(), add_runtime_arguments(), _build_candidate_comparison_context(), _build_candidate_reason_details(), _build_candidate_reason_lines(), _build_candidate_selection_metadata(), _build_chapter_status_detail_lines(), _build_chapter_status_summary_lines() (+56 more)

### Community 3 - "schema.py"
Cohesion: 0.11
Nodes (43): build_publish_ready_bundle_summary(), build_story_state_summary(), canon_ledger_contract(), chapter_artifact_contract(), chapter_briefs_contract(), chapter_handoff_packet_contract(), next_action_decision_contract(), progress_report_contract() (+35 more)

### Community 5 - "SaveArtifactTest"
Cohesion: 0.15
Nodes (6): load_project_manifest(), load_publish_ready_bundle(), load_run_comparison_summary(), load_story_bible(), save_artifact(), SaveArtifactTest

### Community 6 - "storage.py"
Cohesion: 0.11
Nodes (9): ensure_output_dir(), load_next_action_decision(), load_progress_report(), normalize_project_id(), resolve_artifact_path(), save_progress_report(), save_project_manifest(), save_publish_ready_bundle() (+1 more)

### Community 8 - "Any"
Cohesion: 0.16
Nodes (9): apply_replan_updates(), load_chapter_briefs(), load_scene_cards(), save_chapter_briefs(), save_scene_cards(), _validate_replan_apply_targets(), _validate_replan_chapter_brief_updates(), _validate_replan_scene_card_updates() (+1 more)

### Community 11 - "NoRerunContinuityChecker"
Cohesion: 0.15
Nodes (5): NoRerunContinuityChecker, ReplanTriggerContinuityChecker, RerunTriggerContinuityChecker, ReviseTriggerContinuityChecker, StopForReviewContinuityChecker

### Community 14 - "StoryPipelineTest"
Cohesion: 0.18
Nodes (3): RecordingDraftContextLLMClient, StopBeforeRevisionContinuityChecker, StoryPipelineTest

### Community 15 - "pipeline.py"
Cohesion: 0.21
Nodes (3): build_handoff_summary(), build_story_bible_summary(), build_thread_summary()

### Community 16 - "load_thread_registry"
Cohesion: 0.27
Nodes (3): load_thread_registry(), save_thread_registry(), upsert_thread_registry_entry()

### Community 19 - "three_act_plot"
Cohesion: 0.18
Nodes (11): inciting_incident, setup, crisis, midpoint, rising_action, climax, resolution, three_act_plot (+3 more)

### Community 20 - "load_canon_ledger"
Cohesion: 0.36
Nodes (3): load_canon_ledger(), save_canon_ledger(), upsert_canon_ledger_chapter()

### Community 21 - "load_replan_history"
Cohesion: 0.33
Nodes (3): load_replan_history(), save_replan_history(), upsert_replan_history_entry()

### Community 22 - "continuity_report"
Cohesion: 0.22
Nodes (9): continuity_report, character_name_mismatches, length_warnings, missing_fields, plan_to_draft_gaps, plot_to_plan_gaps, recommended_action, severity (+1 more)

### Community 24 - "manifest.json"
Cohesion: 0.25
Nodes (7): rerun_history, revise_history, selected_logline, hook, id, premise, title

### Community 25 - "artifacts"
Cohesion: 0.25
Nodes (8): artifacts, chapter_drafts, chapter_plan, characters, loglines, rerun_history, revise_history, revised_chapter_drafts

### Community 26 - "revised_chapter_1_draft"
Cohesion: 0.29
Nodes (7): revised_chapter_1_draft, chapter_index, chapter_number, revision_notes, summary, text, title

### Community 27 - "story_input"
Cohesion: 0.53
Nodes (6): story_input, genre, target_length, theme, tone, story_input

### Community 28 - "issue_counts"
Cohesion: 0.33
Nodes (6): issue_counts, character_name_mismatches, length_warnings, missing_fields, plan_to_draft_gaps, plot_to_plan_gaps

### Community 29 - "summary"
Cohesion: 0.33
Nodes (6): chapters, characters, loglines, summary, counts, phases

### Community 30 - "source_issue_counts"
Cohesion: 0.33
Nodes (6): source_issue_counts, character_name_mismatches, length_warnings, missing_fields, plan_to_draft_gaps, plot_to_plan_gaps

### Community 32 - "chapter_1_draft"
Cohesion: 0.40
Nodes (5): chapter_1_draft, chapter_number, summary, text, title

### Community 33 - "Chapter success conditions"
Cohesion: 0.50
Nodes (4): Chapter success conditions, Draft generation with required brief/scene inputs, Chapter briefs and scene cards implementation plan, Three-to-seven-scene chapter packets

### Community 34 - "next_action_decision and replan_history snapshots"
Cohesion: 0.50
Nodes (4): next_action_decision and replan_history snapshots, Decision story-state snapshot plan, progress_report.story_state_summary, Read-only saved_story_state_summary status line

### Community 35 - "Validated seven-count story-state summary"
Cohesion: 0.50
Nodes (4): Progress report and publish bundle summary, Shared story-state summary plan, Canon ledger and thread registry, Validated seven-count story-state summary

### Community 39 - "Development prioritization guide"
Cohesion: 0.67
Nodes (3): Artifact contract and layer integration first, Development prioritization guide, Progress report as story-state source of truth

### Community 40 - "Long-form production roadmap"
Cohesion: 0.67
Nodes (3): Autonomy, story state, evaluation and handoff capability axes, Long-form production roadmap, Design, decompose, write, inspect, replan, revise, publish

### Community 41 - "Project autonomy contract implementation plan"
Cohesion: 0.67
Nodes (3): Missing-only assist compatibility default, manual / assist / auto, Project autonomy contract implementation plan

### Community 42 - "Pipeline-owned publish_ready_bundle.summary"
Cohesion: 0.67
Nodes (3): Publish bundle saved summary plan, Pipeline-owned publish_ready_bundle.summary, Saved-summary-first read-only CLI with legacy backfill

### Community 43 - "story_bible → chapter_plan → chapter_briefs → scene_cards → drafts"
Cohesion: 0.67
Nodes (3): Missing or inconsistent generation inputs fail fast, story_bible → chapter_plan → chapter_briefs → scene_cards → drafts, Chapter briefs and scene cards design

### Community 44 - "Task-completion checkpoints and continued queue processing"
Cohesion: 0.67
Nodes (3): Task-completion checkpoints and continued queue processing, Autonomous workflow rules design, Material ambiguity and compatibility stop conditions

### Community 45 - "Project autonomy contract design"
Cohesion: 0.67
Nodes (3): project_manifest.autonomy_level, Contract and status only; control behavior deferred, Project autonomy contract design

### Community 46 - "manual and stop_for_review conjunction"
Cohesion: 0.67
Nodes (3): CLI pre-pipeline boundary, manual and stop_for_review conjunction, Manual resume review gate design

### Community 47 - "Shared gate reason helper"
Cohesion: 0.67
Nodes (3): Resume enforcement and project status display, Shared gate reason helper, Manual gate helper design

### Community 48 - "Shared story-state summary design"
Cohesion: 0.67
Nodes (3): M65b shares shape between progress report and publish summary, with legacy bundle compatibility, Seven count/boundary fields derived from canon ledger and thread registry by schema helper, Shared story-state summary design

### Community 49 - "TASKS single work ledger"
Cohesion: 0.67
Nodes (3): M71a story-state documentation alignment, TASKS single work ledger, M71b source-of-truth alignment

### Community 50 - "Auto-novel-writer CLI"
Cohesion: 0.67
Nodes (3): Auto-novel-writer CLI, Manual review gate, Project resume rerun comparison

## Knowledge Gaps
- **59 isolated node(s):** `auto-novel-writer`, `Provider boundary and artifact compatibility`, `Task queue and stop conditions`, `Artifact contract and layer integration first`, `Progress report as story-state source of truth` (+54 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 160 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **30 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `StoryInput` connect `StoryInput` to `StoryPipeline`, `cli.py`, `schema.py`, `ContinuityChecker`, `SaveArtifactTest`, `storage.py`, `Any`, `OpenAIClient`, `NoRerunContinuityChecker`, `StoryPipelineTest`, `pipeline.py`, `load_thread_registry`?**
  _High betweenness centrality (0.191) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `StoryInput` (e.g. with `run_pipeline()` and `BaseLLMClient`) actually correct?**
  _`StoryInput` has 11 INFERRED edges - model-reasoned connections that need verification._
- **What connects `auto-novel-writer`, `Provider boundary and artifact compatibility`, `Task queue and stop conditions` to the rest of the system?**
  _59 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `StoryPipeline` be split into smaller, more focused modules?**
  _Cohesion score 0.07365792759051186 - nodes in this community are weakly interconnected._
- **Why does `StoryPipeline` connect `StoryPipeline` to `StoryInput`, `cli.py`, `ContinuityChecker`, `storage.py`, `Any`, `NoRerunContinuityChecker`, `ContinuityRerunPolicy`, `StoryPipelineTest`, `pipeline.py`, `load_thread_registry`?**
  _High betweenness centrality (0.089) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `StoryPipeline` (e.g. with `ContinuityChecker` and `ContinuityRerunPolicy`) actually correct?**
  _`StoryPipeline` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Should `StoryInput` be split into smaller, more focused modules?**
  _Cohesion score 0.06846846846846846 - nodes in this community are weakly interconnected._