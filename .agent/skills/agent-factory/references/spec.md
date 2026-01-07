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
agents.autonomy_mode          # FULL | PARTIAL | MANUAL (optional)

context.generated             # YYYY-MM-DD HH:MMZ
context.immediate_action
context.immediate_file
context.immediate_why         # optional
context.execplan_path
context.last_checkpoint       # YYYY-MM-DD HH:MMZ
context.phase
context.phase_name
context.status                # IN_PROGRESS | BLOCKED | COMPLETE
context.constraints[]         # short, high-signal constraints
context.blockers[]            # optional

context.preflight             # optional block (see below)
context.scope                 # optional block (see below)
context.pending_inputs[]      # optional list (see below)
```

### Optional Blocks

```
context.preflight: {
  cwd, interpreter, python_version, venv_active, env_exists,
  git_status, branch, test_cmd_found, secrets_mode, safe_mock_ok, last_preflight
}

context.scope: {
  goal, non_goals, risk_level, test_plan
}

context.pending_inputs: [
  {"question": "...", "needed_for": "..."}
]
```

## Optional Sections

```
runbook                        # Generates docs/RUNBOOK.md
status                         # Generates docs/PROJECT_STATUS.md
skills[]                       # Generates .agent/skills/<name>/SKILL.md
system_instruction             # Generates a System Instruction file
```

If an optional section is omitted, that file is not generated.

## Minimal Shape (outline)

```
{
  "project": {
    "name": "...",
    "updated": "YYYY-MM-DD",
    "one_liner": "...",
    "stack": {"language": "...", "version": "...", "framework": "...", "database": "..."},
    "architecture": "..."
  },
  "agents": {
    "autonomy_mode": "FULL",
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
    "phase": "N",
    "phase_name": "...",
    "status": "IN_PROGRESS",
    "constraints": ["..."],
    "blockers": ["None"],
    "preflight": {"cwd": "...", "interpreter": "...", "python_version": "3.x", "venv_active": "unknown"},
    "scope": {"goal": "...", "non_goals": "...", "risk_level": "LOW", "test_plan": "test.smoke"},
    "pending_inputs": [{"question": "...", "needed_for": "..."}]
  }
}
```

## Runbook Section

```
runbook: {
  metadata: {"repo_root": "...", "shell": "...", "env_file": "..."},
  commands: [
    {"id": "build", "action": "Build", "command": "...", "preconditions": "...", "expected": "..."}
  ],
  command_args: [{"id": "test.single", "args": "{PATH}", "example": "..."}],
  test_tiers: [
    {"tier": "SMOKE", "id": "test.smoke", "command": "...", "preconditions": "...", "fallback": "..."}
  ],
  environment_modes: [
    {"mode": "LIVE", "condition": "...", "behavior": "..."}
  ],
  phase_scripts: [
    {"phase": "1", "script": "scripts/migrate.py", "command": "...", "preconditions": "...", "expected": "..."}
  ],
  troubleshooting: [
    {"pattern": "...", "diagnosis": "...", "next_command": "..."}
  ],
  services: [
    {"service": "...", "purpose": "...", "endpoint": "...", "auth": "...", "health_command": "..."}
  ],
  maintenance: [
    {"task": "...", "frequency": "...", "command": "...", "safe": "yes"}
  ]
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
    "objectives": ["..."],
    "evidence": ["..."],
    "risks": ["..."],
    "blockers": ["..."]
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
    "triggers": ["..."],
    "quick_start": {"command": "...", "expected": "..."},
    "inputs": {"inputs": ["..."], "outputs": ["..."], "preconditions": "..."},
    "scripts": [
      {"path": "scripts/extract_text.py", "purpose": "...", "command": "...", "args": "...", "expected": "..."}
    ],
    "examples": [
      {"name": "Extract", "command": "...", "output": "..."}
    ],
    "references": [
      {"file": "references/forms.md", "when": "..."}
    ]
  }
]
```

## System Instruction Section

```
system_instruction: {
  path: "System_Instruction_Candidate.md",
  kb_templates: [
    "template-agents-md.md",
    "template-governance-md.md",
    "template-context-md.md",
    "template-plans-md.md",
    "template-runbook-md.md",
    "template-project-status-md.md",
    "template-skill-md.md"
  ]
}
```
