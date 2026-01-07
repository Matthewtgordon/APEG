#!/usr/bin/env python3
"""Render Agent Factory templates from a JSON spec."""

import argparse
import json
import os
import re
import sys

PLACEHOLDER_RE = re.compile(r"{{\s*([a-zA-Z0-9_.-]+)\s*}}")


class SpecError(Exception):
    pass


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def get_path(data, path):
    cur = data
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise SpecError(f"Missing required field: {path}")
    return cur


def require_list(data, path):
    value = get_path(data, path)
    if not isinstance(value, list):
        raise SpecError(f"Field must be a list: {path}")
    return value


def ensure_str(value, path):
    if not isinstance(value, str) or not value.strip():
        raise SpecError(f"Field must be a non-empty string: {path}")
    return value


def ensure_list_of_str(values, path):
    if not isinstance(values, list):
        raise SpecError(f"Field must be a list: {path}")
    for idx, value in enumerate(values):
        ensure_str(value, f"{path}[{idx}]")


def format_cell(value, code=False):
    if value is None:
        value = "-"
    text = str(value).strip()
    if not text:
        text = "-"
    text = text.replace("|", "\\|").replace("\n", "<br>")
    text = text.replace("`", "\\`")
    if code:
        return f"`{text}`"
    return text


def make_table(headers, rows):
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    if not rows:
        rows = [["-"] * len(headers)]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def bullet_block(items):
    if not items:
        return "- None"
    return "\n".join(f"- {item}" for item in items)


def numbered_block(items):
    if not items:
        return "- None"
    return "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items))


def section(title, body, intro=None):
    if not body:
        return ""
    parts = [f"## {title}"]
    if intro:
        parts.append(intro)
    parts.append(body)
    return "\n".join(parts) + "\n"


def render_template(path, mapping):
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()

    def repl(match):
        key = match.group(1).strip()
        if key not in mapping:
            raise SpecError(f"Missing template value: {key}")
        return mapping[key]

    rendered = PLACEHOLDER_RE.sub(repl, text)
    if "{{" in rendered or "}}" in rendered:
        raise SpecError(f"Unresolved placeholders in template: {path}")
    return rendered


def write_file(path, content):
    dirpath = os.path.dirname(path)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def validate_core(spec):
    ensure_str(get_path(spec, "project.name"), "project.name")
    ensure_str(get_path(spec, "project.updated"), "project.updated")
    ensure_str(get_path(spec, "project.one_liner"), "project.one_liner")
    ensure_str(get_path(spec, "project.stack.language"), "project.stack.language")
    ensure_str(get_path(spec, "project.stack.version"), "project.stack.version")
    ensure_str(get_path(spec, "project.stack.framework"), "project.stack.framework")
    ensure_str(get_path(spec, "project.stack.database"), "project.stack.database")
    ensure_str(get_path(spec, "project.architecture"), "project.architecture")

    ensure_list_of_str(require_list(spec, "agents.always"), "agents.always")
    ensure_list_of_str(require_list(spec, "agents.ask_first"), "agents.ask_first")
    ensure_list_of_str(require_list(spec, "agents.never"), "agents.never")
    key_files = require_list(spec, "agents.key_files")
    for idx, entry in enumerate(key_files):
        if not isinstance(entry, dict):
            raise SpecError(f"agents.key_files[{idx}] must be an object")
        ensure_str(entry.get("purpose"), f"agents.key_files[{idx}].purpose")
        ensure_str(entry.get("path"), f"agents.key_files[{idx}].path")

    ensure_str(get_path(spec, "context.generated"), "context.generated")
    ensure_str(get_path(spec, "context.immediate_action"), "context.immediate_action")
    ensure_str(get_path(spec, "context.immediate_file"), "context.immediate_file")
    ensure_str(get_path(spec, "context.immediate_why"), "context.immediate_why")
    ensure_str(get_path(spec, "context.execplan_path"), "context.execplan_path")
    ensure_str(get_path(spec, "context.last_checkpoint"), "context.last_checkpoint")
    ensure_list_of_str(require_list(spec, "context.red_lines"), "context.red_lines")


