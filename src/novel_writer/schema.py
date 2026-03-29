from __future__ import annotations

from dataclasses import asdict, dataclass, field


def chapter_artifact_contract() -> dict:
    return {
        "canonical_story_state": {
            "chapter_drafts": {
                "primary_collection": "chapter_drafts",
                "artifact_pattern": "chapter_{n}_draft",
                "compatibility_field": "chapter_1_draft",
                "compatibility_artifact": "05_chapter_1_draft",
                "compatibility_chapter_index": 0,
            },
            "revised_chapter_drafts": {
                "primary_collection": "revised_chapter_drafts",
                "artifact_pattern": "revised_chapter_{n}_draft",
                "compatibility_field": "revised_chapter_1_draft",
                "compatibility_artifact": "revised_chapter_1_draft",
                "compatibility_chapter_index": 0,
            },
            "continuity_history": {
                "primary_collection": "continuity_history",
                "compatibility_field": "continuity_report",
                "compatibility_artifact": "continuity_report",
                "compatibility_chapter_index": 0,
            },
        }
    }


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


def chapter_handoff_packet_contract() -> dict:
    return {
        "schema_name": "chapter_handoff_packet",
        "schema_version": "1.0",
        "required_fields": [
            "schema_name",
            "schema_version",
            "chapter_number",
            "current_chapter_brief",
            "relevant_scene_cards",
            "relevant_canon_facts",
            "unresolved_threads",
            "previous_chapter_summary",
            "style_constraints",
        ],
        "style_constraints_required_fields": [
            "tone",
            "point_of_view",
            "tense",
        ],
    }


def canon_ledger_contract() -> dict:
    return {
        "schema_name": "canon_ledger",
        "schema_version": "1.0",
        "required_fields": [
            "schema_name",
            "schema_version",
            "chapters",
        ],
        "chapter_required_fields": [
            "chapter_number",
            "new_facts",
            "changed_facts",
            "open_questions",
            "timeline_events",
        ],
    }


def thread_registry_contract() -> dict:
    return {
        "schema_name": "thread_registry",
        "schema_version": "1.0",
        "required_fields": [
            "schema_name",
            "schema_version",
            "threads",
        ],
        "thread_required_fields": [
            "thread_id",
            "label",
            "status",
            "introduced_in_chapter",
            "last_updated_in_chapter",
            "related_characters",
            "notes",
        ],
        "allowed_statuses": ["seeded", "progressed", "resolved", "dropped"],
    }


def progress_report_contract() -> dict:
    return {
        "schema_name": "progress_report",
        "schema_version": "1.0",
        "required_fields": [
            "schema_name",
            "schema_version",
            "evaluated_through_chapter",
            "checks",
            "issue_codes",
            "recommended_action",
        ],
        "check_names": [
            "chapter_role_coverage",
            "escalation_pace",
            "emotional_progression",
            "foreshadowing_coverage",
            "unresolved_thread_load",
            "climax_readiness",
        ],
        "check_required_fields": [
            "status",
            "summary",
            "evidence",
        ],
        "allowed_statuses": ["ok", "warning", "critical"],
        "allowed_actions": ["continue", "revise", "rerun", "replan", "stop_for_review"],
    }


def next_action_decision_contract() -> dict:
    return {
        "schema_name": "next_action_decision",
        "schema_version": "1.0",
        "required_fields": [
            "schema_name",
            "schema_version",
            "evaluated_through_chapter",
            "action",
            "reason",
            "issue_codes",
            "target_chapters",
            "policy_budget",
            "decision_trace",
        ],
        "allowed_actions": [
            "continue",
            "revise",
            "rerun_chapter",
            "replan_future",
            "stop_for_review",
        ],
        "policy_budget_required_fields": [
            "max_high_severity_chapters",
            "max_total_rerun_attempts",
            "remaining_high_severity_chapter_budget",
            "remaining_rerun_attempt_budget",
        ],
        "decision_trace_required_fields": [
            "code",
            "summary",
            "value",
        ],
    }


def replan_history_contract() -> dict:
    return {
        "schema_name": "replan_history",
        "schema_version": "1.0",
        "required_fields": [
            "schema_name",
            "schema_version",
            "replans",
        ],
        "replan_required_fields": [
            "replan_id",
            "trigger_chapter_number",
            "reason",
            "issue_codes",
            "impact_scope",
            "updated_artifacts",
            "change_summary",
        ],
        "impact_scope_required_fields": [
            "from_chapter",
            "to_chapter",
            "chapter_numbers",
        ],
    }


def story_bible_contract() -> dict:
    return {
        "schema_name": "story_bible",
        "schema_version": "1.0",
        "required_fields": [
            "schema_name",
            "schema_version",
            "core_premise",
            "ending_reveal",
            "theme_statement",
            "character_arcs",
            "world_rules",
            "forbidden_facts",
            "foreshadowing_seeds",
        ],
        "list_fields": [
            "character_arcs",
            "world_rules",
            "forbidden_facts",
            "foreshadowing_seeds",
        ],
    }


def validate_story_bible(payload: dict) -> dict:
    contract = story_bible_contract()
    missing_fields = [field for field in contract["required_fields"] if field not in payload]
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(
            "Invalid story_bible: missing required fields: "
            f"{missing}. Regenerate the story bible from the pipeline."
        )

    if payload.get("schema_name") != contract["schema_name"]:
        raise ValueError(
            "Invalid story_bible: "
            f"schema_name={payload.get('schema_name')!r} is not supported; expected {contract['schema_name']!r}."
        )

    if payload.get("schema_version") != contract["schema_version"]:
        raise ValueError(
            "Invalid story_bible: "
            f"schema_version={payload.get('schema_version')!r} is not supported; expected {contract['schema_version']!r}."
        )

    for field_name in ["core_premise", "ending_reveal", "theme_statement"]:
        if not isinstance(payload.get(field_name), str):
            raise ValueError(f"Invalid story_bible: {field_name} must be a string.")

    for field_name in contract["list_fields"]:
        if not isinstance(payload.get(field_name), list):
            raise ValueError(f"Invalid story_bible: {field_name} must be a list.")

    return payload


