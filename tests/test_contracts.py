"""Cross-folder contract checks: the agent's instructions (skills/), the tool server (toolserver/),
the network policy (scripts/openshell/) and the impact fields (service/) must agree."""

import re
from pathlib import Path

from fastapi.routing import APIRoute

from toolserver.app import app
from toolserver.stub_data import STUB

REPO = Path(__file__).resolve().parent.parent
SKILL = (REPO / "skills/pitcrew/SKILL.md").read_text()
POLICY = (REPO / "scripts/openshell/pitcrew-toolserver.yaml").read_text()


def _routes() -> set[tuple[str, str]]:
    out = set()
    for r in app.routes:
        if isinstance(r, APIRoute):
            for m in r.methods:
                out.add((m, re.sub(r"\{[^}]+\}", "*", r.path)))
    return out


def _skill_calls() -> set[tuple[str, str]]:
    calls = set()
    for line in SKILL.splitlines():
        for m in re.finditer(r"curl -s (?:-X (POST) )?\"?\$BASE(/[^\s\"?`]*)", line):
            path = re.sub(r"<[^>]+>", "*", m.group(2))
            calls.add((m.group(1) or "GET", path))
    return calls


def _policy_rules() -> set[tuple[str, str]]:
    return {(m, p) for m, p in re.findall(r"method: (\w+),\s+path: \"([^\"]+)\"", POLICY)}


def test_every_skill_call_exists_on_the_toolserver():
    missing = _skill_calls() - _routes()
    assert not missing, f"SKILL.md calls endpoints the tool server doesn't have: {missing}"


def test_policy_allows_every_skill_call():
    missing = _skill_calls() - _policy_rules()
    assert not missing, f"the OpenShell policy would block: {missing}"


def test_policy_allows_nothing_the_toolserver_lacks():
    extra = _policy_rules() - _routes()
    assert not extra, f"policy allows paths that don't exist: {extra}"


def test_impact_fields_used_by_the_agent_exist():
    for field in ("delayed_jobs", "affected_customers", "longest_wait", "backlog", "estimated_value"):
        assert field in STUB["impact"], field
        assert field in SKILL, field


def test_stub_matches_real_impact_shape(conn):
    from service import impact
    assert set(impact.compute(conn)) == set(STUB["impact"])