def build_agents_mapping(spec):
    project = spec["project"]
    agents = spec["agents"]

    rows = []
    for entry in agents.get("key_files", []):
        purpose = format_cell(entry.get("purpose", "-"))
        path = format_cell(entry.get("path", "-"), code=True)
        rows.append([purpose, path])

    mapping = {
        "PROJECT_NAME": project["name"],
        "UPDATED": project["updated"],
        "ONE_SENTENCE_DESCRIPTION": project["one_liner"],
        "LANGUAGE": project["stack"]["language"],
        "VERSION": project["stack"]["version"],
        "FRAMEWORK": project["stack"]["framework"],
        "DATABASE": project["stack"]["database"],
        "ARCHITECTURE": project["architecture"],
        "ALWAYS_BLOCK": bullet_block(agents.get("always", [])),
        "ASK_BLOCK": bullet_block(agents.get("ask_first", [])),
        "NEVER_BLOCK": bullet_block(agents.get("never", [])),
        "KEY_FILES_ROWS": make_table(["Purpose", "Path"], rows).splitlines()[2:],
    }

    # Replace KEY_FILES_ROWS with only table rows (header already in template)
    rows_only = "\n".join(mapping["KEY_FILES_ROWS"])
    mapping["KEY_FILES_ROWS"] = rows_only
    return mapping


def build_context_mapping(spec):
    project = spec["project"]
    context = spec["context"]
    blockers = context.get("blockers")
    if blockers is None:
        blockers = ["None"]
    elif isinstance(blockers, str):
        blockers = [blockers]

    mapping = {
        "PROJECT_NAME": project["name"],
        "CONTEXT_GENERATED": context["generated"],
        "IMMEDIATE_ACTION": context["immediate_action"],
        "IMMEDIATE_FILE": context["immediate_file"],
        "IMMEDIATE_WHY": context["immediate_why"],
        "EXECPLAN_PATH": context["execplan_path"],
        "LAST_CHECKPOINT": context["last_checkpoint"],
        "RED_LINES_BLOCK": bullet_block(context.get("red_lines", [])),
        "BLOCKERS_BLOCK": bullet_block(blockers),
    }
    return mapping


def build_governance_mapping(spec):
    version = spec.get("governance", {}).get("version", "1.1.0")
    return {"GOVERNANCE_VERSION": version}


def build_plans_mapping(spec):
    version = spec.get("plans", {}).get("version", "1.1.0")
    return {"PLANS_VERSION": version}