def validate_progress_report(payload: dict) -> dict:
    contract = progress_report_contract()
    if not isinstance(payload, dict):
        raise ValueError("Invalid progress_report: payload must be an object.")

    missing_fields = [field for field in contract["required_fields"] if field not in payload]
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(
            "Invalid progress_report: missing required fields: "
            f"{missing}. Regenerate the progress report from the pipeline."
        )

    if payload.get("schema_name") != contract["schema_name"]:
        raise ValueError(
            "Invalid progress_report: "
            f"schema_name={payload.get('schema_name')!r} is not supported; expected {contract['schema_name']!r}."
        )

    if payload.get("schema_version") != contract["schema_version"]:
        raise ValueError(
            "Invalid progress_report: "
            f"schema_version={payload.get('schema_version')!r} is not supported; expected {contract['schema_version']!r}."
        )

    _validate_int_field(payload.get("evaluated_through_chapter"), "progress_report", "evaluated_through_chapter")

    checks = payload.get("checks")
    if not isinstance(checks, dict):
        raise ValueError("Invalid progress_report: checks must be an object.")
    missing_checks = [name for name in contract["check_names"] if name not in checks]
    if missing_checks:
        missing = ", ".join(sorted(missing_checks))
        raise ValueError(f"Invalid progress_report: checks is missing required fields: {missing}.")

    for check_name in contract["check_names"]:
        check_payload = checks.get(check_name)
        if not isinstance(check_payload, dict):
            raise ValueError(f"Invalid progress_report: checks.{check_name} must be an object.")
        missing_check_fields = [
            field for field in contract["check_required_fields"] if field not in check_payload
        ]
        if missing_check_fields:
            missing = ", ".join(sorted(missing_check_fields))
            raise ValueError(
                f"Invalid progress_report: checks.{check_name} is missing required fields: {missing}."
            )
        _validate_str_field(check_payload.get("status"), "progress_report", f"checks.{check_name}.status")
        if check_payload.get("status") not in contract["allowed_statuses"]:
            allowed = ", ".join(contract["allowed_statuses"])
            raise ValueError(
                f"Invalid progress_report: checks.{check_name}.status must be one of: {allowed}."
            )
        _validate_str_field(check_payload.get("summary"), "progress_report", f"checks.{check_name}.summary")
        _validate_list_field(check_payload.get("evidence"), "progress_report", f"checks.{check_name}.evidence")

    _validate_list_field(payload.get("issue_codes"), "progress_report", "issue_codes")
    _validate_str_field(payload.get("recommended_action"), "progress_report", "recommended_action")
    if payload.get("recommended_action") not in contract["allowed_actions"]:
        allowed = ", ".join(contract["allowed_actions"])
        raise ValueError(f"Invalid progress_report: recommended_action must be one of: {allowed}.")

    return payload


def validate_next_action_decision(payload: dict) -> dict:
    contract = next_action_decision_contract()
    if not isinstance(payload, dict):
        raise ValueError("Invalid next_action_decision: payload must be an object.")

    missing_fields = [field for field in contract["required_fields"] if field not in payload]
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(
            "Invalid next_action_decision: missing required fields: "
            f"{missing}. Regenerate the next action decision."
        )

    if payload.get("schema_name") != contract["schema_name"]:
        raise ValueError(
            "Invalid next_action_decision: "
            f"schema_name={payload.get('schema_name')!r} is not supported; expected {contract['schema_name']!r}."
        )

    if payload.get("schema_version") != contract["schema_version"]:
        raise ValueError(
            "Invalid next_action_decision: "
            f"schema_version={payload.get('schema_version')!r} is not supported; expected {contract['schema_version']!r}."
        )

    _validate_int_field(
        payload.get("evaluated_through_chapter"),
        "next_action_decision",
        "evaluated_through_chapter",
    )
    _validate_str_field(payload.get("action"), "next_action_decision", "action")
    if payload.get("action") not in contract["allowed_actions"]:
        allowed = ", ".join(contract["allowed_actions"])
        raise ValueError(f"Invalid next_action_decision: action must be one of: {allowed}.")

    _validate_str_field(payload.get("reason"), "next_action_decision", "reason")
    _validate_list_field(payload.get("issue_codes"), "next_action_decision", "issue_codes")
    _validate_list_field(payload.get("target_chapters"), "next_action_decision", "target_chapters")
    for index, chapter_number in enumerate(payload.get("target_chapters", [])):
        _validate_int_field(
            chapter_number,
            "next_action_decision",
            f"target_chapters[{index}]",
        )

    policy_budget = payload.get("policy_budget")
    if not isinstance(policy_budget, dict):
        raise ValueError("Invalid next_action_decision: policy_budget must be an object.")
    missing_policy_fields = [
        field for field in contract["policy_budget_required_fields"] if field not in policy_budget
    ]
    if missing_policy_fields:
        missing = ", ".join(sorted(missing_policy_fields))
        raise ValueError(
            f"Invalid next_action_decision: policy_budget is missing required fields: {missing}."
        )
    for field_name in contract["policy_budget_required_fields"]:
        _validate_int_field(
            policy_budget.get(field_name),
            "next_action_decision",
            f"policy_budget.{field_name}",
        )

    decision_trace = payload.get("decision_trace")
    _validate_list_field(decision_trace, "next_action_decision", "decision_trace")
    for index, entry in enumerate(decision_trace):
        if not isinstance(entry, dict):
            raise ValueError(f"Invalid next_action_decision: decision_trace[{index}] must be an object.")
        missing_trace_fields = [
            field for field in contract["decision_trace_required_fields"] if field not in entry
        ]
        if missing_trace_fields:
            missing = ", ".join(sorted(missing_trace_fields))
            raise ValueError(
                f"Invalid next_action_decision: decision_trace[{index}] is missing required fields: {missing}."
            )
        _validate_str_field(entry.get("code"), "next_action_decision", f"decision_trace[{index}].code")
        _validate_str_field(entry.get("summary"), "next_action_decision", f"decision_trace[{index}].summary")

    return payload


