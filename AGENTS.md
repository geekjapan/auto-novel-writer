# AGENTS.md

## Project goals
- Build a novel-writing pipeline MVP in Python
- Focus on short-story workflow first
- Prefer simple, testable architecture

## Working rules
- Do not add unnecessary dependencies
- Keep OpenAI API access isolated behind a client module
- Save intermediate artifacts as JSON or YAML
- Add tests for each new module
- Update README when behavior changes

## Architecture preferences
- Separate pipeline orchestration, storage, schema, and LLM access
- CLI first, GUI later
- Mock implementation first, real API integration later

## Execution workflow
- Read docs/ROADMAP.md, docs/TASKS.md, and docs/CODEX_WORKFLOW.md before coding
- Select the single top priority task from docs/TASKS.md
- Treat docs/TASKS.md as the source of truth for implementation order
- Implement it with minimal safe changes
- Run tests
- Update docs if behavior changed
- Update docs/TASKS.md as work status changes
- Commit in a small unit
- Then proceed to the next task if the current task is complete
- If blocked, stop and write docs/BLOCKED.md