def build_runbook_mapping(spec):
    project = spec["project"]
    runbook = spec.get("runbook")
    if not runbook:
        return None

    metadata = runbook.get("metadata")
    if not isinstance(metadata, dict):
        raise SpecError("runbook.metadata must be an object")
    ensure_str(metadata.get("repo_root"), "runbook.metadata.repo_root")
    ensure_str(metadata.get("shell"), "runbook.metadata.shell")
    ensure_str(metadata.get("env_file"), "runbook.metadata.env_file")

    commands = runbook.get("commands", [])
    if not isinstance(commands, list):
        raise SpecError("runbook.commands must be a list")

    metadata_body = "\n".join(
        [
            f"- Default working dir: `{metadata.get('repo_root', '-')}`",
            f"- Shell: `{metadata.get('shell', '-')}`",
            f"- Environment file: `{metadata.get('env_file', '-')}`",
        ]
    )

    command_rows = []
    for idx, cmd in enumerate(commands):
        ensure_str(cmd.get("id"), f"runbook.commands[{idx}].id")
        ensure_str(cmd.get("action"), f"runbook.commands[{idx}].action")
        ensure_str(cmd.get("command"), f"runbook.commands[{idx}].command")
        command_rows.append(
            [
                format_cell(cmd.get("id", "-")),
                format_cell(cmd.get("action", "-")),
                format_cell(cmd.get("command", "-"), code=True),
                format_cell(cmd.get("scope", "-")),
                format_cell(cmd.get("preconditions", "-")),
                format_cell(cmd.get("expected", "-")),
                format_cell(cmd.get("side_effects", "-")),
                format_cell(cmd.get("safe", "-")),
            ]
        )

    command_table = make_table(
        [
            "ID",
            "Action",
            "Command",
            "Scope",
            "Preconditions",
            "Expected",
            "Side Effects",
            "Safe",
        ],
        command_rows,
    )

    command_registry_section = section(
        "COMMAND REGISTRY",
        command_table,
        intro="Each row is a single, copy-pasteable command. No implied flags.",
    )

    command_args = runbook.get("command_args", [])
    command_args_section = ""
    if command_args:
        rows = []
        for arg in command_args:
            rows.append(
                [
                    format_cell(arg.get("id", "-")),
                    format_cell(arg.get("args", "-")),
                    format_cell(arg.get("example", "-"), code=True),
                ]
            )
        command_args_section = section(
            "COMMAND ARGUMENTS (Optional, only if needed)",
            make_table(["ID", "Args", "Example"], rows),
        )

    phase_scripts = runbook.get("phase_scripts", [])
    phase_scripts_section = ""
    if phase_scripts:
        rows = []
        for item in phase_scripts:
            rows.append(
                [
                    format_cell(item.get("id", "-")),
                    format_cell(item.get("script", "-"), code=True),
                    format_cell(item.get("command", "-"), code=True),
                    format_cell(item.get("scope", "-")),
                    format_cell(item.get("preconditions", "-")),
                    format_cell(item.get("expected", "-")),
                ]
            )
        phase_scripts_section = section(
            "PHASE-SCOPED SCRIPTS",
            make_table(
                [
                    "ID",
                    "Script",
                    "Command",
                    "Scope",
                    "Preconditions",
                    "Expected",
                ],
                rows,
            ),
            intro="Use Scope to guard execution; only run when current phase matches.",
        )

    troubleshooting = runbook.get("troubleshooting", [])
    troubleshooting_section = ""
    if troubleshooting:
        rows = []
        for item in troubleshooting:
            rows.append(
                [
                    format_cell(item.get("pattern", "-"), code=True),
                    format_cell(item.get("diagnosis", "-")),
                    format_cell(item.get("next_command", "-"), code=True),
                ]
            )
        troubleshooting_section = section(
            "TROUBLESHOOTING MATRIX (Regex-Driven)",
            make_table(["Error Pattern (regex)", "Diagnosis", "Next Command"], rows),
        )

    services = runbook.get("services", [])
    services_section = ""
    if services:
        rows = []
        for item in services:
            rows.append(
                [
                    format_cell(item.get("service", "-")),
                    format_cell(item.get("purpose", "-")),
                    format_cell(item.get("endpoint", "-"), code=True),
                    format_cell(item.get("auth", "-")),
                    format_cell(item.get("health_command", "-"), code=True),
                ]
            )
        services_section = section(
            "EXTERNAL SERVICES (Structured)",
            make_table(["Service", "Purpose", "Endpoint", "Auth", "Health Command"], rows),
        )

    maintenance = runbook.get("maintenance", [])
    maintenance_section = ""
    if maintenance:
        rows = []
        for item in maintenance:
            rows.append(
                [
                    format_cell(item.get("task", "-")),
                    format_cell(item.get("frequency", "-")),
                    format_cell(item.get("command", "-"), code=True),
                    format_cell(item.get("safe", "-")),
                ]
            )
        maintenance_section = section(
            "MAINTENANCE (Only if required)",
            make_table(["Task", "Frequency", "Command", "Safe"], rows),
        )

    mapping = {
        "PROJECT_NAME": project["name"],
        "RUNBOOK_METADATA_SECTION": section("Metadata (Read Once)", metadata_body),
        "COMMAND_REGISTRY_SECTION": command_registry_section,
        "COMMAND_ARGS_SECTION": command_args_section,
        "PHASE_SCRIPTS_SECTION": phase_scripts_section,
        "TROUBLESHOOTING_SECTION": troubleshooting_section,
        "SERVICES_SECTION": services_section,
        "MAINTENANCE_SECTION": maintenance_section,
    }
    return mapping