def validate_replan_history(payload: dict) -> dict:
    contract = replan_history_contract()
    if not isinstance(payload, dict):
        raise ValueError("Invalid replan_history: payload must be an object.")

    missing_fields = [field for field in contract["required_fields"] if field not in payload]
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(
            "Invalid replan_history: missing required fields: "
            f"{missing}. Regenerate the replan history from the pipeline."
        )

    if payload.get("schema_name") != contract["schema_name"]:
        raise ValueError(
            "Invalid replan_history: "
            f"schema_name={payload.get('schema_name')!r} is not supported; expected {contract['schema_name']!r}."
        )

    if payload.get("schema_version") != contract["schema_version"]:
        raise ValueError(
            "Invalid replan_history: "
            f"schema_version={payload.get('schema_version')!r} is not supported; expected {contract['schema_version']!r}."
        )

    replans = payload.get("replans")
    if not isinstance(replans, list) or not replans:
        raise ValueError("Invalid replan_history: replans must be a non-empty list.")

    for index, replan in enumerate(replans):
        validate_replan_entry(replan, f"replans[{index}]")

    return payload


def validate_replan_entry(payload: dict, field_name: str = "replan") -> dict:
    contract = replan_history_contract()
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid replan_history: {field_name} must be an object.")

    missing_fields = [field for field in contract["replan_required_fields"] if field not in payload]
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(f"Invalid replan_history: {field_name} is missing required fields: {missing}.")

    _validate_str_field(payload.get("replan_id"), "replan_history", f"{field_name}.replan_id")
    _validate_int_field(
        payload.get("trigger_chapter_number"),
        "replan_history",
        f"{field_name}.trigger_chapter_number",
    )
    _validate_str_field(payload.get("reason"), "replan_history", f"{field_name}.reason")
    _validate_list_field(payload.get("issue_codes"), "replan_history", f"{field_name}.issue_codes")
    _validate_list_field(payload.get("updated_artifacts"), "replan_history", f"{field_name}.updated_artifacts")
    _validate_list_field(payload.get("change_summary"), "replan_history", f"{field_name}.change_summary")

    impact_scope = payload.get("impact_scope")
    if not isinstance(impact_scope, dict):
        raise ValueError(f"Invalid replan_history: {field_name}.impact_scope must be an object.")
    missing_impact_fields = [field for field in contract["impact_scope_required_fields"] if field not in impact_scope]
    if missing_impact_fields:
        missing = ", ".join(sorted(missing_impact_fields))
        raise ValueError(
            f"Invalid replan_history: {field_name}.impact_scope is missing required fields: {missing}."
        )
    _validate_int_field(
        impact_scope.get("from_chapter"),
        "replan_history",
        f"{field_name}.impact_scope.from_chapter",
    )
    _validate_int_field(
        impact_scope.get("to_chapter"),
        "replan_history",
        f"{field_name}.impact_scope.to_chapter",
    )
    if impact_scope.get("to_chapter") < impact_scope.get("from_chapter"):
        raise ValueError(
            f"Invalid replan_history: {field_name}.impact_scope.to_chapter must be greater than or equal to from_chapter."
        )
    _validate_list_field(
        impact_scope.get("chapter_numbers"),
        "replan_history",
        f"{field_name}.impact_scope.chapter_numbers",
    )
    chapter_numbers = impact_scope.get("chapter_numbers")
    expected_chapters = list(range(impact_scope["from_chapter"], impact_scope["to_chapter"] + 1))
    if chapter_numbers != expected_chapters:
        raise ValueError(
            f"Invalid replan_history: {field_name}.impact_scope.chapter_numbers must be {expected_chapters}."
        )

    return payload


def validate_canon_ledger(payload: dict) -> dict:
    contract = canon_ledger_contract()
    missing_fields = [field for field in contract["required_fields"] if field not in payload]
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(
            "Invalid canon_ledger: missing required fields: "
            f"{missing}. Regenerate the canon ledger from the pipeline."
        )

    if payload.get("schema_name") != contract["schema_name"]:
        raise ValueError(
            "Invalid canon_ledger: "
            f"schema_name={payload.get('schema_name')!r} is not supported; expected {contract['schema_name']!r}."
        )

    if payload.get("schema_version") != contract["schema_version"]:
        raise ValueError(
            "Invalid canon_ledger: "
            f"schema_version={payload.get('schema_version')!r} is not supported; expected {contract['schema_version']!r}."
        )

    chapters = payload.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        raise ValueError("Invalid canon_ledger: chapters must be a non-empty list.")

    for index, chapter in enumerate(chapters):
        validate_canon_ledger_chapter(chapter, f"chapters[{index}]")

    _validate_sequential_numbers(
        [chapter["chapter_number"] for chapter in chapters],
        "canon_ledger",
        "chapters",
        "chapters",
    )

    return payload


def validate_canon_ledger_chapter(payload: dict, field_name: str = "chapter") -> dict:
    contract = canon_ledger_contract()
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid canon_ledger: {field_name} must be an object.")

    missing_fields = [field for field in contract["chapter_required_fields"] if field not in payload]
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(
            "Invalid canon_ledger: "
            f"{field_name} is missing required fields: {missing}."
        )

    _validate_int_field(
        payload.get("chapter_number"),
        "canon_ledger",
        f"{field_name}.chapter_number",
    )
    for list_field in ["new_facts", "changed_facts", "open_questions", "timeline_events"]:
        _validate_list_field(
            payload.get(list_field),
            "canon_ledger",
            f"{field_name}.{list_field}",
        )

    return payload


