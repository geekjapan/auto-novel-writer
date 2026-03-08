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