def build_status_mapping(spec):
    project = spec["project"]
    status = spec.get("status")
    if not status:
        return None
    if not isinstance(status, dict):
        raise SpecError("status must be an object")

    updated = status.get("updated", project.get("updated", ""))
    if updated:
        ensure_str(updated, "status.updated")

    phases = status.get("phases", [])
    if not isinstance(phases, list):
        raise SpecError("status.phases must be a list")

    phase_rows = []
    for idx, item in enumerate(phases):
        if not isinstance(item, dict):
            raise SpecError(f"status.phases[{idx}] must be an object")
        ensure_str(item.get("phase"), f"status.phases[{idx}].phase")
        ensure_str(item.get("name"), f"status.phases[{idx}].name")
        ensure_str(item.get("status"), f"status.phases[{idx}].status")
        ensure_str(item.get("goal"), f"status.phases[{idx}].goal")
        ensure_str(item.get("evidence"), f"status.phases[{idx}].evidence")
        phase_rows.append(
            [
                format_cell(item.get("phase", "-")),
                format_cell(item.get("name", "-")),
                format_cell(item.get("status", "-")),
                format_cell(item.get("goal", "-")),
                format_cell(item.get("evidence", "-"), code=True),
            ]
        )

    phase_map_section = section(
        "Phase Map",
        make_table(["Phase", "Name", "Status", "Goal (1 sentence)", "Evidence"], phase_rows),
    )

    current = status.get("current_phase", {})
    if not isinstance(current, dict):
        raise SpecError("status.current_phase must be an object")
    ensure_str(current.get("phase"), "status.current_phase.phase")
    ensure_str(current.get("name"), "status.current_phase.name")
    ensure_str(current.get("goal"), "status.current_phase.goal")
    current_lines = [
        f"**Phase:** {current.get('phase', '-')} - {current.get('name', '-')}",
        f"**Goal:** {current.get('goal', '-')}",
        "",
        "**Evidence Targets**",
    ]

    targets = current.get("evidence_targets", [])
    if targets:
        for target in targets:
            label = format_cell(target.get("label", "-"))
            path = format_cell(target.get("path", "-"), code=True)
            current_lines.append(f"- {label} -> {path}")
    else:
        current_lines.append("- None")

    current_lines.append("")
    current_lines.append("**Risks / Architectural Debt**")
    risks = current.get("risks", [])
    if risks:
        current_lines.extend(f"- {risk}" for risk in risks)
    else:
        current_lines.append("- None")

    current_phase_section = section("Current Phase Focus", "\n".join(current_lines))

    notes = current.get("notes", [])
    phase_notes_section = ""
    if notes:
        phase_notes_section = section(
            "Phase Notes (Optional, 3 bullets max)",
            "\n".join(f"- {note}" for note in notes),
        )

    mapping = {
        "PROJECT_NAME": project["name"],
        "STATUS_UPDATED": updated,
        "PHASE_MAP_SECTION": phase_map_section,
        "CURRENT_PHASE_SECTION": current_phase_section,
        "PHASE_NOTES_SECTION": phase_notes_section,
    }
    return mapping