def validate_thread_registry(payload: dict) -> dict:
    contract = thread_registry_contract()
    missing_fields = [field for field in contract["required_fields"] if field not in payload]
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(
            "Invalid thread_registry: missing required fields: "
            f"{missing}. Regenerate the thread registry from the pipeline."
        )

    if payload.get("schema_name") != contract["schema_name"]:
        raise ValueError(
            "Invalid thread_registry: "
            f"schema_name={payload.get('schema_name')!r} is not supported; expected {contract['schema_name']!r}."
        )

    if payload.get("schema_version") != contract["schema_version"]:
        raise ValueError(
            "Invalid thread_registry: "
            f"schema_version={payload.get('schema_version')!r} is not supported; expected {contract['schema_version']!r}."
        )

    threads = payload.get("threads")
    if not isinstance(threads, list) or not threads:
        raise ValueError("Invalid thread_registry: threads must be a non-empty list.")

    for index, thread in enumerate(threads):
        validate_thread_registry_entry(thread, f"threads[{index}]")

    return payload


def validate_thread_registry_entry(payload: dict, field_name: str = "thread") -> dict:
    contract = thread_registry_contract()
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid thread_registry: {field_name} must be an object.")

    missing_fields = [field for field in contract["thread_required_fields"] if field not in payload]
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(
            "Invalid thread_registry: "
            f"{field_name} is missing required fields: {missing}."
        )

    _validate_str_field(payload.get("thread_id"), "thread_registry", f"{field_name}.thread_id")
    _validate_str_field(payload.get("label"), "thread_registry", f"{field_name}.label")
    _validate_str_field(payload.get("status"), "thread_registry", f"{field_name}.status")
    if payload.get("status") not in contract["allowed_statuses"]:
        allowed = ", ".join(contract["allowed_statuses"])
        raise ValueError(
            f"Invalid thread_registry: {field_name}.status must be one of: {allowed}."
        )
    _validate_int_field(
        payload.get("introduced_in_chapter"),
        "thread_registry",
        f"{field_name}.introduced_in_chapter",
    )
    _validate_int_field(
        payload.get("last_updated_in_chapter"),
        "thread_registry",
        f"{field_name}.last_updated_in_chapter",
    )
    if payload.get("last_updated_in_chapter") < payload.get("introduced_in_chapter"):
        raise ValueError(
            f"Invalid thread_registry: {field_name}.last_updated_in_chapter must be greater than or equal to introduced_in_chapter."
        )
    _validate_list_field(
        payload.get("related_characters"),
        "thread_registry",
        f"{field_name}.related_characters",
    )
    _validate_list_field(payload.get("notes"), "thread_registry", f"{field_name}.notes")
    return payload


def validate_chapter_handoff_packet(payload: dict) -> dict:
    contract = chapter_handoff_packet_contract()
    if not isinstance(payload, dict):
        raise ValueError("Invalid chapter_handoff_packet: payload must be an object.")

    missing_fields = [field for field in contract["required_fields"] if field not in payload]
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(
            "Invalid chapter_handoff_packet: missing required fields: "
            f"{missing}. Regenerate the chapter handoff packet from the pipeline."
        )

    if payload.get("schema_name") != contract["schema_name"]:
        raise ValueError(
            "Invalid chapter_handoff_packet: "
            f"schema_name={payload.get('schema_name')!r} is not supported; expected {contract['schema_name']!r}."
        )

    if payload.get("schema_version") != contract["schema_version"]:
        raise ValueError(
            "Invalid chapter_handoff_packet: "
            f"schema_version={payload.get('schema_version')!r} is not supported; expected {contract['schema_version']!r}."
        )

    _validate_int_field(payload.get("chapter_number"), "chapter_handoff_packet", "chapter_number")
    validate_chapter_brief_entry(payload.get("current_chapter_brief"), "current_chapter_brief")

    relevant_scene_cards = payload.get("relevant_scene_cards")
    _validate_list_field(relevant_scene_cards, "chapter_handoff_packet", "relevant_scene_cards")
    for index, scene in enumerate(relevant_scene_cards):
        validate_scene_card_entry(scene, f"relevant_scene_cards[{index}]")

    for field_name in ["relevant_canon_facts", "unresolved_threads"]:
        _validate_list_field(payload.get(field_name), "chapter_handoff_packet", field_name)

    _validate_str_field(
        payload.get("previous_chapter_summary"),
        "chapter_handoff_packet",
        "previous_chapter_summary",
    )

    style_constraints = payload.get("style_constraints")
    if not isinstance(style_constraints, dict):
        raise ValueError("Invalid chapter_handoff_packet: style_constraints must be an object.")
    missing_style_fields = [
        field for field in contract["style_constraints_required_fields"] if field not in style_constraints
    ]
    if missing_style_fields:
        missing = ", ".join(sorted(missing_style_fields))
        raise ValueError(
            "Invalid chapter_handoff_packet: "
            f"style_constraints is missing required fields: {missing}."
        )
    for field_name in contract["style_constraints_required_fields"]:
        _validate_str_field(
            style_constraints.get(field_name),
            "chapter_handoff_packet",
            f"style_constraints.{field_name}",
        )

    return payload


def validate_chapter_briefs(payload: list[dict]) -> list[dict]:
    if not isinstance(payload, list) or not payload:
        raise ValueError("Invalid chapter_briefs: payload must be a non-empty list.")

    contract = chapter_briefs_contract()
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Invalid chapter_briefs: chapter_briefs[{index}] must be an object.")

        missing_fields = [field for field in contract["required_fields"] if field not in item]
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ValueError(
                "Invalid chapter_briefs: "
                f"chapter_briefs[{index}] is missing required fields: {missing}."
            )

        _validate_int_field(
            item.get("chapter_number"),
            "chapter_briefs",
            f"chapter_briefs[{index}].chapter_number",
        )
        for field_name in ["purpose", "goal", "conflict", "turn", "arc_progress", "target_length_guidance"]:
            _validate_str_field(item.get(field_name), "chapter_briefs", f"chapter_briefs[{index}].{field_name}")
        for field_name in ["must_include", "continuity_dependencies", "foreshadowing_targets"]:
            _validate_list_field(item.get(field_name), "chapter_briefs", f"chapter_briefs[{index}].{field_name}")

    _validate_sequential_numbers(
        [item["chapter_number"] for item in payload],
        "chapter_briefs",
        "chapter_number",
        "payload",
    )

    return payload


