#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/mypr.sh init <branch-name>
    - Creates a new feature branch from main

  scripts/mypr.sh pr [--fill] [--title "..."] [--body "..."]
    - Pushes current branch and creates a PR to main
    - If no title/body provided, uses --fill

Examples:
  scripts/mypr.sh init feat/my-new-change
  # ...make changes and commit...
  scripts/mypr.sh pr --fill

  scripts/mypr.sh pr --title "feat: add xyz" --body "Short description"
USAGE
}

require_git_repo() {
  if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
    echo "Error: not inside a git repository." >&2
    exit 1
  fi
}

require_clean_worktree() {
  if [[ -n "$(git status --porcelain)" ]]; then
    echo "Error: working tree is not clean. Commit or stash changes first." >&2
    exit 1
  fi
}

require_gh() {
  if ! command -v gh >/dev/null 2>&1; then
    echo "Error: gh CLI not found. Install GitHub CLI to create PRs." >&2
    exit 1
  fi
}

command=${1:-}

if [[ -z "$command" ]]; then
  usage
  exit 1
fi

require_git_repo

case "$command" in
  init)
    branch_name=${2:-}
    if [[ -z "$branch_name" ]]; then
      echo "Error: branch name is required." >&2
      usage
      exit 1
    fi

    require_clean_worktree

    git fetch origin
    git checkout main
    git pull --ff-only origin main

    if git show-ref --verify --quiet "refs/heads/$branch_name"; then
      echo "Error: branch '$branch_name' already exists." >&2
      exit 1
    fi

    git checkout -b "$branch_name"

    echo "Created and switched to branch: $branch_name"
    echo "Next: make changes, commit, then run: scripts/mypr.sh pr --fill"
    ;;

  pr)
    require_gh

    current_branch=$(git rev-parse --abbrev-ref HEAD)
    if [[ "$current_branch" == "main" ]]; then
      echo "Error: refuse to create PR from main. Switch to a feature branch." >&2
      exit 1
    fi

    if [[ -n "$(git status --porcelain)" ]]; then
      echo "Error: uncommitted changes detected. Commit before creating PR." >&2
      exit 1
    fi

    title=""
    body=""
    fill="true"

    shift
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --title)
          title=${2:-}
          shift 2
          fill="false"
          ;;
        --body)
          body=${2:-}
          shift 2
          fill="false"
          ;;
        --fill)
          fill="true"
          shift 1
          ;;
        *)
          echo "Error: unknown option '$1'" >&2
          usage
          exit 1
          ;;
      esac
    done

    if [[ "$fill" == "false" ]]; then
      if [[ -z "$title" || -z "$body" ]]; then
        echo "Error: --title and --body must both be provided." >&2
        usage
        exit 1
      fi
    fi

    git push -u origin "$current_branch"

    if [[ "$fill" == "true" ]]; then
      gh pr create --base main --head "$current_branch" --fill
    else
      gh pr create --base main --head "$current_branch" --title "$title" --body "$body"
    fi

    ;;

  *)
    usage
    exit 1
    ;;
esac