def build_skill_mapping(skill):
    name = ensure_str(skill.get("name"), "skills[].name")
    if "/" in name or "\\" in name:
        raise SpecError("skills[].name must not contain path separators")
    description = ensure_str(skill.get("description"), "skills[].description")
    title = skill.get("title") or name.replace("-", " ").title()
    overview = ensure_str(skill.get("overview"), f"skills[{name}].overview")

    quick_start = skill.get("quick_start", {})
    quick_command = ensure_str(quick_start.get("command"), f"skills[{name}].quick_start.command")
    quick_expected = ensure_str(quick_start.get("expected"), f"skills[{name}].quick_start.expected")

    inputs = skill.get("inputs", {})
    required_files = inputs.get("required_files", [])
    if isinstance(required_files, list):
        required_files_str = ", ".join(required_files) if required_files else "None"
    else:
        required_files_str = str(required_files)

    required_data = inputs.get("required_data", "None")
    preconditions = inputs.get("preconditions", "None")

    scripts = skill.get("scripts", [])
    if scripts:
        script_lines = []
        for item in scripts:
            script_lines.extend(
                [
                    f"### {item.get('path', '-')}",
                    f"- Purpose: {item.get('purpose', '-')}",
                    f"- Required args: {item.get('required_args', '-')}",
                    f"- Optional args: {item.get('optional_args', '-')}",
                    "- Command:",
                    f"    {item.get('command', '-')}",
                    "- Expected:",
                    f"    {item.get('expected', '-')}",
                    "",
                ]
            )
        scripts_block = "\n".join(script_lines).rstrip()
    else:
        scripts_block = "- None"

    workflow = numbered_block(skill.get("workflow", []))

    references = skill.get("references", [])
    if references:
        references_block = "\n".join(
            f"- `{item.get('file', '-')}` - Read when {item.get('when', '-')}."
            for item in references
        )
    else:
        references_block = "- None"

    assets = skill.get("assets", [])
    if assets:
        assets_block = "\n".join(
            f"- `{item.get('file', '-')}` - {item.get('purpose', '-')}." for item in assets
        )
    else:
        assets_block = "- None"

    examples = skill.get("examples", [])
    if examples:
        example_lines = []
        for item in examples:
            example_lines.extend(
                [
                    f"### {item.get('name', 'Example')}",
                    "Command:",
                    f"    {item.get('command', '-')}",
                    "",
                    "Output:",
                    f"    {item.get('output', '-')}",
                    "",
                ]
            )
        examples_block = "\n".join(example_lines).rstrip()
    else:
        examples_block = "- None"

    return {
        "SKILL_NAME": name,
        "SKILL_DESCRIPTION": description,
        "SKILL_TITLE": title,
        "SKILL_OVERVIEW": overview,
        "QUICK_START_COMMAND": quick_command,
        "QUICK_START_EXPECTED": quick_expected,
        "REQUIRED_FILES": required_files_str,
        "REQUIRED_DATA": required_data,
        "PRECONDITIONS": preconditions,
        "SCRIPTS_BLOCK": scripts_block,
        "WORKFLOW_BLOCK": workflow,
        "REFERENCES_BLOCK": references_block,
        "ASSETS_BLOCK": assets_block,
        "EXAMPLES_BLOCK": examples_block,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, help="Path to JSON spec")
    parser.add_argument("--output-root", default=".", help="Repo root to write files")
    parser.add_argument(
        "--templates",
        default=os.path.join(os.path.dirname(__file__), "..", "assets", "templates"),
        help="Template directory",
    )
    parser.add_argument("--validate-only", action="store_true", help="Validate spec only")
    args = parser.parse_args()

    spec = load_json(args.spec)
    validate_core(spec)

    if args.validate_only:
        print("Spec OK")
        return 0

    templates_dir = args.templates
    output_root = args.output_root

    agents_content = render_template(
        os.path.join(templates_dir, "AGENTS.md"), build_agents_mapping(spec)
    )
    governance_content = render_template(
        os.path.join(templates_dir, "GOVERNANCE.md"), build_governance_mapping(spec)
    )
    plans_content = render_template(
        os.path.join(templates_dir, "PLANS.md"), build_plans_mapping(spec)
    )
    context_content = render_template(
        os.path.join(templates_dir, "CONTEXT.md"), build_context_mapping(spec)
    )

    writes = []
    writes.append((os.path.join(output_root, "AGENTS.md"), agents_content))
    writes.append((os.path.join(output_root, ".agent", "GOVERNANCE.md"), governance_content))
    writes.append((os.path.join(output_root, ".agent", "PLANS.md"), plans_content))
    writes.append((os.path.join(output_root, ".agent", "CONTEXT.md"), context_content))

    runbook_mapping = build_runbook_mapping(spec)
    if runbook_mapping:
        runbook_content = render_template(
            os.path.join(templates_dir, "RUNBOOK.md"), runbook_mapping
        )
        writes.append((os.path.join(output_root, "docs", "RUNBOOK.md"), runbook_content))

    status_mapping = build_status_mapping(spec)
    if status_mapping:
        status_content = render_template(
            os.path.join(templates_dir, "PROJECT_STATUS.md"), status_mapping
        )
        writes.append(
            (os.path.join(output_root, "docs", "PROJECT_STATUS.md"), status_content)
        )

    skills = spec.get("skills", [])
    if skills:
        skill_template = os.path.join(templates_dir, "SKILL.md")
        for skill in skills:
            mapping = build_skill_mapping(skill)
            skill_content = render_template(skill_template, mapping)
            output_path = os.path.join(
                output_root, ".agent", "skills", mapping["SKILL_NAME"], "SKILL.md"
            )
            writes.append((output_path, skill_content))

    for path, content in writes:
        write_file(path, content)

    print(f"Wrote {len(writes)} file(s)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SpecError as exc:
        print(f"Spec error: {exc}", file=sys.stderr)
        raise SystemExit(2)