def validate_chapter_brief_entry(payload: dict, field_name: str) -> dict:
    contract = chapter_briefs_contract()
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid chapter_briefs: {field_name} must be an object.")

    missing_fields = [field for field in contract["required_fields"] if field not in payload]
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(
            "Invalid chapter_briefs: "
            f"{field_name} is missing required fields: {missing}."
        )

    _validate_int_field(
        payload.get("chapter_number"),
        "chapter_briefs",
        f"{field_name}.chapter_number",
    )
    for entry_field in ["purpose", "goal", "conflict", "turn", "arc_progress", "target_length_guidance"]:
        _validate_str_field(payload.get(entry_field), "chapter_briefs", f"{field_name}.{entry_field}")
    for entry_field in ["must_include", "continuity_dependencies", "foreshadowing_targets"]:
        _validate_list_field(payload.get(entry_field), "chapter_briefs", f"{field_name}.{entry_field}")

    return payload


def scene_cards_contract() -> dict:
    return {
        "schema_name": "scene_cards",
        "schema_version": "1.0",
        "required_fields": [
            "chapter_number",
            "scenes",
        ],
        "scene_required_fields": [
            "chapter_number",
            "scene_number",
            "scene_goal",
            "scene_conflict",
            "scene_turn",
            "pov_character",
            "participants",
            "setting",
            "must_include",
            "continuity_refs",
            "foreshadowing_action",
            "exit_state",
        ],
    }


def validate_scene_cards(payload: list[dict]) -> list[dict]:
    if not isinstance(payload, list) or not payload:
        raise ValueError("Invalid scene_cards: payload must be a non-empty list.")

    contract = scene_cards_contract()
    for index, chapter_packet in enumerate(payload):
        validate_scene_card_packet(chapter_packet, f"scene_cards[{index}]")
        if chapter_packet.get("chapter_number") != index + 1:
            raise ValueError(
                "Invalid scene_cards: "
                f"scene_cards[{index}] chapter_number sequence must be 1..len(payload)."
            )

    return payload


def validate_scene_card_packet(payload: dict, field_name: str) -> dict:
    contract = scene_cards_contract()
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid scene_cards: {field_name} must be an object.")

    missing_fields = [field for field in contract["required_fields"] if field not in payload]
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(
            "Invalid scene_cards: "
            f"{field_name} is missing required fields: {missing}."
        )

    _validate_int_field(
        payload.get("chapter_number"),
        "scene_cards",
        f"{field_name}.chapter_number",
    )

    scenes = payload.get("scenes")
    _validate_list_field(scenes, "scene_cards", f"{field_name}.scenes")
    if not 3 <= len(scenes) <= 7:
        raise ValueError(f"Invalid scene_cards: {field_name} must contain between 3 and 7 scenes.")

    for scene_index, scene in enumerate(scenes):
        validate_scene_card_entry(scene, f"{field_name}.scenes[{scene_index}]")
        if scene.get("chapter_number") != payload.get("chapter_number"):
            raise ValueError(
                "Invalid scene_cards: "
                f"{field_name}.scenes[{scene_index}].chapter_number must match parent chapter_number."
            )
        for field_name_part in [
            "scene_goal",
            "scene_conflict",
            "scene_turn",
            "pov_character",
            "setting",
            "foreshadowing_action",
            "exit_state",
        ]:
            _validate_str_field(
                scene.get(field_name_part),
                "scene_cards",
                f"{field_name}.scenes[{scene_index}].{field_name_part}",
            )
        for field_name_part in ["participants", "must_include", "continuity_refs"]:
            _validate_list_field(
                scene.get(field_name_part),
                "scene_cards",
                f"{field_name}.scenes[{scene_index}].{field_name_part}",
            )

    _validate_sequential_numbers(
        [scene.get("scene_number") for scene in scenes],
        "scene_cards",
        f"{field_name}.scenes",
        "scenes",
    )

    return payload


def validate_scene_card_entry(payload: dict, field_name: str) -> dict:
    contract = scene_cards_contract()
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid scene_cards: {field_name} must be an object.")

    missing_scene_fields = [
        field for field in contract["scene_required_fields"] if field not in payload
    ]
    if missing_scene_fields:
        missing = ", ".join(sorted(missing_scene_fields))
        raise ValueError(
            "Invalid scene_cards: "
            f"{field_name} is missing required fields: {missing}."
        )

    _validate_int_field(
        payload.get("scene_number"),
        "scene_cards",
        f"{field_name}.scene_number",
    )
    _validate_int_field(
        payload.get("chapter_number"),
        "scene_cards",
        f"{field_name}.chapter_number",
    )
    for field_name_part in [
        "scene_goal",
        "scene_conflict",
        "scene_turn",
        "pov_character",
        "setting",
        "foreshadowing_action",
        "exit_state",
    ]:
        _validate_str_field(
            payload.get(field_name_part),
            "scene_cards",
            f"{field_name}.{field_name_part}",
        )
    for field_name_part in ["participants", "must_include", "continuity_refs"]:
        _validate_list_field(
            payload.get(field_name_part),
            "scene_cards",
            f"{field_name}.{field_name_part}",
        )

    return payload


def _validate_int_field(value: object, prefix: str, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"Invalid {prefix}: {field_name} must be an int.")


def _validate_str_field(value: object, prefix: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"Invalid {prefix}: {field_name} must be a string.")


def _validate_list_field(value: object, prefix: str, field_name: str) -> None:
    if not isinstance(value, list):
        raise ValueError(f"Invalid {prefix}: {field_name} must be a list.")


