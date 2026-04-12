# AGENTS.md

## Read order
- Read `docs/TASKS.md` first for the active work queue; this repo expects at most one `In Progress` item.
- Read `docs/CODEX_WORKFLOW.md` next for the implementation loop and guardrails.
- Treat `README.md` as current user-facing behavior only.
- `README.md` and `docs/CODEX_WORKFLOW.md` reference `docs/ROADMAP.md` and `docs/DEVELOPMENT_GUIDE.md`, but those files are currently absent.

## Verified commands
- Setup: `python -m pip install -e .`
- In a clean repo-root shell, plain `python -m unittest ...` fails because `src/` is not on `sys.path`; use `PYTHONPATH=src` unless you already installed the package editable.
- Full test suite: `PYTHONPATH=src python -m unittest discover -s tests -v`
- Single test: `PYTHONPATH=src python -m unittest tests.test_cli.CliTest.test_cli_main_runs_with_mock_provider -v`
- CLI help: `PYTHONPATH=src python -m novel_writer --help`
- No checked-in lint, typecheck, pre-commit, or CI config was found; the verified project-level check is the unittest suite.

## Repo shape
- This is a single-package Python repo under `src/novel_writer/`.
- Console entrypoint: `novel_writer.cli:main`; `python -m novel_writer` just dispatches to that entrypoint.
- Main runtime flow is `cli.main()` -> project/run helpers -> `StoryPipeline` in `src/novel_writer/pipeline.py`.
- Keep provider-specific changes inside `src/novel_writer/llm/`; `docs/CODEX_WORKFLOW.md` treats that as a hard boundary.
- `src/novel_writer/storage.py` and `src/novel_writer/schema.py` own artifact layout and validation. Artifact filenames, CLI names, and schema shapes are compatibility surfaces; do not change them casually.

## Data and command quirks
- Standalone runs default to `data/latest_run`.
- Project-scoped runs live under `data/projects/<slug>/runs/latest_run`; `project_id` is slugified by `storage.normalize_project_id()`.
- `data/*` is gitignored except `data/.gitkeep`; do not commit generated run artifacts.
- `show-project-status` and `show-run-comparison` are read-only views over saved artifacts.
- `select-best-run` updates manifest state without rerunning the pipeline.
- `resume-project` blocks for `manual` projects when the saved `next_action_decision.action` is `stop_for_review`.

## Optional dependencies and provider defaults
- `pyproject.toml` declares no runtime dependencies; non-mock providers and YAML support are opt-in.
- Install `openai` for `openai`, `openai-compatible`, `lmstudio`, or `ollama` providers.
- Install `PyYAML` for `--format yaml`.
- `openai-compatible` requires an explicit base URL.
- Code defaults local endpoints to `LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1` and `OLLAMA_BASE_URL=http://127.0.0.1:11434/v1` when flags/env vars do not override them.

## Test behavior
- Tests are `unittest` modules under `tests/`.
- The full suite is noisy because CLI tests print generated run summaries to stdout; a passing run still ends with `OK`.
- One YAML-path test skips when `PyYAML` is not installed.
