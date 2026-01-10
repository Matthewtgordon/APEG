#!/usr/bin/env python3
"""Run Phase 0 evidence checks and update docs/ACCEPTANCE_TESTS.md.

This script avoids logging secrets. It records a brief evidence summary
in docs/evidence and updates the Phase 0 table rows by ID.
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
ACCEPTANCE_PATH = ROOT / "docs" / "ACCEPTANCE_TESTS.md"
EVIDENCE_DIR = ROOT / "docs" / "evidence"


def load_dotenv(path: Path) -> dict:
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        env[key] = value
    return env


def get_env(dotenv: dict, key: str) -> str:
    return os.getenv(key) or dotenv.get(key, "")


def http_json(url: str, method: str = "GET", headers: dict | None = None, body: dict | None = None):
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    req.add_header("Accept", "application/json")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return resp.status, {}
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, {"raw": raw}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8") if hasattr(exc, "read") else ""
        if raw:
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"raw": raw}
        else:
            payload = {}
        return exc.code, payload
    except URLError as exc:
        return 0, {"error": f"{exc}"}


def shopify_auth(dotenv: dict) -> tuple[str, str]:
    domain = get_env(dotenv, "SHOPIFY_STORE_DOMAIN")
    token = get_env(dotenv, "SHOPIFY_ADMIN_ACCESS_TOKEN")
    version = get_env(dotenv, "SHOPIFY_API_VERSION") or "2024-10"
    if not (domain and token):
        return "SKIPPED", "Missing SHOPIFY_STORE_DOMAIN or SHOPIFY_ADMIN_ACCESS_TOKEN"
    url = f"https://{domain}/admin/api/{version}/graphql.json"
    status, payload = http_json(
        url,
        method="POST",
        headers={"X-Shopify-Access-Token": token},
        body={"query": "{ shop { name } }"},
    )
    if status != 200:
        return "FAIL", f"HTTP {status}"
    if payload.get("errors"):
        return "FAIL", f"Errors: {payload['errors']}"
    name = payload.get("data", {}).get("shop", {}).get("name", "")
    if not name:
        return "FAIL", "Missing shop name in response"
    return "PASS", f"shop.name={name}"


def meta_token_debug(dotenv: dict) -> tuple[str, str]:
    access_token = get_env(dotenv, "META_ACCESS_TOKEN")
    app_id = get_env(dotenv, "META_APP_ID")
    app_secret = get_env(dotenv, "META_APP_SECRET")
    if not (access_token and app_id and app_secret):
        return "SKIPPED", "Missing META_ACCESS_TOKEN or META_APP_ID or META_APP_SECRET"

    def debug_with(token: str) -> tuple[int, dict]:
        query = urllib.parse.urlencode({"input_token": access_token, "access_token": token})
        url = f"https://graph.facebook.com/debug_token?{query}"
        return http_json(url)

    # Prefer user token as access_token; fall back to app token
    status, payload = debug_with(access_token)
    if status != 200:
        app_token = f"{app_id}|{app_secret}"
        status, payload = debug_with(app_token)

    if status != 200:
        error_detail = ""
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                error_detail = error.get("message") or error.get("type") or str(error)
            elif error:
                error_detail = str(error)
        detail = f"HTTP {status}"
        if error_detail:
            detail = f"{detail} - {error_detail}"
        return "FAIL", detail

    data = payload.get("data", {})
    if not data.get("is_valid"):
        return "FAIL", "Token invalid"
    scopes = data.get("scopes", [])
    scope_str = ",".join(scopes) if scopes else "(none)"
    return "PASS", f"valid scopes={scope_str}"


def n8n_credentials(dotenv: dict) -> tuple[str, str]:
    base_url = get_env(dotenv, "N8N_BASE_URL").rstrip("/")
    api_key = get_env(dotenv, "N8N_API_KEY")
    if not (base_url and api_key):
        return "SKIPPED", "Missing N8N_BASE_URL or N8N_API_KEY"
    paths = ["/api/v1/credentials", "/rest/credentials"]
    headers = [
        ("X-N8N-API-KEY", api_key),
        ("Authorization", f"Bearer {api_key}"),
    ]
    last_status = None
    for path in paths:
        url = f"{base_url}{path}"
        for header, value in headers:
            status, payload = http_json(url, headers={header: value})
            last_status = status
            if status == 200:
                items = payload.get("data", payload)
                if not isinstance(items, list):
                    return "FAIL", f"Unexpected response shape from {path}"
                ids = [str(item.get("id")) for item in items if item.get("id") is not None]
                if not ids:
                    return "FAIL", f"No credential IDs returned from {path}"
                return "PASS", f"credential_ids={','.join(ids)}"
            if status in (401, 404, 405):
                continue
            if status == 0:
                error_detail = ""
                if isinstance(payload, dict):
                    error_detail = payload.get("error", "")
                return "FAIL", f"Request failed: {error_detail or 'network error'}"
            return "FAIL", f"HTTP {status} from {path}"
    return "FAIL", f"HTTP {last_status} from credentials endpoint"


def update_acceptance(table_lines: list[str], updates: dict[str, tuple[str, str, str]]) -> list[str]:
    new_lines = []
    for line in table_lines:
        if not line.startswith("|"):
            new_lines.append(line)
            continue
        parts = [p.strip() for p in line.strip().split("|")][1:-1]
        if not parts:
            new_lines.append(line)
            continue
        test_id = parts[0]
        if test_id not in updates:
            new_lines.append(line)
            continue
        if len(parts) < 8:
            new_lines.append(line)
            continue
        actual, status, evidence = updates[test_id]
        parts[5] = actual
        parts[6] = status
        parts[7] = evidence
        new_lines.append("| " + " | ".join(parts) + " |")
    return new_lines


def main() -> int:
    dotenv = load_dotenv(ENV_PATH)
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%d %H:%MZ")
    evidence_file = EVIDENCE_DIR / f"phase0-evidence-{now.strftime('%Y%m%d-%H%MZ')}.txt"
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    results = {}
    results["AT-P0-SHOPIFY-01"] = shopify_auth(dotenv)
    results["AT-P0-META-01"] = meta_token_debug(dotenv)
    results["AT-P0-N8N-01"] = n8n_credentials(dotenv)

    with evidence_file.open("w", encoding="utf-8") as handle:
        handle.write(f"Phase 0 evidence run: {stamp}\n")
        for test_id, (status, detail) in results.items():
            handle.write(f"{test_id}: {status} - {detail}\n")

    if not ACCEPTANCE_PATH.exists():
        print("Acceptance tests file not found.", file=sys.stderr)
        return 2

    lines = ACCEPTANCE_PATH.read_text(encoding="utf-8").splitlines()
    updates = {}
    for test_id, (status, detail) in results.items():
        updates[test_id] = (detail, status, str(evidence_file.relative_to(ROOT)))

    updated = update_acceptance(lines, updates)
    ACCEPTANCE_PATH.write_text("\n".join(updated) + "\n", encoding="utf-8")

    print(f"Evidence written to {evidence_file}")
    for test_id, (status, detail) in results.items():
        print(f"{test_id}: {status} ({detail})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