def _validate_sequential_numbers(
    values: list[object],
    prefix: str,
    sequence_name: str,
    container_label: str,
) -> None:
    expected_values = list(range(1, len(values) + 1))
    for index, value in enumerate(values):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"Invalid {prefix}: {sequence_name}[{index}] must be an int.")
        if value != expected_values[index]:
            raise ValueError(
                f"Invalid {prefix}: {sequence_name} sequence must be 1..len({container_label})."
            )


def publish_ready_bundle_contract() -> dict:
    return {
        "schema_name": "publish_ready_bundle",
        "schema_version": "1.0",
        "required_fields": [
            "schema_version",
            "bundle_type",
            "title",
            "synopsis",
            "chapter_count",
            "chapters",
            "story_summary",
            "overall_quality_report",
            "selected_logline",
            "source_artifacts",
            "sections",
        ],
        "sections": {
            "manuscript": {
                "field": "chapters",
                "description": "Revised chapter draft collection for downstream publishing or export.",
            },
            "story_summary": {
                "field": "story_summary",
                "description": "Whole-story summary and chapter summaries.",
            },
            "quality": {
                "field": "overall_quality_report",
                "description": "Project-level quality evaluation for downstream review.",
            },
        },
    }


def validate_publish_ready_bundle(payload: dict) -> dict:
    contract = publish_ready_bundle_contract()
    missing_fields = [field for field in contract["required_fields"] if field not in payload]
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(
            "Invalid publish_ready_bundle: missing required fields: "
            f"{missing}. Regenerate the publish bundle from the pipeline."
        )

    schema_version = payload.get("schema_version")
    if schema_version != contract["schema_version"]:
        raise ValueError(
            "Invalid publish_ready_bundle: "
            f"schema_version={schema_version!r} is not supported; expected {contract['schema_version']!r}."
        )

    bundle_type = payload.get("bundle_type")
    if bundle_type != contract["schema_name"]:
        raise ValueError(
            "Invalid publish_ready_bundle: "
            f"bundle_type={bundle_type!r} is not supported; expected {contract['schema_name']!r}."
        )

    sections = payload.get("sections", {})
    for section_name, section_contract in contract["sections"].items():
        section_payload = sections.get(section_name)
        if not isinstance(section_payload, dict):
            raise ValueError(
                "Invalid publish_ready_bundle: "
                f"sections.{section_name!s} must be an object with field metadata."
            )
        if section_payload.get("field") != section_contract["field"]:
            raise ValueError(
                "Invalid publish_ready_bundle: "
                f"sections.{section_name}.field={section_payload.get('field')!r} "
                f"is not supported; expected {section_contract['field']!r}."
            )

    return payload


def project_manifest_contract() -> dict:
    return {
        "schema_name": "project_manifest",
        "schema_version": "1.0",
        "required_fields": [
            "project_id",
            "project_slug",
            "projects_dir",
            "current_run",
            "run_candidates",
            "best_run",
        ],
        "current_run": {
            "required_fields": [
                "name",
                "output_dir",
                "comparison_metrics",
                "comparison_basis",
                "comparison_reason",
                "comparison_reason_details",
            ],
        },
        "best_run": {
            "required_fields": [
                "run_name",
                "output_dir",
                "comparison_metrics",
                "comparison_basis",
                "selection_source",
                "selection_reason",
                "selection_reason_details",
            ],
        },
        "run_candidate": {
            "required_fields": [
                "run_name",
                "output_dir",
                "comparison_metrics",
                "comparison_basis",
                "comparison_reason",
                "comparison_reason_details",
            ],
        },
        "reason_detail_codes": comparison_reason_detail_codes(),
    }


def run_comparison_summary_contract() -> dict:
    return {
        "schema_name": "run_comparison_summary",
        "schema_version": "1.0",
        "required_fields": [
            "schema_name",
            "schema_version",
            "project_id",
            "project_slug",
            "current_run",
            "best_run",
            "candidate_count",
            "compact_summary",
            "run_candidates",
        ],
        "current_run": {
            "required_fields": [
                "run_name",
                "output_dir",
                "comparison_metrics",
                "comparison_basis",
                "comparison_reason",
                "comparison_reason_details",
            ],
        },
        "best_run": {
            "required_fields": [
                "run_name",
                "output_dir",
                "comparison_metrics",
                "comparison_basis",
                "selection_source",
                "selection_reason",
                "selection_reason_details",
            ],
        },
        "run_candidate": {
            "required_fields": [
                "run_name",
                "output_dir",
                "comparison_metrics",
                "comparison_basis",
                "comparison_reason",
                "comparison_reason_details",
            ],
        },
        "reason_detail_codes": comparison_reason_detail_codes(),
        "compact_summary": {
            "selection_source": "string",
            "issue_score": ["current", "best"],
            "completed_step_count": ["current", "best"],
            "long_run_should_stop": ["current", "best"],
            "policy_limits": {
                "max_high_severity_chapters": ["current", "best"],
                "max_total_rerun_attempts": ["current", "best"],
            },
        },
    }


