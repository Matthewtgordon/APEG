# Agent Factory Spec (JSON)

This renderer accepts a single JSON file and generates project agent files.

## Required Fields

```
project.name
project.updated               # YYYY-MM-DD
project.one_liner
project.stack.language
project.stack.version
project.stack.framework
project.stack.database
project.architecture

agents.always[]
agents.ask_first[]
agents.never[]
agents.key_files[]            # [{"purpose": "...", "path": "..."}]

context.generated             # YYYY-MM-DD HH:MMZ
context.immediate_action
context.immediate_file
context.immediate_why
context.execplan_path
context.last_checkpoint       # YYYY-MM-DD HH:MMZ
context.red_lines[]
```

## Optional Sections

```
runbook                        # Generates docs/RUNBOOK.md
status                         # Generates docs/PROJECT_STATUS.md
skills[]                       # Generates .agent/skills/<name>/SKILL.md
```

If an optional section is omitted, that file is not generated.

## Minimal Shape (outline)

```
{
  "project": {
    "name": "...",
    "updated": "YYYY-MM-DD",
    "one_liner": "...",
    "stack": {
      "language": "...",
      "version": "...",
      "framework": "...",
      "database": "..."
    },
    "architecture": "..."
  },
  "agents": {
    "always": ["..."],
    "ask_first": ["..."],
    "never": ["..."],
    "key_files": [{"purpose": "...", "path": "..."}]
  },
  "context": {
    "generated": "YYYY-MM-DD HH:MMZ",
    "immediate_action": "...",
    "immediate_file": "...",
    "immediate_why": "...",
    "execplan_path": ".agent/plans/EXECPLAN-...md",
    "last_checkpoint": "YYYY-MM-DD HH:MMZ",
    "red_lines": ["..."],
    "blockers": ["None"]
  }
}
```

## Runbook Section

```
runbook: {
  metadata: {"repo_root": "...", "shell": "...", "env_file": "..."},
  commands: [
    {"id": "test.all", "action": "Run all tests", "command": "...", "scope": "test", "preconditions": "...", "expected": "...", "side_effects": "...", "safe": "yes"}
  ],
  command_args: [{"id": "test.single", "args": "{PATH}", "example": "..."}],
  phase_scripts: [{"id": "phase-1.migrate", "script": "scripts/migrate.py", "command": "...", "scope": "phase-1", "preconditions": "...", "expected": "..."}],
  troubleshooting: [{"pattern": "...", "diagnosis": "...", "next_command": "..."}],
  services: [{"service": "...", "purpose": "...", "endpoint": "...", "auth": "...", "health_command": "..."}],
  maintenance: [{"task": "...", "frequency": "...", "command": "...", "safe": "yes"}]
}
```

## Project Status Section

```
status: {
  updated: "YYYY-MM-DD",
  phases: [
    {"phase": "0", "name": "...", "status": "COMPLETE", "goal": "...", "evidence": "..."}
  ],
  current_phase: {
    "phase": "N",
    "name": "...",
    "goal": "...",
    "evidence_targets": [{"label": "...", "path": "..."}],
    "risks": ["..."],
    "notes": ["..."]
  }
}
```

## Skills Section

```
skills: [
  {
    "name": "pdf-reporting",
    "title": "PDF Reporting",
    "description": "...",
    "overview": "...",
    "quick_start": {"command": "...", "expected": "..."},
    "inputs": {"required_files": ["..."], "required_data": "...", "preconditions": "..."},
    "scripts": [
      {
        "path": "scripts/extract_text.py",
        "purpose": "...",
        "required_args": "<input>",
        "optional_args": "[--verbose]",
        "command": "python3 scripts/extract_text.py <input>",
        "expected": "..."
      }
    ],
    "workflow": ["Step 1", "Step 2"],
    "references": [{"file": "references/forms.md", "when": "..."}],
    "assets": [{"file": "assets/template.json", "purpose": "..."}],
    "examples": [{"name": "Extract text", "command": "...", "output": "..."}]
  }
]
```
