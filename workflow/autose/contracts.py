"""Structural checks do not purport to prove semantic correctness."""
from __future__ import annotations

import ast
import re

from .common import require, text

DOC_HEADINGS = {
    "requirements_spec.md": ("# Requirements Specification", "## Document control", "## Purpose and scope", "## Sources and evidence", "## Stakeholders, actors, and goals", "## Assumptions and constraints", "## Functional requirements", "## Non-functional requirements", "## Acceptance criteria", "## Dependencies, interfaces, and risks", "## Traceability matrix", "## Decisions and change history", "## Readiness statement"),
    "assumptions_questions.md": ("# Assumptions, Questions, Conflicts, and Risks", "## Assumptions", "## Missing information", "## Conflicts and apparent tensions", "## Unverifiable claims", "## Risks", "## Prioritized questions", "## External evidence limitations"),
    "validation_summary.md": ("# Validation Summary", "## Validation matrix", "## Readiness decisions", "## Traceability audit", "## Evidence and approval gaps", "## Blockers and next actions", "## Human-review handoff", "## Termination status"),
}


def specification(data, issue):
    require(isinstance(data, dict), "requirements schema")
    docs = data.get("documents", {})
    require(set(docs) == set(DOC_HEADINGS), "three original A1 artifacts required")
    for name, headings in DOC_HEADINGS.items():
        text(docs[name], name)
        require(all(h in docs[name] for h in headings), f"missing A1 headings: {name}")
    require(isinstance(data.get("questions"), list), "questions schema")
    if data.get("status") == "needs_clarification" or data["questions"]:
        require(data["questions"], "clarification must name questions")
        return False
    require(data.get("status") == "READY", "A1 readiness not READY")
    criteria = data.get("criteria")
    require(isinstance(criteria, list) and 1 <= len(criteria) <= 8, "AC count")
    seen = set()
    for ac in criteria:
        require(re.fullmatch(r"AC-\d{3}", ac["id"]) and ac["id"] not in seen, "AC identity")
        seen.add(ac["id"])
        require(re.fullmatch(r"(?:FR|NFR|CON)-\d{3}", ac["requirement"]), "requirement ID")
        for key in ("precondition", "action", "expected", "measurement", "pass_fail", "source_quote"):
            text(ac.get(key), key, 4000)
        require(ac["source_quote"] in issue["body"], "AC quote is not in frozen issue")
        require(ac.get("evidence") == "EXPLICIT" and ac.get("approval") == "CONFIRMED", "inferred/unapproved AC cannot enter implementation")
    return True


def design(data, spec, source):
    require(isinstance(data, dict), "design schema")
    text(data.get("design.md"), "design.md")
    require(set(data.get("coverage", {})) == {a["id"] for a in spec["criteria"]}, "design AC coverage")
    require(set(data.get("constraints", {})) == {str(n) for n in range(1, 6)}, "all five A2 constraints required")
    for reason in data["constraints"].values():
        text(reason, "constraint analysis", 4000)
    targets = data.get("targets")
    require(isinstance(targets, list) and targets, "design targets")
    for target in targets:
        path, function = target["path"], target["function"]
        require(path in source and path.startswith("tinydb/"), "design path not in actual TinyDB source")
        text(function, "function", 200)
        nodes = ast.walk(ast.parse(source[path]))
        names = {n.name for n in nodes if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef))}
        require(target.get("new") is True or function.split(".")[-1] in names, "design function not found")
    for targets_for_ac in data["coverage"].values():
        require(isinstance(targets_for_ac, list) and targets_for_ac, "empty criterion plan")
        require(all(isinstance(i, int) and 0 <= i < len(targets) for i in targets_for_ac), "invalid design target index")


def semantic(data):
    require(isinstance(data, dict) and data.get("pass") is True, "semantic gate rejected")
    text(data.get("evidence"), "semantic validation evidence", 8000)
    require(data.get("unsupported_scope") is False, "unsupported/invented scope")


def review(data, source):
    require(data.get("verdict") in {"APPROVE", "REQUEST_CHANGES"}, "review verdict")
    text(data.get("summary"), "review summary", 8000)
    require(isinstance(data.get("findings"), list) and len(data["findings"]) <= 20, "findings schema")
    for finding in data["findings"]:
        require(finding["path"] in source, "finding path absent")
        require(isinstance(finding["line"], int) and 1 <= finding["line"] <= len(source[finding["path"]].splitlines()), "finding line absent")
        text(finding.get("evidence"), "finding evidence", 4000)
        require(finding.get("stage") in {"requirements", "design", "implementation", "testing"}, "invalid review routing")
    if data["verdict"] == "REQUEST_CHANGES":
        require(data["findings"], "rejection requires findings")
    else:
        require(not data["findings"], "approval cannot contain unresolved findings")
    require(data.get("run_tests") in {True, False}, "review test request required")