def validate_run_comparison_summary(payload: dict) -> dict:
    contract = run_comparison_summary_contract()
    missing_fields = [field for field in contract["required_fields"] if field not in payload]
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(
            "Invalid run_comparison_summary: missing required fields: "
            f"{missing}. Regenerate the project comparison summary."
        )

    if payload.get("schema_name") != contract["schema_name"]:
        raise ValueError(
            "Invalid run_comparison_summary: "
            f"schema_name={payload.get('schema_name')!r} is not supported; expected {contract['schema_name']!r}."
        )

    if payload.get("schema_version") != contract["schema_version"]:
        raise ValueError(
            "Invalid run_comparison_summary: "
            f"schema_version={payload.get('schema_version')!r} is not supported; expected {contract['schema_version']!r}."
        )

    _validate_run_comparison_context(
        payload.get("current_run"),
        "current_run",
        contract["current_run"]["required_fields"],
    )
    _validate_run_comparison_context(
        payload.get("best_run"),
        "best_run",
        contract["best_run"]["required_fields"],
    )
    run_candidates = payload.get("run_candidates")
    if not isinstance(run_candidates, list):
        raise ValueError("Invalid run_comparison_summary: run_candidates must be a list.")
    for index, candidate in enumerate(run_candidates):
        _validate_run_comparison_context(
            candidate,
            f"run_candidates[{index}]",
            contract["run_candidate"]["required_fields"],
        )

    compact_summary = payload.get("compact_summary")
    if not isinstance(compact_summary, dict):
        raise ValueError("Invalid run_comparison_summary: compact_summary must be an object.")

    compact_contract = contract["compact_summary"]
    if not isinstance(compact_summary.get("selection_source"), str):
        raise ValueError("Invalid run_comparison_summary: compact_summary.selection_source must be a string.")

    for key in ["issue_score", "completed_step_count", "long_run_should_stop"]:
        _validate_current_best_pair(
            compact_summary.get(key),
            f"compact_summary.{key}",
        )

    policy_limits = compact_summary.get("policy_limits")
    if not isinstance(policy_limits, dict):
        raise ValueError("Invalid run_comparison_summary: compact_summary.policy_limits must be an object.")
    for key in compact_contract["policy_limits"]:
        _validate_current_best_pair(
            policy_limits.get(key),
            f"compact_summary.policy_limits.{key}",
        )

    return payload


def _validate_current_best_pair(payload: dict | None, field_name: str) -> None:
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid run_comparison_summary: {field_name} must be an object.")
    missing_fields = [key for key in ["current", "best"] if key not in payload]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Invalid run_comparison_summary: {field_name} is missing fields: {missing}.")


def _validate_run_comparison_context(
    payload: dict | None,
    field_name: str,
    required_fields: list[str],
) -> None:
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid run_comparison_summary: {field_name} must be an object.")

    missing_fields = [key for key in required_fields if key not in payload]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Invalid run_comparison_summary: {field_name} is missing fields: {missing}.")

    if not isinstance(payload.get("comparison_metrics"), dict):
        raise ValueError(f"Invalid run_comparison_summary: {field_name}.comparison_metrics must be an object.")
    if not isinstance(payload.get("comparison_basis"), list):
        raise ValueError(f"Invalid run_comparison_summary: {field_name}.comparison_basis must be a list.")

    uses_selection_reason = field_name == "best_run"
    reason_field = "selection_reason" if uses_selection_reason else "comparison_reason"
    if not isinstance(payload.get(reason_field), list):
        raise ValueError(f"Invalid run_comparison_summary: {field_name}.{reason_field} must be a list.")

    detail_field = "selection_reason_details" if uses_selection_reason else "comparison_reason_details"
    details = payload.get(detail_field)
    if not isinstance(details, list):
        raise ValueError(f"Invalid run_comparison_summary: {field_name}.{detail_field} must be a list.")
    allowed_codes = set(run_comparison_summary_contract()["reason_detail_codes"])
    for index, detail in enumerate(details):
        if not isinstance(detail, dict):
            raise ValueError(f"Invalid run_comparison_summary: {field_name}.{detail_field}[{index}] must be an object.")
        missing_detail_fields = [key for key in ["code", "value"] if key not in detail]
        if missing_detail_fields:
            missing = ", ".join(missing_detail_fields)
            raise ValueError(
                f"Invalid run_comparison_summary: {field_name}.{detail_field}[{index}] is missing fields: {missing}."
            )
        if not isinstance(detail.get("code"), str):
            raise ValueError(
                f"Invalid run_comparison_summary: {field_name}.{detail_field}[{index}].code must be a string."
            )
        if detail.get("code") not in allowed_codes:
            allowed = ", ".join(sorted(allowed_codes))
            raise ValueError(
                "Invalid run_comparison_summary: "
                f"{field_name}.{detail_field}[{index}].code={detail.get('code')!r} is not supported; "
                f"expected one of: {allowed}."
            )

    if uses_selection_reason and not isinstance(payload.get("selection_source"), str):
        raise ValueError("Invalid run_comparison_summary: best_run.selection_source must be a string.")


def comparison_reason_detail_codes() -> list[str]:
    return [
        "manual_selection",
        "long_run_should_stop",
        "total_issue_score",
        "high_severity_chapter_count",
        "rerun_attempt_total",
        "revision_attempt_total",
        "completed_step_count",
    ]


def validate_project_manifest(payload: dict) -> dict:
    contract = project_manifest_contract()
    missing_fields = [field for field in contract["required_fields"] if field not in payload]
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(
            "Invalid project_manifest: missing required fields: "
            f"{missing}. Recreate the manifest or rerun create-project."
        )

    schema_name = payload.get("schema_name")
    if schema_name is not None and schema_name != contract["schema_name"]:
        raise ValueError(
            "Invalid project_manifest: "
            f"schema_name={schema_name!r} is not supported; expected {contract['schema_name']!r}."
        )

    schema_version = payload.get("schema_version")
    if schema_version is not None and schema_version != contract["schema_version"]:
        raise ValueError(
            "Invalid project_manifest: "
            f"schema_version={schema_version!r} is not supported; expected {contract['schema_version']!r}."
        )

    _validate_project_manifest_reason_context(
        payload.get("current_run"),
        "current_run",
        contract["current_run"]["required_fields"],
        "comparison_reason_details",
        contract["reason_detail_codes"],
    )
    _validate_project_manifest_reason_context(
        payload.get("best_run"),
        "best_run",
        contract["best_run"]["required_fields"],
        "selection_reason_details",
        contract["reason_detail_codes"],
    )

    run_candidates = payload.get("run_candidates")
    if not isinstance(run_candidates, list):
        raise ValueError("Invalid project_manifest: run_candidates must be a list.")
    for index, candidate in enumerate(run_candidates):
        _validate_project_manifest_reason_context(
            candidate,
            f"run_candidates[{index}]",
            contract["run_candidate"]["required_fields"],
            "comparison_reason_details",
            contract["reason_detail_codes"],
        )

    return payload


def _validate_project_manifest_reason_context(
    payload: dict | None,
    field_name: str,
    required_fields: list[str],
    detail_field: str,
    allowed_codes: list[str],
) -> None:
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid project_manifest: {field_name} must be an object.")

    missing_fields = [key for key in required_fields if key not in payload]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Invalid project_manifest: {field_name} is missing fields: {missing}.")

    if not isinstance(payload.get("comparison_metrics"), dict):
        raise ValueError(f"Invalid project_manifest: {field_name}.comparison_metrics must be an object.")
    if not isinstance(payload.get("comparison_basis"), list):
        raise ValueError(f"Invalid project_manifest: {field_name}.comparison_basis must be a list.")

    reason_field = "selection_reason" if detail_field == "selection_reason_details" else "comparison_reason"
    if not isinstance(payload.get(reason_field), list):
        raise ValueError(f"Invalid project_manifest: {field_name}.{reason_field} must be a list.")
    if detail_field == "selection_reason_details" and not isinstance(payload.get("selection_source"), str):
        raise ValueError(f"Invalid project_manifest: {field_name}.selection_source must be a string.")

    details = payload.get(detail_field)
    if not isinstance(details, list):
        raise ValueError(f"Invalid project_manifest: {field_name}.{detail_field} must be a list.")

    allowed = set(allowed_codes)
    for index, detail in enumerate(details):
        if not isinstance(detail, dict):
            raise ValueError(f"Invalid project_manifest: {field_name}.{detail_field}[{index}] must be an object.")
        missing_detail_fields = [key for key in ["code", "value"] if key not in detail]
        if missing_detail_fields:
            missing = ", ".join(missing_detail_fields)
            raise ValueError(
                f"Invalid project_manifest: {field_name}.{detail_field}[{index}] is missing fields: {missing}."
            )
        if not isinstance(detail.get("code"), str):
            raise ValueError(f"Invalid project_manifest: {field_name}.{detail_field}[{index}].code must be a string.")
        if detail.get("code") not in allowed:
            expected = ", ".join(sorted(allowed))
            raise ValueError(
                "Invalid project_manifest: "
                f"{field_name}.{detail_field}[{index}].code={detail.get('code')!r} is not supported; "
                f"expected one of: {expected}."
            )


@dataclass(slots=True)
class StoryInput:
    theme: str
    genre: str
    tone: str
    target_length: int

    def to_dict(self) -> dict:
        return asdict(self)


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
    continuity_report: dict = field(default_factory=dict)
    continuity_history: list[dict] = field(default_factory=list)
    quality_report: dict = field(default_factory=dict)
    revised_chapter_drafts: list[dict] = field(default_factory=list)
    revised_chapter_1_draft: dict = field(default_factory=dict)
    story_summary: dict = field(default_factory=dict)
    project_quality_report: dict = field(default_factory=dict)
    progress_report: dict = field(default_factory=dict)
    publish_ready_bundle: dict = field(default_factory=dict)
    rerun_history: list[dict] = field(default_factory=list)
    revise_history: list[dict] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "story_input": self.story_input.to_dict(),
            "phases": [
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
                "progress_report",
                "publish_ready_bundle",
            ],
            "counts": {
                "loglines": len(self.loglines),
                "characters": len(self.characters),
                "chapters": len(self.chapter_plan),
                "chapter_briefs": len(self.chapter_briefs),
                "scene_cards": len(self.scene_cards),
                "chapter_drafts": len(self.chapter_drafts),
                "revised_chapter_drafts": len(self.revised_chapter_drafts),
            },
        }

    def normalize_chapter_artifacts(self) -> None:
        if self.chapter_drafts:
            self.chapter_1_draft = self.chapter_drafts[0]
        elif self.chapter_1_draft:
            self.set_chapter_draft(0, dict(self.chapter_1_draft))

        if self.revised_chapter_drafts:
            self.revised_chapter_1_draft = self.revised_chapter_drafts[0]
        elif self.revised_chapter_1_draft:
            self.set_revised_chapter_draft(0, dict(self.revised_chapter_1_draft))

        if self.continuity_history:
            self.continuity_report = self.continuity_history[0]
        elif self.continuity_report:
            self.continuity_history = [dict(self.continuity_report)]

    def artifact_contract(self) -> dict:
        return {
            "chapter_artifacts": chapter_artifact_contract(),
            "chapter_handoff_packet": chapter_handoff_packet_contract(),
            "canon_ledger": canon_ledger_contract(),
            "chapter_briefs": chapter_briefs_contract(),
            "next_action_decision": next_action_decision_contract(),
            "progress_report": progress_report_contract(),
            "replan_history": replan_history_contract(),
            "scene_cards": scene_cards_contract(),
            "story_bible": story_bible_contract(),
            "thread_registry": thread_registry_contract(),
            "publish_ready_bundle": publish_ready_bundle_contract(),
        }

    def set_chapter_draft(self, chapter_index: int, payload: dict) -> None:
        self._ensure_slot(self.chapter_drafts, chapter_index)
        self.chapter_drafts[chapter_index] = payload
        if chapter_index == 0:
            self.chapter_1_draft = payload

    def get_chapter_draft(self, chapter_index: int) -> dict:
        if 0 <= chapter_index < len(self.chapter_drafts):
            return self.chapter_drafts[chapter_index]
        if chapter_index == 0:
            return self.chapter_1_draft
        return {}

    def set_revised_chapter_draft(self, chapter_index: int, payload: dict) -> None:
        self._ensure_slot(self.revised_chapter_drafts, chapter_index)
        self.revised_chapter_drafts[chapter_index] = payload
        if chapter_index == 0:
            self.revised_chapter_1_draft = payload

    def get_revised_chapter_draft(self, chapter_index: int) -> dict:
        if 0 <= chapter_index < len(self.revised_chapter_drafts):
            return self.revised_chapter_drafts[chapter_index]
        if chapter_index == 0:
            return self.revised_chapter_1_draft
        return {}

    @staticmethod
    def _ensure_slot(items: list[dict], chapter_index: int) -> None:
        while len(items) <= chapter_index:
            items.append({})
